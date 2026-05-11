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
if exist output rmdir /s /q output
echo    清理完成

:: ===== [2/5] PyInstaller 打包 =====
echo [2/5] PyInstaller 打包 QQForward.exe ...
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

:: ===== [3/5] 准备打包目录 =====
echo [3/5] 准备打包目录 ...
mkdir output\QQForward
copy dist\QQForward.exe output\QQForward\ >nul
xcopy /E /I /Q LLBot-CLI-Win-x64 output\QQForward\LLBot-CLI-Win-x64 >nul
echo    打包目录已就绪

:: ===== [4/5] 7-Zip SFX 打包 =====
echo [4/5] 7-Zip SFX 打包 ...

:: 生成 SFX 配置文件
(
echo ;!@Install@!UTF-8!
echo Title="QQ消息转发"
echo BeginPrompt="即将安装 QQ消息转发 到当前目录。继续？"
echo ExecuteFile="QQForward.exe"
echo ;!@InstallEnd@!
) > output\sfx_config.txt

:: 先用 7z 压缩为 .7z
cd output
7z a -mx=9 -mfb=273 -ms=on -mmt=on QQForward.7z QQForward\ >nul

:: 下载 7-Zip SFX 模块（如果没有）
if not exist "..\7zS.sfx" (
    echo    正在下载 7-Zip SFX 模块...
    powershell -Command "Invoke-WebRequest -Uri 'https://7-zip.org/a/7z2408-extra.7z' -OutFile '7z_extra.7z'"
    7z e 7z_extra.7z 7zS.sfx -aoa >nul
    copy 7zS.sfx ..\7zS.sfx >nul
    del 7zS.sfx 7z_extra.7z
)

:: 拼接 SFX 模块 + 配置 + 压缩包
copy /b "..\7zS.sfx" + sfx_config.txt + QQForward.7z "..\QQForward_Setup.exe" >nul
cd ..

echo    打包完成: QQForward_Setup.exe

:: ===== [5/5] 完成 =====
echo [5/5] 完成！
echo.
echo ====================================
echo   ✅ 构建完成
echo.
echo   输出: QQForward_Setup.exe
echo ====================================
echo.
pause
