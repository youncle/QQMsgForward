## 1. 托盘左键修复

- [x] 1.1 给"打开主面板"菜单项添加 `default=True`，启用 pystray 内置左键 default action
- [x] 1.2 移除 `_hook_left_click` 和 `_find_tray_hwnd` 函数及相关的 Win32 窗口子类化代码（`GWLP_WNDPROC`、`WM_LBUTTONUP`、`_original_wndproc`、`_wndproc_ref`、`_hook_root`、`_hook_callback`、`WNDPROC_TYPE` 等全局变量）
- [x] 1.3 移除 `setup_tray` 中的 `root.after(500, lambda: _hook_left_click(root, on_open))` 调用

## 2. Tab 标题宽度

- [x] 2.1 在 `tray.py` 主窗口创建处配置 `ttk.Style`，为 `TNotebook.Tab` 添加水平内边距（如 `padding=(20, 5)`）

## 3. 日志编码修复

- [x] 3.1 在 `tray.py` 的 `subprocess.Popen` 调用中传入 `PYTHONUTF8=1` 环境变量
- [x] 3.2 在 `qq-message-forward.py` 中尽早调用 `sys.stderr.reconfigure(encoding='utf-8')`，确保 logging 模块输出 UTF-8
