$ErrorActionPreference = 'Stop'

$project = 'G:\AI\E-zzio'
$launcher = Join-Path $project 'E-ZZIO-Bot-Launcher.cmd'
$desktop = [Environment]::GetFolderPath('Desktop')
$shortcutPath = Join-Path $desktop 'E-ZZIO Bot.lnk'

if (-not (Test-Path $launcher)) {
    throw "Launcher introuvable : $launcher"
}

$wsh = New-Object -ComObject WScript.Shell
$shortcut = $wsh.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $launcher
$shortcut.WorkingDirectory = $project
$shortcut.Description = 'Lancer E-ZZIO Bot Discord'
$shortcut.IconLocation = "$env:SystemRoot\System32\shell32.dll,13"
$shortcut.Save()

Write-Host "Launcher cree : $shortcutPath"
