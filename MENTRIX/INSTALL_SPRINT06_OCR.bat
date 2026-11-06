@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
 echo Project virtual environment not found. Start START_MENTRIX_HERE.bat once.
 pause
 exit /b 1
)
echo Installing model libraries into project .venv ONLY...
".venv\Scripts\python.exe" -m pip install -r research\sprint6\requirements_ocr.txt
if errorlevel 1 (
 echo Installation failed. Copy the error above.
 pause
 exit /b 1
)
echo Done. Model weights download automatically from Hugging Face on first use (internet required).
pause
