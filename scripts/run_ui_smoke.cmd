@echo off
setlocal

if "%BASE_URL%"=="" (
  echo [ERROR] BASE_URL is required.
  echo Example:
  echo   set BASE_URL=http://localhost:3000
  echo   set API_USER=your_user
  echo   set API_PASS=your_pass
  echo   scripts\run_ui_smoke.cmd
  exit /b 1
)

echo Running UI smoke...
echo BASE_URL=%BASE_URL%
if not "%API_USER%"=="" (
  echo API_USER=%API_USER%
) else (
  echo API_USER is empty ^(auth tests may be skipped^)
)

powershell -ExecutionPolicy Bypass -File "%~dp0run_ui_smoke.ps1"
exit /b %ERRORLEVEL%
