@echo off
setlocal

if "%API_USER%"=="" (
  echo [ERROR] API_USER is required.
  echo Example:
  echo   set API_USER=your_user
  echo   set API_PASS=your_pass
  echo   set BASE_URL=http://192.168.1.7:19068
  echo   scripts\run_ui_e2e.cmd
  exit /b 1
)

if "%API_PASS%"=="" (
  echo [ERROR] API_PASS is required.
  echo Example:
  echo   set API_USER=your_user
  echo   set API_PASS=your_pass
  echo   set BASE_URL=http://192.168.1.7:19068
  echo   scripts\run_ui_e2e.cmd
  exit /b 1
)

if "%BASE_URL%"=="" (
  set BASE_URL=http://192.168.1.7:19068
)

echo Running admin UI E2E suite...
echo BASE_URL=%BASE_URL%
echo API_USER=%API_USER%

powershell -ExecutionPolicy Bypass -File "%~dp0run_ui_e2e.ps1"
exit /b %ERRORLEVEL%
