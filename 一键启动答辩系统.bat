@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0launch_demo.ps1"
exit /b %errorlevel%
