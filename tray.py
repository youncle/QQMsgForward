"""QQ消息转发 — 系统托盘管理程序"""
import subprocess
import sys
import os
import time
import threading
import socket
import tkinter as tk
from tkinter import ttk
import tkinter.messagebox as tkmb
import pystray
from PIL import Image, ImageDraw

import settings

# 路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FORWARD_SCRIPT = os.path.join(SCRIPT_DIR, 'qq-message-forward.py')
SHUTDOWN_FLAG = os.path.join(SCRIPT_DIR, '.shutdown.flag')
LOG_FILE = os.path.join(SCRIPT_DIR, 'forward.log')

# 端口
LLBOT_PORT = 3000
FORWARD_PORT = 8080

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


def show_status_window(icon):
    """显示状态弹窗"""
    llbot_ok, forward_ok = get_status()
    msg = (
        f"LLBot (端口 3000): {'运行中' if llbot_ok else '已停止'}\n"
        f"转发脚本 (端口 8080): {'运行中' if forward_ok else '已停止'}"
    )
    tkmb.showinfo('QQ消息转发 - 状态', msg)


def shutdown_service(icon):
    """关闭所有服务"""
    global running
    running = False
    stop_forward()
    # 终止 LLBot（实际进程可能是 node.exe）
    subprocess.run(['taskkill', '/f', '/im', 'node.exe'],
                   capture_output=True)
    subprocess.run(['taskkill', '/f', '/im', 'llbot.exe'],
                   capture_output=True)
    # 关闭 QQ
    for qq_name in ['QQ.exe', 'QQNT.exe']:
        subprocess.run(['taskkill', '/f', '/im', qq_name],
                       capture_output=True)
    # 清理标志文件
    if os.path.exists(SHUTDOWN_FLAG):
        try:
            os.remove(SHUTDOWN_FLAG)
        except OSError:
            pass
    icon.stop()


def monitor_loop(icon):
    """监控线程：每5秒检查服务状态 + 关闭标志文件"""
    was_ok = True
    while running:
        time.sleep(5)
        if not running:
            break

        # 检测关闭标志文件（由 stop.vbs 创建）
        if os.path.exists(SHUTDOWN_FLAG):
            shutdown_service(icon)
            break

        llbot_ok, forward_ok = get_status()
        all_ok = llbot_ok and forward_ok

        if not all_ok and was_ok:
            icon.icon = create_icon_image('red')
            icon.title = 'QQ消息转发 - 服务异常'
        elif all_ok and not was_ok:
            icon.icon = create_icon_image('green')
            icon.title = 'QQ消息转发 - 运行中'

        was_ok = all_ok


def setup_tray():
    """创建并运行托盘图标"""
    icon = pystray.Icon(
        'qq_forward',
        create_icon_image('green'),
        'QQ消息转发 - 运行中',
        menu=pystray.Menu(
            pystray.MenuItem('打开设置', lambda icon: settings.open_settings()),
            pystray.MenuItem('查看状态', show_status_window),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('关闭服务', shutdown_service),
        )
    )

    # 启动监控线程
    monitor = threading.Thread(target=monitor_loop, args=(icon,), daemon=True)
    monitor.start()

    icon.run()


if __name__ == '__main__':
    # 先确认 LLBot 已运行
    if not check_port(LLBOT_PORT):
        print(f"错误: LLBot 未运行（端口 {LLBOT_PORT} 不通），请先启动 LLBot")
        sys.exit(1)

    # 启动转发脚本
    start_forward()
    # 等待转发脚本启动
    for _ in range(10):
        if check_port(FORWARD_PORT):
            break
        time.sleep(1)

    if not check_port(FORWARD_PORT):
        print("警告: 转发脚本可能未启动成功（端口 8080 不通）")

    # 启动托盘
    setup_tray()
