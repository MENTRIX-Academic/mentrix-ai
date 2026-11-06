@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
title MENTRIX V1 - SAFE LOCAL START
color 0A
echo =============================================
echo MENTRIX - Windows installation fix
echo Libraries will stay inside this project.
echo =============================================
echo.
if not exist "%~dp0.venv\Scripts\python.exe" goto create_env
goto run_env
:create_env
echo [1/3] Creating an isolated Python environment (.venv)...
call "%~dp0DETECT_PYTHON.bat"
if errorlevel 1 goto failed
%PYCMD% -m venv "%~dp0.venv"
if errorlevel 1 goto venv_failed
:run_env
if not exist "%~dp0.venv\Scripts\python.exe" goto venv_failed
echo [2/3] Checking the project's Python environment...
"%~dp0.venv\Scripts\python.exe" -c "import sys,pip; assert sys.prefix != sys.base_prefix, 'Not inside a virtual environment'; print('Using project Python:',sys.executable)"
if errorlevel 1 goto venv_failed
echo [3/3] Starting MENTRIX (first run may install libraries)...
"%~dp0.venv\Scripts\python.exe" "%~dp0launch_mentrix.py"
if errorlevel 1 goto failed
echo.
echo MENTRIX stopped.
pause
exit /b 0
:venv_failed
echo.
echo ERROR: Could not create or use the local .venv environment.
echo Check that Python 3.10+ is installed and no antivirus blocks this folder.
echo You may rename .venv to .venv_old and rerun this file.
goto failed
:failed
echo.
echo START FAILED. Share the error in this window or start_error_log.txt.
echo No global Python packages were modified by this launcher.
pause
exit /b 1
