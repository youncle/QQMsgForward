"""消息过滤模块 — QR码广告检测 + 联系方式检测"""

import re
from typing import List, Dict, Union, Tuple

# OneBot v11 消息段类型
MessageSegment = Dict[str, Union[str, Dict[str, str]]]


def _extract_text(message: List[MessageSegment]) -> str:
    """从消息段数组（array 格式）中提取所有纯文本"""
    return ''.join(
        seg.get('data', {}).get('text', '')
        for seg in message
        if isinstance(seg, dict) and seg.get('type') == 'text'
    )


def _has_image_array(message: List[MessageSegment]) -> bool:
    """检查消息数组是否包含图片段"""
    return any(
        isinstance(seg, dict) and seg.get('type') == 'image'
        for seg in message
    )


def _parse_cq_string(message: str) -> tuple:
    """解析 CQ 码字符串，返回 (has_image, text)"""
    has_image = '[CQ:image' in message or '[CQ:pic' in message
    # 提取所有 [CQ:text,text=xxx] 中的文本
    text_parts = re.findall(r'\[CQ:text,text=([^\]]*)\]', message)
    text = ''.join(text_parts)
    # 也提取纯文字（不在 CQ 码内的）
    clean = re.sub(r'\[CQ:[^\]]*\]', '', message)
    text = text or clean
    return has_image, text


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
        return any(kw in text for kw in keywords)
    # CQ 码 string 格式
    if isinstance(message, str):
        has_image, text = _parse_cq_string(message)
        if not has_image:
            return False
        if not text:
            return block_pure_image
        return any(kw in text for kw in keywords)
    return False


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
    if any(kw in text for kw in keywords):
        return True
    for pattern in patterns.values():
        if re.search(pattern, text):
            return True
    return False


def _check_contact_detail(
    message: List[MessageSegment],
    config: Dict
) -> str:
    """检查联系方式详情，返回匹配类型（用于日志），未命中返回空字符串"""
    text = _extract_text(message) if isinstance(message, list) else _parse_cq_string(message)[1]
    if not text:
        return ''
    if any(kw in text for kw in config.get('keywords', [])):
        return '关键词'
    for name, pattern in config.get('patterns', {}).items():
        if re.search(pattern, text):
            return name
    return ''


def _format_filter_reason(category: str, message: List[MessageSegment]) -> str:
    """生成过滤日志中的原因字段"""
    if isinstance(message, list):
        text = _extract_text(message)
        summary = text[:50] if text else '[图片消息]'
    elif isinstance(message, str):
        _, text = _parse_cq_string(message)
        summary = text[:50] if text else '[图片消息]'
    else:
        summary = '[未知格式]'
    return f'[{category}] {summary}'


def should_filter(
    message: List[MessageSegment],
    config: Dict
) -> Tuple[bool, str]:
    """综合过滤检查 — 返回 (是否拦截, 原因字符串)
    支持 OneBot array 格式和 CQ 码 string 格式
    """
    # 类型守卫：跳过未知类型的消息
    if not isinstance(message, (list, str)):
        return (False, '')
    qrcode_cfg = config.get('qrcode', {})
    contact_cfg = config.get('contact', {})
    log_only = config.get('log_only', False)

    # QR 码检测
    if qrcode_cfg.get('enabled'):
        block_pure = qrcode_cfg.get('block_pure_image', False)
        if check_qrcode_ad(message, qrcode_cfg.get('keywords', []), block_pure):
            reason = _format_filter_reason('QR码', message)
            return (False if log_only else True, reason)

    # 联系方式检测
    if contact_cfg.get('enabled'):
        hit = _check_contact_detail(message, contact_cfg)
        if hit:
            reason = _format_filter_reason(f'联系方式:{hit}', message)
            return (False if log_only else True, reason)

    return (False, '')
