# QQMsgForward

基于 **LLOneBot** 的 QQ 群消息实时转发系统。Python 胶水层 + Node.js（LLBot）双运行时架构，两端通过 OneBot v11 HTTP 协议通信。支持多 QQ 机器人实例并行、消息过滤、可视化配置。

---

## 功能特性

- **多机器人并行** — 支持 N 个 QQ 号同时监听，端口自动递增（3000+N / 3080+N）
- **智能消息路由** — 优先使用接收消息的同机器人转发，不在目标群则自动轮询其他可用机器人
- **消息过滤** — 四层拦截体系：QR 码解码 → 图片规则(三模式) → 联系方式正则 → 敏感关键词
- **启动探测** — 运行时通过 `GET /get_login_info` 动态发现 QQ 到端口映射，不依赖配置顺序
- **消息去重与限流** — 可配置的去重窗口(秒) + 群消息发送间隔
- **可视化配置面板** — tkinter 图形界面（状态/转发规则/过滤规则三个标签页）
- **系统托盘** — 右下角托盘图标，支持状态指示、快捷操作
- **一键安装/启动/停止** — 提供完整构建、安装、启动脚本

---

## 快速开始

### 环境要求

- Python 3.9+
- QQNT 桌面客户端（已登录状态）
- Windows 10/11

### 安装依赖

```bash
pip install -r requirements.txt
```

requirements.txt：

```
flask>=3.0
requests>=2.31
pystray>=0.19
pillow>=10.0
pyzbar>=0.1.9
```

### 启动

**开发模式：**

```bash
python main.py
```

**生产模式：** 双击 `scripts\start.vbs`（自动提权管理员）

### 停止

双击 `scripts\stop.vbs` 或右键托盘图标 → 关闭服务

---

## 架构概览

```
                  用户视角 (End User)
  start.vbs ---> pythonw tray.py
  tray.py ---> 系统托盘 + Splash 启动画面
              |-- 启动 N 个 LLBot 实例 (多QQ)
              |-- 启动 Flask 转发服务 (port 9090)
              +-- tkinter 设置面板 (3 个 Tab)
                       |
          +------------+------------+
          v            v            v
    LLBot-1        LLBot-2       LLBot-N
    (QQ A)         (QQ B)        (QQ C)
    port 3000      port 3001     port 3002+N
    WebUI 3080     WebUI 3081    WebUI 3080+N
       |               |            |
       +---------------+------------+
                       v HTTP POST /webhook
              Flask Forward Service
              port 9090 (forward.py)
                       |
         +-------------+-------------+
         v             v             v
    目标群1         目标群2        目标群N
```

### 核心流程

```
QQ 群消息
  +--> LLBot -- POST /webhook --> forward.py
       |-- 过滤：仅群聊消息、跳过机器人自身（防循环）
       |-- 匹配转发规则
       |-- 消息去重 + 限流
       |-- 过滤检测（QR码 / 图片 / 联系方式）
       +-- 推送到目标群
```

---

## 目录结构

```
QQMsgForward/
|-- main.py                    # 程序入口
|-- requirements.txt           # Python 依赖
|-- src/
|   |-- tray.py                # 主控（托盘 + 生命周期）
|   |-- forward.py             # 转发引擎（Flask WebHook）
|   |-- filter.py              # 消息过滤引擎
|   |-- qr_decoder.py          # 二维码解码
|   |-- settings.py            # 配置面板
|   |-- wizard.py              # 首次配置向导
|   +-- splash.py              # 启动进度浮窗
|-- config/
|   +-- config.json            # 运行配置
|-- docs/
|   |-- OVERVIEW.md            # 项目解剖文档
|   |-- BUILD.md               # 构建指南
|   +-- 使用教程.txt            # 用户说明
|-- scripts/
|   |-- build.bat              # 构建（PyInstaller + 7z SFX）
|   |-- start.vbs              # 启动
|   +-- stop.vbs               # 停止
|-- resources/
|   +-- app.ico                # 程序图标
|-- runtime/                   # LLBot 运行时 (gitignored)
|-- logs/                      # 日志 (自动生成)
+-- output/                    # 构建产物 (gitignored)
```

---

## 配置说明

配置文件 `config/config.json`：

```json
{
  "robot_qq": [85039678, 2776992588],
  "forward_rules": {
    "源群号": {"targets": ["目标群号"], "note": "备注"}
  },
  "llbot_apis": {
    "QQ号": "http://127.0.0.1:端口"
  },
  "llbot_token": "",
  "filter": {
    "qrcode": {
      "mode": "image_with_keyword",
      "decode_enabled": true
    },
    "contact": {
      "enabled": true
    },
    "log_only": false
  },
  "forward": {
    "duplicate_window": 5,
    "send_interval": 1.0
  }
}
```

### 过滤模式

| 模式 | 说明 |
|---|---|
| `image_with_keyword` | 仅拦截同时包含图片和关键词的消息 |
| `block_pure_image` | 额外拦截无文字纯图片 |
| `block_all_images` | 拦截所有含图片的消息 |
| `log_only` | 试运行模式，仅记录不拦截 |

---

## 多实例管理

| 实例 | 运行目录 | HTTP API 端口 | WebUI 端口 |
|---|---|---|---|
| 0 | `runtime/LLBot-CLI-Win-x64` | 3000 | 3080 |
| 1 | `runtime/LLBot-CLI-Win-x64-2` | 3001 | 3081 |
| N | `runtime/LLBot-CLI-Win-x64-(N+1)` | 3000+N | 3080+N |

实例 0 使用原始目录，后续实例自动拷贝生成独立目录，端口自增。

---

## 构建打包

```bat
scripts\build.bat
```

构建流程：

1. **PyInstaller** 打包 `main.py` -> `QQMsgForward.exe`
2. **Staging**：组装目录（运行时 / 配置 / 脚本 / 图标）
3. **压缩**：7z 压缩 + SFX 自解压模块
4. **输出**：`output\QQMsgForward_Setup.exe`

### 打包依赖

- PyInstaller：`pip install pyinstaller`
- 7-Zip（需加入 PATH）

---

## 技术栈

| 组件 | 技术 |
|---|---|
| 运行时 | Python 3.9+, Node.js (LLBot) |
| Web 框架 | Flask |
| 系统托盘 | pystray |
| 图像处理 | Pillow, pyzbar |
| GUI | tkinter |
| 协议 | OneBot v11 (HTTP POST) |
| 打包 | PyInstaller + 7-Zip SFX |

---

## 开发相关

### WebUI 访问

启动后在浏览器打开 `http://127.0.0.1:3080`

默认密码：`llbot@forward123`

### 日志

`logs/forward.log`，按天轮转，保留最近 2 份。

---

## 许可证

内部项目
