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
| `docs/architecture.md` | 架构详解（模块交互/数据流/异常处理） |
| `docs/config_reference.md` | 配置文件完整参考（所有字段含义/类型/默认值） |
| `docs/build.md` | 构建打包指南 |
| `docs/troubleshooting.md` | 常见问题排查 |

---

## 日志

`logs/forward.log` — 按天轮转，保留最近 2 份副本。

---

## 相关链接

- 官网: https://luckylillia.com
- GitHub: https://github.com/LLOneBot/LuckyLilliaBot
- WebUI: http://127.0.0.1:3080/#onebot
- WebUI 默认密码: `llbot@forward123`
