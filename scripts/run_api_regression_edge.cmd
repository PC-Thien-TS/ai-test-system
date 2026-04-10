@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_api_regression_edge.ps1"
exit /b %errorlevel%
