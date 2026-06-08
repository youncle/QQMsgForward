import os
path = r"D:\DevGitee\agent-space\QQMsgForward\.githooks\pre-commit"

lines = []
lines.append("@echo off\r\n")
lines.append("chcp 65001 >nul 2>&1\r\n")
lines.append('set ROOT=%~dp0..\r\n')
lines.append('set VERIFY=%ROOT%\\scripts\\verify.py\r\n')
lines.append("\r\n")
lines.append("for /f \"delims=\" %%f in ('git diff --cached --name-only') do (\r\n")
lines.append('    if /i "%%f"=="main.py" echo [BLOCKED] %%f & exit /b 1\r\n')
lines.append('    echo %%f | findstr /i /b "runtime" >nul 2>&1 && echo [BLOCKED] %%f & exit /b 1\r\n')
lines.append('    echo %%f | findstr /i /b "config\\config.json" >nul 2>&1 && echo [BLOCKED] %%f & exit /b 1\r\n')
lines.append(")\r\n")
lines.append("echo [OK] Safety check passed\r\n")
lines.append("\r\n")
lines.append('if not exist "%VERIFY%" exit /b 0\r\n')
lines.append('python "%VERIFY%"\r\n')
lines.append("if %errorlevel% neq 0 (\r\n")
lines.append("    echo [BLOCKED] Harness failed. Bypass: git commit --no-verify\r\n")
lines.append("    exit /b 1\r\n")
lines.append(")\r\n")
lines.append("echo [OK] Harness passed\r\n")
lines.append("exit /b 0\r\n")

with open(path, "wb") as f:
    for line in lines:
        f.write(line.encode("ascii"))

print(f"Written: {os.path.getsize(path)} bytes")
with open(path, "rb") as f:
    raw = f.read(30)
    print(f"Has CRLF: {b'\\r\\n' in raw}")
    print(f"Content: {raw}")
