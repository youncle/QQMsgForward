## Why

托盘程序目前只是一个"右键菜单弹窗工具"——绿色圆点图标没辨识度，状态查看用 messagebox 弹窗体验差，左键点击没有反应。需要把它升级成正经桌面应用：有辨识度的图标、点击就能打开的主面板、像桌面程序一样的关闭逻辑。

## What Changes

- 托盘图标从纯色绿圆点改为用 PIL 绘制的聊天气泡+转发箭头图形，运行/异常/警告三种颜色
- 左键单击托盘图标打开主面板（Windows WM_LBUTTONUP hook），右键菜单精简为"打开主面板"和"关闭服务"两项
- 新增含状态选项卡和设置选项卡的主面板窗口，替代原来的 messagebox 弹窗和独立设置窗口
- 主面板点 X 关闭时隐藏到托盘而非退出，任务栏右键关闭同理
- "关闭服务"统一为 stop.vbs 的优雅关闭逻辑：创建标志文件 → 等监控线程自清理 → force kill 残留，而非直接 kill
- settings.py 重构为可嵌入 Frame，不再独立创建 Tk 根窗口
- 首次运行时自动在桌面创建"QQ转发.lnk"快捷方式，指向 start.vbs

## Capabilities

### New Capabilities

- `tray-main-panel`: 带选项卡的主面板窗口——状态 Tab 显示端口状态和日志，设置 Tab 内嵌原设置界面；左键托盘打开、X 按钮隐藏到托盘；右键托盘菜单提供备用入口

### Modified Capabilities

- `one-click-launch`: 托盘右键菜单从"查看状态+打开设置+关闭服务"改为"打开主面板+关闭服务"；关闭服务行为从直接 taskkill 改为标志文件驱动的优雅关闭（与 stop.vbs 一致）；托盘图标从纯色圆点改为 PIL 绘制的图形图标

## Impact

- `tray.py`: 大幅重写，线程模型从 icon.run() 阻塞主线程改为 run_detached() + tkinter mainloop
- `settings.py`: 重构，从自建 Tk 窗口改为返回可嵌入 Frame
- 新增依赖：`ctypes`（标准库，用于左键 hook）、`ttk.Notebook`（标准库）
- `one-click-launch` spec 需要更新托盘菜单、图标、关闭行为相关需求
