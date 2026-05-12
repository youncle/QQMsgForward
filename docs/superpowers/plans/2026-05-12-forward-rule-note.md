# Forward Rule Note Feature Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为转发规则添加可选备注字段，支持旧格式自动迁移，UI 列表优先显示备注

**Architecture:** 将 `forward_rules` 值从 `[target_list]` 升级为 `{"targets": [...], "note": ""}` 对象。settings.py 负责迁移+UI，forward.py 做兼容读取（一行改动）

**Tech Stack:** Python 3, tkinter, JSON config file

---

### Task 1: 旧格式迁移 + 备注输入框 + 列表显示逻辑

**Files:**
- Modify: `settings.py:36-91`（转发规则区域全部改动）

- [ ] **Step 1: 添加迁移函数和 `_src_keys` 列表**

在 `create_settings_frame` 内，`rules = cfg.get('forward_rules', {})` 之后，`frm_rules` 定义之后加入：

```python
# 迁移旧格式 → 新格式
for src, val in list(rules.items()):
    if isinstance(val, list):
        rules[src] = {'targets': val, 'note': ''}

# 规则源键顺序跟踪（listbox index → src key）
_src_keys = []
```

- [ ] **Step 2: 新增备注输入框**

在 `dst_entry.grid(row=1, ...)` 之后，`rules_list = tk.Listbox(...)` 之前插入：

```python
ttk.Label(frm_rules, text='备注').grid(row=2, column=0, sticky='w')
note_entry = ttk.Entry(frm_rules, width=50)
note_entry.grid(row=2, column=1, **pad)
```

同时把 `rules_list` 和 `btn_frm` 的 row 各 +1：

```python
rules_list = tk.Listbox(frm_rules, height=5, width=60)
rules_list.grid(row=3, column=0, columnspan=2, **pad)
```

```python
btn_frm = ttk.Frame(frm_rules)
btn_frm.grid(row=4, column=0, columnspan=2, pady=5)
```

- [ ] **Step 3: 重写 `refresh_rules_list` 支持备注显示**

```python
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
```

- [ ] **Step 4: 更新 `on_add_rule` 保存备注**

```python
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
```

- [ ] **Step 5: 更新 `on_del_rule` 用 `_src_keys` 定位**

```python
def on_del_rule():
    sel = rules_list.curselection()
    if sel:
        src = _src_keys[sel[0]]
        if src in rules:
            del rules[src]
        refresh_rules_list()
```

- [ ] **Step 6: 更新 `on_list_select` 回填备注**

```python
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
```

- [ ] **Step 7: 验证 UI 改动逻辑正确**

启动 GUI 手动测试：
```bash
cd D:/DevVProgram/QQLLOneBotCLI && python -c "from settings import create_settings_frame; import tkinter as tk; r=tk.Tk(); create_settings_frame(r).pack(fill='both',expand=True); r.mainloop()"
```

验证清单：
- [ ] 旧规则（list 格式）被自动迁移，列表显示群号
- [ ] 新规则可添加备注，列表显示备注内容
- [ ] 选中规则时三个字段正确回填
- [ ] 删除规则后备注随之清除
- [ ] 保存后 config.json 写入新格式

- [ ] **Step 8: 提交**

```bash
git add settings.py
git commit -m "feat(settings): add note field to forward rules"
```

---

### Task 2: forward.py 兼容新格式

**Files:**
- Modify: `forward.py:168`

- [ ] **Step 1: 适配 target_groups 读取**

将 line 168：
```python
target_groups = forward_rules[group_id]
```
改为（兼容新旧格式）：
```python
rule = forward_rules[group_id]
target_groups = rule['targets'] if isinstance(rule, dict) else rule
```

- [ ] **Step 2: 运行已有测试确认无回归**

```bash
cd D:/DevVProgram/QQLLOneBotCLI && python -m pytest tests/test_forward.py -v
```
Expected: 3 passed

- [ ] **Step 3: 提交**

```bash
git add forward.py
git commit -m "fix(forward): support new forward_rules format with note field"
```

---

### Task 3: 单元测试覆盖迁移逻辑

**Files:**
- Create: `tests/test_settings.py`

- [ ] **Step 1: 写测试**

```python
"""Test settings module: format migration"""
import sys
import os
import json
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import settings as s


def test_migrate_old_format_in_memory():
    """旧 list 格式在加载后应变为 {targets, note} 格式"""
    # 模拟旧格式
    rules = {
        '1079264158': ['1080631149'],
        '107054156': ['702961941', '123456789'],
    }
    for src, val in list(rules.items()):
        if isinstance(val, list):
            rules[src] = {'targets': val, 'note': ''}

    assert rules['1079264158'] == {'targets': ['1080631149'], 'note': ''}
    assert rules['107054156'] == {'targets': ['702961941', '123456789'], 'note': ''}


def test_new_format_unchanged():
    """新格式保持不变"""
    rules = {
        '1079264158': {'targets': ['1080631149'], 'note': '测试备注'},
    }
    for src, val in list(rules.items()):
        if isinstance(val, list):
            rules[src] = {'targets': val, 'note': ''}

    assert rules['1079264158'] == {'targets': ['1080631149'], 'note': '测试备注'}


def test_mixed_format_handled():
    """混合格式都能正确处理"""
    rules = {
        'a': ['b'],  # 旧格式
        'c': {'targets': ['d'], 'note': 'note1'},  # 新格式
    }
    for src, val in list(rules.items()):
        if isinstance(val, list):
            rules[src] = {'targets': val, 'note': ''}

    assert rules['a'] == {'targets': ['b'], 'note': ''}
    assert rules['c'] == {'targets': ['d'], 'note': 'note1'}


def test_save_and_load_new_format():
    """保存新格式后重新加载，数据正确"""
    tmpdir = tempfile.mkdtemp()
    config_path = os.path.join(tmpdir, 'config.json')
    old_path = s.CONFIG_PATH
    s.CONFIG_PATH = config_path

    try:
        data = {
            'robot_qq': 12345,
            'forward_rules': {
                'src1': {'targets': ['dst1'], 'note': '产品群→研发群'},
            },
            'llbot_api': 'http://test:3000',
            'filter': {'qrcode': {}, 'contact': {}},
        }
        s.save_config(data)
        loaded = s.load_config()
        rule = loaded['forward_rules']['src1']
        assert rule['targets'] == ['dst1']
        assert rule['note'] == '产品群→研发群'
    finally:
        s.CONFIG_PATH = old_path
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)
```

- [ ] **Step 2: 运行测试**

```bash
cd D:/DevVProgram/QQLLOneBotCLI && python -m pytest tests/test_settings.py -v
```
Expected: 4 passed

- [ ] **Step 3: 提交**

```bash
git add tests/test_settings.py
git commit -m "test(settings): add migration and save/load tests for rule notes"
```
