@echo off
setlocal
cd /d "%~dp0"
echo =======================================================
echo MENTRIX - SPRINT 02 - REAL DATA BENCHMARK
echo =======================================================
where py >nul 2>&1
if %errorlevel%==0 (
    py -3 research\sprint2\run.py
) else (
    python research\sprint2\run.py
)
echo.
echo Your previous website and results are untouched.
echo.
pause
