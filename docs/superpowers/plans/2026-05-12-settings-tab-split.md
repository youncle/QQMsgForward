# 设置标签页拆分 实施方案

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将设置页面从 2 个标签页（状态/设置）拆分为 3 个标签页（状态/转发/过滤）

**Architecture:** 在 settings.py 中将 `create_settings_frame()` 拆为 `create_forward_frame()` 和 `create_filter_frame()` 两个独立函数，tray.py 的 Notebook 从 2 个 tab 改为 3 个 tab。公用 load/save 函数保持不变。

**Tech Stack:** Python tkinter

---

### Task 1: 拆分 settings.py — 创建 create_forward_frame

**Files:**
- Modify: `settings.py`

- [ ] **Step 1: 将 create_settings_frame 重命名为 create_forward_frame，只保留转发规则部分**

将 `settings.py` 中 `create_settings_frame` 函数改为 `create_forward_frame`，删除 QR码过滤、QR码图像解码、联系方式过滤相关的 UI 代码，只保留转发规则 + 保存按钮 + 状态标签。

完整替换后的函数：

```python
def create_forward_frame(parent):
    """转发规则设置 Frame"""
    cfg = load_config()
    frame = ttk.Frame(parent, padding=10)

    pad = {'padx': 10, 'pady': 5}

    # ===== 转发规则 =====
    frm_rules = ttk.LabelFrame(frame, text='转发规则', padding=10)
    frm_rules.pack(fill='x', **pad)

    rules = cfg.get('forward_rules', {})
    cfg.setdefault('filter', {}).setdefault('qrcode', {})
    cfg.setdefault('filter', {}).setdefault('contact', {})

    # 迁移旧格式 → 新格式
    for src, val in list(rules.items()):
        if isinstance(val, list):
            rules[src] = {'targets': val, 'note': ''}

    # 规则源键顺序跟踪（listbox index → src key）
    _src_keys = []

    ttk.Label(frm_rules, text='源群').grid(row=0, column=0, sticky='w')
    src_entry = ttk.Entry(frm_rules, width=20)
    src_entry.grid(row=0, column=1, **pad)

    ttk.Label(frm_rules, text='目标群（逗号分隔）').grid(row=1, column=0, sticky='w')
    dst_entry = ttk.Entry(frm_rules, width=50)
    dst_entry.grid(row=1, column=1, **pad)

    ttk.Label(frm_rules, text='备注').grid(row=2, column=0, sticky='w')
    note_entry = ttk.Entry(frm_rules, width=50)
    note_entry.grid(row=2, column=1, **pad)

    rules_list = tk.Listbox(frm_rules, height=5, width=60)
    rules_list.grid(row=3, column=0, columnspan=2, **pad)

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
        dsts = [d.strip() for d in dst_entry.get().split(',') if d.strip()]
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
        try:
            save_config(cfg)
            status_var.set('配置已保存，重启服务后生效。')
        except Exception as e:
            status_var.set(f'保存失败: {e}')

    ttk.Button(btn_frame, text='保存', command=on_save).pack(side='right', padx=5)
    ttk.Label(btn_frame, textvariable=status_var, foreground='gray').pack(side='right', padx=10)

    return frame
```

- [ ] **Step 2: 验证 — 检查语法正确性**

```bash
python -c "import ast; ast.parse(open('settings.py').read()); print('Syntax OK')"
```

预期输出: `Syntax OK`

- [ ] **Step 3: Commit**

```bash
git add settings.py
git commit -m "refactor(settings): extract create_forward_frame from create_settings_frame"
```

---

### Task 2: 新增 create_filter_frame 函数

**Files:**
- Modify: `settings.py`

- [ ] **Step 1: 在 settings.py 中添加 create_filter_frame 函数**

在 `create_forward_frame` 函数之后（`return frame` 之后空一行），添加：

```python
def create_filter_frame(parent):
    """过滤设置 Frame（QR码 + 联系方式）"""
    cfg = load_config()
    frame = ttk.Frame(parent, padding=10)

    pad = {'padx': 10, 'pady': 5}

    cfg.setdefault('filter', {}).setdefault('qrcode', {})
    cfg.setdefault('filter', {}).setdefault('contact', {})

    # ===== QR 码过滤 =====
    qr = cfg['filter']['qrcode']
    frm_qr = ttk.LabelFrame(frame, text='QR码过滤', padding=10)
    frm_qr.pack(fill='x', **pad)

    qr_enabled = tk.BooleanVar(value=qr.get('enabled', True))
    ttk.Checkbutton(frm_qr, text='启用', variable=qr_enabled).pack(anchor='w')

    # 拦截模式下拉框
    frm_mode = ttk.Frame(frm_qr)
    frm_mode.pack(fill='x', **pad)
    ttk.Label(frm_mode, text='拦截模式').pack(side='left')
    mode_var = tk.StringVar(value=qr.get('mode', 'image_with_keyword'))
    mode_combo = ttk.Combobox(frm_mode, textvariable=mode_var, width=24,
                              values=['image_with_keyword', 'block_pure_image', 'block_all_images'],
                              state='readonly')
    mode_combo.pack(side='left', padx=(5, 0))

    ttk.Label(frm_qr, text='关键词（逗号分隔）').pack(anchor='w')
    qr_kw_entry = ttk.Entry(frm_qr, width=60)
    qr_kw_entry.pack(fill='x', **pad)
    qr_kw_entry.insert(0, ', '.join(qr.get('keywords', [])))

    # ===== QR 解码 =====
    frm_decode = ttk.LabelFrame(frm_qr, text='QR码图像解码', padding=5)
    frm_decode.pack(fill='x', pady=(5, 0))

    decode_enabled = tk.BooleanVar(value=qr.get('decode_enabled', False))
    ttk.Checkbutton(frm_decode, text='启用真·QR码解码（需 pyzbar）', variable=decode_enabled).pack(anchor='w')

    frm_decode_row = ttk.Frame(frm_decode)
    frm_decode_row.pack(fill='x', pady=(2, 0))
    ttk.Label(frm_decode_row, text='下载超时(秒)').pack(side='left')
    decode_timeout = tk.IntVar(value=qr.get('decode_timeout', 3))
    ttk.Spinbox(frm_decode_row, from_=1, to=10, textvariable=decode_timeout, width=5).pack(side='left', padx=(5, 15))

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

    ct_enabled = tk.BooleanVar(value=ct.get('enabled', True))
    ttk.Checkbutton(frm_ct, text='启用', variable=ct_enabled).pack(anchor='w')

    ttk.Label(frm_ct, text='关键词（逗号分隔）').pack(anchor='w')
    ct_kw_entry = ttk.Entry(frm_ct, width=60)
    ct_kw_entry.pack(fill='x', **pad)
    ct_kw_entry.insert(0, ', '.join(ct.get('keywords', [])))

    log_only = tk.BooleanVar(value=cfg['filter'].get('log_only', False))
    ttk.Checkbutton(frm_ct, text='仅记录不拦截（log_only）', variable=log_only).pack(anchor='w')

    # ===== 状态标签 =====
    status_var = tk.StringVar(value='')

    # ===== 按钮 =====
    btn_frame = ttk.Frame(frame)
    btn_frame.pack(fill='x', **pad)

    def on_save():
        cfg['filter']['qrcode']['enabled'] = qr_enabled.get()
        cfg['filter']['qrcode']['mode'] = mode_var.get()
        cfg['filter']['qrcode']['keywords'] = [
            k.strip() for k in qr_kw_entry.get().split(',') if k.strip()
        ]
        cfg['filter']['qrcode']['decode_enabled'] = decode_enabled.get()
        cfg['filter']['qrcode']['decode_timeout'] = decode_timeout.get()
        cfg['filter']['qrcode']['decode_block_patterns'] = [
            k.strip() for k in decode_patterns_entry.get().split(',') if k.strip()
        ]
        cfg['filter']['qrcode']['decode_suspicious_domains'] = [
            k.strip() for k in decode_domains_entry.get().split(',') if k.strip()
        ]
        cfg['filter']['contact']['enabled'] = ct_enabled.get()
        cfg['filter']['contact']['keywords'] = [
            k.strip() for k in ct_kw_entry.get().split(',') if k.strip()
        ]
        cfg['filter']['log_only'] = log_only.get()
        try:
            save_config(cfg)
            status_var.set('配置已保存，重启服务后生效。')
        except Exception as e:
            status_var.set(f'保存失败: {e}')

    ttk.Button(btn_frame, text='保存', command=on_save).pack(side='right', padx=5)
    ttk.Label(btn_frame, textvariable=status_var, foreground='gray').pack(side='right', padx=10)

    return frame
```

- [ ] **Step 2: 删除旧的 create_settings_frame 函数和 __main__ 入口**

删除 `create_settings_frame` 函数（已在 Task 1 中替换为 `create_forward_frame`）。
删除文件末尾的 `if __name__ == '__main__':` 独立窗口入口（4 行）。

- [ ] **Step 3: 验证语法**

```bash
python -c "import ast; ast.parse(open('settings.py').read()); print('Syntax OK')"
```

预期输出: `Syntax OK`

- [ ] **Step 4: Commit**

```bash
git add settings.py
git commit -m "feat(settings): add create_filter_frame, remove old combined frame"
```

---

### Task 3: 更新 tray.py — 3 标签页

**Files:**
- Modify: `tray.py:529-530`

- [ ] **Step 1: 替换 Notebook tab 定义**

将 `tray.py` 第 529-530 行：

```python
notebook.add(create_status_tab(notebook), text='状态')
notebook.add(settings_mod.create_settings_frame(notebook), text='设置')
```

替换为：

```python
notebook.add(create_status_tab(notebook), text='状态')
notebook.add(settings_mod.create_forward_frame(notebook), text='转发')
notebook.add(settings_mod.create_filter_frame(notebook), text='过滤')
```

- [ ] **Step 2: 验证语法**

```bash
python -c "import ast; ast.parse(open('tray.py').read()); print('Syntax OK')"
```

预期输出: `Syntax OK`

- [ ] **Step 3: Commit**

```bash
git add tray.py
git commit -m "feat(tray): split settings tab into 转发 and 过滤 tabs"
```

---

### Task 4: 运行现有测试确保无回归

**Files:**
- Test: `tests/test_settings.py`

- [ ] **Step 1: 运行测试**

```bash
python -m pytest tests/test_settings.py -v
```

预期输出: 4 passed

- [ ] **Step 2: 如果测试失败，检查错误并修复**

测试只依赖 `load_config` / `save_config` 函数，这两个函数未修改，预期全部通过。

- [ ] **Step 3: Commit（如果有修复）**

```bash
git add tests/test_settings.py
git commit -m "test(settings): verify tests pass after tab split"
```

---

### Task 5: 手动验证清单

- [ ] **Step 1: 启动主面板，确认 3 个标签页显示正常**

```bash
python -c "import tkinter; print('tkinter available')"
```

人工检查要点：
1. 标签页顺序：状态 → 转发 → 过滤
2. "转发"标签页：转发规则编辑区域 + 保存按钮可见
3. "过滤"标签页：QR码过滤 + QR解码 + 联系方式过滤 + 保存按钮可见
4. "状态"标签页：内容不变
