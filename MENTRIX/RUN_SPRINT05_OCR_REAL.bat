@echo off
setlocal
cd /d "%~dp0"
echo First: add YOUR handwritten images + independently verified GT.
echo Template: research\sprint5\data\ocr_manifest_TEMPLATE.csv
echo Manifest: research\sprint5\data\ocr_manifest.csv
echo Images: research\sprint5\data\images
where py >nul 2>&1
if %errorlevel%==0 (
 py -3 -m research.sprint5.ocr_runner --validate-only || goto fail
 py -3 -m research.sprint5.ocr_runner || goto fail
 py -3 -m research.sprint5.render_report || goto fail
) else (
 python -m research.sprint5.ocr_runner --validate-only || goto fail
 python -m research.sprint5.ocr_runner || goto fail
 python -m research.sprint5.render_report || goto fail
)
echo REAL OCR COMPLETED. Check research\sprint5\local_ocr_results\s05_ocr_metrics.json
pause
exit /b 0
:fail
echo Not yet ready: missing images / human GT / dependencies. No metrics fabricated.
pause
exit /b 1
