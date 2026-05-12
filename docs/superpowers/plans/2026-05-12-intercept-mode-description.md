# 拦截模式说明文字显示 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 QR 码过滤拦截模式下拉框右侧动态显示选中模式的说明文字

**Architecture:** 在 `settings.py` 模块级别新增 `MODE_DESCRIPTIONS` 常量，`create_filter_frame` 内新增说明标签并通过 `<<ComboboxSelected>>` 事件驱动标签文字更新

**Tech Stack:** Python tkinter

---

### Task 1: 添加模式说明描述标签和测试

**Files:**
- Modify: `settings.py:156-173`
- Modify: `tests/test_settings.py`

- [ ] **Step 1: 编写 MODE_DESCRIPTIONS 映射测试**

```python
def test_mode_descriptions_mapping():
    """三种模式都有对应的中文说明"""
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from settings import MODE_DESCRIPTIONS

    assert '仅关键词图片' in MODE_DESCRIPTIONS
    assert '拦截纯图片' in MODE_DESCRIPTIONS
    assert '拦截所有图片' in MODE_DESCRIPTIONS
    assert MODE_DESCRIPTIONS['仅关键词图片'] == '仅拦截同时包含图片和关键词的消息'
    assert MODE_DESCRIPTIONS['拦截纯图片'] == '额外拦截无文字说明的纯图片消息'
    assert MODE_DESCRIPTIONS['拦截所有图片'] == '拦截所有含图片的消息'
```

- [ ] **Step 2: 运行测试确认失败**

运行: `python -m pytest tests/test_settings.py::test_mode_descriptions_mapping -v`
预期: FAIL — `ModuleNotFoundError` 或 `ImportError`，因为 `settings.MODE_DESCRIPTIONS` 尚不存在

- [ ] **Step 3: 在 settings.py 中添加 MODE_DESCRIPTIONS 和说明标签**

在 `settings.py` 模块级别（`SCRIPT_DIR = ...` 之后）添加 MODE_DESCRIPTIONS 常量：

```python
MODE_DESCRIPTIONS = {
    '仅关键词图片': '仅拦截同时包含图片和关键词的消息',
    '拦截纯图片': '额外拦截无文字说明的纯图片消息',
    '拦截所有图片': '拦截所有含图片的消息',
}
```

在 `mode_combo.pack(...)` 之后，添加说明标签和事件绑定：

```python
# 模式说明标签
desc_label = ttk.Label(frm_mode, text=MODE_DESCRIPTIONS.get(display_mode, ''), foreground='gray')

def on_mode_change(event=None):
    selected = mode_var.get()
    desc_label.config(text=MODE_DESCRIPTIONS.get(selected, ''))

mode_combo.bind('<<ComboboxSelected>>', on_mode_change)
desc_label.pack(side='left', padx=(5, 0))
```

- [ ] **Step 4: 运行测试确认通过**

运行: `python -m pytest tests/test_settings.py::test_mode_descriptions_mapping -v`
预期: PASS

- [ ] **Step 5: 手动验证 UI 行为**

- 启动设置界面，检查默认模式下说明文字是否显示
- 切换下拉框选项，确认说明文字同步更新
- 保存配置后再打开，确认说明文字与已保存模式一致

- [ ] **Step 6: 提交**

```bash
git add settings.py tests/test_settings.py
git commit -m "feat(settings): show intercept mode description next to mode dropdown"
```
