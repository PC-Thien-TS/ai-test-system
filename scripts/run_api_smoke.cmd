@echo off
setlocal

REM ======================================================
REM Default configuration (pre-filled for local testing)
REM ======================================================
set API_BASE_URL=http://192.168.1.7:19066
set API_USER=[tieuphiphi020103+71111@gmail.com](mailto:tieuphiphi020103+71111@gmail.com)
set API_PASS=Thien0602$

echo.
echo ==========================================
echo Running API Smoke Test
echo Base URL: %API_BASE_URL%
echo User: %API_USER%
echo ==========================================
echo.

REM ======================================================
REM Execute PowerShell smoke test
REM ======================================================
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_api_smoke.ps1"

set EXIT_CODE=%ERRORLEVEL%

echo.
echo ==========================================
echo API Smoke Test Finished
echo Exit Code: %EXIT_CODE%
echo ==========================================
echo.

exit /b %EXIT_CODE%