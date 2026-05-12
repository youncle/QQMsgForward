# 拦截模式下拉列表中文化 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将过滤标签中拦截模式下拉列表的显示文本从英文改为中文，内部存储值不变。

**Architecture:** 在 `settings.py` 中新增显示映射字典，加载时英文→中文，保存时中文→英文。`filter.py` / `wizard.py` / `config.json` 不变。

**Tech Stack:** Python tkinter

---

### Task 1: 添加映射表并修改显示/保存逻辑

**Files:**
- Modify: `settings.py:156-219`

- [ ] **Step 1: 在 `create_filter_frame` 函数内添加映射表**

在 `# 拦截模式下拉框` 注释之后（第156行后），添加映射字典和反向映射：

```python
    # 拦截模式下拉框
    MODE_OPTIONS = {
        'image_with_keyword': '仅关键词图片',
        'block_pure_image': '拦截纯图片',
        'block_all_images': '拦截所有图片',
    }
    MODE_DISPLAY = list(MODE_OPTIONS.values())
    MODE_REVERSE = {v: k for k, v in MODE_OPTIONS.items()}
```

- [ ] **Step 2: 修改加载逻辑，英文值转中文显示**

将第160行的：
```python
    mode_var = tk.StringVar(value=qr.get('mode', 'image_with_keyword'))
```
改为：
```python
    stored_mode = qr.get('mode', 'image_with_keyword')
    display_mode = MODE_OPTIONS.get(stored_mode, MODE_OPTIONS['image_with_keyword'])
    mode_var = tk.StringVar(value=display_mode)
```

- [ ] **Step 3: 修改下拉列表 values 为中文**

将第161-162行的：
```python
    mode_combo = ttk.Combobox(frm_mode, textvariable=mode_var, width=24,
                              values=['image_with_keyword', 'block_pure_image', 'block_all_images'],
                              state='readonly')
```
改为：
```python
    mode_combo = ttk.Combobox(frm_mode, textvariable=mode_var, width=24,
                              values=MODE_DISPLAY,
                              state='readonly')
```

- [ ] **Step 4: 修改保存逻辑，中文值转回英文存储**

将第219行的：
```python
        cfg['filter']['qrcode']['mode'] = mode_var.get()
```
改为：
```python
        cfg['filter']['qrcode']['mode'] = MODE_REVERSE.get(mode_var.get(), 'image_with_keyword')
```

- [ ] **Step 5: 启动程序验证 UI 显示正确**

```bash
python tray.py
```

检查点：
- 打开「过滤」标签，拦截模式下拉显示三个中文选项
- 默认选中「仅关键词图片」
- 切换选项后保存，重启程序，选项保持
- 修改 `config.json` 中 mode 为 `block_all_images`，重启后下拉显示「拦截所有图片」

- [ ] **Step 6: 提交**

```bash
git add settings.py
git commit -m "feat(filter): display intercept mode options in chinese"
```
