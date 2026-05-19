@echo off
setlocal

rem Launch PowerShell script from the repo root reliably (double-click friendly).
set "REPO_ROOT=%~dp0"
set "PS1=%REPO_ROOT%launch_live_demo.ps1"

if not exist "%PS1%" (
  echo ERROR: Cannot find "%PS1%".
  echo Make sure this .cmd file is in the repo root.
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1%"
set "EXITCODE=%ERRORLEVEL%"

if not "%EXITCODE%"=="0" (
  echo.
  echo launch_live_demo.ps1 exited with code %EXITCODE%.
  pause
)

exit /b %EXITCODE%

