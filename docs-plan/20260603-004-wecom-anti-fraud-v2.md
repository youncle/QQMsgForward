# 企微 UI 风控优化方案

## 当前已有的优化

- `_rand_sleep()` 随机延迟（已有）
- `_verify_clipboard()` 剪贴板校验（已有）
- `_ensure_focus()` 焦点保护（已有）
- 剪贴板清理（已有）

---

## 仍待优化的风控缺口

| 缺口 | 简述 | 风险 | 改动量 |
|------|------|------|--------|
| 1. `send_keys()` 固定 50ms | 每次键盘事件后永远 50ms | 高 | 2 行 |
| 2. 未利用 `_last_chat` | 同一群连续发消息也重复 Ctrl+F 搜索 | 高 | 3 行 |
| 3. 操作序列固定 | 每次都是 Ctrl+A→DEL→Ctrl+V→ENTER | 中 | 12 行 |
| 4. 无全局劳累系数 | 发多少都一样快 | 中 | 5 行 |
| 5. 批量爆发 | 0.3s 窗口后一次性发完 | 中 | 5 行 |
| 6. ALT 键绕过锁定 | 无人类这样操作 | 低 | 5 行 |
| 7. 图片临时文件路径固定 | `qqmsgforward` 目录可被定位 | 低 | 2 行 |

---

## 详细改动

### 1. `send_keys()` 固定 50ms → 随机化

当前：
`python
def send_keys(keys: str):
    if _shell:
        _shell.SendKeys(keys)
        time.sleep(0.05)  # 永远 50ms
`

改为：
`python
def send_keys(keys: str):
    """统一的 SendKeys 封装，内部随机延迟以模拟人类打字节奏"""
    if _shell:
        _shell.SendKeys(keys)
        time.sleep(random.uniform(0.03, 0.15))
`

效果：每次 30~150ms 随机，不再固定

---

### 2. 利用 `_last_chat` 避免重复搜索

当前：每次发送都执行完整 `_find_chat()`，包括 Ctrl+F 搜索

改为：在 `_send_batch()` 中检查是否上次已经搜过同一个群

`python
        if chat_name == self._last_chat:
            ok = True
            self._rand_sleep(0.3, 0.15)  # “考虑”一下
        else:
            for attempt in range(2):
                if self._find_chat(chat_name):
                    ok = True
                    break
                ...
`

效果：同一群连续发消息时省略 Ctrl+F，减少异常流量

---

### 3. `_send_text()` 操作序列随机化

当前：每次固定 `Ctrl+A → DEL → Ctrl+V → ENTER`

改为：30% 概率先模拟打几个字，再粘贴

`python
    def _send_text(self, text):
        if not HAS_SENDKEYS:
            return
        if not self._ensure_focus():
            return
        if not self._verify_clipboard(text):
            logger.error(...)
            return

        # 30% 模拟“打字”开头
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

效果：操作模式不固定，企微无法通过行为指纹识别

---

### 4. 全局劳累系数

在 `__init__()` 中新增 `self._fatigue = 0`

'改 _rand_sleep() 从 @staticmethod 为实例方法，加入劳累因子：
    `python
    def _rand_sleep(self, base=0.5, jitter=0.4):
        fatigue_factor = min(self._fatigue / 50, 1.0) * 0.3
        actual_base = base + fatigue_factor
        time.sleep(max(0.05, actual_base + random.uniform(-jitter, jitter)))
    `

每发完一批增加劳累：`self._fatigue += len(batch)`

效果：发越多动作越慢，符合人类自然节奏。注意：变为实例方法后需更新所有 14 处调用

---

### 5. 批量发送间隔

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

效果：batch 越大等待越久，符合“看完所有消息再回复”

---

### 6. ALT 键绕过前台锁定 → 先试滑鼠点击

当前 `_ensure_window()` 中用 keybd_event ALT 绕过锁定。可以先试滑鼠点击（如果可用），ALT 做 fallback：

`python
    # 最多 3 次尝试
    for attempt in range(3):
        # 新增：先试滑鼠点击标题栏使窗口激活
        if attempt == 0:
            user32.SetCursorPos(x, y)  # 标题栏中间坐标
            user32.mouse_event(0x0002 | 0x0004, 0, 0, 0, 0)  # 左键点击
            time.sleep(0.1)
        # 然后再试 SetForegroundWindow
        ...
`

效果：模拟人类先点窗口再操作

---

### 7. 图片临时文件目录随机化

当前：`tempfile.gettempdir() + "qqmsgforward"`

改为：`os.path.join(tempfile.gettempdir(), "qqmf_" + uuid.uuid4().hex[:8])`

效果：每次启动目录不同，避免被定位

---

## 优先级建议

| 优先级 | 项目 | 原因 |
|----------|------|------|
| P0 | 1. send_keys 随机化 | 最明显的机器特征，改动最小 |
| P0 | 2. _last_chat 优化 | 减少频繁搜索异常流量 |
| P0 | 3. 操作序列随机化 | 破解行为指纹识别 |
| P1 | 4. 劳累系数 | 变更量大（更新 14 处调用） |
| P1 | 5. 批量间隔 | 简单但效果有限 |
| P2 | 6. 滑鼠点击 | 变更量中等，效果不确定 |
| P2 | 7. 临时文件目录 | 防御性优化 |
