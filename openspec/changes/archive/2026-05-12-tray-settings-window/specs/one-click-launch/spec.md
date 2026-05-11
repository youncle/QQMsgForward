## MODIFIED Requirements

### Requirement: 系统托盘图标常驻
托盘程序 SHALL 在系统通知区域显示图标，提供运行状态指示、设置入口和关闭入口。

#### Scenario: 托盘图标显示
- **WHEN** LLBot 和转发服务均已启动
- **THEN** 系统托盘显示绿色图标，提示"QQ消息转发 - 运行中"

#### Scenario: 托盘右键菜单
- **WHEN** 用户右键托盘图标
- **THEN** 显示上下文菜单，包含"打开设置"、"查看状态"和"关闭服务"三个选项

#### Scenario: 打开设置
- **WHEN** 用户点击托盘菜单中的"打开设置"
- **THEN** 弹出 tkinter 设置窗口，展示当前配置

#### Scenario: 查看状态
- **WHEN** 用户点击托盘菜单中的"查看状态"
- **THEN** 弹出 tkinter 消息框显示 LLBot 运行状态、转发脚本运行状态

#### Scenario: 通过托盘关闭服务
- **WHEN** 用户点击托盘菜单中的"关闭服务"
- **THEN** 系统终止 LLBot 和转发脚本进程并移除托盘图标

#### Scenario: 服务异常检测
- **WHEN** LLBot 或转发脚本意外退出
- **THEN** 托盘图标变为红色，提示"服务异常"，并弹窗通知用户
