@echo off
setlocal

cd /d "%~dp0"

if not exist ".tmp" mkdir ".tmp"
set "TEMP=%CD%\.tmp"
set "TMP=%CD%\.tmp"

if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -m pip --version >nul 2>nul
  if errorlevel 1 (
    echo [MissionC] Existing .venv is missing pip. Recreating it...
    rmdir /s /q ".venv"
  )
)

if not exist ".venv\Scripts\python.exe" (
  echo [MissionC] Creating virtual environment...
  python -m venv .venv
  if errorlevel 1 py -3.12 -m venv .venv
  if errorlevel 1 py -3.11 -m venv .venv
  if errorlevel 1 (
    echo [MissionC] Failed to create venv. Install Python 3.11+ and try again.
    goto fail
  )
)

call ".venv\Scripts\activate.bat"

python -m pip install --upgrade pip
if errorlevel 1 goto fail

pip install -r requirements.txt
if errorlevel 1 goto fail

if not exist ".env" (
  copy ".env.example" ".env" >nul
  echo [MissionC] Created .env from .env.example
)

if not exist "data" mkdir "data"

set MC_ENV=development
set HOST=127.0.0.1
set PORT=8000

echo [MissionC] Starting at http://127.0.0.1:8000
python run.py
goto end

:fail
echo.
echo [MissionC] Startup failed. Check the error above.
pause
exit /b 1

:end
