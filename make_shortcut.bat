@echo off
rem === Create Desktop + Start-menu shortcuts to BubblR Trainer ===
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0make_shortcut.ps1"
pause
endlocal
