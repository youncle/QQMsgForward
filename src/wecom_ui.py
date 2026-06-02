"""企微键盘发送引擎 — 通过键盘操作 + 剪贴板操控企业微信桌面端发送消息"""
import queue
import threading
import time
import logging
import io
import random
from typing import Callable

import uiautomation as auto

logger = logging.getLogger(__name__)

# 键盘操作 (win32com → WScript.Shell SendKeys)
try:
    import win32com.client
    _shell = win32com.client.Dispatch("WScript.Shell")
    HAS_SENDKEYS = True
except ImportError:
    _shell = None
    HAS_SENDKEYS = False
    logger.warning("[WECOM_UI] win32com 不可用，键盘功能受限")

# 剪贴板
try:
    import win32clipboard
    import win32con
except ImportError:
    win32clipboard = None
    win32con = None

# 窗口管理 (纯 ctypes)
import ctypes
import ctypes.wintypes

user32 = ctypes.windll.user32
SW_RESTORE = 9


def send_keys(keys: str):
    """统一的 SendKeys 封装"""
    if _shell:
        _shell.SendKeys(keys)
        time.sleep(0.05)


class WeComUIEngine:
    WECHAT_WORK_CLASS = "WeChatWorkMainFrameForPC"
    WECHAT_WORK_TITLE = "\u4f01\u4e1a\u5fae\u4fe1"

    def __init__(self):
        self._queue = queue.Queue()
        self._thread = None
        self._running = False
        self._hwnd = None
        self._last_chat = ""
        self._sent_count = 0
        self._fallback_count = 0

    # --- humanization helpers ---
    @staticmethod
    def _rand_sleep(base=0.5, jitter=0.4):
        """base ± jitter 随机睡眠"""
        time.sleep(max(0.05, base + random.uniform(-jitter, jitter)))

    def _type_text(self, text: str):
        """逐字输入（用于短文本，绕过剪贴板检测）"""
        for char in text:
            auto.SendKeys(char)
            time.sleep(random.uniform(0.06, 0.28))

    # === lifecycle ===
    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._running = True
        self._thread = threading.Thread(target=self._consumer, daemon=True, name="wecom-ui")
        self._thread.start()
        logger.info("[WECOM_UI] consumer started")

    def stop(self):
        self._running = False
        try:
            self._queue.put_nowait(None)
        except queue.Full:
            pass

    # === public API ===
    def enqueue(self, msg: dict, fallback_cb=None):
        self._queue.put((msg, fallback_cb))

    def is_available(self):
        if self._hwnd and user32.IsWindow(self._hwnd):
            return True
        hwnd = user32.FindWindowW(self.WECHAT_WORK_CLASS, None)
        if not hwnd:
            hwnd = user32.FindWindowW(None, self.WECHAT_WORK_TITLE)
        if hwnd:
            self._hwnd = hwnd
            return True
        return False

    def status(self):
        return {
            "running": self._running,
            "window_found": self.is_available(),
            "queue_size": self._queue.qsize(),
            "last_chat": self._last_chat,
            "sent_count": self._sent_count,
            "fallback_count": self._fallback_count,
        }

    # === consumer ===
    def _consumer(self):
        logger.info("[WECOM_UI] consumer loop started")
        while self._running:
            try:
                item = self._queue.get(timeout=1.0)
            except queue.Empty:
                continue
            if item is None:
                break

            batch = [item]
            chat_name = item[0]["chat_name"]
            try:
                while True:
                    nxt = self._queue.get(timeout=0.3)
                    if nxt is None:
                        break
                    if nxt[0]["chat_name"] == chat_name:
                        batch.append(nxt)
                    else:
                        self._queue.put(nxt)
                        break
            except queue.Empty:
                pass

            self._send_batch(batch)
        logger.info("[WECOM_UI] consumer loop exited")

    def _send_batch(self, batch):
        chat_name = batch[0][0]["chat_name"]

        if not self._ensure_window():
            logger.warning(f"[WECOM_UI] window unavailable, fallback all: {chat_name}")
            for _, fb in batch:
                self._try_fallback(fb)
            return

        ok = False
        for attempt in range(2):
            if self._find_chat(chat_name):
                ok = True
                break
            logger.warning(f"[WECOM_UI] search failed (attempt {attempt+1}): {chat_name}")
            self._rand_sleep(0.5, 0.2)
        if not ok:
            logger.error(f"[WECOM_UI] search exhausted, fallback all: {chat_name}")
            for _, fb in batch:
                self._try_fallback(fb)
            return

        for msg, fallback_cb in batch:
            text = msg.get("text", "")
            images = msg.get("images", [])

            if text:
                try:
                    self._send_text(text)
                    self._sent_count += 1
                except Exception as e:
                    logger.error(f"[WECOM_UI] text send failed: {e}")
                    self._try_fallback(fallback_cb)
                    continue

            for i, img_data in enumerate(images):
                try:
                    self._send_image(img_data)
                    self._sent_count += 1
                except Exception as e:
                    logger.error(f"[WECOM_UI] image send failed ({i+1}): {e}")

            self._rand_sleep(0.8, 0.4)  # 消息间隔随机化

        self._last_chat = chat_name

    def _try_fallback(self, fb):
        if fb:
            try:
                fb()
                self._fallback_count += 1
            except Exception as e:
                logger.error(f"[WECOM_UI] fallback error: {e}")

    # === window activation ===
    def _ensure_window(self):
        hwnd = user32.FindWindowW(self.WECHAT_WORK_CLASS, None)
        if not hwnd:
            hwnd = user32.FindWindowW(None, self.WECHAT_WORK_TITLE)
        if hwnd:
            if user32.IsIconic(hwnd):
                user32.ShowWindow(hwnd, SW_RESTORE)
            user32.SetForegroundWindow(hwnd)
            self._rand_sleep(0.3, 0.15)
            self._hwnd = hwnd
            return True
        return False

    # === search chat ===
    def _find_chat(self, name):
        if not name or not HAS_SENDKEYS:
            return False
        try:
            self._ensure_window()
            send_keys("^f")       # Ctrl+F
            self._rand_sleep(0.3, 0.15)
            send_keys("^a")       # Ctrl+A
            self._rand_sleep(0.08, 0.05)
            send_keys("{DELETE}") # clear
            self._rand_sleep(0.12, 0.08)
            self._set_clipboard_text(name)
            send_keys("^v")
            self._rand_sleep(0.5, 0.2)
            send_keys("{ENTER}")
            self._rand_sleep(0.5, 0.2)
            self._rand_sleep(0.3, 0.15)
            return True
        except Exception as e:
            logger.error(f"[WECOM_UI] search failed: {e}")
            return False
    # === send text ===
    def _send_text(self, text):
        if not HAS_SENDKEYS:
            return
        if len(text) <= 20:
            self._type_text(text)
        else:
            self._set_clipboard_text(text)
            send_keys("^v")
        self._rand_sleep(0.3, 0.15)
        send_keys("{ENTER}")
    # === send image ===
    def _send_image(self, data):
        if not HAS_SENDKEYS:
            return
        self._set_clipboard_image(data)
        send_keys("^v")       # Ctrl+V
        self._rand_sleep(0.5, 0.25)
        send_keys("{ENTER}")  # send
        self._clear_clipboard()

    # === clipboard ===
    @staticmethod
    def _set_clipboard_text(text: str):
        """Copy text to clipboard (supports Unicode)"""
        if win32clipboard:
            try:
                win32clipboard.OpenClipboard()
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, text)
                win32clipboard.CloseClipboard()
                return
            except Exception:
                win32clipboard.CloseClipboard()
        # fallback: ctypes
        try:
            CF_UNICODETEXT = 13
            GMEM_MOVEABLE = 0x0002
            data = (text + "\0").encode("utf-16-le")
            hMem = ctypes.windll.kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
            if hMem:
                pMem = ctypes.windll.kernel32.GlobalLock(hMem)
                ctypes.memmove(pMem, data, len(data))
                ctypes.windll.kernel32.GlobalUnlock(hMem)
                user32.OpenClipboard(None)
                ctypes.windll.user32.EmptyClipboard()
                ctypes.windll.user32.SetClipboardData(CF_UNICODETEXT, hMem)
                ctypes.windll.user32.CloseClipboard()
        except Exception as e:
            logger.error(f"[WECOM_UI] clipboard text failed: {e}")

    @staticmethod
    def _set_clipboard_image(data):
        from PIL import Image
        img = Image.open(io.BytesIO(data))

        if win32clipboard:
            buf = io.BytesIO()
            img.convert("RGB").save(buf, format="BMP")
            bmp_data = buf.getvalue()[14:]
            buf.close()
            try:
                win32clipboard.OpenClipboard()
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardData(win32con.CF_DIB, bmp_data)
                win32clipboard.CloseClipboard()
                return
            except Exception:
                win32clipboard.CloseClipboard()

        # fallback: ctypes
        try:
            CF_DIB = 8
            GMEM_MOVEABLE = 0x0002
            buf = io.BytesIO()
            img.convert("RGB").save(buf, format="BMP")
            bmp_data = buf.getvalue()[14:]
            buf.close()
            hMem = ctypes.windll.kernel32.GlobalAlloc(GMEM_MOVEABLE, len(bmp_data))
            if hMem:
                pMem = ctypes.windll.kernel32.GlobalLock(hMem)
                ctypes.memmove(pMem, bmp_data, len(bmp_data))
                ctypes.windll.kernel32.GlobalUnlock(hMem)
                user32.OpenClipboard(None)
                ctypes.windll.user32.EmptyClipboard()
                ctypes.windll.user32.SetClipboardData(CF_DIB, hMem)
                ctypes.windll.user32.CloseClipboard()
        except Exception as e:
            logger.error(f"[WECOM_UI] clipboard fallback failed: {e}")

    @staticmethod
    def _clear_clipboard():
        try:
            user32.OpenClipboard(None)
            user32.EmptyClipboard()
            user32.CloseClipboard()
        except Exception:
            pass
