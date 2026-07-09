@echo off
rem === BubblR Trainer (standalone app) - starten ===
rem Braucht Python 3. PyQt5 wird beim ersten Mal automatisch nachinstalliert.
setlocal
cd /d "%~dp0"

where python >nul 2>&1
if errorlevel 1 (
  echo [FEHLER] Python wurde nicht gefunden.
  echo Installiere Python 3 von https://www.python.org/downloads/
  echo und setze beim Setup den Haken bei "Add Python to PATH".
  pause
  exit /b 1
)

python -c "import PyQt5" 1>nul 2>&1
if errorlevel 1 (
  echo PyQt5 wird einmalig installiert ...
  python -m pip install PyQt5
)

python bubblr_trainer_app.py
if errorlevel 1 pause
endlocal
