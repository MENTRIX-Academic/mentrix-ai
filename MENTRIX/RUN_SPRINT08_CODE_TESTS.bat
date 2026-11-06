@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
 echo Start MENTRIX first so .venv is available.
 pause
 exit /b 1
)
".venv\Scripts\python.exe" -m pytest -q
if errorlevel 1 (
 echo [FAILED] Some engineering tests failed. This is not OCR accuracy.
 pause
 exit /b 1
)
echo [PASS] Code tests only, not handwriting CER/WER.
pause
