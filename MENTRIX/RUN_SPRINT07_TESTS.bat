@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
 echo Run START_MENTRIX_HERE.bat first to set up the local Python environment.
 pause
 exit /b 1
)
".venv\Scripts\python.exe" -m pip show pytest >nul 2>&1
if errorlevel 1 ".venv\Scripts\python.exe" -m pip install pytest
".venv\Scripts\python.exe" -m pytest -q
if errorlevel 1 (
 echo Some software checks failed. Send the output to your team.
 pause
 exit /b 1
)
echo Software checks passed. This is NOT a measured handwriting OCR accuracy.
pause
