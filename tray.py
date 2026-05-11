"""QQ消息转发 — 系统托盘管理程序"""
import subprocess
import sys
import os
import time
import threading
import socket
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
    """创建托盘图标（纯色圆点 64x64）"""
    img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    colors = {
        'green': (76, 175, 80, 255),
        'red': (244, 67, 54, 255),
        'yellow': (255, 193, 7, 255),
    }
    draw.ellipse([8, 8, 56, 56], fill=colors.get(color, colors['green']))
    return img


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
