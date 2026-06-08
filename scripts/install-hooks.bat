@echo off
chcp 65001 >nul
title QQMsgForward — 安装 Git Hooks

:: 设置 Git hooks 路径为项目内的 .githooks 目录
git config core.hooksPath .githooks

echo ✅ Git hooks 已安装
echo    hooks 路径: .githooks/
echo    下次 git commit 自动触发 Harness 验证
pause
