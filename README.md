# QQ 群消息转发

基于 [LLOneBot](https://github.com/LLOneBot/LuckyLilliaBot) 的 QQ 群消息实时转发系统，支持广告过滤、系统托盘管理、一键安装。

## 功能

- **群消息转发** — 监听源群消息，实时转发到目标群
- **广告过滤** — QR 码解码识别 + 联系方式正则匹配
  - QR 码检测：图片 + 关键词 / 纯图片 / 所有图片 三种拦截模式
  - 联系方式检测：正则匹配手机号、QQ 号、微信号、邮箱
  - 试运行模式：先观察再拦截
- **系统托盘** — 托盘图标显示运行状态，右键菜单可查看状态、修改配置、退出
- **一键安装包** — 用户无需安装 Python，双击安装即用

## 用户使用（安装包）

1. 双击 `QQForward_Setup.exe`，选择目录解压
2. 首次登录，进入 'QQForward/LLBot-CLI-Win-x64/'，双击 'llbot.exe' 启动，配置 LLOneBot
3. 进入 `QQForward/`，双击 `QQForward.exe` 启动
4. 首次启动自动创建桌面快捷方式
5. 配置说明见下文「配置」章节

构建安装包详见 [BUILD.md](BUILD.md)。

## 开发使用

### 1. 配置 LLOneBot

1.运行 QQForward/LLBot-CLI-Win-x64/llbot.exe 程序；根据提示登录机器人 QQ 号。

2.打开 LLOneBot WebUI（`http://127.0.0.1:3080/#onebot`，密码 `llbot@forward123`），确保启用：

- **HTTP API**（端口 3000）— 发送消息
- **HTTP POST Webhook**（URL: `http://127.0.0.1:8080/webhook`）— 接收消息

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 启动

```bash
python tray.py
```

或双击 `start.vbs`。

## 配置

编辑 `config.json`（安装包已内置默认配置）：

```json
{
  "robot_qq": 2776992588,
  "forward_rules": { "源群QQ": ["目标群QQ"] },
  "llbot_api": "http://127.0.0.1:3000",
  "filter": {
    "qrcode": {
      "enabled": true,
      "keywords": ["加我", "扫码", "微信", ...],
      "mode": "image_with_keyword"
    },
    "contact": {
      "enabled": true,
      "patterns": {
        "phone": "1[3-9]\\d{9}",
        "qq": "(?<!\\d)[1-9]\\d{4,9}(?!\\d)",
        "wechat": "wxid_[a-z0-9]+",
        "email": "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}"
      },
      "keywords": ["QQ", "微信", "加好友", ...]
    },
    "log_only": false
  }
}
```

| 配置项 | 说明 |
|--------|------|
| `robot_qq` | 机器人 QQ 号，用于区分自身消息 |
| `forward_rules` | 转发规则，格式 `{"源群": ["目标群1", "目标群2"]}` |
| `filter.qrcode.enabled` | 是否启用二维码过滤 |
| `filter.qrcode.mode` | `image_with_keyword` / `pure_image` / `all_images` |
| `filter.qrcode.keywords` | 触发拦截的关键词列表 |
| `filter.contact.enabled` | 是否启用联系方式过滤 |
| `filter.contact.patterns` | 正则表达式（手机号/QQ号/微信号/邮箱） |
| `filter.log_only` | `true` 时仅记录日志不拦截（试运行） |

## 目录结构

```
├── tray.py                  # 主入口，系统托盘 + GUI
├── forward.py               # 转发服务（Flask webhook）
├── filter.py                # 消息过滤模块
├── qr_decoder.py            # QR 码解码（pyzbar）
├── settings.py              # 设置界面
├── wizard.py                # 首次配置向导
├── splash.py                # 启动进度条
├── config.json              # 配置文件
├── requirements.txt         # Python 依赖
├── build.bat                # 一键构建安装包
├── install.bat              # 开发环境安装脚本
├── start.vbs / stop.vbs     # 一键启停
├── app.ico                  # 程序图标（自动生成）
├── libiconv.dll             # zbar 依赖
├── libzbar-64.dll           # 二维码解码引擎
├── msvcr120.dll             # VC++ 2013 运行时
├── LLBot-CLI-Win-x64/       # LLOneBot 运行环境
├── tests/                   # 单元测试
└── openspec/                # 规格文档
```
