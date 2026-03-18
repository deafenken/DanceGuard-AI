@echo off
setlocal
cd /d "%~dp0"

set "PY=%~dp0.venv\Scripts\python.exe"
if not exist "%PY%" (
  echo [ERROR] Missing virtualenv python: %PY%
  echo [ERROR] Rebuild the environment first.
  pause
  exit /b 1
)

echo [INFO] Starting Web UI...
echo [INFO] Open: http://127.0.0.1:8000
echo [INFO] Close this window to stop the server.
echo.
"%PY%" -u main.py

echo.
echo [INFO] Server stopped.
pause
