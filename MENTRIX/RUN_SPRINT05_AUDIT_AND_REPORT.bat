@echo off
setlocal
cd /d "%~dp0"
echo MENTRIX Sprint05: 7 baselines + error audit + validation-only review gate
echo No internet required. No site modification.
where py >nul 2>&1
if %errorlevel%==0 (
  py -3 -m research.sprint5.audit_and_gate || goto fail
  py -3 -m research.sprint5.render_report || goto fail
) else (
  python -m research.sprint5.audit_and_gate || goto fail
  python -m research.sprint5.render_report || goto fail
)
start "" "research\sprint5\results\s05_unified_research_report.html"
echo SUCCESS. Report opened in browser.
pause
exit /b 0
:fail
echo ERROR. Run INSTALL_ASAG_DEPENDENCIES_ONCE.bat and retry.
pause
exit /b 1
