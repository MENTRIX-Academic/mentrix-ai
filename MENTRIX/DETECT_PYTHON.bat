@echo off
set "PYCMD="
if exist "%~dp0.venv\Scripts\python.exe" (
  set PYCMD="%~dp0.venv\Scripts\python.exe"
  goto verify
)
if exist "%LocalAppData%\Programs\Python\Python312\python.exe" (
  set PYCMD="%LocalAppData%\Programs\Python\Python312\python.exe"
  goto verify
)
if exist "%LocalAppData%\Programs\Python\Python313\python.exe" (
  set PYCMD="%LocalAppData%\Programs\Python\Python313\python.exe"
  goto verify
)
py -3.12 -c "import sys; assert sys.version_info >= (3,10)" >nul 2>&1
if not errorlevel 1 (
  set "PYCMD=py -3.12"
  goto verify
)
py -3 -c "import sys; assert sys.version_info >= (3,10)" >nul 2>&1
if not errorlevel 1 (
  set "PYCMD=py -3"
  goto verify
)
python -c "import sys; assert sys.version_info >= (3,10)" >nul 2>&1
if not errorlevel 1 (
  set "PYCMD=python"
  goto verify
)
echo ERROR: Python 3.10 or newer was not found.
echo If Python is installed, try restarting your PC or repair the Python PATH.
exit /b 1
:verify
%PYCMD% -c "import sys; assert sys.version_info >= (3,10); print('Found Python:',sys.version.split()[0])"
if errorlevel 1 (
  echo ERROR: The selected Python did not start.
  exit /b 1
)
exit /b 0
