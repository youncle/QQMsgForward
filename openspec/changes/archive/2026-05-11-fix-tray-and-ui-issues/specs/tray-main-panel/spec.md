## ADDED Requirements

### Requirement: Tab 标签页标题宽度
主面板的 Notebook Tab 标签页标题 SHALL 具有足够的内边距，确保中文标题视觉舒适且易于点击。

#### Scenario: Tab 标题显示
- **WHEN** 主面板窗口显示
- **THEN** "状态"和"设置"两个 Tab 标签页标题左右内边距不少于 15 像素

### Requirement: 状态日志正确编码
状态标签页中的日志显示 SHALL 正确处理 UTF-8 编码，中文和 emoji 符号无乱码。

#### Scenario: 日志中文显示
- **WHEN** 子进程输出包含中文字符的日志
- **THEN** 状态标签页日志区域正确显示中文，无乱码或替换字符

#### Scenario: 日志 emoji 显示
- **WHEN** 子进程输出包含 emoji 符号（如 ✅、❌）的日志
- **THEN** 状态标签页日志区域正确显示 emoji 符号，无乱码或替换字符

## MODIFIED Requirements

### Requirement: 选项卡主面板窗口
系统 SHALL 提供含"状态"和"设置"两个选项卡的主面板窗口，左键单击托盘图标或右键菜单"打开主面板"均可打开。

#### Scenario: 左键单击打开主面板
- **WHEN** 用户在托盘图标上左键单击
- **THEN** 系统通过 pystray 内置的 default action 机制（而非 Win32 窗口子类化）显示主面板窗口，窗口置顶并获取焦点；如窗口已打开但隐藏，则恢复显示

#### Scenario: 右键菜单打开主面板
- **WHEN** 用户点击托盘右键菜单中的"打开主面板"
- **THEN** 系统显示主面板窗口，窗口置顶并获取焦点

#### Scenario: 状态选项卡
- **WHEN** 用户切换到状态选项卡
- **THEN** 系统显示 LLBot（端口 3000）运行状态、转发脚本（端口 8080）运行状态，使用绿色/红色指示点标识

#### Scenario: 设置选项卡
- **WHEN** 用户切换到设置选项卡
- **THEN** 系统显示转发规则管理界面、QR码过滤配置、联系方式过滤配置，与现有设置窗口功能一致
