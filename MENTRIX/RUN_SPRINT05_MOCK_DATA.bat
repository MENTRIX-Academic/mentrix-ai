@echo off
setlocal
cd /d "%~dp0"
echo Building 30 synthetic student records, 12 sessions and sample attendance.
where py >nul 2>&1
if %errorlevel%==0 (
 py -3 -m research.sprint5.mock_data_factory || goto fail
) else (
 python -m research.sprint5.mock_data_factory || goto fail
)
echo Done. Open research\sprint5\mock_data\s05_mock_backend_data.json
pause
exit /b 0
:fail
echo Python error; see text above.
pause
exit /b 1
