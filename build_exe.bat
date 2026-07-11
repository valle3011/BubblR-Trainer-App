@echo off
rem === Build BubblR-Trainer.exe (standalone, no Python needed to RUN it) ===
rem Needs Python 3 + PyQt5 to BUILD. PyInstaller is installed automatically.
setlocal
cd /d "%~dp0"

where python >nul 2>&1
if errorlevel 1 (
  echo [FEHLER] Python wurde nicht gefunden. Installiere Python 3 mit "Add to PATH".
  pause
  exit /b 1
)

python -c "import PyInstaller" 1>nul 2>&1
if errorlevel 1 (
  echo PyInstaller wird installiert ...
  python -m pip install pyinstaller || (echo [FEHLER] Installation fehlgeschlagen. & pause & exit /b 1)
)

echo Baue BubblR-Trainer.exe ...
python -m PyInstaller --onefile --windowed --name "BubblR-Trainer" --noconfirm --clean bubblr_trainer_app.py
if errorlevel 1 (
  echo [FEHLER] Build fehlgeschlagen.
  pause
  exit /b 1
)

echo.
echo Fertig:  "%~dp0dist\BubblR-Trainer.exe"
pause
endlocal
