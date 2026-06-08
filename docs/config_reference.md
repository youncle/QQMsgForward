# 配置文件参考 — config.json

## 文件位置

- 源码运行：`项目根目录/config/config.json`
- 打包运行：`exe所在目录/config/config.json`
- 首次启动：向导自动生成，路径由 `tray.py` 设置

## 热重载

除 `robot_qq` 外，所有字段修改后**立即生效**（每次请求从文件重新读取），无需重启服务。修改 `robot_qq` 后需 `stop.vbs → start.vbs` 重启。

---

## 顶层字段一览

| 字段 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| `robot_qq` | int[] | ✅ | — | 机器人 QQ 号数组 |
| `forward_rules` | object | ✅ | `{}` | 转发规则映射 |
| `llbot_api` | string | ❌ | `http://127.0.0.1:3000` | （已废弃）保留向后兼容 |
| `llbot_token` | string | ❌ | `""` | API 鉴权 Bearer Token |
| `llbot_apis` | object | ❌ | — | 动态写入的 QQ→端口映射 |
| `filter` | object | ✅ | 见下方 | 过滤规则配置 |
| `forward` | object | ✅ | 见下方 | 转发策略配置 |

---

## 各字段详解

### `robot_qq`

```json
"robot_qq": [85039678, 2776992588]
```

| 项目 | 说明 |
|------|------|
| 类型 | int 数组 |
| 必需 | 是 |
| 旧格式兼容 | 单个 int 值自动迁移为数组（如 `"robot_qq": 12345` → `[12345]`） |
| 修改后 | 需重启服务（LLBot 实例数在启动时确定） |

用于标识当前有哪些 QQ 号作为机器人。启动时会为每个 QQ 启动一个 LLBot 实例。

---

### `forward_rules`

```json
"forward_rules": {
  "1079264158": {
    "targets": ["1080631149"],
    "note": "（测试）源1079264158 → 目1080631149"
  },
  "107054156": {
    "targets": ["702961941"],
    "note": "（生产）私享会转发"
  }
}
```

| 项目 | 说明 |
|------|------|
| 类型 | object，key=源群 ID（string），value=规则对象 |
| 必需 | 是 |
| 旧格式兼容 | value 为数组时自动迁移为 `{"targets": [...]}` |

**规则对象字段**：

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `targets` | string[] | ✅ | 目标群 ID 列表，消息转发到这些群 |
| `note` | string | ❌ | 备注，仅用于配置面板显示 |

---

### `llbot_api`（已废弃）

```json
"llbot_api": "http://127.0.0.1:3000"
```

| 项目 | 说明 |
|------|------|
| 类型 | string |
| 必需 | 否 |
| 状态 | ❌ 已废弃，由 `llbot_apis` 替代 |
| 作用 | 旧版单机器人配置，保留仅为向后兼容 |

> 新安装不会生成此字段。保留仅用于读取旧配置。

---

### `llbot_token`

```json
"llbot_token": ""
```

| 项目 | 说明 |
|------|------|
| 类型 | string |
| 必需 | 否 |
| 默认 | `""`（空=无鉴权） |

当 LLBot 配置了 `access_token` 时，设置此值。转发 API 调用时自动添加请求头：

```
Authorization: Bearer {llbot_token}
```

---

### `llbot_apis`（动态写入）

```json
"llbot_apis": {
  "2776992588": "http://127.0.0.1:3000",
  "85039678": "http://127.0.0.1:3001"
}
```

| 项目 | 说明 |
|------|------|
| 类型 | object，key=QQ 号（string），value=API base URL |
| 必需 | 否 |
| 写入时机 | 每次启动后自动探测写入 |
| 手动编辑 | ❌ 不建议手动编辑，`robot_qq` 和端口决定此映射 |

**生成逻辑**：

1. 启动 N 个 LLBot 实例（端口 3000 到 3000+N-1）
2. 对每个端口 GET `/get_login_info`
3. 响应成功 → `{返回的QQ号: "http://127.0.0.1:{端口}"}`
4. 写入 `config.json`

---

### `filter.qrcode`

```json
"filter": {
  "qrcode": {
    "enabled": true,
    "keywords": ["feishu", "weixin", "qq", "dingding"],
    "mode": "image_with_keyword",
    "block_pure_image": false,
    "decode_enabled": true,
    "decode_timeout": 2,
    "decode_cache_seconds": 86400,
    "decode_block_patterns": ["加群", "进群", "兼职", "刷单", "返利", "feishu", "qq", "weixin", "wechat", "dingding"],
    "decode_suspicious_domains": []
  }
}
```

| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `enabled` | bool | `true` | 是否启用 QR 码/图片过滤 |
| `keywords` | string[] | — | 图片匹配关键词（不区分大小写） |
| `mode` | string | `"image_with_keyword"` | 图片拦截模式（见下方） |
| `block_pure_image` | bool | `false` | （旧版兼容）若为 true 且 mode 为默认，自动升级为 `block_pure_image` |
| `decode_enabled` | bool | `true` | 是否启用真·QR 码解码（需 pyzbar） |
| `decode_timeout` | int | `2` | 图片下载超时（秒） |
| `decode_cache_seconds` | int | `86400` | 解码结果缓存时间（秒，默认 24 小时） |
| `decode_block_patterns` | string[] | — | 解码内容广告关键词匹配 |
| `decode_suspicious_domains` | string[] | `[]` | 可疑域名黑名单，命中则拦截 |

**图片拦截模式 (`mode`)**：

| 值 | 行为 | 适用场景 |
|---|---|---|
| `image_with_keyword` | 仅含图片同时匹配 `keywords` 时拦截 | 默认，精度最高 |
| `block_pure_image` | 额外拦截无文字纯图片 | 较严格，减少广告图片 |
| `block_all_images` | 拦截所有含图片的消息 | 最严格，不适合大多数场景 |

---

### `filter.contact`

```json
"contact": {
  "enabled": true,
  "patterns": {
    "phone": "1[3-9]\\d{9}",
    "qq": "(?<!\\d)[1-9]\\d{8,9}(?!\\d)",
    "wechat": "wxid_[a-z0-9]+",
    "email": "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}"
  },
  "keywords": [
    "飞书", "续费", "费用", "VX", "v:", "钉钉", "联系人",
    "我的Q", "我的V", "联系我", "加好友", "私聊我", "加我"
  ]
}
```

| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `enabled` | bool | `true` | 是否启用联系方式过滤 |
| `patterns` | object | 4 条正则 | 正则匹配模式（key=名称，value=正则字符串） |
| `keywords` | string[] | — | 关键词黑名单 |

**内置正则说明**：

| 名称 | 正则 | 匹配内容 | 限制 |
|------|------|---------|------|
| `phone` | `1[3-9]\d{9}` | 手机号（13-19 号段，11 位） | — |
| `qq` | `(?<!\d)[1-9]\d{8,9}(?!\d)` | QQ 号（8-10 位纯数字） | ⚠️ 群号白名单豁免 |
| `wechat` | `wxid_[a-z0-9]+` | 微信号原始 ID | — |
| `email` | RFC 5322 邮箱 | 标准邮箱格式 | — |

**QQ 群号白名单豁免**：

当消息中包含以下词之一，且匹配到的数字 >= 8 位时，**不触发 QQ 号拦截**：

> `群` `加群` `群号` `频道` `channel` `guild` `进群`

避免将正常的群号分享误判为私人 QQ 号。

---

### `filter.log_only`

```json
"log_only": false
```

| 项目 | 说明 |
|------|------|
| 类型 | bool |
| 默认 | `false` |
| 作用 | `true` 时所有过滤仅记录日志，不拦截消息 |
| 用途 | 先观察过滤效果再决定开启 |

- `false`（默认）：命中过滤规则则拦截消息
- `true`：命中过滤规则仅记录，消息正常转发

---

### `forward`

```json
"forward": {
  "duplicate_window": 5,
  "send_interval": 1.0
}
```

| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `duplicate_window` | int | `5` | 消息去重窗口（秒）。相同群+相同内容在此时间内重复收到则丢弃 |
| `send_interval` | float | `1.0` | 单群发送间隔（秒）。防止对同一目标群发送过快触发风控 |

---

---

## 企业微信转发配置

### `wecom_enabled`

```json
"wecom_enabled": true
```

| 项目 | 说明 |
|------|------|
| 类型 | bool |
| 默认 | `true` |
| 作用 | 启用/禁用企业微信转发功能 |

---

### `wecom_mode`

```json
"wecom_mode": "ui"
```

| 项目 | 说明 |
|------|------|
| 类型 | string |
| 默认 | `"api"` |
| 可选值 | `"api"` — 通过 Webhook Key 发送；`"ui"` — 操控企微桌面端发送 |

模式对比：

| 模式 | 发送方式 | 必填字段 | 依赖 |
|------|---------|---------|------|
| API | 企微 Webhook API | key | 网络连接 |
| UI | 键盘模拟发送 | name | 企微桌面端 + pywin32 |

---

### `wecom_bots`

```json
"wecom_bots": [
  {
    "key": "xxxxxxxx",
    "name": "群名称",
    "source_groups": ["111111"]
  }
]
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| key | string | 仅 API 模式 | 企微机器人 Webhook Key，支持全链接或裸 key |
| name | string | 仅 UI 模式 | 企微群名称，用于 UI 模式下搜索群聊天 |
| source_groups | string[] | 否 | 来源 QQ 群 ID 列表，空列表表示全部转发 |

注意：API 模式下 key 为必填，UI 模式下 name 为必填。另一字段可为空。

## 完整示例

```json
{
  "robot_qq": [10001, 10002],
  "forward_rules": {
    "111111": {
      "targets": ["222222", "333333"],
      "note": "主群 → 分群A/B"
    }
  },
  "llbot_token": "my_secret_token",
  "filter": {
    "qrcode": {
      "enabled": true,
      "keywords": ["加我", "扫码", "微信"],
      "mode": "block_pure_image",
      "decode_enabled": true,
      "decode_timeout": 3,
      "decode_cache_seconds": 86400,
      "decode_block_patterns": ["兼职", "刷单"],
      "decode_suspicious_domains": ["bad.com"]
    },
    "contact": {
      "enabled": true,
      "patterns": {
        "phone": "1[3-9]\\d{9}",
        "qq": "(?<!\\d)[1-9]\\d{8,9}(?!\\d)",
        "wechat": "wxid_[a-z0-9]+",
        "email": "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}"
      },
      "keywords": ["私聊我", "加好友"]
    },
    "log_only": false
  },
  "forward": {
    "duplicate_window": 5,
    "send_interval": 1.0
  },
  "wecom_enabled": true,
  "wecom_mode": "api",
  "wecom_bots": [
    {
      "key": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
      "name": "群名称",
      "source_groups": ["111111"]
    }
  ]
}
```
