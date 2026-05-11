# 托盘应用升级为桌面应用

## 背景

`tray.py` 目前是"右键菜单弹窗工具"——绿色圆点图标无辨识度，状态查看用 messagebox，左键点击无反应，关闭逻辑与 stop.vbs 不一致。需升级为正经桌面应用。

## 目标

- 左键点击托盘图标打开主面板（含状态和设置两个选项卡）
- 用 PIL 绘制有辨识度的聊天气泡图标
- 窗口关闭时隐藏到托盘而非退出
- 关闭服务统一走标志文件优雅退出流程
- 首次运行自动创建桌面快捷方式

## 技术方案

### 线程模型

`pystray.Icon.run_detached()` 在 daemon 线程运行托盘事件循环，主线程空闲跑 `root.mainloop()`。tkinter 所有操作都在主线程，解决 messagebox 跨线程无响应问题。

### 左键点击

通过 `ctypes.windll.user32.SetWindowLongPtrW` hook pystray 内部隐藏窗口的 `WM_LBUTTONUP` 消息。拦截后通过 `root.after(0, callback)` 安全切回主线程打开窗口。

右键菜单保留"打开主面板"作为备用入口。

### 窗口生命周期

主窗口启动时创建并 `withdraw()` 隐藏。触发打开时 `deiconify() + lift()`。点 X 或任务栏关闭时 `protocol('WM_DELETE_WINDOW')` 拦截改为 `withdraw()`。只有"关闭服务"才 `destroy()`。

### 关闭服务

托盘"关闭服务"先创建 `.shutdown.flag` 标志文件，监控线程检测后执行优雅关闭：先 `terminate()` 转发子进程（等 5s），再 `taskkill` 残留进程，最后 `icon.stop()`。与 `stop.vbs` 逻辑一致。

### settings.py 重构

将 `open_settings()` 拆为 `create_settings_frame(parent)`，返回可嵌入 Notebook 的 `ttk.Frame`。`load_config()` / `save_config()` 接口不变。

### 桌面快捷方式

首次运行时检测桌面是否有 `QQ转发.lnk`，无则通过 WSH Shell 创建指向 `start.vbs` 的快捷方式。

## 风险

- 左键 hook 依赖 pystray 未公开的内部实现 → 右键菜单保留备用入口
- `root.after(0)` 跨线程调用的安全性 → 是 tkinter 推荐做法，无问题

## 涉及文件

| 文件 | 改动 |
|------|------|
| `tray.py` | 重写：线程模型、左键 hook、Notebook 窗口、状态 Tab、关闭逻辑 |
| `settings.py` | 重构：拆出 `create_settings_frame(parent)` |
