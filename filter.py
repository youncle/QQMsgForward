"""消息过滤模块 — QR码广告检测 + 联系方式检测"""

import re
from typing import List, Dict, Union, Tuple

# OneBot v11 消息段类型
MessageSegment = Dict[str, Union[str, Dict[str, str]]]

# QQ 号上下文白名单：含这些词且数字 >= 6 位时豁免 QQ 正则
QQ_CONTEXT_WHITELIST = ['群', '加群', '群号', '频道', 'channel', 'guild', '进群']


def _extract_text(message: List[MessageSegment]) -> str:
    """从消息段数组（array 格式）中提取所有纯文本"""
    if not isinstance(message, list):
        return ""
    return ''.join(
        seg.get('data', {}).get('text', '')
        for seg in message
        if isinstance(seg, dict) and seg.get('type') == 'text'
    )


def _has_image_array(message: List[MessageSegment]) -> bool:
    """检查消息数组是否包含图片段"""
    if not isinstance(message, list):
        return False
    return any(
        isinstance(seg, dict) and seg.get('type') == 'image'
        for seg in message
    )


def _parse_cq_string(message: str) -> tuple:
    """解析 CQ 码字符串，返回 (has_image, text)
    只将 [CQ:image 视为图片，排除 record/video/file 等
    """
    has_image = '[CQ:image' in message
    # 提取所有 [CQ:text,text=...] 中的文本
    text_parts = re.findall(r'\[CQ:text,text=(.+?)\]', message)
    text = ''.join(text_parts)
    # 也提取纯文字（不在任何 CQ 码内的）
    clean = re.sub(r'\[CQ:[a-z]+(?:,[^\]]*)?\]', '', message)
    if not text:
        text = clean
    else:
        text = text + clean
    return has_image, text


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
        match = re.search(pattern, text)
        if match:
            # QQ 正则：检查群号上下文
            if name == 'qq':
                digits = match.group()
                if len(digits) >= 8 and any(ctx in text for ctx in QQ_CONTEXT_WHITELIST):
                    continue  # 群号上下文，不触发 QQ 拦截
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
        # 向后兼容：block_pure_image=True 且 mode 为默认值时升级为 block_pure_image 模式
        if qrcode_cfg.get('block_pure_image') and mode == 'image_with_keyword':
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
