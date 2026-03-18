@echo off
setlocal

if "%API_BASE_URL%"=="" goto missing_env
if "%API_USER%"=="" goto missing_env
if "%API_PASS%"=="" goto missing_env

if "%API_MODE%"=="" set API_MODE=READ_ONLY

echo ============================================
echo API Full Smoke Runner
echo Base URL: %API_BASE_URL%
echo User: %API_USER%
echo Mode: %API_MODE%
echo ============================================

powershell -ExecutionPolicy Bypass -File "%~dp0run_api_full_smoke.ps1"
exit /b %ERRORLEVEL%

:missing_env
echo ERROR: Missing required environment variables.
echo Required:
echo   API_BASE_URL
echo   API_USER
echo   API_PASS
echo.
echo Example:
echo   set API_BASE_URL=http://192.168.1.7:19066
echo   set API_USER=qa@example.com
echo   set API_PASS=your_password
echo   set API_MODE=READ_ONLY
exit /b 1
