# BubblR Trainer — one-click installer.
# Builds the standalone .exe (if needed) and installs it per-user with Desktop
# and Start-menu shortcuts, so there is no "build then run" step. No admin
# rights required (installs under %LOCALAPPDATA%\Programs).
#
# Usage:  right-click install.bat -> Run,  or:  powershell -File install.ps1
#   -NoBuild            reuse an existing dist\ build instead of rebuilding
#   -SkipModelTrainer   install only BubblR Trainer, not the Model Trainer
param(
    [switch]$NoBuild,
    [switch]$SkipModelTrainer
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

function Fail($msg) { Write-Host "`n[FEHLER] $msg" -ForegroundColor Red; Read-Host "Enter zum Schliessen"; exit 1 }

# --- 1. Python present? ---------------------------------------------------
# A pre-built dist\ means we can install even without Python (end-user case).
$prebuilt = Test-Path (Join-Path $root "dist\BubblR-Trainer\BubblR-Trainer.exe")
$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $py) {
    if ($prebuilt) {
        Write-Host "Python nicht gefunden - installiere den vorhandenen Build." -ForegroundColor Yellow
        $NoBuild = $true
    } else {
        Write-Host "Python 3 wurde nicht gefunden." -ForegroundColor Yellow
        Write-Host "Lade es von https://www.python.org/downloads/ und setze beim"
        Write-Host "Setup den Haken bei 'Add Python to PATH'."
        if ((Read-Host "Jetzt die Download-Seite oeffnen? (j/n)") -match '^[jy]') {
            Start-Process "https://www.python.org/downloads/"
        }
        Fail "Python fehlt und kein fertiger Build vorhanden - abgebrochen."
    }
} else {
    Write-Host "Python:        $py"
}

# --- 2. Build the exe(s) with PyInstaller --------------------------------
if (-not $NoBuild) {
    $specs = @("BubblR-Trainer.spec")
    if (-not $SkipModelTrainer) { $specs += "BubblR-Model-Trainer.spec" }
    # The specs are part of the repo. If one is missing the clone is incomplete
    # (or a stale .gitignore dropped it) - say so instead of failing cryptically.
    foreach ($spec in $specs) {
        if (-not (Test-Path (Join-Path $root $spec))) {
            Fail "$spec fehlt. Hole die Datei aus dem Repository (git pull) und starte erneut."
        }
    }
    & $py -c "import PyInstaller" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "PyInstaller wird installiert ..."
        & $py -m pip install pyinstaller
        if ($LASTEXITCODE -ne 0) { Fail "PyInstaller konnte nicht installiert werden." }
    }
    Write-Host "Abhaengigkeiten werden geprueft ..."
    & $py -m pip install -r (Join-Path $root "requirements.txt")
    if ($LASTEXITCODE -ne 0) { Fail "Die Abhaengigkeiten konnten nicht installiert werden." }
    foreach ($spec in $specs) {
        Write-Host "`nBaue $spec ..." -ForegroundColor Cyan
        & $py -m PyInstaller $spec --noconfirm --clean
        if ($LASTEXITCODE -ne 0) { Fail "Build von $spec fehlgeschlagen." }
    }
} else {
    Write-Host "Ueberspringe Build (-NoBuild)."
}

# --- 3. Install: copy dist\ folders into %LOCALAPPDATA%\Programs\BubblR ---
$installRoot = Join-Path $env:LOCALAPPDATA "Programs\BubblR"
$apps = @(
    @{ name = "BubblR Trainer";       folder = "BubblR-Trainer";       exe = "BubblR-Trainer.exe";       icon = "assets\icon.ico" }
)
if (-not $SkipModelTrainer) {
    $apps += @{ name = "BubblR Model Trainer"; folder = "BubblR-Model-Trainer"; exe = "BubblR-Model-Trainer.exe"; icon = "assets\model_icon.ico" }
}

$ws = New-Object -ComObject WScript.Shell
$desktop = [Environment]::GetFolderPath("Desktop")
$programs = [Environment]::GetFolderPath("Programs")
$installed = @()

foreach ($app in $apps) {
    $src = Join-Path $root ("dist\" + $app.folder)
    if (-not (Test-Path $src)) {
        Write-Host "  uebersprungen: $($app.name) (kein Build in $src)" -ForegroundColor Yellow
        continue
    }
    $dst = Join-Path $installRoot $app.folder
    Write-Host "`nInstalliere $($app.name) -> $dst"
    if (Test-Path $dst) { Remove-Item $dst -Recurse -Force }
    New-Item -ItemType Directory -Force -Path $installRoot | Out-Null
    Copy-Item $src $dst -Recurse -Force

    $exePath = Join-Path $dst $app.exe
    $icoPath = Join-Path $dst $app.icon
    if (-not (Test-Path $icoPath)) { $icoPath = $exePath }
    foreach ($lnk in @((Join-Path $desktop  ($app.name + ".lnk")),
                       (Join-Path $programs ($app.name + ".lnk")))) {
        $s = $ws.CreateShortcut($lnk)
        $s.TargetPath = $exePath
        $s.WorkingDirectory = $dst
        $s.IconLocation = "$icoPath,0"
        $s.Description = $app.name
        $s.Save()
    }
    $installed += $exePath
}

if ($installed.Count -eq 0) { Fail "Nichts installiert - kein Build gefunden. Ohne -NoBuild erneut ausfuehren." }

# --- 4. Write a small uninstaller alongside the install ------------------
$uninstall = @"
# Removes BubblR from %LOCALAPPDATA%\Programs and deletes the shortcuts.
`$ErrorActionPreference = "SilentlyContinue"
Remove-Item "$installRoot" -Recurse -Force
$(($apps | ForEach-Object {
    "Remove-Item `"" + (Join-Path $desktop ($_.name + ".lnk")) + "`" -Force`n" +
    "Remove-Item `"" + (Join-Path $programs ($_.name + ".lnk")) + "`" -Force"
}) -join "`n")
Write-Host "BubblR wurde entfernt."
"@
New-Item -ItemType Directory -Force -Path $installRoot | Out-Null
Set-Content -Path (Join-Path $installRoot "uninstall.ps1") -Value $uninstall -Encoding UTF8

Write-Host "`nFertig! Installiert nach: $installRoot" -ForegroundColor Green
Write-Host "Verknuepfungen liegen auf dem Desktop und im Startmenue."
Write-Host "Deinstallieren:  powershell -File `"$installRoot\uninstall.ps1`""
if ((Read-Host "`nBubblR Trainer jetzt starten? (j/n)") -match '^[jy]') {
    Start-Process $installed[0]
}
