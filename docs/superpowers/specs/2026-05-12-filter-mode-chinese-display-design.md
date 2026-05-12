# 过滤标签拦截模式下拉列表中文化

## 目标
将「过滤标签 → QR码过滤 → 拦截模式」下拉列表中显示的英文选项改为中文，内部存储值保持不变。

## 方案：显示映射
新增中英文映射表，UI 层显示中文，`config.json` 和 `filter.py` 继续使用英文值。

## 中文文案
| 英文值 | 中文显示 |
|---|---|
| `image_with_keyword` | 仅关键词图片 |
| `block_pure_image` | 拦截纯图片 |
| `block_all_images` | 拦截所有图片 |

## 改动文件
仅改 `settings.py` 一个文件。

## 具体修改

### 1. 新增映射表
在 `create_filter_frame` 函数内（下拉框定义之前）加入：

```python
MODE_OPTIONS = {
    'image_with_keyword': '仅关键词图片',
    'block_pure_image': '拦截纯图片',
    'block_all_images': '拦截所有图片',
}
MODE_DISPLAY = list(MODE_OPTIONS.values())
MODE_REVERSE = {v: k for k, v in MODE_OPTIONS.items()}
```

### 2. 加载时：英文存储值 → 中文显示值
```python
# 改前
mode_var = tk.StringVar(value=qr.get('mode', 'image_with_keyword'))

# 改后
stored_mode = qr.get('mode', 'image_with_keyword')
display_mode = MODE_OPTIONS.get(stored_mode, MODE_OPTIONS['image_with_keyword'])
mode_var = tk.StringVar(value=display_mode)
```

### 3. 下拉列表用中文
```python
# 改前
values=['image_with_keyword', 'block_pure_image', 'block_all_images'],

# 改后
values=MODE_DISPLAY,
```

### 4. 保存时：中文显示值 → 英文存储值
```python
# 改前
cfg['filter']['qrcode']['mode'] = mode_var.get()

# 改后
cfg['filter']['qrcode']['mode'] = MODE_REVERSE.get(mode_var.get(), 'image_with_keyword')
```

## 向前兼容
- `config.json` 中已存的英文值不受影响，加载时通过映射表正确显示中文
- `filter.py` 比较逻辑不变（仍用英文值）
- `wizard.py` 默认值不变

## 不改动的文件
- `filter.py` — 无变化
- `wizard.py` — 无变化
- `config.json` — 存储格式不变
