@echo off
chcp 65001 >nul
title QQ消息转发 — 一键安装
cd /d "%~dp0"

:: ===== 自动提权到管理员 =====
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo 正在请求管理员权限...
    mshta vbscript:CreateObject("Shell.Application").ShellExecute("%~s0","","","runas",1)(window.close)
    exit /b
)

echo ====================================
echo   QQ消息转发 — 一键安装
echo ====================================
echo.

:: 1. 检查 Python
echo [1/4] 检测 Python ...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Python，请先安装 Python 3.9+
    echo        下载: https://www.python.org/downloads/
    pause
    exit /b 1
)
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set pyver=%%i
echo    Python %pyver% — 已找到

:: 2. 安装依赖
echo [2/4] 安装 Python 依赖 ...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [警告] pip install 使用了阿里云镜像重试...
    pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
)
echo    依赖安装完成

:: 3. 清理旧日志
echo [3/4] 清理运行时日志文件 ...
if exist forward.log del forward.log
if exist .window_state.json del .window_state.json
if exist "LLBot-CLI-Win-x64\bin\llbot\data\logs" (
    del /q "LLBot-CLI-Win-x64\bin\llbot\data\logs\*.log" 2>nul
)
echo    日志已清理

:: 4. 创建桌面快捷方式
echo [4/4] 创建桌面快捷方式 ...
set VBS=%TEMP%\create_lnk.vbs
set DESKTOP=%USERPROFILE%\Desktop
set START_VBS=%~dp0start.vbs

(
echo Set ws = CreateObject("WScript.Shell")
echo Set sc = ws.CreateShortcut("%DESKTOP%\QQ Forward.lnk")
echo sc.TargetPath = "%START_VBS%"
echo sc.WorkingDirectory = "%~dp0"
echo sc.Description = "QQ消息转发 - 一键启动"
echo sc.Save()
) > "%VBS%"
cscript //Nologo //B "%VBS%"
del "%VBS%"
echo    快捷方式已创建到桌面

echo.
echo ====================================
echo   ✅ 安装完成！
echo.
echo   下一步: 双击桌面「QQ Forward」启动
echo   或双击项目目录下的 start.vbs
echo ====================================
echo.
pause
