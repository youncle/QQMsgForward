# settings.py 重构方案

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**目标：** 将 528 行的 `settings.py` 拆分为独立模块，消除跨页面变量污染（彻底避免过滤页误用企微 `enabled_cb` 这类 bug 再次发生），同时修复现有 bug。

**架构：** 原有 `settings.py` 转为包 `settings/`，内部按 UI 页面职责拆分：`base.py`（共享配置工具）、`forward_frame.py`（转发规则）、`filter_frame.py`（过滤规则 + bug 修复）、`wecom_frame.py`（企微配置 + 清理重复代码）。包 `__init__.py` 透传所有公开接口，保持 `tray.py` 导入路径完全不变。

**接口兼容性：** `tray.py` 中 `settings_mod.set_config_path()`、`settings_mod.load_config()`、`settings_mod.create_forward_frame()`、`settings_mod.create_filter_frame()`、`settings_mod.create_wecom_frame()` 全部通过 `__init__.py` 透传，调用方无需修改。

**bug 修复（嵌入在拆分解耦中）：**
1. 删除 `create_filter_frame.on_save()` 中第 301 行的 `cfg["wecom_enabled"] = ...`（无此变量 → NameError）
2. 删除 `create_wecom_frame.on_save()` 中第 513 行的重复 `cfg["wecom_enabled"] = ...`

**Tech Stack:** Python 3.9+, tkinter, typing

---

### Task 1: 创建包骨架 + 提取共享工具到 `base.py`

**文件:**
- 创建: `src/settings/__init__.py`
- 创建: `src/settings/base.py`
- 删除: `src/settings.py`

- [ ] **Step 1: 创建 `src/settings/` 目录和 `__init__.py`**

```python
# src/settings/__init__.py
from .base import set_config_path, load_config, save_config, CONFIG_PATH
from .forward_frame import create_forward_frame
from .filter_frame import create_filter_frame
from .wecom_frame import create_wecom_frame
```

- [ ] **Step 2: 创建 `src/settings/base.py` — 移入共享工具 + 常量**

从 `settings.py` 第 1-36 行提取，内容如下：

```python
"""QQ消息转发 — 设置界面共享工具"""
import json
import os

SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(SCRIPT_DIR, 'config', 'config.json')

def set_config_path(path: str) -> None:
    global CONFIG_PATH
    CONFIG_PATH = path

MODE_DESCRIPTIONS = {
    '仅关键词图片': '仅拦截同时包含图片和关键词的消息',
    '拦截纯图片': '额外拦截无文字说明的纯图片消息',
    '拦截所有图片': '拦截所有含图片的消息',
}

def load_config():
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_config(data):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    tmp = CONFIG_PATH + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, CONFIG_PATH)
```

- [ ] **Step 3: 删除原 `src/settings.py`**

```
Remove-Item src/settings.py
```

- [ ] **Step 4: 验证导入路径**

```bash
python -c "import sys; sys.path.insert(0, 'src'); from settings import set_config_path, load_config, save_config, create_forward_frame, create_filter_frame, create_wecom_frame; print('OK')"
```

预期输出: `OK`

---

### Task 2: 提取转发规则页面到 `forward_frame.py`

**文件:**
- 创建: `src/settings/forward_frame.py`
- 验证: 通过 python 导入

- [ ] **Step 1: 创建 `src/settings/forward_frame.py`**

将原 `settings.py` 第 38-171 行（`create_forward_frame` 函数完整体）复制到此文件，顶部添加：

```python
"""QQ消息转发 — 转发规则设置界面"""
import tkinter as tk
from tkinter import ttk, messagebox

from .base import load_config, save_config
```

函数体不变（全部保留）。

- [ ] **Step 2: 验证导入**

```bash
python -c "import sys; sys.path.insert(0, 'src'); from settings import create_forward_frame; print('forward OK')"
```

预期输出: `forward OK`

---

### Task 3: 提取过滤规则页面到 `filter_frame.py` + 修复 bug

**文件:**
- 创建: `src/settings/filter_frame.py`
- 修复: 删除误粘的 `enabled_cb` 行

- [ ] **Step 1: 创建 `src/settings/filter_frame.py`**

将原 `settings.py` 第 173-333 行（`create_filter_frame` 函数完整体）复制到此文件，顶部添加：

```python
"""QQ消息转发 — 过滤规则设置界面"""
import tkinter as tk
from tkinter import ttk, messagebox

from .base import load_config, save_config, MODE_DESCRIPTIONS
```

- [ ] **Step 2: 在复制的 `on_save()` 函数中，删除 bug 行**

删除以下行（原 `settings.py:301`）：

```python
cfg['wecom_enabled'] = bool(int(enabled_cb.getvar(enabled_cb['variable'])))
```

该行中 `enabled_cb` 变量在 `create_filter_frame` 中未定义，会导致 `NameError`，且过滤页面完全不需要设置 `wecom_enabled`。

修复后 `on_save()` 应为：

```python
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
```

- [ ] **Step 3: 验证导入**

```bash
python -c "import sys; sys.path.insert(0, 'src'); from settings import create_filter_frame; print('filter OK')"
```

预期输出: `filter OK`

---

### Task 4: 提取企微配置页面到 `wecom_frame.py` + 清理重复行

**文件:**
- 创建: `src/settings/wecom_frame.py`
- 清理: 删除重复的 `cfg["wecom_enabled"]` 赋值行

- [ ] **Step 1: 创建 `src/settings/wecom_frame.py`**

将原 `settings.py` 第 335-528 行（`create_wecom_frame` 函数完整体）复制到此文件，顶部添加：

```python
"""QQ消息转发 — 企业微信配置界面"""
import tkinter as tk
from tkinter import ttk, messagebox

from .base import load_config, save_config
```

- [ ] **Step 2: 删除 `on_save()` 中重复的 `cfg["wecom_enabled"]` 行**

删除第 513 行的重复赋值：

```python
cfg['wecom_enabled'] = bool(int(enabled_cb.getvar(enabled_cb['variable'])))
```

修复后 `on_save()` 中的 `wecom_enabled` 赋值仅保留一次：

```python
def on_save():
    cfg["wecom_enabled"] = bool(int(enabled_cb.getvar(enabled_cb["variable"])))
    cfg["wecom_mode"] = "ui" if bool(int(ui_cb.getvar(ui_cb["variable"]))) else "api"
    cfg["wecom_bots"] = bots
    ...
```

- [ ] **Step 3: 验证导入**

```bash
python -c "import sys; sys.path.insert(0, 'src'); from settings import create_wecom_frame; print('wecom OK')"
```

预期输出: `wecom OK`

---

### Task 5: 更新 `__init__.py` 完善透传

**文件:**
- 修改: `src/settings/__init__.py`（如果 Task 1 已创建但需要补充）

- [ ] **Step 1: 确认 `__init__.py` 完整透传所有公开接口**

确保 `__init__.py` 包含：

```python
# src/settings/__init__.py
from .base import set_config_path, load_config, save_config, CONFIG_PATH, MODE_DESCRIPTIONS
from .forward_frame import create_forward_frame
from .filter_frame import create_filter_frame
from .wecom_frame import create_wecom_frame
```

注意：如果 `tray.py` 或其他地方有 `from settings import MODE_DESCRIPTIONS` 或 `from settings import CONFIG_PATH`，也需透传。经查 `tray.py` 中未直接引用这两个变量，但为安全考虑一并透传。

- [ ] **Step 2: 完整导入验证**

```bash
python -c "import sys; sys.path.insert(0, 'src'); from settings import *; print('all symbols:', [x for x in dir() if not x.startswith('_')])"
```

预期输出应包含: `set_config_path`, `load_config`, `save_config`, `create_forward_frame`, `create_filter_frame`, `create_wecom_frame`

---

### Task 6: 集成验证

**文件:**
- 验证: `src/tray.py` 无需修改

- [ ] **Step 1: 确认 `tray.py` 中所有 `settings_mod.*` 调用仍工作**

原 `tray.py` 调用（第 19, 547, 554, 933-938 行）：

```python
import settings as settings_mod                     # 包导入，不变
settings_mod.set_config_path(fwd_config_path)        # 透传
shared_cfg = settings_mod.load_config()              # 透传
tab2 = settings_mod.create_forward_frame(...)         # 透传
tab3 = settings_mod.create_filter_frame(...)          # 透传
tab4 = settings_mod.create_wecom_frame(...)           # 透传
```

以上所有调用通过 `__init__.py` 透传，无需修改 `tray.py`。

- [ ] **Step 2: 检查 `wizard.py` 中是否引用 `settings` 模块**

```bash
Select-String -Pattern "from settings|import settings" src/wizard.py
```

如果 `wizard.py` 也引用了 `settings` 中的函数，需确保透传覆盖。

- [ ] **Step 3: 最终验证**

```bash
python -c "
import sys, os
sys.path.insert(0, 'src')
os.environ['DISPLAY'] = ''  # 无头环境跳过 tkinter 窗口创建

# 验证所有符号可导入
from settings import (
    set_config_path, load_config, save_config,
    create_forward_frame, create_filter_frame,
    create_wecom_frame, CONFIG_PATH, MODE_DESCRIPTIONS
)
print('All imports OK')

# 验证配置读写（使用临时路径）
import tempfile
tmp = os.path.join(tempfile.gettempdir(), 'test_config.json')
set_config_path(tmp)
with open(tmp, 'w') as f:
    import json
    json.dump({'test': True}, f)
cfg = load_config()
assert cfg['test'] == True, 'load_config failed'
print('Config R/W OK')
os.remove(tmp)
print('All tests passed')
"
```

预期输出:

```
All imports OK
Config R/W OK
All tests passed
```
