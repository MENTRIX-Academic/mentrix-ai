@echo off
setlocal
cd /d "%~dp0"
echo ======================================================
echo MENTRIX - SPRINT 03 ASAG HUMAN-SCORED BENCHMARK
echo No site files or Sprint 01/02 results are changed.
echo ======================================================
where py >nul 2>&1
if %errorlevel%==0 (
  py -3 -m research.sprint3.asag_benchmark
) else (
  python -m research.sprint3.asag_benchmark
)
if errorlevel 1 (
  echo.
  echo Failed. You may need: Run INSTALL_ASAG_DEPENDENCIES_ONCE.bat
) else (
  echo.
  echo Success! Open: research\sprint3\results\asag_s03_report_AR.md
)
echo.
pause
