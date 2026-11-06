@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
 echo Start project once before testing.
 pause
 exit /b 1
)
".venv\Scripts\python.exe" -m pytest --version >nul 2>&1
if errorlevel 1 (
 echo Installing pytest into the project's environment...
 ".venv\Scripts\python.exe" -m pip install pytest
 if errorlevel 1 goto fail
)
".venv\Scripts\python.exe" -m pytest -q
if errorlevel 1 goto fail
echo All engineering tests passed. This is NOT real handwritten OCR accuracy.
pause
exit /b 0
:fail
echo Tests failed. Check errors above.
pause
exit /b 1
