@echo off
cd /d "%~dp0"
call "%~dp0DETECT_PYTHON.bat"
if errorlevel 1 goto fail
echo TEST 1/3: Grading + Attendance + Authentication
%PYCMD% -m unittest discover -s tests -p "test_*.py" -v
if errorlevel 1 goto fail
echo.
echo TEST 2/3: OCR pipeline + Chatbot
%PYCMD% -m unittest discover -s ocr_tests -p "test_*.py" -v
if errorlevel 1 goto fail
echo.
echo TEST 3/3: Research reproducibility
%PYCMD% -m unittest discover -s research/tests -p "test_*.py" -v
if errorlevel 1 goto fail
echo.
echo PASS - local automated tests completed.
pause
exit /b 0
:fail
echo FAILED - capture this window and send it for debugging.
pause
exit /b 1
