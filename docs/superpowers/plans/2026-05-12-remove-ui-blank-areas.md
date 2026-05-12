# Remove UI Blank Areas Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 去除主程序 UI 左右两侧的空白区域，通过削减外层 padding + 让 Forward 页内容拉伸填充 + 解除窗口最小宽度锁定。

**Architecture:** 修改 `tray.py`（容器/窗口层）和 `settings.py`（Tab 内容层）。垂直间距不变，仅收紧水平方向。

**Tech Stack:** Python tkinter + ttk

---

### Task 1: 削减 tray.py 外层容器水平 padding

**Files:**
- Modify: `tray.py:121`
- Modify: `tray.py:573-574`

- [ ] **Step 1: 修改 Status Tab Frame padding（15 → 左右5）**

```python
# tray.py line 121, change:
frame = ttk.Frame(parent, padding=15)
# to:
frame = ttk.Frame(parent, padding=(5, 15))
```
ttk padding 二元组 = (horizontal, vertical)，所以左右从 15 → 5，上下保持 15。

- [ ] **Step 2: 修改 Notebook padding（5 → 0）**

```python
# tray.py line 573, change:
notebook = ttk.Notebook(root, padding=5)
# to:
notebook = ttk.Notebook(root, padding=0)
```

- [ ] **Step 3: 修改 Notebook pack padx（5 → 0）**

```python
# tray.py line 574, change:
notebook.pack(fill='both', expand=True, padx=5, pady=5)
# to:
notebook.pack(fill='both', expand=True, padx=0, pady=5)
```
去掉水平 pack 边距，垂直 pady=5 保持不变。

- [ ] **Step 4: 验证** — 启动应用，Status 页内容两侧空白明显减少；确认上下间距正常。

- [ ] **Step 5: Commit**

```bash
git add tray.py
git commit -m "fix(ui): reduce outer container horizontal padding from 25px to 5px per side"
```

---

### Task 2: 让 Forward 页内容水平拉伸

**Files:**
- Modify: `settings.py:35`
- Modify: `settings.py:37`
- Modify: `settings.py:55-66`（Entry 和 Listbox 的 sticky）
- Modify: `settings.py:65-66`（添加 grid_columnconfigure）

- [ ] **Step 1: 削减 Forward Tab Frame padding（10 → 左右5）**

```python
# settings.py line 35, change:
frame = ttk.Frame(parent, padding=10)
# to:
frame = ttk.Frame(parent, padding=(5, 10))
```

- [ ] **Step 2: 削减 frm_rules 和 btn_frame 的 pack padx（10 → 0）**

pad 字典的 `padx=10` 会使 frm_rules 和 btn_frame 的 `.pack()` 调用产生左右 10px 空白。改为 0：

```python
# settings.py line 37, change:
pad = {'padx': 10, 'pady': 5}
# to:
pad = {'padx': 0, 'pady': 5}
```

- [ ] **Step 3: 添加 grid_columnconfigure 让第2列拉伸**

在 `frm_rules` 创建后（约 line 40 之后），添加列权重配置。当前需要在 `refresh_rules_list()` 调用之前添加。

```python
# settings.py, after line 66 (rules_list.grid(...)), add:
frm_rules.grid_columnconfigure(1, weight=1)
```

这使第 2 列（Entry 和 Listbox 所在列）获得所有额外水平空间。

- [ ] **Step 4: 修改 Entry sticky='w' → sticky='ew' 使其拉伸**

```python
# settings.py line 55, change:
src_entry.grid(row=0, column=1, sticky='w', **pad)
# to:
src_entry.grid(row=0, column=1, sticky='ew', **pad)

# settings.py line 59, change:
dst_entry.grid(row=1, column=1, sticky='w', **pad)
# to:
dst_entry.grid(row=1, column=1, sticky='ew', **pad)

# settings.py line 63, change:
note_entry.grid(row=2, column=1, sticky='w', **pad)
# to:
note_entry.grid(row=2, column=1, sticky='ew', **pad)
```

- [ ] **Step 5: 修改 Listbox sticky 并移除硬编码 width**

```python
# settings.py line 65, change:
rules_list = tk.Listbox(frm_rules, height=10, width=100)
# to:
rules_list = tk.Listbox(frm_rules, height=10)

# settings.py line 66, change:
rules_list.grid(row=3, column=0, columnspan=2, **pad)
# to:
rules_list.grid(row=3, column=0, columnspan=2, sticky='ew', **pad)
```
Listbox 的 `width=100` 移除以允许自然宽度 + 拉伸。`sticky='ew'` 让它随列拉伸。

- [ ] **Step 6: 验证** — 启动应用，切换到 Forward 页：
  - Entry 输入框应随窗口宽度拉伸
  - Listbox 应填满整行
  - 无右侧大面积空白
  - 确认垂直线性布局无异常

- [ ] **Step 7: Commit**

```bash
git add settings.py
git commit -m "fix(ui): make forward tab content stretch horizontally to fill window"
```

---

### Task 3: 削减 Filter 页水平 padding

**Files:**
- Modify: `settings.py:147`
- Modify: `settings.py:149`

- [ ] **Step 1: 修改 Filter Tab Frame padding（10 → 左右5）**

```python
# settings.py line 147, change:
frame = ttk.Frame(parent, padding=10)
# to:
frame = ttk.Frame(parent, padding=(5, 10))
```

- [ ] **Step 2: 修改 Filter 页 pad 字典 padx（10 → 0）**

Filter 页有自己的本地 `pad` 字典（`create_filter_frame` 函数内），独立于 Forward 页：

```python
# settings.py line 149, change:
pad = {'padx': 10, 'pady': 5}
# to:
pad = {'padx': 0, 'pady': 5}
```

这会影响 Filter 页内 `frm_qr`、`frm_ct`、`btn_frame` 的 `.pack(fill='x', **pad)`，去掉左右外边距。Filter 页的 Entry 等控件使用 `pack(fill='x')` 已支持拉伸。

- [ ] **Step 3: 验证** — 启动应用，切换到 Filter 页，确认两侧空白减少。

- [ ] **Step 4: Commit**

```bash
git add settings.py
git commit -m "fix(ui): reduce filter tab horizontal padding from 10px to 5px per side"
```

---

### Task 4: 解除窗口最小宽度锁定

**Files:**
- Modify: `tray.py:643-647`

- [ ] **Step 1: 改为固定最小宽度 600**

```python
# tray.py lines 643-647, change:
    # 设置最小尺寸（基于当前 geometry，用户只能调大不能调小）
    geo_str = root.geometry()
    base_w = int(geo_str.split('x')[0])
    base_h = int(geo_str.split('x')[1].split('+')[0])
    root.minsize(base_w, base_h)
# to:
    # 设置最小尺寸（600px 为合理最小宽度，高度基于当前页）
    geo_str = root.geometry()
    base_h = int(geo_str.split('x')[1].split('+')[0])
    root.minsize(600, base_h)
```

固定 600px 宽度允许用户将窗口缩窄，同时防止缩得过小影响可用性。

- [ ] **Step 2: 验证** — 启动应用，拖拽窗口边缘缩窄，应能缩到约 600px 宽度。确认三个 Tab 在窄窗口下内容不溢出或重叠。

- [ ] **Step 3: Commit**

```bash
git add tray.py
git commit -m "fix(ui): set fixed minimum window width to 600px instead of locking at first-draw size"
```

---

## 整体验证 Checklist

- [ ] 启动应用，三个 Tab 均无左右大面积空白
- [ ] 窗口可自由缩窄至 ~600px
- [ ] Forward 页输入框和列表随窗口拉伸
- [ ] Status 页状态信息布局正常
- [ ] Filter 页内容布局正常
- [ ] 垂直方向（上下间距）无变化
