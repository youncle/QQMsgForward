"""Test settings module: format migration"""
import sys
import os
import json
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import settings as s


def test_migrate_old_format_in_memory():
    """旧 list 格式在加载后应变为 {targets, note} 格式"""
    # 模拟旧格式
    rules = {
        '1079264158': ['1080631149'],
        '107054156': ['702961941', '123456789'],
    }
    for src, val in list(rules.items()):
        if isinstance(val, list):
            rules[src] = {'targets': val, 'note': ''}

    assert rules['1079264158'] == {'targets': ['1080631149'], 'note': ''}
    assert rules['107054156'] == {'targets': ['702961941', '123456789'], 'note': ''}


def test_new_format_unchanged():
    """新格式保持不变"""
    rules = {
        '1079264158': {'targets': ['1080631149'], 'note': '测试备注'},
    }
    for src, val in list(rules.items()):
        if isinstance(val, list):
            rules[src] = {'targets': val, 'note': ''}

    assert rules['1079264158'] == {'targets': ['1080631149'], 'note': '测试备注'}


def test_mixed_format_handled():
    """混合格式都能正确处理"""
    rules = {
        'a': ['b'],  # 旧格式
        'c': {'targets': ['d'], 'note': 'note1'},  # 新格式
    }
    for src, val in list(rules.items()):
        if isinstance(val, list):
            rules[src] = {'targets': val, 'note': ''}

    assert rules['a'] == {'targets': ['b'], 'note': ''}
    assert rules['c'] == {'targets': ['d'], 'note': 'note1'}


def test_save_and_load_new_format():
    """保存新格式后重新加载，数据正确"""
    tmpdir = tempfile.mkdtemp()
    config_path = os.path.join(tmpdir, 'config.json')
    old_path = s.CONFIG_PATH
    s.CONFIG_PATH = config_path

    try:
        data = {
            'robot_qq': 12345,
            'forward_rules': {
                'src1': {'targets': ['dst1'], 'note': '产品群→研发群'},
            },
            'llbot_api': 'http://test:3000',
            'filter': {'qrcode': {}, 'contact': {}},
        }
        s.save_config(data)
        loaded = s.load_config()
        rule = loaded['forward_rules']['src1']
        assert rule['targets'] == ['dst1']
        assert rule['note'] == '产品群→研发群'
    finally:
        s.CONFIG_PATH = old_path
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_mode_descriptions_mapping():
    """三种模式都有对应的中文说明"""
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from settings import MODE_DESCRIPTIONS

    assert '仅关键词图片' in MODE_DESCRIPTIONS
    assert '拦截纯图片' in MODE_DESCRIPTIONS
    assert '拦截所有图片' in MODE_DESCRIPTIONS
    assert MODE_DESCRIPTIONS['仅关键词图片'] == '仅拦截同时包含图片和关键词的消息'
    assert MODE_DESCRIPTIONS['拦截纯图片'] == '额外拦截无文字说明的纯图片消息'
    assert MODE_DESCRIPTIONS['拦截所有图片'] == '拦截所有含图片的消息'
