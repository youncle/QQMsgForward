## 1. 修复查看状态

- [x] 1.1 将 `tray.py` 中 `show_status_window` 的 PowerShell 弹窗改为 `tkinter.messagebox.showinfo`

## 2. 创建设置窗口

- [x] 2.1 创建 `settings.py`，实现 tkinter 设置窗口 UI（转发规则区、QR 码过滤区、联系方式过滤区）
- [x] 2.2 实现设置窗口读取 config.json 并填充到表单控件
- [x] 2.3 实现"保存"按钮：从表单控件收集值，写入 config.json

## 3. 集成托盘菜单

- [x] 3.1 在 `tray.py` 托盘菜单中增加"打开设置"项，调用 `settings.py` 打开窗口
- [x] 3.2 确保设置窗口在 tkinter 主线程中打开，不阻塞 pystray 事件循环

## 4. 验证

- [x] 4.1 运行 32 个 filter 单元测试确保无回归
- [x] 4.2 语法检查 settings.py + tray.py
