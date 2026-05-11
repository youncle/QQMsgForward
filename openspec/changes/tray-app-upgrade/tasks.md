## 1. 托盘图标升级

- [ ] 1.1 用 PIL 绘制聊天气泡+转发箭头图标，替代纯色绿圆点，提供 green/red/yellow 三种颜色
- [ ] 1.2 添加黄色状态图标，在部分服务异常时使用

## 2. 线程模型重构

- [ ] 2.1 将 `icon.run()` 改为 `icon.run_detached()`，在 daemon 线程中运行托盘
- [ ] 2.2 主线程改为运行 tkinter `root.mainloop()`
- [ ] 2.3 确认监控线程（monitor_loop）在新模型下正常工作

## 3. 主面板窗口

- [ ] 3.1 创建含 `ttk.Notebook` 的 tk 根窗口，启动时 `withdraw()` 隐藏
- [ ] 3.2 创建状态选项卡：显示 LLBot（端口 3000）和转发脚本（端口 8080）运行状态，用绿色/红色指示点
- [ ] 3.3 创建设置选项卡：嵌入从 settings.py 重构的 `create_settings_frame(parent)`
- [ ] 3.4 拦截 `WM_DELETE_WINDOW` 协议，X 按钮改为 `withdraw()` 隐藏窗口

## 4. 左键点击 hook

- [ ] 4.1 实现 `ctypes` 窗口过程 hook，拦截 pystray 隐藏窗口的 `WM_LBUTTONUP` 消息
- [ ] 4.2 通过 `root.after(0, callback)` 安全切回主线程打开主面板

## 5. 右键菜单简化

- [ ] 5.1 右键菜单精简为"打开主面板"和"关闭服务"两项，移除"打开设置"和"查看状态"
- [ ] 5.2 "打开主面板"菜单项调用与左键相同的窗口显示逻辑

## 6. 关闭服务统一

- [ ] 6.1 托盘"关闭服务"改为先创建 `.shutdown.flag` 标志文件（保持与 stop.vbs 一致），然后立即调用 `shutdown_service()` 执行关闭，不等监控轮询
- [ ] 6.2 关闭时主面板窗口执行 `destroy()` 后 `icon.stop()`

## 7. 桌面快捷方式

- [ ] 7.1 首次运行时检测桌面是否存在 `QQ转发.lnk`，不存在则通过 VBS 或 COM 自动创建指向 `start.vbs` 的快捷方式

## 8. settings.py 重构

- [ ] 8.1 将 `open_settings()` 拆为 `create_settings_frame(parent, on_save=None)`，返回可嵌入 Notebook 的 `ttk.Frame`
- [ ] 8.2 保存按钮结果不在 settings frame 内弹 messagebox，改为返回状态供主窗口状态栏显示
- [ ] 8.3 保持 `load_config()` / `save_config()` 接口不变，确保向后兼容
