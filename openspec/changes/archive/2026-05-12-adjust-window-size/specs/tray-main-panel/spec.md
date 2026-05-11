## ADDED Requirements

### Requirement: 窗口初始尺寸
主面板窗口 SHALL 默认尺寸为 900x650 像素，内容区域有充足空间容纳选项卡和底部按钮栏。

#### Scenario: 默认尺寸
- **WHEN** 首次启动程序，无已保存的窗口状态
- **THEN** 窗口尺寸为 900x650

### Requirement: 窗口尺寸持久化
用户调整窗口大小后，系统 SHALL 自动保存尺寸并在下次启动时恢复。

#### Scenario: 自动保存尺寸
- **WHEN** 用户拖动窗口边框调整大小
- **THEN** 系统在 resize 结束后将新尺寸写入 `.window_state.json`

#### Scenario: 启动恢复尺寸
- **WHEN** 程序启动且 `.window_state.json` 存在有效尺寸
- **THEN** 窗口使用保存的尺寸，而非默认值 900x650

#### Scenario: 最小化不保存
- **WHEN** 窗口最小化到任务栏
- **THEN** 系统不保存当前尺寸到 `.window_state.json`

#### Scenario: 文件损坏回退
- **WHEN** `.window_state.json` 不存在或内容损坏
- **THEN** 系统静默忽略，使用默认尺寸 900x650
