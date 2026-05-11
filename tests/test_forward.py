"""Test forward module lazy config loading"""
import sys
import os
import json
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_module_imports_without_config():
    """After import, config should NOT be loaded yet (lazy loading)"""
    import forward as fwd
    assert hasattr(fwd, 'app')
    assert hasattr(fwd, 'get_config')
    # Config should stay None until first get_config() call
    assert fwd._config is None


def test_get_config_raises_after_set_path_to_nonexistent():
    """get_config raises FileNotFoundError when path points to nonexistent file"""
    import forward as fwd

    # Reset cached config
    fwd._config = None

    # Point to a nonexistent file
    tmpdir = tempfile.mkdtemp()
    nonexistent = os.path.join(tmpdir, 'no_config.json')
    fwd.CONFIG_PATH = nonexistent

    try:
        fwd.get_config()
        assert False, 'Should have raised FileNotFoundError'
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    finally:
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)
        fwd._config = None  # Reset for other tests


def test_get_config_loads_valid_config():
    """get_config should load and cache a valid config file"""
    import forward as fwd
    fwd._config = None

    tmpdir = tempfile.mkdtemp()
    config_path = os.path.join(tmpdir, 'config.json')
    test_data = {'robot_qq': 12345, 'forward_rules': {}, 'llbot_api': 'http://test:3000'}

    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(test_data, f)

    fwd.CONFIG_PATH = config_path
    try:
        cfg = fwd.get_config()
        assert cfg['robot_qq'] == 12345
        # Second call returns cached version
        cfg2 = fwd.get_config()
        assert cfg2 is cfg
    finally:
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)
        fwd._config = None
