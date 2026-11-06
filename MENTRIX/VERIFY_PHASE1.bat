@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo MENTRIX Phase 1 - reproduce engineering evidence
py -m pip install -r requirements.txt
if errorlevel 1 (
  echo Dependency installation failed.
  pause
  exit /b 1
)
py REPRODUCE_PHASE1.py
if errorlevel 1 (
  echo One or more engineering checks FAILED. See reports\phase1_verification.txt
  pause
  exit /b 1
)
echo.
echo Current package checks passed. Historical and TA gates may still be open.
echo See reports\phase1_verification.txt
pause
