$ErrorActionPreference = "Stop"
$RootPath = "G:\AI\E-zzio"
Set-Location $RootPath

$BaselineDir = "$RootPath\runtime\audit\integrity"
$ManifestPath = "$BaselineDir\sha256_baseline_v1.json"

# 1. Nettoyage de l'ancienne baseline pour éviter tout artefact auto-référentiel
if (Test-Path $ManifestPath) {
    Remove-Item -Path $ManifestPath -Force
}

New-Item -ItemType Directory -Force -Path $BaselineDir | Out-Null

$Targets = @(
    "web_server.py",
    "core",
    "runtime\security",
    "runtime\audit",
    "runtime\observability",
    "runtime\memory",
    "runtime\cognition",
    "runtime\execution",
    "runtime\launcher",
    "runtime\model_router",
    "tools"
)

$Hashes = @()

foreach ($target in $Targets) {
    $fullPath = Join-Path $RootPath $target
    if (Test-Path $fullPath) {
        # Exclusion stricte du dossier d'intégrité pour éliminer les boucles de hash
        $files = Get-ChildItem -Path $fullPath -Recurse -File -Include "*.py", "*.ps1", "*.json" -ErrorAction SilentlyContinue |
            Where-Object { $_.FullName -notmatch "runtime\\audit\\integrity" }

        foreach ($file in $files) {
            $hash = Get-FileHash -Path $file.FullName -Algorithm SHA256
            $relPath = $file.FullName.Replace($RootPath, "").TrimStart("\")
            $Hashes += [PSCustomObject]@{
                Path         = $relPath
                SHA256       = $hash.Hash
                SizeBytes    = $file.Length
                LastModified = $file.LastWriteTime.ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
            }
        }
    }
}

$Manifest = @{
    GeneratedAt       = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    TotalFilesScanned = $Hashes.Count
    Files             = $Hashes
}

$Manifest | ConvertTo-Json -Depth 5 | Set-Content -Path $ManifestPath -Encoding UTF8

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host " BASELINE D'INTÉGRITÉ SHA256 GÉNÉRÉE" -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "Fichiers scannés : $($Hashes.Count)" -ForegroundColor Green
Write-Host "Emplacement      : $ManifestPath" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
