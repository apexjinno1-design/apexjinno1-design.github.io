@echo off
setlocal
title Start STOCK Screener
rem The execution-policy option applies only to this PowerShell process.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start-local.ps1"
echo.
pause
