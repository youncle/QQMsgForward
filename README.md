# QQMsgForward

基于 **LLOneBot** 的 QQ 群消息实时转发系统。Python 胶水层 + Node.js（LLBot）双运行时，通过 OneBot v11 HTTP POST 协议通信。

---

## 功能特性

- **多机器人并行** — 支持 N 个 QQ 号同时监听，端口自增（3000+N / 3080+N），独立运行目录
- **智能消息路由** — 优先使用接收消息的同机器人转发，不在目标群则自动轮询其他可用机器人
- **启动动态探测** — 运行时通过 `/get_login_info` 动态发现 QQ→端口映射，不依赖配置顺序
- **三层消息过滤** — QR 码真解码 + 图片规则（三模式）+ 联系方式检测（含群号白名单豁免）
- **试运行模式** — `log_only` 开关，仅记录不拦截，先验证规则再启用
- **消息去重与限流** — 可配置去重窗口（秒）+ 发送间隔（秒）
- **转发延迟** — 每条消息转发前固定 1 秒延迟
- **配置热重载** — `get_config()` 每次从文件读取，修改配置无需重启（除 `robot_qq` 外）
- **优雅关闭** — `.shutdown.flag` 文件触发，1 秒轮询检测，自动终止 LLBot 进程
- **可视化配置面板** — tkinter 四标签页（状态 / 转发 / 过滤 / 微信），系统托盘常驻
- **一键构建** — PyInstaller + 7-Zip SFX 单文件安装包
- **自动创建桌面快捷方式** — 首次运行自动创建

---

- **企业微信转发** — 支持 Webhook API 和桌面端 UI 操控两种模式，将 QQ 群消息实时转发到企业微信群
- **多模式企微通道** — API 模式通过 Webhook Key 发送，UI 模式模拟键盘剪贴板操控企业微信桌面端
- **文件消息转图片** — 自动识别文件消息中的图片文件，转换后转发（支持 ntcall API 下载）

## 环境要求

- Python 3.9+
- QQNT 桌面客户端（已登录状态）
- Windows 10 / 11

---

## 快速安装

```bash
pip install -r requirements.txt
```

### 依赖清单

| 包 | 用途 |
|---|---|
| flask>=3.0 | WebHook 接收服务 |
| requests>=2.31 | HTTP 客户端（带连接池 + 自动重试） |
| pystray>=0.19 | 系统托盘图标 |
| pillow>=10.0 | 托盘图标生成 + 图片处理 |
| pyzbar>=0.1.9 | QR 码解码（可选，DLL 缺失时自动降级） |
| uiautomation>=2.0.17 | 企业微信 UI 自动化（预留） |
| pywin32>=306 | 企业微信桌面端操控（SendKeys + 剪贴板） |

---

## 快速启动

### 开发模式（源码运行）

```bash
python main.py
```

### 生产模式（打包后）

双击 `QQMsgForward_Setup.exe` 解压，进入 `QQMsgForward` 目录，双击 `QQMsgForward.exe`。程序启动后出现在系统托盘（右下角绿色圆点）。

### 停止服务

- 双击 `scripts\stop.vbs`（自动提权，优雅关闭 → 15 秒超时后强制终止）
- 右键托盘图标 → 关闭服务

### 首次配置

首次运行自动弹出配置向导，4 步完成：

1. **欢迎页** — 项目介绍
2. **机器人 QQ 号** — 输入一个或多个 QQ（逗号分隔）
3. **转发规则** — 添加源群 → 目标群映射
4. **过滤开关** — 选择是否开启图片广告/联系方式过滤

配置完成后生成 `config/config.json`，可在托盘面板中随时修改。

---

## 快速导航

| 文档 | 说明 |
|------|------|
| `docs/ARCHITECTURE.md` | 架构详解（模块交互/数据流/异常处理） |
| `docs/CONFIG_REFERENCE.md` | 配置文件完整参考（所有字段含义/类型/默认值） |
| `docs/BUILD.md` | 构建打包指南 |
| `docs/TROUBLESHOOTING.md` | 常见问题排查 |

---

## 架构概览

```
start.vbs ───→ pythonw tray.py ───→ Splash 启动画面
                      │
            ┌─────────┼─────────┐
            │         │         │
         LLBot-1   LLBot-2   LLBot-N
        port 3000   3001     3000+N
            │         │         │
            └────┬────┼─────────┘
                 ▼  HTTP POST /webhook
          Flask 转发服务 :9090
                 │
           ┌─────┼─────┐
           ▼     ▼     ▼
        目标群1 目标群2 目标群N
```
`
**企业微信转发通道（新增）**：
`
QQ 群消息 → LLBot POST /webhook
                │
          try_forward_wecom()
                │
          ┌──────┴──────┐
          ▼              ▼
     API 模式         UI 模式
   Webhook Key    企微桌面端操控
   发送到企微群    SendKeys+剪贴板
`
  - **API 模式**：通过企业微信机器人 Webhook API (qyapi.weixin.qq.com) 发送消息
  - **UI 模式**：通过 win32com SendKeys + 剪贴板模拟人工操作企业微信桌面客户端

`

---

## 过滤系统

| 关卡 | 模块 | 行为 |
|------|------|------|
| 第 1 关 | QR 码解码（pyzbar） | 真解码二维码内容，检测 URL/域名/联系方式/广告关键词 |
| 第 2 关 | 图片规则 | 三模式：`image_with_keyword` / `block_pure_image` / `block_all_images` |
| 第 3 关 | 联系方式检测 | 正则匹配手机号 / QQ 号（群号白名单豁免）/ 微信号 / 邮箱 + 关键词 |
| 第 3.5 关 | 文件→图片转换 | _convert_file_to_image() 将 type=file 中的图片转为 type=image，非图片移除 |

---

## 目录结构

```
QQMsgForward/
├── main.py                    # 程序入口（导入 src/tray.py）
├── requirements.txt           # Python 依赖
├── src/
│   ├── tray.py          (~750行)  # 主控：托盘 + LLBot 启停 + Flask 守护 + UI 窗口
│   ├── forward_qq.py    (~242行)  # 转发引擎：WebHook 接收 + 去重 + 限流 + 路由
│   ├── filter.py        (~171行)  # 消息过滤：三层过滤规则引擎
│   ├── qr_decoder.py    (~136行)  # QR 码图像解码（pyzbar）+ LRU 缓存
│   ├── settings.py      (~261行)  # 配置面板：转发/过滤规则 CRUD（tkinter）
│   ├── wizard.py        (~234行)  # 配置向导：4 步引导 + 居中布局 + 默认配置生成
│   ├── splash.py         (~67行)  # 启动进度条浮窗（无边框 + 平滑动画）
│   └── __init__.py               # 空文件，标识包
│   ├── wecom.py          (~280行)  # 企业微信转发引擎：API/UI 双模式路由
│   ├── wecom_ui.py       (~411行)  # 企微 UI 操控引擎：SendKeys + 剪贴板自动化
│   ├── nt_utils.py        (~66行)  # NT 工具函数：通过 WebUI ntcall API 获取文件
├── config/
│   ├── config.json              # 运行配置（首次启动向导自动生成）
│   └── .window_state.json       # 窗口几何信息（自动保存/恢复）
├── runtime/
│   ├── LLBot-CLI-Win-x64/       # 主 LLBot 实例
│   ├── LLBot-CLI-Win-x64-2/     # 多实例副本（自动复制）
│   ├── libiconv.dll             # pyzbar 依赖
│   ├── libzbar-64.dll           # pyzbar 依赖
│   └── msvcr120.dll             # pyzbar 依赖
├── docs/
│   ├── ARCHITECTURE.md          # 架构详解
│   ├── CONFIG_REFERENCE.md      # 配置参考
│   ├── BUILD.md                 # 构建指南
│   └── TROUBLESHOOTING.md       # 常见问题排查
├── scripts/
│   ├── start.vbs                # 一键启动（自动提权）
│   ├── stop.vbs                 # 一键停止（优雅→强制）
│   └── build.bat                # 一键构建安装包
├── resources/app.ico            # 应用图标
├── logs/                        # 日志（自动创建，按天轮转保留 2 份）
└── output/                      # 构建产物（QQMsgForward_Setup.exe）
```

---

## 日志

`logs/forward.log` — 按天轮转，保留最近 2 份副本。

---

## 相关链接

- 官网: https://luckylillia.com
- GitHub: https://github.com/LLOneBot/LuckyLilliaBot
- WebUI: http://127.0.0.1:3080/#onebot
- WebUI 默认密码: `llbot@forward123`
