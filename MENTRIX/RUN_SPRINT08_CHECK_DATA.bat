@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
 echo [MISSING PYTHON] First run START_MENTRIX_HERE.bat
 pause
 exit /b 1
)
echo Step 1: Check IAM images, labels, writer-independent splits, and provenance.
echo This is a data audit. It does not run TrOCR or claim OCR accuracy.
".venv\Scripts\python.exe" -m research.sprint8.preflight
if errorlevel 1 (
 echo [FAILED] Missing or invalid registered IAM data. Read READ_ME_FIRST_SPRINT08_AR.md
 pause
 exit /b 1
)
echo [PASSED] Dataset can be benchmarked; does not mean OCR is accurate.
pause
