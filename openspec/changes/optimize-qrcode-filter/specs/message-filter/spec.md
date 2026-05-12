## MODIFIED Requirements

### Requirement: 二维码消息过滤
系统 SHALL 检测消息中的图片内容并结合上下文关键词，过滤疑似二维码广告的消息。关键词匹配 SHALL 不区分大小写。拦截策略 SHALL 支持三级可选模式。

#### Scenario: 图片+关键词组合拦截
- **WHEN** 消息包含图片段且文本中包含 "加我""扫码""联系" 等关键词（大小写不敏感）
- **THEN** 系统记录拦截日志，不转发该消息

#### Scenario: 纯文本消息通过
- **WHEN** 消息仅包含文本且无图片段
- **THEN** 系统不触发二维码过滤规则

#### Scenario: 纯图片无关键词通过（image_with_keyword 模式）
- **WHEN** 消息包含图片段但文本中无二维码相关关键词，且模式为 `image_with_keyword`
- **THEN** 系统不拦截该消息（表情包、正常截图不受影响）

#### Scenario: 纯图片无文字拦截（block_pure_image 模式）
- **WHEN** 消息包含图片段但无任何文字，且模式为 `block_pure_image`
- **THEN** 系统拦截该消息，记录 [QR码] 日志

#### Scenario: 所有图片均拦截（block_all_images 模式）
- **WHEN** 消息包含任何图片段（无论有无文字），且模式为 `block_all_images`
- **THEN** 系统拦截该消息

#### Scenario: 关键词大小写不敏感匹配
- **WHEN** 消息文本包含 "V:" 或 "v:" 或 "扫码" 或 "掃碼"
- **THEN** 系统均能匹配对应关键词并触发规则

#### Scenario: CQ 码字符串格式支持
- **WHEN** 消息为 CQ 码字符串格式（如 `[CQ:image,file=xxx][CQ:text,text=扫码加我]`）
- **THEN** 系统正确解析并应用上述拦截规则

### Requirement: 联系方式文本过滤
系统 SHALL 使用正则表达式匹配消息文本中的私人联系方式并拦截。关键词匹配 SHALL 不区分大小写。QQ 号正则在命中群号上下文时应放行，避免误杀加群邀请。

#### Scenario: 手机号拦截
- **WHEN** 消息文本包含符合中国手机号格式的数字串（如 13812345678）
- **THEN** 系统记录拦截日志，不转发该消息

#### Scenario: QQ号拦截
- **WHEN** 消息文本包含 5-10 位纯数字串且上下文不含群号标识词（如 "群""加群""群号"）
- **THEN** 系统记录拦截日志，不转发该消息

#### Scenario: 群号不误杀
- **WHEN** 消息文本包含 "欢迎加群 1079264158" 等群号上下文
- **THEN** 系统不触发 QQ 号拦截规则

#### Scenario: 微信号拦截
- **WHEN** 消息文本包含 wxid_ 开头的微信号
- **THEN** 系统记录拦截日志，不转发该消息

#### Scenario: 邮箱拦截
- **WHEN** 消息文本包含标准邮箱格式（如 user@example.com）
- **THEN** 系统记录拦截日志，不转发该消息

#### Scenario: 联系方式关键词拦截
- **WHEN** 消息文本包含 "我的Q""我的V""加好友""私聊我" 等关键词（大小写不敏感）
- **THEN** 系统记录拦截日志，不转发该消息

#### Scenario: 正常消息通过
- **WHEN** 消息文本不包含任何联系方式格式或关键词
- **THEN** 系统正常转发该消息

### Requirement: 过滤规则可配置
过滤规则 SHALL 从 `config.json` 文件读取，用户修改配置文件后重启服务即可生效。配置 SHALL 支持 QR 码拦截模式选择和 QR 解码参数。

#### Scenario: 修改关键词列表
- **WHEN** 用户编辑 `config.json` 中的 `filter.qrcode.keywords` 数组并重启
- **THEN** 系统使用新的关键词列表进行过滤

#### Scenario: 启用/禁用过滤规则
- **WHEN** 用户设置 `filter.qrcode.enabled` 为 `false` 并重启
- **THEN** 系统不再进行二维码过滤

#### Scenario: 切换拦截模式
- **WHEN** 用户设置 `filter.qrcode.mode` 为 `block_all_images` 并重启
- **THEN** 系统拦截所有包含图片的消息

#### Scenario: 配置 QR 解码
- **WHEN** 用户设置 `filter.qrcode.decode_enabled` 为 `true`
- **THEN** 系统在过滤时对图片执行真实 QR 码解码

#### Scenario: 仅日志模式（试运行）
- **WHEN** 用户设置 `filter.log_only` 为 `true`
- **THEN** 系统匹配到过滤规则时仅记录日志，正常转发消息

### Requirement: 过滤日志记录
系统 SHALL 以统一格式记录所有被拦截的消息，包括拦截原因、群号和时间。在 `log_only` 模式下，放行消息 SHALL 使用 DEBUG 级别记录以降低日志噪音。

#### Scenario: 拦截日志格式
- **WHEN** 一条消息被二维码过滤规则拦截
- **THEN** 日志输出格式为 `[FILTER] 已拦截: 群{group_id} - [QR码] {消息摘要}`

#### Scenario: 联系方式拦截日志
- **WHEN** 一条消息被联系方式规则拦截
- **THEN** 日志输出格式为 `[FILTER] 已拦截: 群{group_id} - [联系方式:手机号] {消息摘要}`

#### Scenario: QR 解码拦截日志
- **WHEN** 一条消息被 QR 解码结果命中
- **THEN** 日志输出格式为 `[FILTER] 已拦截: 群{group_id} - [QR解码:URL]{内容}`

#### Scenario: log_only 放行日志降噪
- **WHEN** `log_only` 为 `true` 且消息未被任何过滤规则命中
- **THEN** 系统使用 DEBUG 级别记录放行信息，默认不输出到日志
