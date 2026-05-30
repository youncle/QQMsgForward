"""QQMsgForward 入口 — pythonw main.py"""
import sys
import os

_src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
sys.path.insert(0, _src)

import tray
tray.main()
