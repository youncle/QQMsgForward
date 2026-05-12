"""日志设置模块测试"""
import os
import tempfile
import logging
import sys
sys.path.insert(0, '.')


def _cleanup_log_handlers(tmp_path: str) -> None:
    """关闭并移除所有关联到 tmp_path 的 FileHandler，以便在 Windows 上删除文件"""
    root_logger = logging.getLogger()
    for h in list(root_logger.handlers):
        if isinstance(h, logging.FileHandler) and h.baseFilename == os.path.abspath(tmp_path):
            h.close()
            root_logger.removeHandler(h)


def test_set_log_path_writes_to_file():
    """测试 set_log_path 配置 FileHandler 后日志写入文件"""
    import forward as forward_mod

    with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False,
                                      encoding='utf-8') as tmp:
        tmp_path = tmp.name

    try:
        forward_mod.set_log_path(tmp_path)
        forward_mod.logger.info('测试消息: 中文和emoji ✅')

        with open(tmp_path, 'r', encoding='utf-8') as f:
            content = f.read()
        assert '测试消息' in content
        assert '中文和emoji' in content
    finally:
        _cleanup_log_handlers(tmp_path)
        os.unlink(tmp_path)


def test_set_log_path_does_not_crash_without_stderr(monkeypatch):
    """测试 stderr 为 None 时 set_log_path 仍可正常工作"""
    monkeypatch.setattr('sys.stderr', None)

    import forward as forward_mod

    with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False,
                                      encoding='utf-8') as tmp:
        tmp_path = tmp.name

    try:
        forward_mod.set_log_path(tmp_path)
        forward_mod.logger.info('test message')
        forward_mod.logger.error('error message')

        with open(tmp_path, 'r', encoding='utf-8') as f:
            content = f.read()
        assert 'test message' in content
        assert 'error message' in content
    finally:
        _cleanup_log_handlers(tmp_path)
        os.unlink(tmp_path)
