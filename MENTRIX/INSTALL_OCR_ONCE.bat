@echo off
setlocal
cd /d "%~dp0"
call "%~dp0DETECT_PYTHON.bat"
if errorlevel 1 goto failed
echo.
echo Checking the OCR libraries...
%PYCMD% -m pip install -r requirements.txt
if errorlevel 1 goto failed
%PYCMD% -c "import torch; print('PyTorch already installed:',torch.__version__)" >nul 2>&1
if errorlevel 1 (
  echo Installing CPU PyTorch. This can be a large download.
  %PYCMD% -m pip install torch --index-url https://download.pytorch.org/whl/cpu
  if errorlevel 1 goto failed
) else (
  echo PyTorch is already installed. Keeping your current version.
)
%PYCMD% -m pip install "transformers==4.57.6"
if errorlevel 1 goto failed
%PYCMD% -c "from transformers import TrOCRProcessor, VisionEncoderDecoderModel; print('OCR libraries are ready')"
if errorlevel 1 goto failed
echo Done. Start MENTRIX again.
pause
exit /b 0
:failed
echo OCR installation failed. Please send a screenshot of the error.
pause
exit /b 1
