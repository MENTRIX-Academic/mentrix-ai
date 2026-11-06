@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>&1
if %errorlevel%==0 (
  py -3 -m unittest research.sprint4.test_sprint4 -v
) else (
  python -m unittest research.sprint4.test_sprint4 -v
)
echo.
pause
