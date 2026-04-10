@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_api_regression_core.ps1"
exit /b %errorlevel%
