# QQ 群消息转发

基于 [LLOneBot](https://github.com/LLOneBot/LuckyLilliaBot) 的 QQ 群消息实时转发系统，采用 **Python 胶水层 + Node.js 运行时** 架构，两端通过 **OneBot v11 HTTP POST** 协议交互，支持多机器人、广告过滤、系统托盘管理。

## 一、 功能

- **群消息转发** — 监听源群消息，实时转发到目标群
- **多机器人** — 同时运行多个 QQ 机器人，智能分配端口，登录顺序无关的 QQ→API 自动映射
- **广告过滤** — QR 码图像解码 + 联系方式正则匹配 + 三层图片拦截规则
  - 二维码解码：pyzbar 真解码，支持 URL 域名风险识别 + 联系方式检出
  - 图片拦截三模式：图片+关键词 / 纯图片 / 全部图片
  - 联系方式检测：手机号、QQ 号、微信号、邮箱
  - 试运行模式：先观察日志再拦截
- **系统托盘** — 托盘图标显示运行状态，右键菜单查看状态、修改配置

## 二、 快速开始

### 安装包用户

1. 双击 `QQForward_Setup.exe`，选择目录解压
2. 进入 `QQForward/` 目录，双击 `start.vbs` 启动
3. 首次启动自动弹出配置向导，填写机器人 QQ 号和转发规则
4. 看到 QQ 登录窗口后扫码登录
5. 后续通过系统托盘右键菜单查看状态、修改配置

### 开发运行

```bash
pip install -r requirements.txt
python tray.py
```

或双击 `start.vbs`。

## 三、 架构总览

```
┌──────────────────────────────────────────────────┐
│              用户视角 (End User)                   │
│  start.vbs ──▶ pythonw tray.py                    │
│  tray.py ──▶ 系统托盘 + Splash 启动画面            │
│              ├── 启动 N 个 LLBot 实例 (多QQ)        │
│              ├── 探测真实 QQ→端口映射               │
│              ├── 启动 Flask 转发服务 (port 9090)    │
│              └── tkinter 设置面板 (3 个 Tab)        │
└──────────────────────┬───────────────────────────┘
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
    LLBot-1        LLBot-2       LLBot-N
    (QQ A)         (QQ B)        (QQ C)
    port 3000      port 3001     port 3002+N
    WebUI 3080     WebUI 3081    WebUI 3080+N
       │               │            │
       └───────────────┼────────────┘
                       │ HTTP POST /webhook
                       ▼
              Flask Forward Service
              port 9090 (forward.py)
                       │
         ┌─────────────┼─────────────┐
         ▼             ▼             ▼
    目标群1         目标群2        目标群N
```

## 四、 启动链路

```
start.vbs
  └─▶ 管理员权限提权
       └─▶ pythonw tray.py
            ├─▶ 加载 Splash 启动进度窗
            ├─▶ 查杀占用端口的残留进程
            ├─▶ 校验 config.json，缺失则唤起配置向导
            ├─▶ 循环启动多 LLBot 实例
            │   ├─▶ 主实例：直接使用原目录
            │   ├─▶ 多实例：复制目录生成独立运行目录
            │   ├─▶ 动态注入端口、WebHook、Token 配置
            │   ├─▶ 无窗口拉起 llbot.exe
            │   └─▶ 主动轮询 /get_login_info 检测 QQ 登录状态，
            │        确认登录后再启动下一个（每端口最多等 60s）
            ├─▶ 轮询检测端口，等待剩余 LLBot 服务就绪
            ├─▶ 后置全量探测各端口 /get_login_info，
            │   写入真实 QQ→端口映射到 llbot_apis
            ├─▶ 后台守护线程启动 Flask 转发服务(9090)
            └─▶ 初始化系统托盘 + 主配置窗口
```

## 五、 消息转发流水线

```
QQ 群消息
  └─▶ LLBot 触发 OneBot 回调 → POST 127.0.0.1:9090/webhook
       └─▶ forward.py 接收
            ├─▶ 过滤：仅处理群聊、屏蔽机器人自身消息（防循环）
            ├─▶ 匹配预设转发规则
            ├─▶ 短时去重缓存（窗口 5s），拦截重复
            ├─▶ 多层内容过滤（filter.py + qr_decoder.py）
            │   ├─▶ QR 码 pyzbar 解码 + URL/联系方式/关键词风险分析
            │   ├─▶ 图片拦截规则校验（三模式）
            │   └─▶ 手机号/QQ/微信/邮箱正则检测
            ├─▶ 群限流（同群发送间隔 ≥ 1s）
            └─▶ 智能匹配机器人 API 发送到目标群
                ├─▶ 优先用接收消息的同机器人
                └─▶ 不在目标群则轮询其他机器人
```


## 六、 多机器人

配置 `config.json` 中的 `robot_qq` 数组，系统自动启动对应数量的 LLBot 实例：

```json
{
  "robot_qq": [2776992588, 85039678]
}
```

### 端口分配

| 实例 | 目录 | HTTP API | WebUI |
|------|------|----------|-------|
| 实例1 | `LLBot-CLI-Win-x64` | 3000 | 3080 |
| 实例2 | `LLBot-CLI-Win-x64-2` | 3001 | 3081 |
| 实例3 | `LLBot-CLI-Win-x64-3` | 3002 | 3082 |

实例 2+ 首次启动自动复制主目录并注入端口配置。

### QQ→端口映射

系统不再假设 QQ 登录顺序与 `robot_qq` 数组一致。启动后通过 `GET /get_login_info` 探测各端口实际登录的 QQ 号，自动写入 `llbot_apis`：

```json
"llbot_apis": {
  "2776992588": "http://127.0.0.1:3001",
  "85039678":  "http://127.0.0.1:3000"
}
```

状态页也基于此映射展示真实对应关系。

### 实例间等待

每个实例启动后主动轮询该端口的登录状态，用户扫码快则快速继续，慢则最多等待 60s 后自动跳过。不再硬等 10 秒。

### 消息发送策略

**哪个机器人接收的消息，优先用哪个机器人发送。** 接收方不在目标群时自动轮询其他可用机器人 API。

## 七、 配置

编辑 `config.json`：

```json
{
  "robot_qq": [2776992588, 85039678],
  "llbot_apis": {},
  "llbot_token": "",
  "forward_rules": {
    "源群QQ": {
      "targets": ["目标群QQ"],
      "note": "备注说明"
    }
  },
  "filter": {
    "qrcode": {
      "enabled": true,
      "keywords": ["加我", "扫码", "微信", "刷单"],
      "mode": "image_with_keyword",
      "decode_enabled": true,
      "decode_timeout": 2
    },
    "contact": {
      "enabled": true,
      "patterns": {
        "phone": "1[3-9]\\d{9}",
        "qq": "(?<!\\d)[1-9]\\d{8,9}(?!\\d)",
        "wechat": "wxid_[a-z0-9]+",
        "email": "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}"
      },
      "keywords": ["QQ", "微信", "加好友", "联系我"]
    },
    "log_only": false
  },
  "forward": {
    "duplicate_window": 5,
    "send_interval": 1.0
  }
}
```

| 配置项 | 说明 |
|--------|------|
| `robot_qq` | 机器人 QQ 号数组（支持多个） |
| `llbot_apis` | 各机器人 API 映射，启动时自动探测生成（不必手动填写） |
| `llbot_token` | LLBot API 鉴权 Token |
| `forward_rules` | 转发规则，源群 → 目标群列表 |
| `filter.qrcode.mode` | `image_with_keyword` / `block_pure_image` / `block_all_images` |
| `filter.qrcode.decode_enabled` | 启用 pyzbar 真二维码解码 |
| `filter.contact.patterns.qq` | QQ 号正则（9~10 位） |
| `filter.log_only` | `true` 时仅记录日志不拦截 |
| `forward.duplicate_window` | 消息去重时间窗口（秒） |
| `forward.send_interval` | 同群发送间隔（秒） |

> `llbot_apis` 由系统在启动时自动探测并写入，用户无需手动维护。`llbot_api` 旧格式（单字符串）作为向后兼容保留。

## 八、 多层过滤系统

### 拦截判断逻辑（优先级从高到低）

1. **QR 码图像解码层**（依赖 pyzbar）
   - 下载消息图片 → pyzbar 解码 → 检查解码内容
   - URL 域名风险识别、内嵌联系方式检出、广告关键词匹配
   - 结果缓存 24 小时，避免重复下载解码

2. **图片规则层**（三模式互斥）
   - `image_with_keyword`（默认）：图片 + 敏感关键词 拦截
   - `block_pure_image`：额外拦截无文字纯图片
   - `block_all_images`：拦截所有含图片的消息

3. **联系方式检测层**
   - 文本关键词匹配（加我、私聊、VX 等）
   - 正则匹配手机号 / QQ / 微信号 / 邮箱
   - 上下文豁免：含「群号、频道、guild」等词跳过 QQ 正则

4. **试运行开关**
   - `log_only = true`：仅输出日志，不执行拦截，适合观察期

### 异常降级

| 场景 | 行为 |
|------|------|
| pyzbar DLL 缺失 | 跳过 QR 解码层，不影响文本过滤 |
| 图片下载超时 | 跳过该图片解码，不影响其他图片 |
| 解码内容为空 | 缓存空结果，避免重复下载 |

## 九、 目录结构

```
├── tray.py                  # 主入口：系统托盘 + LLBot 多实例管理
├── forward.py               # 转发服务（Flask webhook）
├── filter.py                # 消息过滤模块
├── qr_decoder.py            # QR 码图像解码
├── settings.py              # 设置界面
├── wizard.py                # 首次配置向导
├── splash.py                # 启动进度条
├── config.json              # 主配置文件
├── start.vbs / stop.vbs     # 一键启停
├── requirements.txt         # Python 依赖
├── LLBot-CLI-Win-x64/       # LLOneBot 运行环境（实例1）
├── BUILD.md                 # 构建指南
├── OVERVIEW.md              # 全库解构文档
└── tests/                   # 单元测试
```

## 十、 构建安装包

详见 [BUILD.md](BUILD.md)。一键构建：

```bat
build.bat
```

输出 `QQForward_Setup.exe`（约 84MB），位于项目根目录。

## 十一、 更多

项目全库详细解构见 [OVERVIEW.md](OVERVIEW.md)，涵盖：
- 完整数据结构和消息格式
- 多实例管理规则细节
- 异常与安全处理策略
- 已有短板与潜在优化方向
