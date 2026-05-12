# Fix Notebook Tab Content Padding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 移除 `notebook.tab()` 对内容区域误加的 100px 水平内边距，彻底消除左右白色空白。

**Architecture:** `notebook.tab(tab_id, padding=...)` 在 ttk 中设置的是**内容区域**内边距，不是标签间距。将其从 `(100, 8)` 改为 `(0, 8)`，去掉水平内容内边距，保留 8px 垂直间距防止内容贴边。标签文字宽度由 `style.configure('TNotebook.Tab', padding=(35, 8))` 单独控制。

**Tech Stack:** Python tkinter + ttk

---

### Task 1: 修正 notebook.tab() 内容 padding

**Files:**
- Modify: `tray.py:583 What's the `

- [ ] **Step 1: 将 tab_pad 从 (100, 8) 改为 (0, 8)**

```python
# tray.py lines 583-584, change:
    # 加宽 tab 标签（Windows 原生主题下 style padding 无效，需在 tab 上直接设）
    tab_pad = (100, 8)
# to:
    tab_pad = (0, 8)
```

水平 100 → 0 去掉内容区域左右空白，垂直保留 8px 防止内容紧贴顶部/底部。

- [ ] **Step 2: 验证** — 启动应用 `python tray.py`，检查三个 Tab 页左右两侧白色空白是否消失，确认底部无多余白色区域。

- [ ] **Step 3: Commit**

```bash
git add tray.py
git commit -m "fix(ui): remove 100px horizontal content padding from notebook tabs"
```

---

## 变更说明

| 改动 | 之前 | 之后 | 效果 |
|------|------|------|------|
| `tab_pad` | `(100, 8)` | `(0, 8)` | 内容区域左右各减 100px 空白 |

`notebook.tab(tab_id, padding=...)` 是 ttk 的内容区域 padding，不是标签文字间距。原代码误以为能加宽标签，实际给了每个 Tab 内容区域加了 200px（左右各 100）空白。标签样式由 `style.configure('TNotebook.Tab', padding=(35, 8))` 控制，不受此改动影响。
