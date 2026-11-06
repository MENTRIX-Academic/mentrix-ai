@echo off
cd /d "%~dp0"
if not exist "research\sprint3\results\asag_s03_report.html" (
  echo Report missing. Please run RUN_ASAG_BENCHMARK.bat first.
  pause
  exit /b 1
)
start "" "%~dp0research\sprint3\results\asag_s03_report.html"
