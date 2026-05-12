# 状态日志文件输出 + 滚动交互修复 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 forward.py 日志不写入文件 + tray.py 日志面板无滚动条两个问题。

**Architecture:** forward.py 模块加载时不再仅依赖 stderr，新增 `set_log_path()` 函数在 tray.py 启动阶段注入日志文件路径，通过 FileHandler 写入日志文件。tray.py 日志控件包裹滚动条，自动刷新时仅在用户处于底部时才滚动。

**Tech Stack:** Python logging (FileHandler), tkinter (Text + Scrollbar)

---

### Task 1: forward.py — 新增 set_log_path() 函数

**Files:**
- Modify: `forward.py:41-52`

- [ ] **Step 1: 重构 logging 初始化，添加 set_log_path()**

将模块级 logging 初始化重构为两部分：
1. 模块加载时：仅尝试 stderr 重编码
2. `set_log_path()` 调用时：添加 FileHandler

```python
# 在 set_config_path 之后、stderr 检查之前，插入 LOG_PATH 变量

LOG_PATH = None

def set_log_path(path: str) -> None:
    """设置日志文件路径（由 tray.py 在启动时调用）"""
    global LOG_PATH
    LOG_PATH = path
    fh = logging.FileHandler(path, encoding='utf-8')
    fh.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    fh.setLevel(logging.INFO)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(fh)

# 确保 stderr 输出 UTF-8，与日志文件编码一致（windowed 模式下 stderr 为 None）
if sys.stderr:
    sys.stderr.reconfigure(encoding='utf-8')

# 初始化日志（仅在 stderr 可用时添加控制台输出）
if sys.stderr:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
logger = logging.getLogger(__name__)
```

- [ ] **Step 2: 验证 forward.py 语法正确**

```bash
python -c "import py_compile; py_compile.compile('D:/DevVProgram/QQLLOneBotCLI/forward.py', doraise=True)" && echo "OK"
```

Expected: `OK`

- [ ] **Step 3: 提交**

```bash
git add forward.py
git commit -m "feat(log): add set_log_path for file-based logging"
```

---

### Task 2: tray.py — 启动时传递日志路径

**Files:**
- Modify: `tray.py:350-352`

- [ ] **Step 1: 在 set_forward_config 后调用 set_log_path**

```python
# 设置 forward 模块的配置文件路径（PyInstaller 下与 exe 同目录）
fwd_config_path = os.path.join(base_dir, 'config.json')
set_forward_config(fwd_config_path)

# 设置 forward 模块的日志文件路径
forward_mod.set_log_path(os.path.join(base_dir, 'forward.log'))
```

注意：将 LOG_FILE 的路径改为基于 `base_dir`（与 config.json 同目录），而不是 `SCRIPT_DIR`。这样在 PyInstaller 打包后，日志文件在 exe 同级目录，与用户期望一致。

- [ ] **Step 2: 提交**

```bash
git add tray.py
git commit -m "feat(tray): pass log file path to forward module"
```

---

### Task 3: tray.py — 日志控件添加滚动条 + 智能滚动

**Files:**
- Modify: `tray.py:154-173`

- [ ] **Step 1: 重写日志控件区域**

将原来的单个 Text 控件替换为 Frame + Text + Scrollbar 结构，并在刷新时检查用户是否在底部：

```python
ttk.Label(frame, text='最近日志', font=('微软雅黑', 11, 'bold')).pack(
    anchor='w', pady=(0, 5))

log_frame = ttk.Frame(frame)
log_frame.pack(fill='both', expand=True)

log_text = tk.Text(log_frame, height=10, wrap='word', state='disabled',
                   font=('Consolas', 9))
log_scrollbar = ttk.Scrollbar(log_frame, orient='vertical',
                              command=log_text.yview)
log_text.config(yscrollcommand=log_scrollbar.set)

log_text.grid(row=0, column=0, sticky='nsew')
log_scrollbar.grid(row=0, column=1, sticky='ns')
log_frame.grid_rowconfigure(0, weight=1)
log_frame.grid_columnconfigure(0, weight=1)

def load_logs():
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()[-30:]
            is_at_bottom = log_text.yview()[1] >= 1.0
            log_text.config(state='normal')
            log_text.delete('1.0', 'end')
            log_text.insert('1.0', ''.join(lines))
            if is_at_bottom:
                log_text.see('end')
            log_text.config(state='disabled')
        except Exception:
            pass
    frame.after(5000, load_logs)

load_logs()
```

- [ ] **Step 2: 提交**

```bash
git add tray.py
git commit -m "feat(tray): add scrollbar and smart auto-scroll to log panel"
```

---

### Task 4: 编写单元测试

**Files:**
- Create: `tests/test_log_setup.py`

- [ ] **Step 1: 写测试文件**

```python
import os
import tempfile
import logging
import importlib


def test_set_log_path_writes_to_file():
    """测试 set_log_path 配置 FileHandler 后日志写入文件"""
    import forward as forward_mod

    with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False,
                                      encoding='utf-8') as tmp:
        tmp_path = tmp.name

    try:
        forward_mod.set_log_path(tmp_path)
        forward_mod.logger.info('测试消息: 中文和emoji ✅')

        with open(tmp_path, 'r', encoding='utf-8') as f:
            content = f.read()
        assert '测试消息' in content
        assert '中文和emoji' in content
    finally:
        os.unlink(tmp_path)


def test_set_log_path_does_not_crash_without_stderr(monkeypatch):
    """测试 stderr 为 None 时 set_log_path 仍可正常工作"""
    import forward as forward_mod

    with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False,
                                      encoding='utf-8') as tmp:
        tmp_path = tmp.name

    try:
        forward_mod.set_log_path(tmp_path)
        # 在无 stderr 情况下记录日志不应抛异常
        forward_mod.logger.info('test message')
        forward_mod.logger.error('error message')

        with open(tmp_path, 'r', encoding='utf-8') as f:
            content = f.read()
        assert 'test message' in content
        assert 'error message' in content
    finally:
        os.unlink(tmp_path)
```

- [ ] **Step 2: 运行测试确认通过**

```bash
pytest tests/test_log_setup.py -v
```

Expected: 2 passed

- [ ] **Step 3: 提交**

```bash
git add tests/test_log_setup.py
git commit -m "test(log): add tests for set_log_path FileHandler"
```

---

### Task 5: 手动集成验证

- [ ] **Step 1: 启动应用**

```bash
python tray.py
```

- [ ] **Step 2: 验证日志文件写入**

1. 在 QQ 群发送一条测试消息
2. 检查 `forward.log` 是否有新日志行

```bash
tail -3 forward.log
```

Expected: 看到新出现的日志行（如 "✅ 转发成功" 等）

- [ ] **Step 3: 验证日志面板滚动**

1. 打开托盘主面板，切换到状态标签页
2. 确认日志区域右侧有滚动条
3. 用鼠标滚轮上下滚动，确认可查看历史日志
4. 发送新消息，确认日志自动滚动到底部显示新内容
5. 手动滚动到中间位置，等待 5 秒，确认不会被打断（保持当前位置）
