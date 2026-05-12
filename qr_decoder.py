"""QR 码图像解码模块 — pyzbar 真·二维码识别"""
import time
import re
from typing import List, Optional, Dict
from io import BytesIO

import requests
from PIL import Image

# pyzbar 导入保护：缺失或 DLL 加载失败时降级
try:
    from pyzbar.pyzbar import decode as zbar_decode
    PYZBAR_AVAILABLE = True
except Exception:
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
    按优先级：URL域名 -> 联系方式 -> 广告关键词
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
    """处理消息中的图片：下载->解码->分析，返回命中原因或 None"""
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
