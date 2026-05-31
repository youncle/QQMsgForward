# QQMsgForward

基于 **LLOneBot** 的 QQ 群消息实时转发系统。Python 胶水层 + Node.js（LLBot）双运行时架构，两端通过 OneBot v11 HTTP 协议通信。

---
## 安装

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

## 快速启动

### 开发模式（源码运行）

```bash
python main.py
```

### 生产模式（打包后）

双击 QQMsgForward_Setup.exe 进行解压，然后进入 QQMsgForward 目录，双击 QQMsgForward.exe，程序启动后出现在系统托盘。

### 停止

双击 scripts\stop.vbs，或右键托盘图标 -> 关闭服务。

### 首次配置

首次运行会自动弹出配置向导，4 步完成：

1. 欢迎页
2. 输入机器人 QQ 号
3. 添加转发规则（源群 -> 目标群）
4. 选择是否开启过滤

配置完成后生成 config/config.json，可在托盘面板中随时修改。



## 功能特性

- **多机器人并行** — 支持 N 个 QQ 号同时监听，端口自增（3000+N / 3080+N），独立运行目录
- **智能消息路由** — 优先使用接收消息的同机器人转发，不在目标群则自动轮询其他可用机器人
- **启动探测** — 运行时通过 GET /get_login_info 动态发现 QQ 到端口映射，不依赖配置顺序
- **三层消息过滤** — QR 码解码 + 图片规则（三模式）+ 联系方式检测
- **试运行模式** — log_only 开关，仅记录不拦截，先验证规则再启用
- **消息去重与限流** — 可配置去重窗口（秒）+ 发送间隔（秒）
- **转发延迟** — 每条消息转发前固定延迟 1 秒
- **可视化配置面板** — tkinter 三标签页（状态/转发/过滤）
- **系统托盘** — 右下角图标，状态指示
- **一键构建** — PyInstaller + 7-Zip SFX 单文件安装包
- **无配置文件依赖** — 首次运行时向导自动生成配置

## 目录结构

```
QQMsgForward/
|-- main.py                    # 程序入口
|-- requirements.txt           # Python 依赖
|-- src/
|   |-- tray.py                # 主控（托盘+生命周期）~750行
|   |-- forward.py             # 转发引擎 ~242行
|   |-- filter.py              # 消息过滤 ~171行
|   |-- qr_decoder.py          # 二维码解码 ~136行
|   |-- settings.py            # 配置面板 ~261行
|   |-- wizard.py              # 配置向导 ~234行
|   +-- splash.py              # 启动动画 ~67行
|-- config/
|   +-- config.json            # 运行配置（首次启动生成）
|-- docs/（OVERVIEW.md / BUILD.md / 使用教程.txt）
|-- scripts/（build.bat / start.vbs / stop.vbs）
|-- resources/ +-- app.ico
|-- runtime/                   # LLBot 运行时
|-- logs/                      # 日志（自动生成）
+-- output/                    # 构建产物
```

## 架构概览

```
start.vbs ---> pythonw tray.py ---> Splash 启动画面
                        |
              +---------+---------+
              |         |         |
           LLBot-1   LLBot-2   LLBot-N
           port3000    3001     3000+N
              |         |         |
              +----+----+---------+
                   v HTTP POST /webhook
            Flask Forward Service 9090
                   |
         +---------+---------+
         v         v         v
     目标群1    目标群2    目标群N
```

## 过滤系统

| 模式 | 行为 |
|---|---|
| image_with_keyword | 仅含图片+关键词时拦截（默认）|
| block_pure_image | 额外拦截无文字纯图片 |
| block_all_images | 拦截所有含图片的消息 |
| log_only | 试运行，仅记录不拦截 |

## 构建打包

```bat
scripts\build.bat
```

输出：output\QQMsgForward_Setup.exe
