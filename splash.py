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
        self._root.lift()
        self._destroyed = False

        # 窗口尺寸和居中
        win_w, win_h = 520, 150
        scr_w = self._root.winfo_screenwidth()
        scr_h = self._root.winfo_screenheight()
        x = (scr_w - win_w) // 2
        y = (scr_h - win_h) // 3  # 位置上移
        self._root.geometry(f'{win_w}x{win_h}+{x}+{y}')

        # 标题
        title = tk.Label(
            self._root,
            text='QQ Forward',
            font=('微软雅黑', 16, 'bold'),
            fg='#ffffff',
            bg='#2b2b2b',
        )
        title.pack(pady=(18, 8))

        # 进度条
        self._bar = ttk.Progressbar(
            self._root,
            mode='determinate',
            length=460,
            maximum=100,
        )
        self._bar.pack(pady=(0, 6))

        # 状态文字
        self._label = tk.Label(
            self._root,
            text='正在准备...',
            font=('微软雅黑', 10),
            fg='#ffcc00',
            bg='#2b2b2b',
        )
        self._label.pack()

        self._root.update()

    def update(self, percent: float, text: str) -> None:
        """平滑动画更新进度条到目标值；已关闭则忽略"""
        if self._destroyed:
            return
        current = self._bar['value']
        target = float(percent)
        step = 0.5 if target > current else -0.5
        while abs(current - target) > abs(step):
            current += step
            self._bar['value'] = current
            self._label.config(text=text, fg='#ffcc00')
            self._root.update()
        self._bar['value'] = target
        self._label.config(text=text, fg='#ffcc00')
        self._root.update()

    def close(self) -> None:
        """销毁窗口"""
        if self._destroyed:
            return
        self._destroyed = True
        self._root.destroy()
