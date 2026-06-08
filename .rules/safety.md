# 安全规则

## 级别 1：禁止修改 ❌

以下内容在任何情况下都不应修改（除非经架构评审+用户明确批准）：

| 路径 | 原因 |
|------|------|
| `runtime/LLBot-CLI-Win-x64/` | Node.js 第三方二进制，修改会导致 LLBot 不可用 |
| `config/config.json` | 用户产品配置，AI 修改可能破坏热重载或丢失用户数据 |
| `.shutdown.flag` | 优雅关闭协议信号文件，格式和时机不可变更 |
| `main.py` | 项目入口，修改可能破坏打包或启动链路 |
| `requirements.txt` 版本号 | 依赖版本经过验证，修改前需确认兼容性 |

## 级别 2：修改需谨慎 ⚠️

以下操作允许，但必须先确认后再执行：

| 操作 | 风险 | 必须确认的内容 |
|------|------|---------------|
| 新增/删除 config 字段 | 热重载断裂 | `forward_qq.py` 和 `settings.py` 两处 load_config 是否同步更新？|
| 修改 settings.py GUI | tkinter 布局崩溃 | 修改后是否在本地运行验证所有标签页正常？|
| 修改 filter.py 逻辑 | 误拦/漏放消息 | 是否用真实消息格式（array+CQ 码两种）测试过？|
| 修改 wecom_ui.py 延迟参数 | 微信安全风控 | 延迟是否合理范围（建议 0.03-0.15s）？|
| 修改 scripts/ 下的构建脚本 | 构建失败 | 是否运行 `build.bat` 验证过？|
| 新增第三方包 | 打包体积膨胀/兼容冲突 | 是否在 `requirements.txt` 同步添加？|

## 级别 3：修改后必须验证 ✅

以下操作修改后必须运行验证脚本：

| 文件 | 验证方式 |
|------|---------|
| `filter.py` | `python scripts/verify.py`（导入检查+逻辑测试）|
| `forward_qq.py` | `python scripts/verify.py`（导入检查）|
| `qr_decoder.py` | `python scripts/verify.py`（导入检查）|
| `.rules/*` | 检查格式正确性 |
| `AGENTS.md` | 建议用 markdown lint 检查 |

## 违规处理

- 触碰 Level 1 → 回退变更，重新评估
- 触碰 Level 2 未经确认 → 暂停修改，补充确认
- Level 3 未验证 → 补跑验证，通过后方可继续
