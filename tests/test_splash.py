"""测试启动进度条模块"""
import pytest
import tkinter


@pytest.fixture
def splash():
    """创建 SplashScreen 并确保测试后清理；无显示环境时跳过"""
    from splash import SplashScreen
    try:
        s = SplashScreen()
    except tkinter.TclError:
        pytest.skip('需要显示环境')
    yield s
    try:
        s.close()
    except tkinter.TclError:
        pass


def test_splash_create_and_close(splash):
    """splash 创建后应立即显示，close 后窗口销毁"""
    assert splash._root.winfo_exists()
    splash.close()
    try:
        assert not splash._root.winfo_exists()
    except tkinter.TclError:
        pass


def test_splash_update_changes_progress(splash):
    """update 应正确设置进度和文字"""
    splash.update(50, '测试文字')
    assert splash._bar['value'] == 50
    assert splash._label['text'] == '测试文字'


def test_splash_multiple_updates(splash):
    """连续 update 应能前后推进"""
    splash.update(25, '步骤1')
    splash.update(75, '步骤3')
    assert splash._bar['value'] == 75
    assert splash._label['text'] == '步骤3'
