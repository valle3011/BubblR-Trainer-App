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

rem --onedir = Ordner-Version: startet am schnellsten (kein Entpacken).
rem Fuer eine Einzeldatei stattdessen --onefile setzen (startet etwas langsamer).
rem --icon setzt das Programm-Icon; --add-data buendelt es fuers Fenster-Icon.
echo Baue BubblR-Trainer (onedir) ...
python -m PyInstaller --onedir --windowed --name "BubblR-Trainer" --noconfirm --clean ^
  --icon "assets/icon.ico" ^
  --add-data "assets/icon.ico;assets" ^
  --add-data "assets/icon.png;assets" ^
  bubblr_trainer_app.py
if errorlevel 1 (
  echo [FEHLER] Build fehlgeschlagen.
  pause
  exit /b 1
)

echo.
echo Fertig:  "%~dp0dist\BubblR-Trainer\BubblR-Trainer.exe"
echo (den ganzen Ordner "dist\BubblR-Trainer" weitergeben)
pause
endlocal
