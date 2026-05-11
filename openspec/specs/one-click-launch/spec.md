## ADDED Requirements

### Requirement: 一键启动服务
用户双击 `start.vbs` 文件时，系统 SHALL 自动获取管理员权限并静默启动 LLBot 和转发服务，无需其他操作。

#### Scenario: 正常启动
- **WHEN** 用户双击 `start.vbs`
- **THEN** 系统弹出 UAC 确认框，用户确认后 LLBot 和转发脚本在后台启动，弹窗提示"服务已启动"

#### Scenario: Python 未安装
- **WHEN** 用户双击 `start.vbs` 且系统未安装 Python
- **THEN** 系统弹窗提示"未找到 Python，请先安装 Python 并添加到 PATH"

#### Scenario: 端口被占用
- **WHEN** 3000 端口已被其他进程占用
- **THEN** 系统弹窗提示"端口 3000 已被占用，请先关闭占用程序"

### Requirement: 一键关闭服务
用户双击 `stop.vbs` 文件时，系统 SHALL 自动获取管理员权限并强制终止 LLBot、转发脚本和托盘程序的所有相关进程。

#### Scenario: 正常关闭
- **WHEN** 用户双击 `stop.vbs`
- **THEN** 系统终止 llbot.exe、python.exe（转发脚本）、pythonw.exe（托盘程序）进程，弹窗提示"服务已关闭"

#### Scenario: 服务已在运行中（重复启动）
- **WHEN** 用户再次双击 `start.vbs` 且服务已在运行
- **THEN** 系统检测到端口已占用，弹窗提示"服务已在运行中"，不重复启动

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
