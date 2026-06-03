"""QQ消息转发 — 过滤规则设置界面"""
import tkinter as tk
from tkinter import ttk, messagebox

from .base import load_config, save_config, MODE_DESCRIPTIONS

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

    # ===== 试运行模式 =====
    frm_log = ttk.LabelFrame(frame, text='试运行模式', padding=10)
    frm_log.pack(fill='x', **pad)

    log_only_cb = tk.Checkbutton(frm_log, text='仅日志记录不拦截，即：QR码过滤、联系方式过滤过滤规则无效')
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
            status_var.set('配置已保存，立即生效。')
            messagebox.showinfo('保存成功', '配置已保存，立即生效。')
        except Exception as e:
            status_var.set(f'保存失败: {e}')
            messagebox.showerror('保存失败', str(e))

    ttk.Button(btn_frame, text='保存', command=on_save).pack(side='right', padx=5)
    ttk.Label(btn_frame, textvariable=status_var, foreground='gray').pack(side='right', padx=10)

    return frame


