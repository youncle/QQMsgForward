@echo off
chcp 65001 >nul
title QQForward — 构建脚本
cd /d "%~dp0"

echo ====================================
echo   QQForward 一键安装包 — 构建
echo ====================================
echo.

:: ===== 预检查 =====
where python >nul 2>&1 || (echo [错误] 未找到 Python & pause & exit /b 1)
where pyinstaller >nul 2>&1 || (echo [错误] 未找到 PyInstaller，请先 pip install pyinstaller & pause & exit /b 1)
where 7z >nul 2>&1 || (echo [错误] 未找到 7-Zip，请先安装并加入 PATH & pause & exit /b 1)

:: ===== [1/5] 清理旧产物 =====
echo [1/5] 清理旧构建产物 ...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist QQForward rmdir /s /q QQForward
if exist QQForward.spec del QQForward.spec
if exist QQForward.7z del QQForward.7z
if exist sfx_config.txt del sfx_config.txt
echo    清理完成

:: ===== [2/5] 生成图标（如缺失） =====
if not exist app.ico (
    echo [2/5] 生成 app.ico ...
    python -c "from tray import _save_icon_file; _save_icon_file('app.ico')"
) else (
    echo [2/5] app.ico 已存在，跳过
)

:: ===== [3/5] PyInstaller 打包 =====
echo [3/5] PyInstaller 打包 QQForward.exe ...
pyinstaller --onefile --windowed --icon=app.ico --name QQForward --clean ^
    --hidden-import pystray ^
    --hidden-import PIL ^
    --hidden-import flask ^
    --hidden-import requests ^
    tray.py

if %errorlevel% neq 0 (
    echo [错误] PyInstaller 打包失败
    pause
    exit /b 1
)
echo    打包完成: dist\QQForward.exe

:: ===== [4/5] 准备打包目录 =====
echo [4/5] 准备打包目录 ...
mkdir QQForward
copy dist\QQForward.exe QQForward\ >nul
xcopy /E /I /Q LLBot-CLI-Win-x64 QQForward\LLBot-CLI-Win-x64 >nul
copy libiconv.dll QQForward\ >nul
copy libzbar-64.dll QQForward\ >nul
copy msvcr120.dll QQForward\ >nul
if exist config.json copy config.json QQForward\ >nul
echo    打包目录已就绪

:: ===== [5/5] 7-Zip SFX 打包 =====
echo [5/5] 7-Zip SFX 打包 ...

:: 生成 SFX 配置文件
(
echo ;!@Install@!UTF-8!
echo Title="QQ消息转发"
echo BeginPrompt="即将安装 QQ消息转发 到当前目录。继续？"
echo ExecuteFile="QQForward\\QQForward.exe"
echo ;!@InstallEnd@!
) > sfx_config.txt

:: 先用 7z 压缩为 .7z
7z a -mx=9 -mfb=273 -ms=on -mmt=on QQForward.7z QQForward\ >nul

:: 查找 7-Zip SFX 模块（7-Zip 26.x 自带 7z.sfx）
set "SFX_MODULE="
if exist "%ProgramFiles%\7-Zip\7z.sfx" set "SFX_MODULE=%ProgramFiles%\7-Zip\7z.sfx"
if exist "%ProgramFiles(x86)%\7-Zip\7z.sfx" set "SFX_MODULE=%ProgramFiles(x86)%\7-Zip\7z.sfx"
if "%SFX_MODULE%"=="" (
    echo [错误] 未找到 7z.sfx，请确认 7-Zip 已安装
    pause
    exit /b 1
)

:: 拼接 SFX 模块 + 配置 + 压缩包
copy /b "%SFX_MODULE%" + sfx_config.txt + QQForward.7z QQForward_Setup.exe >nul

echo    打包完成: QQForward_Setup.exe

:: ===== [6/6] 清理 =====
echo [6/6] 清理中间产物 ...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist QQForward rmdir /s /q QQForward
if exist QQForward.spec del QQForward.spec
if exist QQForward.7z del QQForward.7z
if exist sfx_config.txt del sfx_config.txt
echo    清理完成

echo.
echo ====================================
echo   ✅ 构建完成
echo.
echo   输出: QQForward_Setup.exe
echo ====================================
echo.
pause
