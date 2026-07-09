# 代码优化计划

**日期**: 2026-07-09
**背景**: 全量代码评审后发现的优化点
**状态**: 已分析，待实施

---

## 🔴 高优先级（Bug/功能影响）

### 1. `settings.py` 企微保存逻辑重复

- **位置**: `src/settings.py` `create_wecom_frame` → `on_save()` 第 512-513 行
- **问题**: `cfg["wecom_enabled"]` 赋值两次，双引号/单引号写法不一致
- **修复**: 删除第 513 行（重复行）

### 2. `settings.py` 过滤页 on_save 写错字段

- **位置**: `src/settings.py` `create_filter_frame` → `on_save()` 第 301 行
- **问题**: 过滤页保存函数中写的是 `cfg['wecom_enabled']`，应为 `cfg['filter']['qrcode']['enabled']`
- **修复**: 将第 301 行改为 `cfg['filter']['qrcode']['enabled'] = _cb_checked(qr_enabled_cb)`

### 3. `forward_qq.py` 重复的空 data 检测

- **位置**: `src/forward_qq.py` 第 208-210 行、第 232-237 行
- **问题**: `if not data: return "ok"` 出现两次，第二次永远无效
- **修复**: 删除第 232-237 行（冗余代码块）

### 4. `nt_utils.py` 硬编码端口和实例名

- **位置**: `src/nt_utils.py` 第 14 行、第 35 行
- **问题**: 实例名称和 WebUI 端口硬编码，实例超过 2 个时失效
- **修复**: 改为动态扫描 `runtime/LLBot-Desktop-win-x64*` 目录，按后缀推断端口

---

## 🟡 中优先级（代码质量）

### 5. `tray.py` 多处重复导入

- **位置**: `src/tray.py` `create_status_tab`（第 140、157 行）、`refresh()`（第 238 行）、`shutdown_service()`（第 350 行）
- **问题**: 各函数内部重复 `import forward_qq as _fwd`
- **修复**: 模块顶部统一导入 `import forward_qq`

### 6. `wecom_ui.py` 滥用 `__import__`

- **位置**: `src/wecom_ui.py` 第 346、390、391、394、401、402、451 行
- **问题**: 用 `__import__("logging")` 等非常规调用
- **修复**: 改为头部标准 `import` 语句

### 7. 抽取统一保存反馈函数

- **位置**: `src/settings.py` 三个标签页的 `on_save`
- **问题**: 保存 → 弹窗 → 状态文字逻辑重复 3 次
- **修复**: 抽取 `_save_with_feedback(cfg, status_var, msg)` 公共函数

### 8. `forward_qq.py` 日志级别不统一

- **位置**: `src/forward_qq.py` 第 211 行（debug）vs 第 237 行（info）
- **问题**: 相同内容的 webhook 信息分别用 debug 和 info 级别输出
- **修复**: 统一为 `logger.info`，删除冗余行

---

## 🟢 低优先级（清理/规范）

### 9. `splash.py` Unicode 转义

- **位置**: `src/splash.py` 第 76 行
- **问题**: `正在关闭...` 应直接写中文
- **修复**: 替换为 `"正在关闭..."`

### 10. `.gitignore` 忽略 node_modules

- **位置**: `.gitignore`
- **问题**: `node_modules/` 被完整 git 跟踪
- **修复**: 添加 `runtime/LLBot-Desktop-win-x64/bin/llbot/node_modules/`

---

## 实施顺序

```
Phase 1（🔴高优先级）→ Phase 2（🟡中优先级）→ Phase 3（🟢低优先级）
```

每阶段完成后运行 `python scripts/verify.py` 验证。
