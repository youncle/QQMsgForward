"""QQ消息转发 — 系统托盘管理程序"""
import subprocess
import sys
import os
import time
import threading
import socket
import tkinter as tk
from tkinter import ttk

import pystray
from PIL import Image, ImageDraw

import settings as settings_mod

import ctypes
from ctypes import wintypes

# 路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FORWARD_SCRIPT = os.path.join(SCRIPT_DIR, 'qq-message-forward.py')
SHUTDOWN_FLAG = os.path.join(SCRIPT_DIR, '.shutdown.flag')
LOG_FILE = os.path.join(SCRIPT_DIR, 'forward.log')

# 端口
LLBOT_PORT = 3000
FORWARD_PORT = 8080

# Win32 constants for left-click hook
GWLP_WNDPROC = -4
WM_LBUTTONUP = 0x0202

_original_wndproc = None
_wndproc_ref = None
_hook_root = None
_hook_callback = None

WNDPROC_TYPE = ctypes.WINFUNCTYPE(
    ctypes.c_longlong, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM
)

forward_process = None
running = True


def check_port(port: int, host: str = '127.0.0.1') -> bool:
    """检查端口是否开放"""
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


def start_forward():
    """启动转发脚本子进程"""
    global forward_process
    log_fh = open(LOG_FILE, 'a', encoding='utf-8')
    forward_process = subprocess.Popen(
        [sys.executable, FORWARD_SCRIPT],
        stdout=log_fh,
        stderr=subprocess.STDOUT
    )


def stop_forward():
    """停止转发脚本子进程"""
    global forward_process
    if forward_process and forward_process.poll() is None:
        forward_process.terminate()
        try:
            forward_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            forward_process.kill()
    if forward_process and forward_process.stdout:
        forward_process.stdout.close()


def get_status():
    """获取当前服务状态"""
    llbot_ok = check_port(LLBOT_PORT)
    forward_ok = check_port(FORWARD_PORT)
    return llbot_ok, forward_ok


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


def create_status_tab(parent):
    """创建状态选项卡内容"""
    frame = ttk.Frame(parent, padding=15)

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

    refresh()

    ttk.Separator(frame, orient='horizontal').pack(fill='x', pady=10)

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

    def auto_refresh():
        refresh()
        frame.after(3000, auto_refresh)

    auto_refresh()

    return frame


def show_main_window(root):
    """显示主面板"""
    root.deiconify()
    root.lift()
    root.focus_force()


def hide_main_window(root):
    """隐藏主面板（不退出）"""
    root.withdraw()


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


def monitor_loop(icon, root):
    """监控线程：每5秒检查服务状态 + 关闭标志文件"""
    was_ok = True
    while running:
        time.sleep(5)
        if not running:
            break

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


def setup_tray(root, on_open):
    """创建托盘图标（在 daemon 线程中运行 pystray）"""
    def do_shutdown():
        handle_shutdown(icon, root)

    icon = pystray.Icon(
        'qq_forward',
        create_icon_image('green'),
        'QQ消息转发 - 运行中',
        menu=pystray.Menu(
            pystray.MenuItem('打开主面板', lambda: root.after(0, lambda: on_open(root))),
            pystray.MenuItem('关闭服务', lambda: do_shutdown()),
        )
    )

    monitor = threading.Thread(target=monitor_loop, args=(icon, root), daemon=True)
    monitor.start()

    tray_thread = threading.Thread(target=icon.run, daemon=True)
    tray_thread.start()

    # 延迟 hook 左键点击（等 pystray 窗口创建）
    root.after(500, lambda: _hook_left_click(root, on_open))

    return icon


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
