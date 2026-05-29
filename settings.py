"""QQ消息转发 — 设置界面（可嵌入 Frame）"""
import json
import os
import tkinter as tk
from tkinter import ttk, messagebox

from wizard import get_base_dir

SCRIPT_DIR = get_base_dir()
CONFIG_PATH = os.path.join(SCRIPT_DIR, 'config.json')

MODE_DESCRIPTIONS = {
    '仅关键词图片': '仅拦截同时包含图片和关键词的消息',
    '拦截纯图片': '额外拦截无文字说明的纯图片消息',
    '拦截所有图片': '拦截所有含图片的消息',
}


def load_config():
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_config(data):
    tmp = CONFIG_PATH + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, CONFIG_PATH)


def create_forward_frame(parent, cfg=None):
    """创建转发规则设置界面 Frame，可嵌入 Notebook 等容器"""
    if cfg is None:
        cfg = load_config()
    frame = ttk.Frame(parent, padding=(5, 10))

    pad = {'padx': 0, 'pady': 5}

    # ===== 机器人QQ =====
    frm_qq = ttk.LabelFrame(frame, text='机器人QQ', padding=10)
    frm_qq.pack(fill='x', **pad)

    robot_qqs = cfg.get('robot_qq', [])
    if isinstance(robot_qqs, int):
        robot_qqs = [robot_qqs]

    ttk.Label(frm_qq, text='QQ号码（多个用逗号分隔）').pack(anchor='w')
    qq_entry = ttk.Entry(frm_qq, width=60)
    qq_entry.pack(fill='x', padx=0, pady=3)
    qq_entry.insert(0, ', '.join(str(q) for q in robot_qqs))

    ttk.Label(frm_qq, text='注：修改后需重启服务生效，端口按顺序自动分配。').pack(anchor='w')

    # ===== 转发规则 =====
    frm_rules = ttk.LabelFrame(frame, text='转发规则', padding=10)
    frm_rules.pack(fill='x', **pad)

    rules = cfg.get('forward_rules', {})

    # 迁移旧格式 → 新格式
    for src, val in list(rules.items()):
        if isinstance(val, list):
            rules[src] = {'targets': val, 'note': ''}

    # 规则源键顺序跟踪（listbox index → src key）
    _src_keys = []

    ttk.Label(frm_rules, text='源群').grid(row=0, column=0, sticky='w')
    src_entry = ttk.Entry(frm_rules, width=80)
    src_entry.grid(row=0, column=1, sticky='ew', **pad)

    ttk.Label(frm_rules, text='目标群（逗号分隔）').grid(row=1, column=0, sticky='w')
    dst_entry = ttk.Entry(frm_rules, width=80)
    dst_entry.grid(row=1, column=1, sticky='ew', **pad)

    ttk.Label(frm_rules, text='备注').grid(row=2, column=0, sticky='w')
    note_entry = ttk.Entry(frm_rules, width=80)
    note_entry.grid(row=2, column=1, sticky='ew', **pad)

    rules_list = tk.Listbox(frm_rules, height=10)
    rules_list.grid(row=3, column=0, columnspan=2, sticky='ew', **pad)

    frm_rules.grid_columnconfigure(1, weight=1)

    def refresh_rules_list():
        nonlocal _src_keys
        _src_keys = []
        rules_list.delete(0, 'end')
        for src, rule in rules.items():
            _src_keys.append(src)
            note = rule.get('note', '')
            if note:
                rules_list.insert('end', note)
            else:
                rules_list.insert('end', f'{src} → {", ".join(rule["targets"])}')

    def on_add_rule():
        src = src_entry.get().strip()
        dsts = [d.strip() for d in dst_entry.get().replace('，', ',').split(',') if d.strip()]
        note = note_entry.get().strip()
        if src and dsts:
            rules[src] = {'targets': dsts, 'note': note}
            refresh_rules_list()
            src_entry.delete(0, 'end')
            dst_entry.delete(0, 'end')
            note_entry.delete(0, 'end')

    def on_del_rule():
        sel = rules_list.curselection()
        if sel:
            src = _src_keys[sel[0]]
            if src in rules:
                del rules[src]
            refresh_rules_list()

    def on_list_select(event):
        sel = rules_list.curselection()
        if sel:
            src = _src_keys[sel[0]]
            rule = rules.get(src, {})
            targets = rule.get('targets', [])
            note = rule.get('note', '')
            src_entry.delete(0, 'end')
            src_entry.insert(0, src)
            dst_entry.delete(0, 'end')
            dst_entry.insert(0, ', '.join(targets))
            note_entry.delete(0, 'end')
            note_entry.insert(0, note)

    rules_list.bind('<<ListboxSelect>>', on_list_select)

    btn_frm = ttk.Frame(frm_rules)
    btn_frm.grid(row=4, column=0, columnspan=2, pady=5)
    ttk.Button(btn_frm, text='＋ 添加/更新', command=on_add_rule).pack(side='left', padx=2)
    ttk.Button(btn_frm, text='－ 删除', command=on_del_rule).pack(side='left', padx=2)

    refresh_rules_list()

    # ===== 状态标签 =====
    status_var = tk.StringVar(value='')

    # ===== 按钮 =====
    btn_frame = ttk.Frame(frame)
    btn_frame.pack(fill='x', **pad)

    def on_save():
        cfg['forward_rules'] = rules
        # 保存机器人QQ
        _raw = qq_entry.get().strip()
        _parts = [v.strip() for v in _raw.replace('，', ',').split(',') if v.strip()]
        cfg['robot_qq'] = [int(p) for p in _parts if p.isdigit()]
        try:
            save_config(cfg)
            status_var.set('配置已保存，重启服务后生效。')
            messagebox.showinfo('保存成功', '配置已保存，重启服务后生效。')
        except Exception as e:
            status_var.set(f'保存失败: {e}')
            messagebox.showerror('保存失败', str(e))

    ttk.Button(btn_frame, text='保存', command=on_save).pack(side='right', padx=5)
    ttk.Label(btn_frame, textvariable=status_var, foreground='gray').pack(side='right', padx=10)

    return frame


def create_filter_frame(parent, cfg=None):
    """创建过滤设置界面 Frame，可嵌入 Notebook 等容器"""
    if cfg is None:
        cfg = load_config()
    frame = ttk.Frame(parent, padding=(5, 10))

    pad = {'padx': 0, 'pady': 5}

    cfg.setdefault('filter', {}).setdefault('qrcode', {})
    cfg.setdefault('filter', {}).setdefault('contact', {})

    # ===== QR 码过滤 =====
    qr = cfg['filter']['qrcode']
    frm_qr = ttk.LabelFrame(frame, text='QR码过滤', padding=10)
    frm_qr.pack(fill='x', **pad)

    qr_enabled_cb = tk.Checkbutton(frm_qr, text='启用')
    qr_enabled_cb.pack(anchor='w')
    if qr.get('enabled', True):
        qr_enabled_cb.select()
    else:
        qr_enabled_cb.deselect()

    # 拦截模式下拉框
    MODE_OPTIONS = {
        'image_with_keyword': '仅关键词图片',
        'block_pure_image': '拦截纯图片',
        'block_all_images': '拦截所有图片',
    }
    MODE_DISPLAY = list(MODE_OPTIONS.values())
    MODE_REVERSE = {v: k for k, v in MODE_OPTIONS.items()}
    frm_mode = ttk.Frame(frm_qr)
    frm_mode.pack(fill='x', **pad)
    ttk.Label(frm_mode, text='拦截模式').pack(side='left')
    stored_mode = qr.get('mode', 'image_with_keyword')
    display_mode = MODE_OPTIONS.get(stored_mode, MODE_OPTIONS['image_with_keyword'])
    mode_combo = ttk.Combobox(frm_mode, width=24, values=MODE_DISPLAY, state='readonly')
    mode_combo.set(display_mode)
    mode_combo.pack(side='left', padx=(5, 0))

    # 确保 Combobox 当前选中项与配置一致
    try:
        mode_combo.current(MODE_DISPLAY.index(display_mode))
    except ValueError:
        pass

    # 拦截模式说明标签
    desc_label = ttk.Label(frm_mode, text=MODE_DESCRIPTIONS.get(display_mode, ''), foreground='gray', width=45)

    def on_mode_change(*args):
        selected = mode_combo.get()
        desc_label.config(text=MODE_DESCRIPTIONS.get(selected, ''))

    mode_combo.bind('<<ComboboxSelected>>', on_mode_change)
    desc_label.pack(side='left', padx=(5, 0))

    ttk.Label(frm_qr, text='关键词（逗号分隔）').pack(anchor='w')
    qr_kw_entry = ttk.Entry(frm_qr, width=60)
    qr_kw_entry.pack(fill='x', **pad)
    qr_kw_entry.insert(0, ', '.join(qr.get('keywords', [])))

    # ===== QR 解码（B方案）=====
    frm_decode = ttk.LabelFrame(frm_qr, text='QR码图像解码', padding=5)
    frm_decode.pack(fill='x', pady=(5, 0))

    decode_enabled_cb = tk.Checkbutton(frm_decode, text='启用真·QR码解码（需 pyzbar）')
    decode_enabled_cb.pack(anchor='w')
    if qr.get('decode_enabled', False):
        decode_enabled_cb.select()
    else:
        decode_enabled_cb.deselect()

    frm_decode_row = ttk.Frame(frm_decode)
    frm_decode_row.pack(fill='x', pady=(2, 0))
    ttk.Label(frm_decode_row, text='下载超时(秒)').pack(side='left')
    decode_timeout_sp = ttk.Spinbox(frm_decode_row, from_=1, to=10, width=5)
    decode_timeout_sp.pack(side='left', padx=(5, 15))
    decode_timeout_sp.set(str(qr.get('decode_timeout', 3)))

    ttk.Label(frm_decode, text='解码内容拦截关键词（逗号分隔）').pack(anchor='w')
    decode_patterns_entry = ttk.Entry(frm_decode, width=60)
    decode_patterns_entry.pack(fill='x', **pad)
    decode_patterns_entry.insert(0, ', '.join(qr.get('decode_block_patterns', [])))

    ttk.Label(frm_decode, text='可疑域名（逗号分隔，如 bad.com）').pack(anchor='w')
    decode_domains_entry = ttk.Entry(frm_decode, width=60)
    decode_domains_entry.pack(fill='x', **pad)
    decode_domains_entry.insert(0, ', '.join(qr.get('decode_suspicious_domains', [])))

    # ===== 联系方式过滤 =====
    ct = cfg['filter']['contact']
    frm_ct = ttk.LabelFrame(frame, text='联系方式过滤', padding=10)
    frm_ct.pack(fill='x', **pad)

    ct_enabled_cb = tk.Checkbutton(frm_ct, text='启用')
    ct_enabled_cb.pack(anchor='w')
    if ct.get('enabled', True):
        ct_enabled_cb.select()
    else:
        ct_enabled_cb.deselect()

    ttk.Label(frm_ct, text='关键词（逗号分隔）').pack(anchor='w')
    ct_kw_entry = ttk.Entry(frm_ct, width=60)
    ct_kw_entry.pack(fill='x', **pad)
    ct_kw_entry.insert(0, ', '.join(ct.get('keywords', [])))

    log_only_cb = tk.Checkbutton(frm_ct, text='仅记录不拦截（log_only）')
    log_only_cb.pack(anchor='w')
    if cfg['filter'].get('log_only', False):
        log_only_cb.select()
    else:
        log_only_cb.deselect()

    # ===== 状态标签 =====
    status_var = tk.StringVar(value='')

    # ===== 按钮 =====
    btn_frame = ttk.Frame(frame)
    btn_frame.pack(fill='x', **pad)

    def _cb_checked(cb):
        return bool(int(cb.getvar(cb['variable'])))

    def on_save():
        cfg['filter']['qrcode']['enabled'] = _cb_checked(qr_enabled_cb)
        cfg['filter']['qrcode']['mode'] = MODE_REVERSE.get(mode_combo.get(), 'image_with_keyword')
        cfg['filter']['qrcode']['keywords'] = [
            k.strip() for k in qr_kw_entry.get().split(',') if k.strip()
        ]
        cfg['filter']['qrcode']['decode_enabled'] = _cb_checked(decode_enabled_cb)
        cfg['filter']['qrcode']['decode_timeout'] = int(decode_timeout_sp.get())
        cfg['filter']['qrcode']['decode_block_patterns'] = [
            k.strip() for k in decode_patterns_entry.get().split(',') if k.strip()
        ]
        cfg['filter']['qrcode']['decode_suspicious_domains'] = [
            k.strip() for k in decode_domains_entry.get().split(',') if k.strip()
        ]
        cfg['filter']['contact']['enabled'] = _cb_checked(ct_enabled_cb)
        cfg['filter']['contact']['keywords'] = [
            k.strip() for k in ct_kw_entry.get().split(',') if k.strip()
        ]
        cfg['filter']['log_only'] = _cb_checked(log_only_cb)
        try:
            save_config(cfg)
            status_var.set('配置已保存，重启服务后生效。')
            messagebox.showinfo('保存成功', '配置已保存，重启服务后生效。')
        except Exception as e:
            status_var.set(f'保存失败: {e}')
            messagebox.showerror('保存失败', str(e))

    ttk.Button(btn_frame, text='保存', command=on_save).pack(side='right', padx=5)
    ttk.Label(btn_frame, textvariable=status_var, foreground='gray').pack(side='right', padx=10)

    return frame
