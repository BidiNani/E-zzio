# ==============================================================================
# E-ZZIO - NETTOYAGE .git + SUPPRESSION STUBS REDONDANTS core/
# ==============================================================================

$ProjectRoot = "G:\AI\E-zzio"
Set-Location $ProjectRoot

function Format-Size($bytes) {
    if ($bytes -ge 1GB) { return "{0:N2} GB" -f ($bytes / 1GB) }
    elseif ($bytes -ge 1MB) { return "{0:N2} MB" -f ($bytes / 1MB) }
    elseif ($bytes -ge 1KB) { return "{0:N2} KB" -f ($bytes / 1KB) }
    else { return "$bytes B" }
}

Write-Host "==============================================" -ForegroundColor Cyan
Write-Host " E-ZZIO - NETTOYAGE .git + STUBS core/" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""

# ==============================================================================
# PARTIE 1 : DIAGNOSTIC .git
# ==============================================================================
Write-Host "[1/6] Diagnostic du dépôt .git..." -ForegroundColor Yellow

if (-not (Test-Path ".git")) {
    Write-Host "  Pas de dépôt git ici, on saute cette partie." -ForegroundColor Red
} else {
    Write-Host ""
    git count-objects -vH
    Write-Host ""

    Write-Host "[2/6] Recherche des plus gros objets dans l'historique git (top 15)..." -ForegroundColor Yellow
    Write-Host "  (ceci peut prendre 30s-2min selon la taille de l'historique)" -ForegroundColor DarkGray
    Write-Host ""

    # Liste les plus gros blobs de l'historique complet, avec leur chemin
    $bigObjects = git rev-list --objects --all |
        git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' |
        Where-Object { $_ -match '^blob' } |
        ForEach-Object {
            $parts = $_ -split ' ', 4
            [PSCustomObject]@{
                Size = [int64]$parts[2]
                Path = $parts[3]
            }
        } | Sort-Object Size -Descending | Select-Object -First 15

    $bigObjects | ForEach-Object {
        Write-Host ("  {0,10} - {1}" -f (Format-Size $_.Size), $_.Path) -ForegroundColor Magenta
    }
    Write-Host ""
    Write-Host "  Si des fichiers lourds (models, .db, backups) apparaissent ci-dessus," -ForegroundColor DarkGray
    Write-Host "  c'est probablement pourquoi .git pèse $(git count-objects -vH | Select-String 'size-pack')" -ForegroundColor DarkGray
    Write-Host ""

    Write-Host "[3/6] Nettoyage local (gc + prune) - SANS réécrire l'historique..." -ForegroundColor Yellow
    Write-Host "  Ceci ne supprime PAS les gros fichiers de l'historique, juste le garbage collection standard." -ForegroundColor DarkGray
    $before = (git count-objects -v | Select-String 'size-pack').ToString()
    git gc --aggressive --prune=now
    Write-Host "  Terminé." -ForegroundColor Green
    Write-Host ""

    Write-Host "  NOTE IMPORTANTE :" -ForegroundColor Red
    Write-Host "  Si les gros fichiers listés ci-dessus sont dans l'HISTORIQUE (anciens commits)," -ForegroundColor Red
    Write-Host "  le simple 'gc' ne suffira pas à les enlever. Il faudrait réécrire l'historique" -ForegroundColor Red
    Write-Host "  avec 'git filter-repo' (outil séparé à installer) - je ne le fais PAS automatiquement" -ForegroundColor Red
    Write-Host "  car c'est une opération destructive qui réécrit tous les hash de commits." -ForegroundColor Red
    Write-Host ""
}

# ==============================================================================
# PARTIE 2 : STUBS REDONDANTS DANS core/
# ==============================================================================
Write-Host "[4/6] Vérification des références aux 5 stubs avant suppression..." -ForegroundColor Yellow

$stubs = @{
    'provider_manager.py' = 'pc_model_router.py'
    'memory_core.py'      = 'memory.py'
    'tool_engine.py'      = $null
    'guardian_client.py'  = $null
    'persona.py'          = 'ezzio_identity.py'
}

$coreDir = Join-Path $ProjectRoot 'core'
$safeToDelete = @()
$needsReview = @()

foreach ($stub in $stubs.Keys) {
    $stubPath = Join-Path $coreDir $stub
    if (-not (Test-Path $stubPath)) { continue }

    $moduleName = [System.IO.Path]::GetFileNameWithoutExtension($stub)
    # Cherche des imports/références au module dans tout le projet (hors le stub lui-même)
    $refs = Get-ChildItem $ProjectRoot -Recurse -Include *.py -File -Force -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -ne $stubPath } |
        Select-String -Pattern "\b$moduleName\b" -ErrorAction SilentlyContinue

    if ($refs) {
        Write-Host "  [RÉFÉRENCÉ] $stub trouvé dans $($refs.Count) fichier(s) - À VÉRIFIER MANUELLEMENT" -ForegroundColor Red
        $refs | Select-Object -First 5 | ForEach-Object {
            Write-Host "      -> $($_.Path):$($_.LineNumber)" -ForegroundColor DarkGray
        }
        $needsReview += $stub
    } else {
        Write-Host "  [SÛR] $stub - aucune référence trouvée ailleurs dans le projet" -ForegroundColor Green
        $safeToDelete += $stub
    }
}
Write-Host ""

Write-Host "[5/6] Suppression des stubs sûrs..." -ForegroundColor Yellow
if ($safeToDelete.Count -eq 0) {
    Write-Host "  Aucun stub sûr à supprimer (tous référencés, voir ci-dessus)." -ForegroundColor DarkGray
} else {
    # Backup avant suppression
    $backupDir = Join-Path $ProjectRoot 'archive\stubs_backup'
    New-Item -Path $backupDir -ItemType Directory -Force | Out-Null

    foreach ($stub in $safeToDelete) {
        $stubPath = Join-Path $coreDir $stub
        $equivalent = $stubs[$stub]
        Copy-Item $stubPath (Join-Path $backupDir $stub) -Force
        Remove-Item $stubPath -Force
        if ($equivalent) {
            Write-Host "  Supprimé : core\$stub (équivalent existant : core\$equivalent)" -ForegroundColor Green
        } else {
            Write-Host "  Supprimé : core\$stub (aucun équivalent identifié - à créer si besoin)" -ForegroundColor Yellow
        }
    }
    Write-Host "  Backup des stubs dans archive\stubs_backup avant suppression." -ForegroundColor DarkGray
}
Write-Host ""

if ($needsReview.Count -gt 0) {
    Write-Host "  ATTENTION : ces stubs sont référencés ailleurs, non supprimés automatiquement :" -ForegroundColor Red
    $needsReview | ForEach-Object { Write-Host "    - $_" -ForegroundColor Red }
    Write-Host "  Vérifiez les références listées ci-dessus avant de les supprimer manuellement." -ForegroundColor Red
    Write-Host ""
}

# ==============================================================================
# PARTIE 3 : RÉSULTAT FINAL
# ==============================================================================
Write-Host "[6/6] État final" -ForegroundColor Yellow
if (Test-Path ".git") {
    git count-objects -vH
}
Write-Host ""
Write-Host "Fichiers restants dans core/ :" -ForegroundColor Cyan
Get-ChildItem $coreDir -File | Sort-Object Name | ForEach-Object {
    Write-Host "  $($_.Name)" -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "==============================================" -ForegroundColor Green
Write-Host " TERMINÉ" -ForegroundColor Green
Write-Host "==============================================" -ForegroundColor Green
