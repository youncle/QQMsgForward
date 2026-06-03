# 企微 UI 代码层防御方案

## 背景

当前 `wecom_ui.py` 对剪贴板被清理、窗口焦点被抢走没有任何防御。运行时若其他软件清理剪贴板或弹窗抢焦点，会导致粘贴内容为空、快捷键发到错误窗口。

## 改动清单

仅修改 `src/wecom_ui.py`，新增 2 个辅助方法，在 3 个现有方法中集成。

---

### 新增 1: `_verify_clipboard()`

设置剪贴板后读回校验，失败重试。在 `WeComUIEngine` 类内新增：

`python
    def _verify_clipboard(self, expected: str, max_retries: int = 2) -> bool:
        for attempt in range(max_retries):
            self._set_clipboard_text(expected)
            self._rand_sleep(0.05, 0.03)
            try:
                win32clipboard.OpenClipboard()
                actual = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
                win32clipboard.CloseClipboard()
                if actual == expected:
                    return True
            except Exception:
                try:
                    win32clipboard.CloseClipboard()
                except:
                    pass
            self._rand_sleep(0.1, 0.05)
        return False
`

---

### 新增 2: `_ensure_focus()`

发送前确认企微窗口在前台，丢失则重新激活。在 `WeComUIEngine` 类内新增：

`python
    def _ensure_focus(self) -> bool:
        if user32.GetForegroundWindow() != self._hwnd:
            logger.warning("[WECOM_UI] 窗口焦点丢失，重新激活")
            return self._ensure_window()
        return True
`

---

### 集成 1: `_send_text()`

在粘贴前加入焦点检查和剪贴板校验：

当前：
`python
    def _send_text(self, text):
        if not HAS_SENDKEYS:
            return
        self._set_clipboard_text(text)
`

改为：
`python
    def _send_text(self, text):
        if not HAS_SENDKEYS:
            return
        if not self._ensure_focus():
            return
        if not self._verify_clipboard(text):
            logger.error("[WECOM_UI] 剪贴板校验失败，跳过发送")
            return
`

---

### 集成 2: `_send_image()`

在粘贴前加入焦点检查（图片剪贴板无法用 GetClipboardData 校验内容）：

当前：
`python
    def _send_image(self, data):
        ...
        self._clear_clipboard()
        WeComUIEngine._set_clipboard_files([path])
        send_keys("^v")
`

改为：
`python
    def _send_image(self, data):
        ...
        if not self._ensure_focus():
            return
        self._clear_clipboard()
        WeComUIEngine._set_clipboard_files([path])
        self._rand_sleep(0.15, 0.1)
        send_keys("^v")
`

---

### 集成 3: `_find_chat()`

粘贴群名前加入剪贴板校验：

当前：
`python
        self._set_clipboard_text(name)
        send_keys("^v")
`

改为：
`python
        if not self._verify_clipboard(name):
            logger.error("[WECOM_UI] 搜索名剪贴板写入失败")
            return False
        send_keys("^v")
`

---

## 合计改动量

| 地方 | 新增行数 |
|------|--------|
| `_verify_clipboard()` | ~16 行 |
| `_ensure_focus()` | ~5 行 |
| `_send_text()` | +4 行 |
| `_send_image()` | +3 行 |
| `_find_chat()` | +2 行 |
| 合计 | ~30 行 |

---

## 验证方法

1. 正常发送不受影响
2. 发送过程中复制其他文本，观察是否自动重写剪贴板并成功发送
3. 发送过程中点击其他窗口，观察是否自动重新激活企微
4. 检查 `logs/forward.log` 中的 [WECOM_UI] 日志是否正确记录重试和恢复

---

## 回滚

新增方法可直接删除，集成处删除对应行即可，不影响其他逻辑。