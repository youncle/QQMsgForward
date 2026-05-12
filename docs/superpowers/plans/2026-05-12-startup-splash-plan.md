# Startup Splash Screen Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在启动过程中显示一个屏幕居中的无边框进度条浮窗，展示启动进度，启动完成后自动关闭。

**Architecture:** 新增 `splash.py` 模块，封装 `SplashScreen` 类（独立 `Tk` 实例）。在 `tray.py` 的 `__main__` 中配置校验通过后创建 splash，各启动阶段调用 `update()` 推进进度，所有服务就绪后 `close()` 销毁 splash 再创建主窗口。

**Tech Stack:** Python 3, tkinter, ttk

---

### Task 1: Create `SplashScreen` class

**Files:**
- Create: `splash.py`

- [ ] **Step 1: Write `splash.py`**

```python
"""启动进度条浮窗"""
import tkinter as tk
from tkinter import ttk


class SplashScreen:
    """无边框启动进度条浮窗，屏幕居中显示"""

    def __init__(self) -> None:
        self._root = tk.Tk()
        self._root.overrideredirect(True)
        self._root.attributes('-topmost', True)
        self._root.configure(bg='#2b2b2b')

        # 窗口尺寸和居中
        win_w, win_h = 400, 120
        scr_w = self._root.winfo_screenwidth()
        scr_h = self._root.winfo_screenheight()
        x = (scr_w - win_w) // 2
        y = (scr_h - win_h) // 2
        self._root.geometry(f'{win_w}x{win_h}+{x}+{y}')

        # 标题
        title = tk.Label(
            self._root,
            text='QQ Forward',
            font=('微软雅黑', 14, 'bold'),
            fg='#ffffff',
            bg='#2b2b2b',
        )
        title.pack(pady=(18, 8))

        # 进度条
        self._bar = ttk.Progressbar(
            self._root,
            mode='determinate',
            length=340,
            maximum=100,
        )
        self._bar.pack(pady=(0, 6))

        # 状态文字
        self._label = tk.Label(
            self._root,
            text='正在准备...',
            font=('微软雅黑', 9),
            fg='#aaaaaa',
            bg='#2b2b2b',
        )
        self._label.pack()

        self._root.update()

    def update(self, percent: float, text: str) -> None:
        """平滑动画更新进度条到目标值"""
        current = self._bar['value']
        target = float(percent)
        step = 0.5 if target > current else -0.5
        while abs(current - target) > abs(step):
            current += step
            self._bar['value'] = current
            self._label.config(text=text)
            self._root.update()
        self._bar['value'] = target
        self._label.config(text=text)
        self._root.update()

    def close(self) -> None:
        """销毁窗口"""
        self._root.destroy()
```

- [ ] **Step 2: 手动验证模块可导入**

```bash
python -c "from splash import SplashScreen; print('OK')"
```
Expected: `OK`

---

### Task 2: Integrate splash into `tray.py` startup

**Files:**
- Modify: `tray.py`

- [ ] **Step 1: 在 `tray.py` `__main__` 块中集成 splash**

在配置校验通过之后、启动 LLBot 之前创建 splash；
在主窗口创建之前关闭 splash。

具体修改 `tray.py` 的 `if __name__ == '__main__':` 块：

在第 425 行（`# 启动 LLBot` 注释）之后插入 splash 创建和第 1 步更新：

```python
    import splash as splash_mod

    splash = splash_mod.SplashScreen()
    splash.update(0, '正在准备环境...')
```

第 2 步——启动 LLBot 阶段（在 `subprocess.Popen([llbot_exe], ...)` 之后，等待端口循环内）：

```python
        # 启动 LLBot（后台隐藏窗口）
        llbot_exe = os.path.join(llbot_dir, 'llbot.exe')
        if os.path.exists(llbot_exe) and not check_port(LLBOT_PORT):
            subprocess.Popen(
                [llbot_exe],
                cwd=llbot_dir,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0,
            )
            splash.update(25, '正在启动 LLBot 服务...')
        elif not os.path.exists(llbot_exe):
            splash.close()
            # ... existing error handling ...

        # 等待 LLBot 端口就绪
        for i in range(20):
            if check_port(LLBOT_PORT):
                splash.update(50, '正在启动 LLBot 服务...')
                break
            time.sleep(1)
            # 进度条在 25-50 之间逐步推进
            splash.update(25 + (i + 1) * 1.25, '正在启动 LLBot 服务...')

        if not check_port(LLBOT_PORT):
            splash.close()
            # ... existing error handling ...
```

第 3 步——启动转发服务阶段（在启动 Flask 线程之后，等待端口循环内）：

```python
        flask_thread = threading.Thread(target=run_flask, daemon=True)
        flask_thread.start()

        splash.update(50, '正在启动转发服务...')

        # 等待转发端口就绪
        for i in range(10):
            if check_port(FORWARD_PORT):
                splash.update(75, '正在启动转发服务...')
                break
            time.sleep(1)
            splash.update(50 + (i + 1) * 2.5, '正在启动转发服务...')
```

第 4 步——加载界面阶段（在创建主窗口之前）：

```python
        splash.update(75, '正在加载界面...')

        # ... existing AppUserModelID, tk 主窗口创建 ...

        splash.update(100, '启动完成')
        splash.close()
```

任何启动失败路径（`sys.exit(1)`）前都要先 `splash.close()`。

- [ ] **Step 2: 手动测试完整启动流程**

```bash
python tray.py
```
验证：splash 浮窗出现在屏幕中央 → 进度条分 4 段推进 → 主窗口出现后 splash 消失。

---

### Task 3: Add unit tests

**Files:**
- Create: `tests/test_splash.py`

- [ ] **Step 1: Write tests**

```python
"""测试启动进度条模块"""
import pytest


def test_splash_create_and_close():
    """splash 创建后应立即显示，close 后窗口销毁"""
    from splash import SplashScreen
    s = SplashScreen()
    assert s._root.winfo_exists()
    s.close()
    # 窗口销毁后 winfo_exists 返回 0
    assert not s._root.winfo_exists()


def test_splash_update_changes_progress():
    """update 应正确设置进度和文字"""
    from splash import SplashScreen
    s = SplashScreen()
    s.update(50, '测试文字')
    assert s._bar['value'] == 50
    assert s._label['text'] == '测试文字'
    s.close()


def test_splash_multiple_updates():
    """连续 update 应能前后推进"""
    from splash import SplashScreen
    s = SplashScreen()
    s.update(25, '步骤1')
    s.update(75, '步骤3')
    assert s._bar['value'] == 75
    assert s._label['text'] == '步骤3'
    s.close()
```

- [ ] **Step 2: Run tests**

```bash
pytest tests/test_splash.py -v
```
Expected: 3 tests PASS
