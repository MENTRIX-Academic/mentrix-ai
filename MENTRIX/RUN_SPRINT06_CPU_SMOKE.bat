@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
 echo Start project and install OCR dependencies first.
 pause
 exit /b 1
)
if not exist "research\sprint6\data\iam_manifest.csv" (
 echo Import IAM dataset first. Read research\sprint6\README_AR.md
 pause
 exit /b 1
)
echo Diagnostic ONLY: 5 IAM validation lines, one small model; NOT a scientific score or selected winner.
".venv\Scripts\python.exe" -m research.sprint6.benchmark --manifest research\sprint6\data\iam_manifest.csv --images-dir research\sprint6\data\iam_lines --out research\sprint6\results\diagnostics --split validation --device cpu --max-samples 5 --pipelines E03_small_rgb
pause
