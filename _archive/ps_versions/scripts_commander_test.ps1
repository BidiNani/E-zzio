$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=== E-ZZIO PC COMMANDER TEST ===" -ForegroundColor Cyan

$tests = @(
    "E-ZZIO, fais un état rapide de ton système.",
    "E-ZZIO, lance un audit.",
    "E-ZZIO, prépare la prochaine optimisation PC sans rien casser.",
    "CONFIRME",
    "E-ZZIO, fais un dry-run poussière.",
    "E-ZZIO, affiche tes sessions mémoire."
)

foreach ($text in $tests) {
    Write-Host ""
    Write-Host ">>> $text" -ForegroundColor Yellow

    & "G:\AI\E-zzio\scripts\ezzio_commander_pc.ps1" -Text $text
}
