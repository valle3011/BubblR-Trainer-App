@echo off
rem === BubblR Trainer installer ===
rem Builds the standalone app (if needed) and installs it with Desktop +
rem Start-menu shortcuts. No "build then run" step, no admin rights.
rem Just double-click this file.
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" %*
endlocal
