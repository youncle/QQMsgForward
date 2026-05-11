## ADDED Requirements

### Requirement: 设置窗口可视化编辑
系统 SHALL 提供 tkinter 设置窗口，用户可通过托盘菜单打开，可视化编辑转发规则和过滤配置。

#### Scenario: 打开设置窗口
- **WHEN** 用户点击托盘菜单中的"打开设置"
- **THEN** 系统弹出 tkinter 设置窗口，展示当前 config.json 中的转发规则、QR 码过滤和联系方式过滤配置

#### Scenario: 修改转发规则
- **WHEN** 用户在设置窗口中修改源群、目标群文本框
- **THEN** 点击保存后 config.json 中的 forward_rules 被更新

#### Scenario: 修改过滤开关
- **WHEN** 用户在设置窗口中勾选/取消 QR 码过滤的启用复选框
- **THEN** 点击保存后 config.json 中的 filter.qrcode.enabled 被更新

#### Scenario: 修改纯图片拦截
- **WHEN** 用户在设置窗口中勾选/取消"拦截无文字的纯图片"
- **THEN** 点击保存后 config.json 中的 filter.qrcode.block_pure_image 被更新

#### Scenario: 保存配置
- **WHEN** 用户点击"保存"按钮
- **THEN** 系统将当前设置窗口中的值写入 config.json，弹窗提示"配置已保存，重启服务后生效"
