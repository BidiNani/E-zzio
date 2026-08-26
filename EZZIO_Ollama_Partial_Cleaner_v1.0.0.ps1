# ============================================================================
# E-ZZIO — OLLAMA PARTIAL CLEANER v1.0.0
# FORENSIC / TARGETED CLEANUP / FAIL-CLOSED / ZERO MODEL BLOB TOUCH
#
# OBJECTIF :
#   Supprimer UNIQUEMENT les blobs Ollama partials identifiés par le
#   FORENSIC OLLAMA BLOB TRUTH ENGINE v4.1.2
#
# PROTECTION :
#   - NE SUPPRIME PAS les blobs complets
#   - NE SUPPRIME PAS les manifests
#   - NE MODIFIE PAS les modèles complets
#   - NE TOUCHE PAS aux fichiers non identifiés
#   - REFUSE si Ollama est en cours d'exécution
#   - REFUSE si une anomalie de structure est détectée
#   - journal JSON + CSV
# ============================================================================

& {

    Set-StrictMode -Version Latest
    $ErrorActionPreference = 'Stop'

    # =========================================================================
    # CONFIGURATION
    # =========================================================================

    $RunId = Get-Date -Format 'yyyyMMdd_HHmmss'

    $OllamaRoot = 'G:\Ollama\Models'
    $BlobRoot   = Join-Path $OllamaRoot 'blobs'
    $AuditRoot  = 'G:\AI\E-zzio\runtime\audit\forensic'

    $JsonOut = Join-Path $AuditRoot "EZZIO_OLLAMA_PARTIAL_CLEANUP_$RunId.json"
    $CsvOut  = Join-Path $AuditRoot "EZZIO_OLLAMA_PARTIAL_CLEANUP_$RunId.csv"

    # Familles prouvées par le forensic v4.1.2
    $ApprovedFamilies = @(
        '1194192cf2a187eb02722edcc3f77b11d21f537048ce04b67ccf8ba78863006a',
        '6e9f90f02bb3b39b59e81916e8cfce9deb45aeaeb9a54a5be4414486b907dc1e',
        '83c54730a5fea8a0958598c01617c1419c431e93b33bacf980b49a420c798926',
        'ac3d1ba8aa77755dab3806d9024e9c385ea0d5b412d6bdf9157f8a4a7e9fc0d9'
    )

    $FatalErrors = 0
    $Deleted = 0
    $Rejected = 0

    $Results = New-Object System.Collections.Generic.List[object]

    # =========================================================================
    # EN-TÊTE
    # =========================================================================

    Write-Host ''
    Write-Host '================================================================================'
    Write-Host '       E-ZZIO — OLLAMA PARTIAL CLEANER v1.0.0'
    Write-Host '       FORENSIC TARGETED CLEANUP / FAIL-CLOSED / ZERO MODEL BLOB TOUCH'
    Write-Host '================================================================================'
    Write-Host ''

    Write-Host "[INFO] RunId       : $RunId"
    Write-Host "[INFO] PowerShell  : $($PSVersionTable.PSVersion)"
    Write-Host "[INFO] Machine     : $env:COMPUTERNAME"
    Write-Host "[INFO] Ollama Root : $OllamaRoot"
    Write-Host "[INFO] Blob Root   : $BlobRoot"
    Write-Host ''

    # =========================================================================
    # [1/8] VALIDATION STRUCTURE
    # =========================================================================

    Write-Host '--------------------------------------------------------------------------------'
    Write-Host '[1/8] VALIDATION DE LA STRUCTURE'
    Write-Host '--------------------------------------------------------------------------------'

    if (-not (Test-Path -LiteralPath $OllamaRoot -PathType Container)) {
        Write-Host "[FAIL] Ollama Root introuvable : $OllamaRoot" -ForegroundColor Red
        $FatalErrors++
    }
    else {
        Write-Host "[PASS] $OllamaRoot"
    }

    if (-not (Test-Path -LiteralPath $BlobRoot -PathType Container)) {
        Write-Host "[FAIL] Blob Root introuvable : $BlobRoot" -ForegroundColor Red
        $FatalErrors++
    }
    else {
        Write-Host "[PASS] $BlobRoot"
    }

    if ($FatalErrors -gt 0) {
        Write-Host ''
        Write-Host '[FAIL-CLOSED] Structure invalide. AUCUNE SUPPRESSION.' -ForegroundColor Red
        exit 2
    }

    # =========================================================================
    # [2/8] VÉRIFICATION OLLAMA
    # =========================================================================

    Write-Host ''
    Write-Host '--------------------------------------------------------------------------------'
    Write-Host '[2/8] VÉRIFICATION DU PROCESSUS OLLAMA'
    Write-Host '--------------------------------------------------------------------------------'

    $OllamaProcesses = @(
        Get-Process -Name 'ollama' -ErrorAction SilentlyContinue
    )

    if ($OllamaProcesses.Count -gt 0) {
        Write-Host ''
        Write-Host '[FAIL] Ollama est actuellement en cours d''exécution.' -ForegroundColor Red
        Write-Host '[FAIL] Nettoyage REFUSÉ afin d''éviter la suppression d''un téléchargement actif.' -ForegroundColor Red
        Write-Host ''
        Write-Host '[INFO] Ferme Ollama puis relance ce script.'
        Write-Host ''
        exit 2
    }

    Write-Host '[PASS] Aucun processus Ollama détecté.'

    # =========================================================================
    # [3/8] INVENTAIRE PHYSIQUE
    # =========================================================================

    Write-Host ''
    Write-Host '--------------------------------------------------------------------------------'
    Write-Host '[3/8] INVENTAIRE DES BLOBS PARTIALS'
    Write-Host '--------------------------------------------------------------------------------'

    $AllBlobFiles = @(
        Get-ChildItem -LiteralPath $BlobRoot -File -Force -ErrorAction Stop
    )

    Write-Host "[INFO] Fichiers physiques dans blobs : $($AllBlobFiles.Count)"

    # =========================================================================
    # [4/8] SÉLECTION STRICTE DES CIBLES
    # =========================================================================

    Write-Host ''
    Write-Host '--------------------------------------------------------------------------------'
    Write-Host '[4/8] SÉLECTION FORENSIC DES CIBLES'
    Write-Host '--------------------------------------------------------------------------------'

    $Targets = New-Object System.Collections.Generic.List[object]

    foreach ($File in $AllBlobFiles) {

        $Name = $File.Name

        # -------------------------------------------------------------
        # Un partial autorisé doit obligatoirement respecter :
        #
        # sha256-<64 hex>-partial...
        # -------------------------------------------------------------

        if ($Name -notmatch '^sha256-([0-9a-fA-F]{64})-partial(?:$|[-_.])') {
            continue
        }

        $Family = $Matches[1].ToLowerInvariant()

        if ($ApprovedFamilies -notcontains $Family) {
            Write-Host "[WARN] Partial hors périmètre forensic : $Name" -ForegroundColor Yellow

            $Results.Add([pscustomobject]@{
                RunId       = $RunId
                Action      = 'REJECTED'
                Family      = $Family
                FileName    = $Name
                Path        = $File.FullName
                SizeBytes   = $File.Length
                SizeGB      = [math]::Round($File.Length / 1GB, 6)
                Reason      = 'PARTIAL_FAMILY_NOT_APPROVED'
            })

            $Rejected++
            continue
        }

        $Targets.Add([pscustomobject]@{
            Family    = $Family
            FileName  = $Name
            FullName  = $File.FullName
            SizeBytes = $File.Length
            SizeGB    = [math]::Round($File.Length / 1GB, 6)
        })
    }

    Write-Host "[INFO] Cibles autorisées : $($Targets.Count)"
    Write-Host "[INFO] Cibles rejetées    : $Rejected"

    if ($Targets.Count -eq 0) {

        Write-Host '[PASS] Aucun partial autorisé à nettoyer.'

        if ($Rejected -gt 0) {
            Write-Host '[WARN] Des partials hors périmètre existent et n''ont PAS été touchés.'
        }

        exit 0
    }

    # =========================================================================
    # [5/8] CONTRÔLE D'INTÉGRITÉ DES CIBLES
    # =========================================================================

    Write-Host ''
    Write-Host '--------------------------------------------------------------------------------'
    Write-Host '[5/8] CONTRÔLE D''INTÉGRITÉ DES CIBLES'
    Write-Host '--------------------------------------------------------------------------------'

    $Grouped = $Targets | Group-Object Family

    foreach ($Group in $Grouped) {

        $Family = $Group.Name
        $Count  = $Group.Count
        $Bytes  = ($Group.Group | Measure-Object -Property SizeBytes -Sum).Sum

        Write-Host ''
        Write-Host "[PARTIAL-FAMILY] $Family"
        Write-Host "    Fichiers     : $Count"
        Write-Host "    Taille       : $([math]::Round($Bytes / 1GB, 6)) Go"

        # Aucun blob complet correspondant ne doit exister.
        $CompleteBlob = Join-Path $BlobRoot "sha256-$Family"

        if (Test-Path -LiteralPath $CompleteBlob -PathType Leaf) {
            Write-Host '[FAIL] Blob complet correspondant détecté.' -ForegroundColor Red
            Write-Host '[FAIL] SUPPRESSION REFUSÉE POUR CETTE FAMILLE.' -ForegroundColor Red

            $FatalErrors++
        }
        else {
            Write-Host '[PASS] Aucun blob complet correspondant.'
        }

        foreach ($Item in $Group.Group) {
            Write-Host "    [TARGET] $($Item.FileName) — $($Item.SizeBytes) octets"
        }
    }

    if ($FatalErrors -gt 0) {
        Write-Host ''
        Write-Host '[FAIL-CLOSED] Une famille possède un blob complet correspondant.' -ForegroundColor Red
        Write-Host '[FAIL-CLOSED] AUCUNE SUPPRESSION EFFECTUÉE.' -ForegroundColor Red
        exit 2
    }

    # =========================================================================
    # [6/8] RÉSUMÉ AVANT SUPPRESSION
    # =========================================================================

    Write-Host ''
    Write-Host '--------------------------------------------------------------------------------'
    Write-Host '[6/8] RÉSUMÉ AVANT SUPPRESSION'
    Write-Host '--------------------------------------------------------------------------------'

    $TotalBytes = ($Targets | Measure-Object -Property SizeBytes -Sum).Sum

    Write-Host "[INFO] Familles autorisées : $($Grouped.Count)"
    Write-Host "[INFO] Fichiers ciblés     : $($Targets.Count)"
    Write-Host "[INFO] Espace à libérer    : $([math]::Round($TotalBytes / 1GB, 6)) Go"
    Write-Host ''
    Write-Host '[INFO] Cibles :'

    $Targets |
        Sort-Object Family, FileName |
        Format-Table `
            @{Label='Family';Expression={$_.Family}}, `
            @{Label='SizeMB';Expression={[math]::Round($_.SizeBytes / 1MB, 3)}}, `
            @{Label='FileName';Expression={$_.FileName}} `
        | Out-Host

    # =========================================================================
    # [7/8] SUPPRESSION CIBLÉE
    # =========================================================================

    Write-Host ''
    Write-Host '--------------------------------------------------------------------------------'
    Write-Host '[7/8] SUPPRESSION CIBLÉE'
    Write-Host '--------------------------------------------------------------------------------'

    foreach ($Target in $Targets) {

        # Double vérification avant chaque suppression.
        if (-not (Test-Path -LiteralPath $Target.FullName -PathType Leaf)) {
            Write-Host "[WARN] Déjà absent : $($Target.FileName)" -ForegroundColor Yellow
            continue
        }

        $Current = Get-Item -LiteralPath $Target.FullName -Force

        if ($Current.Name -ne $Target.FileName) {
            Write-Host "[FAIL] Mutation de nom détectée : $($Target.FullName)" -ForegroundColor Red
            $FatalErrors++
            continue
        }

        if ($Current.DirectoryName -ne $BlobRoot) {
            Write-Host "[FAIL] Chemin hors BlobRoot : $($Target.FullName)" -ForegroundColor Red
            $FatalErrors++
            continue
        }

        if ($Current.Name -notmatch '^sha256-([0-9a-fA-F]{64})-partial(?:$|[-_.])') {
            Write-Host "[FAIL] Nom non conforme : $($Current.Name)" -ForegroundColor Red
            $FatalErrors++
            continue
        }

        $FamilyCheck = $Matches[1].ToLowerInvariant()

        if ($ApprovedFamilies -notcontains $FamilyCheck) {
            Write-Host "[FAIL] Famille non autorisée : $FamilyCheck" -ForegroundColor Red
            $FatalErrors++
            continue
        }

        try {

            Remove-Item -LiteralPath $Target.FullName -Force -ErrorAction Stop

            if (Test-Path -LiteralPath $Target.FullName -PathType Leaf) {
                Write-Host "[FAIL] Suppression non confirmée : $($Target.FileName)" -ForegroundColor Red
                $FatalErrors++
                continue
            }

            Write-Host "[PASS] SUPPRIMÉ : $($Target.FileName)"

            $Results.Add([pscustomobject]@{
                RunId       = $RunId
                Action      = 'DELETED'
                Family      = $Target.Family
                FileName    = $Target.FileName
                Path        = $Target.FullName
                SizeBytes   = $Target.SizeBytes
                SizeGB      = $Target.SizeGB
                Reason      = 'FORENSIC_APPROVED_PARTIAL'
            })

            $Deleted++

        }
        catch {

            Write-Host "[FAIL] Suppression impossible : $($Target.FileName)" -ForegroundColor Red
            Write-Host "[FAIL] $($_.Exception.Message)" -ForegroundColor Red

            $FatalErrors++

            $Results.Add([pscustomobject]@{
                RunId       = $RunId
                Action      = 'DELETE_FAILED'
                Family      = $Target.Family
                FileName    = $Target.FileName
                Path        = $Target.FullName
                SizeBytes   = $Target.SizeBytes
                SizeGB      = $Target.SizeGB
                Reason      = $_.Exception.Message
            })
        }
    }

    # =========================================================================
    # [8/8] RECONTRÔLE POST-NETTOYAGE
    # =========================================================================

    Write-Host ''
    Write-Host '--------------------------------------------------------------------------------'
    Write-Host '[8/8] RECONTRÔLE POST-NETTOYAGE'
    Write-Host '--------------------------------------------------------------------------------'

    $RemainingApproved = @()

    foreach ($Family in $ApprovedFamilies) {

        $Pattern = "sha256-$Family-partial*"

        $Found = @(
            Get-ChildItem `
                -LiteralPath $BlobRoot `
                -File `
                -Force `
                -ErrorAction Stop |
            Where-Object {
                $_.Name -like $Pattern
            }
        )

        if ($Found.Count -gt 0) {
            $RemainingApproved += $Found
        }

        Write-Host "[INFO] Famille $Family : $($Found.Count) partial(s) restant(s)"
    }

    Write-Host ''
    Write-Host "[INFO] Suppressions confirmées : $Deleted"
    Write-Host "[INFO] Restants autorisés       : $($RemainingApproved.Count)"
    Write-Host "[INFO] Rejets hors périmètre   : $Rejected"
    Write-Host "[INFO] Erreurs                  : $FatalErrors"

    # =========================================================================
    # EXPORT AUDIT
    # =========================================================================

    if (-not (Test-Path -LiteralPath $AuditRoot -PathType Container)) {
        New-Item -ItemType Directory -Path $AuditRoot -Force | Out-Null
    }

    $Summary = [pscustomobject]@{
        Engine                  = 'E-ZZIO OLLAMA PARTIAL CLEANER'
        Version                 = '1.0.0'
        RunId                   = $RunId
        OllamaRoot              = $OllamaRoot
        BlobRoot                = $BlobRoot
        ApprovedFamilies        = $ApprovedFamilies.Count
        TargetFiles             = $Targets.Count
        DeletedFiles            = $Deleted
        RemainingApproved       = $RemainingApproved.Count
        RejectedFiles           = $Rejected
        FatalErrors             = $FatalErrors
        ReadOnlyBeforeCleanup   = $true
        CompleteBlobsTouched    = $false
        ManifestsTouched        = $false
        Verdict                 = if (($FatalErrors -eq 0) -and ($RemainingApproved.Count -eq 0)) {
            'CLEANUP_PASS'
        }
        else {
            'CLEANUP_FAIL'
        }
    }

    $ExportObject = [pscustomobject]@{
        Summary = $Summary
        Results = @($Results)
    }

    $ExportObject |
        ConvertTo-Json -Depth 10 |
        Set-Content -LiteralPath $JsonOut -Encoding UTF8

    if ($Results.Count -gt 0) {
        $Results |
            Export-Csv -LiteralPath $CsvOut -NoTypeInformation -Encoding UTF8
    }

    # =========================================================================
    # VERDICT FINAL
    # =========================================================================

    Write-Host ''
    Write-Host '================================================================================'
    Write-Host '              E-ZZIO — OLLAMA PARTIAL CLEANUP VERDICT'
    Write-Host '================================================================================'
    Write-Host ''

    if (($FatalErrors -eq 0) -and ($RemainingApproved.Count -eq 0)) {

        Write-Host '[PASS] VERDICT : CLEANUP_PASS' -ForegroundColor Green
        Write-Host ''
        Write-Host '[PASS] Les partials forensic autorisés ont été supprimés.'
        Write-Host '[PASS] Aucun blob complet supprimé.'
        Write-Host '[PASS] Aucun manifest modifié.'
        Write-Host '[PASS] Aucun modèle complet modifié.'
        Write-Host "[PASS] Fichiers supprimés : $Deleted"
        Write-Host ''
        Write-Host '[INFO] JSON audit :'
        Write-Host "       $JsonOut"
        Write-Host ''
        Write-Host '[INFO] CSV audit :'
        Write-Host "       $CsvOut"

        $ExitCode = 0
    }
    else {

        Write-Host '[FAIL] VERDICT : CLEANUP_FAIL' -ForegroundColor Red
        Write-Host ''
        Write-Host "[FAIL] Erreurs       : $FatalErrors"
        Write-Host "[FAIL] Partials restants : $($RemainingApproved.Count)"
        Write-Host ''
        Write-Host '[FAIL-CLOSED] Le nettoyage ne peut pas être certifié complet.'

        $ExitCode = 2
    }

    Write-Host ''
    Write-Host '--------------------------------------------------------------------------------'
    Write-Host ' CONTRAINTES DE SÉCURITÉ'
    Write-Host '--------------------------------------------------------------------------------'
    Write-Host '[PASS] Suppression limitée aux 4 familles forensic approuvées'
    Write-Host '[PASS] Blob complet sha256-* protégé'
    Write-Host '[PASS] Manifests protégés'
    Write-Host '[PASS] Modèles complets protégés'
    Write-Host '[PASS] Ollama arrêté avant mutation'
    Write-Host '[PASS] Vérification post-suppression'
    Write-Host '[PASS] Journal JSON'
    Write-Host '[PASS] Journal CSV'

    Write-Host ''
    Write-Host '================================================================================'
    Write-Host ' E-ZZIO — OLLAMA PARTIAL CLEANER v1.0.0 — TERMINÉ'
    Write-Host '================================================================================'
    Write-Host ''
    Write-Host "[INFO] RunId          : $RunId"
    Write-Host "[INFO] Verdict        : $($Summary.Verdict)"
    Write-Host "[INFO] DeletedFiles   : $Deleted"
    Write-Host "[INFO] Remaining      : $($RemainingApproved.Count)"
    Write-Host "[INFO] FatalErrors    : $FatalErrors"
    Write-Host "[INFO] EZZIO_ExitCode : $ExitCode"
    Write-Host ''

    exit $ExitCode
}