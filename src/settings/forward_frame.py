"""QQ消息转发 — 转发规则设置界面"""
import tkinter as tk
from tkinter import ttk, messagebox

from .base import load_config, save_config

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

    ttk.Label(frm_qq, text='注：修改后需重启服务生效，启动后自动检测QQ登录与端口对应关系。').pack(anchor='w')

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
        # 记录旧值，判断 robot_qq 是否有变动
        _old_qq = cfg.get('robot_qq', [])
        if isinstance(_old_qq, int):
            _old_qq = [_old_qq]
        _old_qq_set = set(str(q) for q in _old_qq)

        cfg['forward_rules'] = rules
        # 保存机器人QQ
        _raw = qq_entry.get().strip()
        _parts = [v.strip() for v in _raw.replace('，', ',').split(',') if v.strip()]
        cfg['robot_qq'] = [int(p) for p in _parts if p.isdigit()]
        _new_qq_set = set(str(p) for p in cfg['robot_qq'])

        _qq_changed = _old_qq_set != _new_qq_set

        try:
            save_config(cfg)
            if _qq_changed:
                _msg = '配置已保存，机器人QQ号改动需重启服务后生效。'
            else:
                _msg = '配置已保存，立即生效。'
            status_var.set(_msg)
            messagebox.showinfo('保存成功', _msg)
        except Exception as e:
            status_var.set(f'保存失败: {e}')
            messagebox.showerror('保存失败', str(e))

    ttk.Button(btn_frame, text='保存', command=on_save).pack(side='right', padx=5)
    ttk.Label(btn_frame, textvariable=status_var, foreground='gray').pack(side='right', padx=10)

    return frame

