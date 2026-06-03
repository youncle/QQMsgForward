# 企微状态检测优化 — 进程名替代窗口类名

## 背景

当前代码中对企业微信（企微）的窗口查找硬编码了类名 `WeChatWorkMainFrameForPC`，但实际企微窗口类名为 `WeWorkWindow`（进程名 `WXWork.exe`）。导致：

- **状态标签页**：企微明明已打开，却显示橙色"企微未启动"
- **UI 转发引擎**：`_ensure_window()` 虽然后备通过标题 `"企业微信"` 查找到，但类名匹配第一条失效

## 方案

### 核心理念

- **状态标签页**只需知道"企微是否在运行"，用进程名最稳定
- **UI 转发引擎**需要窗口句柄（HWND）来激活和操控，用进程枚举 + 标题 fallback 组合

### 改动文件及具体变更

#### 1. `src/tray.py` — 状态标签页

**位置**：`refresh()` 函数内，企微状态检测部分（当前 L244-253）

**当前代码**（伪）：
```python
_hwnd = ctypes.windll.user32.FindWindowW("WeChatWorkMainFrameForPC", None)
if _hwnd:
    wecom_status.config(text="UI 模式 (企微运行中)", foreground="green")
else:
    wecom_status.config(text="UI 模式 (企微未启动)", foreground="orange")
```

**改为**：
```python
# 进程名查找 WXWork.exe
import psutil
_wecom_running = any(
    p.info["name"] == "WXWork.exe"
    for p in psutil.process_iter(["name"])
)
if _wecom_running:
    wecom_status.config(text="UI 模式 (企微运行中)", foreground="green")
else:
    wecom_status.config(text="UI 模式 (企微未启动)", foreground="orange")
```

若不想新增 `psutil` 依赖，可用 `subprocess` + `tasklist`：
```python
import subprocess
_output = subprocess.run(
    ["tasklist", "/fi", "IMAGENAME eq WXWork.exe"],
    capture_output=True, text=True
)
_wecom_running = "WXWork.exe" in _output.stdout
```

**建议用 `subprocess` 方式**，零依赖。

#### 2. `src/wecom_ui.py` — UI 转发引擎

**位置**：`_ensure_window()` 方法（当前约 L190）

**当前逻辑**：
1. `FindWindowW("WeChatWorkMainFrameForPC", None)`
2. 失败 → `FindWindowW(None, "企业微信")` ← 实际靠这条工作

**改为**：
1. `FindWindowW("WeWorkWindow", None)` ← 修正为真实类名
2. 失败 → `FindWindowW(None, "企业微信")` ← 标题 fallback 保留

### 影响范围

| 维度 | 说明 |
|------|------|
| 功能 | 无变化，UI 转发原本就靠标题 fallback 在工作，现在只是修复显示 |
| 性能 | 可忽略，status refresh 每 5 秒才运行一次 |
| 依赖 | `tray.py` 用 `subprocess` 方式零新增依赖；`wecom_ui.py` 纯 ctypes 不变 |

### 验证方法

1. 企微打开 → 状态标签显示"UI 模式 (企微运行中)" (绿色)
2. 企微关闭 → 状态标签显示"UI 模式 (企微未启动)" (橙色)
3. 企微打开时有消息触发 → UI 引擎正常激活窗口并发送

### 回滚

两颗改动的代码位置各自独立，恢复原文即可。
