## Why

当前 QR 码过滤仅依赖"图片+关键词"启发式匹配，存在四个问题：(1) 大小写敏感导致关键词绕过，(2) `block_pure_image` 无差别拦截所有纯图片（误杀表情包/截图），(3) QQ 号正则误匹配群号，(4) 没有真正的二维码内容识别——无法区分"带文字的正常截图"和"真正含二维码的广告图片"。需要在优化规则引擎的同时，引入真实 QR 码图像解码能力，从根本上提升过滤准确率。

## What Changes

- 关键词匹配改为大小写不敏感（3 处函数）
- `block_pure_image` 升级为三级可选策略：`image_with_keyword` / `block_pure_image` / `block_all_images`
- QQ 号正则增加上下文语义判断，排除群号场景
- 修复 CQ 码字符串解析中 `]` 字符截断问题
- log_only 模式下降噪：放行日志从 INFO 降为 DEBUG
- **新增**：pyzbar 真实 QR 码图像解码模块，从消息图片中提取 QR 内容
- **新增**：QR 解码结果分析——对解码出的 URL/联系方式/广告关键词做规则匹配
- 设置界面新增 QR 解码相关配置项
- config.json 扩增 decode_enabled、decode_timeout、suspicious_domains 等字段

## Capabilities

### New Capabilities
- `qrcode-decode`: 真实 QR 码图像解码与内容分析，从图片中提取二维码信息并基于内容做过滤决策

### Modified Capabilities
- `message-filter`: 增强过滤规则（大小写不敏感、三级拦截策略、QQ 正则上下文判断）；新增 QR 解码结果作为过滤输入源

## Impact

- `filter.py` — 核心过滤逻辑修改（A 方案 5 项优化 + 集成 QR 解码调用）
- `qr_decoder.py` — **新文件**，pyzbar 图像解码 + 下载 + 缓存
- `config.json` — 扩增 `qrcode.decode_*` 配置字段
- `settings.py` — 设置界面新增 QR 解码配置区域
- `tests/test_filter.py` — 新增大小写、模式切换、QQ 正则上下文测试
- `tests/test_qr_decoder.py` — **新文件**，QR 解码模块测试
- `requirements.txt` — 新增 `pyzbar>=0.1`
