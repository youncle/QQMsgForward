# 企微 uiautomation 通道实施计划 — 第二阶段

> 本文档记录了 QQMsgForward 项目企微 uiautomation 发送引擎的实施方案。
> 第二阶段：实现 uiautomation 引擎，完成 UI 模式消息发送。

---

## 一、阶段目标

1. **新建 `src/wecom_ui.py`** — uiautomation 引擎（窗口管理 + 消息队列 + 发送执行）
2. **修改 `src/wecom.py`** — 替换 `_forward_ui` 桩为实际调用
3. **修改 `src/tray.py`** — 启动时初始化 UI 引擎
4. **修改 `requirements.txt`** — 添加 `uiautomation` 依赖
5. **零 API 模式影响** — 不勾 UI 开关则行为与第一阶段完全一致

---

## 二、涉及文件

| 文件 | 动作 | 行数 |
|------|------|------|
| `src/wecom_ui.py` | **新建** | ~220 行 |
| `src/wecom.py` | 修改 | ~+10 行（替换桩实现 + 生命周期管理） |
| `src/tray.py` | 修改 | ~+8 行（导入 + init 调用） |
| `requirements.txt` | 修改 | +1 行 |
| `docs/CONFIG_REFERENCE.md` | 修改 | +5 行（wecom_mode 文档） |

---

## 三、架构设计

### 3.1 整体流程

```
forward_qq.py webhook
       │
       ▼
wecom.try_forward(data, cfg)
       │
       ├── mode = "api" → _forward_api()  [不变]
       │
       └── mode = "ui"  → _forward_ui()
                              │
                              ▼
                       wecom_ui.WeComUIEngine
                              │
                       msg_queue.put({msg})
                              │
                              ▼
                    消费者线程 (daemon)
                         │
                     ┌─────┴──────┐
                     │ 批量分组排序 │  ← 同一企微群的合并连续发
                     └─────┬──────┘
                           │
                     ┌─────┴──────┐
                     │ 发送执行     │
                     │             │
                     │ ① 定位企微窗口 │
                     │ ② 搜索目标群   │
                     │ ③ 输入文本/粘贴图片 │
                     │ ④ Enter 发送  │
                     │ ⑤ 记录 _last_chat │
                     └─────────────┘
                           │
                     失败 → fallback_api()
```

### 3.2 消息队列结构

```python
# 入队消息格式
{
    "chat_name": "朝暮说-测试群",    # 企微群名
    "text": "这是一条消息",          # 文本内容，可能为空
    "images": [bytes, ...],        # 图片数据列表，最多3张
    "fallback": callable,          # 降级回调 → _forward_api()
}
```

### 3.3 批量策略

```
消费者每次取 1 条消息后，尝试最多 0.3 秒收集更多相同 chat_name 的消息
→ 同一群的 N 条消息一次性发完
→ 避免频繁切换群聊
```

---

## 四、代码详解

### 4.1 新建 `src/wecom_ui.py` — 引擎核心

#### 类结构

```
WeComUIEngine
├── __init__()
│   ├── self._queue = Queue()
│   ├── self._thread = None
│   ├── self._running = False
│   ├── self._window = None        # 缓存企微窗口
│   ├── self._last_chat = ""        # 缓存上次群名
│   ├── self._search_box = None     # 缓存搜索框控件
│   └── self._input_box = None      # 缓存输入框控件
│
├── start()                → 启动消费者线程
├── stop()                 → 停止线程
├── enqueue(msg, fallback) → 外部入队接口
│
├── _consumer()            → 消费者：取消息 → 批量 → 发送
├── _send_batch(batch)     → 批量发送同群消息
│
├── _ensure_window()       → FindWindow → ShowWindow → SetForeground
├── _find_chat(name)       → 搜索框输入群名 → 点击结果
├── _send_text(text)       → 定位输入框 → SendKeys → Enter
├── _send_image(data)      → 剪贴板写入 → Ctrl+V → Enter
│
├── is_available()         → 检测企微窗口是否存在
└── status()               → 返回引擎运行状态
```

#### 关键技术点

**① 窗口定位**

```python
def _ensure_window(self):
    """查找并激活企微窗口，返回是否成功"""
    # 1. 尝试按类名找
    try:
        self._window = auto.WindowControl(ClassName="WeChatWorkMainFrameForPC")
        if self._window.Exists(maxSearchSeconds=1):
            self._window.SetActive()
            time.sleep(0.3)
            return True
    except Exception:
        pass
    
    # 2. fallback: 按进程名找（win32gui）
    import win32gui
    hwnd = win32gui.FindWindow("WeChatWorkMainFrameForPC", None)
    if not hwnd:
        hwnd = win32gui.FindWindow(None, "企业微信")
    if hwnd:
        win32gui.ShowWindow(hwnd, 5)  # SW_SHOW
        win32gui.SetForegroundWindow(hwnd)
        time.sleep(0.5)
        self._window = auto.WindowControl(hwnd)  # 从句柄创建
        return True
    
    return False
```

**② 搜索群聊**

```python
def _find_chat(self, chat_name: str):
    """搜索群名并进入聊天"""
    # 跳过上次已进入的群
    if chat_name == self._last_chat:
        return True
    
    # 1. UIA 方式：找搜索框 EditControl
    search_box = self._window.EditControl(foundIndex=1)
    if search_box.Exists():
        search_box.Click()
        search_box.SendKeys("{Ctrl}A}{Delete}")
        time.sleep(0.2)
        search_box.SendKeys(chat_name)
        time.sleep(0.8)
        
        # 2. 点击搜索结果
        result = self._window.ListItemControl(Name=chat_name)
        if result.Exists():
            result.Click()
            time.sleep(0.5)
            return True
    
    # 3. fallback: 快捷键搜索
    self._window.SendKeys("{Ctrl}L")  # 或 Ctrl+Alt+F
    time.sleep(0.3)
    self._window.SendKeys(chat_name)
    time.sleep(0.8)
    self._window.SendKeys("{Enter}")
    time.sleep(0.5)
    
    self._last_chat = chat_name
    return True
```

**③ 发送文本**

```python
def _send_text(self, text: str):
    """定位输入框 → 输入文本 → Enter"""
    input_box = self._window.EditControl(foundIndex=2)
    if not input_box.Exists():
        input_box = self._window.RichEditControl()
    if not input_box.Exists():
        # fallback: 直接键盘输入
        self._window.SendKeys(text[:2000])
        self._window.SendKeys("{Enter}")
        return
    
    input_box.Click()
    input_box.SendKeys(text[:2000])
    time.sleep(0.3)
    input_box.SendKeys("{Enter}")
    time.sleep(0.5)
```

**④ 发送图片**

```python
def _send_image(self, img_data: bytes):
    """图片 → 剪贴板 → Ctrl+V → Enter"""
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    tmp.write(img_data)
    tmp.close()
    
    auto.SetClipboardFile(tmp.name)
    time.sleep(0.2)
    
    self._window.SendKeys("{Ctrl}V")
    time.sleep(0.5)
    self._window.SendKeys("{Enter}")
    time.sleep(0.5)
    
    os.unlink(tmp.name)
```

**⑤ 消费者批量循环**

```python
def _consumer(self):
    while self._running:
        try:
            item = self._queue.get(timeout=0.5)
        except queue.Empty:
            continue
        
        # 收集同群消息（0.3 秒窗口）
        batch = [item]
        try:
            while True:
                next_item = self._queue.get(timeout=0.3)
                if next_item[0]["chat_name"] == item[0]["chat_name"]:
                    batch.append(next_item)
                else:
                    # 不同群的放回队列
                    self._queue.put(next_item)
                    break
        except queue.Empty:
            pass
        
        self._send_batch(batch)
```

#### 异常处理策略

```
_send_batch()
  ├── _ensure_window() 失败 → 全部 fallback API
  ├── _find_chat() 失败 → 重试 1 次 → 失败则 fallback
  ├── _send_text() 异常 → 该条 fallback，继续发其他
  └── _send_image() 异常 → 该张跳过，继续发
```

---

### 4.2 修改 `src/wecom.py` — 替换桩

**① 文件顶部新增导入 + 单例**

```python
from wecom_ui import WeComUIEngine

# 全局单例（懒初始化）
_ui_engine: WeComUIEngine = None

def get_ui_engine() -> WeComUIEngine:
    global _ui_engine
    if _ui_engine is None:
        _ui_engine = WeComUIEngine()
        _ui_engine.start()
        logger.info("[WECOM] UI引擎已初始化")
    return _ui_engine
```

**② 替换 `_forward_ui` 实现**

```python
def _forward_ui(bot: dict, text: str, image_urls: list, group_id: str) -> None:
    """UI 模式发送 — 入队后立即返回"""
    chat_name = bot.get("name", "")
    if not chat_name:
        logger.warning(f"[WECOM_UI] bot 缺少 name 字段，跳过")
        return

    engine = get_ui_engine()
    if not engine.is_available():
        logger.warning(f"[WECOM_UI] 企微窗口不可用，降级API: {chat_name}")
        _forward_api(bot, text, image_urls, group_id)
        return

    nm = bot.get("name", "") or extract_key(bot.get("key", ""))[:8]
    logger.info(f"[WECOM_UI] 入队: 群{group_id} → {nm} ({chat_name})")

    engine.enqueue({
        "chat_name": chat_name,
        "text": text,
        "images": [_download_image(u) for u in image_urls[:3] if _download_image(u)],
    }, lambda: _forward_api(bot, text, image_urls, group_id))
```

---

### 4.3 修改 `src/tray.py` — 引擎生命周期

在 `main()` 中，Flask 端口确认后、UI 创建前（约第 837 行）：

```python
# 初始化企微 UI 引擎（仅在 UI 模式下使用）
from wecom import get_ui_engine
get_ui_engine()
```

> 注意：引擎线程是 `daemon=True`，进程退出自动终止，无需显式 stop。

---

### 4.4 修改 `requirements.txt`

```
uiautomation>=2.0.17
```

---

## 五、实施顺序

```
Step 1 → 展示计划文档（当前）
       ↓ 你确认
Step 2 → 新建 src/wecom_ui.py（贴完整代码 → 你确认 → 写入）
       ↓ 你确认
Step 3 → 修改 wecom.py（贴改动段 → 你确认 → 应用）
       ↓ 你确认
Step 4 → 修改 tray.py（贴改动段 → 你确认 → 应用）
       ↓ 你确认
Step 5 → 修改 requirements.txt（你确认 → 应用）
Step 6 → 安装依赖 & 验证
```

---

## 六、已知风险 & 应对

| 风险 | 概率 | 应对 |
|------|------|------|
| 企微 Duilib 控件不暴露 EditControl | 🟡 中 | 有键盘 fallback：`SendKeys` 直接输入 |
| 搜索框快捷键版本不同 | 🟡 中 | 配置化快捷键，或用 UIA 搜索框优先 |
| 图片剪贴板过大 | 🟢 低 | 企微 API 已有 2MB 限制，UI 通道无此限制 |
| 窗口被最小化/隐藏 | 🟡 中 | `ShowWindow` + `SetForegroundWindow` 强制激活 |
| 多屏 DPI 缩放 | 🟢 低 | uiautomation 自动处理 DPI 感知 |
| 企微版本升级 UI 变化 | 🟡 中 | 控件查找失败 → 自动降级 API + 日志告警 |

---

## 七、验证清单

| # | 检查项 | 验证方法 |
|---|--------|----------|
| 1 | UI 模式开 → 消息走 UI 发送 | 勾 UI 开关 → QQ 发消息 → 企微桌面端收到 |
| 2 | 企微窗口关闭 → 自动降级 API | 关掉企微 → 发消息 → 企微 API 群收到 |
| 3 | 多群连续发送不串群 | A群发3条 → B群发2条 → 正确到达对应群 |
| 4 | 图片发送正常 | 发包含图片的消息 → 企微收到图片 |
| 5 | API 模式不受影响 | 取消 UI 开关 → 消息仍走 API 正常发送 |
| 6 | 引擎不阻塞 webhook | 批量发送多条消息 → webhook 响应时间正常 |
