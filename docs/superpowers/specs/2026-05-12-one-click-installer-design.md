# 一键安装包 — 设计文档

## 目标

为纯小白用户提供绿色免安装、双击即用的 QQ 消息转发工具安装包。

## 整体架构

自解压包解开后的目录结构：

```
QQForward/
├── QQForward.exe          ← PyInstaller 打包的主程序（tray.py 入口）
├── LLBot-CLI-Win-x64/     ← LLBot Node.js 组件（原样复制）
│   └── llbot.exe
├── config.json            ← 用户配置（首次运行自动生成）
└── config.example.json    ← 配置模板参考
```

- `tray.py` / `qq-message-forward.py` / `filter.py` / `settings.py` 全部打包进 `QQForward.exe`
- `config.json` 外置，方便后续升级保留配置
- `LLBot-CLI-Win-x64/` 保持外置目录，PyInstaller 按相对路径查找

## 启动流程

```
用户双击 QQForward.exe
  → 检查 LLBot-CLI-Win-x64/llbot.exe 存在？
      └── 不存在 → 弹框报错退出
  → 检查 config.json 存在且有效？
      ├── 不存在 → 弹出 GUI 配置向导
      └── 损坏 → 询问是否重建
  → 检查端口 3000/8080 是否占用？
      └── 占用 → kill 旧进程 → 仍占用 → 报错退出
  → 启动 llbot.exe（后台，隐藏窗口）
  → 等待端口 3000 就绪（最多 20 秒，超时报错）
  → 启动 Flask 转发服务（端口 8080）
  → 显示托盘图标
```

托盘图标状态：绿色=运行中，黄色=启动中，红色=异常。

## GUI 配置向导

首次运行时未检测到 `config.json` 则自动弹出。用 ttk（tkinter）实现，单窗口多页切换（`tkraise()`），固定 480×400，居中显示。

### 页面流程

**第 1 页：欢迎页**
- 标题："欢迎使用 QQ消息转发"
- [下一步] 按钮

**第 2 页：QQ 号**
- 输入框：机器人 QQ 号（数字验证，必填）
- [上一步] [下一步]，必填为空时"下一步"禁用

**第 3 页：转发规则**
- 源群 QQ 号输入框 + 目标群输入框 + [添加] 按钮
- 已添加规则列表（可选中删除）
- 可选步骤，允许跳过
- [上一步] [下一步]

**第 4 页：过滤设置**
- 单选：○ 开启（推荐）— 自动过滤二维码、联系方式
- 单选：○ 暂时关闭 — 所有消息都转发
- [上一步] [完成]

点击"完成"→ 按默认模板写入 `config.json`，然后自动进入托盘模式。

### 默认值内置

PyInstaller 打包时内置以下默认值（不暴露给用户）：

- `llbot_api`: `http://127.0.0.1:3000`
- `llbot_token`: `""`
- `forward.duplicate_window`: 5
- `forward.send_interval`: 1.0
- `filter.qrcode.enabled`: true
- `filter.qrcode.mode`: `image_with_keyword`
- `filter.qrcode.block_pure_image`: true
- `filter.contact.enabled`: true
- `filter.log_only`: false
- Webhook 地址: `http://127.0.0.1:8080/webhook`（Flask 内部硬编码）
- LLBot 已默认配置向 8080/webhook 上报消息

## 自解压包制作

- **工具**: 7-Zip SFX（开源 LGPL，无授权问题）
- **压缩算法**: LZMA2
- **图标**: 注入 `app.ico`

### 构建脚本（build.bat）

```
[1/5] 清理旧构建产物（build/, dist/, output/）
[2/5] PyInstaller 打包 QQForward.exe
      pyinstaller --onefile --windowed --icon=app.ico tray.py
[3/5] 准备打包目录
      复制 dist/QQForward.exe, LLBot-CLI-Win-x64/, config.example.json → output/QQForward/
[4/5] 7-Zip SFX 打包
      7z a -sfx -mmt 存档.7z output/QQForward/*
      注入图标（Resource Hacker）
[5/5] 输出: QQForward_Setup.exe
```

构建依赖（仅开发机）：Python、PyInstaller、7-Zip 命令行版。

## 错误处理

| 场景 | 行为 |
|------|------|
| `LLBot-CLI-Win-x64/` 目录不存在 | 弹框提示"安装不完整，缺少 LLBot 组件"，退出 |
| 端口 3000/8080 被占用 | 弹框提示"端口被占用，请关闭其他程序后重试" |
| `config.json` 损坏 | 弹框提示"配置文件损坏，是否重新配置？"→ 是→ 打开向导 |
| llbot.exe 启动超时 | 弹框提示"LLBot 启动超时"，退出 |

## 测试要点

- 自解压包在干净 Windows 系统（无 Python）上解压后能正常运行
- 首次运行弹出向导，填写后能正常启动并转发消息
- 再次运行时跳过向导，直接启动
- 端口占用时正确处理
- 托盘图标各状态正常显示

## 不做

- 开机自启（用户选择不需要）
- 在线自动更新
- 安装版（NSIS/Inno Setup）
- LLBot WebUI 的自动配置
