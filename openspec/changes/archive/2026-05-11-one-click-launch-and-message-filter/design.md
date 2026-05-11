## Context

当前项目：
- `LLBot-CLI-Win-x64/` — LLOneBot v7.11.4 打包版，提供 QQ 机器人 OneBot v11 HTTP API
- `qq-message-forward.py` — Flask webhook 服务器，接收消息并按规则转发
- `启动/关闭.bat` — bat 批处理，需要右键管理员运行，弹出两个 CMD 黑窗

用户 QQ 机器人号：2776992588，转发规则：源群 1079264158 → 目标群 1087980588, 1080631149

## Goals / Non-Goals

**Goals:**
- 一键启动全部服务（双击一个文件即可），自动获取管理员权限
- 服务后台静默运行，不弹 CMD 黑窗
- 系统托盘图标显示运行状态，提供关闭入口
- 过滤含二维码图片的广告消息
- 过滤含私人联系方式（手机号、QQ号、微信号、邮箱）的消息
- 配置文件与代码分离，方便修改规则

**Non-Goals:**
- 不实现 QR 码图像解码识别（太重且依赖大）
- 不实现 Windows 服务注册
- 不改动 LLBot 自身配置和运行方式
- 不增加消息持久化/数据库

## Decisions

### 1. 启动方式：VBS + 托盘 Python 程序

```
双击 start.vbs
  │ 自动 UAC 提权（Shell.Application.ShellExecute "runas"）
  │
  ├─▶ 静默启动 llbot.exe（wsh.Run 第2参数=0隐藏窗口）
  ├─▶ 等待 LLBot 端口就绪（netstat 轮询 3000 端口）
  ├─▶ 静默启动 pythonw.exe tray.py（后台托盘程序）
  └─▶ 托盘程序负责启动/监控 forward.py

双击 stop.vbs
  │ 自动 UAC 提权
  ├─▶ taskkill llbot.exe 及相关进程
  ├─▶ taskkill python/pythonw 进程（转发脚本+托盘）
  └─▶ 弹窗确认
```

**为什么 VBS 而不是纯 Python 启动器？** VBS 原生支持 `ShellExecute "runas"` 提权，不依赖 Python 环境。如果 Python 未安装，至少在启动阶段就能给出明确错误。

**为什么托盘程序用 Python 而不是 C#/其他？** 开发者已熟悉 Python，`pystray` 库成熟稳定，只需 `pip install pystray pillow`。

### 2. 托盘程序设计

```
┌──────────────────────────────────┐
│  tray.py                         │
│                                  │
│  ┌─ 启动时:                      │
│  │   1. 检查 llbot 3000 端口      │
│  │   2. 启动 forward.py (subprocess)│
│  │   3. 创建托盘图标              │
│  │   4. 开启监控线程(每5秒检查状态)│
│  └─────────────────────────────── │
│  ┌─ 托盘菜单:                     │
│  │   ✓ 服务运行中 (状态指示)      │
│  │   ──────────                   │
│  │   查看状态 → 弹窗显示详情       │
│  │   关闭服务 → 杀子进程 → 退出    │
│  └─────────────────────────────── │
│  ┌─ 退出时:                       │
│  │   1. 终止 forward.py 进程       │
│  │   2. 提示是否同时关闭 LLBot     │
│  │   3. 移除托盘图标               │
│  └─────────────────────────────── │
└──────────────────────────────────┘
```

### 3. 消息过滤架构

```
webhook 消息进入
  │
  ├─▶ filter.py: check_qrcode_ad()
  │     检查消息段中是否有 image 类型
  │     + 上下文关键词匹配（"加我""扫码""联系""VX"等）
  │     → True = 疑似二维码广告
  │
  ├─▶ filter.py: check_contact_info()
  │     正则匹配:
  │     - 手机号: 1[3-9]\d{9}
  │     - QQ号: [1-9]\d{4,11}（排除群号段）
  │     - 微信号: wxid_[a-z0-9]+
  │     - 邮箱: \S+@\S+\.\S+
  │     - 关键词: "加好友""私聊""接单"等
  │     → True = 含联系方式
  │
  ├─▶ 命中任一规则
  │     → 记录日志 "[FILTER] 已拦截: {群号} - {摘要}"
  │     → 不转发（返回 ok 给 LLBot，不调用 send_group_msg）
  │
  └─▶ 未命中 → 正常转发
```

**为什么用"图片+关键词"而非真实 QR 码解码？** QR 码解码需要下载图片 + `pyzbar`（依赖 Visual C++ 运行时，60MB+，安装复杂）。群广告 QR 码几乎都有引导文字，用图片+关键词组合即可拦截 90%+ 的广告。

### 4. 配置文件

将硬编码配置提取到 `config.json`：

```json
{
  "robot_qq": 2776992588,
  "forward_rules": {
    "1079264158": ["1087980588", "1080631149"]
  },
  "llbot_api": "http://127.0.0.1:3000",
  "llbot_token": "",
  "filter": {
    "qrcode": {
      "enabled": true,
      "keywords": ["加我", "扫码", "扫一扫", "联系我", "加好友", "VX", "v:", "微信", "私聊"],
      "mode": "image_with_keyword"
    },
    "contact": {
      "enabled": true,
      "patterns": {
        "phone": "1[3-9]\\d{9}",
        "qq": "[1-9]\\d{4,9}",
        "wechat": "wxid_[a-z0-9]+",
        "email": "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}"
      },
      "keywords": ["我的Q", "我的V", "联系我", "加好友", "私聊我"]
    },
    "log_only": false
  },
  "forward": {
    "duplicate_window": 5,
    "send_interval": 1.0
  }
}
```

## Risks / Trade-offs

- **误杀风险**：QR 码检测用"图片+关键词"可能误拦含关键词但非广告的图片消息 → 给 `filter.log_only` 模式，先观察再启用拦截
- **pystray 依赖**：需要额外 pip install → 在 `config.json` 旁边放 `requirements.txt`
- **托盘程序崩溃**：托盘挂了不影响转发（forward.py 独立运行），下次启动时会自动恢复
- **VBS 被杀软拦截**：部分杀软对 VBS 脚本敏感 → 建议放在信任目录，或提供 .bat 替代方案

## Open Questions

1. 联系方式正则是否需要加白名单？比如允许群主/管理员的联系方式通过？
2. QR 码关键词是否需要支持自定义添加？
