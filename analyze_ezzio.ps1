# ==============================================================================
# E-ZZIO - ANALYSE STRUCTURE RÉELLE
# ==============================================================================

$ProjectRoot = "G:\AI\E-zzio"

function Format-Size($bytes) {
    if ($bytes -ge 1GB) { return "{0:N2} GB" -f ($bytes / 1GB) }
    elseif ($bytes -ge 1MB) { return "{0:N2} MB" -f ($bytes / 1MB) }
    elseif ($bytes -ge 1KB) { return "{0:N2} KB" -f ($bytes / 1KB) }
    else { return "$bytes B" }
}

function Get-FolderSize($path) {
    if (-not (Test-Path $path)) { return 0 }
    $measure = Get-ChildItem $path -Recurse -Force -ErrorAction SilentlyContinue |
        Measure-Object -Property Length -Sum
    if ($null -eq $measure -or $null -eq $measure.Sum) { return 0 }
    return $measure.Sum
}

Write-Host "==============================================" -ForegroundColor Cyan
Write-Host " E-ZZIO - ANALYSE STRUCTURE RÉELLE" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path $ProjectRoot)) {
    Write-Host "ERREUR : $ProjectRoot introuvable." -ForegroundColor Red
    exit
}

Set-Location $ProjectRoot

# ------------------------------------------------------------------------
# 1. Taille totale
# ------------------------------------------------------------------------
$total = Get-FolderSize $ProjectRoot
Write-Host "[1/5] Taille totale du projet : $(Format-Size $total)" -ForegroundColor Yellow
Write-Host ""

# ------------------------------------------------------------------------
# 2. Taille par dossier de premier niveau
# ------------------------------------------------------------------------
Write-Host "[2/5] Répartition par dossier (1er niveau)" -ForegroundColor Yellow
Get-ChildItem $ProjectRoot -Directory -Force -ErrorAction SilentlyContinue | ForEach-Object {
    $size = Get-FolderSize $_.FullName
    $fileCount = (Get-ChildItem $_.FullName -Recurse -File -Force -ErrorAction SilentlyContinue | Measure-Object).Count
    [PSCustomObject]@{
        Dossier  = $_.Name
        Taille   = Format-Size $size
        Fichiers = $fileCount
        Bytes    = $size
    }
} | Sort-Object -Property Bytes -Descending | Format-Table Dossier, Taille, Fichiers -AutoSize
Write-Host ""

# Fichiers à la racine
$rootFiles = Get-ChildItem $ProjectRoot -File -Force -ErrorAction SilentlyContinue
if ($rootFiles) {
    Write-Host "Fichiers à la racine :" -ForegroundColor DarkGray
    $rootFiles | ForEach-Object {
        Write-Host "  $($_.Name) - $(Format-Size $_.Length)" -ForegroundColor DarkGray
    }
    Write-Host ""
}

# ------------------------------------------------------------------------
# 3. Contenu détaillé de core/
# ------------------------------------------------------------------------
Write-Host "[3/5] Contenu de core/" -ForegroundColor Yellow
$coreDir = Join-Path $ProjectRoot 'core'
if (Test-Path $coreDir) {
    Get-ChildItem $coreDir -Recurse -File -Force -ErrorAction SilentlyContinue | ForEach-Object {
        $lines = (Get-Content $_.FullName -ErrorAction SilentlyContinue | Measure-Object -Line).Lines
        $isStub = $lines -le 5
        $tag = if ($isStub) { "[VIDE/STUB]" } else { "[REMPLI]" }
        $color = if ($isStub) { "DarkGray" } else { "Green" }
        Write-Host "  $tag $($_.Name) - $lines lignes - $(Format-Size $_.Length)" -ForegroundColor $color
    }
} else {
    Write-Host "  core/ introuvable" -ForegroundColor Red
}
Write-Host ""

# ------------------------------------------------------------------------
# 4. Doublons potentiels (par nom de fichier, >50 MB)
# ------------------------------------------------------------------------
Write-Host "[4/5] Recherche de doublons (fichiers >50 MB, même nom)" -ForegroundColor Yellow
$allBigFiles = Get-ChildItem $ProjectRoot -Recurse -File -Force -ErrorAction SilentlyContinue |
    Where-Object { $_.Length -gt 50MB }

$grouped = $allBigFiles | Group-Object Name | Where-Object { $_.Count -gt 1 }

if ($grouped) {
    foreach ($g in $grouped) {
        $totalDup = ($g.Group | Measure-Object -Property Length -Sum).Sum
        $recoverable = $totalDup - ($g.Group[0].Length)
        Write-Host "  $($g.Name) x$($g.Count) - récupérable : $(Format-Size $recoverable)" -ForegroundColor Magenta
        foreach ($f in $g.Group) {
            Write-Host "      -> $($f.FullName) ($(Format-Size $f.Length))" -ForegroundColor DarkGray
        }
    }
} else {
    Write-Host "  Aucun doublon >50MB détecté à la racine du projet" -ForegroundColor Green
}
Write-Host ""

# ------------------------------------------------------------------------
# 5. Archive data_heavy - état actuel
# ------------------------------------------------------------------------
Write-Host "[5/5] État de archive\data_heavy" -ForegroundColor Yellow
$archiveData = Join-Path $ProjectRoot 'archive\data_heavy'
if (Test-Path $archiveData) {
    $archSize = Get-FolderSize $archiveData
    Write-Host "  Présent - $(Format-Size $archSize)" -ForegroundColor Yellow
    Get-ChildItem $archiveData -Force -ErrorAction SilentlyContinue | ForEach-Object {
        Write-Host "      $($_.Name) - $(Format-Size $_.Length)" -ForegroundColor DarkGray
    }
} else {
    Write-Host "  Absent (déjà supprimé ou jamais créé)" -ForegroundColor Green
}
Write-Host ""

Write-Host "==============================================" -ForegroundColor Green
Write-Host " ANALYSE TERMINÉE" -ForegroundColor Green
Write-Host "==============================================" -ForegroundColor Green
