@echo off
setlocal
cd /d "%~dp0"
echo Real MiniLM + NLI on CPU-oriented small batch; download first run.
echo If package missing: INSTALL_SPRINT04_MODELS_ONCE.bat
where py >nul 2>&1
if %errorlevel%==0 (
 py -3 -m research.sprint4.model_benchmark --batch-size 2 || goto fail
 py -3 -m research.sprint4.render_report || goto fail
 py -3 -m research.sprint5.render_report || goto fail
) else (
 python -m research.sprint4.model_benchmark --batch-size 2 || goto fail
 python -m research.sprint4.render_report || goto fail
 python -m research.sprint5.render_report || goto fail
)
start "" "research\sprint5\results\s05_unified_research_report.html"
echo SUCCESS: model scores produced; S03 files remain unchanged.
pause
exit /b 0
:fail
echo Could not run real models. Check internet/RAM and model dependencies.
pause
exit /b 1
