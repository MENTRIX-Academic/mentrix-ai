@echo off
setlocal
cd /d "%~dp0"
echo Running the REAL MiniLM only (skip NLI to reduce CPU/RAM needs)
where py >nul 2>&1
if %errorlevel%==0 (
  py -3 -m research.sprint4.model_benchmark --skip-nli
  if errorlevel 1 goto fail
  py -3 -m research.sprint4.render_report
  if errorlevel 1 goto fail
) else (
  python -m research.sprint4.model_benchmark --skip-nli
  if errorlevel 1 goto fail
  python -m research.sprint4.render_report
  if errorlevel 1 goto fail
)
echo.
echo SUCCESS. Use OPEN_SPRINT04_REPORT.bat
pause
exit /b 0
:fail
echo FAILED; review the output above.
pause
exit /b 1
