## Context

当前 `tray.py` 用 `pystray.Icon.run()` 阻塞主线程跑托盘事件循环，tkinter 窗口（设置、messagebox）在 pystray 的回调线程中创建，导致两个问题：跨线程 tkinter 造成 messagebox 按钮不响应；左键点击无法绑定。需要改为 pystray 后台线程 + tkinter 主线程的模型。

## Goals / Non-Goals

**Goals:**
- 左键单击托盘图标打开主面板
- 主面板使用 `ttk.Notebook` 整合状态和设置两个选项卡
- 窗口关闭时隐藏而非销毁
- 关闭服务统一走标志文件优雅退出流程
- 用 PIL 绘制有辨识度的图形图标

**Non-Goals:**
- 不引入新的第三方依赖（全部用标准库 + 已有 pystray/PIL）
- 不改动转发脚本 `qq-message-forward.py` 和过滤逻辑
- 不添加开机自启、最小化到托盘动画等高级特性

## Decisions

### 1. 线程模型：`icon.run_detached()` + tk mainloop

`pystray.Icon.run_detached()` 在 daemon 线程中运行托盘事件循环，主线程空闲出来跑 `root.mainloop()`。这样 tkinter 所有操作都在主线程，彻底解决跨线程问题。

**替代方案**：在主线程跑 pystray、用 `threading` 跑 tkinter —— 被否决，因为 tkinter 在主线程外运行在 Windows 上不稳定。

### 2. 左键点击：Win32 窗口消息 hook

pystray 在 Windows 下内部调用 `Shell_NotifyIcon` 并创建隐藏窗口接收 `WM_LBUTTONUP` 等消息。通过 `ctypes.windll.user32.SetWindowLongPtrW(hwnd, GWLP_WNDPROC, new_wndproc)` 替换窗口过程，拦截 `WM_LBUTTONUP` 后通过 `root.after(0, callback)` 切回主线程打开窗口。

**替代方案**：保留右键菜单入口、放弃左键 —— 已在 explore 阶段否决。  
**替代方案**：换用原生 win32api 实现托盘 —— 被否决，工作量太大。

### 3. 窗口生命周期：withdraw/deiconify

主窗口在启动时创建并立即 `withdraw()` 隐藏。左键点击或菜单触发时 `deiconify() + lift()`。点 X 或任务栏关闭时 `protocol('WM_DELETE_WINDOW')` 拦截改为 `withdraw()`。只有"关闭服务"才 `destroy()` 窗口。

这比每次打开都新建 Tk 实例更稳定——避免重复 `mainloop` 或 `Tk` 冲突。

### 4. settings.py 重构为嵌入式 Frame

将 `open_settings()` 拆成 `create_settings_frame(parent, on_save_callback)`，返回 `ttk.Frame` 嵌入 Notebook 的"设置"选项卡。`load_config()` / `save_config()` 保持不变，被 frame 内按钮调用。保存按钮不再弹 messagebox，改为在主窗口状态栏显示结果。

### 5. 关闭服务：标志文件 + 优雅退出

托盘"关闭服务"不再直接 `taskkill`，而是：
1. 创建 `.shutdown.flag` 文件
2. 监控线程（已有的 5 秒轮询）检测到标志后调用 `shutdown_service()`
3. `shutdown_service()` 先 `forward_process.terminate()` + `wait(5)`，再 `taskkill` 残留（llbot.exe、node.exe、QQ.exe、QQNT.exe），最后 `icon.stop()`

**替代方案**：直接调用 `shutdown_service()` 不走标志文件 —— 被否决，因为 stop.vbs 单独运行时无法通知 tray 退出，标志文件是唯一通信通道。保持两边逻辑一致。

## Risks / Trade-offs

- **左键 hook 依赖 pystray 内部实现**：pystray 的隐藏窗口和消息处理是未公开细节，未来版本可能变化。→ 右键菜单保留"打开主面板"作为备用入口。
- **`root.after(0)` 跨线程调用**：win32 窗口过程回调在托盘线程执行，`root.after(0)` 安全地将回调排队到 tkinter 主线程，不涉及线程安全问题。
- **窗口隐藏 vs 销毁**：隐藏窗口仍占用少量内存。→ 对桌面托盘程序来说这是标准做法，内存占用可忽略。
- **32/64 位兼容**：`SetWindowLongPtrW` 在 64 位 Python 下正常工作，`GWLP_WNDPROC` 常量值在 32/64 位下通用。
