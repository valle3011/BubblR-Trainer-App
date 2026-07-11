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

rem PyQt5 nur EINMAL pruefen/installieren (Marker-Datei). Jeder weitere Start
rem spart so den zusaetzlichen Python-Prozess fuer den Import-Check -> schneller.
if not exist ".deps_ok" (
  python -c "import PyQt5" 1>nul 2>&1
  if errorlevel 1 (
    echo PyQt5 wird einmalig installiert ...
    python -m pip install PyQt5
    if errorlevel 1 (
      echo [FEHLER] PyQt5 konnte nicht installiert werden.
      pause
      exit /b 1
    )
  )
  echo ok> ".deps_ok"
)

rem First run only: offer to create Desktop + Start-menu shortcuts.
if not exist ".shortcut_asked" call :ask_shortcut

python bubblr_trainer_app.py %*
if errorlevel 1 pause
endlocal
exit /b

:ask_shortcut
echo.
choice /C JN /N /M "Verknuepfung auf Desktop und im Startmenue anlegen? (J/N) "
if errorlevel 2 goto :ask_done
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0make_shortcut.ps1"
:ask_done
echo done> ".shortcut_asked"
exit /b
