## ADDED Requirements

### Requirement: QR 码图像解码
系统 SHALL 从消息附带的图片中检测并解码 QR 码内容，作为过滤决策的输入源。

#### Scenario: 成功解码图片中的 QR 码
- **WHEN** 消息包含 image 段且该图片含有效 QR 码（如扫码加群的 URL）
- **THEN** 系统提取 QR 码内容（URL、文本等），传递给后续内容分析规则

#### Scenario: 图片不含 QR 码
- **WHEN** 消息包含 image 段但图片中无 QR 码
- **THEN** 系统返回空解码结果，不触发 QR 解码拦截规则

#### Scenario: 图片下载超时
- **WHEN** 图片 URL 下载超过配置的超时时间（默认 3 秒）
- **THEN** 系统放弃解码，回退到关键词规则判断

#### Scenario: 非 image 段消息
- **WHEN** 消息不包含 image 段（纯文本、record、video 等）
- **THEN** 系统跳过 QR 解码流程，直接进入关键词规则判断

### Requirement: 解码内容分析
系统 SHALL 对 QR 码解码出的内容执行规则匹配，判断是否为广告/风险内容。

#### Scenario: QR 码含可疑域名
- **WHEN** QR 码内容为 URL 且域名匹配配置的可疑域名列表
- **THEN** 系统触发过滤拦截或记录日志

#### Scenario: QR 码含联系方式
- **WHEN** QR 码解码出的文本包含手机号、QQ 号、微信号或邮箱格式
- **THEN** 系统触发过滤拦截或记录日志

#### Scenario: QR 码含广告关键词
- **WHEN** QR 码内容包含 "加群""进群""兼职""刷单" 等广告关键词
- **THEN** 系统触发过滤拦截或记录日志

#### Scenario: QR 码内容正常
- **WHEN** QR 码解码出的内容不匹配任何风险规则（如正常 URL、扫码支付、官方链接）
- **THEN** 系统放行消息

### Requirement: 解码结果缓存
系统 SHALL 对已解码的图片结果进行缓存，避免相同图片重复下载和解码。

#### Scenario: 重复图片命中缓存
- **WHEN** 同一 file_id 的图片在缓存有效期内（默认 24 小时）再次出现
- **THEN** 系统直接使用缓存结果，不重新下载和解码

#### Scenario: 缓存过期
- **WHEN** 缓存超过配置的有效期
- **THEN** 系统重新下载图片并解码

### Requirement: QR 解码可配置
系统 SHALL 从 config.json 读取 QR 解码相关配置，允许启用/禁用及调整参数。

#### Scenario: 启用 QR 解码
- **WHEN** 用户设置 `filter.qrcode.decode_enabled` 为 `true`
- **THEN** 系统在过滤检查时执行图片 QR 码解码

#### Scenario: 禁用 QR 解码
- **WHEN** 用户设置 `filter.qrcode.decode_enabled` 为 `false`
- **THEN** 系统跳过 QR 解码，仅使用关键词规则过滤

#### Scenario: 配置解码超时
- **WHEN** 用户设置 `filter.qrcode.decode_timeout` 为 5 秒
- **THEN** 系统在 5 秒内未完成图片下载则放弃解码

### Requirement: 解码与关键词联合过滤
系统 SHALL 将 QR 解码结果与原有关键词规则合并，按优先级执行过滤决策。

#### Scenario: QR 解码命中优先于关键词
- **WHEN** QR 解码识别出风险内容且关键词规则未命中
- **THEN** 系统基于解码结果触发过滤（解码结果优先级更高）

#### Scenario: 解码失败回退关键词
- **WHEN** QR 解码失败、超时或图片不含 QR 码
- **THEN** 系统回退到关键词规则判断

#### Scenario: log_only 模式下的解码日志
- **WHEN** `log_only` 为 `true` 且 QR 解码命中风险内容
- **THEN** 系统仅记录日志，不拦截消息
