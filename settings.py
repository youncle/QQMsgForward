"""QQ消息转发 — 设置窗口"""
import json
import os
import tkinter as tk
from tkinter import ttk, messagebox

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, 'config.json')


def load_config():
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_config(data):
    tmp = CONFIG_PATH + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, CONFIG_PATH)


def open_settings():
    """打开设置窗口（可在非主线程中调用）"""
    cfg = load_config()
    root = tk.Tk()
    root.title('QQ消息转发 - 设置')
    root.resizable(False, False)

    pad = {'padx': 10, 'pady': 5}

    # ===== 转发规则 =====
    frm_rules = ttk.LabelFrame(root, text='转发规则', padding=10)
    frm_rules.pack(fill='x', **pad)

    rules = cfg.get('forward_rules', {})
    cfg.setdefault('filter', {}).setdefault('qrcode', {})
    cfg.setdefault('filter', {}).setdefault('contact', {})

    ttk.Label(frm_rules, text='源群').grid(row=0, column=0, sticky='w')
    src_entry = ttk.Entry(frm_rules, width=20)
    src_entry.grid(row=0, column=1, **pad)

    ttk.Label(frm_rules, text='目标群（逗号分隔）').grid(row=1, column=0, sticky='w')
    dst_entry = ttk.Entry(frm_rules, width=50)
    dst_entry.grid(row=1, column=1, **pad)

    rules_list = tk.Listbox(frm_rules, height=4, width=60)
    rules_list.grid(row=2, column=0, columnspan=2, **pad)

    def refresh_rules_list():
        rules_list.delete(0, 'end')
        for src, dsts in rules.items():
            rules_list.insert('end', f'{src} → {", ".join(dsts)}')

    def on_add_rule():
        src = src_entry.get().strip()
        dsts = [d.strip() for d in dst_entry.get().split(',') if d.strip()]
        if src and dsts:
            rules[src] = dsts
            refresh_rules_list()
            src_entry.delete(0, 'end')
            dst_entry.delete(0, 'end')

    def on_del_rule():
        sel = rules_list.curselection()
        if sel:
            text = rules_list.get(sel[0])
            src = text.split(' → ')[0]
            if src in rules:
                del rules[src]
            refresh_rules_list()

    def on_list_select(event):
        sel = rules_list.curselection()
        if sel:
            text = rules_list.get(sel[0])
            src, dsts_str = text.split(' → ', 1)
            src_entry.delete(0, 'end')
            src_entry.insert(0, src)
            dst_entry.delete(0, 'end')
            dst_entry.insert(0, ', '.join(rules.get(src, [])))

    rules_list.bind('<<ListboxSelect>>', on_list_select)

    btn_frm = ttk.Frame(frm_rules)
    btn_frm.grid(row=3, column=0, columnspan=2, pady=5)
    ttk.Button(btn_frm, text='＋ 添加/更新', command=on_add_rule).pack(side='left', padx=2)
    ttk.Button(btn_frm, text='－ 删除', command=on_del_rule).pack(side='left', padx=2)

    refresh_rules_list()

    # ===== QR 码过滤 =====
    qr = cfg['filter']['qrcode']
    frm_qr = ttk.LabelFrame(root, text='QR码过滤', padding=10)
    frm_qr.pack(fill='x', **pad)

    qr_enabled = tk.BooleanVar(value=qr.get('enabled', True))
    ttk.Checkbutton(frm_qr, text='启用', variable=qr_enabled).pack(anchor='w')

    ttk.Label(frm_qr, text='关键词（逗号分隔）').pack(anchor='w')
    qr_kw_entry = ttk.Entry(frm_qr, width=60)
    qr_kw_entry.pack(fill='x', **pad)
    qr_kw_entry.insert(0, ', '.join(qr.get('keywords', [])))

    qr_block = tk.BooleanVar(value=qr.get('block_pure_image', False))
    ttk.Checkbutton(frm_qr, text='拦截无文字的纯图片', variable=qr_block).pack(anchor='w')

    # ===== 联系方式过滤 =====
    ct = cfg['filter']['contact']
    frm_ct = ttk.LabelFrame(root, text='联系方式过滤', padding=10)
    frm_ct.pack(fill='x', **pad)

    ct_enabled = tk.BooleanVar(value=ct.get('enabled', True))
    ttk.Checkbutton(frm_ct, text='启用', variable=ct_enabled).pack(anchor='w')

    ttk.Label(frm_ct, text='关键词（逗号分隔）').pack(anchor='w')
    ct_kw_entry = ttk.Entry(frm_ct, width=60)
    ct_kw_entry.pack(fill='x', **pad)
    ct_kw_entry.insert(0, ', '.join(ct.get('keywords', [])))

    log_only = tk.BooleanVar(value=cfg['filter'].get('log_only', False))
    ttk.Checkbutton(frm_ct, text='仅记录不拦截（log_only）', variable=log_only).pack(anchor='w')

    # ===== 按钮 =====
    btn_frame = ttk.Frame(root)
    btn_frame.pack(fill='x', **pad)

    def on_save():
        cfg['forward_rules'] = rules
        cfg['filter']['qrcode']['enabled'] = qr_enabled.get()
        cfg['filter']['qrcode']['keywords'] = [
            k.strip() for k in qr_kw_entry.get().split(',') if k.strip()
        ]
        cfg['filter']['qrcode']['block_pure_image'] = qr_block.get()
        cfg['filter']['contact']['enabled'] = ct_enabled.get()
        cfg['filter']['contact']['keywords'] = [
            k.strip() for k in ct_kw_entry.get().split(',') if k.strip()
        ]
        cfg['filter']['log_only'] = log_only.get()
        try:
            save_config(cfg)
            messagebox.showinfo('保存成功', '配置已保存，重启服务后生效。', parent=root)
        except Exception as e:
            messagebox.showerror('保存失败', str(e), parent=root)

    ttk.Button(btn_frame, text='保存', command=on_save).pack(side='right', padx=5)
    ttk.Button(btn_frame, text='取消', command=root.destroy).pack(side='right', padx=5)

    root.mainloop()


if __name__ == '__main__':
    open_settings()
