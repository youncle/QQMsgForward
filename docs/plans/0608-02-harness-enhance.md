---
title: "Harness 持续完善 — Hooks 增强 + JSON 锁扩展"
date: 2026-06-08
status: "pending_review"
---

# Harness 持续完善

## 当前状态回顾

已完成的 P0：
- ✅ 三步唤醒（AGENTS.md 工作流 Step 1）
- ✅ pre-commit hook（Safety 检查 + verify 自动运行）
- ✅ filter JSON 锁（5 条测试用例）
- ✅ 沙盒隔离（verify diff 红线检查）
- ✅ 记忆健康检查（verify 行数监控 + 压缩脚本）

## 下一步完善项

### P0：pre-commit 增强 — 考前不偷卷

**问题**：AI 可以修改自己的验收标准（JSON 锁），让测试永远通过。

**文章解法**：beforeFileWrite 钩子禁止修改测试/评估文件。

**我们的实现**：在 pre-commit 中增加规则：

```
禁止修改 .rules/verify/ 目录下的文件
  └── 防止 AI 篡改验收标准
  └── 违反直接阻断
```

涉及：`.githooks/pre-commit` 新增 1 条 case

---

### P0：进度追踪 JSON

**问题**：当前没有结构化的方式追踪项目里程碑完成状态。

**文章解法**：JSON 格式的功能清单，由框架管理，AI 只能标 passing/failing。

**我们的实现**：

```json
{
  "schema": "1.0",
  "updated_at": "2026-06-08",
  "milestones": [
    {
      "id": "harness-p0",
      "title": "Harness P0：约定级",
      "status": "completed",
      "completed_at": "2026-06-08"
    },
    {
      "id": "harness-p1",
      "title": "Harness P1：可执行级",
      "status": "completed",
      "completed_at": "2026-06-08"
    },
    {
      "id": "xxx",
      "title": "待定",
      "status": "pending"
    }
  ]
}
```

路径：`.rules/verify/progress.json`

用途：
- verify.py 新增检查：读取 progress.json，验证状态一致性
- pre-commit 检查：禁止 AI 自行将 pending 改为 completed
- 每次 milestone 完成时人工更新

---

### P1：qr_decoder JSON 锁

**问题**：filter.py 已有验收标准，但 qr_decoder.py（二维码解码模块）没有。

**文章解法**：每个关键模块对应一份验收 JSON。

**我们的实现**：`.rules/verify/qr-decoder-acceptance.json`

测试用例：
- 图片 URL 下载失败时优雅降级
- 解码缓存命中/未命中行为
- 解码超时处理
- 无可解码内容时返回空

---

### P1：afterCommit 自动触发记忆压缩

**问题**：CLAUDE.md 行数检查只报警，不自动处理。

**文章解法**：onSessionEnd / afterCommit 钩子自动维护记忆。

**我们的实现**：在 pre-commit hook 末尾增加：

```bash
# 如果 CLAUDE.md 超过 150 行，自动压缩
if [ $(wc -l < "$ROOT/CLAUDE.md") -gt 150 ]; then
    python "$ROOT/scripts/compress-memory.py"
fi
```

---

## 实施顺序

```
Step 1：pre-commit 增强（禁改 verify 文件）
Step 2：progress.json 进度追踪
Step 3：qr_decoder JSON 锁
Step 4：afterCommit 自动记忆压缩
```

请审核。
