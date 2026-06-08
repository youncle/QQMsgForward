# 技术决策日志

记录所有重要的技术决策、架构选择和踩坑记录。

---

## 格式

每次重大修改时追加一条：

```markdown
### YYYY-MM-DD：标题

**背景**：为什么需要这个修改

**决策**：做了什么、怎么做的

**影响范围**：改了哪些文件、影响了什么行为

**踩坑记录**：过程中遇到的问题和解决方式
```

---

## 初始记录

### 2026-06-08：双运行时架构确认

**背景**：项目使用 Python + Node.js 双运行时，AI 容易混淆。

**决策**：
- Python 部分（src/ + main.py）是主要的开发对象
- Node.js 部分（runtime/LLBot-CLI-Win-x64/）是第三方二进制，不可修改
- LLBot 的配置通过 `config.json` 间接控制，不直接操作 runtime 目录

**影响范围**：AGENTS.md 中标注双运行时警告。.rules/safety.md Level 1 禁止修改 runtime/。

---

### 2026-06-08：config 热重载机制确认

**背景**：配置系统设计为热重载，但 `forward_qq.py` 和 `settings.py` 分别有自己的 `load_config()` 实现。

**决策**：两套独立的 `load_config()` 从同一文件读取，必须保持同步。修改配置结构时两处同时更新。

**影响范围**：所有涉及 config 字段增减的修改。.rules/safety.md Level 2 标注为谨慎操作。

---

### 2026-06-08：企微 UI 键盘模拟延迟策略

**背景**：企微 UI 模式使用 win32com SendKeys 模拟键盘输入，速度过快会被微信安全机制检测。

**决策**：
- 每次按键间随机延迟 0.03-0.15 秒
- 不使用固定延迟，避免被模式识别
- 不减少延迟，安全优先

**影响范围**：`wecom_ui.py` 中的 `send_keys()` 函数。

---

### 2026-06-08：优雅关闭协议

**背景**：需要在不强制终止进程的情况下安全关闭服务。

**决策**：
- `stop.vbs` 创建 `.shutdown.flag`
- `tray.py` 每秒轮询检测 flag 文件
- 检测到后按序：倒计时 → 清理 LLBot 进程 → 删除 flag → 退出
- `stop.vbs` 15 秒超时检测，flag 未删除则强制 taskkill

**影响范围**：`tray.py`（轮询 + 清理）、`scripts/stop.vbs`（创建 flag + 超时检测）。

---

### 2026-06-08：项目 Harness 工程化

**背景**：为 QQMsgForward 项目建立 AI Agent 开发 Harness，确保 AI 在此仓库上工作时更可靠。

**决策**：按照标准 Harness Engineering 六层架构，创建 5 份文件：
- `AGENTS.md`（Context + Feedback）
- `.rules/coding.md`（Tool）
- `.rules/safety.md`（Safety）
- `CLAUDE.md`（Memory）
- `scripts/verify.py`（Evaluation）

**影响范围**：新增文件，不修改现有代码。
