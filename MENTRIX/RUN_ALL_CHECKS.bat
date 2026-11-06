@echo off
setlocal
cd /d "%~dp0"
call "%~dp0DETECT_PYTHON.bat"
if errorlevel 1 goto done
%PYCMD% -m pip install pytest httpx
%PYCMD% -m pytest -q
:done
pause
