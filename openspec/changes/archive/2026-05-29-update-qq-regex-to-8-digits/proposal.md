## Why

当前 QQ 号正则 `\d{4,9}` 匹配 5 位起，大量 5~7 位数字串（如群号、课程编号、订单号）被误判为 QQ 号拦截。收紧到 8 位以上可大幅降低误杀，同时覆盖 99%+ 真实 QQ 号（主流 8~10 位）。

## What Changes

- 核心 QQ 号正则从 `\d{4,9}`（5~10位）改为 `\d{7,9}`（8~10位）
- 群号上下文豁免阈值从 `>= 6` 同步到 `>= 8`，消除逻辑裂隙
- 同步更新 4 处正则定义 + 1 处阈值

## Capabilities

### New Capabilities
<!-- 无新增能力 -->

### Modified Capabilities
- `message-filter`: QQ 号匹配规则从 5 位放宽门槛改为 8 位收紧门槛；群号上下文豁免阈值同步调整

## Impact

| 文件 | 改动 |
|------|------|
| `filter.py:126` | `>= 6` → `>= 8`（群号豁免阈值） |
| `config.json:45` | 正则 `\d{4,9}` → `\d{7,9}` |
| `wizard.py:36` | 同上（默认模板） |
| `qr_decoder.py:20` | 同上（硬编码回退） |
| `openspec/specs/message-filter/spec.md` | 规格描述更新 |
