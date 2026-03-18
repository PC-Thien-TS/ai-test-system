@echo off
setlocal

if "%API_BASE_URL%"=="" goto :missing
if "%API_USER%"=="" goto :missing
if "%API_PASS%"=="" goto :missing

echo.
echo ==========================================
echo API Regression Runner
echo Base URL: %API_BASE_URL%
echo User: %API_USER%
echo ==========================================
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_api_regression.ps1"
set EXIT_CODE=%ERRORLEVEL%

echo.
echo ==========================================
echo API Regression Finished - Exit Code: %EXIT_CODE%
echo Artifacts: artifacts\test-results\api-regression
echo ==========================================
echo.

exit /b %EXIT_CODE%

:missing
echo Missing required environment variables.
echo.
echo Required:
echo   API_BASE_URL
echo   API_USER
echo   API_PASS
echo.
echo Example:
echo   set API_BASE_URL=http://192.168.1.7:19066
echo   set API_USER=your_email@example.com
echo   set API_PASS=your_password
echo   scripts\run_api_regression.cmd
echo.
exit /b 1
