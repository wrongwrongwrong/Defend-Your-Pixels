@echo off
REM ──────────────────────────────────────────────────────────
REM Defend Your Pixels — Windows launcher
REM
REM Starts BOTH the React dev server and the Python live
REM tracker in a single terminal using "concurrently".
REM
REM Prerequisites:
REM   1.  cd react_frontend && npm install
REM   2.  pip install -e .   (from project root)
REM
REM Usage:
REM   cd D:\Defend-Your-Pixels
REM   scripts\run-windows.bat
REM ──────────────────────────────────────────────────────────

setlocal

set "PROJECT_ROOT=%~dp0.."

echo =============================================
echo   Defend Your Pixels — Windows
echo   Project root: %PROJECT_ROOT%
echo =============================================
echo.

REM Check that npm dependencies are installed
if not exist "%PROJECT_ROOT%\react_frontend\node_modules" (
    echo [setup] Installing React frontend dependencies...
    cd /d "%PROJECT_ROOT%\react_frontend"
    call npm install
)

echo [start] Launching React dev server + Python live tracker...
echo         React UI  -^> http://localhost:5173
echo         Tracker   -^> ws://localhost:8765
echo.

cd /d "%PROJECT_ROOT%\react_frontend"
call npx concurrently -k ^
    -n react,tracker ^
    -c cyan,magenta ^
    "npx vite" ^
    "cd /d \"%PROJECT_ROOT%\" && python -m runner.run_live_tracker"

endlocal
