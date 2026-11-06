@echo off
setlocal
cd /d "%~dp0"
echo Installing optional transformer dependencies.
echo This may download large Python packages; internet required.
where py >nul 2>&1
if %errorlevel%==0 (
  py -3 -m pip install -r research\sprint3\requirements.txt -r research\sprint4\requirements_models.txt
) else (
  python -m pip install -r research\sprint3\requirements.txt -r research\sprint4\requirements_models.txt
)
if errorlevel 1 (
  echo INSTALL FAILED. See the error above.
) else (
  echo INSTALL COMPLETE. Next run RUN_SPRINT04_MODELS.bat
)
pause
