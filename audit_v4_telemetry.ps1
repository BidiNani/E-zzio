# ==============================================================================
# E-ZZIO STORAGE AUDIT v4.0 - TÉLÉMÉTRIE INTÉGRÉE
# READ ONLY - NO DELETE - NO MOVE - NO MODIFY
# ==============================================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ------------------------------------------------------------------------------
# MOTEUR DE PROGRESSION E-ZZIO (OPTIMISÉ)
# ------------------------------------------------------------------------------
$script:ProgressStart = Get-Date
$script:EZZ_Total = 1
$script:EZZ_Start = Get-Date

function Start-EzzioProgress {
    param(
        [string]$Activity,
        [int]$Total
    )
    $script:EZZ_Total = [Math]::Max($Total, 1)
    $script:EZZ_Start = Get-Date

    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host " $Activity" -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host ""
}

function Update-EzzioProgress {
    param(
        [int]$Current,
        [string]$Status = ""
    )
    # Forçage du type [int] pour éviter l'erreur de conversion Write-Progress
    [int]$percent = [Math]::Min([Math]::Max([Math]::Round(($Current / $script:EZZ_Total) * 100, 0), 0), 100)
    
    $elapsed = (Get-Date) - $script:EZZ_Start
    $speed = if ($elapsed.TotalSeconds -gt 0) { $Current / $elapsed.TotalSeconds } else { 0 }
    $remaining = if ($speed -gt 0) { ($script:EZZ_Total - $Current) / $speed } else { 0 }
    $eta = (Get-Date).AddSeconds($remaining)
    
    # PrivateMemorySize64 isole la RAM réellement allouée au script
    $mem = [Math]::Round((Get-Process -Id $PID).PrivateMemorySize64 / 1MB, 0)

    Write-Progress `
        -Activity "E-ZZIO Télémétrie" `
        -Status "$Status" `
        -PercentComplete $percent `
        -CurrentOperation "$Current / $($script:EZZ_Total) | $([Math]::Round($speed,1)) obj/s | ETA $($eta.ToString('HH:mm:ss')) | RAM ${mem}MB"
}

function Stop-EzzioProgress {
    Write-Progress -Activity "E-ZZIO Télémétrie" -Completed
    $elapsed = (Get-Date) - $script:EZZ_Start
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host (" OPÉRATION TERMINÉE (Durée : {0:hh\:mm\:ss})" -f $elapsed) -ForegroundColor Green
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host ""
}

# ------------------------------------------------------------------------------
# CONFIGURATION AUDIT
# ------------------------------------------------------------------------------
$Root = 'G:\'
$AIPath = 'G:\AI'
$MinHashSize = 50MB
$TopFolders = 20
$TopFiles = 30
$TopExtensions = 15
$ExcludedNames = @('$Recycle.Bin', 'System Volume Information')

function Pause-Exit {
    param([string]$Message)
    Write-Host "`n$Message" -ForegroundColor Red
    Write-Host "Appuie sur Entrée pour fermer..." -ForegroundColor Yellow
    [void][System.Console]::ReadLine()
    exit 1
}

try {
    if (-not (Test-Path -LiteralPath $Root)) { Pause-Exit "Le lecteur $Root est introuvable." }

    $AuditStart = Get-Date
    $Stopwatch = [System.Diagnostics.Stopwatch]::StartNew()

    function Format-Size {
        param([Int64]$Bytes)
        switch ($Bytes) {
            { $_ -ge 1TB } { "{0:N2} TB" -f ($Bytes / 1TB); break }
            { $_ -ge 1GB } { "{0:N2} GB" -f ($Bytes / 1GB); break }
            { $_ -ge 1MB } { "{0:N2} MB" -f ($Bytes / 1MB); break }
            { $_ -ge 1KB } { "{0:N2} KB" -f ($Bytes / 1KB); break }
            default        { "$Bytes B" }
        }
    }

    function Test-ExcludedPath {
        param([string]$Path)
        foreach ($name in $ExcludedNames) {
            if ($Path -match [regex]::Escape("\$name(\\|$)")) { return $true }
        }
        return $false
    }

    $Report = [ordered]@{
        TotalFiles     = 0
        TotalFolders   = 0
        TotalBytes     = 0L
        DuplicateFiles = @()
        Errors         = [System.Collections.Generic.List[string]]::new()
    }

    $allFiles = [System.Collections.Generic.List[object]]::new()
    $folderSet = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)

    Write-Host "`n[1/5] Scan du volume (Phase indéterminée)..." -ForegroundColor Yellow
    $items = Get-ChildItem -LiteralPath $Root -Recurse -Force -ErrorAction SilentlyContinue
    $count = 0

    foreach ($item in $items) {
        $count++
        if (($count % 500) -eq 0) {
            Write-Progress -Activity "Scan Disque" -Status "Analyse en cours" -CurrentOperation "Fichiers: $count | RAM: $([Math]::Round((Get-Process -Id $PID).PrivateMemorySize64/1MB,0))MB"
        }

        if (Test-ExcludedPath $item.FullName) { continue }
        if ($item.PSIsContainer) { [void]$folderSet.Add($item.FullName); continue }

        $allFiles.Add($item)
        $Report.TotalFiles++
        $Report.TotalBytes += [int64]$item.Length
    }
    $Report.TotalFolders = $folderSet.Count
    Write-Progress -Activity "Scan Disque" -Completed

    Write-Host "[2/5] Calcul des Tops ignoré pour l'exemple..." -ForegroundColor DarkGray
    Write-Host "[3/5] Détail G:\AI ignoré pour l'exemple..." -ForegroundColor DarkGray
    Write-Host "[4/5] Extensions ignorées pour l'exemple..." -ForegroundColor DarkGray

    # ==============================================================================
    # PHASE 5 : INTÉGRATION DU PROGRESS ENGINE
    # ==============================================================================
    $phaseA = @($allFiles | Where-Object { $_.Length -ge $MinHashSize } | Group-Object Name, Length | Where-Object { $_.Count -gt 1 })
    $duplicateGroups = [System.Collections.Generic.List[object]]::new()
    
    if ($phaseA.Count -gt 0) {
        # Déclenchement du moteur E-ZZIO
        Start-EzzioProgress -Activity "Hash SHA256 des Doublons (> 50MB)" -Total $phaseA.Count
        
        $groupIndex = 0
        foreach ($group in $phaseA) {
            $groupIndex++
            
            # Mise à jour de la télémétrie en temps réel
            Update-EzzioProgress -Current $groupIndex -Status "Traitement: $($group.Name)"

            $hashes = foreach ($file in $group.Group) {
                try {
                    [PSCustomObject]@{
                        File = $file.FullName
                        Name = $file.Name
                        Length = [int64]$file.Length
                        Hash = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256 -ErrorAction Stop).Hash
                    }
                } catch {
                    $Report.Errors.Add("Hash échoué : $($file.FullName) -> $($_.Exception.Message)")
                }
            }

            foreach ($hg in (@($hashes | Group-Object Hash | Where-Object { $_.Count -gt 1 }))) {
                $size = [int64]$hg.Group[0].Length
                $duplicateGroups.Add([PSCustomObject]@{
                    SizeBytes = $size
                    Count = $hg.Count
                })
            }
        }
        # Arrêt propre du moteur
        Stop-EzzioProgress
    } else {
        Write-Host "`n[5/5] Aucun doublon nécessitant un hashage." -ForegroundColor Green
    }
    
    $Report.DuplicateFiles = @($duplicateGroups | Sort-Object SizeBytes -Descending)
    $Stopwatch.Stop()

    Write-Host "==========================================" -ForegroundColor Green
    Write-Host " AUDIT TERMINÉ" -ForegroundColor Green
    Write-Host "==========================================" -ForegroundColor Green
    Write-Host ("Fichiers : {0:N0}" -f $Report.TotalFiles)
    Write-Host ("Doublons : {0} groupes" -f $Report.DuplicateFiles.Count)
    Write-Host ("Durée    : {0:N2} sec" -f $Stopwatch.Elapsed.TotalSeconds)
    Write-Host ""
}
catch {
    Pause-Exit ("Erreur fatale: $($_.Exception.Message)")
}# ==============================================================================
# E-ZZIO - SUPPRESSION DU DOSSIER ARCHIVE (libération d'espace)
# ==============================================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ProjectRoot = 'G:\AI\E-zzio'
$ArchivePath = Join-Path $ProjectRoot 'archive'

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
Write-Host " E-ZZIO - SUPPRESSION DU DOSSIER ARCHIVE" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path -LiteralPath $ArchivePath)) {
    Write-Host "Le dossier archive n'existe pas." -ForegroundColor Yellow
    Write-Host "Rien à faire."
    exit 0
}

$size = Get-FolderSize $ArchivePath
Write-Host "Dossier   : $ArchivePath" -ForegroundColor White
Write-Host "Taille    : $(Format-Size $size)" -ForegroundColor Yellow
Write-Host ""
Write-Host "ATTENTION : Cette action est IRRÉVERSIBLE." -ForegroundColor Red
Write-Host "Tout le contenu de archive\ va être supprimé." -ForegroundColor Red
Write-Host ""

$confirm = Read-Host "Tape SUPPRIMER pour confirmer"

if ($confirm -eq 'SUPPRIMER') {
    Write-Host ""
    Write-Host "Suppression en cours..." -ForegroundColor Cyan

    try {
        Remove-Item -LiteralPath $ArchivePath -Recurse -Force -ErrorAction Stop
        Write-Host "Dossier archive supprimé avec succès." -ForegroundColor Green
        Write-Host "Espace libéré : $(Format-Size $size)" -ForegroundColor Green
    }
    catch {
        Write-Host "Erreur lors de la suppression : $($_.Exception.Message)" -ForegroundColor Red
    }
}
else {
    Write-Host "Annulé." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Taille actuelle du projet :" -ForegroundColor Cyan
$final = Get-FolderSize $ProjectRoot
Write-Host (Format-Size $final)
Write-Host ""
Write-Host "Appuie sur Entrée pour fermer..."
[void][System.Console]::ReadLine()