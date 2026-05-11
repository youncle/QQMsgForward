## Context

当前系统有三个已发现的 bug/问题：

1. **托盘左键点击无效**：现有实现通过 Win32 窗口子类化（`_hook_left_click`）拦截 `WM_LBUTTONUP` 来触发主面板显示。但 pystray 的内部机制是：托盘图标交互 → Windows 发 `WM_NOTIFY`（`WM_USER + 11`）到隐藏窗口 → `_on_notify` 检查 `lparam == WM_LBUTTONUP` → 调用 `self()`（即 `Icon.__call__`）→ 执行 `default=True` 的菜单项。当前 hook 拦截的是 `WM_LBUTTONUP` 消息体本身，而非包含它的 `WM_NOTIFY`，因此永远不会触发。另外，两个菜单项都没有设 `default=True`，导致 pystray 自身的左键逻辑也不生效。

2. **Tab 标题过窄**：`ttk.Notebook` 默认 tab 宽度由文字长度决定，"状态"/"设置"仅两个汉字，视觉上太窄，不易点选。

3. **日志乱码**：子进程 `qq-message-forward.py` 的 `logging.basicConfig()` 默认写入 `sys.stderr`，Windows 上 `sys.stderr.encoding` 为 `cp936`。但日志文件以 UTF-8 打开写入。cp936 编码的字节流写入 UTF-8 文件后，中文和 emoji（✅❌）解码异常。Python 3.14 虽然默认 UTF-8，但 subprocess 继承的是当前进程环境，若未设 `PYTHONUTF8=1`，子进程仍用系统 ANSI 编码。

## Goals / Non-Goals

**Goals:**
- 左键点击托盘图标能可靠打开主面板
- Tab 标题头有足够宽度，视觉舒适、容易点击
- 日志在状态标签页正确显示中文和 emoji

**Non-Goals:**
- 不改变托盘右键菜单的行为
- 不引入新的日志存储方式（仍用文件）
- 不改变设置的任何功能

## Decisions

### 决策 1：左键点击修复方案 — 使用 pystray 内置 default action 替代窗口子类化

**选择**：给"打开主面板"菜单项添加 `default=True`，移除 `_hook_left_click` 及 `_find_tray_hwnd` 整套窗口子类化代码。

**备选方案**：
- A. 修复 hook：改拦截 `WM_NOTIFY` + 检查 `lparam`。但依赖 pystray 内部实现细节（window class name 格式、WM_NOTIFY 常量值），版本升级可能失效。
- B. 删除 hook，用 `default=True`：依赖 pystray 公开 API（`MenuItem.default`），跨版本稳定，代码量更少。

**选择 B**。`pystray.Icon.HAS_DEFAULT_ACTION = True` 是公开接口，`MenuItem.default` 是文档化的属性。比维护一个脆弱的 ctypes hook 更合理。

### 决策 2：Tab 宽度 — ttk.Style 配置

**选择**：创建自定义 `ttk.Style`，为 `TNotebook.Tab` 添加 `padding`。

```python
style = ttk.Style()
style.configure('TNotebook.Tab', padding=(20, 5))
```

简单直接，无需改布局结构。

### 决策 3：日志编码 — PYTHONUTF8 + FileHandler

**选择**：双重保障：
1. `tray.py` 的 `subprocess.Popen` 传入 `env` 包含 `PYTHONUTF8=1`，强制子进程 Python 用 UTF-8 模式
2. `qq-message-forward.py` 尽早调用 `sys.stderr.reconfigure(encoding='utf-8')`，确保 logging 输出 UTF-8

**备选方案**：
- A. `subprocess.Popen` 的 `encoding='utf-8'` 参数（text=True）：让 subprocess 以文本模式读取，但需要额外线程将文本再写入日志文件，复杂。
- B. 仅在子进程加 FileHandler：能解决日志文件编码，但其他 stderr 输出仍有编码问题。

**选择双重保障**，两者互补，且都不依赖 deprecated API。

## Risks / Trade-offs

- 移除窗口子类化后，托盘左键只能触发 default action（即打开主面板），无法自定义其他左键行为。当前需求就是打开主面板，无影响。未来如需自定义，可重新评估。
- `PYTHONUTF8=1` 在 Python 3.7+ 有效。当前 Python 3.14，完全支持。
- Tab padding 值是主观选择，可能需要微调。
