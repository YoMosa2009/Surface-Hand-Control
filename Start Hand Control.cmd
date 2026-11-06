@echo off
cd /d "%~dp0"
if exist "runtime\mediapipe" (
  start "" pythonw.exe "hand_control.py"
) else if exist ".venv\Scripts\pythonw.exe" (
  start "" ".venv\Scripts\pythonw.exe" "hand_control.py"
) else (
  echo Run Setup.cmd first.
  pause
)
