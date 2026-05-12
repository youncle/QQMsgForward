## 1. A方案 RED 阶段 — 规则引擎测试编写

- [ ] 1.1 编写大小写不敏感测试（test_filter.py）
  - 文件：`tests/test_filter.py`
  - 新增 `test_qrcode_case_insensitive_keyword` — 文本 "V: 加好友" 能命中关键词 "v:" 和 "加好友"
  - 新增 `test_contact_case_insensitive_keyword` — 文本 "我的v是 xxx" 能命中关键词
  - **验收**：`python -m pytest tests/test_filter.py -v` → 新测试 RED（失败）

- [ ] 1.2 编写三级拦截策略测试（test_filter.py）
  - 文件：`tests/test_filter.py`
  - 新增 `test_qrcode_mode_block_pure_image` — mode=block_pure_image 时纯图片被拦截
  - 新增 `test_qrcode_mode_block_all_images` — mode=block_all_images 时所有带图片消息被拦截
  - 新增 `test_qrcode_mode_image_with_keyword` — mode=image_with_keyword 时纯图片放行
  - **验收**：新测试 RED（失败，当前无 mode 参数）

- [ ] 1.3 编写 QQ 号上下文判断测试（test_filter.py）
  - 文件：`tests/test_filter.py`
  - 新增 `test_contact_qq_context_whitelist` — "加群 1079264158" 不触发 QQ 拦截
  - 新增 `test_contact_qq_no_context_blocks` — "加我QQ 12345678" 仍然触发 QQ 拦截
  - **验收**：新测试 RED（失败，当前群号会被误拦）

- [ ] 1.4 编写 CQ 码解析 edge case 测试（test_filter.py）
  - 文件：`tests/test_filter.py`
  - 新增 `test_cq_parse_text_with_bracket` — text 中含 `]` 字符时不被截断
  - 新增 `test_cq_parse_record_video_ignored` — [CQ:record, [CQ:video 不误判为图片
  - **验收**：新测试 RED（失败，当前解析有 bug）

## 2. A方案 GREEN+REFACTOR — 规则引擎实现

- [ ] 2.1 实现关键词大小写不敏感匹配
  - 文件：`filter.py`
  - 修改 `check_qrcode_ad`、`check_contact_info`、`_check_contact_detail` 中 `kw in text` → `kw.lower() in text.lower()`
  - **验收**：1.1 测试全部 GREEN

- [ ] 2.2 实现三级拦截策略
  - 文件：`filter.py`
  - `check_qrcode_ad` 增加 `mode` 参数（默认 `image_with_keyword`）
  - 实现三种 mode 的行为分支
  - `should_filter` 传入 `qrcode_cfg.get('mode', 'image_with_keyword')`
  - **验收**：1.2 测试全部 GREEN

- [ ] 2.3 实现 QQ 号上下文判断
  - 文件：`filter.py`
  - 新增 `QQ_CONTEXT_WHITELIST` 常量
  - `_check_contact_detail` 中 QQ 正则命中后检查上下文白名单
  - 仅对 ≥6 位数字做白名单豁免
  - **验收**：1.3 测试全部 GREEN

- [ ] 2.4 修复 CQ 码字符串解析
  - 文件：`filter.py`
  - 修复 `_parse_cq_string`：处理 text 中的 `]` 字符，排除 record/video/file 等非图片段
  - 提取 CQ 码参数时处理 value 含特殊字符的边界
  - **验收**：1.4 测试全部 GREEN

- [ ] 2.5 实现日志降噪
  - 文件：`qq-message-forward.py`
  - `log_only` 模式下放行日志从 `logger.info` 改为 `logger.debug`
  - **验收**：log_only=true 时放行消息不出现在 INFO 日志中

## 3. B方案 RED 阶段 — QR 解码测试编写

- [ ] 3.1 编写 QR 解码模块测试
  - 文件：`tests/test_qr_decoder.py`（新建）
  - 用 PIL 生成含 QR 码的测试图片，用 pyzbar 解码验证 round-trip
  - 测试不含 QR 码的普通图片返回空结果
  - 测试下载超时场景（mock requests）
  - 测试缓存命中/过期场景
  - **验收**：`python -m pytest tests/test_qr_decoder.py -v` → RED（模块不存在）

- [ ] 3.2 编写解码内容分析测试
  - 文件：`tests/test_qr_decoder.py`
  - QR 内容为可疑 URL → 命中
  - QR 内容为手机号 → 命中
  - QR 内容为广告关键词 → 命中
  - QR 内容为正常 URL → 放行
  - **验收**：新测试 RED

- [ ] 3.3 编写联合过滤集成测试
  - 文件：`tests/test_filter.py`
  - 新增 `test_should_filter_qr_decode_hit` — 消息含 QR 码图片 + decode_enabled → QR 解码拦截
  - 新增 `test_should_filter_qr_decode_disabled` — decode_enabled=false → 回退关键词规则
  - 新增 `test_should_filter_qr_decode_fallback` — 解码失败/超时 → 回退关键词规则
  - **验收**：新测试 RED（当前无 decode 逻辑）

## 4. B方案 GREEN+REFACTOR — QR 解码实现

- [ ] 4.1 创建 qr_decoder.py 模块骨架
  - 文件：`qr_decoder.py`（新建）
  - 函数签名：`decode_qr(image_data: bytes) -> List[str]`
  - `try/except ImportError` 保护 pyzbar 导入
  - **验收**：模块可 import，pyzbar 缺失时有明确错误提示

- [ ] 4.2 实现图片下载与缓存
  - 文件：`qr_decoder.py`
  - 函数 `download_image(url: str, timeout: int) -> Optional[bytes]`
  - 函数 `get_cached(file_id: str, cache_seconds: int) -> Optional[List[str]]`
  - 函数 `set_cache(file_id: str, result: List[str]) -> None`
  - 函数 `clean_expired_cache() -> None`
  - **验收**：下载成功返回 bytes，超时返回 None；缓存 TTL 生效

- [ ] 4.3 实现 pyzbar 解码
  - 文件：`qr_decoder.py`
  - Pillow 打开图片 → 转灰度 → pyzbar.decode
  - 返回所有解码出的 data 列表
  - **验收**：3.1 模块测试 GREEN

- [ ] 4.4 实现解码内容分析
  - 文件：`qr_decoder.py`
  - 函数 `analyze_decoded_content(content_list: List[str], config: dict) -> Optional[str]`
  - 按优先级：URL域名检测 → 联系方式正则 → 广告关键词
  - 返回命中原因字符串或 None
  - **验收**：3.2 测试 GREEN

- [ ] 4.5 集成到 should_filter 流程
  - 文件：`filter.py`
  - `should_filter` 中在关键词检查前插入 QR 解码调用
  - 仅当 `decode_enabled=true` 且消息含 image 段时触发
  - 解码命中 → 直接返回过滤决策
  - 解码未命中/失败 → 继续关键词规则
  - **验收**：3.3 集成测试 GREEN

## 5. 配置与 UI 更新

- [ ] 5.1 更新 config.json schema
  - 文件：`config.json`
  - 新增：`qrcode.mode`、`qrcode.decode_enabled`、`qrcode.decode_timeout`
  - 新增：`qrcode.decode_cache_seconds`、`qrcode.decode_block_patterns`、`qrcode.decode_suspicious_domains`
  - 保留 `qrcode.block_pure_image` 标记为 deprecated（不再读取）
  - **验收**：JSON 合法，所有字段有默认值

- [ ] 5.2 实现配置迁移逻辑
  - 文件：`filter.py` 或新建 `migration.py`
  - 启动时检查：`block_pure_image=true` 且 `mode` 不存在 → 设置 `mode = "block_pure_image"`
  - 输出 `logger.warning` 引导用户使用新字段
  - **验收**：旧配置启动后自动迁移，日志有 warning

- [ ] 5.3 更新 settings.py 设置界面
  - 文件：`settings.py`
  - QR 码过滤区新增：mode 下拉选择框（三选一）
  - 新增 QR 解码子区域：decode_enabled 开关、decode_timeout 输入框、decode_block_patterns 输入框
  - 保存时写入新字段
  - **验收**：UI 可操作，配置正确持久化

- [ ] 5.4 更新 requirements.txt
  - 文件：`requirements.txt`
  - 新增 `pyzbar>=0.1.9`
  - **验收**：`pip install -r requirements.txt` 成功

## 6. 全量验证

- [ ] 6.1 运行全量测试套件
  - 命令：`python -m pytest tests/ -v`
  - 所有旧测试保持 GREEN
  - 所有新测试 GREEN
  - **验收**：0 失败，覆盖率 ≥ 当前基线

- [ ] 6.2 编译检查与代码审查
  - `python -m py_compile filter.py qr_decoder.py settings.py qq-message-forward.py`
  - 无语法错误
  - 确认 CLAUDE.md 规范（2空格缩进、单引号、无分号）
  - **验收**：编译通过，lint 无新增警告
