@echo off
cd /d "%~dp0"
if exist "research\sprint5\results\s05_unified_research_report.html" (
 start "" "research\sprint5\results\s05_unified_research_report.html"
) else (
 echo Report missing. First run RUN_SPRINT05_AUDIT_AND_REPORT.bat
)
pause
