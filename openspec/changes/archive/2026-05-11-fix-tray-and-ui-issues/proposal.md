## Why

用户反馈三个问题：托盘左键点击打不开主面板（spec 已要求但实现有 bug）、Tab 标题头过窄影响操作体验、状态标签页日志显示乱码（子进程编码与日志文件编码不一致）。这三个问题直接影响日常使用，需要修复。

## What Changes

- 修复托盘图标左键点击无法打开主面板的 bug（窗口子类化 hook 失败）
- 加宽主面板 Notebook Tab 标题头的内边距，改善视觉和点击体验
- 修复子进程日志编码问题：统一使用 UTF-8 输出，消除中文和 emoji 乱码

## Capabilities

### Modified Capabilities

- `tray-main-panel`: 修复左键点击托盘图标打开主面板的行为、改善 Tab 标题头宽度、修复状态日志显示乱码

## Impact

- `tray.py` — `_find_tray_hwnd()` 窗口查找逻辑、`_hook_left_click()` hook 机制、Notebook 样式、日志文件读写编码
- `qq-message-forward.py` — 子进程 stdout/stderr 编码设置
