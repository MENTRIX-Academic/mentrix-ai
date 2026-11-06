@echo off
setlocal
cd /d "%~dp0"
echo ===================================================
echo MENTRIX Sprint04 - ACTUAL MINILM + NLI comparison
echo Downloading model checkpoints may take time on first run.
echo On older CPU, use RUN_SPRINT04_MINILM_ONLY.bat first.
echo No website changes or automatic grade publishing.
echo ===================================================
where py >nul 2>&1
if %errorlevel%==0 (
  py -3 -m research.sprint4.model_benchmark
  if errorlevel 1 goto fail
  py -3 -m research.sprint4.render_report
  if errorlevel 1 goto fail
) else (
  python -m research.sprint4.model_benchmark
  if errorlevel 1 goto fail
  python -m research.sprint4.render_report
  if errorlevel 1 goto fail
)
echo.
echo SUCCESS. Use OPEN_SPRINT04_REPORT.bat
pause
exit /b 0
:fail
echo ERROR OR MODEL DOWNLOAD FAILED. Read research\sprint4\README_AR.md
pause
exit /b 1
