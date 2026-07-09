"""QQ Message Forward — 系统托盘管理程序"""
import subprocess
import sys
import os
import time
import threading
import json
import socket
import tkinter as tk
from tkinter import ttk, messagebox

import ctypes

import pystray
from PIL import Image, ImageDraw

import requests

import settings as settings_mod

import splash as splash_mod
import forward_qq as forward_mod
# 路径
if getattr(sys, 'frozen', False):
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    BASE_DIR = os.path.dirname(sys.executable)  # PyInstaller: exe 所在目录
else:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    BASE_DIR = os.path.dirname(SCRIPT_DIR)  # 开发模式: 项目根目录
LOG_FILE = os.path.join(BASE_DIR, 'logs', 'forward.log')
SHUTDOWN_FLAG = os.path.join(BASE_DIR, '.shutdown.flag')

# 端口
LLBOT_PORT = 3000
FORWARD_PORT = 9090

# 窗口状态文件
WINDOW_STATE_FILE = os.path.join(BASE_DIR, 'config', '.window_state.json')
_save_timer_id = None


def load_window_geometry() -> str | None:
    """读取保存的窗口几何信息"""
    try:
        with open(WINDOW_STATE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('geometry')
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def save_window_geometry(geometry: str) -> None:
    """保存窗口几何信息"""
    try:
        with open(WINDOW_STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump({'geometry': geometry}, f)
    except OSError:
        pass


running = True
_llbot_pids: list[int] = []


def find_port_pid(port: int) -> str | None:
    """查找占用指定端口的进程 PID"""
    try:
        output = subprocess.run(
            ['netstat', '-ano'], capture_output=True, text=True
        ).stdout
        for line in output.split('\n'):
            if f':{port}' in line and 'LISTENING' in line:
                parts = line.strip().split()
                return parts[-1]
    except Exception:
        pass
    return None


def kill_port_process(port: int) -> bool:
    """终止占用指定端口的进程，返回是否成功"""
    pid = find_port_pid(port)
    if pid and pid != str(os.getpid()):
        subprocess.run(['taskkill', '/f', '/pid', pid], capture_output=True)
        time.sleep(1)
        return not check_port(port)
    return False


def check_port(port: int, host: str = '127.0.0.1') -> bool:
    """检查端口是否开放"""
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


def get_status():
    """获取当前服务状态"""
    llbot_ok = check_port(LLBOT_PORT)
    forward_ok = check_port(FORWARD_PORT)
    return llbot_ok, forward_ok


def create_icon_image(color: str = 'green'):
    """创建托盘图标（深灰圆点+彩色状态外圈，64x64）"""
    img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    colors = {
        'green': (76, 175, 80, 255),
        'red': (244, 67, 54, 255),
        'yellow': (255, 193, 7, 255),
    }
    c = colors.get(color, colors['green'])

    # 外圈（状态色，3px 宽）
    draw.ellipse([2, 2, 61, 61], outline=c, width=3)
    # 内圆点（深灰色 #37474F）
    draw.ellipse([13, 13, 50, 50], fill=(55, 71, 79, 255))
    # 高光（左上角半透明白色小圆）
    draw.ellipse([18, 18, 28, 28], fill=(255, 255, 255, 50))

    return img


def create_status_tab(parent):
    """创建状态选项卡内容"""
    frame = ttk.Frame(parent, padding=(10, 15))

    ttk.Label(frame, text='服务状态', font=('微软雅黑', 11, 'bold')).pack(
        anchor='w', pady=(0, 10))

    status_frm = ttk.Frame(frame)
    status_frm.pack(fill='x')

    # 读取 llbot_apis 获取真实 QQ→端口映射（探测后已写入）
    _llbot_entries = []  # [(port, qq)]
    try:
        _cfg = forward_mod.get_config()
        _apis = _cfg.get('llbot_apis', {})
        for _qq, _url in _apis.items():
            try:
                _port = int(_url.rsplit(':', 1)[-1])
            except (ValueError, IndexError):
                _port = 0
            _llbot_entries.append((_port, _qq))
        _llbot_entries.sort()
    except Exception:
        pass

    # fallback: 无 llbot_apis 时从 robot_qq 推断
    _llbot_labels = []
    if not _llbot_entries:
        try:
            _cfg = forward_mod.get_config()
            _rqt = _cfg.get('robot_qq', [])
            if isinstance(_rqt, int):
                _rqt = [_rqt]
        except Exception:
            _rqt = []
        for _si, _sq in enumerate(_rqt or [0]):
            _llbot_entries.append((LLBOT_PORT + _si, str(_sq)))

    for _idx, (_port, _qq) in enumerate(_llbot_entries):
        ttk.Label(status_frm, text=f"{_qq} (端口 {_port}):", width=22, anchor="w").grid(
            row=_idx, column=0, sticky="w", pady=3)
        _sl = ttk.Label(status_frm, text="检测中...", foreground="gray")
        _sl.grid(row=_idx, column=1, sticky="w", pady=3)
        _llbot_labels.append((_port, _sl))

    _row_offset = len(_llbot_entries) if _llbot_entries else 1
    ttk.Label(status_frm, text='QQ转发 (端口 9090):', width=20, anchor='w').grid(
        row=_row_offset, column=0, sticky='w', pady=3)
    forward_status = ttk.Label(status_frm, text='检测中...', foreground='gray')
    forward_status.grid(row=_row_offset, column=1, sticky='w', pady=3)

    _wecom_row = _row_offset + 1
    ttk.Label(status_frm, text='企业微信转发:', width=20, anchor='w').grid(
        row=_wecom_row, column=0, sticky='w', pady=3)
    wecom_status = ttk.Label(status_frm, text='检测中...', foreground='gray')
    wecom_status.grid(row=_wecom_row, column=1, sticky='w', pady=3)

    status_frm.grid_columnconfigure(1, weight=1)

    refresh_btn = ttk.Button(status_frm, text='刷新', command=lambda: refresh())
    refresh_btn.grid(row=0, column=2, rowspan=_wecom_row + 1, sticky='e', padx=(10, 0), pady=3)

    _log_timer_id = None
    _btn_timer_id = None

    def load_logs():
        nonlocal _log_timer_id
        if os.path.exists(LOG_FILE):
            try:
                with open(LOG_FILE, 'r', encoding='utf-8', errors='replace') as f:
                    f.seek(0, 2)
                    size = f.tell()
                    if size > 8192:
                        f.seek(max(0, size - 8192))
                    else:
                        f.seek(0)
                    f.readline()  # 跳过可能的不完整行
                    tail = f.read()
                    lines = tail.splitlines(True)[-30:]
                log_text.config(state='normal')
                log_text.delete('1.0', 'end')
                log_text.insert('1.0', ''.join(lines))
                log_text.see('end')
                log_text.config(state='disabled')
            except Exception:
                pass
        if _log_timer_id is not None:
            frame.after_cancel(_log_timer_id)
        _log_timer_id = frame.after(5000, load_logs)

    def refresh():
        nonlocal _btn_timer_id
        forward_ok = check_port(FORWARD_PORT)
        for _port, _sl in _llbot_labels:
            _sok = check_port(_port)
            _sl.config(
                text=f'运行中 (端口 {_port})' if _sok else '已停止',
                foreground='green' if _sok else 'red')
        forward_status.config(
            text='运行中' if forward_ok else '已停止',
            foreground='green' if forward_ok else 'red')

        # 企业微信状态
        try:
            _wc_cfg = forward_mod.get_config()
            _wc_enabled = _wc_cfg.get("wecom_enabled", True)
            _wc_bots = _wc_cfg.get("wecom_bots", [])
            if not _wc_bots:
                wecom_status.config(text="未配置", foreground="gray")
            elif not _wc_enabled:
                wecom_status.config(text="未启用", foreground="gray")
            else:
                _mode = _wc_cfg.get("wecom_mode", "api")
                if _mode == "api":
                    wecom_status.config(text=f"API 模式 ({len(_wc_bots)} 个机器人)", foreground="green")
                else:
                    try:
                        import subprocess
                        _r = subprocess.run(
                            ["tasklist", "/fi", "IMAGENAME eq WXWork.exe"],
                            capture_output=True, text=True, creationflags=0x08000000
                        )
                        if "WXWork.exe" in _r.stdout:
                            wecom_status.config(text="UI 模式 (企微运行中)", foreground="green")
                        else:
                            wecom_status.config(text="UI 模式 (企微未启动)", foreground="orange")
                    except Exception:
                        wecom_status.config(text="UI 模式 (状态未知)", foreground="gray")
        except Exception:
            wecom_status.config(text="读取失败", foreground="red")
        load_logs()
        refresh_btn.config(text='已刷新')
        if _btn_timer_id is not None:
            frame.after_cancel(_btn_timer_id)
        _btn_timer_id = frame.after(1500, lambda: refresh_btn.config(text='刷新'))

    refresh()
    load_logs()

    ttk.Separator(frame, orient='horizontal').pack(fill='x', pady=10)

    # 日志标题行：标签 + 清空按钮
    log_header = ttk.Frame(frame)
    log_header.pack(fill="x", pady=(0, 5))
    ttk.Label(log_header, text="最近日志", font=("微软雅黑", 11, "bold")).pack(side="left")
    ttk.Button(log_header, text="清空日志", command=lambda: clear_logs()).pack(side="right")

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

    def clear_logs():
        """清空全部日志（文件 + 界面）"""
        if not messagebox.askyesno("确认清空", "确定要清空所有日志吗？\n此操作不可恢复。"):
            return
        try:
            with open(LOG_FILE, "w", encoding="utf-8") as f:
                f.write("")
            log_text.config(state="normal")
            log_text.delete("1.0", "end")
            log_text.config(state="disabled")
        except Exception as e:
            messagebox.showerror("清空失败", f"无法清空日志文件：\n{e}")


    def auto_refresh():
        refresh()
        frame.after(5000, auto_refresh)

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


def _abort_startup(splash):
    """取消启动，清理所有已启动的进程"""
    for pid in _llbot_pids:
        subprocess.run(
            ['taskkill', '/f', '/t', '/pid', str(pid)],
            capture_output=True, timeout=3,
        )
    _llbot_pids.clear()
    splash.close()
    os._exit(0)


def shutdown_service(icon):
    global running
    running = False

    for pid in _llbot_pids:
        subprocess.run(
            ['taskkill', '/f', '/t', '/pid', str(pid)],
            capture_output=True, timeout=3,
        )
    _llbot_pids.clear()

    try:
        _cfg = forward_mod.get_config()
        _rq_list = _cfg.get('robot_qq', [])
        if isinstance(_rq_list, int):
            _rq_list = [_rq_list]
    except Exception:
        _rq_list = []
    for _idx in range(len(_rq_list or [])):
        _port = LLBOT_PORT + _idx
        _pid = find_port_pid(_port)
        if _pid:
            subprocess.run(
                ['taskkill', '/f', '/pid', _pid],
                capture_output=True, timeout=3,
            )

    for _name in ['QQ.exe', 'QQNT.exe', 'pythonw.exe']:
        subprocess.run(
            ['taskkill', '/f', '/im', _name],
            capture_output=True, timeout=3,
        )

    if os.path.exists(SHUTDOWN_FLAG):
        try:
            os.remove(SHUTDOWN_FLAG)
        except OSError:
            pass

    try:
        with open(cfg_path, 'r', encoding='utf-8') as f:
            _cfg_data = json.load(f)
        _rq = _cfg_data.get('robot_qq', [])
        if isinstance(_rq, int):
            _rq = [_rq]
        _keep = max(1, len(_rq))
    except Exception:
        _keep = 1
    _base = os.path.join(BASE_DIR, 'runtime', 'LLBot-Desktop-win-x64')
    for _idx_dir in range(_keep, 20):
        _dir = _base + (f'-{_idx_dir + 1}' if _idx_dir > 0 else '')
        if _dir != _base and os.path.isdir(_dir):
            import shutil
            shutil.rmtree(_dir, ignore_errors=True)

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
        time.sleep(10)
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
            icon.title = 'QQ Message Forward - 服务异常'
        elif not all_ok:
            icon.icon = create_icon_image('yellow')
            icon.title = 'QQ Message Forward - 部分异常'
        elif all_ok and not was_ok:
            icon.icon = create_icon_image('green')
            icon.title = 'QQ Message Forward - 运行中'

        was_ok = all_ok


def setup_tray(root, on_open):
    """创建托盘图标（在 daemon 线程中运行 pystray）"""
    def do_shutdown():
        handle_shutdown(icon, root)

    icon = pystray.Icon(
        'qq_forward',
        create_icon_image('green'),
        'QQ Message Forward - 运行中',
        menu=pystray.Menu(
            pystray.MenuItem('打开主面板', lambda: root.after(0, lambda: on_open(root)), default=True),
            pystray.MenuItem('关闭服务', lambda: root.after(0, do_shutdown)),
        )
    )

    monitor = threading.Thread(target=monitor_loop, args=(icon, root), daemon=True)
    monitor.start()

    tray_thread = threading.Thread(target=icon.run, daemon=True)
    tray_thread.start()

    return icon


def create_desktop_shortcut():
    """在桌面创建快捷方式（PyInstaller 下指向 exe，开发模式下指向 start.vbs）"""
    try:
        desktop = os.path.join(os.environ['USERPROFILE'], 'Desktop')
        lnk_path = os.path.join(desktop, 'QQ Message Forward.lnk')

        # PyInstaller 下 exe 目录 ≠ __file__ 目录，需用 get_base_dir()
        if getattr(sys, 'frozen', False):
            app_dir = os.path.dirname(sys.executable)
            target_path = sys.executable
        else:
            app_dir = SCRIPT_DIR
            target_path = os.path.join(BASE_DIR, 'scripts', 'start.vbs')

        # 生成 .ico 图标文件
        ico_path = os.path.join(BASE_DIR, 'resources', 'app.ico')
        _save_icon_file(ico_path)

        scripts_dir = os.path.join(BASE_DIR, 'scripts')
        os.makedirs(scripts_dir, exist_ok=True)
        tmp_vbs = os.path.join(scripts_dir, '.create_shortcut.vbs')

        vbs_code = (
            f'Set ws = CreateObject("WScript.Shell")\r\n'
            f'Set sc = ws.CreateShortcut("{lnk_path}")\r\n'
            f'sc.TargetPath = "{target_path}"\r\n'
            f'sc.WorkingDirectory = "{app_dir}"\r\n'
            f'sc.Description = "QQ Message Forward - 一键启动"\r\n'
            f'sc.IconLocation = "{ico_path}"\r\n'
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


def _save_icon_file(path: str) -> None:
    """将托盘图标另存为 .ico 文件（含 16/32/48 多尺寸）"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img = create_icon_image('green')
    sizes = [(16, 16), (32, 32), (48, 48)]
    icons = [img.resize(s, Image.LANCZOS) for s in sizes]
    icons[0].save(path, format='ICO', sizes=sizes, append_images=icons[1:])


def _set_taskbar_icon(hwnd: int, ico_path: str) -> None:
    """通过 Win32 API 设置窗口任务栏/标题栏图标"""
    try:
        handle = ctypes.windll.user32.LoadImageW(
            0, ico_path, 1, 0, 0, 0x00000010
        )
        if handle:
            WM_SETICON = 0x0080
            ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, 0, handle)
            ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, 1, handle)
            ctypes.windll.user32.DestroyIcon(handle)
    except Exception:
        pass


def main():
    splash = splash_mod.SplashScreen(on_cancel=lambda: _abort_startup(splash))
    splash.update(0, '正在准备环境...')

    # 注册异常钩子：启动过程中任何未处理异常都会关闭进度条
    _orig_excepthook = sys.excepthook

    def _splash_excepthook(exc_type, exc_val, exc_tb):
        splash.close()
        _orig_excepthook(exc_type, exc_val, exc_tb)

    sys.excepthook = _splash_excepthook

    # 清理上次运行残留进程
    for _cp in [LLBOT_PORT, LLBOT_PORT + 1, LLBOT_PORT + 2, FORWARD_PORT]:
        if check_port(_cp):
            kill_port_process(_cp)

    import wizard as wizard_mod
    import forward_qq as forward_mod
    forward_app = forward_mod.app
    set_forward_config = forward_mod.set_config_path

    base_dir = wizard_mod.get_base_dir()

    # 设置 forward 模块的配置文件路径（PyInstaller 下与 exe 同目录）
    fwd_config_path = os.path.join(BASE_DIR, 'config', 'config.json')
    set_forward_config(fwd_config_path)
    settings_mod.set_config_path(fwd_config_path)

    # 设置 forward 模块的日志文件路径（PyInstaller 下与 exe 同目录）
    forward_mod.set_log_path(os.path.join(BASE_DIR, 'logs', 'forward.log'))

    # 检查 runtime/LLBot-Desktop-win-x64 目录是否存在
    llbot_dir = os.path.join(base_dir, 'runtime/LLBot-Desktop-win-x64')
    if not os.path.isdir(llbot_dir):
        # 尝试在开发模式下查找
        llbot_dir = os.path.join(BASE_DIR, 'runtime', 'LLBot-Desktop-win-x64')

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
        splash.close()
        sys.exit(1)

    # 检查 config.json，不存在则弹出向导
    if not os.path.exists(fwd_config_path):
        splash.close()
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
        splash = splash_mod.SplashScreen(on_cancel=lambda: _abort_startup(splash))
        splash.update(0, '正在准备环境...')

    # 检查 config.json 是否有效
    try:
        with open(fwd_config_path, 'r', encoding='utf-8') as f:
            json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        splash.close()
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
            splash = splash_mod.SplashScreen(on_cancel=lambda: _abort_startup(splash))
            splash.update(0, '正在准备环境...')
        else:
            sys.exit(1)

    splash.update(25, '正在准备环境...')

    # ====== 多 LLBot 实例启动 ======
    # 读取 robot_qq 数组，确定实例数
    _instances = []
    try:
        with open(fwd_config_path, 'r', encoding='utf-8') as _f:
            _cfg_data = json.load(_f)
            _rq_list = _cfg_data.get('robot_qq', [])
            if isinstance(_rq_list, int):
                _rq_list = [_rq_list]
    except Exception:
        _rq_list = []
    if not _rq_list:
        _rq_list = [0]

    _llbot_apis = {}
    for _idx, _qq in enumerate(_rq_list):
        _port = LLBOT_PORT + _idx
        _webui_port = 3080 + _idx
        _llbot_apis[str(_qq)] = f'http://127.0.0.1:{_port}'

        if _idx == 0:
            _inst_dir = llbot_dir
        else:
            _inst_dir = llbot_dir.rstrip('\\') + f'-{_idx + 1}'
            # 不存在则复制目录
            if not os.path.isdir(_inst_dir):
                import shutil
                splash.update(25, f'正在复制 LLBot 实例 {_idx + 1}...')
                shutil.copytree(llbot_dir, _inst_dir)

            # 从实例1同步所有QQ配置数据到实例2，并更新端口
            _src_data = os.path.join(llbot_dir, 'bin', 'llbot', 'data')
            _dst_data = os.path.join(_inst_dir, 'bin', 'llbot', 'data')
            if os.path.isdir(_src_data) and _idx > 0:
                if not os.path.isdir(_dst_data):
                    os.makedirs(_dst_data, exist_ok=True)
                import shutil
                for _fname in os.listdir(_src_data):
                    _srcf = os.path.join(_src_data, _fname)
                    _dstf = os.path.join(_dst_data, _fname)
                    if os.path.isfile(_srcf) and _fname.endswith('.json'):
                        try:
                            shutil.copy2(_srcf, _dstf)
                        except Exception:
                            pass

        # 更新实例2中所有配置文件的端口
        _inst_data_dir = os.path.join(_inst_dir, 'bin', 'llbot', 'data')
        if _idx > 0 and os.path.isdir(_inst_data_dir):
            for _cfg_fn in os.listdir(_inst_data_dir):
                if not _cfg_fn.endswith('.json'):
                    continue
                _cfg_fp = os.path.join(_inst_data_dir, _cfg_fn)
                try:
                    with open(_cfg_fp, 'r', encoding='utf-8') as _f:
                        _c = json.load(_f)
                    _ch = False
                    for _conn in _c.get('ob11', {}).get('connect', []):
                        if _conn.get('type') == 'http':
                            if _conn.get('port') != _port:
                                _conn['port'] = _port
                                _ch = True
                    _wu = _c.get('webui', {})
                    if _wu.get('port') != _webui_port:
                        _wu['port'] = _webui_port
                        _ch = True
                    if _ch:
                        with open(_cfg_fp, 'w', encoding='utf-8') as _f:
                            json.dump(_c, _f, ensure_ascii=False, indent=2)
                except Exception:
                    pass

        # 同步更新 default_config.json 的 webui 端口
        _def_cfg_path = os.path.join(_inst_dir, 'bin', 'llbot', 'default_config.json')
        if os.path.exists(_def_cfg_path) and _idx > 0:
            try:
                with open(_def_cfg_path, 'r', encoding='utf-8') as _f:
                    _def_cfg = json.load(_f)
                if _def_cfg.get('webui', {}).get('port') != _webui_port:
                    _def_cfg['webui']['port'] = _webui_port
                    with open(_def_cfg_path, 'w', encoding='utf-8') as _f:
                        json.dump(_def_cfg, _f, ensure_ascii=False, indent=2)
            except Exception:
                pass

        # 启动实例
        _exe = os.path.join(_inst_dir, 'llbot.exe')
        if os.path.exists(_exe) and not check_port(_port):
            proc = subprocess.Popen(
                [_exe], cwd=_inst_dir,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0,
            )
            _llbot_pids.append(proc.pid)
            if splash.canceled:
                _abort_startup(splash)
            # 登录窗口已弹出，引导用户操作
            if _idx == 0:
                splash.update(30, '请查看弹出的QQ登录窗口，扫码登录...')
            # 主动等待当前实例登录再启动下一个
            if _idx < len(_rq_list) - 1:
                splash.update(25, f'等待第 {_idx + 1} 个 QQ 扫码登录...')
                _logged_in = False
                for _w in range(60):
                    if splash.canceled:
                        _abort_startup(splash)
                    if check_port(_port):
                        try:
                            _r = requests.get(f'http://127.0.0.1:{_port}/get_login_info', timeout=3)
                            _j = _r.json()
                            if _j.get("retcode") == 0 and _j.get("data", {}).get("user_id"):
                                _logged_in = True
                                break
                        except Exception:
                            pass
                    # 响应式睡眠：100ms 间隔 + 事件处理
                    for _t in range(10):
                        if splash.canceled:
                            _abort_startup(splash)
                        time.sleep(0.1)
                        splash._root.update()
                    splash.update(30, f'等待扫码登录... ({_w + 1}s)')
                if not _logged_in:
                    splash.close()
                    from tkinter import messagebox
                    _root_tmp = tk.Tk()
                    _root_tmp.withdraw()
                    messagebox.showerror('登录超时',
                        f'第 {_idx + 1} 个 QQ 未在 60 秒内完成登录\n程序将关闭。')
                    _root_tmp.destroy()
                    for pid in _llbot_pids:
                        subprocess.run(['taskkill', '/f', '/t', '/pid', str(pid)], capture_output=True, timeout=3)
                    _llbot_pids.clear()
                    sys.exit(1)
        elif not os.path.exists(_exe):
            splash.close()
            from tkinter import messagebox
            root_tmp = tk.Tk()
            root_tmp.withdraw()
            messagebox.showerror('组件缺失',
                f'未找到 LLBot 程序:\n{_exe}')
            root_tmp.destroy()
            sys.exit(1)

        splash.update(25, f'已启动 LLBot 实例 {_idx + 1}/{len(_rq_list)}')

    # 统一等待所有实例 HTTP API 端口就绪
    for _wait_i in range(60):
        _ready_ports = [p for p in [LLBOT_PORT + i for i in range(len(_rq_list))] if check_port(p)]
        if len(_ready_ports) == len(_rq_list):
            break
        time.sleep(1)
        splash.update(30 + min(_wait_i * 0.5, 20),
            f'等待实例就绪... ({len(_ready_ports)}/{len(_rq_list)})')

    _failed = [p for p in [LLBOT_PORT + i for i in range(len(_rq_list))] if not check_port(p)]
    if _failed:
        splash.close()
        from tkinter import messagebox
        root_tmp = tk.Tk()
        root_tmp.withdraw()
        messagebox.showwarning('启动提示',
            f'部分 LLBot 实例未登录（端口 {_failed}）\n\n'
            '请在 WebUI 中完成登录后重新刷新。')
        root_tmp.destroy()

    splash.update(50, f'启动完成 {len(_rq_list)} 个 LLBot 实例')
    if splash.canceled:
        _abort_startup(splash)
    # ====== 探测各端口实际登录的 QQ (绕开索引顺序假设) ======
    splash.update(55, '正在探测机器人登录状态...')
    _probed_apis = {}
    _probefail_ports = []
    for _idx in range(len(_rq_list)):
        _port = LLBOT_PORT + _idx
        _base = f'http://127.0.0.1:{_port}'
        _real_qq = None
        for _try in range(5):
            try:
                _r = requests.get(f'{_base}/get_login_info', timeout=3)
                _j = _r.json()
                _uid = _j.get('data', {}).get('user_id') if _j.get('retcode') == 0 else None
                if _uid:
                    _real_qq = str(_uid)
                    break
            except Exception:
                pass
            time.sleep(2)
        if _real_qq:
            _probed_apis[_real_qq] = _base
            splash.update(55, f'探测完成: QQ {_real_qq} → 127.0.0.1:{_port}')
        else:
            _probefail_ports.append(_port)
            _fallback_qq = str(_rq_list[_idx]) if _idx < len(_rq_list) else str(_port)
            _probed_apis[_fallback_qq] = _base
            splash.update(55, f'⚠ 探测失败: 端口 {_port}，使用索引映射')
        if splash.canceled:
            _abort_startup(splash)
    if _probed_apis:
        _llbot_apis = _probed_apis


    # 写入 llbot_apis 到 config.json
    try:
        with open(fwd_config_path, 'r', encoding='utf-8') as _f:
            _cfg_save = json.load(_f)
        _cfg_save['llbot_apis'] = _llbot_apis
        _tmp = fwd_config_path + '.tmp'
        with open(_tmp, 'w', encoding='utf-8') as _f:
            json.dump(_cfg_save, _f, ensure_ascii=False, indent=2)
        os.replace(_tmp, fwd_config_path)
    except Exception:
        pass

    # 检查端口 9090，如果被旧进程占用则 kill
    if check_port(FORWARD_PORT):
        kill_port_process(FORWARD_PORT)
        if check_port(FORWARD_PORT):
            splash.close()
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
        try:
            forward_app.run(
                host='127.0.0.1',
                port=FORWARD_PORT,
                debug=False,
                threaded=True,
                use_reloader=False,
            )
        except Exception as e:
            import traceback
            with open(LOG_FILE, 'a', encoding='utf-8') as lf:
                lf.write(f'[FATAL] Flask forward service crashed:\n{traceback.format_exc()}\n')

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

    if not check_port(FORWARD_PORT):
        splash.close()
        from tkinter import messagebox
        root_tmp = tk.Tk()
        root_tmp.withdraw()
        messagebox.showwarning(
            '启动警告',
            '转发服务可能未启动成功，请稍后在托盘面板中查看状态。'
        )
        root_tmp.destroy()

    splash.update(75, '正在加载界面...')
    if splash.canceled:
        _abort_startup(splash)

    # 初始化企微 UI 引擎（仅在 UI 模式下使用）
    from wecom import get_ui_engine
    get_ui_engine()

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
    root.title('QQ Message Forward')
    root.resizable(True, True)

    # 设置窗口图标
    ico_path = os.path.join(BASE_DIR, 'resources', 'app.ico')
    if not os.path.exists(ico_path):
        ico_path = os.path.join(BASE_DIR, 'resources', 'app.ico')
    _save_icon_file(ico_path)
    try:
        root.iconbitmap(ico_path)
    except Exception:
        pass

    root.protocol('WM_DELETE_WINDOW', lambda: hide_main_window(root))

    # Tab 标签页
    style = ttk.Style()
    style.configure('TNotebook.Tab', padding=(35, 16), font=('微软雅黑', 10))

    notebook = ttk.Notebook(root, padding=0)
    notebook.pack(fill='both', expand=True, padx=0, pady=5)
    tab1 = create_status_tab(notebook)
    notebook.add(tab1, text='     状态     ')
    shared_cfg = settings_mod.load_config()
    tab2 = settings_mod.create_forward_frame(notebook, shared_cfg)
    notebook.add(tab2, text='     转发     ')
    tab3 = settings_mod.create_filter_frame(notebook, shared_cfg)
    notebook.add(tab3, text='     过滤     ')
    tab4 = settings_mod.create_wecom_frame(notebook, shared_cfg)
    notebook.add(tab4, text='     微信     ')

    # 内容区域保留 8px 垂直间距，水平由 Frame padding 控制
    notebook.tab(tab1, padding=(0, 8))
    notebook.tab(tab2, padding=(0, 8))
    notebook.tab(tab3, padding=(0, 8))
    notebook.tab(tab4, padding=(0, 8))

    def _geometry_on_screen(geo: str) -> bool:
        """检查窗口位置是否在任意显示器范围内"""
        try:
            parts = geo.split('+')
            if len(parts) < 3:
                return True
            x, y = int(parts[1]), int(parts[2])
            w_h = parts[0].split('x')
            w, h = int(w_h[0]), int(w_h[1])
            scr_w = root.winfo_screenwidth()
            scr_h = root.winfo_screenheight()
            # 窗口至少部分可见：不完全在屏幕左边/右边/上边/下边之外
            if x + w < 0 or x > scr_w + w or y + h < 0 or y > scr_h + h:
                return False
            return True
        except Exception:
            return True

    # 恢复窗口尺寸
    saved_geo = load_window_geometry()
    if saved_geo:
        if _geometry_on_screen(saved_geo):
            root.geometry(saved_geo)
        else:
            root.geometry(saved_geo.split('+')[0])

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

    # 首次运行：捕获布局自然尺寸作为默认
    if not saved_geo:
        root.update_idletasks()
        default_geo = root.geometry()
        save_window_geometry(default_geo)

    # 设置最小尺寸（600px 为合理最小宽度，高度基于当前页）
    geo_str = root.geometry()
    base_h = int(geo_str.split('x')[1].split('+')[0])
    root.minsize(1024, base_h)

    splash.update(100, '启动完成')
    splash.close()

    root.mainloop()

if __name__ == '__main__':
    main()






