@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher not found. Install Python 3.12 x64 and its launcher.
  exit /b 1
)
py -3.12 -m venv .venv
if errorlevel 1 exit /b 1
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 exit /b 1
.venv\Scripts\python.exe setup_model.py
if errorlevel 1 exit /b 1
where dotnet >nul 2>nul
if errorlevel 1 (
  echo .NET SDK not found. Webcam setup is complete; IR bridge was not built.
) else (
  dotnet build irbridge\irbridge.csproj -c Release
  if errorlevel 1 (
    echo IR bridge build failed. Webcam setup is complete.
  )
)
echo Setup complete. Double-click Start Hand Control.cmd.
pause
