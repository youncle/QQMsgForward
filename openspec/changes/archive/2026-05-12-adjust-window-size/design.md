## Context

当前主面板窗口初始尺寸为 `520x500`，包含双选项卡（状态 + 设置）和底部按钮栏，内容拥挤。窗口 resize 后不保存尺寸，每次重新打开或重启程序后恢复默认大小。

## Goals / Non-Goals

**Goals:**
- 默认窗口尺寸从 520x500 增大到 900x650，内容有足够空间
- 用户手动调整窗口大小后自动保存，下次启动恢复保存的尺寸
- 稳定、无副作用，不影响现有功能

**Non-Goals:**
- 不保存窗口位置（仅尺寸），避免多显示器场景的问题
- 不改变现有布局结构
- 不涉及窗口状态其他属性（最大化、最小化）

## Decisions

### 决策 1：存储格式 — 独立 JSON 文件

选择：`tray.py` 同级创建 `.window_state.json`，仅保存 `geometry` 字符串。

```json
{"geometry": "900x650"}
```

`geometry` 直接使用 tkinter `winfo_geometry()` 输出格式（`宽x高`），兼容 `root.geometry(geometry)` 直接设置。

### 决策 2：保存时机 — `<Configure>` 事件 + debounce

绑定根窗口的 `<Configure>` 事件，窗口尺寸变化时通过 `root.after()` 延迟 500ms 写入文件。500ms 内连续 resize 会重置定时器，避免高频磁盘写入。

### 决策 3：读取时机 — 窗口创建后、首次显示前

```
root.withdraw()
  ↓
saved = load_window_geometry()  ← 尝试读取
  ↓
root.geometry(saved or '900x650')
  ↓
root.deiconify()                ← 显示窗口
```

## Risks / Trade-offs

- [风险] JSON 写入失败 → 静默忽略，下次启动使用默认尺寸
- [风险] 窗口最小化时触发 `<Configure>` → 过滤 `wm_state() == 'iconic'`，不保存
- [风险] 文件损坏 → `json.JSONDecodeError` 静默忽略，回退默认值
