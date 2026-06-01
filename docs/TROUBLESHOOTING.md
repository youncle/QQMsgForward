# 常见问题排查

---

## 1. 托盘图标不出现 / 启动后没反应

**可能原因**：Python 环境问题或 LLBot 启动失败

**排查步骤**：

1. 打开命令行，手动运行 `python main.py` 观察控制台输出
2. 检查 `logs/forward.log` 中是否有错误信息
3. 确认 `runtime/LLBot-CLI-Win-x64/` 目录存在且完整
4. 确认 Python 版本 >= 3.9
5. 确认所有依赖已安装：`pip install -r requirements.txt`
6. 检查 3000/9090 端口是否被其他程序占用：
   ```bat
   netstat -ano | findstr :3000
   netstat -ano | findstr :9090
   ```

---

## 2. 服务状态显示红色 / 黄色

托盘图标状态含义：

| 颜色 | 含义 |
|------|------|
| 🟢 绿色 | 全部正常（LLBot + Flask 均在线） |
| 🟡 黄色 | 部分异常（某个 LLBot 未响应） |
| 🔴 红色 | 服务离线（Flask 或全部 LLBot 离线） |

打开配置面板 → **状态** 标签页查看每个端口的运行状态。确认 QQNT 桌面客户端已登录。

---

## 3. 消息没有转发到目标群

**按以下顺序排查**：

1. **确认转发规则**：打开配置面板 → **转发** 标签页，检查源群和目标群 ID 是否正确
2. **确认机器人号**：`config.json` 中的 `robot_qq` 是已在目标群中的 QQ 号
3. **确认机器人入群**：机器人 QQ 号必须在目标群中，否则 API 会返回错误
4. **查看日志**：`logs/forward.log` 搜索 `转发成功` 或 `转发超时` 或 `API 处理失败`
5. **检查过滤**：试运行模式 `log_only` 不会拦截但日志中会记录 `[FILTER] 仅记录`
6. **检查去重**：同一内容在 5 秒内收到两次会被去重，检查日志中 `重复消息`

---

## 4. 过滤误拦了正常消息

**分情况处理**：

### QR 码过滤误拦

- 降低过滤模式：`image_with_keyword` → 最宽松，需图片+关键词同时命中
- 减少 `keywords` 列表中的敏感词
- 关闭 QR 码解码：`filter.qrcode.decode_enabled = false`

### 联系方式过滤误拦

- **QQ 号误拦**：检查消息是否包含群号分享（如"加群 xxx"），系统已有群号白名单豁免，如果仍误拦，检查 `QQ_CONTEXT_WHITELIST` 是否覆盖了上下文关键词
- **手机号误拦**：可以调整 `patterns.phone` 正则或关闭 `filter.contact.enabled`
- 先开启 `log_only = true` 观察一段时间，确认规则准确后再开启拦截

---

## 5. QR 码解码不工作 / pyzbar 报错

**已知原因**：

1. **DLL 缺失**：`runtime/` 目录下缺少 `libiconv.dll`、`libzbar-64.dll`、`msvcr120.dll` 之一
   - 从正常安装的 Visual C++ Redistributable 或 ZBar 项目中获取
2. **pyzbar 未安装**：`pip install pyzbar`
3. **降级机制**：系统检测到 pyzbar 无法加载会自动降级，使用关键词匹配方案替代
4. **日志提示**：打开 `log_only = true` 查看是否有 `[QR解码]` 相关记录

---

## 6. "端口已被占用" 错误

**原因**：上一次运行未正常退出，LLBot 或旧实例残留

**解决方法**：

1. 双击 `stop.vbs` 强制清理
2. 手动查杀：
   ```bat
   taskkill /f /im llbot.exe
   taskkill /f /im pythonw.exe
   ```
3. 或手动释放端口：
   ```bat
   netstat -ano | findstr :3000
   taskkill /f /pid <找到的PID>
   ```
4. 如反复出现，检查 3000-3010 端口是否有其他服务占用

系统在启动时已自动执行以上第 1 步，若仍失败则需手动介入。

---

## 7. 多机器人只有部分生效

**可能原因**：

1. **QQ 未登录**：启动探测时部分机器人 QQ 未登录
   - 检查日志中登录探测结果
   - 启动后手动在 QQNT 中登录，然后重启服务
2. **多实例目录缺失**：`runtime/LLBot-CLI-Win-x64-2/` 可能被手动删除
   - 系统会自动复制，但如果手动干预过可能不一致
3. **端口冲突**：3001/3002 等端口被其他程序占用
   - 使用 `netstat -ano | findstr :3001` 检查

---

## 8. 如何查看日志定位问题

日志文件：`logs/forward.log`

```bat
REM 查看最新 50 行
powershell -Command "Get-Content logs\forward.log -Tail 50"

REM 实时追踪
powershell -Command "Get-Content logs\forward.log -Wait"

REM 搜索关键信息
Select-String -Path logs\forward.log -Pattern "ERROR|FATAL|失败|异常|超时"
```

日志级别说明：

| 级别 | 颜色 | 含义 |
|------|------|------|
| INFO | 正常 | 常规运行日志（转发成功/心跳） |
| WARNING | ⚠️ | 可恢复的错误（API 失败切换） |
| ERROR | ❌ | 严重错误（所有 API 失败） |
| FATAL | 💀 | 致命错误（Flask 崩溃） |

---

## 9. 如何恢复出厂配置

```bat
REM 1. 停止服务
scripts\stop.vbs

REM 2. 删除配置（下次启动走向导）
del config\config.json

REM 3. 清理窗口状态（可选）
del config\.window_state.json

REM 4. 清理日志（可选）
rmdir /s /q logs

REM 5. 重启
scripts\start.vbs
```

---

## 10. 构建时 PyInstaller 失败

**常见错误及解决**：

| 错误信息 | 原因 | 解决 |
|---------|------|------|
| `Failed to execute script main` | `--paths src` 未设置 | 确保构建命令包含 `--paths src` |
| `ModuleNotFoundError: No module named 'pystray'` | 缺少 `--hidden-import` | 添加 `--hidden-import pystray` |
| `unable to find 7z.exe` | 7-Zip 未安装或不在 PATH | 安装 7-Zip 或手动添加 PATH |
| `unable to find 7z.sfx` | 7-Zip SFX 模块路径错误 | 确认 7z.sfx 在 7-Zip 安装目录下 |
| `*.spec` 文件冲突 | 上次构建残留 | 手动删除 `QQMsgForward.spec` |

---

## 11. WebUI 无法访问

- 默认地址：`http://127.0.0.1:3080`
- 多机器人：端口递增 3080、3081、3082...
- 默认密码：`llbot@forward123`
- 确认 LLBot 已启动（托盘状态绿色）
- 确认 WebUI 端口未被防火墙拦截

---

## 12. 关闭服务时提示 "无法停止"

**原因**：`stop.vbs` 的优雅关闭等待 15 秒后自动转为强制终止

**手动强制终止**：

```bat
taskkill /f /im llbot.exe
taskkill /f /im pythonw.exe
taskkill /f /im QQMsgForward.exe
del .shutdown.flag
```

---

## 仍需帮助？

- 检查 `logs/forward.log` 获取详细错误信息
- 确认 `config/config.json` 格式正确（JSON 语法）
- 在 GitHub 项目页面提交 Issue 并附上日志
