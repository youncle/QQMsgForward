# QQMsgForward 构建指南

## 环境要求
- Python 3.9+
- PyInstaller：pip install pyinstaller
- 7-Zip（需加入 PATH）

## 构建

```bat
scripts\build.bat
```

输出：output\QQMsgForward_Setup.exe

## 打包内容

解压后目录：

```
QQMsgForward.exe              主程序
resources/app.ico             图标
runtime/LLBot-CLI-Win-x64/    LLBot 运行时（不含 logs/）
runtime/*.dll                 pyzbar 依赖 DLL
```

> config/、scripts/ 不包含在安装包中，首次运行向导自动生成配置。

## 构建流程

1. PyInstaller 打包 main.py -> QQMsgForward.exe
2. 准备 staging 目录（单层 QQMsgForward/ 前缀）
3. robocopy 复制 runtime/（排除 logs/ 目录）
4. 复制 DLL、图标
5. 7z 压缩 + SFX 自解压模块拼接
6. 清理中间产物

## 目录结构

```
QQMsgForward/
|-- main.py              # 入口
|-- requirements.txt     # 依赖
|-- src/                 # Python 源码（7 个模块）
|-- config/              # 运行时配置（打包不含）
|-- runtime/             # LLBot + DLL
|-- resources/           # 图标
|-- scripts/             # 构建/启动/停止脚本
|-- docs/                # 文档
|-- logs/                # 日志（自动创建）
+-- output/              # 构建产物
```
