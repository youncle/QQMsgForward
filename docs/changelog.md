# 变更日志

## [1.1.0] - 2026-06-03

### Added
- 企业微信 UI 模式：键盘模拟、剪贴板粘贴、随机延迟防风控
- 图片文件类型自动识别与转换（type=file → type=image）
- 基于 ntcall API 的文件下载引擎
- 模拟打字功能（send_keys 随机延迟 0.03-0.15s）

### Fixed
- 数据库文件冲突解决
- 中文输入改用剪贴板修复编码问题
- 清空 _send_text 残留旧代码导致的空白消息
- 微信前端窗口无法激活的问题
- 消息发送 2 遍的重复问题

### Changed
- 企微转发通道从 API 单模式升级为 API/UI 双模式
- URL 发送 → 键盘操作的全面迁移
- 时序随机化策略优化
- 相关文档整理

## [1.0.0] - 2026-06-01

### Added
- 企业微信转发通道（QQ 群→企业微信）
- API 模式 + UI 开关面板（Webhook Key 发送）
- 状态标签页显示企业微信在线状态
- 系统托盘窗口重构（状态/转发/过滤/微信 四标签页）
- 基础 Harness：AGENTS.md + .rules/ + CLAUDE.md

### Fixed
- 配置保存逻辑：原子写入（tmp + os.replace）
- 窗口位置多显示器越界检测
- 状态页滚动条与自动滚动

### Changed
- LLBot 升级至最新版本
- 配置系统重构：热重载支持所有字段（除 robot_qq）
- 日志系统：按天轮转保留 2 份、UTF-8 编码修复
- tray 退出流程统一为 flag 文件 + 优雅关闭

## [0.9.0] - 2026-05-31

### Added
- 首次运行配置向导（4 步引导）
- QR 码真解码模块（pyzbar）
- 三层消息过滤模式（image_with_keyword / block_pure_image / block_all_images）
- QQ 群号白名单豁免
- 转发规则备注功能
- 消息去重 + 限流 + 固定 1 秒延迟

### Fixed
- PyInstaller 打包兼容性（hidden-import）
- 7-Zip SFX 构建流程
- 过滤器 CQ 码正则解析修复
- 前端窗口 UI 布局（标签页间距/列表宽度/最小窗口锁定）

### Changed
- 项目结构重构：提取 src/ 目录，分离 tray / forward / filter / settings
- 构建流程：一键 build.bat + 自动图标生成
- 配置迁移：旧格式自动升级（int→数组、list→dict）

## [0.8.0] - 2026-05-11

### Added
- 初始版本：基于 LLOneBot 的 QQ 群消息转发
- 多 QQ 号并行监听（端口自增 3000+N）
- 智能消息路由（优先同机器人转发）
- 启动动态端口探测
- 基础消息过滤（二维码关键词 + 联系方式正则）
- 系统托盘（左侧 3 色状态图标）
- PyInstaller 单文件打包
- 自动创建桌面快捷方式
- 优雅关闭（.shutdown.flag 协议）
