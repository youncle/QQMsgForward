## Context

当前项目使用 pystray 系统托盘，菜单仅有"查看状态"和"关闭服务"。配置需手动编辑 `config.json`。查看状态用 PowerShell 弹窗，因缺少 `System.Windows.Forms` 程序集加载而闪退。

## Goals / Non-Goals

**Goals:**
- 修复查看状态弹窗（tkinter.messagebox 替代 PowerShell）
- 托盘菜单增加"打开设置"
- 设置窗口可视化编辑：转发规则、QR 码过滤、联系方式过滤
- 保存直接写入 config.json

**Non-Goals:**
- 不支持高级正则语法引导（用户可直接编辑 config.json）
- 不做实时预览（改动范围小）
- 不打包 exe

## Decisions

### 1. tkinter 而非其他 GUI 框架

tkinter 是 Python 标准库，已在用户机器上（Python 安装时自带）。PyQt/wxPython 需额外安装且体积大。

### 2. 设置窗口结构

```
┌────────────────────────────────────────┐
│ QQ消息转发 - 设置                 □ X  │
├────────────────────────────────────────┤
│ ▎ 转发规则                             │
│  源群  [___________]                   │
│  目标群 [___________] [＋添加] [－删除] │
│  [ 列表 ]                              │
│                                        │
│ ▎ QR码过滤  [✓ 启用]                   │
│  关键词   [__________]                  │
│  [✓] 拦截无文字的纯图片                 │
│                                        │
│ ▎ 联系方式过滤  [✓ 启用]               │
│  关键词   [__________]                  │
│  [ ] 仅记录不拦截（log_only）           │
│                                        │
│           [ 保存 ]  [ 取消 ]            │
└────────────────────────────────────────┘
```

### 3. 保存策略

点击"保存"→ 直接写回 `config.json`。转发规则和过滤开关立即生效（forward.py 每次 webhook 从模块变量读取，但 config.json 在模块加载时读取一次）。为支持热生效，需让 forward.py 在每次请求时重新读取或提供 reload 端点。当前方案：保存后提示"配置已保存，重启服务后生效"。

## Risks / Trade-offs

- tkinter 窗口在 pystray 事件线程中打开 → 用 `root.after()` 避免阻塞
- config.json 写入期间崩溃 → 用 `json.dump` 原子写入（先写临时文件再 rename）
