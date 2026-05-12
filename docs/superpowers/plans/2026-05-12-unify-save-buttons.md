# Unify Save Buttons into Global Save Bar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Forward 和 Filter 两个 Tab 各自独立的「保存」按钮合并为一个全局保存按钮，统一收集 UI 状态后写入磁盘，消除互相覆盖问题。

**Architecture:** 每个 Tab 暴露 `collect_state()` 函数（挂载为 frame 属性），仅负责将当前 UI 控件值写入 `cfg` 字典，不写磁盘。tray.py 在 Notebook 下方新增一个全局保存栏，调用所有 Tab 的 `collect_state()` 后统一 `save_config()`。去掉各 Tab 内部的保存按钮和状态标签。

**Tech Stack:** Python tkinter + ttk

---

### Task 1: 改造 Forward Tab — 去保存按钮，暴露 collect_state

**Files:**
- Modify: `settings.py:125-142`

- [ ] **Step 1: 去掉保存按钮和状态标签，改为 collect_state**

将 `create_forward_frame` 中 lines 125-139 的按钮区域改为只暴露 `collect_state`：

```python
# settings.py lines 125-142, change from:
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

# to:
    def collect_state():
        cfg['forward_rules'] = rules

    frame.collect_state = collect_state

    return frame
```

注意：`status_var` 和 `btn_frame` 完全移除。`pad` 变量（`{'padx': 0, 'pady': 5}`）如果只在 btn_frame 处使用，删除 `btn_frame` 后不受影响（`pad` 仍被 `frm_rules` 的多处使用）。

- [ ] **Step 2: 验证** — `python -m pytest tests/ -q`，76 tests pass。

- [ ] **Step 3: Commit**

```bash
git add settings.py
git commit -m "refactor(ui): replace forward tab save button with collect_state() on frame"
```

---

### Task 2: 改造 Filter Tab — 去保存按钮，暴露 collect_state

**Files:**
- Modify: `settings.py:244-279`

- [ ] **Step 1: 去掉保存按钮和状态标签，改为 collect_state**

将 `create_filter_frame` 中 lines 244-279 的按钮区域改为只暴露 `collect_state`：

```python
# settings.py lines 244-279, change from:
    # ===== 状态标签 =====
    status_var = tk.StringVar(value='')

    # ===== 按钮 =====
    btn_frame = ttk.Frame(frame)
    btn_frame.pack(fill='x', **pad)

    def on_save():
        cfg['filter']['qrcode']['enabled'] = qr_enabled.get()
        cfg['filter']['qrcode']['mode'] = MODE_REVERSE.get(mode_var.get(), 'image_with_keyword')
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

# to:
    def collect_state():
        cfg['filter']['qrcode']['enabled'] = qr_enabled.get()
        cfg['filter']['qrcode']['mode'] = MODE_REVERSE.get(mode_var.get(), 'image_with_keyword')
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

    frame.collect_state = collect_state

    return frame
```

- [ ] **Step 2: 验证** — `python -m pytest tests/ -q`，76 tests pass。

- [ ] **Step 3: Commit**

```bash
git add settings.py
git commit -m "refactor(ui): replace filter tab save button with collect_state() on frame"
```

---

### Task 3: 在 tray.py 添加全局保存栏

**Files:**
- Modify: `tray.py:592-603`

- [ ] **Step 1: 在 Notebook 下方添加全局保存栏**

```python
# tray.py, after notebook.tab() calls (after line 603), add:

    # ===== 全局保存栏 =====
    save_frame = ttk.Frame(root)
    save_frame.pack(fill='x', padx=5, pady=(0, 5))

    save_status = tk.StringVar(value='')
    ttk.Label(save_frame, textvariable=save_status, foreground='gray').pack(side='right', padx=10)

    def on_global_save():
        for tab in [tab2, tab3]:
            collect = getattr(tab, 'collect_state', None)
            if collect:
                collect()
        try:
            settings_mod.save_config(shared_cfg)
            save_status.set('配置已保存，重启服务后生效。')
        except Exception as e:
            save_status.set(f'保存失败: {e}')

    ttk.Button(save_frame, text='保存配置', command=on_global_save).pack(side='right', padx=5)
```

全局保存按钮依次调用 `tab2.collect_state()` 和 `tab3.collect_state()` 将当前 UI 状态同步到 `shared_cfg`，然后统一写入磁盘。

**注意**：`tab2` 和 `tab3` 需要在 `notebook.add()` 之前保存引用。当前代码中 tab2、tab3 变量已经存在（line 595, 597），无需额外改动。

- [ ] **Step 2: 验证** — `python -m pytest tests/ -q`，76 tests pass。启动应用，修改设置 → 点「保存配置」→ 确认 config.json 更新。

- [ ] **Step 3: Commit**

```bash
git add tray.py
git commit -m "feat(ui): add global save bar replacing per-tab save buttons"
```

---

## 整体验证

- [ ] 启动应用，三个 Tab 均无独立「保存」按钮
- [ ] 底部出现「保存配置」按钮 + 状态标签
- [ ] 修改 Forward 规则 → 全局保存 → config.json 更新
- [ ] 修改 Filter 设置 → 全局保存 → config.json 更新
- [ ] 同时修改两个 Tab → 全局保存 → 两处修改均生效
- [ ] 76 tests pass
