$RootPath = "G:\AI\E-zzio"
Set-Location $RootPath

$ManifestPath = "$RootPath\runtime\audit\integrity\sha256_baseline_v1.json"
if (-not (Test-Path $ManifestPath)) {
    Write-Error "[FAIL] Aucune baseline SHA256 trouvée dans runtime\audit\integrity\"
    exit 1
}

$Manifest = Get-Content $ManifestPath -Raw | ConvertFrom-Json
$Altered = 0
$Missing = 0
$Valid = 0

foreach ($fileItem in $Manifest.Files) {
    $fullPath = Join-Path $RootPath $fileItem.Path
    if (-not (Test-Path $fullPath)) {
        Write-Host "[MISSING] $($fileItem.Path)" -ForegroundColor Red
        $Missing++
        continue
    }

    $currentHash = (Get-FileHash -Path $fullPath -Algorithm SHA256).Hash
    if ($currentHash -ne $fileItem.SHA256) {
        Write-Host "[ALTERED] $($fileItem.Path)" -ForegroundColor Yellow
        $Altered++
    } else {
        $Valid++
    }
}

Write-Host "`n=== RÉSULTAT DU CONTRÔLE D'INTÉGRITÉ ===" -ForegroundColor Cyan
Write-Host "Fichiers valides   : $Valid" -ForegroundColor Green
Write-Host "Fichiers altérés   : $Altered" -ForegroundColor $(if($Altered -gt 0){'Yellow'}else{'Green'})
Write-Host "Fichiers manquants : $Missing" -ForegroundColor $(if($Missing -gt 0){'Red'}else{'Green'})

if ($Altered -eq 0 -and $Missing -eq 0) {
    Write-Host "`n[OK] INTÉGRITÉ TOTALE CERTIFIÉE (0 Dérive)" -ForegroundColor Green
} else {
    Write-Host "`n[!] DÉRIVE DÉTECTÉE — Révision requise." -ForegroundColor Red
}
