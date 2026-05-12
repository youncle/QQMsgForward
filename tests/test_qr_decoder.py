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
