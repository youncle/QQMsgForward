@echo off
chcp 65001 >nul
title QQMsgForward Build
cd /d "%~dp0.."
setlocal enabledelayedexpansion

set NAME=QQMsgForward

:: Pre-checks
where python >nul 2>&1 || (echo [ERROR] Python not found & timeout /t 3 >nul & exit /b 1)

where pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    for /f "tokens=*" %%i in ('python -c "import sys; print(sys.executable)"') do set py_exe=%%i
    set "py_site=!py_exe:\python.exe=\Scripts!"
    if exist "!py_site!\pyinstaller.exe" set "PATH=!py_site!;%PATH%"
)
where pyinstaller >nul 2>&1 || (echo [ERROR] PyInstaller not found & timeout /t 3 >nul & exit /b 1)

where 7z >nul 2>&1
if %errorlevel% neq 0 (
    if exist "%ProgramFiles%\7-Zip\7z.exe" set "PATH=%ProgramFiles%\7-Zip;%PATH%"
    if exist "%ProgramFiles(x86)%\7-Zip\7z.exe" set "PATH=%ProgramFiles(x86)%\7-Zip;%PATH%"
)
where 7z >nul 2>&1 || (echo [ERROR] 7-Zip not found & timeout /t 3 >nul & exit /b 1)

:: [1/5] Clean
echo [1/5] Cleaning old builds ...
for %%d in (build dist %NAME% %NAME%.spec %NAME%.7z sfx_config.txt) do (
    if exist %%d\ (rmdir /s /q %%d) else if exist %%d del %%d
)
echo     Done

:: [2/5] Generate icon if missing
if not exist resources\app.ico (
    echo [2/5] Generating app.ico ...
    python -c "import sys; sys.path.insert(0, 'src'); from tray import _save_icon_file; _save_icon_file('resources\\app.ico')"
) else echo [2/5] app.ico exists, skip

:: [3/5] PyInstaller
echo [3/5] PyInstaller ...
pyinstaller --onefile --windowed --icon=resources\app.ico --name %NAME% --clean ^
    --hidden-import pystray --hidden-import PIL --hidden-import flask --hidden-import requests --paths src main.py
if %errorlevel% neq 0 (echo [ERROR] PyInstaller failed & timeout /t 3 >nul & exit /b 1)
echo     OK: dist\%NAME%.exe

:: [4/5] Prepare staging (QQMsgForward\ prefix for 7z)
echo [4/5] Preparing staging ...
mkdir %NAME%\ 2>nul
cd %NAME%
mkdir %NAME% 2>nul
mkdir %NAME%\runtime %NAME%\config %NAME%\resources %NAME%\scripts 2>nul
copy ..\dist\%NAME%.exe %NAME%\ >nul
xcopy /E /I /Q ..\runtime\LLBot-CLI-Win-x64 %NAME%\runtime\LLBot-CLI-Win-x64 >nul
copy ..\runtime\libiconv.dll ..\runtime\libzbar-64.dll ..\runtime\msvcr120.dll %NAME%\runtime\ >nul
copy ..\config\config.json %NAME%\config\ >nul
copy ..\resources\app.ico %NAME%\resources\ >nul
copy ..\scripts\start.vbs ..\scripts\stop.vbs %NAME%\scripts\ >nul
cd ..
echo     Done

:: [5/5] 7z + SFX
echo [5/5] Packaging ...
7z a -mx=5 -mmt=on %NAME%.7z %NAME%\* >nul
if not exist %NAME%.7z (echo [ERROR] 7z failed & timeout /t 3 >nul & exit /b 1)

set "SFX_MODULE="
if exist "%ProgramFiles%\7-Zip\7z.sfx" set "SFX_MODULE=%ProgramFiles%\7-Zip\7z.sfx"
if exist "%ProgramFiles(x86)%\7-Zip\7z.sfx" set "SFX_MODULE=%ProgramFiles(x86)%\7-Zip\7z.sfx"
if "%SFX_MODULE%"=="" (echo [ERROR] 7z.sfx not found & timeout /t 3 >nul & exit /b 1)

echo ;!@Install@!UTF-8! > sfx_config.txt
echo Title=%NAME% >> sfx_config.txt
echo BeginPrompt=Install %NAME% to current directory? >> sfx_config.txt
echo ;!@InstallEnd@! >> sfx_config.txt

copy /b "%SFX_MODULE%" + sfx_config.txt + %NAME%.7z output\%NAME%_Setup.exe >nul
echo     OK: output\%NAME%_Setup.exe

:: Cleanup
for %%d in (build dist %NAME% %NAME%.spec %NAME%.7z sfx_config.txt) do (
    if exist %%d\ (rmdir /s /q %%d) else if exist %%d del %%d
)

echo.
echo ====================================
echo   BUILD COMPLETE
echo   output\%NAME%_Setup.exe
echo ====================================
pause

