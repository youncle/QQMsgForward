## Why

当前启动需要右键 .bat → 以管理员身份运行，弹出两个 CMD 黑窗，关闭也不方便。同时转发群中有大量广告消息（二维码图片、私人联系方式），需要自动拦截。

## What Changes

- **一键启动/关闭**：双击 VBS 脚本即可启动/关闭全部服务，无需右键，自动获取管理员权限
- **系统托盘图标**：Python 托盘小程序显示运行状态，右键可关闭服务，双击可查看状态
- **窗口隐藏**：LLBot 和转发脚本全部后台静默运行，不再弹出 CMD 窗口
- **二维码消息过滤**：检测消息中的图片段，配合上下文关键词（"加我""扫码"等）识别并拦截 QR 码广告
- **联系方式文本过滤**：正则匹配手机号、QQ 号、微信号、邮箱等，拦截包含私人联系方式的消息
- 代码中配置项从硬编码移到独立的 `config.json`，方便修改

## Capabilities

### New Capabilities

- `one-click-launch`: VBS 一键启动/关闭脚本 + Python 托盘图标常驻程序，管理员权限自动获取，LLBot 和转发脚本后台静默运行
- `message-filter`: 消息过滤器，支持二维码检测和联系方式正则匹配，可配置过滤规则和拦截行为

### Modified Capabilities

<!-- 无现有 specs 需要修改 -->

## Impact

- 新增文件：`start.vbs`、`stop.vbs`、`tray.py`（托盘程序）、`config.json`（配置文件）、`filter.py`（过滤模块）
- 修改文件：`qq-message-forward.py`（读取 config.json，接入过滤模块）
- 废弃文件：`启动 - 右键 - 以管理员身份运行.bat`、`关闭 - 右键 - 以管理员身份运行.bat`
- 依赖：Python 标准库 `tkinter`（托盘图标），无需额外 pip 安装
