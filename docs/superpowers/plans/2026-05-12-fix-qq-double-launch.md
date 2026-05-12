# Fix QQ Double Launch Bug Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix `tray.py` unconditionally starting `llbot.exe` when it's already running (started by `start.vbs`), which causes QQ to launch twice.

**Architecture:** Add a port check guard in `tray.py` before launching `llbot.exe`. If port 3000 is already open (meaning `start.vbs` already started it), skip the launch. The `check_port()` function already exists at `tray.py:81`.

**Tech Stack:** Python 3, subprocess, socket

---

### Task 1: Guard llbot.exe launch with port check

**Files:**
- Modify: `tray.py:411-418`

- [ ] **Step 1: Add `not check_port(LLBOT_PORT)` guard to the launch condition**

Change `tray.py` line 413 from:

```python
        if os.path.exists(llbot_exe):
```

To:

```python
        if os.path.exists(llbot_exe) and not check_port(LLBOT_PORT):
```

The full block after change:

```python
    # 启动 LLBot（后台隐藏窗口）—— 如果已在运行则跳过
    llbot_exe = os.path.join(llbot_dir, 'llbot.exe')
    if os.path.exists(llbot_exe) and not check_port(LLBOT_PORT):
        subprocess.Popen(
            [llbot_exe],
            cwd=llbot_dir,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0,
        )
    elif not os.path.exists(llbot_exe):
        from tkinter import messagebox
        root_tmp = tk.Tk()
        root_tmp.withdraw()
        messagebox.showerror(
            '组件缺失',
            f'未找到 LLBot 程序:\n{llbot_exe}\n\n'
            '请确认安装包已完整解压。'
        )
        root_tmp.destroy()
        sys.exit(1)
```

**Why `elif` for the else branch:** The original `else` branch only fires when `llbot.exe` doesn't exist. With the new guard, when port is already open, we should not error — we should simply skip the launch and continue. The `elif` preserves the original error behavior (only error when exe truly missing) while the new "port already open" case falls through silently.

- [ ] **Step 2: Verify syntax**

Run: `python -m py_compile tray.py`
Expected: No output (compiles cleanly)

- [ ] **Step 3: Commit**

```bash
git add tray.py
git commit -m "fix(tray): prevent duplicate llbot.exe launch when already running

Check port 3000 before launching llbot.exe. When start.vbs has already
started it, tray.py skips the redundant launch, preventing QQ from
being started twice through PMHQ."
```
