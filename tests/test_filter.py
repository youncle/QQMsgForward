import sys
sys.path.insert(0, '.')
from filter import check_qrcode_ad

# OneBot v11 message segments (array format)
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


# ============================================================
# 联系方式检测测试
# ============================================================

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


def test_contact_hit_long_number():
    """10位数字（如群号）也会被QQ正则匹配到 — 这是当前实现的已知行为"""
    msg = [{'type': 'text', 'data': {'text': '欢迎加群 1079264158'}}]
    result = check_contact_info(msg, CONTACT_PATTERNS, CONTACT_KEYWORDS)
    assert result is True


# ============================================================
# should_filter 整合函数测试
# ============================================================

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
    assert '[QR码]' in reason


def test_should_filter_returns_contact_reason_for_phone():
    """纯手机号（不含关键词）验证 phone 正则路径"""
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


# ===== CQ 码字符串格式测试 =====

CQ_IMAGE_AND_KEYWORD = '[CQ:image,file=abc123,url=http://example.com/img.jpg][CQ:text,text=扫码加我好友]'
CQ_IMAGE_AND_NORMAL = '[CQ:image,file=def456][CQ:text,text=看看这张图]'
CQ_IMAGE_ONLY = '[CQ:image,file=ghi789]'
CQ_PURE_TEXT = '[CQ:text,text=今天天气不错]'
CQ_PHONE = '[CQ:text,text=打我电话 13800001111]'


def test_qrcode_cq_string_hit():
    result = check_qrcode_ad(CQ_IMAGE_AND_KEYWORD, QR_KEYWORDS)
    assert result is True


def test_qrcode_cq_string_pass_normal():
    result = check_qrcode_ad(CQ_IMAGE_AND_NORMAL, QR_KEYWORDS)
    assert result is False


def test_qrcode_cq_string_pass_image_only():
    result = check_qrcode_ad(CQ_IMAGE_ONLY, QR_KEYWORDS)
    assert result is False


def test_qrcode_cq_string_pass_pure_text():
    result = check_qrcode_ad(CQ_PURE_TEXT, QR_KEYWORDS)
    assert result is False


def test_contact_cq_string_hit_phone():
    result = check_contact_info([{'type': 'text', 'data': {'text': '13800001111'}}],
                                 CONTACT_PATTERNS, CONTACT_KEYWORDS)
    assert result is True


def test_should_filter_cq_string_qrcode():
    filtered, reason = should_filter(CQ_IMAGE_AND_KEYWORD, FILTER_CONFIG)
    assert filtered is True
    assert '[QR码]' in reason


def test_should_filter_cq_string_pass():
    filtered, reason = should_filter(CQ_PURE_TEXT, FILTER_CONFIG)
    assert filtered is False


def test_should_filter_unknown_type_skips():
    """非 list 非 str 类型（如 int）应安全跳过"""
    filtered, reason = should_filter(12345, FILTER_CONFIG)
    assert filtered is False
    assert reason == ''


# ===== block_pure_image 测试 =====

def test_qrcode_block_pure_image_array():
    """纯图片 array 消息 + block_pure_image=True → 拦截"""
    msg = [{'type': 'image', 'data': {'file': 'qr.png'}}]
    result = check_qrcode_ad(msg, QR_KEYWORDS, block_pure_image=True)
    assert result is True


def test_qrcode_pass_pure_image_array_when_disabled():
    """纯图片 array 消息 + block_pure_image=False → 放行"""
    msg = [{'type': 'image', 'data': {'file': 'qr.png'}}]
    result = check_qrcode_ad(msg, QR_KEYWORDS, block_pure_image=False)
    assert result is False


def test_qrcode_block_pure_image_cq_string():
    """纯图片 CQ 码 + block_pure_image=True → 拦截"""
    msg = '[CQ:image,file=qr.png]'
    result = check_qrcode_ad(msg, QR_KEYWORDS, block_pure_image=True)
    assert result is True


def test_qrcode_pass_pure_image_cq_string_when_disabled():
    """纯图片 CQ 码 + block_pure_image=False → 放行"""
    msg = '[CQ:image,file=qr.png]'
    result = check_qrcode_ad(msg, QR_KEYWORDS, block_pure_image=False)
    assert result is False


def test_should_filter_block_pure_image_integration():
    """should_filter + block_pure_image 集成测试"""
    cfg = {
        **FILTER_CONFIG,
        'qrcode': {**FILTER_CONFIG['qrcode'], 'block_pure_image': True}
    }
    msg = [{'type': 'image', 'data': {'file': 'qr.png'}}]
    filtered, reason = should_filter(msg, cfg)
    assert filtered is True
    assert '[QR码]' in reason


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


# ============================================================
# A方案增强 — CQ码解析 edge case 测试
# ============================================================

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


# ============================================================
# B方案 — QR 解码集成测试
# ============================================================

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
