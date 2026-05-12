# 状态日志文件输出 + 滚动交互修复

## 问题

1. 状态日志面板不更新：`forward.py` 的 logging 仅输出到 stderr，PyInstaller 打包时 `console=False` 导致 stderr 为 None，日志全部丢失
2. 日志控件无滚动条，用户无法手动查看历史日志

## 设计

### forward.py — 添加 FileHandler

- 新增 `LOG_PATH` 全局变量
- 新增 `set_log_path(path)` 函数，由 tray.py 启动时调用
- logging 初始化时始终添加 `FileHandler`，无论 stderr 是否可用
- 日志格式：`%(asctime)s - %(levelname)s - %(message)s`
- 文件编码：UTF-8

### tray.py — 传递日志路径 + 滚动条 + 智能滚动

**启动时传递日志路径：**
- 在 `set_forward_config()` 之后调用 `forward_mod.set_log_path(LOG_FILE)`

**日志控件加滚动条：**
- Text 和 Scrollbar 放入 Frame，采用 grid 布局
- Scrollbar 绑定 Text.yscrollcommand

**智能滚动：**
- 刷新日志后，只在用户处于底部时才调用 `see('end')`
- 用户主动上翻查看历史时，不被自动滚动打断
- 判断方式：在 `see('end')` 之前检查 `log_text.yview()[1] >= 1.0`

## 改动文件

| 文件 | 改动 |
|------|------|
| forward.py | ~12 行（新增 `LOG_PATH`、`set_log_path()`、FileHandler） |
| tray.py | ~25 行（传递路径、滚动条、智能滚动逻辑） |

## 验证

- 在 PyInstaller 打包的 exe 中运行，发送群消息后确认 `forward.log` 有新日志行
- 日志面板可鼠标滚轮/拖拽滚动条上下翻看
- 用户在上翻状态时不被自动滚动拉回底部
