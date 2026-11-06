@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
 echo First run START_MENTRIX_HERE.bat and INSTALL_SPRINT06_OCR.bat
 pause
 exit /b 1
)
echo Checking user-provided registered IAM dataset...
".venv\Scripts\python.exe" -m research.sprint8.preflight
if errorlevel 1 goto :error
echo Testing FOUR real TrOCR pipelines on exactly the same full validation split.
echo This may require substantial RAM, CPU or GPU time.
".venv\Scripts\python.exe" -m research.sprint6.benchmark --manifest research\sprint6\data\iam_manifest.csv --images-dir research\sprint6\data\iam_lines --out research\sprint6\results --split validation
if errorlevel 1 goto :error
".venv\Scripts\python.exe" -m research.sprint8.error_analysis
if errorlevel 1 goto :error
echo [DONE] See research\sprint6\results\validation\validation_metrics.json
pause
exit /b 0
:error
echo [FAILED] No winner should be claimed. See output above.
pause
exit /b 1
