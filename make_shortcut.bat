@echo off
rem === Desktop-Verknuepfung zur gebauten BubblR-Trainer.exe anlegen ===
setlocal
cd /d "%~dp0"
set "EXE=%~dp0dist\BubblR-Trainer\BubblR-Trainer.exe"
set "ICO=%~dp0assets\icon.ico"

if not exist "%EXE%" (
  echo [FEHLER] "%EXE%" fehlt - bitte zuerst build_exe.bat ausfuehren.
  pause
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws=New-Object -ComObject WScript.Shell; $l=Join-Path ([Environment]::GetFolderPath('Desktop')) 'BubblR Trainer.lnk'; $s=$ws.CreateShortcut($l); $s.TargetPath=$env:EXE; $s.WorkingDirectory=(Split-Path $env:EXE); $s.IconLocation=($env:ICO + ',0'); $s.Description='BubblR Trainer'; $s.Save(); Write-Host ('Verknuepfung erstellt: ' + $l)"

pause
endlocal
