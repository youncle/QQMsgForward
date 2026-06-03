# 企微 UI 风控优化 — 剩余项目

> 说明：`send_keys()` 随机化已实施，本文档仅记录剩余 6 项的方案

---

## 总览

| # | 项目 | 优先级 | 文件 | 改动量 |
|---|------|----------|------|--------|
| 1 | `_last_chat` 避免重复搜索 | P0 | `wecom_ui.py` | 3 行 |
| 2 | `_send_text()` 操作序列随机化 | P0 | `wecom_ui.py` | 12 行 |
| 3 | 全局劳累系数 | P1 | `wecom_ui.py` | +5 行 + 14 处调用更新 |
| 4 | 批量发送间隔 | P1 | `wecom_ui.py` | 5 行 |
| 5 | ALT 绕过→滑鼠点击 fallback | P2 | `wecom_ui.py` | 5 行 |
| 6 | 图片临时目录随机化 | P2 | `wecom_ui.py` | 2 行 |

---

### 1. `_last_chat` 避免重复搜索

当前：`_send_batch()` 每次都执行完整的 `_find_chat()`，包括 Ctrl+F 搜索 + 粘贴群名 + ENTER。

改为：
`python
        if chat_name == self._last_chat:
            ok = True
            self._rand_sleep(0.3, 0.15)  # “考虑”一下
        else:
            for attempt in range(2):
                if self._find_chat(chat_name):
                    ok = True
                    break
                logger.warning(...)
                self._rand_sleep(0.5, 0.2)
`

效果：同一个群连续发多条消息时，只搜索第一次，后续直接发。减少频繁 Ctrl+F 引起的异常流量。

---

### 2. `_send_text()` 操作序列随机化

当前：每次固定 `Ctrl+A → DEL → Ctrl+V → ENTER`，完全一样的模式。

改为：30% 概率先模拟打几个字再粘贴
`python
    def _send_text(self, text):
        if not HAS_SENDKEYS:
            return
        if not self._ensure_focus():
            return
        if not self._verify_clipboard(text):
            logger.error(...)
            return

        if random.random() < 0.3:
            for ch in text[:random.randint(2, 4)]:
                send_keys(ch)
                time.sleep(random.uniform(0.05, 0.15))
            send_keys("^a")
            self._rand_sleep(0.15, 0.1)
            send_keys("{DELETE}")
            self._rand_sleep(0.12, 0.08)
        else:
            send_keys("^a")
            self._rand_sleep(0.15, 0.1)
            send_keys("{DELETE}")
            self._rand_sleep(0.12, 0.08)

        send_keys("^v")
        self._rand_sleep(0.3, 0.15)
        send_keys("{ENTER}")
`

效果：操作模式每次可能不同，破解行为指纹识别。

---

### 3. 全局劳累系数

当前：发 1 条和发 100 条速度完全一样。

改为：
`python
# __init__ 中新增
        self._fatigue = 0

# _rand_sleep 从 @staticmethod 改为实例方法
    def _rand_sleep(self, base=0.5, jitter=0.4):
        fatigue_factor = min(self._fatigue / 50, 1.0) * 0.3
        actual_base = base + fatigue_factor
        time.sleep(max(0.05, actual_base + random.uniform(-jitter, jitter)))

# _send_batch 末尾新增
        self._fatigue += len(batch)
`

注意：`_rand_sleep()` 目前是 `@staticmethod`，转为实例方法后需更新全部 14 处调用。

效果：发越多动作越慢（发 50 条后所有动作慢 0.3s），模拟人类笾劳。

---

### 4. 批量发送间隔

当前：
`python
        self._rand_sleep(0.8, 0.4)
`

改为：
`python
        if len(batch) >= 3:
            self._rand_sleep(2.5, 1.0)  # 1.5~3.5s
        elif len(batch) >= 2:
            self._rand_sleep(1.5, 0.5)  # 1.0~2.0s
        else:
            self._rand_sleep(0.8, 0.4)   # 0.4~1.2s
`

效果：批量越大等待越久，模拟“看完所有消息再回复”。

---

### 5. ALT 绕过 → 滑鼠点击 fallback

当前 `_ensure_window()` 直接用 keybd_event ALT 绕过 Windows 前台锁定。

改为：第一次尝试用滑鼠点击标题栏，失败再用 ALT。
`python
    def _ensure_window(self):
        ...
        for attempt in range(3):
            if attempt == 0:
                # 先试滑鼠点击标题栏中间
                import ctypes.wintypes
                rect = ctypes.wintypes.RECT()
                user32.GetWindowRect(hwnd, ctypes.byref(rect))
                cx = (rect.left + rect.right) // 2
                cy = rect.top + 5  # 标题栏顶部
                user32.SetCursorPos(cx, cy)
                user32.mouse_event(0x0002 | 0x0004, 0, 0, 0, 0)  # 左键单击
                time.sleep(0.15)
            # ALT fallback 保留
            ctypes.windll.user32.keybd_event(0x12, 0, 0, 0)
            ctypes.windll.user32.keybd_event(0x12, 0, 2, 0)
            ...
`

效果：模拟人类点击窗口行为，ALT 作为备用。

---

### 6. 图片临时目录随机化

当前：`tempfile.gettempdir() + "qqmsgforward"`，固定目录。

改为：`os.path.join(tempfile.gettempdir(), "qm_" + uuid.uuid4().hex[:6])`，每次启动随机目录。

`python
    @staticmethod
    def _get_temp_dir():
        if WeComUIEngine.TEMP_DIR is None:
            import tempfile
            salt = uuid.uuid4().hex[:6]
            WeComUIEngine.TEMP_DIR = os.path.join(tempfile.gettempdir(), f"qm_{salt}")
            os.makedirs(WeComUIEngine.TEMP_DIR, exist_ok=True)
        return WeComUIEngine.TEMP_DIR
`

注意：这也会导致旧目录残留，可配合 `_cleanup_temp_files()` 清理。

---

## 执行顺序

按优先级逐项实施，每项独立可回滚：

1. P0 → 先做 #1 _last_chat + #2 序列随机化
2. P1 → 再做 #3 劳累系数 + #4 批量间隔
3. P2 → 最后做 #5 滑鼠 + #6 目录随机化
