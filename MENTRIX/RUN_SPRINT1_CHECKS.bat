@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %ERRORLEVEL%==0 (
 set "PYCMD=py -3"
) else (
 set "PYCMD=python"
)
echo.
echo [1/2] Check archived research files - read only
%PYCMD% research\sprint1\preflight.py
if errorlevel 1 goto err
echo.
echo [2/2] Run Sprint 01 code smoke tests (synthetic fixture, NOT MODEL ACCURACY)
%PYCMD% research\sprint1\test_sprint1.py
if errorlevel 1 goto err
echo.
echo PASS: Sprint 01 checks completed. No Kaggle data downloaded or model trained.
echo Follow research\sprint1\README_AR.md to use real datasets.
pause
exit /b 0
:err
echo.
echo Checks stopped due to an error. See message above.
pause
exit /b 1
