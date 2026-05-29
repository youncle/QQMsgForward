"""QQ Forward — 首次运行配置向导"""
import copy
import json
import os
import sys
import tkinter as tk
from tkinter import ttk


def get_base_dir():
    """获取应用根目录"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


DEFAULT_CONFIG = {
    'robot_qq': 0,
    'forward_rules': {},
    'llbot_api': 'http://127.0.0.1:3000',
    'llbot_token': '',
    'filter': {
        'qrcode': {
            'enabled': True,
            'keywords': [
                '添加', '扫码', '扫一扫', '扫描', '联系人',
                'VX', 'v:', '微信', '私聊',
            ],
            'mode': 'image_with_keyword',
            'block_pure_image': True,
        },
        'contact': {
            'enabled': True,
            'patterns': {
                'phone': '1[3-9]\\d{9}',
                'qq': '(?<!\\d)[1-9]\\d{8,9}(?!\\d)',
                'wechat': 'wxid_[a-z0-9]+',
                'email': '[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}',
            },
            'keywords': [
                'QQ', '微信', '飞书', '续费', '费用', 'VX', 'v:',
                '钉钉', '联系人', '我的Q', '我的V', '联系我',
                '加好友', '私聊我', '加我',
            ],
        },
        'log_only': False,
    },
    'forward': {
        'duplicate_window': 5,
        'send_interval': 1.0,
    },
}


def validate_qq_number(value: str) -> bool:
    """QQ 号纯数字且至少 5 位，支持逗号分隔多个"""
    parts = [v.strip() for v in value.replace("，", ",").split(",") if v.strip()]
    if not parts:
        return False
    return all(p.isdigit() and len(p) >= 5 for p in parts)


def generate_config(robot_qq: str, forward_rules: dict, filter_enabled: bool) -> dict:
    """根据向导输入生成完整配置 dict"""
    if not validate_qq_number(robot_qq):
        raise ValueError(f'无效的 QQ 号: {robot_qq}')
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    cfg['robot_qq'] = [int(v.strip()) for v in robot_qq.replace('，', ',').split(',') if v.strip()]
    cfg['forward_rules'] = forward_rules
    if not filter_enabled:
        cfg['filter']['qrcode']['enabled'] = False
        cfg['filter']['contact']['enabled'] = False
    return cfg


def save_config(cfg: dict, path: str) -> None:
    """原子写入配置文件"""
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def run_wizard() -> dict | None:
    """运行配置向导，返回生成的 config dict；用户取消则返回 None"""
    root = tk.Tk()
    root.title('QQ Forward — 首次配置')
    root.resizable(False, False)
    root.configure(bg='#f5f5f5')

    # 居中窗口
    win_w, win_h = 480, 400
    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()
    x = (screen_w - win_w) // 2
    y = (screen_h - win_h) // 2
    root.geometry(f'{win_w}x{win_h}+{x}+{y}')

    result: dict | None = None
    pages = {}
    current_page = [0]

    # ---- Shared state ----
    qq_var = tk.StringVar()
    qq_error = tk.StringVar()
    rules: dict[str, list[str]] = {}
    filter_var = tk.BooleanVar(value=True)

    container = ttk.Frame(root)
    container.pack(fill='both', expand=True)

    # ---- Page 1: Welcome ----
    p1 = ttk.Frame(container)
    p1.columnconfigure(0, weight=1)
    ttk.Label(p1, text='欢迎使用 QQ 消息转发', font=('微软雅黑', 14, 'bold')).grid(
        row=0, column=0, pady=(60, 10))
    ttk.Label(p1, text='此向导将帮助您完成首次配置', font=('微软雅黑', 10)).grid(
        row=1, column=0, pady=5)
    ttk.Label(p1, text='整个过程只需 1-2 分钟', font=('微软雅黑', 10)).grid(
        row=2, column=0, pady=5)
    ttk.Button(p1, text='下一步 →', command=lambda: show_page(1)).grid(
        row=3, column=0, pady=(40, 10))
    pages[0] = p1

    # ---- Page 2: QQ Number ----
    p2 = ttk.Frame(container)
    p2.columnconfigure(0, weight=1)
    ttk.Label(p2, text='请输入机器人 QQ 号', font=('微软雅黑', 12, 'bold')).grid(
        row=0, column=0, pady=(60, 15), columnspan=2)
    ttk.Label(p2, text='即您的 QQ 机器人账号，用于区分自身消息', font=('微软雅黑', 9)).grid(
        row=1, column=0, pady=(0, 15), columnspan=2)

    qq_entry = ttk.Entry(p2, textvariable=qq_var, width=30, font=('微软雅黑', 11))
    qq_entry.grid(row=2, column=0, columnspan=2, pady=5)
    qq_label = ttk.Label(p2, textvariable=qq_error, foreground='red')
    qq_label.grid(row=3, column=0, columnspan=2, pady=5)

    def validate_and_next():
        val = qq_var.get().strip()
        if not val:
            qq_error.set('请输入机器人 QQ 号')
        elif not validate_qq_number(val):
            qq_error.set('QQ 号必须是纯数字，至少 5 位')
        else:
            qq_error.set('')
            show_page(2)

    btn_frame_2 = ttk.Frame(p2)
    btn_frame_2.grid(row=4, column=0, columnspan=2, pady=(30, 10))
    ttk.Button(btn_frame_2, text='← 上一步', command=lambda: show_page(0)).pack(side='left', padx=5)
    ttk.Button(btn_frame_2, text='下一步 →', command=validate_and_next).pack(side='left', padx=5)
    pages[1] = p2

    # ---- Page 3: Forward Rules ----
    p3 = ttk.Frame(container)
    p3.columnconfigure(0, weight=1)
    ttk.Label(p3, text='配置消息转发规则', font=('微软雅黑', 12, 'bold')).grid(
        row=0, column=0, pady=(40, 10), columnspan=2)
    ttk.Label(p3, text='设置哪些群的消息自动转发到哪些群（可选，稍后也能加）',
              font=('微软雅黑', 9)).grid(row=1, column=0, pady=(0, 10), columnspan=2)

    rule_frame = ttk.Frame(p3)
    rule_frame.grid(row=2, column=0, columnspan=2, pady=5)

    ttk.Label(rule_frame, text='源群 QQ:').grid(row=0, column=0, sticky='w', padx=2)
    src_entry = ttk.Entry(rule_frame, width=18)
    src_entry.grid(row=0, column=1, padx=2)

    ttk.Label(rule_frame, text='目标群:').grid(row=0, column=2, sticky='w', padx=2)
    dst_entry = ttk.Entry(rule_frame, width=18)
    dst_entry.grid(row=0, column=3, padx=2)

    ttk.Button(rule_frame, text='添加', command=lambda: add_rule()).grid(
        row=0, column=4, padx=5)

    rules_list = tk.Listbox(p3, height=4, width=55)
    rules_list.grid(row=3, column=0, columnspan=2, pady=5)

    ttk.Button(p3, text='删除选中规则', command=lambda: del_rule()).grid(
        row=4, column=0, columnspan=2, pady=2)

    def refresh_list():
        rules_list.delete(0, 'end')
        for src, dsts in rules.items():
            rules_list.insert('end', f'{src} → {", ".join(dsts)}')

    def add_rule():
        src = src_entry.get().strip()
        dsts = [d.strip() for d in dst_entry.get().split(',') if d.strip()]
        if src and dsts:
            rules[src] = dsts
            refresh_list()
            src_entry.delete(0, 'end')
            dst_entry.delete(0, 'end')

    def del_rule():
        sel = rules_list.curselection()
        if sel:
            text = rules_list.get(sel[0])
            src = text.split(' → ')[0]
            if src in rules:
                del rules[src]
            refresh_list()

    btn_frame_3 = ttk.Frame(p3)
    btn_frame_3.grid(row=5, column=0, columnspan=2, pady=10)
    ttk.Button(btn_frame_3, text='← 上一步', command=lambda: show_page(1)).pack(side='left', padx=5)
    ttk.Button(btn_frame_3, text='下一步 →', command=lambda: show_page(3)).pack(side='left', padx=5)
    pages[2] = p3

    # ---- Page 4: Filter & Finish ----
    p4 = ttk.Frame(container)
    p4.columnconfigure(0, weight=1)
    ttk.Label(p4, text='消息过滤设置', font=('微软雅黑', 12, 'bold')).grid(
        row=0, column=0, pady=(60, 15), columnspan=2)

    ttk.Radiobutton(p4, text='开启过滤（推荐）— 自动拦截二维码广告、联系方式等',
                    variable=filter_var, value=True).grid(
        row=1, column=0, columnspan=2, sticky='w', pady=5, padx=40)
    ttk.Radiobutton(p4, text='暂时关闭 — 所有消息都会转发',
                    variable=filter_var, value=False).grid(
        row=2, column=0, columnspan=2, sticky='w', pady=5, padx=40)

    ttk.Label(p4, text='配置可在启动后通过托盘菜单「设置」随时修改',
              font=('微软雅黑', 8), foreground='gray').grid(
        row=3, column=0, columnspan=2, pady=(20, 10))

    btn_frame_4 = ttk.Frame(p4)
    btn_frame_4.grid(row=4, column=0, columnspan=2, pady=10)
    ttk.Button(btn_frame_4, text='← 上一步', command=lambda: show_page(2)).pack(side='left', padx=5)
    ttk.Button(btn_frame_4, text='✓ 完成配置', command=lambda: on_finish()).pack(side='left', padx=5)
    pages[3] = p4

    # ---- Page Navigation ----
    def show_page(idx):
        for i, page in pages.items():
            page.grid_forget()
        pages[idx].grid(row=0, column=0, sticky='nsew')
        current_page[0] = idx

    def on_finish():
        nonlocal result
        result = generate_config(
            robot_qq=qq_var.get().strip(),
            forward_rules=rules,
            filter_enabled=filter_var.get(),
        )
        root.destroy()

    # Show first page
    show_page(0)

    # Modal loop
    root.mainloop()
    return result
