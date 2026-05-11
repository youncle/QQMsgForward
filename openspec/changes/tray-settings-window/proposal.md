## Why

托盘"查看状态"点击后窗口一闪而过，因为 PowerShell 的 `[System.Windows.MessageBox]` 缺少程序集加载。同时修改配置必须手动编辑 `config.json` 并重启，体验不像桌面程序。

## What Changes

- **修复查看状态** — 用 tkinter.messagebox 替代 PowerShell 弹窗，稳定显示不闪退
- **新增设置窗口** — 托盘菜单增加"打开设置"，弹出 tkinter 窗口可视化编辑转发规则和过滤配置
- **热保存** — 设置窗口"保存"直接写入 config.json，无需重启即可生效

## Capabilities

### New Capabilities

- `settings-window`: tkinter 设置窗口，可视化编辑转发规则、QR 码过滤开关/关键词、联系方式过滤开关/正则，保存写入 config.json

### Modified Capabilities

- `one-click-launch`: 托盘菜单新增"打开设置"项；"查看状态"弹窗从 PowerShell 改为 tkinter

## Impact

- 新增文件：`settings.py`（tkinter 设置窗口）
- 修改文件：`tray.py`（修复 show_status_window + 增加"打开设置"菜单项）
- 依赖：仅 Python 标准库 tkinter（无额外 pip 安装）
