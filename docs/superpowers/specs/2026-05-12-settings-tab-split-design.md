# 设置标签页拆分

**日期:** 2026-05-12
**状态:** 已确认

## 目标

将当前"设置"标签页中的内容拆分为两个独立标签页：**转发** 和 **过滤**，使设置界面从 2 个标签变为 3 个标签。

## 当前状态

```
┌──────────┬──────────┐
│   状态   │   设置   │
│ 服务状态 │ 转发规则 │
│ 日志查看 │ QR码过滤 │
│          │ QR解码   │
│          │ 联系方式 │
│          │ [保存]   │
└──────────┴──────────┘
```

## 目标状态

```
┌──────────┬──────────┬──────────┐
│   状态   │   转发   │   过滤   │
│ 服务状态 │ 转发规则 │ QR码过滤 │
│ 日志查看 │ [保存]   │ QR解码   │
│          │          │ 联系方式 │
│          │          │ [保存]   │
└──────────┴──────────┴──────────┘
```

## 文件变更

### settings.py

- 删除 `create_settings_frame(parent)` 函数
- 新增 `create_forward_frame(parent)` — 包含转发规则区域 + 保存按钮 + 状态标签
- 新增 `create_filter_frame(parent)` — 包含 QR码过滤/QR码图像解码/联系方式过滤 三个区域 + 保存按钮 + 状态标签
- 公用函数 `load_config()`、`save_config()` 保持不变
- 移除 `if __name__ == '__main__'` 独立窗口入口

### tray.py

- Notebook 标签页从 2 个改为 3 个：
  - `create_status_tab(notebook)` → `text='状态'`
  - `settings_mod.create_forward_frame(notebook)` → `text='转发'`
  - `settings_mod.create_filter_frame(notebook)` → `text='过滤'`
- 导入方式从 `import settings as settings_mod` 保持不变，调用改为新函数名

## 保存行为

- 每个标签页各有独立的"保存"按钮
- 点击保存时，从当前标签页的表单控件读取值，写入 `config.json`
- 两个标签页读写同一个 `config.json`，后保存的覆盖先保存的（不同配置段互不干扰）

## 不涉及

- 状态标签页内容不变
- `config.json` 数据结构不变
- `wizard.py` 首次运行向导不变
- `filter.py` / `qr_decoder.py` / `forward.py` 业务逻辑不变
