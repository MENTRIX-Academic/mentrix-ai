@echo off
setlocal
cd /d "%~dp0"
echo Installing MENTRIX Sprint 03 baseline requirements (one time only)...
where py >nul 2>&1
if %errorlevel%==0 (
  py -3 -m pip install -r research\sprint3\requirements.txt
) else (
  python -m pip install -r research\sprint3\requirements.txt
)
if errorlevel 1 (
  echo.
  echo INSTALL FAILED. Check Python and internet connection.
) else (
  echo.
  echo INSTALL FINISHED. Now run RUN_ASAG_BENCHMARK.bat.
)
pause
