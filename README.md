# QQ 群消息转发

基于 [LLOneBot](https://github.com/LLOneBot/LuckyLilliaBot) 的 QQ 群消息实时转发系统，支持广告过滤、一键启停、托盘管理。

## 功能

- **群消息转发** — 监听源群消息，实时转发到目标群
- **广告过滤** — 自动拦截二维码广告和私人联系方式
  - QR 码检测：图片 + 关键词 / 纯图片拦截
  - 联系方式检测：正则匹配手机号、QQ 号、微信号、邮箱
  - 试运行模式：先观察再拦截
- **一键启停** — 双击 `start.vbs` 启动，双击 `stop.vbs` 关闭
- **托盘管理** — 系统托盘图标显示运行状态，右键菜单可查看状态或关闭

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 LLOneBot

打开 LLOneBot WebUI（`http://127.0.0.1:3080/#onebot`，密码 `llbot@forward123`），确保启用：

- **HTTP API**（端口 3000）— 用于发送消息
- **HTTP POST Webhook**（URL: `http://127.0.0.1:8080/webhook`）— 用于接收消息

### 3. 修改转发规则

编辑 `config.json`：

```json
{
  "forward_rules": {
    "1079264158": ["1080631149"]
  }
}
```

格式：`"源群ID": ["目标群ID1", "目标群ID2"]`

### 4. 启动

双击 `start.vbs`，UAC 确认后服务在后台启动，托盘出现绿色圆点。

## 配置说明

```json
{
  "robot_qq": 2776992588,
  "forward_rules": { "源群": ["目标群"] },
  "llbot_api": "http://127.0.0.1:3000",
  "filter": {
    "qrcode": {
      "enabled": true,
      "keywords": ["加我", "扫码", "微信", ...],
      "block_pure_image": true
    },
    "contact": {
      "enabled": true,
      "patterns": { "phone": "1[3-9]\\d{9}", ... },
      "keywords": ["我的Q", "私聊我", ...]
    },
    "log_only": false
  }
}
```

| 配置项 | 说明 |
|--------|------|
| `filter.qrcode.enabled` | 是否启用二维码过滤 |
| `filter.qrcode.keywords` | 触发拦截的关键词列表 |
| `filter.qrcode.block_pure_image` | 是否拦截所有纯图片消息（无文字 = 疑似二维码） |
| `filter.contact.enabled` | 是否启用联系方式过滤 |
| `filter.contact.patterns` | 正则表达式（手机号/QQ号/微信号/邮箱） |
| `filter.log_only` | `true` 时仅记录日志不拦截（先观察再启用） |

## 目录结构

```
├── config.json              # 配置文件
├── qq-message-forward.py    # 转发服务（Flask webhook）
├── filter.py                # 消息过滤模块
├── tray.py                  # 系统托盘程序
├── start.vbs                # 一键启动
├── stop.vbs                 # 一键关闭
├── requirements.txt         # Python 依赖
├── tests/
│   └── test_filter.py       # 过滤单元测试（32 个）
├── LLBot-CLI-Win-x64/       # LLOneBot 运行环境
└── forward.log              # 运行日志
```
