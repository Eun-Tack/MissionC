@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [MissionC] Creating virtual environment...
  where py >nul 2>nul
  if errorlevel 1 (
    python -m venv .venv
  ) else (
    py -3 -m venv .venv
  )
  if errorlevel 1 (
    echo [MissionC] Failed to create venv. Install Python 3.11+ and try again.
    exit /b 1
  )
)

call ".venv\Scripts\activate.bat"

python -m pip install --upgrade pip
if errorlevel 1 exit /b 1

pip install -r requirements.txt
if errorlevel 1 exit /b 1

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
