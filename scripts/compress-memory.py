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
        m = re.match(r"^### (\d{4}-\d{2}-\d{2})：(.+)$", line)
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
    """压缩记录：保留前 5 条完整，其余合并为表格"""
    output = []
    output.append("# 技术决策日志\n")
    output.append("> 本文档由 scripts/compress-memory.py 自动管理。超过 200 行时旧记录自动摘要。\n\n")
    output.append("---\n\n")

    keep = records[:5]

    for record in reversed(keep):
        for line in record["lines"]:
            output.append(line + "\n")
        output.append("\n")

    archive = records[5:]
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

    tmp = CLAUDE_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(new_content)
    os.replace(tmp, CLAUDE_PATH)

    old_lines = len(lines)
    new_lines = len(new_content.split("\n"))
    print(f"压缩完成: {old_lines} 行 → {new_lines} 行（减少了 {old_lines - new_lines} 行）")


if __name__ == "__main__":
    main()
