@echo off
setlocal
cd /d "%~dp0"
echo Installing TrOCR dependencies. Needs internet and free disk space.
where py >nul 2>&1
if %errorlevel%==0 (
  py -3 -m pip install -r research\sprint5\ocr_requirements.txt
) else (
  python -m pip install -r research\sprint5\ocr_requirements.txt
)
if errorlevel 1 echo Installation failed; see messages above.
pause
