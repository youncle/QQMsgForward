"""测试启动进度条模块"""
import pytest


def test_splash_create_and_close():
    """splash 创建后应立即显示，close 后窗口销毁"""
    import _tkinter
    from splash import SplashScreen
    s = SplashScreen()
    assert s._root.winfo_exists()
    s.close()
    # 窗口销毁后 winfo_exists 可能返回 0 或抛出 TclError（不同平台/版本行为不同）
    try:
        assert not s._root.winfo_exists()
    except _tkinter.TclError:
        pass


def test_splash_update_changes_progress():
    """update 应正确设置进度和文字"""
    from splash import SplashScreen
    s = SplashScreen()
    s.update(50, '测试文字')
    assert s._bar['value'] == 50
    assert s._label['text'] == '测试文字'
    s.close()


def test_splash_multiple_updates():
    """连续 update 应能前后推进"""
    from splash import SplashScreen
    s = SplashScreen()
    s.update(25, '步骤1')
    s.update(75, '步骤3')
    assert s._bar['value'] == 75
    assert s._label['text'] == '步骤3'
    s.close()
