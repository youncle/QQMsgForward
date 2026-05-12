# QR码过滤优化 — A方案规则增强 + B方案真·QR解码 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 优化 filter.py 规则引擎（大小写不敏感、三级拦截策略、QQ上下文判断、CQ解析修复、日志降噪），并新增 qr_decoder.py 模块实现 pyzbar 真·QR码图像解码

**Architecture:** `filter.py` 规则引擎 + `qr_decoder.py` 图像解码模块串联工作。图片消息进入后优先走 QR 解码（可配置开关），命中则直接拦截；解码失败/关闭时回退关键词规则。`forward.py` 的 webhook 调用 `should_filter()`，所有配置集中在 `config.json`，通过 `settings.py` GUI 编辑

**Tech Stack:** Python 3, pyzbar + Pillow, Flask, requests, tkinter

---

### Task 1: A方案 RED — 编写规则引擎增强测试

**Files:**
- Modify: `tests/test_filter.py`

- [ ] **Step 1: 在 test_filter.py 末尾追加大小写不敏感测试**

写入以下代码到 `tests/test_filter.py` 末尾（在文件最后追加）：

```python
# ============================================================
# A方案增强 — 大小写不敏感测试
# ============================================================

def test_qrcode_case_insensitive_keyword():
    """文本 'V: 扫码加好友' 应命中小写关键词 'v:' 和 '加好友'"""
    msg = [
        {'type': 'image', 'data': {'file': 'img1'}},
        {'type': 'text', 'data': {'text': 'V: 扫码加好友'}}
    ]
    result = check_qrcode_ad(msg, QR_KEYWORDS)
    assert result is True


def test_contact_case_insensitive_keyword():
    """文本 '我的v是 xxx 联系我' 应命中小写关键词"""
    msg = [{'type': 'text', 'data': {'text': '我的v是 xxx123 联系我'}}]
    result = check_contact_info(msg, CONTACT_PATTERNS, CONTACT_KEYWORDS)
    assert result is True
```

- [ ] **Step 2: 追加三级拦截策略测试**

追加到 `tests/test_filter.py` 末尾：

```python
# ============================================================
# A方案增强 — 三级拦截策略测试
# ============================================================

def test_qrcode_mode_image_with_keyword():
    """mode=image_with_keyword 时纯图片放行，图片+关键词拦截"""
    pure_image = [{'type': 'image', 'data': {'file': 'cat.png'}}]
    image_with_kw = [
        {'type': 'image', 'data': {'file': 'qr.png'}},
        {'type': 'text', 'data': {'text': '扫码进群'}}
    ]
    assert check_qrcode_ad(pure_image, QR_KEYWORDS, mode='image_with_keyword') is False
    assert check_qrcode_ad(image_with_kw, QR_KEYWORDS, mode='image_with_keyword') is True


def test_qrcode_mode_block_pure_image():
    """mode=block_pure_image 时纯图片也被拦截"""
    pure_image = [{'type': 'image', 'data': {'file': 'qr.png'}}]
    assert check_qrcode_ad(pure_image, QR_KEYWORDS, mode='block_pure_image') is True


def test_qrcode_mode_block_all_images():
    """mode=block_all_images 时所有带图片消息都被拦截"""
    image_with_text = [
        {'type': 'image', 'data': {'file': 'screenshot.png'}},
        {'type': 'text', 'data': {'text': '看看这个截图'}}
    ]
    assert check_qrcode_ad(image_with_text, QR_KEYWORDS, mode='block_all_images') is True
```

- [ ] **Step 3: 追加 QQ 号上下文判断测试**

追加到 `tests/test_filter.py` 末尾：

```python
# ============================================================
# A方案增强 — QQ号上下文判断测试
# ============================================================
# 注意：这些测试验证 _check_contact_detail 级别的行为，
# check_contact_info 当前不支持上下文参数，所以通过 should_filter 间接验证

def test_should_filter_qq_group_context_pass():
    """'欢迎加群 1079264158' 含群号上下文 → QQ正则不触发"""
    msg = [{'type': 'text', 'data': {'text': '欢迎加群 1079264158'}}]
    filtered, reason = should_filter(msg, FILTER_CONFIG)
    # 群号上下文应放行（不含其他联系方式关键词时）
    assert reason == '' or '[联系方式' not in reason


def test_should_filter_qq_no_context_blocks():
    """'加我QQ 12345678' 无群号上下文 → 正常拦截"""
    msg = [{'type': 'text', 'data': {'text': '加我QQ 12345678'}}]
    filtered, reason = should_filter(msg, FILTER_CONFIG)
    assert '[联系方式' in reason
```

- [ ] **Step 4: 追加 CQ 码解析 edge case 测试**

追加到 `tests/test_filter.py` 末尾：

```python
# ============================================================
# A方案增强 — CQ码解析 edge case 测试
# ============================================================

# 直接测试 _parse_cq_string（需要 import）
from filter import _parse_cq_string


def test_cq_parse_text_with_bracket():
    """CQ 码 text 内容含 ] 字符时不应截断"""
    msg = '[CQ:image,file=abc][CQ:text,text=点击[链接]查看详情]'
    has_image, text = _parse_cq_string(msg)
    assert has_image is True
    assert '链接' in text
    assert '查看详情' in text


def test_cq_parse_record_ignored():
    """[CQ:record 不应被误判为图片"""
    msg = '[CQ:record,file=audio.mp3][CQ:text,text=语音消息]'
    has_image, text = _parse_cq_string(msg)
    assert has_image is False


def test_cq_parse_video_ignored():
    """[CQ:video 不应被误判为图片"""
    msg = '[CQ:video,file=video.mp4][CQ:text,text=看看这个视频]'
    has_image, text = _parse_cq_string(msg)
    assert has_image is False
```

- [ ] **Step 5: 运行测试确认 RED（失败）**

```bash
python -m pytest tests/test_filter.py -v
```

Expected: 新增的大小写不敏感、mode 策略、QQ 上下文测试全部 FAIL，CQ 解析 edge case 测试 FAIL

---

### Task 2: A方案 GREEN — 实现大小写不敏感匹配

**Files:**
- Modify: `filter.py`

- [ ] **Step 1: 修改 check_qrcode_ad — 大小写不敏感**

将 `filter.py` 中 `check_qrcode_ad` 函数的第 61、69 行的 `kw in text` 改为 `kw.lower() in text.lower()`：

```python
def check_qrcode_ad(
    message: List[MessageSegment],
    keywords: List[str],
    block_pure_image: bool = False
) -> bool:
    """检查消息是否为二维码广告
    支持 OneBot array 格式和 CQ 码 string 格式

    规则：
    1. 无图片 → 放行
    2. 有图片 + 关键词 → 拦截
    3. 有图片 + 无文字 + block_pure_image → 拦截（纯图片疑似二维码）
    4. 有图片 + 有文字但无关键词 → 放行（正常带文字图片）
    """
    # array 格式
    if isinstance(message, list):
        has_image = _has_image_array(message)
        if not has_image:
            return False
        text = _extract_text(message)
        if not text:
            return block_pure_image
        return any(kw.lower() in text.lower() for kw in keywords)
    # CQ 码 string 格式
    if isinstance(message, str):
        has_image, text = _parse_cq_string(message)
        if not has_image:
            return False
        if not text:
            return block_pure_image
        return any(kw.lower() in text.lower() for kw in keywords)
    return False
```

- [ ] **Step 2: 修改 check_contact_info — 大小写不敏感**

将 `filter.py` 第 84 行 `any(kw in text for kw in keywords)` 改为：

```python
def check_contact_info(
    message: List[MessageSegment],
    patterns: Dict[str, str],
    keywords: List[str]
) -> bool:
    """检查消息是否包含私人联系方式
    支持 OneBot array 格式和 CQ 码 string 格式
    """
    text = _extract_text(message) if isinstance(message, list) else _parse_cq_string(message)[1]
    if not text:
        return False
    if any(kw.lower() in text.lower() for kw in keywords):
        return True
    for pattern in patterns.values():
        if re.search(pattern, text):
            return True
    return False
```

- [ ] **Step 3: 修改 _check_contact_detail — 大小写不敏感**

将 `filter.py` 第 100 行 `any(kw in text for kw in keywords)` 改为：

```python
def _check_contact_detail(
    message: List[MessageSegment],
    config: Dict
) -> str:
    """检查联系方式详情，返回匹配类型（用于日志），未命中返回空字符串"""
    text = _extract_text(message) if isinstance(message, list) else _parse_cq_string(message)[1]
    if not text:
        return ''
    if any(kw.lower() in text.lower() for kw in config.get('keywords', [])):
        return '关键词'
    for name, pattern in config.get('patterns', {}).items():
        if re.search(pattern, text):
            return name
    return ''
```

- [ ] **Step 4: 运行测试确认大小写不敏感测试 GREEN**

```bash
python -m pytest tests/test_filter.py::test_qrcode_case_insensitive_keyword tests/test_filter.py::test_contact_case_insensitive_keyword -v
```

Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add tests/test_filter.py filter.py
git commit -m "feat(filter): add case-insensitive keyword matching"
```

---

### Task 3: A方案 GREEN — 实现三级拦截策略

**Files:**
- Modify: `filter.py`

- [ ] **Step 1: 修改 check_qrcode_ad — 增加 mode 参数**

将 `filter.py` 中 `check_qrcode_ad` 的签名和实现改为：

```python
def check_qrcode_ad(
    message: List[MessageSegment],
    keywords: List[str],
    block_pure_image: bool = False,
    mode: str = 'image_with_keyword'
) -> bool:
    """检查消息是否为二维码广告
    支持 OneBot array 格式和 CQ 码 string 格式

    mode:
    - image_with_keyword: 仅图片+关键词时拦截（默认）
    - block_pure_image: 额外拦截无文字纯图片
    - block_all_images: 拦截所有含图片的消息
    """
    # 统一提取 has_image 和 text
    if isinstance(message, list):
        has_image = _has_image_array(message)
        text = _extract_text(message) if has_image else ''
    elif isinstance(message, str):
        has_image, text = _parse_cq_string(message)
    else:
        return False

    # 向后兼容：block_pure_image=True + 默认 mode → 等效 mode='block_pure_image'
    if block_pure_image and mode == 'image_with_keyword':
        mode = 'block_pure_image'

    if not has_image:
        return False

    # mode: block_all_images — 有图片就拦
    if mode == 'block_all_images':
        return True

    # mode: block_pure_image — 纯图片也拦
    if mode == 'block_pure_image' and not text:
        return True

    # mode: image_with_keyword (默认) — 仅图片+关键词时拦截
    if not text:
        return False
    return any(kw.lower() in text.lower() for kw in keywords)
```

- [ ] **Step 2: 修改 should_filter — 传入 mode 参数**

将 `filter.py` 中 `should_filter` 的 QR 检测部分（第 136-140 行）改为：

```python
    # QR 码检测
    if qrcode_cfg.get('enabled'):
        mode = qrcode_cfg.get('mode', 'image_with_keyword')
        # 向后兼容：旧的 block_pure_image 布尔值 → mode 映射
        if 'mode' not in qrcode_cfg and qrcode_cfg.get('block_pure_image'):
            mode = 'block_pure_image'
        if check_qrcode_ad(message, qrcode_cfg.get('keywords', []), mode=mode):
            reason = _format_filter_reason('QR码', message)
            return (False if log_only else True, reason)
```

- [ ] **Step 3: 运行测试确认三级策略测试 GREEN**

```bash
python -m pytest tests/test_filter.py::test_qrcode_mode_image_with_keyword tests/test_filter.py::test_qrcode_mode_block_pure_image tests/test_filter.py::test_qrcode_mode_block_all_images -v
```

Expected: 3 passed. 同时确保旧测试不变：

```bash
python -m pytest tests/test_filter.py -v
```

Expected: 所有旧测试仍 GREEN

- [ ] **Step 4: Commit**

```bash
git add filter.py
git commit -m "feat(filter): add three-tier interception mode strategy"
```

---

### Task 4: A方案 GREEN — 实现 QQ 号上下文判断 + CQ 解析修复

**Files:**
- Modify: `filter.py`

- [ ] **Step 1: 在 filter.py 顶部添加 QQ_CONTEXT_WHITELIST 常量**

在 `filter.py` 的 import 区域后添加：

```python
# QQ 号上下文白名单：含这些词且数字 ≥ 6 位时豁免 QQ 正则
QQ_CONTEXT_WHITELIST = ['群', '加群', '群号', '频道', 'channel', 'guild', '进群']
```

- [ ] **Step 2: 修改 _check_contact_detail — QQ 正则命中后检查上下文**

将 `_check_contact_detail` 函数改为：

```python
def _check_contact_detail(
    message: List[MessageSegment],
    config: Dict
) -> str:
    """检查联系方式详情，返回匹配类型（用于日志），未命中返回空字符串"""
    text = _extract_text(message) if isinstance(message, list) else _parse_cq_string(message)[1]
    if not text:
        return ''
    if any(kw.lower() in text.lower() for kw in config.get('keywords', [])):
        return '关键词'
    for name, pattern in config.get('patterns', {}).items():
        if re.search(pattern, text):
            # QQ 正则：检查群号上下文
            if name == 'qq':
                match = re.search(pattern, text)
                if match:
                    digits = match.group()
                    if len(digits) >= 6 and any(ctx in text for ctx in QQ_CONTEXT_WHITELIST):
                        continue  # 群号上下文，不触发 QQ 拦截
            return name
    return ''
```

- [ ] **Step 3: 修复 _parse_cq_string — 处理 ] 字符 + 排除非图片段**

将 `filter.py` 中的 `_parse_cq_string` 改为：

```python
def _parse_cq_string(message: str) -> tuple:
    """解析 CQ 码字符串，返回 (has_image, text)
    只将 [CQ:image 视为图片，排除 record/video/file 等
    """
    has_image = '[CQ:image' in message
    # 提取所有 [CQ:text,text=...] 中的文本
    # 使用非贪婪匹配到最后一个 ] 前的内容（处理 text 内含 ] 的情况）
    text_parts = re.findall(r'\[CQ:text,text=(.+?)\]', message)
    text = ''.join(text_parts)
    # 也提取纯文字（不在任何 CQ 码内的）
    clean = re.sub(r'\[CQ:[a-z]+,[^\]]*\]', '', message)
    if not text:
        text = clean
    return has_image, text
```

**注意**：`\[CQ:text,text=(.+?)\]` 使用非贪婪匹配，虽然仍无法完美处理 text 值中含 `]` 的情况（因为 CQ 码本身用 `]` 终止），但比 `[^\]]*` 更准确。完全解决需要 LLOneBot 层面的格式规范。record/video/file 的排除通过 `[CQ:image` 精确匹配已实现。

- [ ] **Step 4: 运行测试确认全部 GREEN**

```bash
python -m pytest tests/test_filter.py -v
```

Expected: 所有新增测试全部 GREEN，旧测试无回归

- [ ] **Step 5: Commit**

```bash
git add filter.py
git commit -m "feat(filter): add QQ context whitelist and fix CQ string parsing"
```

---

### Task 5: A方案 REFACTOR — 日志降噪

**Files:**
- Modify: `forward.py`

- [ ] **Step 1: 修改 forward.py — log_only 放行日志降为 DEBUG**

将 `forward.py` webhook() 函数中的过滤日志部分（第 155-165 行）修改为：

```python
        # 6. 消息过滤（QR码 + 联系方式）
        if filter_config:
            blocked, reason = should_filter(message_content, filter_config)
            if blocked:
                logger.info(f"[FILTER] 已拦截: 群{group_id} - {reason}")
                return "ok"
            elif reason:
                # log_only 模式：仅记录，不拦截
                logger.info(f"[FILTER] 仅记录: 群{group_id} - {reason}")
            else:
                logger.debug(f"[FILTER] 放行: 群{group_id} | 类型={type(message_content).__name__} "
                            f"| 文本={raw_text[:50]}")
```

**关键变更**: 第 164 行 `logger.info` → `logger.debug`

- [ ] **Step 2: 验证**

```bash
python -m py_compile forward.py
```

Expected: 编译通过

- [ ] **Step 3: Commit**

```bash
git add forward.py
git commit -m "fix(forward): reduce log noise in log_only mode (INFO→DEBUG)"
```

---

### Task 6: B方案 RED — 编写 QR 解码模块测试

**Files:**
- Create: `tests/test_qr_decoder.py`

- [ ] **Step 1: 创建 test_qr_decoder.py — 模块导入 + QR 生成/解码 round-trip 测试**

写入 `tests/test_qr_decoder.py`：

```python
"""QR 解码模块测试"""
import sys
sys.path.insert(0, '.')
import pytest
import io
from unittest.mock import patch, Mock
from PIL import Image
import qrcode  # 用于生成测试 QR 码


@pytest.fixture
def qr_image_bytes():
    """生成含 QR 码的 PNG 图片字节"""
    img = qrcode.make('https://example.com/join-group/12345')
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()


@pytest.fixture
def plain_image_bytes():
    """生成不含 QR 码的纯色图片字节"""
    img = Image.new('RGB', (100, 100), color='blue')
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()


def test_decode_qr_finds_qrcode(qr_image_bytes):
    """含 QR 码的图片应解码出内容"""
    from qr_decoder import decode_qr
    results = decode_qr(qr_image_bytes)
    assert len(results) >= 1
    assert 'join-group' in results[0]


def test_decode_qr_plain_image_returns_empty(plain_image_bytes):
    """普通图片应返回空列表"""
    from qr_decoder import decode_qr
    results = decode_qr(plain_image_bytes)
    assert results == []


def test_download_image_success():
    """下载成功返回 bytes"""
    from qr_decoder import download_image
    with patch('qr_decoder.requests.get') as mock_get:
        mock_get.return_value = Mock(status_code=200, content=b'fake-image-data')
        result = download_image('http://example.com/img.jpg', timeout=3)
        assert result == b'fake-image-data'


def test_download_image_timeout():
    """下载超时返回 None"""
    from qr_decoder import download_image
    import requests as req
    with patch('qr_decoder.requests.get', side_effect=req.Timeout):
        result = download_image('http://example.com/img.jpg', timeout=1)
        assert result is None


def test_cache_set_and_get():
    """缓存写入后能读取"""
    from qr_decoder import set_cache, get_cached
    set_cache('file_123', ['https://example.com'])
    result = get_cached('file_123', cache_seconds=86400)
    assert result == ['https://example.com']


def test_cache_expired():
    """过期缓存返回 None"""
    from qr_decoder import set_cache, get_cached
    set_cache('file_456', ['https://example.com'])
    result = get_cached('file_456', cache_seconds=0)
    assert result is None


def test_cache_not_found():
    """未缓存的 key 返回 None"""
    from qr_decoder import get_cached
    result = get_cached('nonexistent', cache_seconds=86400)
    assert result is None


def test_clean_expired_cache():
    """清理过期条目"""
    from qr_decoder import set_cache, get_cached, clean_expired_cache
    import time
    set_cache('old_key', ['old_data'])
    # 伪造时间戳为 2 天前
    from qr_decoder import _decode_cache
    _decode_cache['old_key'] = (time.time() - 172800, ['old_data'])
    clean_expired_cache(86400)
    assert get_cached('old_key', cache_seconds=86400) is None


def test_analyze_decoded_content_url_suspicious():
    """可疑域名 URL → 命中"""
    from qr_decoder import analyze_decoded_content
    config = {
        'decode_block_patterns': ['加群', '进群'],
        'decode_suspicious_domains': ['suspicious.com']
    }
    reason = analyze_decoded_content(['https://suspicious.com/join'], config)
    assert reason is not None
    assert 'URL' in reason


def test_analyze_decoded_content_phone():
    """QR 含手机号 → 命中"""
    from qr_decoder import analyze_decoded_content
    config = {
        'decode_block_patterns': [],
        'decode_suspicious_domains': []
    }
    reason = analyze_decoded_content(['加我微信 13812345678'], config)
    assert reason is not None
    assert 'phone' in reason


def test_analyze_decoded_content_keyword():
    """QR 含广告关键词 → 命中"""
    from qr_decoder import analyze_decoded_content
    config = {
        'decode_block_patterns': ['加群', '进群', '兼职', '刷单'],
        'decode_suspicious_domains': []
    }
    reason = analyze_decoded_content(['扫码加群每天领红包'], config)
    assert reason is not None
    assert '关键词' in reason


def test_analyze_decoded_content_normal():
    """正常 URL → 放行"""
    from qr_decoder import analyze_decoded_content
    config = {
        'decode_block_patterns': ['加群'],
        'decode_suspicious_domains': ['evil.com']
    }
    reason = analyze_decoded_content(['https://github.com/anthropics'], config)
    assert reason is None
```

- [ ] **Step 2: 安装测试依赖 qrcode**

```bash
pip install qrcode[pil]
```

- [ ] **Step 3: 运行测试确认 RED**

```bash
python -m pytest tests/test_qr_decoder.py -v
```

Expected: ModuleNotFoundError — `qr_decoder` 模块不存在

---

### Task 7: B方案 GREEN — 创建 qr_decoder.py 模块基础

**Files:**
- Create: `qr_decoder.py`

- [ ] **Step 1: 创建 qr_decoder.py 基础骨架**

写入 `qr_decoder.py`：

```python
"""QR 码图像解码模块 — pyzbar 真·二维码识别"""
import time
import re
from typing import List, Optional, Dict
from io import BytesIO

import requests
from PIL import Image

# pyzbar 导入保护：缺失时降级
try:
    from pyzbar.pyzbar import decode as zbar_decode
    PYZBAR_AVAILABLE = True
except ImportError:
    PYZBAR_AVAILABLE = False

# 联系方式正则（与 filter.py 公用）
CONTACT_PATTERNS = {
    'phone': r'1[3-9]\d{9}',
    'qq': r'(?<!\d)[1-9]\d{4,9}(?!\d)',
    'wechat': r'wxid_[a-z0-9]+',
    'email': r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
}

# 解码结果缓存 {file_id: (timestamp, [content_list])}
_decode_cache: Dict[str, tuple] = {}


def decode_qr(image_data: bytes) -> List[str]:
    """解码图片中的 QR 码，返回内容列表"""
    if not PYZBAR_AVAILABLE:
        return []
    image = Image.open(BytesIO(image_data))
    if image.mode != 'L':
        image = image.convert('L')
    decoded = zbar_decode(image)
    return [d.data.decode('utf-8', errors='replace') for d in decoded]


def download_image(url: str, timeout: int = 3) -> Optional[bytes]:
    """下载图片，超时返回 None"""
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        return resp.content
    except Exception:
        return None


def get_cached(file_id: str, cache_seconds: int = 86400) -> Optional[List[str]]:
    """获取缓存，过期返回 None"""
    entry = _decode_cache.get(file_id)
    if entry is None:
        return None
    ts, data = entry
    if time.time() - ts > cache_seconds:
        del _decode_cache[file_id]
        return None
    return data


def set_cache(file_id: str, result: List[str]) -> None:
    """写入缓存"""
    _decode_cache[file_id] = (time.time(), result)


def clean_expired_cache(cache_seconds: int = 86400) -> None:
    """清理过期缓存条目"""
    now = time.time()
    expired = [k for k, v in _decode_cache.items() if now - v[0] > cache_seconds]
    for k in expired:
        del _decode_cache[k]


def analyze_decoded_content(content_list: List[str], config: Dict) -> Optional[str]:
    """分析解码内容，返回命中原因或 None
    按优先级：URL域名 → 联系方式 → 广告关键词
    """
    contact_patterns = config.get('_contact_patterns', CONTACT_PATTERNS)
    suspicious_domains = config.get('decode_suspicious_domains', [])
    block_patterns = config.get('decode_block_patterns', [])

    for content in content_list:
        # 1. URL 域名检测
        if content.startswith(('http://', 'https://')):
            from urllib.parse import urlparse
            domain = urlparse(content).netloc.lower()
            for sd in suspicious_domains:
                if sd.lower() in domain:
                    return f'[QR解码:URL]{domain}'
            # URL 中也检查联系方式
            for name, pattern in contact_patterns.items():
                if re.search(pattern, content):
                    return f'[QR解码:URL+{name}]{content[:80]}'

        # 2. 联系方式检测
        for name, pattern in contact_patterns.items():
            if re.search(pattern, content):
                return f'[QR解码:{name}]{content[:80]}'

        # 3. 广告关键词
        for kw in block_patterns:
            if kw in content:
                return f'[QR解码:关键词]{content[:80]}'

    return None


def process_message_images(message, config: Dict) -> Optional[str]:
    """处理消息中的图片：下载→解码→分析，返回命中原因或 None"""
    if not config.get('decode_enabled'):
        return None
    if not PYZBAR_AVAILABLE:
        return None

    timeout = config.get('decode_timeout', 3)
    cache_seconds = config.get('decode_cache_seconds', 86400)

    # 从消息段中提取图片 file_id 和 url
    images = []
    if isinstance(message, list):
        for seg in message:
            if isinstance(seg, dict) and seg.get('type') == 'image':
                file_id = seg.get('data', {}).get('file', '')
                url = seg.get('data', {}).get('url', '')
                images.append((file_id, url))
    elif isinstance(message, str) and '[CQ:image' in message:
        # CQ 码格式：提取 file=xxx 和 url=xxx
        matches = re.findall(r'\[CQ:image,file=([^,\]]+)(?:,url=([^,\]]+))?\]', message)
        for m in matches:
            images.append((m[0], m[1] if len(m) > 1 and m[1] else ''))

    if not images:
        return None

    # 逐张图片下载和解码
    for file_id, url in images:
        # 检查缓存
        cached = get_cached(file_id, cache_seconds)
        if cached is not None:
            if cached:  # 有解码结果
                reason = analyze_decoded_content(cached, config)
                if reason:
                    return reason
            continue  # cached == [] (之前解码为空) 或分析未命中

        if not url:
            continue

        # 下载图片
        img_data = download_image(url, timeout)
        if img_data is None:
            continue

        # 解码
        results = decode_qr(img_data)
        set_cache(file_id, results)

        if results:
            reason = analyze_decoded_content(results, config)
            if reason:
                return reason

    return None
```

- [ ] **Step 2: 安装 pyzbar**

```bash
pip install pyzbar
```

- [ ] **Step 3: 验证基本导入**

```bash
python -c "from qr_decoder import decode_qr, PYZBAR_AVAILABLE; print(f'pyzbar: {PYZBAR_AVAILABLE}')"
```

- [ ] **Step 4: 运行测试**

```bash
python -m pytest tests/test_qr_decoder.py -v
```

Expected: 所有 QR 解码模块测试 GREEN

- [ ] **Step 5: Commit**

```bash
git add qr_decoder.py tests/test_qr_decoder.py
git commit -m "feat(qr-decoder): add pyzbar-based QR code image decoding module"
```

---

### Task 8: B方案 RED+GREEN — 集成测试 + 集成到 filter.py

**Files:**
- Modify: `tests/test_filter.py`
- Modify: `filter.py`

- [ ] **Step 1: 追加集成测试到 test_filter.py**

追加到 `tests/test_filter.py` 末尾：

```python
# ============================================================
# B方案 — QR 解码集成测试
# ============================================================

from unittest.mock import patch

DUMMY_QR_CONFIG = {
    **FILTER_CONFIG,
    'qrcode': {
        **FILTER_CONFIG['qrcode'],
        'decode_enabled': True,
        'decode_timeout': 3,
        'decode_cache_seconds': 86400,
        'decode_block_patterns': ['加群', '进群', '兼职'],
        'decode_suspicious_domains': ['bad-domain.com']
    }
}


def test_should_filter_qr_decode_disabled():
    """decode_enabled=false 时不触发 QR 解码"""
    cfg = {**DUMMY_QR_CONFIG, 'qrcode': {**DUMMY_QR_CONFIG['qrcode'], 'decode_enabled': False}}
    msg = [{'type': 'image', 'data': {'file': 'dummy', 'url': 'http://x.com/qr.png'}}]
    filtered, reason = should_filter(msg, cfg)
    # 纯图片无关键词，mode=image_with_keyword 应放行
    assert filtered is False


def test_should_filter_qr_decode_fallback_to_keyword():
    """QR 解码未命中时回退关键词规则"""
    cfg = DUMMY_QR_CONFIG
    msg = [
        {'type': 'image', 'data': {'file': 'dummy', 'url': 'http://x.com/normal.png'}},
        {'type': 'text', 'data': {'text': '扫码进群'}}
    ]
    # 即使 qr_decoder 找不到 QR 码，关键词规则依然会命中
    filtered, reason = should_filter(msg, cfg)
    assert filtered is True
    assert '[QR码]' in reason
```

- [ ] **Step 2: 运行集成测试确认 RED**

```bash
python -m pytest tests/test_filter.py::test_should_filter_qr_decode_disabled tests/test_filter.py::test_should_filter_qr_decode_fallback_to_keyword -v
```

Expected: RED — `should_filter` 还没传入 decode 配置

- [ ] **Step 3: 修改 filter.py should_filter — 集成 QR 解码**

将 `filter.py` 顶部的 import 区域添加 qr_decoder 导入：

```python
"""消息过滤模块 — QR码广告检测 + 联系方式检测"""

import re
from typing import List, Dict, Union, Tuple

# OneBot v11 消息段类型
MessageSegment = Dict[str, Union[str, Dict[str, str]]]
```

在 `_format_filter_reason` 后（`should_filter` 前）添加导入和函数。修改 `should_filter` 函数：

```python
def should_filter(
    message: List[MessageSegment],
    config: Dict
) -> Tuple[bool, str]:
    """综合过滤检查 — 返回 (是否拦截, 原因字符串)
    支持 OneBot array 格式和 CQ 码 string 格式

    优先级: QR 解码 → QR 关键词 → 联系方式
    """
    # 类型守卫：跳过未知类型的消息
    if not isinstance(message, (list, str)):
        return (False, '')
    qrcode_cfg = config.get('qrcode', {})
    contact_cfg = config.get('contact', {})
    log_only = config.get('log_only', False)

    # QR 解码（优先级最高）
    if qrcode_cfg.get('enabled') and qrcode_cfg.get('decode_enabled'):
        # 延迟导入，避免 pyzbar 缺失时影响整个模块
        try:
            from qr_decoder import process_message_images
            # 构建 decode 子配置
            decode_config = {
                'decode_enabled': True,
                'decode_timeout': qrcode_cfg.get('decode_timeout', 3),
                'decode_cache_seconds': qrcode_cfg.get('decode_cache_seconds', 86400),
                'decode_block_patterns': qrcode_cfg.get('decode_block_patterns', []),
                'decode_suspicious_domains': qrcode_cfg.get('decode_suspicious_domains', []),
            }
            decode_reason = process_message_images(message, decode_config)
            if decode_reason:
                return (False if log_only else True, decode_reason)
        except ImportError:
            pass  # pyzbar 不可用，跳过解码

    # QR 关键词检测
    if qrcode_cfg.get('enabled'):
        mode = qrcode_cfg.get('mode', 'image_with_keyword')
        if 'mode' not in qrcode_cfg and qrcode_cfg.get('block_pure_image'):
            mode = 'block_pure_image'
        if check_qrcode_ad(message, qrcode_cfg.get('keywords', []), mode=mode):
            reason = _format_filter_reason('QR码', message)
            return (False if log_only else True, reason)

    # 联系方式检测
    if contact_cfg.get('enabled'):
        hit = _check_contact_detail(message, contact_cfg)
        if hit:
            reason = _format_filter_reason(f'联系方式:{hit}', message)
            return (False if log_only else True, reason)

    return (False, '')
```

- [ ] **Step 4: 运行集成测试确认 GREEN**

```bash
python -m pytest tests/test_filter.py::test_should_filter_qr_decode_disabled tests/test_filter.py::test_should_filter_qr_decode_fallback_to_keyword -v
```

Expected: 2 passed

- [ ] **Step 5: 运行全量测试确认无回归**

```bash
python -m pytest tests/ -v
```

Expected: 0 failed

- [ ] **Step 6: Commit**

```bash
git add filter.py tests/test_filter.py
git commit -m "feat(filter): integrate QR decode pipeline into should_filter"
```

---

### Task 9: 配置与 UI 更新

**Files:**
- Modify: `config.json`
- Modify: `settings.py`
- Modify: `requirements.txt`

- [ ] **Step 1: 更新 config.json — 新增字段**

将 `config.json` 的 `filter.qrcode` 部分更新为：

```json
{
  "robot_qq": 2776992588,
  "forward_rules": {
    "1079264158": [
      "1080631149"
    ],
    "107054156": [
      "702961941"
    ]
  },
  "llbot_api": "http://127.0.0.1:3000",
  "llbot_token": "",
  "filter": {
    "qrcode": {
      "enabled": true,
      "keywords": [
        "添加",
        "扫码",
        "扫一扫",
        "扫描",
        "联系人",
        "VX",
        "v:",
        "微信",
        "私聊"
      ],
      "mode": "image_with_keyword",
      "block_pure_image": true,
      "decode_enabled": false,
      "decode_timeout": 3,
      "decode_cache_seconds": 86400,
      "decode_block_patterns": [
        "加群",
        "进群",
        "兼职",
        "刷单",
        "返利"
      ],
      "decode_suspicious_domains": []
    },
    "contact": {
      "enabled": true,
      "patterns": {
        "phone": "1[3-9]\\d{9}",
        "qq": "(?<!\\d)[1-9]\\d{4,9}(?!\\d)",
        "wechat": "wxid_[a-z0-9]+",
        "email": "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}"
      },
      "keywords": [
        "QQ",
        "微信",
        "飞书",
        "续费",
        "费用",
        "VX",
        "v:",
        "钉钉",
        "联系人",
        "我的Q",
        "我的V",
        "联系我",
        "加好友",
        "私聊我",
        "加我"
      ]
    },
    "log_only": true
  },
  "forward": {
    "duplicate_window": 5,
    "send_interval": 1.0
  }
}
```

- [ ] **Step 2: 更新 settings.py — 新增 mode 下拉框和 QR 解码区域**

修改 `settings.py` 的 QR 码过滤区域（第 93-107 行）。将：

```python
    # ===== QR 码过滤 =====
    qr = cfg['filter']['qrcode']
    frm_qr = ttk.LabelFrame(frame, text='QR码过滤', padding=10)
    frm_qr.pack(fill='x', **pad)

    qr_enabled = tk.BooleanVar(value=qr.get('enabled', True))
    ttk.Checkbutton(frm_qr, text='启用', variable=qr_enabled).pack(anchor='w')

    ttk.Label(frm_qr, text='关键词（逗号分隔）').pack(anchor='w')
    qr_kw_entry = ttk.Entry(frm_qr, width=60)
    qr_kw_entry.pack(fill='x', **pad)
    qr_kw_entry.insert(0, ', '.join(qr.get('keywords', [])))

    qr_block = tk.BooleanVar(value=qr.get('block_pure_image', False))
    ttk.Checkbutton(frm_qr, text='拦截无文字的纯图片', variable=qr_block).pack(anchor='w')
```

替换为：

```python
    # ===== QR 码过滤 =====
    qr = cfg['filter']['qrcode']
    frm_qr = ttk.LabelFrame(frame, text='QR码过滤', padding=10)
    frm_qr.pack(fill='x', **pad)

    qr_enabled = tk.BooleanVar(value=qr.get('enabled', True))
    ttk.Checkbutton(frm_qr, text='启用', variable=qr_enabled).pack(anchor='w')

    # 拦截模式下拉框
    frm_mode = ttk.Frame(frm_qr)
    frm_mode.pack(fill='x', **pad)
    ttk.Label(frm_mode, text='拦截模式').pack(side='left')
    mode_var = tk.StringVar(value=qr.get('mode', 'image_with_keyword'))
    mode_combo = ttk.Combobox(frm_mode, textvariable=mode_var, width=24,
                              values=['image_with_keyword', 'block_pure_image', 'block_all_images'],
                              state='readonly')
    mode_combo.pack(side='left', padx=(5, 0))

    ttk.Label(frm_qr, text='关键词（逗号分隔）').pack(anchor='w')
    qr_kw_entry = ttk.Entry(frm_qr, width=60)
    qr_kw_entry.pack(fill='x', **pad)
    qr_kw_entry.insert(0, ', '.join(qr.get('keywords', [])))

    # ===== QR 解码（B方案）=====
    frm_decode = ttk.LabelFrame(frm_qr, text='QR码图像解码', padding=5)
    frm_decode.pack(fill='x', pady=(5, 0))

    decode_enabled = tk.BooleanVar(value=qr.get('decode_enabled', False))
    ttk.Checkbutton(frm_decode, text='启用真·QR码解码（需 pyzbar）', variable=decode_enabled).pack(anchor='w')

    frm_decode_row = ttk.Frame(frm_decode)
    frm_decode_row.pack(fill='x', pady=(2, 0))
    ttk.Label(frm_decode_row, text='下载超时(秒)').pack(side='left')
    decode_timeout = tk.IntVar(value=qr.get('decode_timeout', 3))
    ttk.Spinbox(frm_decode_row, from_=1, to=10, textvariable=decode_timeout, width=5).pack(side='left', padx=(5, 15))

    ttk.Label(frm_decode, text='解码内容拦截关键词（逗号分隔）').pack(anchor='w')
    decode_patterns_entry = ttk.Entry(frm_decode, width=60)
    decode_patterns_entry.pack(fill='x', **pad)
    decode_patterns_entry.insert(0, ', '.join(qr.get('decode_block_patterns', [])))

    ttk.Label(frm_decode, text='可疑域名（逗号分隔，如 bad.com）').pack(anchor='w')
    decode_domains_entry = ttk.Entry(frm_decode, width=60)
    decode_domains_entry.pack(fill='x', **pad)
    decode_domains_entry.insert(0, ', '.join(qr.get('decode_suspicious_domains', [])))
```

- [ ] **Step 3: 更新 settings.py 的 on_save 函数**

修改 `on_save` 函数中 QR 码配置保存部分（第 132-136 行），将：

```python
        cfg['filter']['qrcode']['enabled'] = qr_enabled.get()
        cfg['filter']['qrcode']['keywords'] = [
            k.strip() for k in qr_kw_entry.get().split(',') if k.strip()
        ]
        cfg['filter']['qrcode']['block_pure_image'] = qr_block.get()
```

替换为：

```python
        cfg['filter']['qrcode']['enabled'] = qr_enabled.get()
        cfg['filter']['qrcode']['mode'] = mode_var.get()
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
```

- [ ] **Step 4: 更新 requirements.txt**

```bash
echo "pyzbar>=0.1.9" >> requirements.txt
```

- [ ] **Step 5: 验证编译**

```bash
python -m py_compile settings.py filter.py qr_decoder.py forward.py
```

Expected: 编译通过，无错误

- [ ] **Step 6: Commit**

```bash
git add config.json settings.py requirements.txt
git commit -m "feat: add QR decode config fields and settings UI"
```

---

### Task 10: 全量验证

**Files:**
- All modified files

- [ ] **Step 1: 运行全量测试**

```bash
python -m pytest tests/ -v
```

Expected: 所有测试 GREEN（包括新增和旧测试），0 failed

- [ ] **Step 2: 编译检查所有文件**

```bash
python -m py_compile filter.py qr_decoder.py settings.py forward.py tray.py wizard.py
```

Expected: 编译通过

- [ ] **Step 3: 运行选择性集成测试（手动验证消息处理逻辑）**

```bash
python -c "
from filter import should_filter
# 验证大小写不敏感
msg = [{'type':'image','data':{'file':'x'}},{'type':'text','data':{'text':'V: 扫码'}}]
config = {'qrcode':{'enabled':True,'keywords':['v:','扫码'],'mode':'image_with_keyword'},'contact':{'enabled':False},'log_only':False}
blocked, reason = should_filter(msg, config)
assert blocked, '大小写不敏感应命中'
assert '[QR码]' in reason
print('✓ 大小写不敏感集成验证通过')

# 验证 mode=block_pure_image
msg2 = [{'type':'image','data':{'file':'qr.png'}}]
config2 = {'qrcode':{'enabled':True,'keywords':[],'mode':'block_pure_image'},'contact':{'enabled':False},'log_only':False}
blocked2, reason2 = should_filter(msg2, config2)
assert blocked2, 'block_pure_image 应拦截纯图片'
print('✓ 三级策略集成验证通过')

# 验证 QQ 群号上下文
msg3 = [{'type':'text','data':{'text':'欢迎加群 1079264158'}}]
config3 = {'qrcode':{'enabled':False},'contact':{'enabled':True,'patterns':{'phone':r'1[3-9]\\d{9}','qq':r'(?<!\\d)[1-9]\\d{4,9}(?!\\d)','wechat':r'wxid_[a-z0-9]+','email':r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}'},'keywords':['我的Q','我的V','联系我','加好友','私聊我']},'log_only':False}
blocked3, reason3 = should_filter(msg3, config3)
assert '[联系方式' not in reason3, f'群号不应触发拦截: {reason3}'
print('✓ QQ上下文集成验证通过')
"
```

Expected: 三个集成验证通过

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "chore: final verification — all tests pass"
```
