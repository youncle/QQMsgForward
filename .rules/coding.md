# 编码规范

## 1. import 顺序

```python
# 标准库
import os
import sys
import json
import logging
import time
from typing import Dict, List, Optional

# 空行
# 第三方
import requests
from flask import Flask, request
from PIL import Image

# 空行
# 本地模块
from filter import should_filter
from nt_utils import get_file_bytes_via_ntcall
```

## 2. 类型注解

所有新函数必须有完整的类型注解（含返回值）：

```python
# ✅ 正确
def is_duplicate(group_id: str, raw_text: str) -> bool:
    ...

# ❌ 错误
def is_duplicate(group_id, raw_text):
    ...
```

## 3. 日志

使用 logging，禁止 print：

```python
# ✅ 正确
logger = logging.getLogger(__name__)
logger.info(f"转发成功: {group_id} → {target}")
logger.error(f"转发失败: {e}", exc_info=True)

# ❌ 错误
print(f"转发成功: {group_id} → {target}")
```

## 4. 错误处理

优先捕获特定异常，避免裸 except：

```python
# ✅ 正确
try:
    resp = session.post(url, json=data, timeout=5)
    resp.raise_for_status()
except requests.exceptions.ConnectionError:
    logger.warning(f"连接失败: {url}")
except requests.exceptions.Timeout:
    logger.warning(f"超时: {url}")

# ❌ 错误
try:
    ...
except:
    ...
```

## 5. 配置写入（原子操作）

```python
# ✅ 正确
tmp = CONFIG_PATH + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
os.replace(tmp, CONFIG_PATH)

# ❌ 错误
with open(CONFIG_PATH, "w") as f:
    json.dump(data, f)  # 写入中断会损坏配置
```

## 6. 字符串编码

所有文件 IO 操作显式指定 encoding：

```python
# ✅ 正确
with open(path, "r", encoding="utf-8") as f:

# ❌ 错误
with open(path, "r") as f:  # 依赖系统默认编码
```

## 7. 不引入新依赖

添加新的第三方包必须在 `requirements.txt` 中同步记录：

```python
# 在 requirements.txt 追加一行
# 然后运行 pip install -r requirements.txt
```
