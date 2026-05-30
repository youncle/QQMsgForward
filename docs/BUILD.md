# QQMsgForward 构建指南

## 目录结构
```
QQMsgForward/
├── main.py                 ← 入口
├── src/                    ← Python 源码
│   ├── tray.py             主程序（托盘+生命周期）
│   ├── forward.py          消息转发引擎
│   ├── filter.py           消息过滤
│   ├── qr_decoder.py       二维码解码
│   ├── settings.py         配置面板
│   ├── wizard.py           配置向导
│   └── splash.py           启动动画
├── config/                 ← 配置
├── runtime/                ← 运行时依赖（LLBot + DLL）
├── resources/              ← 静态资源（图标）
├── scripts/                ← 构建/启动/停止脚本
│   ├── build.bat           一键构建
│   ├── start.vbs           启动
│   └── stop.vbs            停止
├── docs/                   ← 文档
├── logs/                   ← 运行时日志（gitignored）
├── output/                 ← 构建产物（gitignored）
├── .gitignore
└── requirements.txt
```

## 环境要求
- Python 3.9+
- PyInstaller：pip install pyinstaller
- 7-Zip：安装后确保 7z.exe 在 PATH 中

## 构建
scripts\build.bat
输出：output\QQMsgForward_Setup.exe

## 打包内容
QQMsgForward_Setup.exe 解压后：
  QQMsgForward.exe          主程序
  config\config.json        配置
  resources\app.ico         图标
  runtime\LLBot-CLI-Win-x64\  LLBot 运行时
  runtime\*.dll             系统 DLL
  scripts\start.vbs         启动脚本
  scripts\stop.vbs          停止脚本
  logs\                     日志目录（自动创建）

## 构建流程
1. PyInstaller 打包 main.py → QQMsgForward.exe
2. 准备 staging 目录（含 QQMsgForward/ 前缀）
3. 复制 runtime/、config/、resources/、scripts/
4. 7z 压缩
5. 7z.sfx + sfx_config + .7z 拼接为 SFX 自解压包
6. 清理中间产物
