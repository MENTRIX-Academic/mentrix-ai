@echo off
setlocal
cd /d "%~dp0"
echo MENTRIX: Download authorized ASAP-SAS dataset and run benchmark
 echo First sign in on Kaggle and accept competition rules:
echo https://www.kaggle.com/competitions/asap-sas/data
 echo Install and configure the Kaggle CLI first: py -m pip install kaggle
 echo Do not share your Kaggle API token with anyone.
echo.
where py >nul 2>&1
if %errorlevel%==0 (
    py -3 research\sprint2\run.py --download
) else (
    python research\sprint2\run.py --download
)
pause
