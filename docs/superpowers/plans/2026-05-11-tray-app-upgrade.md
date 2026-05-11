# 托盘应用升级为桌面应用 — 实现计划

> **For agentic workers:** 使用 superpowers:subagent-driven-development 或 superpowers:executing-plans 按任务逐步实现。步骤使用 checkbox (`- [ ]`) 语法追踪进度。

**目标:** 将 tray.py 从"右键菜单弹窗工具"升级为左键可打开选项卡主面板的正经桌面应用。

**架构:** pystray 通过 `run_detached()` 在 daemon 线程运行，主线程跑 tkinter `root.mainloop()`。左键点击通过 ctypes hook pystray 隐藏窗口的 `WM_LBUTTONUP` 实现。主面板使用 `ttk.Notebook` 整合状态页和设置页，X 按钮通过 `WM_DELETE_WINDOW` 协议改为隐藏而非退出。

**技术栈:** Python 3, tkinter + ttk, pystray, PIL/Pillow, ctypes (win32)

---

### Task 1: 重写托盘图标（PIL 绘制聊天气泡）

**文件:**
- Modify: `tray.py:69-79` (replace `create_icon_image`)

- [ ] **Step 1: 用聊天气泡+箭头图形替换纯色圆点**

编辑 `tray.py`，替换 `create_icon_image` 函数：

```python
def create_icon_image(color: str = 'green'):
    """创建托盘图标（聊天气泡+转发箭头，64x64）"""
    img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    colors = {
        'green': (76, 175, 80, 255),
        'red': (244, 67, 54, 255),
        'yellow': (255, 193, 7, 255),
    }
    c = colors.get(color, colors['green'])
    dark = tuple(max(0, x - 60) for x in c[:3]) + (255,)

    # 聊天气泡主体（圆角矩形）
    draw.rounded_rectangle([4, 10, 56, 48], radius=10, fill=c)
    # 气泡尾巴（右下小三角）
    draw.polygon([(44, 46), (54, 46), (44, 58)], fill=c)
    # 双箭头图标
    draw.polygon([(18, 22), (26, 29), (18, 36)], fill=dark)
    draw.polygon([(28, 22), (36, 29), (28, 36)], fill=dark)

    return img
```

- [ ] **Step 2: 验证图标可生成**

```bash
python -c "from tray import create_icon_image; img=create_icon_image('green'); img.show()"
```

- [ ] **Step 3: Commit**

```bash
git add tray.py
git commit -m "feat(tray): replace solid circle icon with chat-bubble design"
```

---

### Task 2: 重构 settings.py 为可嵌入 Frame

**文件:**
- Modify: `settings.py` (重构 `open_settings` → `create_settings_frame`)

`open_settings()` 当前自建 `tk.Tk()` 并调用 `mainloop()`，无法嵌入 Notebook。需要拆为返回 Frame 的工厂函数。

- [ ] **Step 1: 读当前 settings.py 确认完整内容**

```bash
cat -n settings.py
```

- [ ] **Step 2: 重构 settings.py**

将 `open_settings()` 替换为 `create_settings_frame(parent)`，去掉 `tk.Tk()` 和 `mainloop()`：

```python
"""QQ消息转发 — 设置界面（可嵌入 Frame）"""
import json
import os
import tkinter as tk
from tkinter import ttk

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, 'config.json')


def load_config():
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_config(data):
    tmp = CONFIG_PATH + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, CONFIG_PATH)


def create_settings_frame(parent):
    """创建设置界面 Frame，可嵌入 Notebook 等容器"""
    cfg = load_config()
    frame = ttk.Frame(parent, padding=10)

    pad = {'padx': 10, 'pady': 5}

    # ===== 转发规则 =====
    frm_rules = ttk.LabelFrame(frame, text='转发规则', padding=10)
    frm_rules.pack(fill='x', **pad)

    rules = cfg.get('forward_rules', {})
    cfg.setdefault('filter', {}).setdefault('qrcode', {})
    cfg.setdefault('filter', {}).setdefault('contact', {})

    ttk.Label(frm_rules, text='源群').grid(row=0, column=0, sticky='w')
    src_entry = ttk.Entry(frm_rules, width=20)
    src_entry.grid(row=0, column=1, **pad)

    ttk.Label(frm_rules, text='目标群（逗号分隔）').grid(row=1, column=0, sticky='w')
    dst_entry = ttk.Entry(frm_rules, width=50)
    dst_entry.grid(row=1, column=1, **pad)

    rules_list = tk.Listbox(frm_rules, height=4, width=60)
    rules_list.grid(row=2, column=0, columnspan=2, **pad)

    def refresh_rules_list():
        rules_list.delete(0, 'end')
        for src, dsts in rules.items():
            rules_list.insert('end', f'{src} → {", ".join(dsts)}')

    def on_add_rule():
        src = src_entry.get().strip()
        dsts = [d.strip() for d in dst_entry.get().split(',') if d.strip()]
        if src and dsts:
            rules[src] = dsts
            refresh_rules_list()
            src_entry.delete(0, 'end')
            dst_entry.delete(0, 'end')

    def on_del_rule():
        sel = rules_list.curselection()
        if sel:
            text = rules_list.get(sel[0])
            src = text.split(' → ')[0]
            if src in rules:
                del rules[src]
            refresh_rules_list()

    def on_list_select(event):
        sel = rules_list.curselection()
        if sel:
            text = rules_list.get(sel[0])
            src, dsts_str = text.split(' → ', 1)
            src_entry.delete(0, 'end')
            src_entry.insert(0, src)
            dst_entry.delete(0, 'end')
            dst_entry.insert(0, ', '.join(rules.get(src, [])))

    rules_list.bind('<<ListboxSelect>>', on_list_select)

    btn_frm = ttk.Frame(frm_rules)
    btn_frm.grid(row=3, column=0, columnspan=2, pady=5)
    ttk.Button(btn_frm, text='＋ 添加/更新', command=on_add_rule).pack(side='left', padx=2)
    ttk.Button(btn_frm, text='－ 删除', command=on_del_rule).pack(side='left', padx=2)

    refresh_rules_list()

    # ===== QR 码过滤 =====
    qr = cfg['filter']['qrcode']
    frm_qr = ttk.LabelFrame(frame, text='QR码过滤', padding=10)
    frm_qr.pack(fill='x', **pad)

    qr_enabled = tk.BooleanVar(value=qr.get('enabled', True))
    ttk.Checkbutton(frm_qr, text='启用', variable=qr_enabled).pack(anchor='w')

    ttk.Label(frm_qr, text='关键词（逗号分隔）').pack(anchor='w')
    qr_kw_entry = ttk.Entry(frm_qr, width=60)
    qr_kw_entry.pack(fill='x', **pad)
    qr_kw_entry.insert(0, ', '.join(qr.get('keywords', [])))

    qr_block = tk.BooleanVar(value=qr.get('block_pure_image', False))
    ttk.Checkbutton(frm_qr, text='拦截无文字的纯图片', variable=qr_block).pack(anchor='w')

    # ===== 联系方式过滤 =====
    ct = cfg['filter']['contact']
    frm_ct = ttk.LabelFrame(frame, text='联系方式过滤', padding=10)
    frm_ct.pack(fill='x', **pad)

    ct_enabled = tk.BooleanVar(value=ct.get('enabled', True))
    ttk.Checkbutton(frm_ct, text='启用', variable=ct_enabled).pack(anchor='w')

    ttk.Label(frm_ct, text='关键词（逗号分隔）').pack(anchor='w')
    ct_kw_entry = ttk.Entry(frm_ct, width=60)
    ct_kw_entry.pack(fill='x', **pad)
    ct_kw_entry.insert(0, ', '.join(ct.get('keywords', [])))

    log_only = tk.BooleanVar(value=cfg['filter'].get('log_only', False))
    ttk.Checkbutton(frm_ct, text='仅记录不拦截（log_only）', variable=log_only).pack(anchor='w')

    # ===== 状态标签 =====
    status_var = tk.StringVar(value='')

    # ===== 按钮 =====
    btn_frame = ttk.Frame(frame)
    btn_frame.pack(fill='x', **pad)

    def on_save():
        cfg['forward_rules'] = rules
        cfg['filter']['qrcode']['enabled'] = qr_enabled.get()
        cfg['filter']['qrcode']['keywords'] = [
            k.strip() for k in qr_kw_entry.get().split(',') if k.strip()
        ]
        cfg['filter']['qrcode']['block_pure_image'] = qr_block.get()
        cfg['filter']['contact']['enabled'] = ct_enabled.get()
        cfg['filter']['contact']['keywords'] = [
            k.strip() for k in ct_kw_entry.get().split(',') if k.strip()
        ]
        cfg['filter']['log_only'] = log_only.get()
        try:
            save_config(cfg)
            status_var.set('配置已保存，重启服务后生效。')
        except Exception as e:
            status_var.set(f'保存失败: {e}')

    ttk.Button(btn_frame, text='保存', command=on_save).pack(side='right', padx=5)
    ttk.Label(btn_frame, textvariable=status_var, foreground='gray').pack(side='right', padx=10)

    return frame


# 保持向后兼容：直接运行时弹出独立窗口
if __name__ == '__main__':
    root = tk.Tk()
    root.title('QQ消息转发 - 设置')
    root.resizable(False, False)
    create_settings_frame(root).pack(fill='both', expand=True)
    root.mainloop()
```

- [ ] **Step 3: 测试独立运行 settings.py**

```bash
python settings.py
```

确认窗口正常显示，保存按钮工作。

- [ ] **Step 4: Commit**

```bash
git add settings.py
git commit -m "refactor(settings): extract create_settings_frame for embedding"
```

---

### Task 3: 创建主面板窗口（Notebook + 状态Tab）

**文件:**
- Modify: `tray.py` (新增 `create_status_tab`, `create_main_window`, `show_main_window`, `hide_main_window`)

- [ ] **Step 1: 在 tray.py 顶部添加 tkinter import**

在现有 import 区域添加：

```python
import tkinter as tk
from tkinter import ttk
import ctypes
from ctypes import wintypes
```

- [ ] **Step 2: 添加 `create_status_tab(parent)` 函数**

在 `create_icon_image` 函数之后添加：

```python
def create_status_tab(parent):
    """创建状态选项卡内容"""
    frame = ttk.Frame(parent, padding=15)

    # 服务状态标题
    ttk.Label(frame, text='服务状态', font=('微软雅黑', 11, 'bold')).pack(
        anchor='w', pady=(0, 10))

    status_frm = ttk.Frame(frame)
    status_frm.pack(fill='x')

    ttk.Label(status_frm, text='LLBot (端口 3000):', width=20, anchor='w').grid(
        row=0, column=0, sticky='w', pady=3)
    llbot_status = ttk.Label(status_frm, text='检测中...', foreground='gray')
    llbot_status.grid(row=0, column=1, sticky='w', pady=3)

    ttk.Label(status_frm, text='转发脚本 (端口 8080):', width=20, anchor='w').grid(
        row=1, column=0, sticky='w', pady=3)
    forward_status = ttk.Label(status_frm, text='检测中...', foreground='gray')
    forward_status.grid(row=1, column=1, sticky='w', pady=3)

    ttk.Button(frame, text='刷新', command=lambda: refresh()).pack(
        anchor='w', pady=(5, 10))

    def refresh():
        llbot_ok, forward_ok = get_status()
        llbot_status.config(
            text='运行中' if llbot_ok else '已停止',
            foreground='green' if llbot_ok else 'red')
        forward_status.config(
            text='运行中' if forward_ok else '已停止',
            foreground='green' if forward_ok else 'red')

    # 初始刷新
    refresh()

    # 分隔线
    ttk.Separator(frame, orient='horizontal').pack(fill='x', pady=10)

    # 日志区域
    ttk.Label(frame, text='最近日志', font=('微软雅黑', 11, 'bold')).pack(
        anchor='w', pady=(0, 5))

    log_text = tk.Text(frame, height=10, wrap='word', state='disabled',
                       font=('Consolas', 9))
    log_text.pack(fill='both', expand=True)

    def load_logs():
        if os.path.exists(LOG_FILE):
            try:
                with open(LOG_FILE, 'r', encoding='utf-8', errors='replace') as f:
                    lines = f.readlines()[-30:]
                log_text.config(state='normal')
                log_text.delete('1.0', 'end')
                log_text.insert('1.0', ''.join(lines))
                log_text.see('end')
                log_text.config(state='disabled')
            except Exception:
                pass
        frame.after(5000, load_logs)

    load_logs()

    # 自动刷新状态（3 秒）
    def auto_refresh():
        refresh()
        frame.after(3000, auto_refresh)

    auto_refresh()

    return frame
```

- [ ] **Step 3: 添加主面板创建和显示/隐藏函数**

```python
def show_main_window(root):
    """显示主面板"""
    root.deiconify()
    root.lift()
    root.focus_force()


def hide_main_window(root):
    """隐藏主面板（不退出）"""
    root.withdraw()
```

- [ ] **Step 4: Commit**

```bash
git add tray.py
git commit -m "feat(tray): add status tab and main panel window functions"
```

---

### Task 4: 线程模型 + 托盘 setup 重构

**文件:**
- Modify: `tray.py` (重写 `setup_tray` 和 `__main__` 块)

- [ ] **Step 1: 重写 `setup_tray` 函数使用 `run_detached`**

替换现有 `setup_tray` 函数：

```python
def setup_tray(root, on_open):
    """创建托盘图标（在 daemon 线程中运行 pystray）"""
    icon = pystray.Icon(
        'qq_forward',
        create_icon_image('green'),
        'QQ消息转发 - 运行中',
        menu=pystray.Menu(
            pystray.MenuItem('打开主面板', lambda: root.after(0, lambda: on_open(root))),
            pystray.MenuItem('关闭服务', lambda: handle_shutdown(icon, root)),
        )
    )

    # 启动监控线程
    monitor = threading.Thread(target=monitor_loop, args=(icon, root), daemon=True)
    monitor.start()

    # 在 daemon 线程中运行 pystray 事件循环
    tray_thread = threading.Thread(target=icon.run, daemon=True)
    tray_thread.start()

    return icon
```

- [ ] **Step 2: 重写 `__main__` 块，创建 tk root 并运行 mainloop**

替换 `if __name__ == '__main__':` 以下的全部内容：

```python
if __name__ == '__main__':
    # 检查 LLBot 是否运行
    if not check_port(LLBOT_PORT):
        print(f'错误: LLBot 未运行（端口 {LLBOT_PORT} 不通），请先启动 LLBot')
        sys.exit(1)

    # 启动转发脚本
    start_forward()
    for _ in range(10):
        if check_port(FORWARD_PORT):
            break
        time.sleep(1)

    if not check_port(FORWARD_PORT):
        print('警告: 转发脚本可能未启动成功（端口 8080 不通）')

    # 创建 tk 主窗口
    root = tk.Tk()
    root.title('QQ消息转发')
    root.geometry('520x500')
    root.resizable(True, True)

    # 窗口关闭 = 隐藏到托盘
    root.protocol('WM_DELETE_WINDOW', lambda: hide_main_window(root))

    # Notebook 选项卡
    notebook = ttk.Notebook(root, padding=5)
    notebook.pack(fill='both', expand=True, padx=5, pady=5)

    # 状态选项卡
    notebook.add(create_status_tab(notebook), text='状态')

    # 设置选项卡
    notebook.add(settings_mod.create_settings_frame(notebook), text='设置')

    # 底部按钮栏
    bottom = ttk.Frame(root, padding=5)
    bottom.pack(fill='x', side='bottom')
    ttk.Button(bottom, text='隐藏到托盘',
               command=lambda: hide_main_window(root)).pack(side='right', padx=5)

    # 启动时隐藏
    root.withdraw()

    # 启动托盘
    icon = setup_tray(root, show_main_window)

    # 桌面快捷方式（首次运行自动创建）
    create_desktop_shortcut()

    # 主线程运行 tkinter
    root.mainloop()
```

> 注意：import 区域需要 `import settings as settings_mod`

- [ ] **Step 3: 确认 tray.py 顶部 import 完整**

应为：

```python
"""QQ消息转发 — 系统托盘管理程序"""
import subprocess
import sys
import os
import time
import threading
import socket
import ctypes
from ctypes import wintypes
import tkinter as tk
from tkinter import ttk

import pystray
from PIL import Image, ImageDraw

import settings as settings_mod
```

- [ ] **Step 4: Commit**

```bash
git add tray.py
git commit -m "feat(tray): switch to run_detached thread model with tk mainloop"
```

---

### Task 5: 左键点击 Hook

**文件:**
- Modify: `tray.py` (新增 `_find_tray_hwnd`, `_hook_left_click`, 在 `setup_tray` 中调用)

- [ ] **Step 1: 添加 Win32 常量和辅助函数**

在 `create_icon_image` 之后添加：

```python
# Win32 constants
GWLP_WNDPROC = -4
WM_LBUTTONUP = 0x0202

# 保存原始窗口过程指针，用于链式调用
_original_wndproc = None
_hook_root = None
_hook_callback = None

# ctypes 函数指针类型
WNDPROC_TYPE = ctypes.WINFUNCTYPE(ctypes.c_longlong, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)


def _find_tray_hwnd():
    """枚举当前进程的所有隐藏窗口，找到 pystray 的消息窗口 HWND"""
    user32 = ctypes.windll.user32
    hwnd_found = []

    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    @WNDENUMPROC
    def enum_proc(hwnd, lparam):
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value != os.getpid():
            return True
        if user32.IsWindowVisible(hwnd):
            return True
        class_name = ctypes.create_unicode_buffer(64)
        user32.GetClassNameW(hwnd, class_name, 64)
        cn = class_name.value
        if cn and ('ystray' in cn or 'TrayIcon' in cn):
            hwnd_found.append(hwnd)
            return False
        return True

    user32.EnumWindows(enum_proc, 0)
    return hwnd_found[0] if hwnd_found else None


def _hook_left_click(root, on_click):
    """Hook pystray 隐藏窗口的 WM_LBUTTONUP，切回主线程执行 on_click"""
    global _original_wndproc, _hook_root, _hook_callback

    _hook_root = root
    _hook_callback = on_click

    # 等待 pystray 窗口创建
    for _ in range(50):
        hwnd = _find_tray_hwnd()
        if hwnd:
            break
        time.sleep(0.1)
    else:
        return  # 没找到就不 hook，右键菜单仍可用

    user32 = ctypes.windll.user32

    @WNDPROC_TYPE
    def new_wndproc(hwnd, msg, wparam, lparam):
        if msg == WM_LBUTTONUP:
            _hook_root.after(0, _hook_callback, _hook_root)
        return user32.CallWindowProcW(_original_wndproc, hwnd, msg, wparam, lparam)

    _original_wndproc = user32.SetWindowLongPtrW(hwnd, GWLP_WNDPROC, new_wndproc)

    # 防止 new_wndproc 被 Python GC 回收
    import gc
    gc.disable()
```

- [ ] **Step 2: 在 `setup_tray` 中调用 hook**

修改 `setup_tray` 函数，在 `tray_thread.start()` 之后添加：

```python
def setup_tray(root, on_open):
    """创建托盘图标（在 daemon 线程中运行 pystray）"""
    icon = pystray.Icon(
        'qq_forward',
        create_icon_image('green'),
        'QQ消息转发 - 运行中',
        menu=pystray.Menu(
            pystray.MenuItem('打开主面板', lambda: root.after(0, lambda: on_open(root))),
            pystray.MenuItem('关闭服务', lambda: handle_shutdown(icon, root)),
        )
    )

    monitor = threading.Thread(target=monitor_loop, args=(icon, root), daemon=True)
    monitor.start()

    tray_thread = threading.Thread(target=icon.run, daemon=True)
    tray_thread.start()

    # 延迟 hook 左键点击（等 pystray 窗口创建）
    root.after(500, lambda: _hook_left_click(root, on_open))

    return icon
```

- [ ] **Step 3: Commit**

```bash
git add tray.py
git commit -m "feat(tray): add left-click hook via ctypes win32 subclassing"
```

---

### Task 6: 关闭服务统一（标志文件 + 优雅退出）

**文件:**
- Modify: `tray.py` (新增 `handle_shutdown`, 修改 `shutdown_service` 清理流程)

- [ ] **Step 1: 添加 `handle_shutdown` 和更新 `shutdown_service`**

替换现有的 `shutdown_service` 函数，并新增 `handle_shutdown`：

```python
def shutdown_service(icon):
    """执行服务关闭（终止子进程、清理残留进程）"""
    global running
    running = False

    # 先终止转发脚本（graceful）
    stop_forward()

    # 清理残留进程
    for proc in ['node.exe', 'llbot.exe', 'python.exe', 'pythonw.exe']:
        subprocess.run(['taskkill', '/f', '/im', proc], capture_output=True)

    # 关闭 QQ
    for qq_name in ['QQ.exe', 'QQNT.exe']:
        subprocess.run(['taskkill', '/f', '/im', qq_name], capture_output=True)

    # 清理标志文件
    if os.path.exists(SHUTDOWN_FLAG):
        try:
            os.remove(SHUTDOWN_FLAG)
        except OSError:
            pass

    icon.stop()


def handle_shutdown(icon, root):
    """用户点击"关闭服务"：创建标志文件 → 立即关闭 → 销毁窗口"""
    with open(SHUTDOWN_FLAG, 'w') as f:
        f.write('shutdown')
    shutdown_service(icon)
    root.destroy()
```

- [ ] **Step 2: 更新 `monitor_loop` 添加黄色状态和 stop.vbs 兼容**

替换现有 `monitor_loop` 函数：

```python
def monitor_loop(icon, root):
    """监控线程：每 5 秒检查服务状态 + 检测 shutdown 标志文件"""
    was_ok = True
    while running:
        time.sleep(5)
        if not running:
            break

        # 检测 stop.vbs 创建的关闭标志
        if os.path.exists(SHUTDOWN_FLAG):
            root.after(0, lambda: handle_shutdown(icon, root))
            break

        llbot_ok, forward_ok = get_status()
        all_ok = llbot_ok and forward_ok
        any_ok = llbot_ok or forward_ok

        if not any_ok:
            icon.icon = create_icon_image('red')
            icon.title = 'QQ消息转发 - 服务异常'
        elif not all_ok:
            icon.icon = create_icon_image('yellow')
            icon.title = 'QQ消息转发 - 部分异常'
        elif all_ok and not was_ok:
            icon.icon = create_icon_image('green')
            icon.title = 'QQ消息转发 - 运行中'

        was_ok = all_ok
```

- [ ] **Step 3: Commit**

```bash
git add tray.py
git commit -m "feat(tray): unify shutdown with flag-file + graceful exit"
```

---

### Task 7: 桌面快捷方式自动创建

**文件:**
- Modify: `tray.py` (新增 `create_desktop_shortcut`)

- [ ] **Step 1: 添加快捷方式创建函数**

在 `__main__` 块之前添加：

```python
def create_desktop_shortcut():
    """首次运行时在桌面创建指向 start.vbs 的快捷方式"""
    try:
        # 获取桌面路径
        import pythoncom
        from win32com.client import Dispatch
    except ImportError:
        return

    try:
        pythoncom.CoInitialize()
        desktop = os.path.join(os.environ['USERPROFILE'], 'Desktop')
        lnk_path = os.path.join(desktop, 'QQ转发.lnk')

        if os.path.exists(lnk_path):
            return

        start_vbs = os.path.join(SCRIPT_DIR, 'start.vbs')
        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortcut(lnk_path)
        shortcut.TargetPath = start_vbs
        shortcut.WorkingDirectory = SCRIPT_DIR
        shortcut.IconLocation = start_vbs + ',0'
        shortcut.Description = 'QQ消息转发 — 一键启动'
        shortcut.Save()
    except Exception:
        pass  # 静默失败，不影响主流程
```

> 注意：此方案需要 `pywin32`。如果用户环境没有，将改用 VBS 备选方案。

- [ ] **Step 2: 如果 pywin32 不可用，改用纯 VBS 方案**

```python
def create_desktop_shortcut():
    """首次运行时在桌面创建指向 start.vbs 的快捷方式（纯 VBS 实现）"""
    try:
        desktop = os.path.join(os.environ['USERPROFILE'], 'Desktop')
        lnk_path = os.path.join(desktop, 'QQ转发.lnk')

        if os.path.exists(lnk_path):
            return

        start_vbs = os.path.join(SCRIPT_DIR, 'start.vbs')
        vbs_code = f'''
Set ws = CreateObject("WScript.Shell")
Set sc = ws.CreateShortcut("{lnk_path}")
sc.TargetPath = "{start_vbs}"
sc.WorkingDirectory = "{SCRIPT_DIR}"
sc.Description = "QQ消息转发 — 一键启动"
sc.Save()
'''
        subprocess.run(['cscript', '//Nologo', '//B'],
                       input=vbs_code.encode('utf-8'),
                       capture_output=True)
    except Exception:
        pass
```

修正：cscript 不能用 stdin 传入脚本。改用临时文件：

```python
def create_desktop_shortcut():
    """首次运行时在桌面创建指向 start.vbs 的快捷方式"""
    try:
        desktop = os.path.join(os.environ['USERPROFILE'], 'Desktop')
        lnk_path = os.path.join(desktop, 'QQ转发.lnk')

        if os.path.exists(lnk_path):
            return

        start_vbs = os.path.join(SCRIPT_DIR, 'start.vbs')
        tmp_vbs = os.path.join(SCRIPT_DIR, '.create_shortcut.vbs')

        vbs_code = (
            f'Set ws = CreateObject("WScript.Shell")\r\n'
            f'Set sc = ws.CreateShortcut("{lnk_path}")\r\n'
            f'sc.TargetPath = "{start_vbs}"\r\n'
            f'sc.WorkingDirectory = "{SCRIPT_DIR}"\r\n'
            f'sc.Description = "QQ消息转发 - 一键启动"\r\n'
            f'sc.Save()\r\n'
        )

        with open(tmp_vbs, 'w') as f:
            f.write(vbs_code)

        subprocess.run(['cscript', '//Nologo', '//B', tmp_vbs],
                       capture_output=True, timeout=5)

        try:
            os.remove(tmp_vbs)
        except OSError:
            pass
    except Exception:
        pass
```

- [ ] **Step 3: Commit**

```bash
git add tray.py
git commit -m "feat(tray): auto-create desktop shortcut on first run"
```

---

### Task 8: 集成测试和最终验证

**文件:**
- No files modified (verification only)

- [ ] **Step 1: 语法检查**

```bash
python -c "import py_compile; py_compile.compile('tray.py', doraise=True); print('tray.py OK')"
python -c "import py_compile; py_compile.compile('settings.py', doraise=True); print('settings.py OK')"
```

- [ ] **Step 2: 验证 settings.py 向后兼容（独立运行模式）**

```bash
python settings.py
# 窗口应正常显示，保存按钮可点击
```

- [ ] **Step 3: 图标生成验证**

```bash
python -c "from tray import create_icon_image; img=create_icon_image('green'); img.save('/tmp/test_icon.png'); print(f'Size: {img.size}')"
```

- [ ] **Step 4: 模块导入验证**

```bash
python -c "import tray; print('All imports OK'); print('Functions:', [x for x in dir(tray) if not x.startswith('_')])"
```

- [ ] **Step 5: 端到端测试（需要 LLBot 运行）**

```bash
python tray.py
```

手动检查：
- [ ] 托盘出现聊天气泡绿色图标
- [ ] 左键点击 → 主面板打开，显示状态和设置两个选项卡
- [ ] 状态选项卡显示端口状态（绿色运行中）
- [ ] 切换到设置选项卡，可见转发规则、过滤配置
- [ ] 点 X 按钮 → 窗口隐藏，托盘图标仍在
- [ ] 左键再次点击 → 窗口恢复
- [ ] 右键菜单 → 只有"打开主面板"和"关闭服务"
- [ ] 点击"关闭服务" → 服务终止，窗口销毁，托盘图标消失
- [ ] 桌面出现 `QQ转发.lnk` 快捷方式

- [ ] **Step 6: 验证 stop.vbs 兼容性**

```bash
# 启动服务后，双击 stop.vbs，确认托盘程序正常退出
```

- [ ] **Step 7: Commit**

```bash
git add tray.py settings.py
git commit -m "chore(tray): final integration verification and cleanup"
```

---

## 备选方案和回退

| 风险 | 回退方案 |
|------|----------|
| 左键 hook 找不到 pystray 窗口 | 类名匹配失败时，回退枚举所有本进程隐藏窗口、取第一个不可见窗口；右键"打开主面板"始终可用 |
| `rounded_rectangle` 在旧 PIL 不可用 | 用 `draw.rectangle` + 四角 `draw.pieslice` 手动画圆角矩形 |
| pywin32 未安装（快捷方式创建） | 使用纯 VBS 临时文件方案（Task 7 Step 2） |
| `run_detached()` 行为异常 | 回退用 `threading.Thread(target=icon.run)` |

---

## Post-Implementation

完成后：
1. 更新 `使用教程.txt` 说明新的托盘交互方式
2. 运行 `openspec verify --change tray-app-upgrade` 验证实现与 spec 一致
