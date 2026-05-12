## Context

当前消息过滤系统 (`filter.py`) 通过 "图片+关键词" 启发式规则识别二维码广告。用户群存在真实二维码广告（如扫码加群/加好友），现有规则存在误杀和漏杀。需要在优化规则引擎的同时引入 pyzbar 进行图像级 QR 码解码。

消息格式支持 OneBot v11 array 格式和 CQ 码 string 格式。图片通过 LLOneBot API 传递，消息段中 `data.url` 提供可直接 HTTP 下载的图片链接。

## Goals / Non-Goals

**Goals:**
- 修复大小写敏感导致的绕过漏洞
- 实现三级拦截策略（image_with_keyword / block_pure_image / block_all_images），替代当前二元开关
- QQ 号正则增加群号上下文判断，降低误杀
- 修复 CQ 码字符串解析中 `]` 截断问题
- log_only 模式下降噪
- 新增 pyzbar 真实 QR 码解码能力，对解码内容做规则匹配
- 解码结果缓存（同一 file_id 24h 内不重复下载）
- 设置界面支持新增配置项

**Non-Goals:**
- 不实现通用 OCR 文字识别
- 不接入 LLM 语义判断
- 不修改联系方式正则（phone/wechat/email）
- 不改变转发的 webhook 架构

## Decisions

### 1. QR 解码库选择：pyzbar

**选择**：pyzbar + Pillow（已有依赖）

**备选方案**：
- opencv-python：~100MB，过于臃肿
- zxing-cpp：功能丰富但 Python 绑定不成熟

**理由**：pyzbar 核心 DLL 仅 ~500KB。项目已依赖 Pillow（tray.py 用），无额外大型依赖。Visual C++ 运行时在高版本 Windows 上已预装。发布时在安装包中附带 `libzbar-64.dll` 即可。

### 2. 图片下载策略：优先 url，不调 API

**选择**：直接从消息段 `data.url` HTTP 下载，不通过 LLBot API `get_image` action。

**理由**：LLOneBot 生成的消息段已包含临时 URL（如 `https://multimedia.nt.qq.com.cn/...`），直接 GET 比 API 调用少一次网络往返，且不依赖 LLBot 鉴权。

### 3. QR 解码与关键词规则的关系：串联优先

```
图片消息 → QR 解码（可配置开关）→ 解码命中 → 过滤决策
                ↓ 未命中/失败/关闭
           关键词规则 → 过滤决策
```

**理由**：解码结果更精准（内容即证据），优先采用。解码失败时回退到关键词规则，保证基础覆盖率。

### 4. 三级拦截策略实现

config.json 中 `mode` 字段（当前未使用的 `"image_with_keyword"`）做实为三级枚举：

| mode | 行为 |
|------|------|
| `image_with_keyword` | 仅图片+关键词时拦截（默认，最宽松） |
| `block_pure_image` | 额外拦截无文字纯图片 |
| `block_all_images` | 拦截所有含图片的消息（最激进） |

原 `block_pure_image` 布尔值保留为 deprecated，有值时迁移到对应 mode 并警告，保证向后兼容。

### 5. QQ 号上下文判断

不修改正则本身（数字范围完全重叠，纯正则无解），而是在命中 QQ 正则后检查文本上下文：

```python
QQ_CONTEXT_WHITELIST = ['群', '加群', '群号', '频道', 'channel', 'guild', '进群']
```

若文本含白名单词且命中数字 ≥ 6 位，不触发 QQ 号拦截。

### 6. 解码结果缓存

用内存 dict，以 `file_id` 为 key，存储 `(timestamp, decoded_content)`。默认 TTL 24 小时，通过 `decode_cache_seconds` 配置。缓存仅对成功解码和"无 QR 码"结果生效，超时/错误不缓存。

### 7. 解码结果分析规则

QR 解码出的内容按优先级匹配：

1. **URL** → 检查域名是否在 `decode_suspicious_domains` 列表中
2. **联系方式** → 复用 `check_contact_info` 正则
3. **广告关键词** → 匹配 `decode_block_patterns` 列表

配置文件扩增：

```json
"qrcode": {
  "mode": "image_with_keyword",
  "decode_enabled": true,
  "decode_timeout": 3,
  "decode_cache_seconds": 86400,
  "decode_block_patterns": ["加群", "进群", "兼职", "刷单", "返利"],
  "decode_suspicious_domains": []
}
```

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| pyzbar 在无 VC++ 运行时的机器上导入失败 | `try/except ImportError` 降级为纯关键词模式，日志警告 |
| 图片 URL 可能已过期（腾讯临时链接） | 3 秒超时保护；链接过期自动回退关键词规则 |
| QR 解码增加延迟（下载+解码 ~500ms-2s） | 解码在 webhook 处理流程中同步执行，但设超时上限；默认关闭 `decode_enabled` 由用户按需开启 |
| mode 配置迁移（block_pure_image → mode） | 启动时检查旧字段，自动映射并 warning 日志 |
| QQ 群号判断可能漏杀（广告文本中故意加"群"字） | 仅对 ≥6 位数字豁免；5 位以下 QQ 号不受影响；后续可细化 |
| 解码结果缓存内存泄漏 | dict 有 TTL，定期清理过期条目 |

## Migration Plan

1. 更新 `config.json` schema：新增 `mode`、`decode_*` 字段，保留旧 `block_pure_image` 为 deprecated
2. 启动时自动迁移：若有 `block_pure_image: true` 无 `mode` → 设置 `mode: "block_pure_image"` 并 warning
3. 不支持回退（新字段向下兼容，旧版忽略新字段不影响功能）
4. 部署包需附带 `libzbar-64.dll` 到安装目录

## Open Questions

- `decode_suspicious_domains` 默认列表需要运营数据支撑，初期为空，由用户自行配置
- pyzbar DLL 在 Windows 11 纯净环境（无 VC++ Redistributable）的实际兼容性待验证
