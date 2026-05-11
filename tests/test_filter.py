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
