# 一键安装包 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a self-extracting one-click installer (QQForward_Setup.exe) that bundles QQForward.exe + LLBot into a single distributable file for non-technical users.

**Architecture:** PyInstaller packages tray.py + all Python modules into QQForward.exe (--onefile --windowed). LLBot-CLI-Win-x64 sits alongside the exe. First run detects missing config.json and opens a 4-page ttk wizard. The Flask forward server runs in-process (daemon thread) instead of as a subprocess, avoiding PyInstaller subprocess complications.

**Tech Stack:** Python 3.10+, tkinter/ttk, PyInstaller, 7-Zip SFX, pystray, Flask

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `qq-message-forward.py` | Modify | Lazy config loading — importable without config.json |
| `tray.py` | Modify | New startup flow: wizard trigger → llbot launch → Flask thread → tray |
| `wizard.py` | **Create** | 4-page ttk configuration wizard |
| `tests/test_wizard.py` | **Create** | Wizard logic tests (validation, config generation) |
| `tests/test_forward.py` | **Create** | Forward module lazy-load tests |
| `build.bat` | **Create** | PyInstaller + 7-Zip SFX build script |
| `.gitignore` | Modify | Add build artifact entries |

---

### Task 1: Refactor qq-message-forward.py — Lazy Config Loading

**Why:** Currently config is loaded at module level (line 16-25), which crashes on `import` if config.json doesn't exist. The wizard creates config.json after import, so we need lazy loading.

**Files:**
- Create: `tests/test_forward.py`
- Modify: `qq-message-forward.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_forward.py
"""Test forward module lazy config loading"""
import sys
import os
import json
import tempfile
import importlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_module_imports_without_config():
    """After import, config should NOT be loaded yet (lazy loading)"""
    import importlib
    fwd = importlib.import_module('qq-message-forward')
    assert hasattr(fwd, 'app')
    assert hasattr(fwd, 'get_config')
    # Config should stay None until first get_config() call
    assert fwd._config is None


def test_get_config_raises_after_set_path_to_nonexistent():
    """get_config raises FileNotFoundError when path points to nonexistent file"""
    import importlib
    fwd = importlib.import_module('qq-message-forward')

    # Reset cached config
    fwd._config = None

    # Point to a nonexistent file
    tmpdir = tempfile.mkdtemp()
    nonexistent = os.path.join(tmpdir, 'no_config.json')
    fwd.CONFIG_PATH = nonexistent

    try:
        fwd.get_config()
        assert False, 'Should have raised FileNotFoundError'
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    finally:
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)
        fwd._config = None  # Reset for other tests


def test_get_config_loads_valid_config():
    """get_config should load and cache a valid config file"""
    import importlib
    fwd = importlib.import_module('qq-message-forward')
    fwd._config = None

    tmpdir = tempfile.mkdtemp()
    config_path = os.path.join(tmpdir, 'config.json')
    test_data = {'robot_qq': 12345, 'forward_rules': {}, 'llbot_api': 'http://test:3000'}

    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(test_data, f)

    fwd.CONFIG_PATH = config_path
    try:
        cfg = fwd.get_config()
        assert cfg['robot_qq'] == 12345
        # Second call returns cached version
        cfg2 = fwd.get_config()
        assert cfg2 is cfg
    finally:
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)
        fwd._config = None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd D:/DevVProgram/QQLLOneBotCLI && python -m pytest tests/test_forward.py::test_module_imports_without_config -v
```

Expected: FAIL — `AttributeError: module 'qq-message-forward' has no attribute '_config'` (old code has no lazy-load `_config` global). Other tests fail too because `_config` doesn't exist.

- [ ] **Step 3: Refactor qq-message-forward.py for lazy config loading**

Replace lines 15-25 (the config loading block):

```python
# 配置文件路径
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
_config = None


def load_config():
    """从文件加载配置（强制重新加载）"""
    global _config
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        _config = json.load(f)
    return _config


def get_config():
    """获取配置（延迟加载，首次访问时从文件读取）"""
    global _config
    if _config is None:
        _config = load_config()
    return _config
```

Remove the old module-level lines 16-25:
```python
# DELETE these lines:
# with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
#     config = json.load(f)
#
# ROBOT_QQ = config['robot_qq']
# FORWARD_RULES: Dict[str, List[str]] = config['forward_rules']
# LLBOT_API = config['llbot_api']
# LLBOT_TOKEN = config.get('llbot_token', '')
# DUPLICATE_WINDOW = config['forward']['duplicate_window']
# SEND_INTERVAL = config['forward']['send_interval']
# FILTER_CONFIG = config.get('filter', {})
```

Replace lines 50-53 (module-level headers):

```python
# 配置请求头（带Token）— 每次请求前获取
def _get_headers():
    cfg = get_config()
    h = {'Content-Type': 'application/json'}
    token = cfg.get('llbot_token', '')
    if token:
        h['Authorization'] = f'Bearer {token}'
    return h
```

Update the `is_duplicate` function (line 62-72) — replace `DUPLICATE_WINDOW`:

```python
def is_duplicate(msg_id: str) -> bool:
    """检查消息是否重复，同时清理过期缓存"""
    cfg = get_config()
    window = cfg['forward']['duplicate_window']
    now = time.time()
    expired = [k for k, v in msg_cache.items() if now - v > window * 10]
    for k in expired:
        del msg_cache[k]
    if msg_id in msg_cache:
        if now - msg_cache[msg_id] < window:
            return True
    msg_cache[msg_id] = now
    return False
```

Update the `rate_limit` function (line 75-82) — replace `SEND_INTERVAL`:

```python
def rate_limit(target_group: str) -> None:
    """限流：保证单群发送间隔不小于配置值"""
    cfg = get_config()
    interval = cfg['forward']['send_interval']
    now = time.time()
    if target_group in last_send_time:
        wait = interval - (now - last_send_time[target_group])
        if wait > 0:
            time.sleep(wait)
    last_send_time[target_group] = time.time()
```

Update the `webhook` function (line 85-170) — add config loading at the top:

```python
@app.post('/webhook')
def webhook():
    try:
        cfg = get_config()
        robot_qq = cfg['robot_qq']
        forward_rules = cfg['forward_rules']
        llbot_api = cfg['llbot_api']
        filter_config = cfg.get('filter', {})

        data = request.json
        # ... rest of the function unchanged ...
```

Then replace references inside webhook():
- `ROBOT_QQ` → `robot_qq` (line 111)
- `FORWARD_RULES` → `forward_rules` (lines 116, 138)
- `LLBOT_API` → `llbot_api` (line 143)
- `FILTER_CONFIG` → `filter_config` (lines 125, 127-128, 130, 132-133)
- `headers=headers` → `headers=_get_headers()` (line 148)

Update the `__main__` block (line 173-180) — add config load for logger info:

```python
if __name__ == '__main__':
    cfg = get_config()
    logger.info('=' * 50)
    logger.info('✅ QQ群转发服务已启动')
    logger.info(f"📋 WebHook地址: http://127.0.0.1:8080/webhook")
    logger.info(f"📋 转发规则: {cfg['forward_rules']}")
    logger.info(f"📋 过滤状态: QR码={'启用' if cfg['filter'].get('qrcode',{}).get('enabled') else '关闭'} | 联系方式={'启用' if cfg['filter'].get('contact',{}).get('enabled') else '关闭'} | 模式={'仅日志' if cfg['filter'].get('log_only') else '拦截'}")
    logger.info('=' * 50)
    app.run(host='127.0.0.1', port=8080, debug=False, threaded=True)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd D:/DevVProgram/QQLLOneBotCLI && python -m pytest tests/test_forward.py -v
```

Expected: All 3 tests PASS.

- [ ] **Step 5: Run existing filter tests to confirm no regression**

```bash
cd D:/DevVProgram/QQLLOneBotCLI && python -m pytest tests/test_filter.py -v
```

Expected: All tests PASS.

- [ ] **Step 6: Commit**

```bash
git add qq-message-forward.py tests/test_forward.py
git commit -m "refactor(forward): lazy config loading for import without config.json"
```

---

### Task 2: Create wizard.py — GUI Configuration Wizard

**Files:**
- Create: `wizard.py`
- Create: `tests/test_wizard.py`

- [ ] **Step 1: Write wizard logic tests (pure functions, no GUI)**

```python
# tests/test_wizard.py
"""Test wizard business logic (validation, config generation)"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wizard import validate_qq_number, generate_config, DEFAULT_CONFIG


def test_validate_qq_number_valid():
    assert validate_qq_number('12345') == True
    assert validate_qq_number('2776992588') == True
    assert validate_qq_number('10001') == True


def test_validate_qq_number_invalid():
    assert validate_qq_number('') == False
    assert validate_qq_number('abc') == False
    assert validate_qq_number('12.5') == False
    assert validate_qq_number('12345 67890') == False
    assert validate_qq_number('12345a') == False


def test_validate_qq_number_boundary():
    """QQ 号至少 5 位"""
    assert validate_qq_number('1234') == False
    assert validate_qq_number('12345') == True


def test_generate_config_basic():
    """生成包含 QQ 号 + 默认值的完整配置"""
    result = generate_config(robot_qq='2776992588', forward_rules={}, filter_enabled=True)

    assert result['robot_qq'] == 2776992588
    assert result['llbot_api'] == 'http://127.0.0.1:3000'
    assert result['llbot_token'] == ''
    assert result['forward']['duplicate_window'] == 5
    assert result['forward']['send_interval'] == 1.0
    assert result['filter']['qrcode']['enabled'] == True
    assert result['filter']['contact']['enabled'] == True
    assert result['filter']['log_only'] == False


def test_generate_config_filter_disabled():
    result = generate_config(robot_qq='12345', forward_rules={}, filter_enabled=False)

    assert result['filter']['qrcode']['enabled'] == False
    assert result['filter']['contact']['enabled'] == False


def test_generate_config_with_rules():
    rules = {'1079264158': ['1080631149', '702961941']}
    result = generate_config(robot_qq='2776992588', forward_rules=rules, filter_enabled=True)

    assert result['forward_rules'] == rules
    assert '1079264158' in result['forward_rules']
    assert len(result['forward_rules']['1079264158']) == 2


def test_generate_config_preserves_default_keywords():
    """生成的配置应包含默认的过滤关键词"""
    result = generate_config(robot_qq='12345', forward_rules={}, filter_enabled=True)
    assert len(result['filter']['qrcode']['keywords']) > 0
    assert len(result['filter']['contact']['keywords']) > 0
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd D:/DevVProgram/QQLLOneBotCLI && python -m pytest tests/test_wizard.py -v
```

Expected: FAIL — module `wizard` not found.

- [ ] **Step 3: Create wizard.py**

```python
"""QQ Forward — 首次运行配置向导"""
import json
import os
import sys
import tkinter as tk
from tkinter import ttk


def get_base_dir():
    """获取应用根目录"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


DEFAULT_CONFIG = {
    'robot_qq': 0,
    'forward_rules': {},
    'llbot_api': 'http://127.0.0.1:3000',
    'llbot_token': '',
    'filter': {
        'qrcode': {
            'enabled': True,
            'keywords': [
                '添加', '扫码', '扫一扫', '扫描', '联系人',
                'VX', 'v:', '微信', '私聊',
            ],
            'mode': 'image_with_keyword',
            'block_pure_image': True,
        },
        'contact': {
            'enabled': True,
            'patterns': {
                'phone': '1[3-9]\\d{9}',
                'qq': '(?<!\\d)[1-9]\\d{4,9}(?!\\d)',
                'wechat': 'wxid_[a-z0-9]+',
                'email': '[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}',
            },
            'keywords': [
                'QQ', '微信', '飞书', '续费', '费用', 'VX', 'v:',
                '钉钉', '联系人', '我的Q', '我的V', '联系我',
                '加好友', '私聊我', '加我',
            ],
        },
        'log_only': False,
    },
    'forward': {
        'duplicate_window': 5,
        'send_interval': 1.0,
    },
}


def validate_qq_number(value: str) -> bool:
    """QQ 号纯数字且至少 5 位"""
    return value.isdigit() and len(value) >= 5


def generate_config(robot_qq: str, forward_rules: dict, filter_enabled: bool) -> dict:
    """根据向导输入生成完整配置 dict"""
    import copy
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    cfg['robot_qq'] = int(robot_qq)
    cfg['forward_rules'] = forward_rules
    if not filter_enabled:
        cfg['filter']['qrcode']['enabled'] = False
        cfg['filter']['contact']['enabled'] = False
    return cfg


def save_config(cfg: dict, path: str) -> None:
    """原子写入配置文件"""
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def run_wizard() -> dict | None:
    """运行配置向导，返回生成的 config dict；用户取消则返回 None"""
    root = tk.Tk()
    root.title('QQ Forward — 首次配置')
    root.resizable(False, False)
    root.configure(bg='#f5f5f5')

    # 居中窗口
    win_w, win_h = 480, 400
    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()
    x = (screen_w - win_w) // 2
    y = (screen_h - win_h) // 2
    root.geometry(f'{win_w}x{win_h}+{x}+{y}')

    result: dict | None = None
    pages = {}
    current_page = [0]

    # ---- Shared state ----
    qq_var = tk.StringVar()
    qq_error = tk.StringVar()
    rules: dict[str, list[str]] = {}
    filter_var = tk.BooleanVar(value=True)

    container = ttk.Frame(root)
    container.pack(fill='both', expand=True)

    # ---- Page 1: Welcome ----
    p1 = ttk.Frame(container)
    p1.columnconfigure(0, weight=1)
    ttk.Label(p1, text='欢迎使用 QQ 消息转发', font=('微软雅黑', 14, 'bold')).grid(
        row=0, column=0, pady=(60, 10))
    ttk.Label(p1, text='此向导将帮助您完成首次配置', font=('微软雅黑', 10)).grid(
        row=1, column=0, pady=5)
    ttk.Label(p1, text='整个过程只需 1-2 分钟', font=('微软雅黑', 10)).grid(
        row=2, column=0, pady=5)
    ttk.Button(p1, text='下一步 →', command=lambda: show_page(1)).grid(
        row=3, column=0, pady=(40, 10))
    pages[0] = p1

    # ---- Page 2: QQ Number ----
    p2 = ttk.Frame(container)
    p2.columnconfigure(0, weight=1)
    ttk.Label(p2, text='请输入机器人 QQ 号', font=('微软雅黑', 12, 'bold')).grid(
        row=0, column=0, pady=(60, 15), columnspan=2)
    ttk.Label(p2, text='即您的 QQ 机器人账号，用于区分自身消息', font=('微软雅黑', 9)).grid(
        row=1, column=0, pady=(0, 15), columnspan=2)

    qq_entry = ttk.Entry(p2, textvariable=qq_var, width=30, font=('微软雅黑', 11))
    qq_entry.grid(row=2, column=0, columnspan=2, pady=5)
    qq_label = ttk.Label(p2, textvariable=qq_error, foreground='red')
    qq_label.grid(row=3, column=0, columnspan=2, pady=5)

    def on_qq_change(*_):
        val = qq_var.get().strip()
        if not val:
            qq_error.set('')
            next_btn.state(['disabled'])
        elif not validate_qq_number(val):
            qq_error.set('QQ 号必须是纯数字，至少 5 位')
            next_btn.state(['disabled'])
        else:
            qq_error.set('')
            next_btn.state(['!disabled'])

    qq_var.trace_add('write', on_qq_change)

    btn_frame_2 = ttk.Frame(p2)
    btn_frame_2.grid(row=4, column=0, columnspan=2, pady=(30, 10))
    ttk.Button(btn_frame_2, text='← 上一步', command=lambda: show_page(0)).pack(side='left', padx=5)
    next_btn = ttk.Button(btn_frame_2, text='下一步 →', command=lambda: show_page(2))
    next_btn.pack(side='left', padx=5)
    next_btn.state(['disabled'])
    pages[1] = p2

    # ---- Page 3: Forward Rules ----
    p3 = ttk.Frame(container)
    p3.columnconfigure(0, weight=1)
    ttk.Label(p3, text='配置消息转发规则', font=('微软雅黑', 12, 'bold')).grid(
        row=0, column=0, pady=(40, 10), columnspan=2)
    ttk.Label(p3, text='设置哪些群的消息自动转发到哪些群（可选，稍后也能加）',
              font=('微软雅黑', 9)).grid(row=1, column=0, pady=(0, 10), columnspan=2)

    rule_frame = ttk.Frame(p3)
    rule_frame.grid(row=2, column=0, columnspan=2, pady=5)

    ttk.Label(rule_frame, text='源群 QQ:').grid(row=0, column=0, sticky='w', padx=2)
    src_entry = ttk.Entry(rule_frame, width=18)
    src_entry.grid(row=0, column=1, padx=2)

    ttk.Label(rule_frame, text='目标群:').grid(row=0, column=2, sticky='w', padx=2)
    dst_entry = ttk.Entry(rule_frame, width=18)
    dst_entry.grid(row=0, column=3, padx=2)

    ttk.Button(rule_frame, text='添加', command=lambda: add_rule()).grid(
        row=0, column=4, padx=5)

    rules_list = tk.Listbox(p3, height=4, width=55)
    rules_list.grid(row=3, column=0, columnspan=2, pady=5)

    ttk.Button(p3, text='删除选中规则', command=lambda: del_rule()).grid(
        row=4, column=0, columnspan=2, pady=2)

    def refresh_list():
        rules_list.delete(0, 'end')
        for src, dsts in rules.items():
            rules_list.insert('end', f'{src} → {", ".join(dsts)}')

    def add_rule():
        src = src_entry.get().strip()
        dsts = [d.strip() for d in dst_entry.get().split(',') if d.strip()]
        if src and dsts:
            rules[src] = dsts
            refresh_list()
            src_entry.delete(0, 'end')
            dst_entry.delete(0, 'end')

    def del_rule():
        sel = rules_list.curselection()
        if sel:
            text = rules_list.get(sel[0])
            src = text.split(' → ')[0]
            if src in rules:
                del rules[src]
            refresh_list()

    btn_frame_3 = ttk.Frame(p3)
    btn_frame_3.grid(row=5, column=0, columnspan=2, pady=10)
    ttk.Button(btn_frame_3, text='← 上一步', command=lambda: show_page(1)).pack(side='left', padx=5)
    ttk.Button(btn_frame_3, text='下一步 →', command=lambda: show_page(3)).pack(side='left', padx=5)
    pages[2] = p3

    # ---- Page 4: Filter & Finish ----
    p4 = ttk.Frame(container)
    p4.columnconfigure(0, weight=1)
    ttk.Label(p4, text='消息过滤设置', font=('微软雅黑', 12, 'bold')).grid(
        row=0, column=0, pady=(60, 15), columnspan=2)

    ttk.Radiobutton(p4, text='开启过滤（推荐）— 自动拦截二维码广告、联系方式等',
                    variable=filter_var, value=True).grid(
        row=1, column=0, columnspan=2, sticky='w', pady=5, padx=40)
    ttk.Radiobutton(p4, text='暂时关闭 — 所有消息都会转发',
                    variable=filter_var, value=False).grid(
        row=2, column=0, columnspan=2, sticky='w', pady=5, padx=40)

    ttk.Label(p4, text='配置可在启动后通过托盘菜单「设置」随时修改',
              font=('微软雅黑', 8), foreground='gray').grid(
        row=3, column=0, columnspan=2, pady=(20, 10))

    btn_frame_4 = ttk.Frame(p4)
    btn_frame_4.grid(row=4, column=0, columnspan=2, pady=10)
    ttk.Button(btn_frame_4, text='← 上一步', command=lambda: show_page(2)).pack(side='left', padx=5)
    ttk.Button(btn_frame_4, text='✓ 完成配置', command=lambda: on_finish()).pack(side='left', padx=5)
    pages[3] = p4

    # ---- Page Navigation ----
    def show_page(idx):
        for i, page in pages.items():
            page.grid_forget()
        pages[idx].grid(row=0, column=0, sticky='nsew')
        current_page[0] = idx

    def on_finish():
        nonlocal result
        result = generate_config(
            robot_qq=qq_var.get().strip(),
            forward_rules=rules,
            filter_enabled=filter_var.get(),
        )
        root.destroy()

    # Show first page
    show_page(0)

    # Modal loop
    root.mainloop()
    return result
```

- [ ] **Step 4: Run wizard logic tests**

```bash
cd D:/DevVProgram/QQLLOneBotCLI && python -m pytest tests/test_wizard.py -v
```

Expected: All 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add wizard.py tests/test_wizard.py
git commit -m "feat(wizard): add first-run configuration wizard"
```

---

### Task 3: Modify tray.py — New Startup Flow

**Files:**
- Modify: `tray.py`

Changes to `__main__` block (lines 349-437):

- [ ] **Step 1: Replace the startup flow in `__main__`**

Replace lines 349-437 with:

```python
if __name__ == '__main__':
    import importlib
    import wizard as wizard_mod
    fwd = importlib.import_module('qq-message-forward')
    forward_app = fwd.app
    set_forward_config = fwd.set_config_path

    base_dir = wizard_mod.get_base_dir()

    # 设置 forward 模块的配置文件路径（PyInstaller 下与 exe 同目录）
    fwd_config_path = os.path.join(base_dir, 'config.json')
    set_forward_config(fwd_config_path)

    # 检查 LLBot-CLI-Win-x64 目录是否存在
    llbot_dir = os.path.join(base_dir, 'LLBot-CLI-Win-x64')
    if not os.path.isdir(llbot_dir):
        # 尝试在开发模式下查找
        llbot_dir = os.path.join(SCRIPT_DIR, 'LLBot-CLI-Win-x64')

    if not os.path.isdir(llbot_dir):
        from tkinter import messagebox
        root_tmp = tk.Tk()
        root_tmp.withdraw()
        messagebox.showerror(
            '安装不完整',
            '缺少 LLBot 组件目录，请检查安装包是否完整解压。\n\n'
            f'期望路径: {llbot_dir}'
        )
        root_tmp.destroy()
        sys.exit(1)

    # 检查 config.json，不存在则弹出向导
    if not os.path.exists(fwd_config_path):
        from tkinter import messagebox
        root_tmp = tk.Tk()
        root_tmp.withdraw()
        answer = messagebox.askyesno(
            '首次运行',
            '未检测到配置文件，需要先完成配置。\n\n是否现在开始配置？'
        )
        root_tmp.destroy()
        if not answer:
            sys.exit(0)

        wizard_config = wizard_mod.run_wizard()
        if wizard_config is None:
            sys.exit(0)
        wizard_mod.save_config(wizard_config, fwd_config_path)

    # 检查 config.json 是否有效
    try:
        with open(fwd_config_path, 'r', encoding='utf-8') as f:
            json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        from tkinter import messagebox
        root_tmp = tk.Tk()
        root_tmp.withdraw()
        rebuild = messagebox.askyesno(
            '配置文件损坏',
            '配置文件读取失败，是否重新配置？'
        )
        root_tmp.destroy()
        if rebuild:
            wizard_config = wizard_mod.run_wizard()
            if wizard_config is None:
                sys.exit(0)
            wizard_mod.save_config(wizard_config, fwd_config_path)
        else:
            sys.exit(1)

    # 启动 LLBot（后台隐藏窗口）
    llbot_exe = os.path.join(llbot_dir, 'llbot.exe')
    if os.path.exists(llbot_exe):
        subprocess.Popen(
            [llbot_exe],
            cwd=llbot_dir,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0,
        )

    # 等待 LLBot 端口就绪
    for _ in range(20):
        if check_port(LLBOT_PORT):
            break
        time.sleep(1)

    if not check_port(LLBOT_PORT):
        from tkinter import messagebox
        root_tmp = tk.Tk()
        root_tmp.withdraw()
        messagebox.showerror(
            '启动失败',
            'LLBot 启动超时（端口 3000 未响应）。\n\n'
            '请确认 LLBot-CLI-Win-x64 目录是否存在且完整。'
        )
        root_tmp.destroy()
        sys.exit(1)

    # 检查端口 3000/8080 占用，如果被旧进程占用则 kill
    if check_port(FORWARD_PORT):
        for proc in ['python.exe', 'pythonw.exe']:
            subprocess.run(['taskkill', '/f', '/im', proc], capture_output=True)
        time.sleep(1)
        if check_port(FORWARD_PORT):
            from tkinter import messagebox
            root_tmp = tk.Tk()
            root_tmp.withdraw()
            messagebox.showerror(
                '端口占用',
                f'端口 {FORWARD_PORT} 被占用，请关闭占用程序后重试。'
            )
            root_tmp.destroy()
            sys.exit(1)

    # 在 daemon 线程中启动 Flask 转发服务
    def run_flask():
        forward_app.run(
            host='127.0.0.1',
            port=FORWARD_PORT,
            debug=False,
            threaded=True,
            use_reloader=False,
        )

    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # 等待转发端口就绪
    for _ in range(10):
        if check_port(FORWARD_PORT):
            break
        time.sleep(1)

    if not check_port(FORWARD_PORT):
        from tkinter import messagebox
        root_tmp = tk.Tk()
        root_tmp.withdraw()
        messagebox.showwarning(
            '启动警告',
            '转发服务可能未启动成功，请稍后在托盘面板中查看状态。'
        )
        root_tmp.destroy()

    # 声明应用身份
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            'QQLL.OneBot.Forward'
        )
    except Exception:
        pass

    # 创建 tk 主窗口
    root = tk.Tk()
    root.withdraw()
    root.title('QQ Forward')
    root.resizable(True, True)

    # 设置窗口图标
    ico_path = os.path.join(SCRIPT_DIR, 'app.ico')
    if not os.path.exists(ico_path):
        ico_path = os.path.join(base_dir, 'app.ico')
    _save_icon_file(ico_path)
    try:
        root.iconbitmap(ico_path)
    except Exception:
        pass

    root.protocol('WM_DELETE_WINDOW', lambda: hide_main_window(root))

    # Tab 标签页
    style = ttk.Style()
    style.configure('TNotebook.Tab', padding=(20, 5))

    notebook = ttk.Notebook(root, padding=5)
    notebook.pack(fill='both', expand=True, padx=5, pady=5)
    notebook.add(create_status_tab(notebook), text='状态')
    notebook.add(settings_mod.create_settings_frame(notebook), text='设置')

    # 底部按钮栏
    bottom = ttk.Frame(root, padding=5)
    bottom.pack(fill='x', side='bottom')
    ttk.Button(bottom, text='隐藏到托盘',
               command=lambda: hide_main_window(root)).pack(side='right', padx=5)

    # 恢复窗口尺寸
    saved_geo = load_window_geometry()
    root.geometry(saved_geo or '1100x750')

    def _on_configure(event):
        global _save_timer_id
        if root.wm_state() != 'normal' or event.widget is not root:
            return
        if _save_timer_id:
            root.after_cancel(_save_timer_id)
        _save_timer_id = root.after(
            500, lambda: save_window_geometry(root.geometry())
        )

    root.bind('<Configure>', _on_configure)

    # 启动托盘
    icon = setup_tray(root, show_main_window)

    # 桌面快捷方式（首次运行自动创建）
    create_desktop_shortcut()

    # 显示主窗口
    show_main_window(root)
    _set_taskbar_icon(root.winfo_id(), ico_path)

    root.mainloop()
```

- [ ] **Step 2: Add `set_config_path` to qq-message-forward.py**

In `qq-message-forward.py`, add a helper to change config path externally:

```python
def set_config_path(path: str) -> None:
    """设置配置文件路径（由 tray.py 在启动时调用）"""
    global CONFIG_PATH, _config
    CONFIG_PATH = path
    _config = None  # 重置缓存，强制重新加载
```

- [ ] **Step 3: Remove unused `start_forward` / `stop_forward` logic from tray.py**

The old `start_forward` (line 67-79) and `stop_forward` (line 81-91) functions are now unused. Remove them. Also remove the `forward_process` global (line 54).

- [ ] **Step 4: Run all existing tests**

```bash
cd D:/DevVProgram/QQLLOneBotCLI && python -m pytest tests/ -v
```

Expected: All tests PASS (filter + forward + wizard).

- [ ] **Step 5: Commit**

```bash
git add tray.py qq-message-forward.py
git commit -m "feat(tray): integrate wizard, launch llbot, run Flask in-process"
```

---

### Task 4: Create build.bat

**Files:**
- Create: `build.bat`

- [ ] **Step 1: Create build.bat**

```batch
@echo off
chcp 65001 >nul
title QQForward — 构建脚本
cd /d "%~dp0"

echo ====================================
echo   QQForward 一键安装包 — 构建
echo ====================================
echo.

:: ===== 预检查 =====
where python >nul 2>&1 || (echo [错误] 未找到 Python & pause & exit /b 1)
where pyinstaller >nul 2>&1 || (echo [错误] 未找到 PyInstaller，请先 pip install pyinstaller & pause & exit /b 1)
where 7z >nul 2>&1 || (echo [错误] 未找到 7-Zip，请先安装并加入 PATH & pause & exit /b 1)

:: ===== [1/5] 清理旧产物 =====
echo [1/5] 清理旧构建产物 ...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist output rmdir /s /q output
echo    清理完成

:: ===== [2/5] PyInstaller 打包 =====
echo [2/5] PyInstaller 打包 QQForward.exe ...
pyinstaller --onefile --windowed --icon=app.ico --name QQForward --clean ^
    --add-data "filter.py;." ^
    --add-data "settings.py;." ^
    --add-data "wizard.py;." ^
    --add-data "qq-message-forward.py;." ^
    --hidden-import pystray ^
    --hidden-import PIL ^
    --hidden-import flask ^
    --hidden-import requests ^
    --hidden-import filter ^
    --hidden-import settings ^
    --hidden-import wizard ^
    --hidden-import qq_message_forward ^
    tray.py

if %errorlevel% neq 0 (
    echo [错误] PyInstaller 打包失败
    pause
    exit /b 1
)
echo    打包完成: dist\QQForward.exe

:: ===== [3/5] 准备打包目录 =====
echo [3/5] 准备打包目录 ...
mkdir output\QQForward
copy dist\QQForward.exe output\QQForward\ >nul
xcopy /E /I /Q LLBot-CLI-Win-x64 output\QQForward\LLBot-CLI-Win-x64 >nul
echo    打包目录已就绪

:: ===== [4/5] 7-Zip SFX 打包 =====
echo [4/5] 7-Zip SFX 打包 ...

:: 生成 SFX 配置文件
(
echo ;!@Install@!UTF-8!
echo Title="QQ消息转发"
echo BeginPrompt="即将安装 QQ消息转发 到当前目录。继续？"
echo ExecuteFile="QQForward.exe"
echo ;!@InstallEnd@!
) > output\sfx_config.txt

:: 先用 7z 压缩为 .7z
cd output
7z a -mx=9 -mfb=273 -ms=on -mmt=on QQForward.7z QQForward\ >nul

:: 下载 7-Zip SFX 模块（如果没有）
if not exist "..\7zS.sfx" (
    echo    正在下载 7-Zip SFX 模块...
    powershell -Command "Invoke-WebRequest -Uri 'https://7-zip.org/a/7z2408-extra.7z' -OutFile '7z_extra.7z'"
    7z e 7z_extra.7z 7zS.sfx -aoa >nul
    copy 7zS.sfx ..\7zS.sfx >nul
    del 7zS.sfx 7z_extra.7z
)

:: 拼接 SFX 模块 + 配置 + 压缩包
copy /b "..\7zS.sfx" + sfx_config.txt + QQForward.7z "..\QQForward_Setup.exe" >nul
cd ..

:: 注入图标
if exist app.ico (
    powershell -Command ^
        "$path = Resolve-Path 'QQForward_Setup.exe';" ^
        "Write-Host '    SFX 图标需要通过 Resource Hacker 手动注入 app.ico'"
)

echo    打包完成: QQForward_Setup.exe

:: ===== [5/5] 完成 =====
echo [5/5] 完成！
echo.
echo ====================================
echo   ✅ 构建完成
echo.
echo   输出: QQForward_Setup.exe
echo   大小: 
dir QQForward_Setup.exe | find "QQForward_Setup.exe"
echo ====================================
echo.
pause
```

- [ ] **Step 2: Commit**

```bash
git add build.bat
git commit -m "build: add PyInstaller + 7-Zip SFX build script"
```

---

### Task 5: Update .gitignore

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: Add build artifact entries to .gitignore**

Append to `.gitignore`:

```gitignore
# Build artifacts
build/
dist/
output/
*.spec
7zS.sfx
QQForward_Setup.exe
```

- [ ] **Step 2: Commit**

```bash
git add .gitignore
git commit -m "chore: add build artifacts to .gitignore"
```

---

### Task 6: Integration Smoke Test

- [ ] **Step 1: Verify dev-mode startup flow**

```bash
cd D:/DevVProgram/QQLLOneBotCLI

# 1. 临时重命名 config.json 模拟首次运行
move config.json config.json.bak

# 2. 启动 tray.py（会弹出向导）
python tray.py
# 手动验证: 向导出现 → 填写 QQ 号 → 点完成 → 启动托盘

# 3. 检查 config.json 已生成
python -c "import json; cfg=json.load(open('config.json')); assert cfg['robot_qq']!=0, 'QQ号未被写入'"
echo "config.json 生成成功"

# 4. 恢复原 config
move config.json.bak config.json
```

- [ ] **Step 2: Verify PyInstaller build runs**

```bash
cd D:/DevVProgram/QQLLOneBotCLI

# 构建
call build.bat

# 检查产物
dir QQForward_Setup.exe
dir dist\QQForward.exe

# 运行 PyInstaller 打包的 exe（在开发机上测试）
# 手动: 双击 dist\QQForward.exe
# 验证: 能启动，不闪退
```

- [ ] **Step 3: Run full test suite one final time**

```bash
cd D:/DevVProgram/QQLLOneBotCLI && python -m pytest tests/ -v
```

Expected: All tests PASS.

---

### Task 7: Final Commit

- [ ] **Step 1: Commit any remaining changes and push**

```bash
git add -A
git commit -m "feat: complete one-click installer implementation"
```
