# Fix Tray Left-Click, Tab Width, and Log Encoding — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix three bugs: tray left-click not opening main panel, tab headers too narrow, garbled log text in status tab.

**Architecture:** Three independent fixes in two files. Left-click fix removes fragile Win32 window subclassing (~40 lines) and uses pystray's `MenuItem(default=True)` API instead. Tab width fix adds a `ttk.Style` configuration. Encoding fix adds `PYTHONUTF8=1` env var to subprocess + `stderr.reconfigure(encoding='utf-8')` in the forward script.

**Tech Stack:** Python 3.14, tkinter/ttk, pystray 0.19.5, ctypes (removed)

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `tray.py` | **Modify** | Remove hook code, add default=True, add ttk style, add PYTHONUTF8 env |
| `qq-message-forward.py` | **Modify** | Add stderr encoding reconfigure |

---

### Task 1: Fix tray left-click — add default=True to menu item

**Files:**
- Modify: `tray.py:324`

- [ ] **Step 1: Add `default=True` to "打开主面板" menu item**

In `setup_tray()`, the `pystray.Menu` currently has two items, neither with `default` set. pystray's `Icon.__call__` invokes the first `MenuItem` with `default=True`. Without it, left-click does nothing.

Edit `tray.py`, change the menu item at line 324:

```python
# Before:
pystray.MenuItem('打开主面板', lambda: root.after(0, lambda: on_open(root))),

# After:
pystray.MenuItem('打开主面板', lambda: root.after(0, lambda: on_open(root)), default=True),
```

- [ ] **Step 2: Commit**

```bash
git add tray.py
git commit -m "fix(tray): add default=True to menu item for left-click open"
```

---

### Task 2: Fix tray left-click — remove Win32 window subclassing code

**Files:**
- Modify: `tray.py:29-41` (remove globals), `86-110` (remove `_find_tray_hwnd`), `113-145` (remove `_hook_left_click`), `336` (remove hook call)

This task removes the broken window subclassing mechanism that was supposed to handle left-clicks but intercepted the wrong message (`WM_LBUTTONUP` instead of `WM_NOTIFY`).

- [ ] **Step 1: Remove Win32 hook constants and globals (lines 29-41)**

Delete these lines:

```python
# Lines 29-41 — REMOVE
GWLP_WNDPROC = -4
WM_LBUTTONUP = 0x0202

_original_wndproc = None
_wndproc_ref = None
_hook_root = None
_hook_callback = None

WNDPROC_TYPE = ctypes.WINFUNCTYPE(
    ctypes.c_longlong, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM
)
```

- [ ] **Step 2: Remove the `ctypes` and `wintypes` imports if no longer needed**

After removing the hook code, check if `ctypes` and `wintypes` are still used elsewhere. They are not — remove the import lines:

```python
# Lines 16-17 — REMOVE
import ctypes
from ctypes import wintypes
```

- [ ] **Step 3: Remove `_find_tray_hwnd()` function (lines 86-110)**

Delete the entire function:

```python
# Lines 86-110 — REMOVE
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
```

- [ ] **Step 4: Remove `_hook_left_click()` function (lines 113-145)**

Delete the entire function:

```python
# Lines 113-145 — REMOVE
def _hook_left_click(root, on_click):
    """Hook pystray 隐藏窗口的 WM_LBUTTONUP，切回主线程执行 on_click"""
    global _original_wndproc, _hook_root, _hook_callback, _wndproc_ref

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

    # 修复 64 位指针截断问题
    user32.SetWindowLongPtrW.restype = wintypes.LONG_PTR
    user32.SetWindowLongPtrW.argtypes = (wintypes.HWND, ctypes.c_int, WNDPROC_TYPE)
    user32.CallWindowProcW.restype = wintypes.LPARAM

    @WNDPROC_TYPE
    def new_wndproc(hwnd, msg, wparam, lparam):
        if msg == WM_LBUTTONUP:
            _hook_root.after(0, _hook_callback, _hook_root)
        return user32.CallWindowProcW(_original_wndproc, hwnd, msg, wparam, lparam)

    # 保存引用到模块级变量，防止被 Python GC 回收
    _wndproc_ref = new_wndproc

    _original_wndproc = user32.SetWindowLongPtrW(hwnd, GWLP_WNDPROC, new_wndproc)
```

- [ ] **Step 5: Remove hook call in `setup_tray()` (line 336)**

Delete this line in `setup_tray()`:

```python
# Line 336 — REMOVE
    root.after(500, lambda: _hook_left_click(root, on_open))
```

- [ ] **Step 6: Run syntax check to verify no broken references**

```bash
python -c "import py_compile; py_compile.compile('tray.py', doraise=True)"
```

Expected: PASS (no output)

- [ ] **Step 7: Commit**

```bash
git add tray.py
git commit -m "refactor(tray): remove broken Win32 window subclassing for left-click"
```

---

### Task 3: Fix tab header width with ttk.Style

**Files:**
- Modify: `tray.py` — add style configuration before notebook creation (around line 402)

- [ ] **Step 1: Add ttk.Style configuration before notebook creation**

In the `__main__` block, after `root = tk.Tk()` and before `notebook = ttk.Notebook(...)`, add the style configuration. Insert these lines after line 397 (`root.resizable(True, True)`):

```python
    # Tab 标签页内边距
    style = ttk.Style()
    style.configure('TNotebook.Tab', padding=(20, 5))
```

- [ ] **Step 2: Run syntax check**

```bash
python -c "import py_compile; py_compile.compile('tray.py', doraise=True)"
```

Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add tray.py
git commit -m "style(tray): add horizontal padding to notebook tab headers"
```

---

### Task 4: Fix log encoding — add PYTHONUTF8 env var to subprocess

**Files:**
- Modify: `tray.py:58-63` (`start_forward()`)

- [ ] **Step 1: Add `PYTHONUTF8=1` to subprocess environment**

In `start_forward()`, add an environment variable to force the child Python process to use UTF-8 mode. Change lines 58-63:

```python
# Before:
def start_forward():
    """启动转发脚本子进程"""
    global forward_process
    log_fh = open(LOG_FILE, 'a', encoding='utf-8')
    forward_process = subprocess.Popen(
        [sys.executable, FORWARD_SCRIPT],
        stdout=log_fh,
        stderr=subprocess.STDOUT
    )

# After:
def start_forward():
    """启动转发脚本子进程"""
    global forward_process
    env = os.environ.copy()
    env['PYTHONUTF8'] = '1'
    log_fh = open(LOG_FILE, 'a', encoding='utf-8')
    forward_process = subprocess.Popen(
        [sys.executable, FORWARD_SCRIPT],
        stdout=log_fh,
        stderr=subprocess.STDOUT,
        env=env
    )
```

- [ ] **Step 2: Run syntax check**

```bash
python -c "import py_compile; py_compile.compile('tray.py', doraise=True)"
```

Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add tray.py
git commit -m "fix(tray): pass PYTHONUTF8=1 to subprocess for correct log encoding"
```

---

### Task 5: Fix log encoding — add stderr.reconfigure in forward script

**Files:**
- Modify: `qq-message-forward.py` — after imports, before `logging.basicConfig`

- [ ] **Step 1: Add `import sys` and `stderr.reconfigure`**

The forward script doesn't import `sys` yet. Add `sys` to the existing imports and call `reconfigure` before `logging.basicConfig`:

Add `import sys` to line 5:

```python
# Before:
import time
import logging

# After:
import sys
import time
import logging
```

Add `sys.stderr.reconfigure(encoding='utf-8')` after the import block and before `logging.basicConfig` (after line 7, before the old line 27 `logging.basicConfig`):

```python
# 确保 stderr 输出 UTF-8，与日志文件编码一致
sys.stderr.reconfigure(encoding='utf-8')
```

The full change context in the file (lines 1-30):

```python
from flask import Flask, request
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import sys
import time
import logging
import json
import os
from typing import Dict, List

from filter import should_filter

# 加载配置文件
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    config = json.load(f)

# ... config loading ...

# 确保 stderr 输出 UTF-8，与日志文件编码一致
sys.stderr.reconfigure(encoding='utf-8')

# 初始化日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)
```

- [ ] **Step 2: Run syntax check**

```bash
python -c "import py_compile; py_compile.compile('qq-message-forward.py', doraise=True)"
```

Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add qq-message-forward.py
git commit -m "fix(forward): reconfigure stderr to utf-8 for correct log encoding"
```

---

### Task 6: Final verification

- [ ] **Step 1: Verify no remaining references to removed symbols**

```bash
grep -n "hook_left_click\|_find_tray_hwnd\|WNDPROC_TYPE\|_original_wndproc\|_wndproc_ref\|GWLP_WNDPROC\|WM_LBUTTONUP" tray.py
```

Expected: No output (no matches)

- [ ] **Step 2: Verify both files parse without errors**

```bash
python -c "import py_compile; py_compile.compile('tray.py', doraise=True); py_compile.compile('qq-message-forward.py', doraise=True); print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Verify encoding fix with a smoke test**

Write a quick inline test:

```bash
python -c "
import subprocess, sys, os, tempfile

# Create a temp script that logs Chinese + emoji
script = '''
import sys
sys.stderr.reconfigure(encoding='utf-8')
import logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)
logger.info('✅ 转发成功: 测试群 → 目标群 | 你好世界...')
'''

with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
    f.write(script)
    tmp_script = f.name

with tempfile.NamedTemporaryFile(mode='w+', suffix='.log', delete=False, encoding='utf-8') as f:
    log_path = f.name

env = os.environ.copy()
env['PYTHONUTF8'] = '1'
subprocess.run([sys.executable, tmp_script], stdout=open(log_path, 'a', encoding='utf-8'), stderr=subprocess.STDOUT, env=env)

with open(log_path, 'r', encoding='utf-8') as f:
    content = f.read()
    assert '✅' in content, 'Emoji missing!'
    assert '转发成功' in content, 'Chinese missing!'
    assert '你好世界' in content, 'Chinese text missing!'
    print('PASS: All characters present and correct')

os.unlink(tmp_script)
os.unlink(log_path)
"
```

Expected: `PASS: All characters present and correct`

- [ ] **Step 4: Commit any final adjustments and push**

```bash
git status
git log --oneline -5
```
