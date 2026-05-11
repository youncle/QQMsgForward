"""Test wizard business logic (validation, config generation)"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wizard import validate_qq_number, generate_config, DEFAULT_CONFIG


def test_validate_qq_number_valid():
    assert validate_qq_number('12345') == True
    assert validate_qq_number('2776992588') == True
    assert validate_qq_number('10001') == True


def test_validate_qq_number_invalid():
    assert validate_qq_number('') == False
    assert validate_qq_number('abc') == False
    assert validate_qq_number('12.5') == False
    assert validate_qq_number('12345 67890') == False
    assert validate_qq_number('12345a') == False


def test_validate_qq_number_boundary():
    """QQ 号至少 5 位"""
    assert validate_qq_number('1234') == False
    assert validate_qq_number('12345') == True


def test_generate_config_basic():
    """生成包含 QQ 号 + 默认值的完整配置"""
    result = generate_config(robot_qq='2776992588', forward_rules={}, filter_enabled=True)

    assert result['robot_qq'] == 2776992588
    assert result['llbot_api'] == 'http://127.0.0.1:3000'
    assert result['llbot_token'] == ''
    assert result['forward']['duplicate_window'] == 5
    assert result['forward']['send_interval'] == 1.0
    assert result['filter']['qrcode']['enabled'] == True
    assert result['filter']['contact']['enabled'] == True
    assert result['filter']['log_only'] == False


def test_generate_config_filter_disabled():
    result = generate_config(robot_qq='12345', forward_rules={}, filter_enabled=False)

    assert result['filter']['qrcode']['enabled'] == False
    assert result['filter']['contact']['enabled'] == False


def test_generate_config_with_rules():
    rules = {'1079264158': ['1080631149', '702961941']}
    result = generate_config(robot_qq='2776992588', forward_rules=rules, filter_enabled=True)

    assert result['forward_rules'] == rules
    assert '1079264158' in result['forward_rules']
    assert len(result['forward_rules']['1079264158']) == 2


def test_generate_config_preserves_default_keywords():
    """生成的配置应包含默认的过滤关键词"""
    result = generate_config(robot_qq='12345', forward_rules={}, filter_enabled=True)
    assert len(result['filter']['qrcode']['keywords']) > 0
    assert len(result['filter']['contact']['keywords']) > 0
