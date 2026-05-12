# 窗口默认尺寸与最小尺寸锁定 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 窗口默认尺寸由 tkinter 布局自动决定（不再硬编码），并将该尺寸设为最小限制，用户只能调大不能调小。

**Architecture:** 移除 `1100x750` 硬编码，首次运行时让 tkinter 自动布局后捕获实际渲染尺寸作为默认值，所有启动路径均从 geometry 解析宽高设置 `root.minsize()`。

**Tech Stack:** tkinter (root.geometry, root.minsize, root.winfo_width/height)

---

### Task 1: tray.py — 动态默认尺寸 + minsize 锁定

**Files:**
- Modify: `tray.py:521-575`

- [ ] **Step 1: 重写窗口初始化代码（geometry + minsize 部分）**

找到第 549-551 行的代码：
```python
# 恢复窗口尺寸
    saved_geo = load_window_geometry()
    root.geometry(saved_geo or '1100x750')
```

替换为：
```python
    # 恢复窗口尺寸
    saved_geo = load_window_geometry()
    if saved_geo:
        root.geometry(saved_geo)
```

然后找到第 571-572 行：
```python
    # 显示主窗口
    show_main_window(root)
```

在其后添加：
```python
    # 首次运行：捕获布局自然尺寸作为默认
    if not saved_geo:
        root.update_idletasks()
        default_geo = root.geometry()
        save_window_geometry(default_geo)

    # 设置最小尺寸（基于当前 geometry，用户只能调大不能调小）
    geo_str = root.geometry()
    base_w = int(geo_str.split('x')[0])
    base_h = int(geo_str.split('x')[1].split('+')[0])
    root.minsize(base_w, base_h)
```

完整上下文改动后的代码块（第 549-575 行区域）：
```python
    # 恢复窗口尺寸
    saved_geo = load_window_geometry()
    if saved_geo:
        root.geometry(saved_geo)

    def _on_configure(event):
        global _save_timer_id
        if root.wm_state() != 'normal' or event.widget is not root:
            return
        if _save_timer_id:
            root.after_cancel(_save_timer_id)
        _save_timer_id = root.after(
            500, lambda: save_window_geometry(root.geometry())
        )

    root.bind('<Configure>', _on_configure)

    # 启动托盘
    icon = setup_tray(root, show_main_window)

    # 桌面快捷方式（首次运行自动创建）
    create_desktop_shortcut()

    # 显示主窗口
    show_main_window(root)

    # 首次运行：捕获布局自然尺寸作为默认
    if not saved_geo:
        root.update_idletasks()
        default_geo = root.geometry()
        save_window_geometry(default_geo)

    # 设置最小尺寸（基于当前 geometry，用户只能调大不能调小）
    geo_str = root.geometry()
    base_w = int(geo_str.split('x')[0])
    base_h = int(geo_str.split('x')[1].split('+')[0])
    root.minsize(base_w, base_h)

    _set_taskbar_icon(root.winfo_id(), ico_path)
```

- [ ] **Step 2: 验证语法正确**

```bash
cd D:/DevVProgram/QQLLOneBotCLI && python -c "import py_compile; py_compile.compile('tray.py', doraise=True); print('OK')"
```

Expected: `OK`

- [ ] **Step 3: 提交**

```bash
git add tray.py
git commit -m "feat(tray): use dynamic default size and enforce minsize"
```

---

### Task 2: 手动验证

- [ ] **Step 1: 删除已保存的窗口状态**

```bash
rm .window_state.json
```

- [ ] **Step 2: 启动应用**

```bash
python tray.py
```

- [ ] **Step 3: 验证默认尺寸**

1. 窗口以布局自然尺寸显示（非硬编码的 1100x750）
2. 尝试缩小窗口 — 无法缩小到默认尺寸以下
3. 尝试拉大窗口 — 正常拉大
4. 关闭并重启 — 窗口恢复上次的尺寸，minsize 仍然生效
