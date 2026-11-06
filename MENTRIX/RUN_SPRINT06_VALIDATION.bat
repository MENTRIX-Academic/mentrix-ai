@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
 echo Run START_MENTRIX_HERE.bat once, then INSTALL_SPRINT06_OCR.bat
 pause
 exit /b 1
)
if not exist "research\sprint6\data\iam_manifest.csv" (
 echo Missing data\iam_manifest.csv. See research\sprint6\README_AR.md
 pause
 exit /b 1
)
echo Running FOUR OCR variants on the same IAM validation split...
".venv\Scripts\python.exe" -m research.sprint6.benchmark --manifest research\sprint6\data\iam_manifest.csv --images-dir research\sprint6\data\iam_lines --out research\sprint6\results --split validation
if errorlevel 1 echo ERROR: check traceback, model memory, internet, and manifest.
pause
