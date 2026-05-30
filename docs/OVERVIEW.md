# QQMsgForward 项目全库解剖
## 一、项目定位
基于 **LLOneBot v7.11.4** 开发的 QQ 群消息实时转发系统，采用**Python 胶水层 + Node.js 运行时（llbot.exe）** 架构，两端通过 **OneBot v11 HTTP POST** 协议完成数据交互，支持多 QQ 机器人实例并行、消息过滤、群消息转发全流程管控。

## 二、整体架构总览
```
┌──────────────────────────────────────────────────┐
│                用户视角 (End User)                 │
│  start.vbs ──▶ pythonw tray.py                    │
│  tray.py ──▶ 系统托盘 + Splash 启动画面            │
│              ├── 启动 N 个 LLBot 实例 (多QQ)        │
│              ├── 启动 Flask 转发服务 (port 9090)    │
│              └── tkinter 设置面板 (3 个 Tab)        │
└──────────────────────┬───────────────────────────┘
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
    LLBot-1        LLBot-2       LLBot-N
    (QQ A)         (QQ B)        (QQ C)
    port 3000      port 3001     port 3002+N
    WebUI 3080     WebUI 3081    WebUI 3080+N
       │               │            │
       └───────────────┼────────────┘
                       │ HTTP POST /webhook
                       ▼
              Flask Forward Service
              port 9090 (forward.py)
                       │
         ┌─────────────┼─────────────┐
         ▼             ▼             ▼
    目标群1         目标群2        目标群N
```

## 三、文件地图与核心职责
| 文件/目录 | 代码体量 | 核心职责 |
| ---- | ---- | ---- |
| `tray.py` | ~746 行 | 项目主入口、全生命周期管理；多 LLBot 启停、托盘图标、启动动画、配置窗口、Flask 守护线程、配置持久化、快捷方式管理 |
| `forward.py` | ~239 行 | 消息转发核心引擎；WebHook 接收、消息去重、群限流、API 轮询、消息重发重试 |
| `filter.py` | ~171 行 | 消息过滤引擎；二维码拦截、联系方式正则检测、群白名单豁免 |
| `qr_decoder.py` | ~170 行 | 二维码解析；图片拉取、pyzbar 解码、LRU 缓存、域名风险识别 |
| `settings.py` | ~319 行 | 可视化配置面板；转发规则、过滤规则 CRUD、配置原子化保存 |
| `wizard.py` | ~210 行 | 首次启动配置向导；4 步引导、模板配置自动生成 |
| `splash.py` | ~78 行 | 启动进度浮窗；无边框动画、暗色主题进度条 |
| `config.json` | - | 全局运行配置（机器人、转发规则、过滤、限流等） |
| `build.bat` | - | 项目打包脚本；PyInstaller 编译 + 7-Zip 制作自解压包 |
| `install.bat` | - | 客户端一键安装；权限提权、依赖安装、环境清理、快捷方式创建 |
| `start.vbs` | - | 一键启动脚本；权限提权、残留清理、拉起主程序 |
| `stop.vbs` | - | 一键停止脚本；优雅关闭标记、进程终止、临时目录清理 |
| `runtime/LLBot-CLI-Win-x64/` | - | LLOneBot v7.11.4 运行时（Node.js + 协议组件） |

## 四、核心业务流程
### 4.1 启动链路
```
start.vbs
  └─▶ 管理员权限提权
       └─▶ pythonw tray.py
            ├─▶ 加载 Splash 启动进度窗
            ├─▶ 查杀占用端口的残留进程
            ├─▶ 校验 config.json，缺失则唤起配置向导
            ├─▶ 循环启动多 LLBot 实例
            │   ├─▶ 主实例：直接使用原目录
            │   ├─▶ 多实例：复制目录生成独立运行目录
            │   ├─▶ 动态注入端口、WebHook、Token 配置
            │   ├─▶ 无窗口拉起 llbot.exe
            │   └─▶ 主动轮询 /get_login_info 检测当前 QQ 登录状态，确认登录后再启动下一个实例(每端口最多等 60s)
            ├─▶ 轮询检测端口，等待剩余 LLBot 服务就绪
            ├─▶ 后置全量探测：遍历各端口调用 /get_login_info，获取真实 QQ→端口映射，覆盖写入 llbot_apis
            ├─▶ 后台守护线程启动 Flask 转发服务(9090)
            └─▶ 初始化系统托盘 + 主配置窗口
```

### 4.2 消息转发流水线
```
QQ 群消息
  └─▶ LLBot 触发 OneBot 回调 → POST 127.0.0.1:9090/webhook
       └─▶ forward.py 接收 WebHook 请求
            ├─▶ 过滤：仅处理群聊消息、屏蔽机器人自身消息（防循环）
            ├─▶ 匹配预设转发规则
            ├─▶ 5 秒短时去重缓存，拦截重复消息
            ├─▶ 调用 filter.py 执行多层内容过滤
            │   ├─▶ 二维码解码 + 风险识别
            │   ├─▶ 图片拦截规则校验
            │   └─▶ 手机号/QQ/微信/邮箱 正则拦截
            ├─▶ 试运行模式判断（仅日志/直接拦截）
            ├─▶ 智能选择发送机器人 + 群级 1s 限流
            └─▶ 3 次重试(间隔0.5s)，失败则记录日志
```

### 4.3 关闭链路
```
stop.vbs / 托盘【关闭服务】
  └─▶ 写入 .shutdown.flag 停止标记
       └─▶ 后台监控线程检测标记
            ├─▶ 执行服务关闭逻辑
            │   ├─▶ 批量查杀 node.exe / llbot.exe / QQ 相关进程
            │   ├─▶ 删除多实例临时目录
            │   └─▶ 销毁托盘图标
            └─▶ 关闭主窗口，程序退出
```

## 五、通信协议细节
### 5.1 LLBot → 转发服务（入站）
- 请求地址：`http://127.0.0.1:9090/webhook`
- 请求方式：`HTTP POST`
- 数据格式：**标准 OneBot v11 结构体**（数组格式消息，非 CQ 字符串）
- 关键字段：`post_type`、`message_type`、`group_id`、`sender.user_id`、`raw_message`、`message[]`

### 5.2 转发服务 → LLBot（出站）
- 请求地址：`http://127.0.0.1:{port}/send_group_msg`
- 请求方式：`HTTP POST`
- 请求体：
  ```json
  {"group_id": 群号, "message": 消息内容}
  ```
- 请求头：`Authorization: Bearer {token}`（开启鉴权时）
- 重试策略：仅针对 **HTTP 5xx** 错误重试，共 3 次，重试间隔 0.5s

## 六、配置系统（config.json）
### 主配置结构
```json
{
  "robot_qq": [],               // 机器人QQ列表，决定实例数量
  "forward_rules": {},          // 转发规则：{源群号: {targets:[目标群], note:"备注"}}
  "llbot_apis": {},             // 运行时探测生成：{QQ号: API地址}（启动后通过 GET /get_login_info 获取真实映射）
  "llbot_token": "",            // LLBot API 鉴权Token
  "filter": {                   // 过滤规则
    "qrcode": {                 // 二维码过滤
      "mode": "",               // 三种模式：image_with_keyword / block_pure_image / block_all_images
      "decode_enabled": true,   // 二维码解码总开关
      "decode_timeout": 2,      // 图片下载超时(秒)
      "decode_block_patterns":[],// 解码内容拦截关键词
      "decode_suspicious_domains":[] // 风险域名黑名单
    },
    "contact": {                // 联系方式过滤
      "patterns": {             // 正则规则：手机/QQ/微信/邮箱
        "phone":"", "qq":"", "wechat":"", "email":""
      },
      "keywords": []            // 敏感话术关键词
    },
    "log_only": false           // 试运行模式：仅记录、不拦截
  },
  "forward": {
    "duplicate_window": 5,      // 消息去重窗口(秒)
    "send_interval": 1.0        // 群消息发送限流间隔(秒)
  }
}
```
- 历史兼容：`config.xxx.json` 为单机器人旧版配置文件，仅作备份。

## 七、多实例管理规则
### 7.1 目录与端口映射
| 实例序号 | 运行目录 | HTTP API 端口 | WebUI 端口 |
| ---- | ---- | ---- | ---- |
| 0 | runtime/LLBot-CLI-Win-x64 | 3000 | 3080 |
| 1 | runtime/LLBot-CLI-Win-x64-2 | 3001 | 3081 |
| 2 | runtime/LLBot-CLI-Win-x64-3 | 3002 | 3082 |
| N | runtime/LLBot-CLI-Win-x64-(N+1) | 3000+N | 3080+N |

### 7.2 消息发送策略
优先使用**接收消息的同机器人**发送；若该机器人不在目标群，自动轮询其他可用机器人 API。

QQ→端口映射通过启动时 `GET /get_login_info` 探测获得，不再依赖 `robot_qq` 数组的索引顺序。

## 八、多层过滤系统
### 拦截判断逻辑
1. **二维码解析层**（依赖 pyzbar）
   - 解码内容命中风险关键词 / 风险域名
   - 二维码内嵌手机号、QQ、邮箱等联系方式
2. **图片规则层**（三模式互斥）
   - `image_with_keyword`(默认)：图片+敏感关键词 拦截
   - `block_pure_image`：额外拦截纯图片消息
   - `block_all_images`：拦截全部图片消息
3. **联系方式检测层**
   - 文本关键词匹配（加我、私聊等）
   - 正则匹配手机号/QQ/微信/邮箱
   - 上下文豁免：含「群、群号、频道」等词，跳过 QQ 检测
4. **试运行开关**
   - `log_only=true`：仅打印日志，不执行拦截

## 九、异常与安全处理
| 异常场景 | 处理方案 |
| ---- | ---- |
| 端口占用 | 启动前查杀对应端口进程 |
| 配置文件损坏 | 弹窗提示，唤起配置向导 |
| LLBot 运行目录缺失 | 弹窗报错，直接退出程序 |
| 机器人未登录 | 弹窗提醒，服务继续运行 |
| API 转发失败 | 自动切换下一个机器人 API |
| HTTP 5xx 服务异常 | 3 次重试，指数退避间隔 |
| Flask 服务崩溃 | 后台日志记录致命错误 |
| pyzbar 依赖缺失 | 优雅降级，关闭二维码解码功能 |
| 日志管理 | 按天轮转日志，最多保留 2 份 |

## 十、版本迭代脉络（Git Commit 摘要）
1. **早期构建**：基础打包、冗余文件清理、UI 操作提示优化
2. **调试优化**：移除冗余调试日志、临时变量监控（后回滚）
3. **UI 问题修复**：修复 ttk Checkbutton 内存回收 Bug、控件状态绑定迭代、窗口尺寸与样式调优
4. **性能优化**：修复定时器泄漏、降低 CPU 占用、接入日志轮转
5. **启动体验**：统一启动流程、完善 Splash 动画规范
6. **后期运维**：新增多机器人配置、端口优化、正式打包准备
7. **登录探测**：改实例间硬等待为主动轮询登录状态；新增后置全量探测，运行时发现真实 QQ→端口映射；状态页改用 llbot_apis 反向索引展示
