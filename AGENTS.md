# QQMsgForward

基于 **LLOneBot** 的 QQ 群消息实时转发系统。Python 胶水层 + Node.js（LLBot）双运行时。

---

## 🔴 第一行警告：双运行时架构

```
LLBot（Node.js 二进制）← → Python 胶水层（本仓库）
runtime/LLBot-Desktop-win-x64/     src/ + main.py
不可修改、不可 pip install      这是你可以修改的部分
```

- LLBot 是独立的 Node.js 二进制程序，**不是 Python 包**
- `pip install` 不会安装它，`requirements.txt` 不包含它的依赖
- 不要修改 `runtime/` 目录下的任何文件
- 不要尝试用 Python 重新实现 LLBot 的功能

---

## src/ 模块速查表

| 文件 | 职责 | 核心函数 | 可测性 |
|------|------|---------|--------|
| `tray.py` | 系统托盘 + 启动入口。管理 LLBot 进程生命周期、Splash 动画、托盘图标状态 | `main()` | ❌ 依赖 tkinter + Windows API |
| `forward_qq.py` | Flask WebHook 接收 + 消息转发管线。接收→过滤→去重→限流→转发 | `webhook()` `is_duplicate()` `rate_limit()` | ⚠️ 需 Flask 环境 |
| `filter.py` | 三层消息过滤：QR码关键词/图片模式/联系方式正则。纯函数，**最推荐编写测试** | `should_filter()` `check_qrcode_ad()` `check_contact_info()` | ✅ 纯函数 |
| `qr_decoder.py` | pyzbar QR 码图像真解码。含图像下载、解码缓存 | `process_message_images()` | ⚠️ 需图片 |
| `settings.py` | tkinter 配置面板（四标签页：状态/转发/过滤/微信）。含配置读写 | `create_xxx_frame()` | ❌ 依赖 tkinter |
| `wecom.py` | 企微转发（API Webhook + UI 键盘模拟双模式） | `try_forward()` `test_bot()` | ❌ 依赖企微 |
| `wecom_ui.py` | 企微键盘模拟引擎。win32com SendKeys + 剪贴板 | `WeComUIEngine` | ❌ 依赖 Windows |
| `nt_utils.py` | NT 协议文件下载。SQLite 查 fileUuid + ntcall API | `get_file_bytes_via_ntcall()` | ❌ 依赖 LLBot |
| `splash.py` | 启动进度条浮窗。无边框、平滑动画 | `SplashScreen` | ❌ 依赖 tkinter |
| `wizard.py` | 首次运行配置向导。4 步引导创建 config.json | `run_wizard()` | ❌ 依赖 tkinter |

---

## 数据流（完整消息路径）

```
QQ 群消息
   │
   ▼
LLBot（Node.js，端口 3000+N）
   │  POST /webhook（HTTP）
   ▼
forward_qq.py（Flask，端口 9090）
   │
   ├── 1. 过滤非群聊 / 非消息
   ├── 2. 跳过自身消息（sender_qq in robot_qq）
   ├── 3. 匹配 forward_rules（源群 → 目标群列表）
   ├── 4. is_duplicate() 去重（群+内容，可配窗口秒数）
   ├── 5. filter.should_filter() 消息过滤
   │     ├── QR码真解码（pyzbar）
   │     ├── QR码关键词（图片+关键词模式）
   │     └── 联系方式正则（手机/QQ/微信/邮箱）
   ├── 6. 文件消息 → 图片转换（_convert_file_to_image）
   ├── 7. 同步转发企微（try_forward_wecom）
   ├── 8. rate_limit() 限流（可配间隔秒数）
   └── 9. POST /send_group_msg 到目标群
         ├── 优先使用接收消息的机器人
         └── 失败自动轮询其他机器人
```

---

## 配置结构（config.json）

参考 `docs/config_reference.md`，关键要点：

| 字段 | 热重载 | 修改注意 |
|------|--------|---------|
| `robot_qq` | ❌ 需重启 | 决定 LLBot 实例数 |
| `forward_rules` | ✅ | object，key=源群，value={targets, note} |
| `filter.*` | ✅ | 修改后过滤逻辑立即生效 |
| `forward.*` | ✅ | duplicate_window / send_interval |
| `llbot_apis` | ✅ | 启动时自动探测写入 |
| `wecom_*` | ✅ | 企业微信配置 |

**重要**：`forward_qq.py` 和 `settings.py` **各自有独立的 `load_config()` 实现**。修改 config 结构时，必须同时更新两处：

```
forward_qq.py: def load_config() → 读取 CONFIG_PATH
settings.py:  def load_config() → 读取 CONFIG_PATH（同路径）
```

---

## 已有文档索引

| 文档 | 内容 | AI 使用场景 |
|------|------|------------|
| `docs/architecture.md` | 完整架构、启动链路、异常处理 | 修改核心流程前必读 |
| `docs/build.md` | PyInstaller 打包流程 | 打包相关操作时参考 |
| `docs/config_reference.md` | 所有配置字段详解 | 修改配置结构时参考 |
| `docs/troubleshooting.md` | 常见问题排查 | 排查问题时参考 |

---

## 工作流（Feedback 层）

每次修改必须遵守以下步骤：

```
Step 1：三步唤醒
  ├── ① pwd                          — 确认工作目录
  ├── ② git log --oneline -5         — 查看最近变更
  └── ③ cat CLAUDE.md                — 加载决策记忆

Step 2：制定方案
  ├── 给出多个可选方案（含理由和对比）
  ├── 等你选择确认
  └── 方案文档保存到 docs/plans/mmdd-序号-简述.md

Step 3：Safety 自检
  ├── 修改是否触碰 .rules/safety.md 中的红线？
  ├── 如果改了 config 结构 → 同步两处 load_config？
  └── 如果改了 settings.py → 本地运行验证 GUI？

Step 4：遵守 Tool 规范
  └── 代码风格遵守 .rules/coding.md

Step 5：跑 Evaluation
  └── python scripts/verify.py（必须通过）

Step 6：更新 Memory
  └── 重要决策写入 CLAUDE.md

Step 7：Commit
  └── 信息包含：修改了什么 + 为什么 + 影响范围
```

---

## 与 AI 协作的约定

- 在修改代码之前，先展示你的理解让我确认
- 如果某个方案有多个选择，给出选项让我选择
- 修改涉及用户体验（GUI/过滤规则/转发行为）时，先在测试环境验证
- 不确定时，先问，不要猜
