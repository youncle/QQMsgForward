# QQMsgForward 构建指南

## 环境要求

| 工具 | 说明 |
|------|------|
| Python 3.9+ | 运行环境 |
| PyInstaller | 打包工具：`pip install pyinstaller` |
| 7-Zip | 自解压模块（`7z.exe` + `7z.sfx`），需加入 PATH 或使用默认安装路径 |

---

## 一键构建

```bat
scripts\build.bat
```

输出：`output\QQMsgForward_Setup.exe`

---

## 构建流程详解

### 第 1 步：清理

删除 `build/`、`dist/`、旧 spec 文件和创建 `output/` 目录。

### 第 2 步：生成图标（可选）

若 `resources/app.ico` 不存在，通过 Python 脚本生成。

### 第 3 步：PyInstaller 打包

```bat
pyinstaller --onefile --windowed --icon=resources\app.ico --name QQMsgForward --clean ^
    --hidden-import pystray --hidden-import PIL --hidden-import flask --hidden-import requests --hidden-import win32com --hidden-import win32clipboard --hidden-import win32con ^
    --paths src main.py
```

| 参数 | 说明 |
|------|------|
| `--onefile` | 单文件 exe |
| `--windowed` | 无控制台窗口（配合 start.vbs 隐藏运行） |
| `--icon` | 应用图标 |
| `--clean` | 清理临时文件 |
| `--hidden-import` | 显式声明 PyInstaller 自动检测不到的依赖 |
| `--paths src` | 将 `src/` 加入模块搜索路径（否则 `import tray` 失败） |

### 第 4 步：准备 Staging 目录

```
QQMsgForward/              ← 7z 包内结构（单层前缀）
├── QQMsgForward.exe       ← PyInstaller 产物
├── runtime/
│   ├── LLBot-Desktop-win-x64/ ← LLBot 运行时（排除 logs/）
│   ├── libiconv.dll       ← pyzbar 依赖
│   ├── libzbar-64.dll     ← pyzbar 依赖
│   └── msvcr120.dll       ← pyzbar 依赖
└── resources/
    └── app.ico            ← 图标
```

> 注意：`config/`、`scripts/`、`docs/` **不包含**在安装包中。`config/` 由首次运行向导生成。

### 第 5 步：7z 压缩 + SFX 拼接

```bat
REM 压缩
7z a -mx=5 -mmt=on QQMsgForward.7z QQMsgForward\*

REM 生成 SFX 配置
echo ;!@Install@!UTF-8! > sfx_config.txt
echo Title=QQMsgForward >> sfx_config.txt
echo BeginPrompt=Install QQMsgForward to current directory? >> sfx_config.txt
echo ;!@InstallEnd@! >> sfx_config.txt

REM 拼接
copy /b 7z.sfx + sfx_config.txt + QQMsgForward.7z output\QQMsgForward_Setup.exe
```

---

## DLL 依赖说明

`runtime/` 目录中的 3 个 DLL 是 `pyzbar` 的依赖：

| DLL | 用途 | 来源 |
|-----|------|------|
| `libiconv.dll` | 字符编码转换（ZBar 依赖） | Visual C++ Redistributable |
| `libzbar-64.dll` | ZBar 条码/QR 码识别核心库 | ZBar Project |
| `msvcr120.dll` | Visual C++ 2013 运行时 | Visual C++ Redistributable |

若环境中已经安装了这些 DLL，`pyzbar` 仍可正常工作。打包时显式复制是为了保证隔离性。

### 企微 UI 模式依赖

企业微信 UI 模式（`wecom_mode: "ui"`）需要以下额外依赖：

| 包 | 用途 |
|---|---|
| pywin32>=306 | 企微窗口激活、SendKeys 键盘模拟、剪贴板操作 |

```bat
pip install pywin32
```

如果不安装，UI 模式将无法发送消息（`HAS_SENDKEYS = False`），建议切换到 API 模式。

---

## 构建产物目录结构（解压后）

```
QQMsgForward/
├── QQMsgForward.exe         # 主程序
├── runtime/
│   ├── LLBot-Desktop-win-x64/   # LLBot 运行时
│   ├── libiconv.dll
│   ├── libzbar-64.dll
│   └── msvcr120.dll
└── resources/
    └── app.ico
```

首次运行后自动生成：

```
├── config/
│   ├── config.json          # 运行配置
│   └── .window_state.json   # 窗口状态
├── logs/
│   └── forward.log          # 运行日志
└── runtime/
    ├── LLBot-Desktop-win-x64-2/ # 多实例（按需复制）
    ├── LLBot-Desktop-win-x64-3/
    └── ...
```

---

## 构建验证

```bat
REM 检查 exe 是否存在且可执行
dir output\QQMsgForward_Setup.exe

REM 检查文件大小（正常约 20-25 MB）
dir output\QQMsgForward_Setup.exe
```
