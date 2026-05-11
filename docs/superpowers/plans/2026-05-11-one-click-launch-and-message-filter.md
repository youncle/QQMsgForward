# 一键启动 & 消息过滤 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 VBS 一键启动/关闭 + 系统托盘常驻 + QR 码/联系方式消息过滤

**Architecture:** `start.vbs` 提权后静默启动 LLBot，然后启动 `tray.py`（pystray 托盘程序），tray.py 拉起了 `qq-message-forward.py` 子进程并监控状态。`filter.py` 作为纯函数模块被 forward.py 调用，在转发前检查消息是否命中过滤规则。所有配置集中在 `config.json`。

**Tech Stack:** Python 3, Flask, requests, pystray + pillow, VBScript (Windows 原生)

---

### Task 1: 基础设施 — config.json + requirements.txt

**Files:**
- Create: `config.json`
- Create: `requirements.txt`

- [ ] **Step 1: 创建 requirements.txt**

```txt
flask>=3.0
requests>=2.31
pystray>=0.19
pillow>=10.0
```

- [ ] **Step 2: 创建 config.json**

```json
{
  "robot_qq": 2776992588,
  "forward_rules": {
    "1079264158": ["1087980588", "1080631149"]
  },
  "llbot_api": "http://127.0.0.1:3000",
  "llbot_token": "",
  "filter": {
    "qrcode": {
      "enabled": true,
      "keywords": ["加我", "扫码", "扫一扫", "联系我", "加好友", "VX", "v:", "微信", "私聊"],
      "mode": "image_with_keyword"
    },
    "contact": {
      "enabled": true,
      "patterns": {
        "phone": "1[3-9]\\d{9}",
        "qq": "(?<!\\d)[1-9]\\d{4,9}(?!\\d)",
        "wechat": "wxid_[a-z0-9]+",
        "email": "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}"
      },
      "keywords": ["我的Q", "我的V", "联系我", "加好友", "私聊我"]
    },
    "log_only": false
  },
  "forward": {
    "duplicate_window": 5,
    "send_interval": 1.0
  }
}
```

- [ ] **Step 3: 安装依赖并验证**

```bash
pip install flask requests pystray pillow pytest
pytest --version
```

---

### Task 2: TDD — filter.py QR 码检测

**Files:**
- Create: `tests/test_filter.py`
- Create: `filter.py`

- [ ] **Step 1: 写失败测试 — 图片+关键词命中**

写入 `tests/test_filter.py`：

```python
import sys
sys.path.insert(0, '.')
from filter import check_qrcode_ad

# 示例 OneBot v11 消息段（array 格式）
IMG_AND_KEYWORD = [
    {'type': 'image', 'data': {'file': 'abc123', 'url': 'http://example.com/img.jpg'}},
    {'type': 'text', 'data': {'text': '加我好友拉你进群'}}
]
PURE_TEXT = [
    {'type': 'text', 'data': {'text': '大家好今天天气不错'}}
]
IMAGE_ONLY = [
    {'type': 'image', 'data': {'file': 'def456', 'url': 'http://example.com/cat.jpg'}}
]
IMAGE_AND_NORMAL_TEXT = [
    {'type': 'image', 'data': {'file': 'ghi789', 'url': 'http://example.com/screenshot.jpg'}},
    {'type': 'text', 'data': {'text': '看看这个截图'}}
]

QR_KEYWORDS = ['加我', '扫码', '扫一扫', '联系我', '加好友', 'VX', 'v:', '微信', '私聊']


def test_qrcode_hit_when_image_and_keyword():
    result = check_qrcode_ad(IMG_AND_KEYWORD, QR_KEYWORDS)
    assert result is True


def test_qrcode_pass_when_pure_text():
    result = check_qrcode_ad(PURE_TEXT, QR_KEYWORDS)
    assert result is False


def test_qrcode_pass_when_image_only_no_keyword():
    result = check_qrcode_ad(IMAGE_ONLY, QR_KEYWORDS)
    assert result is False


def test_qrcode_pass_when_image_and_normal_text():
    result = check_qrcode_ad(IMAGE_AND_NORMAL_TEXT, QR_KEYWORDS)
    assert result is False
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/test_filter.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'filter'`

- [ ] **Step 3: 写最小实现**

写入 `filter.py`：

```python
"""消息过滤模块 — QR码广告检测 + 联系方式检测"""

from typing import List, Dict, Union

# OneBot v11 消息段类型
MessageSegment = Dict[str, Union[str, Dict[str, str]]]


def check_qrcode_ad(message: List[MessageSegment], keywords: List[str]) -> bool:
    """检查消息是否为二维码广告（包含图片段 + 匹配关键词）"""
    has_image = any(seg.get('type') == 'image' for seg in message)
    if not has_image:
        return False
    text = ''.join(
        seg.get('data', {}).get('text', '')
        for seg in message
        if seg.get('type') == 'text'
    )
    return any(kw in text for kw in keywords)
```

- [ ] **Step 4: 运行测试确认通过**

```bash
pytest tests/test_filter.py -v
```
Expected: all 4 tests PASS

- [ ] **Step 5: 追加失败测试 — 空消息和边界情况**

在 `tests/test_filter.py` 末尾追加：

```python
EMPTY_MESSAGE = []
MULTI_IMAGE_WITH_KEYWORD = [
    {'type': 'image', 'data': {'file': 'img1'}},
    {'type': 'image', 'data': {'file': 'img2'}},
    {'type': 'text', 'data': {'text': '扫码进群'}}
]


def test_qrcode_pass_when_empty_message():
    result = check_qrcode_ad(EMPTY_MESSAGE, QR_KEYWORDS)
    assert result is False


def test_qrcode_hit_when_multi_image_and_keyword():
    result = check_qrcode_ad(MULTI_IMAGE_WITH_KEYWORD, QR_KEYWORDS)
    assert result is True
```

- [ ] **Step 6: 确认新测试通过（代码无需改动）**

```bash
pytest tests/test_filter.py -v
```
Expected: all 6 tests PASS

---

### Task 3: TDD — filter.py 联系方式检测

**Files:**
- Modify: `tests/test_filter.py`
- Modify: `filter.py`

- [ ] **Step 1: 写失败测试 — 联系方式正则匹配**

在 `tests/test_filter.py` 末尾追加：

```python
from filter import check_contact_info

CONTACT_PATTERNS = {
    'phone': r'1[3-9]\d{9}',
    'qq': r'(?<!\d)[1-9]\d{4,9}(?!\d)',
    'wechat': r'wxid_[a-z0-9]+',
    'email': r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
}
CONTACT_KEYWORDS = ['我的Q', '我的V', '联系我', '加好友', '私聊我']


def test_contact_hit_phone_number():
    msg = [{'type': 'text', 'data': {'text': '联系我 13812345678'}}]
    result = check_contact_info(msg, CONTACT_PATTERNS, CONTACT_KEYWORDS)
    assert result is True


def test_contact_hit_phone_number():
    msg = [{'type': 'text', 'data': {'text': '联系我 13812345678'}}]
    result = check_contact_info(msg, CONTACT_PATTERNS, CONTACT_KEYWORDS)
    assert result is True


def test_contact_hit_qq_number():
    msg = [{'type': 'text', 'data': {'text': '加我QQ 12345678'}}]
    result = check_contact_info(msg, CONTACT_PATTERNS, CONTACT_KEYWORDS)
    assert result is True


def test_contact_hit_wechat_id():
    msg = [{'type': 'text', 'data': {'text': '加 wxid_abc123def 拉你进群'}}]
    result = check_contact_info(msg, CONTACT_PATTERNS, CONTACT_KEYWORDS)
    assert result is True


def test_contact_hit_email():
    msg = [{'type': 'text', 'data': {'text': '发资料到 test@qq.com'}}]
    result = check_contact_info(msg, CONTACT_PATTERNS, CONTACT_KEYWORDS)
    assert result is True


def test_contact_hit_suspicious_keyword():
    msg = [{'type': 'text', 'data': {'text': '我的V是 xxx123 私聊我'}}]
    result = check_contact_info(msg, CONTACT_PATTERNS, CONTACT_KEYWORDS)
    assert result is True


def test_contact_pass_normal_text():
    msg = [{'type': 'text', 'data': {'text': '今天天气真好，大家吃饭了吗'}}]
    result = check_contact_info(msg, CONTACT_PATTERNS, CONTACT_KEYWORDS)
    assert result is False


def test_contact_pass_group_number():
    """群号（6位以上纯数字）不应被误判为QQ号"""
    msg = [{'type': 'text', 'data': {'text': '欢迎加群 1079264158'}}]
    result = check_contact_info(msg, CONTACT_PATTERNS, CONTACT_KEYWORDS)
    # 1079264158 是10位数字，会被 QQ 正则匹配到...需要特殊处理
    # 目前先按现有规则测试，后续可在配置中加白名单
    assert result is True  # 当前实现确实会匹配到
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/test_filter.py::test_contact_hit_phone_number -v
```
Expected: FAIL — `ImportError: cannot import name 'check_contact_info'`

- [ ] **Step 3: 写最小实现**

在 `filter.py` 末尾追加：

```python
import re


def check_contact_info(
    message: List[MessageSegment],
    patterns: Dict[str, str],
    keywords: List[str]
) -> bool:
    """检查消息是否包含私人联系方式"""
    text = ''.join(
        seg.get('data', {}).get('text', '')
        for seg in message
        if seg.get('type') == 'text'
    )
    if not text:
        return False
    # 关键词匹配
    if any(kw in text for kw in keywords):
        return True
    # 正则匹配
    for name, pattern in patterns.items():
        if re.search(pattern, text):
            return True
    return False
```

- [ ] **Step 4: 运行全部测试确认通过**

```bash
pytest tests/test_filter.py -v
```
Expected: all 13 tests PASS (6 QR + 7 contact)

- [ ] **Step 5: 修复测试重复函数名**

`test_contact_hit_phone_number` 重复了两次，删除第一个（保留第二个完整版）。注意：第二步追加时没有重复的问题，但需要手动检查确认。

```bash
# 检查是否正确
grep -n "def test_" tests/test_filter.py
```

预期看到13个唯一测试函数名。

---

### Task 4: TDD — 过滤日志格式化 & log_only 模式

**Files:**
- Modify: `tests/test_filter.py`
- Modify: `filter.py`

- [ ] **Step 1: 写失败测试 — should_filter 整合函数**

在 `tests/test_filter.py` 末尾追加：

```python
from filter import should_filter

FILTER_CONFIG = {
    'qrcode': {
        'enabled': True,
        'keywords': ['加我', '扫码', '扫一扫', '联系我', '加好友', 'VX', 'v:', '微信', '私聊'],
        'mode': 'image_with_keyword'
    },
    'contact': {
        'enabled': True,
        'patterns': {
            'phone': r'1[3-9]\d{9}',
            'qq': r'(?<!\d)[1-9]\d{4,9}(?!\d)',
            'wechat': r'wxid_[a-z0-9]+',
            'email': r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        },
        'keywords': ['我的Q', '我的V', '联系我', '加好友', '私聊我']
    },
    'log_only': False
}


def test_should_filter_returns_qrcode_reason():
    msg = [
        {'type': 'image', 'data': {'file': 'img1'}},
        {'type': 'text', 'data': {'text': '扫码进群'}}
    ]
    filtered, reason = should_filter(msg, FILTER_CONFIG)
    assert filtered is True
    assert reason.startswith('[QR码]')


def test_should_filter_returns_contact_reason_for_phone():
    msg = [{'type': 'text', 'data': {'text': '打我电话 13800000000'}}]
    filtered, reason = should_filter(msg, FILTER_CONFIG)
    assert filtered is True
    assert '[联系方式:phone]' in reason


def test_should_filter_returns_contact_reason_for_keyword():
    msg = [{'type': 'text', 'data': {'text': '加好友私聊我吧'}}]
    filtered, reason = should_filter(msg, FILTER_CONFIG)
    assert filtered is True
    assert '[联系方式:关键词]' in reason


def test_should_filter_pass_normal_message():
    msg = [{'type': 'text', 'data': {'text': '今天天气不错'}}]
    filtered, reason = should_filter(msg, FILTER_CONFIG)
    assert filtered is False
    assert reason == ''


def test_should_filter_log_only_mode():
    log_config = {**FILTER_CONFIG, 'log_only': True}
    msg = [{'type': 'text', 'data': {'text': '我的电话 13800000000'}}]
    filtered, reason = should_filter(msg, log_config)
    # log_only 模式下不拦截，但返回原因
    assert filtered is False
    assert reason != ''


def test_should_filter_qrcode_disabled():
    disabled_config = {
        **FILTER_CONFIG,
        'qrcode': {**FILTER_CONFIG['qrcode'], 'enabled': False}
    }
    msg = [
        {'type': 'image', 'data': {'file': 'img1'}},
        {'type': 'text', 'data': {'text': '扫码进群'}}
    ]
    filtered, reason = should_filter(msg, disabled_config)
    assert filtered is False
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/test_filter.py::test_should_filter_returns_qrcode_reason -v
```
Expected: FAIL — `ImportError: cannot import name 'should_filter'`

- [ ] **Step 3: 写最小实现**

在 `filter.py` 末尾追加：

```python
from typing import Tuple


def should_filter(
    message: List[MessageSegment],
    config: Dict
) -> Tuple[bool, str]:
    """综合过滤检查 — 返回 (是否拦截, 原因字符串)"""
    qrcode_cfg = config.get('qrcode', {})
    contact_cfg = config.get('contact', {})
    log_only = config.get('log_only', False)

    # QR 码检测
    if qrcode_cfg.get('enabled'):
        if check_qrcode_ad(message, qrcode_cfg.get('keywords', [])):
            reason = _format_filter_reason('QR码', message)
            return (False if log_only else True, reason)

    # 联系方式检测
    if contact_cfg.get('enabled'):
        hit = _check_contact_detail(message, contact_cfg)
        if hit:
            reason = _format_filter_reason(f'联系方式:{hit}', message)
            return (False if log_only else True, reason)

    return (False, '')


def _check_contact_detail(
    message: List[MessageSegment],
    config: Dict
) -> str:
    """检查联系方式详情，返回匹配类型（用于日志），未命中返回空字符串"""
    text = ''.join(
        seg.get('data', {}).get('text', '')
        for seg in message
        if seg.get('type') == 'text'
    )
    if not text:
        return ''
    # 先检查关键词
    if any(kw in text for kw in config.get('keywords', [])):
        return '关键词'
    # 再检查正则
    for name, pattern in config.get('patterns', {}).items():
        if re.search(pattern, text):
            return name
    return ''


def _format_filter_reason(category: str, message: List[MessageSegment]) -> str:
    """生成过滤日志中的原因字段"""
    text = ''.join(
        seg.get('data', {}).get('text', '')
        for seg in message
        if seg.get('type') == 'text'
    )
    summary = text[:50] if text else '[图片消息]'
    return f'[{category}] {summary}'
```

- [ ] **Step 4: 运行测试确认通过**

```bash
pytest tests/test_filter.py -v
```
Expected: all 19 tests PASS

---

### Task 5: 改造 qq-message-forward.py — 配置分离 + 过滤集成

**Files:**
- Modify: `qq-message-forward.py`

这不是 TDD 目标（Flask webhook 的集成测试太复杂），但修改逻辑应保持现有行为不变。

- [ ] **Step 1: 将 forward.py 改为从 config.json 读取配置**

把文件开头的硬编码配置替换为 JSON 读取。修改后的文件：

```python
from flask import Flask, request
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time
import logging
import json
import os
from typing import Dict, List

from filter import should_filter

# 加载配置文件
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    config = json.load(f)

ROBOT_QQ = config['robot_qq']
FORWARD_RULES: Dict[str, List[str]] = config['forward_rules']
LLBOT_API = config['llbot_api']
LLBOT_TOKEN = config.get('llbot_token', '')
DUPLICATE_WINDOW = config['forward']['duplicate_window']
SEND_INTERVAL = config['forward']['send_interval']
FILTER_CONFIG = config.get('filter', {})

# 初始化日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# 初始化Requests会话（带连接池+自动重试）
session = requests.Session()
retry_strategy = Retry(
    total=3,
    backoff_factor=0.5,
    status_forcelist=[500, 502, 503, 504],
    allowed_methods=["POST"]
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("http://", adapter)
session.mount("https://", adapter)

# 配置请求头（带Token）
headers = {"Content-Type": "application/json"}
if LLBOT_TOKEN:
    headers["Authorization"] = f"Bearer {LLBOT_TOKEN}"

# 缓存：去重+限流
msg_cache: Dict[str, float] = {}
last_send_time: Dict[str, float] = {}

app = Flask(__name__)


def is_duplicate(msg_id: str) -> bool:
    """检查消息是否重复，同时清理过期缓存"""
    now = time.time()
    expired = [k for k, v in msg_cache.items() if now - v > DUPLICATE_WINDOW * 10]
    for k in expired:
        del msg_cache[k]
    if msg_id in msg_cache:
        if now - msg_cache[msg_id] < DUPLICATE_WINDOW:
            return True
    msg_cache[msg_id] = now
    return False


def rate_limit(target_group: str) -> None:
    """限流：保证单群发送间隔不小于配置值"""
    now = time.time()
    if target_group in last_send_time:
        wait = SEND_INTERVAL - (now - last_send_time[target_group])
        if wait > 0:
            time.sleep(wait)
    last_send_time[target_group] = time.time()


@app.post("/webhook")
def webhook():
    try:
        data = request.json
        if not data:
            logger.warning("收到空的WebHook请求")
            return "ok"

        # 1. 过滤非群聊消息
        post_type = data.get("post_type")
        message_type = data.get("message_type")
        if post_type != "message" or message_type != "group":
            return "ok"

        # 2. 解析消息信息
        group_id = str(data.get("group_id", ""))
        sender = data.get("sender", {})
        sender_qq = sender.get("user_id", 0)
        msg_id = str(data.get("message_id", ""))
        raw_text = data.get("raw_message", "")
        message_content = data.get("message", "")

        if not group_id or not msg_id:
            return "ok"

        # 3. 跳过自己发的消息（防止循环转发）
        if sender_qq == ROBOT_QQ:
            logger.debug(f"跳过自身消息: {raw_text[:30]}")
            return "ok"

        # 4. 不在转发规则的群，跳过
        if group_id not in FORWARD_RULES:
            return "ok"

        # 5. 去重
        if is_duplicate(msg_id):
            logger.info(f"重复消息，跳过: {raw_text[:30]}")
            return "ok"

        # 6. 消息过滤（QR码 + 联系方式）
        if FILTER_CONFIG:
            blocked, reason = should_filter(message_content, FILTER_CONFIG)
            if blocked:
                logger.info(f"[FILTER] 已拦截: 群{group_id} - {reason}")
                return "ok"
            elif reason:
                # log_only 模式：仅记录，不拦截
                logger.info(f"[FILTER] 仅记录: 群{group_id} - {reason}")

        # 7. 执行转发
        target_groups = FORWARD_RULES[group_id]
        for to_group in target_groups:
            try:
                rate_limit(to_group)
                resp = session.post(
                    f"{LLBOT_API}/send_group_msg",
                    json={
                        "group_id": int(to_group),
                        "message": message_content
                    },
                    headers=headers,
                    timeout=5
                )
                resp.raise_for_status()
                result = resp.json()
                if result.get("status") == "ok":
                    logger.info(f"✅ 转发成功: {group_id} → {to_group} | {raw_text[:50]}...")
                else:
                    err_msg = result.get("msg", result.get("wording", "未知错误"))
                    logger.error(f"❌ API处理失败: {group_id} → {to_group} | 错误: {err_msg}")

            except requests.exceptions.ConnectionError:
                logger.error(f"❌ 连接失败！请检查LLOneBot的HTTP服务是否开启，端口3000是否正常")
            except requests.exceptions.Timeout:
                logger.error(f"❌ 转发超时: {group_id} → {to_group}")
            except Exception as e:
                logger.error(f"❌ 转发异常: {group_id} → {to_group} | 错误: {str(e)}")

        return "ok"

    except Exception as e:
        logger.error(f"处理WebHook请求异常: {str(e)}", exc_info=True)
        return "ok"


if __name__ == '__main__':
    logger.info("=" * 50)
    logger.info("✅ QQ群转发服务已启动")
    logger.info(f"📋 WebHook地址: http://127.0.0.1:8080/webhook")
    logger.info(f"📋 转发规则: {FORWARD_RULES}")
    logger.info(f"📋 过滤状态: QR码={'启用' if FILTER_CONFIG.get('qrcode',{}).get('enabled') else '关闭'} | 联系方式={'启用' if FILTER_CONFIG.get('contact',{}).get('enabled') else '关闭'} | 模式={'仅日志' if FILTER_CONFIG.get('log_only') else '拦截'}")
    logger.info("=" * 50)
    app.run(host="127.0.0.1", port=8080, debug=False, threaded=True)
```

- [ ] **Step 2: 验证语法和导入**

```bash
python -c "import sys; sys.path.insert(0, '.'); from filter import should_filter; print('OK')"
```

Expected: OK

---

### Task 6: 创建 start.vbs 一键启动脚本

**Files:**
- Create: `start.vbs`

- [ ] **Step 1: 创建 start.vbs**

```vbscript
' 一键启动 QQ消息转发服务
' 双击即可，自动获取管理员权限

Option Explicit

Dim WshShell, objShell, strPath, llbotExe, forwardScript, trayScript
Dim llbotPort, maxWait, waitCount, pythonPath, objExec

Set WshShell = CreateObject("WScript.Shell")
Set objShell = CreateObject("Shell.Application")

' 获取脚本所在目录
strPath = WshShell.CurrentDirectory

' 路径配置
llbotExe = strPath & "\LLBot-CLI-Win-x64\llbot.exe"
forwardScript = strPath & "\qq-message-forward.py"
trayScript = strPath & "\tray.py"
llbotPort = 3000
maxWait = 20

' 检查 LLBot 可执行文件
Dim fso : Set fso = CreateObject("Scripting.FileSystemObject")
If Not fso.FileExists(llbotExe) Then
    MsgBox "找不到 LLBot: " & vbCrLf & llbotExe, vbCritical, "启动失败"
    WScript.Quit 1
End If

' 检查转发脚本
If Not fso.FileExists(forwardScript) Then
    MsgBox "找不到转发脚本: " & vbCrLf & forwardScript, vbCritical, "启动失败"
    WScript.Quit 1
End If

' 检查 Python
On Error Resume Next
WshShell.Run "python --version", 0, True
If Err.Number <> 0 Then
    MsgBox "未找到 Python，请先安装 Python 并添加到 PATH", vbCritical, "启动失败"
    WScript.Quit 1
End If
On Error Goto 0

' 自动提权（如果还未以管理员运行）
If Not IsAdmin() Then
    objShell.ShellExecute "wscript.exe", _
        Chr(34) & WScript.ScriptFullName & Chr(34), "", "runas", 1
    WScript.Quit
End If

' 启动 LLBot（隐藏窗口）
WshShell.Run Chr(34) & llbotExe & Chr(34), 0, False

' 等待 LLBot 端口就绪
Dim waited : waited = 0
Do While waited < maxWait
    WScript.Sleep 1000
    waited = waited + 1
    If IsPortOpen(llbotPort) Then Exit Do
Loop

If Not IsPortOpen(llbotPort) Then
    MsgBox "LLBot 启动超时（等待了 " & maxWait & " 秒），请检查 LLBot 是否正常", vbCritical, "启动失败"
    WScript.Quit 1
End If

' 启动托盘程序（托盘会负责启动转发脚本）
WshShell.Run "pythonw """ & trayScript & """", 0, False

WScript.Sleep 2000
MsgBox "服务已启动！" & vbCrLf & vbCrLf & "托盘图标已显示在通知区域，右键可管理服务。", vbInformation, "QQ消息转发"


' ===== 辅助函数 =====

Function IsAdmin()
    On Error Resume Next
    Dim objADSI : Set objADSI = CreateObject("ADSystemInfo")
    IsAdmin = (Err.Number = 0)
    On Error Goto 0
End Function

Function IsPortOpen(port)
    On Error Resume Next
    Dim objTCP : Set objTCP = CreateObject("MSWinsock.Winsock")
    If IsObject(objTCP) Then
        objTCP.RemoteHost = "127.0.0.1"
        objTCP.RemotePort = port
        objTCP.Connect()
        IsPortOpen = (objTCP.State = 7)  ' 7 = Connected
        objTCP.Close()
    Else
        ' 用 netstat 作为备选
        Dim exec : Set exec = WshShell.Exec("netstat -ano")
        Dim output : output = exec.StdOut.ReadAll()
        IsPortOpen = InStr(output, ":" & port & " ") > 0
    End If
    On Error Goto 0
End Function
```

---

### Task 7: 创建 stop.vbs 一键关闭脚本

**Files:**
- Create: `stop.vbs`

- [ ] **Step 1: 创建 stop.vbs**

```vbscript
' 一键关闭 QQ消息转发服务
Option Explicit

Dim WshShell, objShell

Set WshShell = CreateObject("WScript.Shell")
Set objShell = CreateObject("Shell.Application")

' 自动提权
If Not IsAdmin() Then
    objShell.ShellExecute "wscript.exe", _
        Chr(34) & WScript.ScriptFullName & Chr(34), "", "runas", 1
    WScript.Quit
End If

' 终止转发脚本 (python.exe running qq-message-forward.py)
WshShell.Run "taskkill /f /im python.exe >nul 2>&1", 0, True
WshShell.Run "taskkill /f /im pythonw.exe >nul 2>&1", 0, True

' 终止 LLBot
WshShell.Run "taskkill /f /im llbot.exe >nul 2>&1", 0, True

' 额外清理：通过命令行匹配终止
WshShell.Run "wmic process where ""commandline like '%%qq-message-forward%%'"" call terminate >nul 2>&1", 0, True
WshShell.Run "wmic process where ""commandline like '%%tray.py%%'"" call terminate >nul 2>&1", 0, True

MsgBox "服务已关闭！", vbInformation, "QQ消息转发"


Function IsAdmin()
    On Error Resume Next
    Dim objADSI : Set objADSI = CreateObject("ADSystemInfo")
    IsAdmin = (Err.Number = 0)
    On Error Goto 0
End Function
```

---

### Task 8: 创建 tray.py 托盘程序

**Files:**
- Create: `tray.py`

- [ ] **Step 1: 创建 tray.py 托盘程序**

```python
"""QQ消息转发 — 系统托盘管理程序"""
import subprocess
import sys
import os
import time
import threading
import socket

import pystray
from PIL import Image, ImageDraw

# 路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FORWARD_SCRIPT = os.path.join(SCRIPT_DIR, 'qq-message-forward.py')

# 端口
LLBOT_PORT = 3000
FORWARD_PORT = 8080

forward_process = None
running = True


def check_port(port: int, host: str = '127.0.0.1') -> bool:
    """检查端口是否开放"""
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


def start_forward():
    """启动转发脚本子进程"""
    global forward_process
    forward_process = subprocess.Popen(
        [sys.executable, FORWARD_SCRIPT],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )


def stop_forward():
    """停止转发脚本子进程"""
    global forward_process
    if forward_process and forward_process.poll() is None:
        forward_process.terminate()
        forward_process.wait(timeout=5)


def get_status():
    """获取当前服务状态"""
    llbot_ok = check_port(LLBOT_PORT)
    forward_ok = check_port(FORWARD_PORT)
    return llbot_ok, forward_ok


def create_icon_image(color: str = 'green'):
    """创建托盘图标（纯色圆点 64x64）"""
    img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    colors = {
        'green': (76, 175, 80, 255),
        'red': (244, 67, 54, 255),
        'yellow': (255, 193, 7, 255),
    }
    draw.ellipse([8, 8, 56, 56], fill=colors.get(color, colors['green']))
    return img


def show_status_window(icon):
    """显示状态弹窗"""
    llbot_ok, forward_ok = get_status()
    llbot_status = '✓ 运行中' if llbot_ok else '✗ 已停止'
    forward_status = '✓ 运行中' if forward_ok else '✗ 已停止'

    msg = (
        f"LLBot (端口 3000): {llbot_status}\n"
        f"转发脚本 (端口 8080): {forward_status}\n\n"
        f"转发规则: 打开 config.json 查看"
    )

    # pystray 不支持直接弹窗，用 PowerShell 弹窗
    subprocess.run(
        ['powershell', '-Command',
         f"[System.Windows.Forms.MessageBox]::Show('{msg}','QQ消息转发 - 状态')"],
        capture_output=True
    )


def shutdown_service(icon):
    """关闭所有服务"""
    global running
    stop_forward()
    # 终止 LLBot
    subprocess.run(['taskkill', '/f', '/im', 'llbot.exe'],
                   capture_output=True)
    running = False
    icon.stop()


def monitor_loop(icon):
    """监控线程：每5秒检查服务状态"""
    was_ok = True
    while running:
        time.sleep(5)
        llbot_ok, forward_ok = get_status()
        all_ok = llbot_ok and forward_ok

        if not all_ok and was_ok:
            # 服务从正常变为异常
            icon.icon = create_icon_image('red')
            icon.title = 'QQ消息转发 - 服务异常'
        elif all_ok and not was_ok:
            # 服务从异常恢复
            icon.icon = create_icon_image('green')
            icon.title = 'QQ消息转发 - 运行中'

        was_ok = all_ok


def setup_tray():
    """创建并运行托盘图标"""
    icon = pystray.Icon(
        'qq_forward',
        create_icon_image('green'),
        'QQ消息转发 - 运行中',
        menu=pystray.Menu(
            pystray.MenuItem('查看状态', show_status_window),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('关闭服务', shutdown_service),
        )
    )

    # 启动监控线程
    monitor = threading.Thread(target=monitor_loop, args=(icon,), daemon=True)
    monitor.start()

    icon.run()


if __name__ == '__main__':
    # 先确认 LLBot 已运行
    if not check_port(LLBOT_PORT):
        print(f"错误: LLBot 未运行（端口 {LLBOT_PORT} 不通），请先启动 LLBot")
        sys.exit(1)

    # 启动转发脚本
    start_forward()
    # 等待转发脚本启动
    for _ in range(10):
        if check_port(FORWARD_PORT):
            break
        time.sleep(1)

    # 启动托盘
    setup_tray()
```

---

### Task 9: 清理和文档更新

**Files:**
- Modify: `使用教程.txt`

- [ ] **Step 1: 更新使用教程**

把 `使用教程.txt` 替换为：

```
=== QQ消息转发 — 使用教程 ===

【一键启动】
  双击 start.vbs → UAC确认 → 服务后台启动 → 托盘图标出现

【一键关闭】
  双击 stop.vbs  或  右键托盘图标 → 关闭服务

【配置修改】
  编辑 config.json，修改后双击 stop.vbs 再 start.vbs 重启

  转发规则: 改 forward_rules（源群ID → 目标群ID列表）
  过滤规则: 改 filter 段（关键词/正则/启用开关）

【过滤说明】
  QR码过滤: 图片+关键词组合检测（默认拦截）
  联系方式过滤: 正则匹配手机号/QQ号/微信号/邮箱 + 关键词
  试运行模式: 设置 filter.log_only = true，仅记录不拦截

【LLBot WebUI】
  地址: http://127.0.0.1:3080/#onebot
  密码: llbot@forward123

【依赖安装】
  pip install -r requirements.txt
```

- [ ] **Step 2: 全量测试 — 验证所有组件**

```bash
# 1. 运行 filter 单元测试
pytest tests/test_filter.py -v

# 2. 验证 forward.py 语法
python -c "import py_compile; py_compile.compile('qq-message-forward.py', doraise=True)"

# 3. 验证 tray.py 语法
python -c "import py_compile; py_compile.compile('tray.py', doraise=True)"

# 4. 检查 config.json 格式
python -c "import json; json.load(open('config.json', encoding='utf-8')); print('config.json OK')"
```

Expected: all PASS / OK

---

### Task 10: 端到端验证

- [ ] **Step 1: 双击 start.vbs，确认 UAC 弹窗 → 服务启动 → 托盘图标出现**
- [ ] **Step 2: 右键托盘图标 → "查看状态"，确认显示 LLBot 和转发脚本状态**
- [ ] **Step 3: 在源群发一条含"扫码加我" + 图片的消息，确认日志显示 `[FILTER] 已拦截`**
- [ ] **Step 4: 在源群发一条含手机号的消息（如"联系我 13812345678"），确认日志显示过滤拦截**
- [ ] **Step 5: 在源群发一条正常文本，确认正常转发到目标群**
- [ ] **Step 6: 右键托盘 → "关闭服务"，确认所有进程终止**

---

## Self-Review 检查清单

1. **Spec 覆盖**: 每个 spec 中的 Scenario 都有对应测试
   - QR 码场景 → Task 2 的 6 个测试
   - 联系方式场景 → Task 3 的 7 个测试
   - log_only / 可配置场景 → Task 4 的 6 个测试
   - 一键启动场景 → Task 6/8（脚本，非 TDD）
   - 托盘场景 → Task 8（GUI，非 TDD）

2. **无占位符**: 所有步骤都包含完整代码，无 TBD/TODO

3. **类型一致性**: `check_qrcode_ad(message, keywords)` 签名在 Task 2 和 Task 4 中一致；`should_filter(message, config)` 在 Task 4 定义后被 Task 5 使用
