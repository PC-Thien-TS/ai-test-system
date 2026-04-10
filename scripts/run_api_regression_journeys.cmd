@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_api_regression_journeys.ps1"
exit /b %errorlevel%
