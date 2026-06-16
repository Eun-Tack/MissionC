@echo off
setlocal

cd /d "%~dp0"

if not exist ".tmp" mkdir ".tmp"
set "TEMP=%CD%\.tmp"
set "TMP=%CD%\.tmp"
set "MISSIONC_PY="

call :find_python
if not defined MISSIONC_PY (
  echo [MissionC] Python 3.11+ was not found.
  call :install_python
  call :find_python
)

if not defined MISSIONC_PY (
  echo [MissionC] Could not find or install Python 3.11+ automatically.
  echo [MissionC] Install Python 3.12 from https://www.python.org/downloads/windows/ and run this again.
  goto fail
)

echo [MissionC] Using Python: %MISSIONC_PY%

if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -m pip --version >nul 2>nul
  if errorlevel 1 (
    echo [MissionC] Existing .venv is missing pip. Recreating it...
    rmdir /s /q ".venv"
  )
)

if not exist ".venv\Scripts\python.exe" (
  echo [MissionC] Creating virtual environment...
  "%MISSIONC_PY%" -m venv .venv
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

:find_python
set "MISSIONC_PY="
python --version >nul 2>nul
if not errorlevel 1 (
  for /f "delims=" %%P in ('python -c "import sys; assert sys.version_info >= (3, 11); print(sys.executable)" 2^>nul') do set "MISSIONC_PY=%%P"
  if defined MISSIONC_PY exit /b 0
)
py -3.12 --version >nul 2>nul
if not errorlevel 1 (
  for /f "delims=" %%P in ('py -3.12 -c "import sys; print(sys.executable)" 2^>nul') do set "MISSIONC_PY=%%P"
  if defined MISSIONC_PY exit /b 0
)
py -3.11 --version >nul 2>nul
if not errorlevel 1 (
  for /f "delims=" %%P in ('py -3.11 -c "import sys; print(sys.executable)" 2^>nul') do set "MISSIONC_PY=%%P"
  if defined MISSIONC_PY exit /b 0
)
if exist "%LocalAppData%\Programs\Python\Python312\python.exe" (
  set "MISSIONC_PY=%LocalAppData%\Programs\Python\Python312\python.exe"
  exit /b 0
)
if exist "%LocalAppData%\Programs\Python\Python311\python.exe" (
  set "MISSIONC_PY=%LocalAppData%\Programs\Python\Python311\python.exe"
  exit /b 0
)
exit /b 0

:install_python
where winget >nul 2>nul
if errorlevel 1 (
  echo [MissionC] winget is not available, so Python cannot be installed automatically.
  exit /b 1
)
echo [MissionC] Installing Python 3.12 with winget. This may take a few minutes...
winget install -e --id Python.Python.3.12 --scope user --accept-package-agreements --accept-source-agreements
exit /b %ERRORLEVEL%

:end
