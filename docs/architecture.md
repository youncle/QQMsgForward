# QQMsgForward 架构详解

基于 LLOneBot v7.11.4 的 QQ 群消息实时转发系统。Python 胶水层 + Node.js 运行时，通过 OneBot v11 HTTP POST 协议通信。

---

## 一、项目定位

- **运行时**：Python 3.9+ 做胶水层（进程管理 + HTTP 转发 + GUI 界面），Node.js（LLBot）做 OneBot 协议实现
- **传输**：LLBot 接收 QQ 消息 → POST 到 Python Flask → Python 调用 LLBot API 转发到目标群
- **配置**：`config.json` 热重载，修改即生效（`robot_qq` 除外）
- **部署**：PyInstaller 打包为单 exe + 7-Zip SFX 自解压安装包

---

## 二、整体架构

```
start.vbs ───→ pythonw tray.py ───→ Splash 启动画面
                      │
            ┌─────────┼─────────┐
            │         │         │
         LLBot-1   LLBot-2   LLBot-N
        port 3000   3001     3000+N
        WebUI 3080  3081     3080+N
            │         │         │
            └────┬────┼─────────┘
                 ▼  HTTP POST /webhook
          Flask 转发服务 :9090
                 │
           ┌─────┼─────┐
           ▼     ▼     ▼
        目标群1 目标群2 目标群N
```

### 优雅关闭机制

```
stop.vbs ──→ 创建 .shutdown.flag
                 │
           tray.py 1秒轮询检测
                 │
           检测到 .shutdown.flag
                 │
           ├── 启动关停倒计时 5 秒
           ├── 清理 LLBot 进程（端口反查 + taskkill）
           ├── 删除 .shutdown.flag（通知 stop.vbs 优雅完成）
           └── 退出事件循环
                 │
           stop.vbs 15秒超时检测
           若 flag 未删除 → 强制 taskkill
```

---

## 三、核心流程详解

### 3.1 启动链路

```
start.vbs
 │
 ├── 自动提权（UAC）
 ├── 校验 Python 环境
 └── pythonw main.py (隐藏窗口)
      │
      ├── Splash 进度窗（无边框居中，平滑动画）
      │
      ├── 查杀残留进程
      │    └── 扫描 3000-3010 端口 → 反查 PID → taskkill
      │
      ├── 校验 config.json
      │    ├── 存在 → 加载配置
      │    └── 不存在/损坏 → 弹出向导 → 生成配置
      │
      ├── 校验 runtime/LLBot-Desktop-win-x64/
      │    └── 不存在 → 弹窗错误，退出
      │
      ├── 启动 LLBot 实例（N 个）
      │    ├── 主实例：runtime/LLBot-Desktop-win-x64/，端口 3000
      │    ├── 多实例：复制到 LLBot-Desktop-win-x64-2/3/...，端口 3001/3002/...
      │    └── 每实例轮询等待端口就绪（最多 60 秒，2 秒间隔）
      │
      ├── 探测登录状态
      │    └── GET /get_login_info → 动态写入 llbot_apis 映射
      │
      ├── 启动 Flask 转发服务（:9090，daemon 线程）
      │    └── 轮询等待端口就绪（最多 10 秒）
      │
      ├── 声明 AppUserModelID = "QQLL.OneBot.Forward"
      │
      ├── 创建 tkinter 主窗口
      │    ├── 恢复上次窗口位置（.window_state.json）
      │    ├── 多显示器越界检测
      │    └── 窗口最小尺寸 1024 × 当前高度
      │
      ├── 创建桌面快捷方式（首次运行）
      │
      ├── 初始化系统托盘（绿色=正常 / 黄色=部分异常 / 红色=离线）
      │
      └── 关闭 Splash → mainloop
      │
      │
      ├── 初始化企微 UI 引擎
      │    └── WeComUIEngine() 惰性初始化，start() 后启动 consumer 线程
      │
```

### 3.2 转发流水线

```
LLBot 接收群消息 → POST /webhook
 ├── 1. 过滤非群聊
 ├── 2. 解析消息元数据
 ├── 3. 跳过自身消息（防止循环转发）
 ├── 4. 匹配转发规则
 ├── 5. 去重
 ├── 6. 消息过滤（三层）
 ├── 7. 固定延迟 1 秒
 └── 8. 转发到目标群
      ├── 优先使用接收消息的机器人（API 轮询排序）
      ├── 目标群级限流（send_interval，默认 1 秒）
      ├── POST /send_group_msg
      ├── 失败则自动切换下一可用机器人
      ├── 3 次 HTTP 重试（500/502/503/504，0.5s backoff）
      └── 所有 API 失败 → 记录错误日志
```

### 3.3 企业微信转发通道

从 QQ 群消息到企微群的转发路径，支持 API 和 UI 双模式：

```
try_forward_wecom(data, cfg)
 │
 ├── wecom_enabled? → false → 跳过
 │
 ├── 解析 wecom_bots 列表
 │
 ├── 按 source_groups 过滤
 │    ├── 空列表 → 匹配所有消息
 │    └── 非空 → group_id in sources 才匹配
 │
 ├── 过滤检查（复用 QQ 通道 filter 规则）
 │
 ├── 解析消息段（文本 + 图片 URL + 文件转图片）
 │
 └── 按 mode 路由
      ├── ui  → _forward_ui()
      │    ├── 校验 name 非空
      │    ├── 调用 WeComUIEngine.enqueue() 入队
      │    └── consumer 线程批量发送（合并同群消息）
      │
      └── api → _forward_api()
           ├── 校验 key 非空
           ├── 发送文本（content[:2000]）
           ├── 发送图片（最多 3 张，base64+md5）
           └── 图片失败 → 降级发送 [图片]
```

### 3.4 UI 操控引擎（WeComUIEngine）

通过键盘模拟 + 剪贴板操控企业微信桌面端发送消息：

```
WeComUIEngine
 │
 ├── 生命周期
 │    ├── get_ui_engine() → 全局单例
 │    ├── start() → 启动 consumer 线程
 │    └── stop() → 停止 consumer
 │
 ├── 窗口管理
 │    ├── is_available() → FindWindowW(类名/标题)
 │    ├── _ensure_window() → 激活企微窗口（绕过前台锁定）
 │    └── _find_chat() → Ctrl+F 搜索群名 → Enter
 │
 ├── 消息发送
 │    ├── _send_text() → 剪贴板 → Ctrl+V → Enter
 │    ├── _send_image() → 保存临时 PNG → 剪贴板 CF_HDROP → Ctrl+V → Enter
 │    └── 随机延迟（防风控）：base ± jitter
 │
 └── 队列机制
      ├── enqueue() → 入队
      ├── consumer 批量拉取（同群合并）
      └── 失败 → fallback 回调
```

## 四、多实例管理

| 实例 | 运行目录 | API 端口 | WebUI 端口 |
|------|---------|---------|-----------|
| 0 | `runtime/LLBot-Desktop-win-x64/` | 3000 | 3080 |
| 1 | `runtime/LLBot-Desktop-win-x64-2/` | 3001 | 3081 |
| 2 | `runtime/LLBot-Desktop-win-x64-3/` | 3002 | 3082 |
| N | `runtime/LLBot-Desktop-win-x64-(N+1)/` | 3000+N | 3080+N |

- 多实例目录由 `tray.py` 自动复制（排除 `logs/`），启动时清空该实例的 `logs/`
- 每个实例使用 `--port` 和 `--webui-port` 参数区分
- 启动后通过 `GET /get_login_info` 探测每个端口对应的 QQ 号，写入 `llbot_apis`

---

## 五、过滤系统

```
should_filter(message, config)
     ▼
 ┌─────────────────────────┐
 └─────────┬───────────────┘
           ▼
 ┌─────────────────────────┐
 └─────────┬───────────────┘
           ▼
 ┌─────────────────────────┐
 └─────────┬───────────────┘
           ▼
         ✅ 放行
```

### 5.1 QQ 群号白名单

当消息中包含 `群` / `加群` / `群号` / `频道` / `channel` / `guild` / `进群` 这些词，且匹配到的数字 >= 8 位时，不触发 QQ 号拦截（避免误拦正常的群号分享）。

### 5.2 log_only 试运行模式

- 启用后所有过滤仅记录日志，不实际拦截消息
- 日志中标记 `[FILTER] 仅记录` 方便观察
- 适用于：刚配置规则时先观察效果，再决定是否启用

---

## 六、配置热重载

```python
def get_config():
    """每次从文件重新读取，支持热重载"""
    return load_config()
```

- 所有修改（通过配置面板或直接编辑 `config.json`）**立即生效**
- 唯一例外：`robot_qq` 修改后需重启服务（因为 LLBot 实例数在启动时确定）
- `set_config_path()` 由 `tray.py` 在启动时调用，覆盖默认路径
- 旧配置自动迁移：`robot_qq` int → 数组、`forward_rules` list → dict

### 配置写入

```python
tmp = CONFIG_PATH + '.tmp'
json.dump(cfg, tmp)
os.replace(tmp, CONFIG_PATH)  # 原子操作，防写入中断损坏
```

---

## 七、异常处理与健壮性

| 场景 | 处理方式 |
|---|---|
| 端口被占用（3000-3010） | 启动前查杀 |—any →
| 配置缺失 | 向导自动创建 |
| 企微窗口不可用（UI 模式） | 跳过该 bot 的转发，不影响其他 bot |
| 企微 Webhook 发送失败 | API 模式记录 ERROR 日志，不重试 |
| 企微窗口不可用（UI 模式） | 跳过该 bot 的转发，不影响其他 bot |
| 企微 Webhook 发送失败 | API 模式记录 ERROR 日志，不重试 |
| 配置损坏（JSON 解析失败） | 弹窗 → 重建配置 |
| LLBot 目录缺失 | 弹窗错误 → 退出 |
| 机器人未登录（无 /get_login_info 响应） | 弹窗提醒，服务继续运行 |
| API 转发失败（连接拒绝） | 切换下一可用机器人 |
| API 返回 5xx | 3 次重试（0.5s backoff） |
| 所有 API 均失败 | 记录错误日志 |
| pyzbar 缺失/DLL 加载失败 | 自动降级，跳过 QR 解码 |
| stderr 为 None（windowed 模式） | 跳过 logging.basicConfig |
| 配置文件写入权限不足 | 捕获异常，记录警告，内存配置继续使用 |
| 转发服务崩溃 | 捕获异常，记录 FATAL 日志 |
| 窗口位置在屏幕外（多显示器变动） | 越界检测 → 仅恢复尺寸不恢复位置 |

### Requests 会话配置

```python
session = requests.Session()
retry_strategy = Retry(
    total=3,
    backoff_factor=0.5,
    status_forcelist=[500, 502, 503, 504],
    allowed_methods=["POST"]
)
adapter = HTTPAdapter(max_retries=retry_strategy)
```

- 连接池复用，减少 TCP 握手开销
- 自动重试幂等 POST 请求（5xx 错误）
- 请求超时 5 秒（不包含重试时间）

---

## 八、文件职责

| 文件 | 行数 | 职责 |
|---|---|---|
| `main.py` | 10 | 程序入口，将 `src/` 加入 sys.path 后调用 `tray.main()` |
| `src/tray.py` | ~750 | 主控：系统托盘、LLBot 进程启停、Flask 守护、tkinter 主窗口、桌面快捷方式 |
| `src/forward_qq.py` | ~242 | 转发引擎：Flask WebHook 接收、去重、限流、API 路由、重试策略 |
| `src/filter.py` | ~171 | 消息过滤：QR 码关键词检测、图片规则三模式、联系方式正则 |
| `src/qr_decoder.py` | ~136 | QR 码解码：图片下载、pyzbar 解码、LRU 缓存、内容分析 |
| `src/settings.py` | ~261 | 配置面板：转发规则 CRUD、过滤规则编辑、保存/热重载 |
| `src/wizard.py` | ~234 | 配置向导：4 步引导、默认配置模板、居中布局 |
| `src/splash.py` | ~67 | 启动动画：无边框进度浮窗、平滑动画更新 |
| `src/wecom.py` | ~280 | 企业微信转发引擎：API/UI 双模式路由、消息解析、过滤、图片下载 |
| `src/wecom_ui.py` | ~411 | 企微 UI 操控引擎：SendKeys + 剪贴板自动化、窗口管理、队列批量发送 |
| `src/nt_utils.py` | ~66 | NT 工具函数：通过 WebUI ntcall API 获取群文件下载链接 |

---

## 九、消息格式兼容

支持 OneBot v11 的两种消息格式：

| 格式 | 示例 | 处理路径 |
|---|---|---|
| Array（推荐） | `[{"type":"text","data":{"text":"hello"}}]` | `_extract_text()` / `_has_image_array()` |
| CQ 码（兼容） | `[CQ:text,text=hello]` | `_parse_cq_string()` |

- `filter.py` 和 `qr_decoder.py` 中的函数均检测消息类型，自动分派到对应解析路径
- 转发到目标群时保持原始格式（`message_content` 原样传递）

---

## 十、日志系统

```python
fh = TimedRotatingFileHandler(path, when='midnight', backupCount=2, encoding='utf-8')
```

- 路径：`logs/forward.log`
- 轮转：每天 00:00 滚动，保留最近 2 份
- 编码：UTF-8
- 级别：INFO（生产）/ DEBUG（调试）
- stderr 同时输出（windowed 模式下 stderr=None 则仅文件）
