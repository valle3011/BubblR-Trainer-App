# Create "BubblR Trainer" shortcuts on the Desktop and in the Start menu.
# Targets the built .exe if present, otherwise runs the Python app via pythonw
# (no console window). Called by run.bat on first launch and by make_shortcut.bat.
$ErrorActionPreference = "Stop"
$appDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ico = Join-Path $appDir "assets\icon.ico"

$exe = Join-Path $appDir "dist\BubblR-Trainer\BubblR-Trainer.exe"
if (Test-Path $exe) {
    $target = $exe
    $arguments = ""
    $workdir = Split-Path $exe
} else {
    $py = (Get-Command pythonw -ErrorAction SilentlyContinue).Source
    if (-not $py) { $py = (Get-Command python -ErrorAction SilentlyContinue).Source }
    if (-not $py) { Write-Host "Python not found - cannot create a shortcut."; exit 1 }
    $target = $py
    $arguments = '"' + (Join-Path $appDir "bubblr_trainer_app.py") + '"'
    $workdir = $appDir
}

$ws = New-Object -ComObject WScript.Shell
$locations = @(
    (Join-Path ([Environment]::GetFolderPath("Desktop"))  "BubblR Trainer.lnk"),
    (Join-Path ([Environment]::GetFolderPath("Programs")) "BubblR Trainer.lnk")
)
foreach ($lnk in $locations) {
    $s = $ws.CreateShortcut($lnk)
    $s.TargetPath = $target
    $s.Arguments = $arguments
    $s.WorkingDirectory = $workdir
    if (Test-Path $ico) { $s.IconLocation = "$ico,0" }
    $s.Description = "BubblR Trainer"
    $s.Save()
    Write-Host ("Shortcut: " + $lnk)
}
