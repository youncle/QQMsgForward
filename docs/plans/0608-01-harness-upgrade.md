---
title: "Harness 升级：从约定级到可执行级"
date: 2026-06-08
status: "pending_review"
---

# Harness 升级路线

## 目标

将 QQMsgForward 的 Harness 从「约定文件级」升级到「可执行代码级」。

---

## Step 1：三步唤醒仪式（改 AGENTS.md）

**问题**：工作流 Step 1 只写了「读 Context」，AI 可能跳步、漏步、只读一半。

**改法**：用三条具体命令替换抽象描述：

```diff
- Step 1：读 Context
-   ├── 读 AGENTS.md（全景认知）
-   ├── 读目标模块代码（理解现有逻辑）
-   └── 读 docs/architecture.md（如涉及核心流程）

+ Step 1：三步唤醒
+   ├── ① pwd                      — 确认工作目录
+   ├── ② git log --oneline -5     — 查看最近变更
+   └── ③ cat CLAUDE.md            — 加载决策记忆
```

**涉及文件**：`AGENTS.md` 工作流章节，1 处替换

**验证方式**：人工检查工作流段落输出正确

---

## Step 2：Hooks 钩子（pre-commit 自动拦截）

### 2.1 新建 .githooks/pre-commit

路径：`QQMsgForward/.githooks/pre-commit`

内容（PowerShell 脚本，Windows 兼容）：

```powershell
# .githooks/pre-commit — QQMsgForward Harness 提交前检查
# 返回 0=通过，非0=阻断

$ErrorActionPreference = "Continue"

# 找项目根目录（hooks 所在目录的上一级）
$root = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$verify = Join-Path $root "scripts" "verify.py"

# 检查 verify.py 是否存在
if (-not (Test-Path $verify)) {
    Write-Host "⚠️  scripts/verify.py 不存在，跳过 Harness 检查"
    exit 0
}

# 运行验证
Write-Host "🧪 Running Harness verification..."
python $verify
$exitCode = $LASTEXITCODE

if ($exitCode -eq 0) {
    Write-Host "✅ Harness verification passed"
    exit 0
} elseif ($exitCode -eq 1) {
    Write-Host "⚠️  Harness verification has warnings"
    Write-Host "   To bypass: git commit --no-verify"
    exit 1  # 有警告也阻断，强制处理
} else {
    Write-Host "❌ Harness verification failed"
    Write-Host "   Fix errors first, or bypass with: git commit --no-verify"
    exit 1
}
```

### 2.2 新增 Safety diff 检查（内嵌在 pre-commit 中）

在 pre-commit 中，除了跑 verify.py，还要做 Safety 红线检查：

```powershell
# pre-commit 内嵌 Safety 检查
$safetyFile = Join-Path $root ".rules" "safety.md"
$gitDiff = git diff --cached --name-only

if ($gitDiff -match "runtime/") {
    Write-Host "❌ BLOCKED: 修改了 runtime/ 目录（Safety Level 1 红线）"
    exit 1
}
if ($gitDiff -match "config/config\.json") {
    Write-Host "❌ BLOCKED: 修改了 config/config.json（Safety Level 1 红线）"
    exit 1
}
if ($gitDiff -match "main\.py") {
    Write-Host "❌ BLOCKED: 修改了 main.py（Safety Level 1 红线）"
    exit 1
}
```

### 2.3 新建 scripts/install-hooks.bat

路径：`QQMsgForward/scripts/install-hooks.bat`

内容：

```bat
@echo off
chcp 65001 >nul
title QQMsgForward — 安装 Git Hooks

:: 设置 Git hooks 路径为项目内的 .githooks 目录
git config core.hooksPath .githooks

echo ✅ Git hooks 已安装
echo    hooks 路径: .githooks/
echo    下次 git commit 自动触发 Harness 验证
pause
```

### 2.4 更新 .gitignore

新增一行：

```
# Git hooks 安装记录（供参考）
.githooks/
```

（实际上 `.githooks/` 需要被 Git 跟踪，不加这行，确保它被提交）

### 涉及文件

| 文件 | 操作 |
|------|------|
| `.githooks/pre-commit` | 新建（PowerShell 脚本）|
| `scripts/install-hooks.bat` | 新建（Windows 批处理）|

### 验证方式

```bash
# 1. 安装 hooks
scripts\install-hooks.bat

# 2. 验证 hooks 路径
git config core.hooksPath
# → 输出：.githooks

# 3. 触发一次 commit 验证 hook 生效
# （故意引入一个错误，看是否阻断）
```

---

## Step 3：JSON 物理锁（filter 验收标准）

### 3.1 新建 .rules/verify/filter-acceptance.json

路径：`QQMsgForward/.rules/verify/filter-acceptance.json`

内容：

```json
{
  "schema_version": "1.0",
  "target_module": "filter.py",
  "description": "filter 模块的验收标准，任何修改必须通过以下所有测试用例",
  "created_at": "2026-06-08",
  "test_cases": [
    {
      "id": "TC-001",
      "description": "无图片的普通文本消息不应被 QR 码过滤器拦截",
      "input": {
        "message": [{"type": "text", "data": {"text": "今天天气不错"}}],
        "config": {
          "qrcode": {
            "enabled": true,
            "keywords": ["微信", "扫码"],
            "mode": "image_with_keyword"
          }
        }
      },
      "expected": false,
      "check": "should_filter"
    },
    {
      "id": "TC-002",
      "description": "图片+关键词的消息应被 QR 码过滤器拦截",
      "input": {
        "message": [{"type": "image", "data": {"file": "test.jpg"}}, {"type": "text", "data": {"text": "加微信"}}],
        "config": {
          "qrcode": {
            "enabled": true,
            "keywords": ["微信"],
            "mode": "image_with_keyword"
          }
        }
      },
      "expected": true,
      "check": "should_filter"
    },
    {
      "id": "TC-003",
      "description": "纯图片在 block_pure_image 模式下应被拦截",
      "input": {
        "message": [{"type": "image", "data": {"file": "test.jpg"}}],
        "config": {
          "qrcode": {
            "enabled": true,
            "keywords": [],
            "mode": "block_pure_image"
          }
        }
      },
      "expected": true,
      "check": "should_filter"
    },
    {
      "id": "TC-004",
      "description": "包含群号上下文的长数字不应触发 QQ 拦截",
      "input": {
        "message": [{"type": "text", "data": {"text": "欢迎加群 123456789"}}],
        "config": {
          "contact": {
            "enabled": true,
            "patterns": {"qq": "(?<!\\d)[1-9]\\d{7,9}(?!\\d)"},
            "keywords": []
          }
        }
      },
      "expected": false,
      "check": "should_filter"
    },
    {
      "id": "TC-005",
      "description": "CQ 码格式消息在 block_all_images 模式下应拦截",
      "input": {
        "message": "[CQ:image,file=test.jpg]快来扫码",
        "config": {
          "qrcode": {
            "enabled": true,
            "keywords": ["扫码"],
            "mode": "block_all_images"
          }
        }
      },
      "expected": true,
      "check": "should_filter"
    }
  ]
}
```

### 3.2 修改 scripts/verify.py（新增 JSON 锁检查）

在第 4 项检查后新增 `check_filter_acceptance()`：

```python
def check_filter_acceptance() -> list[str]:
    """读取 filter 验收 JSON，逐条运行测试用例验证"""
    errors = []
    acceptance_path = os.path.join(PROJECT_ROOT, ".rules", "verify", "filter-acceptance.json")

    if not os.path.exists(acceptance_path):
        errors.append(".rules/verify/filter-acceptance.json: 缺失")
        log(FAIL, ".rules/verify/filter-acceptance.json: 缺失")
        return errors

    import filter
    with open(acceptance_path, "r", encoding="utf-8") as f:
        suite = json.load(f)

    for tc in suite.get("test_cases", []):
        tc_id = tc["id"]
        msg = tc["input"]["message"]
        cfg = tc["input"]["config"]
        expected = tc["expected"]

        try:
            result, _ = filter.should_filter(msg, cfg)
            status = PASS if result == expected else FAIL
            log(status, f"{tc_id}: {'通过' if result == expected else '失败—期望={expected}, 实际={result}'}")
            if result != expected:
                errors.append(f"{tc_id}: 期望={expected}, 实际={result}")
        except Exception as e:
            log(FAIL, f"{tc_id}: 异常—{e}")
            errors.append(f"{tc_id}: {e}")

    return errors
```

> 注意：上述代码中的 f-string 花括号需要转义，实际实现时用 `{{expected}}` 或字符串拼接。

### 涉及文件

| 文件 | 操作 |
|------|------|
| `.rules/verify/filter-acceptance.json` | 新建（5 个测试用例）|
| `scripts/verify.py` | 修改（新增 check_filter_acceptance + 注册到主流程）|

### 验证方式

```bash
python scripts/verify.py
# → 输出中包含「Filter 验收检查」章节
# → 5 个测试用例全部显示 ✅ 或 ❌
```

---

## Step 4：沙盒隔离（verify 新增 diff 检查）

### 4.1 修改 scripts/verify.py

在已有安全规则检查中增强，新增对 git diff 的检查：

```python
def check_safety_violations() -> list[str]:
    """检查当前 git diff 是否触碰 safety.md 中的红线"""
    errors = []

    # 获取暂存区和未暂存的变更文件列表
    import subprocess
    result = subprocess.run(
        ["git", "diff", "--name-only", "--cached"],
        capture_output=True, text=True, cwd=PROJECT_ROOT
    )
    staged_files = result.stdout.splitlines()

    # 也检查未暂存的变更
    result2 = subprocess.run(
        ["git", "diff", "--name-only"],
        capture_output=True, text=True, cwd=PROJECT_ROOT
    )
    working_files = result2.stdout.splitlines()

    all_changed = set(staged_files + working_files)

    # Safety Level 1 红线路径
    forbidden_paths = [
        "runtime/",
        "config/config.json",
        "main.py",
    ]

    for f in all_changed:
        for forbidden in forbidden_paths:
            if f.startswith(forbidden):
                msg = f"Safety 违规：{f} 触碰 Level 1 红线（禁止修改）"
                errors.append(msg)
                log(FAIL, msg)

    if not errors:
        log(PASS, "无 Safety 红线违规")
    return errors
```

### 涉及文件

| 文件 | 操作 |
|------|------|
| `scripts/verify.py` | 修改（新增 check_safety_violations + 注册到主流程）|

### 验证方式

```bash
# 先修改一个红线文件测试
echo "# test" >> config/config.json
python scripts/verify.py
# → 输出：❌ Safety 违规：config/config.json 触碰 Level 1 红线
git checkout config/config.json  # 还原
```

---

## Step 5：记忆压缩（CLAUDE.md 行数检查 + 压缩脚本）

### 5.1 修改 scripts/verify.py（新增行数检查）

在安全规则检查后新增：

```python
def check_memory_health() -> list[str]:
    """检查 CLAUDE.md 是否超限"""
    errors = []
    claude_path = os.path.join(PROJECT_ROOT, "CLAUDE.md")
    if not os.path.exists(claude_path):
        log(INFO, "CLAUDE.md: 不存在，跳过")
        return errors

    with open(claude_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    line_count = len(lines)
    if line_count > 200:
        log(WARN, f"CLAUDE.md: {line_count} 行（超过 200 行建议，运行 scripts/compress-memory.py）")
    else:
        log(PASS, f"CLAUDE.md: {line_count} 行（正常）")

    return errors
```

### 5.2 新建 scripts/compress-memory.py

路径：`QQMsgForward/scripts/compress-memory.py`

内容：

```python
#!/usr/bin/env python3
"""
CLAUDE.md 记忆压缩工具

当决策日志超过 200 行时，将旧记录摘要化。

用法：python scripts/compress-memory.py

策略：
1. 保留最近 5 条完整记录
2. 第 6 条开始的旧记录，按季度合并为摘要
3. 总行数控制在 150 行以内
"""

import os
import re
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLAUDE_PATH = os.path.join(PROJECT_ROOT, "CLAUDE.md")


def get_records(lines: list[str]) -> list[dict]:
    """解析 CLAUDE.md 为结构化记录列表"""
    records = []
    current = None
    for line in lines:
        m = re.match(r'^### (\d{4}-\d{2}-\d{2})：(.+)$', line)
        if m:
            if current:
                records.append(current)
            current = {"date": m.group(1), "title": m.group(2), "lines": [line]}
        elif current:
            current["lines"].append(line)
    if current:
        records.append(current)
    return records


def compress(records: list[dict]) -> list[str]:
    """压缩记录：保留前 5 条完整，其余合并摘要"""
    output = []
    output.append("# 技术决策日志\n")
    output.append("> 本文档由 scripts/compress-memory.py 自动管理。超过 200 行时旧记录自动摘要。\n\n")
    output.append("---\n")
    output.append("## 格式\n\n每次重大修改时追加一条。\n\n---\n\n")

    # 保留最近的 5 条完整记录
    keep = records[:5]
    archive = records[5:]

    for record in reversed(keep):
        for line in record["lines"]:
            output.append(line + "\n")
        output.append("\n")

    if archive:
        output.append("---\n\n")
        output.append("## 归档记录\n\n")
        output.append("| 日期 | 标题 |\n")
        output.append("|------|------|\n")
        for record in archive:
            output.append(f"| {record['date']} | {record['title']} |\n")

    return output


def main():
    if not os.path.exists(CLAUDE_PATH):
        print("CLAUDE.md 不存在，跳过")
        return

    with open(CLAUDE_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.split("\n")
    if len(lines) <= 200:
        print(f"CLAUDE.md 当前 {len(lines)} 行，未超限，无需压缩")
        return

    records = get_records(lines)
    if not records:
        print("未识别到结构化记录，跳过压缩")
        return

    compressed = compress(records)
    new_content = "".join(compressed)

    # 原子写入
    tmp = CLAUDE_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(new_content)
    os.replace(tmp, CLAUDE_PATH)

    old_lines = len(lines)
    new_lines = len(new_content.split("\n"))
    print(f"压缩完成: {old_lines} 行 → {new_lines} 行 (减少了 {old_lines - new_lines} 行)")


if __name__ == "__main__":
    main()
```

### 涉及文件

| 文件 | 操作 |
|------|------|
| `scripts/compress-memory.py` | 新建 |
| `scripts/verify.py` | 修改（新增 check_memory_health）|

### 验证方式

```bash
# 行数检查
python scripts/verify.py
# → 输出：ℹ️ CLAUDE.md: X 行（正常/超限）

# 压缩测试（手动模拟超限）
python scripts/compress-memory.py
# → 输出：压缩完成: N 行 → M 行
```

---

## 总计

| Step | 新建文件 | 修改文件 | 预计分钟 |
|------|---------|---------|---------|
| 1. 三步唤醒 | 0 | 1（AGENTS.md）| 1 |
| 2. Hooks 钩子 | 2（.githooks/pre-commit, scripts/install-hooks.bat）| 0 | 5 |
| 3. JSON 物理锁 | 1（.rules/verify/filter-acceptance.json）| 1（verify.py）| 10 |
| 4. 沙盒隔离 | 0 | 1（verify.py）| 5 |
| 5. 记忆压缩 | 1（compress-memory.py）| 1（verify.py）| 8 |
| **合计** | **4 个新文件** | **3 个文件修改** | **~30 分钟** |

---

请审核。
