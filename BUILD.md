# 构建安装包

## 依赖环境

| 工具 | 用途 | 安装方式 |
|------|------|----------|
| Python 3.14 | PyInstaller 打包 | `pip install pyinstaller` |
| PyInstaller 6.20+ | 打包 exe | `pip install pyinstaller` |
| 7-Zip 26.x | SFX 自解压 | [7-zip.org](https://7-zip.org/) |

需在 Windows 环境下构建，生成的安装包仅支持 Win10 1809+。

## 一键构建

```bat
build.bat
```

输出 `QQForward_Setup.exe` (~84MB)，在项目根目录。

## 手动分步构建

### [1/6] 清理旧产物

```bash
rm -rf build dist QQForward QQForward.spec QQForward.7z sfx_config.txt
```

### [2/6] 生成图标（如缺失）

```bash
python -c "from tray import _save_icon_file; _save_icon_file('app.ico')"
```

### [3/6] PyInstaller 打包

```bash
pyinstaller --onefile --windowed --icon=app.ico --name QQForward --clean \
    --hidden-import pystray \
    --hidden-import PIL \
    --hidden-import flask \
    --hidden-import requests \
    tray.py
```

输出：`dist/QQForward.exe`

### [4/6] 准备打包目录

```bash
mkdir -p QQForward
cp dist/QQForward.exe QQForward/
cp -r LLBot-CLI-Win-x64 QQForward/
cp libiconv.dll libzbar-64.dll msvcr120.dll QQForward/
cp config.json QQForward/
```

### [5/6] SFX 自解压打包

```bash
cat > sfx_config.txt << 'EOF'
;!@Install@!UTF-8!
Title="QQ消息转发"
BeginPrompt="即将安装 QQ消息转发 到当前目录。继续？"
ExecuteFile="QQForward\\QQForward.exe"
;!@InstallEnd@!
EOF

7z a -mx=9 -mfb=273 -ms=on -mmt=on QQForward.7z QQForward/

cat "C:/Program Files/7-Zip/7z.sfx" sfx_config.txt QQForward.7z > QQForward_Setup.exe
```

### [6/6] 清理中间产物

```bash
rm -rf build dist QQForward QQForward.spec QQForward.7z sfx_config.txt
```

## 安装包内容

| 文件 | 来源 | 大小 |
|------|------|------|
| `QQForward.exe` | PyInstaller 打包 tray.py | ~24MB |
| `config.json` | 项目配置模板 | 2KB |
| `LLBot-CLI-Win-x64/` | LLOneBot 运行环境 | ~151MB |
| `libiconv.dll` | pyzbar/zbar 依赖 | 0.9MB |
| `libzbar-64.dll` | 二维码解码引擎 | 0.2MB |
| `msvcr120.dll` | VC++ 2013 运行时 | 0.9MB |

## 安装包结构（解压后）

```
QQForward/
├── QQForward.exe
├── config.json
├── libiconv.dll
├── libzbar-64.dll
├── msvcr120.dll
└── LLBot-CLI-Win-x64/
    ├── llbot.exe
    └── bin/
```

## 用户端体验

1. 双击 `QQForward_Setup.exe`，弹出安装确认
2. 确认后解压出 `QQForward/` 文件夹
3. 进入 `QQForward/`，双击 `QQForward.exe` 即可使用
4. 首次启动自动读取 `config.json`，无需额外配置
