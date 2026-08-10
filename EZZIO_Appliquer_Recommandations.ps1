# ==============================================================================
# E-ZZIO - APPLICATION DES RECOMMANDATIONS (mode réel)
# ==============================================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ProjectRoot = 'G:\AI\E-zzio'
$WhatIf      = $false         # MODE RÉEL

function Format-Size {
    param([Int64]$Bytes)
    if ($Bytes -ge 1GB) { "{0:N2} GB" -f ($Bytes/1GB) }
    elseif ($Bytes -ge 1MB) { "{0:N2} MB" -f ($Bytes/1MB) }
    elseif ($Bytes -ge 1KB) { "{0:N2} KB" -f ($Bytes/1KB) }
    else { "$Bytes B" }
}

function Get-FolderSize {
    param([string]$Path)
    $s = 0L
    if (Test-Path -LiteralPath $Path) {
        Get-ChildItem -LiteralPath $Path -File -Recurse -Force -ErrorAction SilentlyContinue |
            ForEach-Object { $s += [int64]$_.Length }
    }
    return $s
}

Clear-Host
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host " E-ZZIO - APPLICATION DES RECOMMANDATIONS" -ForegroundColor Cyan
Write-Host " MODE RÉEL" -ForegroundColor Red
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""

Set-Location $ProjectRoot
$before = Get-FolderSize $ProjectRoot
Write-Host "Taille avant : $(Format-Size $before)" -ForegroundColor Yellow
Write-Host ""

# ==============================================================================
# 1. Archiver CONSOLIDATION_*
# ==============================================================================
Write-Host "[1/4] Archivage CONSOLIDATION_*..." -ForegroundColor Yellow

$archiveConsol = Join-Path $ProjectRoot 'archive\consolidation'
New-Item -Path $archiveConsol -ItemType Directory -Force | Out-Null

$consolidation = Get-ChildItem -LiteralPath $ProjectRoot -Directory -Force -ErrorAction SilentlyContinue |
                 Where-Object { $_.Name -like 'CONSOLIDATION_*' }

foreach ($d in $consolidation) {
    $size = Get-FolderSize $d.FullName
    $dest = Join-Path $archiveConsol $d.Name
    Move-Item -LiteralPath $d.FullName -Destination $dest -Force
    Write-Host "  Archivé : $($d.Name) ($(Format-Size $size))" -ForegroundColor Green
}

# ==============================================================================
# 2. git gc
# ==============================================================================
Write-Host ""
Write-Host "[2/4] Optimisation Git (peut prendre 1-3 min)..." -ForegroundColor Yellow

$gitBefore = Get-FolderSize (Join-Path $ProjectRoot '.git')
Write-Host "  .git avant : $(Format-Size $gitBefore)"

if (Test-Path (Join-Path $ProjectRoot '.git')) {
    & git gc --aggressive --prune=now 2>&1 | Out-Null
    $gitAfter = Get-FolderSize (Join-Path $ProjectRoot '.git')
    Write-Host "  .git après  : $(Format-Size $gitAfter)" -ForegroundColor Green
    Write-Host "  Gain        : $(Format-Size ($gitBefore - $gitAfter))" -ForegroundColor Green
}

# ==============================================================================
# 3. Archiver les rapports
# ==============================================================================
Write-Host ""
Write-Host "[3/4] Archivage des rapports..." -ForegroundColor Yellow

$reportsPath = Join-Path $ProjectRoot 'reports'
$archiveReports = Join-Path $ProjectRoot 'archive\reports'

if (Test-Path $reportsPath) {
    $reportsSize = Get-FolderSize $reportsPath
    New-Item -Path $archiveReports -ItemType Directory -Force | Out-Null
    Move-Item -LiteralPath $reportsPath -Destination $archiveReports -Force
    Write-Host "  reports archivé ($(Format-Size $reportsSize))" -ForegroundColor Green
} else {
    Write-Host "  Pas de dossier reports." -ForegroundColor DarkGray
}

# ==============================================================================
# 4. _harvested_assets (demande confirmation)
# ==============================================================================
Write-Host ""
Write-Host "[4/4] _harvested_assets..." -ForegroundColor Yellow

$harvested = Join-Path $ProjectRoot '_harvested_assets'
if (Test-Path $harvested) {
    $hSize = Get-FolderSize $harvested
    Write-Host "  Taille : $(Format-Size $hSize)" -ForegroundColor Cyan
    Write-Host "  Ce dossier contient des assets récupérés." -ForegroundColor Yellow
    $confirm = Read-Host "  Tu veux l'archiver aussi ? (OUI / non)"

    if ($confirm -eq 'OUI') {
        $archiveHarvest = Join-Path $ProjectRoot 'archive\harvested_assets'
        New-Item -Path $archiveHarvest -ItemType Directory -Force | Out-Null
        Move-Item -LiteralPath $harvested -Destination $archiveHarvest -Force
        Write-Host "  _harvested_assets archivé." -ForegroundColor Green
    } else {
        Write-Host "  Conservé." -ForegroundColor DarkGray
    }
} else {
    Write-Host "  Dossier absent." -ForegroundColor DarkGray
}

# ==============================================================================
# Résultat final
# ==============================================================================
Write-Host ""
$after = Get-FolderSize $ProjectRoot
Write-Host "==============================================" -ForegroundColor Green
Write-Host " Terminé."
Write-Host " Taille avant : $(Format-Size $before)"
Write-Host " Taille après : $(Format-Size $after)"
Write-Host " Gain         : $(Format-Size ($before - $after))"
Write-Host "==============================================" -ForegroundColor Green
Write-Host ""
Write-Host "Appuie sur Entrée pour fermer..."
[void][System.Console]::ReadLine()