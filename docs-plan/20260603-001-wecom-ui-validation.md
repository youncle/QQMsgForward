# 微信标签 — 按模式区分必填字段

## 背景

当前微信标签页的"添加机器人"按钮（on_add）强制校验 Webhook Key 非空。但 UI 模式（操控企业微信桌面端）不需要 Key，只需要群名称。导致 UI 模式下无法添加机器人。

## 分析

### 转发引擎实际需要的字段

| 模式 | 必要字段 | 可选字段 |
|------|---------|---------|
| UI 模式 | `name`（企微群名称） | `key`, `source_groups` |
| API 模式 | `key`（Webhook Key） | `name`, `source_groups` |

### 当前代码阻塞点

```
on_add() ──→ if not key: 弹出警告并 return    ←── 阻塞 UI 模式
              ├─ 用 bot["key"] == key 判重    ←── key 为空时 KeyError
              └─ 列表显示 fallback key[:16]    ←── key 为空时显示异常
```

### 转发引擎（wecom.py）— 不需要改

- `_forward_api()` 已有 `if not key: return`，空 key 自动跳过
- `_forward_ui()` 只读 `bot.get("name", "")`，不依赖 key

## 改动清单

### 1. `src/settings.py` — `on_add()`

**当前**：
```python
def on_add():
    key = key_entry.get().strip()
    name = name_entry.get().strip()
    ...
    if not key:
        messagebox.showwarning("提示", "请输入 Webhook Key")
        return
    for i, bot in enumerate(bots):
        if bot["key"] == key:    # ← key 为空时 KeyError
            bots[i] = {"key": key, "name": name, ...}
            ...
            return
    bots.append({"key": key, "name": name, ...})
```

**改为**：
```python
def on_add():
    key = key_entry.get().strip()
    name = name_entry.get().strip()
    raw = sources_entry.get().replace("，", ",")
    srcs = [s.strip() for s in raw.split(",") if s.strip()]
    is_ui = bool(int(ui_cb.getvar(ui_cb["variable"])))

    # 按模式校验
    if is_ui:
        if not name:
            messagebox.showwarning("提示", "UI 模式需要填写群名称")
            return
        dup_key = name     # UI 模式用 name 判重
    else:
        if not key:
            messagebox.showwarning("提示", "API 模式需要填写 Webhook Key")
            return
        dup_key = key      # API 模式用 key 判重

    # 判重（安全访问）
    for i, bot in enumerate(bots):
        if bot.get("key", "") == key or bot.get("name", "") == name:
            bots[i] = {"key": key, "name": name, "source_groups": srcs}
            refresh_list()
            clear_inputs()
            return
    bots.append({"key": key, "name": name, "source_groups": srcs})
    refresh_list()
    clear_inputs()
```

### 2. `src/settings.py` — `refresh_list()`

**当前**：
```python
label = name + " (" + src_str + ")" if name else key[:16] + "... (" + src_str + ")"
```

**改为**：
```python
label = name + " (" + src_str + ")" if name else (key[:16] + "..." if key else "未命名") + " (" + src_str + ")"
```

## 影响范围

| 维度 | 说明 |
|------|------|
| 功能 | UI 模式不再强制 Key，可正常添加机器人 |
| 兼容 | 现有配置不受影响，key 非空的机器人照常工作 |
| 风险 | 极低，仅改 UI 校验和显示，不动转发逻辑 |
| 依赖 | 无 |

## 验证方法

1. UI 模式 → 不填 Key，只填群名称 → 添加成功
2. API 模式 → 不填 Key，点添加 → 提示"请输入 Webhook Key"
3. API 模式 → 填写 Key 和群名称 → 添加成功
4. 列表显示：只有 name 无 key → 显示"名称 (来源群)"；name 和 key 都空 → 显示"未命名 (来源群)"
