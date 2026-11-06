@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
 echo Run START_MENTRIX_HERE.bat first.
 pause
 exit /b 1
)
if not exist "research\sprint6\results\selected_from_validation.json" (
 echo STOP: Need complete REAL validation, not a diagnostic or mock test.
 pause
 exit /b 1
)
echo Testing PRESELECTED validation winner on held-out IAM Test ONCE. No retuning.
".venv\Scripts\python.exe" -m research.sprint6.benchmark --manifest research\sprint6\data\iam_manifest.csv --images-dir research\sprint6\data\iam_lines --out research\sprint6\results --split test
if errorlevel 1 (
 echo [FAILED] Check labels, dataset fingerprint, selection file, and test lock.
 pause
 exit /b 1
)
echo [DONE] See research\sprint6\results\test\test_metrics.json
pause
