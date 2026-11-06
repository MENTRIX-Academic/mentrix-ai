@echo off
setlocal
cd /d "%~dp0"
echo ===================================================
echo MENTRIX SPRINT 04 - ERROR ANALYSIS (NO MODEL DOWNLOAD)
echo This does NOT change the website or Sprint 03 results.
echo ===================================================
where py >nul 2>&1
if %errorlevel%==0 (
  py -3 -m research.sprint4.error_analysis
  if errorlevel 1 goto fail
  py -3 -m research.sprint4.render_report
  if errorlevel 1 goto fail
) else (
  python -m research.sprint4.error_analysis
  if errorlevel 1 goto fail
  python -m research.sprint4.render_report
  if errorlevel 1 goto fail
)
echo.
echo COMPLETE. Open OPEN_SPRINT04_REPORT.bat
pause
exit /b 0
:fail
echo ERROR. Make sure you have run the Sprint03 Python dependency installation.
pause
exit /b 1
