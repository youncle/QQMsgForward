# 企微 uiautomation 通道实施计划 — 第一阶段

> 本文档记录了 QQMsgForward 项目新增企微 uiautomation 发送通道的实施方案。
> 第一阶段：API 模式重构 + 配置面板改造（纯重构，不改变任何运行行为）

---

## 一、阶段目标

1. **`wecom.py`**：`try_forward` 从大函数拆分为调度层 + `_forward_api` 执行层 + `_forward_ui` 桩
2. **`settings.py`**：微信标签页增加"启用UI转发"复选框（与"启用微信转发"同行）
3. **配置兼容**：旧 `config.json` 无 `wecom_mode` 字段时默认 `"api"`
4. **零行为变化**：所有 API 模式发送流程、日志格式、过滤逻辑与重构前一致

---

## 二、涉及文件

| 文件 | 改动量 | 说明 |
|------|--------|------|
| `src/wecom.py` | ~-10 / +50 行 | try_forward 调度重写 + _forward_api 提取 + _forward_ui 桩 |
| `src/settings.py` | ~+8 行 | UI 开关复选框 + on_save 写 wecom_mode 字段 |
| `config/config.json` | 0 行 | 运行时写入，不做硬改动 |

---

## 三、改动详解

### 3.1 `src/wecom.py` — try_forward 重构

#### 改后结构

```
try_forward(data, cfg)                    ← 调度层
  ├── 现有逻辑：启用检查/bot匹配/消息解析/过滤 (不变)
  └── mode = cfg.get("wecom_mode", "api")
       ├── "ui"  → _forward_ui(bot, text, image_urls, group_id)
       └── "api" → _forward_api(bot, text, image_urls, group_id)

_forward_api(bot, text, image_urls, group_id)   ← 从原 try_forward 提取
  └── send_to_bot(text) + _send_image(url)  (完整保留原逻辑)

_forward_ui(bot, text, image_urls, group_id)    ← 桩函数
  └── raise NotImplementedError("下一阶段实现")
```

#### 不变的部分

- `send_to_bot(key, payload)`
- `_send_image(key, data)`
- `_download_image(url)`
- `_extract_key(key)`
- `_image_b64_md5(data)`
- `test_bot(key)`
- 导入语句、常量 `WECOM_API`、`_image_cache`

#### 关键细节

- `_forward_api` 接收到空 `text` 时不发送文本消息（`if text` 判断）
- 图片发送循环保留了 `[:3]` 截断、下载失败时发 `[图片]` 占位
- 日志格式前缀 `[WECOM]` 保持不变

---

### 3.2 `src/settings.py` — 微信标签页改造

#### 3.2.1 顶部复选框

```python
# 改前（7行）
frm_top = ttk.Frame(frame)
frm_top.pack(fill="x", pady=(0, 5))
enabled_cb = tk.Checkbutton(frm_top, text="启用微信转发")
enabled_cb.pack(anchor="w")

# 改后（9行）
frm_top = ttk.Frame(frame)
frm_top.pack(fill="x", pady=(0, 5))
enabled_cb = tk.Checkbutton(frm_top, text="启用微信转发")
enabled_cb.pack(side="left", padx=(0, 15))

ui_mode = cfg.get("wecom_mode", "api") == "ui"
ui_var = tk.IntVar(value=1 if ui_mode else 0)
ui_cb = tk.Checkbutton(frm_top, text="启用UI转发 (操控企业微信)", variable=ui_var)
ui_cb.pack(side="left")
```

效果：

```
┌────────────────────────────────────────────────────┐
│  ☐ 启用微信转发     ☐ 启用UI转发 (操控企业微信) │
└────────────────────────────────────────────────────┘
```

#### 3.2.2 on_save 保存逻辑

在 `cfg["wecom_bots"] = bots` 之前插入：

```python
cfg["wecom_mode"] = "ui" if ui_var.get() else "api"
```

#### 3.2.3 向后兼容

- `cfg.get("wecom_mode", "api")` 确保旧配置无此字段时默认 `"api"`
- UI 开关初始化：读取 cfg 中的 `wecom_mode`，为 `"ui"` 时勾选

---

### 3.3 config.json — 运行时写入

首次通过面板保存后，配置文件中新增字段：

```json
{
  "wecom_enabled": true,
  "wecom_mode": "api",
  "wecom_bots": [
    {
      "key": "8b561d39-...",
      "name": "朝暮说-测试群",
      "source_groups": []
    }
  ]
}
```

手动编辑或旧版本配置读取时，`cfg.get("wecom_mode", "api")` 向下兼容。

---

## 四、阶段边界（不做的事）

| 事项 | 原因 |
|------|------|
| 不新建 `wecom_ui.py` | 第二阶段实现 UI 引擎时再建 |
| 不修改 `forward_qq.py` | QQ→QQ 链路不动 |
| 不修改 `tray.py` | 启动逻辑无变化（UI 引擎下阶段再初始化） |
| 不修改 `filter.py` | 过滤逻辑与通道无关 |
| 不修改 `main.py` | 入口不动 |
| 不添加 `uiautomation` 依赖 | 下阶段再加 |
| 不改现有日志格式 | 保持 `[WECOM]` 前缀一致性 |

---

## 五、验证清单

| # | 检查项 | 验证方法 |
|---|--------|----------|
| 1 | API 转发功能不变 | 启动服务 → QQ 发消息 → 企微群收到 |
| 2 | UI 开关默认不勾 | 启动后打开面板 → 确认"启用UI转发"未选中 |
| 3 | UI 开关状态持久化 | 勾选 → 保存 → 关闭面板 → 重新打开 → 状态一致 |
| 4 | 旧配置兼容 | 备份 config.json，删掉 wecom_mode → 重启 → 面板显示 API 模式 |
| 5 | 配置写入正确 | 保存后检查 config.json 中 wecom_mode 值正确 |

---

## 六、实施顺序

```
Step 1 → 展示最终计划文档（当前）
       ↓ 你确认
Step 2 → 修改 wecom.py（贴代码段 → 你确认 → 应用）
       ↓ 你确认
Step 3 → 修改 settings.py（贴代码段 → 你确认 → 应用）
       ↓ 你确认
Step 4 → 验证测试
```

