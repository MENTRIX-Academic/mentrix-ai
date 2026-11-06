@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
 echo Missing project .venv. Run START_MENTRIX_HERE.bat
 pause
 exit /b 1
)
if not exist "research\sprint6\results\selected_from_validation.json" (
 echo Run RUN_SPRINT06_VALIDATION.bat first. No test-set tuning allowed.
 pause
 exit /b 1
)
echo Testing ONLY the preselected winner once on frozen held-out test lines...
".venv\Scripts\python.exe" -m research.sprint6.benchmark --manifest research\sprint6\data\iam_manifest.csv --images-dir research\sprint6\data\iam_lines --out research\sprint6\results --split test
if errorlevel 1 echo ERROR: check error details above.
pause
