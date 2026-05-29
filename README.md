# QQ 群消息转发

基于 [LLOneBot](https://github.com/LLOneBot/LuckyLilliaBot) 的 QQ 群消息实时转发系统，支持多机器人、广告过滤、系统托盘管理。

## 功能

- **群消息转发** — 监听源群消息，实时转发到目标群
- **多机器人** — 同时运行多个 QQ 机器人，自动分配端口，智能匹配发送 API
- **广告过滤** — QR 码解码识别 + 联系方式正则匹配
  - 三种拦截模式：图片+关键词 / 纯图片 / 所有图片
  - 联系方式检测：手机号、QQ 号（9位以上）、微信号、邮箱
  - 试运行模式：先观察再拦截
- **系统托盘** — 托盘图标显示运行状态，右键菜单查看状态、修改配置

## 快速开始

### 安装包用户

1. 双击 `QQForward_Setup.exe`，选择目录解压
2. 双击 `start.vbs` 启动
3. 首次启动自动弹出配置向导
4. 系统托盘中可打开设置修改转发规则

### 开发运行

```bash
pip install -r requirements.txt
python tray.py
```

或双击 `start.vbs`。

## 多机器人

配置 `config.json` 中的 `robot_qq` 数组，系统自动启动对应数量的 LLBot 实例：

```json
{
  "robot_qq": [2776992588, 85039678, 352140057]
}
```

### 端口分配

| 实例 | 目录 | HTTP API | WebUI |
|------|------|----------|-------|
| 实例1 | `LLBot-CLI-Win-x64` | 3000 | 3080 |
| 实例2 | `LLBot-CLI-Win-x64-2` | 3001 | 3081 |
| 实例3 | `LLBot-CLI-Win-x64-3` | 3002 | 3082 |

首次启动自动复制目录并配置端口。启动时 QQ 登录窗口依次弹出（间隔 10 秒），可分别登录不同 QQ。

消息转发采用智能匹配：**哪个机器人接收的消息，优先用哪个机器人发送**。接收方不在目标群时自动轮询其他机器人。

## 配置

编辑 `config.json`：

```json
{
  "robot_qq": [2776992588, 85039678],
  "llbot_apis": {
    "2776992588": "http://127.0.0.1:3000",
    "85039678": "http://127.0.0.1:3001"
  },
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
| `llbot_apis` | 各机器人 API 地址映射（自动生成） |
| `forward_rules` | 转发规则，源群 → 目标群列表 |
| `filter.qrcode.mode` | `image_with_keyword` / `block_pure_image` / `block_all_images` |
| `filter.contact.patterns.qq` | QQ 号正则（当前 9~10 位） |
| `filter.log_only` | `true` 时仅记录日志不拦截 |
| `forward.duplicate_window` | 消息去重时间窗口（秒） |
| `forward.send_interval` | 同群发送间隔（秒） |

## 目录结构

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
├── tests/                   # 单元测试
└── openspec/                # 设计规格文档
```

## 构建安装包

详见 [BUILD.md](BUILD.md)。
