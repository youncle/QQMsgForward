## Why

主面板初始窗口尺寸 520x500 偏小，内容（双选项卡 + 底部按钮栏）显得拥挤。用户调整窗口后，再次打开时尺寸被重置，每次都要重新拖拽。

## What Changes

- 默认窗口尺寸从 `520x500` 调整为 `900x650`
- 新增窗口尺寸持久化机制：用户 resize 后自动保存，下次启动恢复

## Capabilities

### Modified Capabilities

- `tray-main-panel`: 修改窗口默认尺寸；新增窗口尺寸自动保存与恢复

## Impact

- `tray.py`：修改 `root.geometry()`、新增 `.window_state.json` 读写、绑定 `<Configure>` 事件 + debounce 保存
