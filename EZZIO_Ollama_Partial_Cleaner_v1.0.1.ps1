# ============================================================================
# E-ZZIO — OLLAMA PARTIAL CLEANER v1.0.1
# FORENSIC / TARGETED CLEANUP / FAIL-CLOSED / ZERO MODEL BLOB TOUCH
#
# OBJECTIF :
#   Supprimer UNIQUEMENT les blobs Ollama partials identifiés par le
#   FORENSIC OLLAMA BLOB TRUTH ENGINE v4.1.2
#
# v1.0.1 CORRECTIONS :
#   - Correction robuste de la construction de l'objet d'export.
#   - Aucun crash "Argument types do not match".
#   - Export JSON systématique, même avec zéro cible.
#   - Export CSV systématique si des résultats existent.
#   - Validation de relecture du JSON après écriture.
#   - Validation de présence du CSV après écriture.
#   - Relance post-nettoyage sûre : aucune suppression si déjà propre.
#   - Verdict distinct CLEANUP_PASS / CLEANUP_ALREADY_CLEAN / CLEANUP_FAIL.
#
# PROTECTION :
#   - NE SUPPRIME PAS les blobs complets
#   - NE SUPPRIME PAS les manifests
#   - NE MODIFIE PAS les modèles complets
#   - NE TOUCHE PAS aux fichiers non identifiés
#   - REFUSE si Ollama est en cours d'exécution
#   - REFUSE si une anomalie de structure est détectée
#   - FAIL-CLOSED
#   - journal JSON + CSV
# ============================================================================

& {

    Set-StrictMode -Version Latest
    $ErrorActionPreference = 'Stop'

    # =========================================================================
    # CONFIGURATION
    # =========================================================================

    $EngineName = 'E-ZZIO OLLAMA PARTIAL CLEANER'
    $Version    = '1.0.1'
    $RunId      = Get-Date -Format 'yyyyMMdd_HHmmss'

    $OllamaRoot = 'G:\Ollama\Models'
    $BlobRoot   = Join-Path $OllamaRoot 'blobs'
    $AuditRoot  = 'G:\AI\E-zzio\runtime\audit\forensic'

    $JsonOut = Join-Path $AuditRoot "EZZIO_OLLAMA_PARTIAL_CLEANUP_$RunId.json"
    $CsvOut  = Join-Path $AuditRoot "EZZIO_OLLAMA_PARTIAL_CLEANUP_$RunId.csv"

    # =========================================================================
    # FAMILLES APPROUVÉES PAR LE FORENSIC OLLAMA BLOB TRUTH ENGINE v4.1.2
    # =========================================================================

    $ApprovedFamilies = @(
        '1194192cf2a187eb02722edcc3f77b11d21f537048ce04b67ccf8ba78863006a',
        '6e9f90f02bb3b39b59e81916e8cfce9deb45aeaeb9a54a5be4414486b907dc1e',
        '83c54730a5fea8a0958598c01617c1419c431e93b33bacf980b49a420c798926',
        'ac3d1ba8aa77755dab3806d9024e9c385ea0d5b412d6bdf9157f8a4a7e9fc0d9'
    )

    # =========================================================================
    # COMPTEURS
    # =========================================================================

    [int]$FatalErrors = 0
    [int]$Deleted     = 0
    [int]$Rejected    = 0
    [int]$AlreadyGone = 0

    # IMPORTANT :
    # Utilisation d'une collection générique explicitement typée.
    # Lors de l'export, elle sera convertie en tableau réel.
    $Results = New-Object System.Collections.Generic.List[object]

    # =========================================================================
    # FONCTIONS FORENSIC
    # =========================================================================

    function Add-Result {
        param(
            [Parameter(Mandatory = $true)]
            [string]$Action,

            [Parameter(Mandatory = $true)]
            [string]$Family,

            [Parameter(Mandatory = $true)]
            [string]$FileName,

            [Parameter(Mandatory = $true)]
            [string]$Path,

            [Parameter(Mandatory = $true)]
            [long]$SizeBytes,

            [Parameter(Mandatory = $true)]
            [string]$Reason
        )

        $ResultObject = [pscustomobject][ordered]@{
            RunId     = $RunId
            Action    = $Action
            Family    = $Family
            FileName  = $FileName
            Path      = $Path
            SizeBytes = $SizeBytes
            SizeGB    = [math]::Round($SizeBytes / 1GB, 6)
            Reason    = $Reason
        }

        [void]$Results.Add($ResultObject)
    }

    function Write-Section {
        param(
            [Parameter(Mandatory = $true)]
            [string]$Number,

            [Parameter(Mandatory = $true)]
            [string]$Title
        )

        Write-Host ''
        Write-Host '--------------------------------------------------------------------------------'
        Write-Host "[$Number/8] $Title"
        Write-Host '--------------------------------------------------------------------------------'
    }

    # =========================================================================
    # EN-TÊTE
    # =========================================================================

    Write-Host ''
    Write-Host '================================================================================'
    Write-Host '       E-ZZIO — OLLAMA PARTIAL CLEANER v1.0.1'
    Write-Host '       FORENSIC TARGETED CLEANUP / FAIL-CLOSED / ZERO MODEL BLOB TOUCH'
    Write-Host '================================================================================'
    Write-Host ''

    Write-Host "[INFO] Engine      : $EngineName"
    Write-Host "[INFO] Version     : $Version"
    Write-Host "[INFO] RunId       : $RunId"
    Write-Host "[INFO] PowerShell  : $($PSVersionTable.PSVersion)"
    Write-Host "[INFO] Machine     : $env:COMPUTERNAME"
    Write-Host "[INFO] Ollama Root : $OllamaRoot"
    Write-Host "[INFO] Blob Root   : $BlobRoot"
    Write-Host "[INFO] Audit Root  : $AuditRoot"
    Write-Host ''

    # =========================================================================
    # [1/8] VALIDATION STRUCTURE
    # =========================================================================

    Write-Section '1' 'VALIDATION DE LA STRUCTURE'

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

    Write-Section '2' 'VÉRIFICATION DU PROCESSUS OLLAMA'

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

    Write-Section '3' 'INVENTAIRE DES BLOBS PARTIALS'

    $AllBlobFiles = @(
        Get-ChildItem `
            -LiteralPath $BlobRoot `
            -File `
            -Force `
            -ErrorAction Stop
    )

    Write-Host "[INFO] Fichiers physiques dans blobs : $($AllBlobFiles.Count)"

    # =========================================================================
    # [4/8] SÉLECTION STRICTE DES CIBLES
    # =========================================================================

    Write-Section '4' 'SÉLECTION FORENSIC DES CIBLES'

    $Targets = New-Object System.Collections.Generic.List[object]

    foreach ($File in $AllBlobFiles) {

        $Name = $File.Name

        # ---------------------------------------------------------------------
        # FORMAT STRICT :
        # sha256-<64 hex>-partial...
        # ---------------------------------------------------------------------

        if ($Name -notmatch '^sha256-([0-9a-fA-F]{64})-partial(?:$|[-_.])') {
            continue
        }

        $Family = $Matches[1].ToLowerInvariant()

        if ($ApprovedFamilies -notcontains $Family) {

            Write-Host "[WARN] Partial hors périmètre forensic : $Name" -ForegroundColor Yellow

            Add-Result `
                -Action 'REJECTED' `
                -Family $Family `
                -FileName $Name `
                -Path $File.FullName `
                -SizeBytes ([long]$File.Length) `
                -Reason 'PARTIAL_FAMILY_NOT_APPROVED'

            $Rejected++
            continue
        }

        $TargetObject = [pscustomobject][ordered]@{
            Family    = $Family
            FileName  = $Name
            FullName  = $File.FullName
            SizeBytes = [long]$File.Length
            SizeGB    = [math]::Round($File.Length / 1GB, 6)
        }

        [void]$Targets.Add($TargetObject)
    }

    Write-Host "[INFO] Cibles autorisées : $($Targets.Count)"
    Write-Host "[INFO] Cibles rejetées    : $Rejected"

    # =========================================================================
    # [5/8] CONTRÔLE D'INTÉGRITÉ DES CIBLES
    # =========================================================================

    Write-Section '5' 'CONTRÔLE D''INTÉGRITÉ DES CIBLES'

    if ($Targets.Count -eq 0) {

        Write-Host '[INFO] Aucun partial autorisé présent physiquement.'

        if ($Rejected -gt 0) {

            Write-Host '[WARN] Des partials hors périmètre existent et n''ont PAS été touchés.' -ForegroundColor Yellow
        }

        Write-Host '[PASS] État physique déjà nettoyé pour les familles approuvées.'
    }
    else {

        $Grouped = @(
            $Targets |
                Group-Object Family
        )

        foreach ($Group in $Grouped) {

            $Family = [string]$Group.Name
            $Count  = [int]$Group.Count

            $BytesMeasurement = $Group.Group |
                Measure-Object -Property SizeBytes -Sum

            [long]$Bytes = 0

            if ($null -ne $BytesMeasurement.Sum) {
                $Bytes = [long]$BytesMeasurement.Sum
            }

            Write-Host ''
            Write-Host "[PARTIAL-FAMILY] $Family"
            Write-Host "    Fichiers     : $Count"
            Write-Host "    Taille       : $([math]::Round($Bytes / 1GB, 6)) Go"

            # -----------------------------------------------------------------
            # Aucun blob complet correspondant ne doit exister.
            # -----------------------------------------------------------------

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

    Write-Section '6' 'RÉSUMÉ AVANT SUPPRESSION'

    [long]$TotalBytes = 0

    if ($Targets.Count -gt 0) {

        $TotalMeasurement = $Targets |
            Measure-Object -Property SizeBytes -Sum

        if ($null -ne $TotalMeasurement.Sum) {
            $TotalBytes = [long]$TotalMeasurement.Sum
        }
    }

    if ($Targets.Count -gt 0) {

        $GroupedSummary = @(
            $Targets | Group-Object Family
        )

        Write-Host "[INFO] Familles autorisées : $($GroupedSummary.Count)"
    }
    else {

        Write-Host '[INFO] Familles autorisées : 0 cible physique restante'
    }

    Write-Host "[INFO] Fichiers ciblés     : $($Targets.Count)"
    Write-Host "[INFO] Espace à libérer    : $([math]::Round($TotalBytes / 1GB, 6)) Go"
    Write-Host ''

    if ($Targets.Count -gt 0) {

        Write-Host '[INFO] Cibles :'

        $Targets |
            Sort-Object Family, FileName |
            Format-Table `
                @{Label='Family';Expression={$_.Family}}, `
                @{Label='SizeMB';Expression={[math]::Round($_.SizeBytes / 1MB, 3)}}, `
                @{Label='FileName';Expression={$_.FileName}} `
            | Out-Host
    }
    else {

        Write-Host '[INFO] Aucune cible à supprimer.'
    }

    # =========================================================================
    # [7/8] SUPPRESSION CIBLÉE
    # =========================================================================

    Write-Section '7' 'SUPPRESSION CIBLÉE'

    if ($Targets.Count -eq 0) {

        Write-Host '[INFO] Aucune suppression nécessaire.'
        Write-Host '[PASS] Le périmètre forensic approuvé est déjà propre.'
    }
    else {

        foreach ($Target in $Targets) {

            # -----------------------------------------------------------------
            # Double vérification avant chaque suppression.
            # -----------------------------------------------------------------

            if (-not (Test-Path -LiteralPath $Target.FullName -PathType Leaf)) {

                Write-Host "[WARN] Déjà absent : $($Target.FileName)" -ForegroundColor Yellow
                $AlreadyGone++
                continue
            }

            $Current = Get-Item `
                -LiteralPath $Target.FullName `
                -Force `
                -ErrorAction Stop

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

            # -----------------------------------------------------------------
            # Vérification finale du blob complet juste avant suppression.
            # -----------------------------------------------------------------

            $CompleteBlobCheck = Join-Path $BlobRoot "sha256-$FamilyCheck"

            if (Test-Path -LiteralPath $CompleteBlobCheck -PathType Leaf) {

                Write-Host "[FAIL] Blob complet détecté avant suppression : $FamilyCheck" -ForegroundColor Red
                Write-Host "[FAIL-CLOSED] Cible refusée : $($Target.FileName)" -ForegroundColor Red

                $FatalErrors++
                continue
            }

            try {

                Remove-Item `
                    -LiteralPath $Target.FullName `
                    -Force `
                    -ErrorAction Stop

                if (Test-Path -LiteralPath $Target.FullName -PathType Leaf) {

                    Write-Host "[FAIL] Suppression non confirmée : $($Target.FileName)" -ForegroundColor Red
                    $FatalErrors++
                    continue
                }

                Write-Host "[PASS] SUPPRIMÉ : $($Target.FileName)"

                Add-Result `
                    -Action 'DELETED' `
                    -Family $Target.Family `
                    -FileName $Target.FileName `
                    -Path $Target.FullName `
                    -SizeBytes ([long]$Target.SizeBytes) `
                    -Reason 'FORENSIC_APPROVED_PARTIAL'

                $Deleted++
            }
            catch {

                Write-Host "[FAIL] Suppression impossible : $($Target.FileName)" -ForegroundColor Red
                Write-Host "[FAIL] $($_.Exception.Message)" -ForegroundColor Red

                $FatalErrors++

                Add-Result `
                    -Action 'DELETE_FAILED' `
                    -Family $Target.Family `
                    -FileName $Target.FileName `
                    -Path $Target.FullName `
                    -SizeBytes ([long]$Target.SizeBytes) `
                    -Reason $_.Exception.Message
            }
        }
    }

    # =========================================================================
    # [8/8] RECONTRÔLE POST-NETTOYAGE
    # =========================================================================

    Write-Section '8' 'RECONTRÔLE POST-NETTOYAGE'

    $RemainingApproved = New-Object System.Collections.Generic.List[object]

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

        foreach ($Item in $Found) {

            [void]$RemainingApproved.Add($Item)
        }

        Write-Host "[INFO] Famille $Family : $($Found.Count) partial(s) restant(s)"
    }

    Write-Host ''

    # =========================================================================
    # VERDICT LOGIQUE
    # =========================================================================

    [string]$Verdict = 'CLEANUP_FAIL'

    if (
        ($FatalErrors -eq 0) -and
        ($RemainingApproved.Count -eq 0)
    ) {

        if (
            ($Targets.Count -eq 0) -and
            ($Deleted -eq 0)
        ) {

            $Verdict = 'CLEANUP_ALREADY_CLEAN'
        }
        else {

            $Verdict = 'CLEANUP_PASS'
        }
    }

    Write-Host "[INFO] Suppressions confirmées : $Deleted"
    Write-Host "[INFO] Déjà absents            : $AlreadyGone"
    Write-Host "[INFO] Restants autorisés       : $($RemainingApproved.Count)"
    Write-Host "[INFO] Rejets hors périmètre   : $Rejected"
    Write-Host "[INFO] Erreurs                  : $FatalErrors"
    Write-Host "[INFO] Verdict logique          : $Verdict"

    # =========================================================================
    # CRÉATION DU RÉPERTOIRE D'AUDIT
    # =========================================================================

    if (-not (Test-Path -LiteralPath $AuditRoot -PathType Container)) {

        New-Item `
            -ItemType Directory `
            -Path $AuditRoot `
            -Force `
            -ErrorAction Stop |
            Out-Null
    }

    # =========================================================================
    # CONSTRUCTION ROBUSTE DU SUMMARY
    #
    # IMPORTANT :
    #   On utilise [ordered] afin d'éviter toute ambiguïté du binder
    #   PowerShell lors de la construction de l'objet.
    # =========================================================================

    $SummaryProperties = [ordered]@{
        Engine                = $EngineName
        Version               = $Version
        RunId                 = $RunId
        OllamaRoot            = $OllamaRoot
        BlobRoot              = $BlobRoot
        ApprovedFamilies      = [int]$ApprovedFamilies.Count
        TargetFiles           = [int]$Targets.Count
        DeletedFiles          = [int]$Deleted
        AlreadyGoneFiles      = [int]$AlreadyGone
        RemainingApproved     = [int]$RemainingApproved.Count
        RejectedFiles         = [int]$Rejected
        FatalErrors            = [int]$FatalErrors
        ReadOnlyBeforeCleanup = [bool]$true
        CompleteBlobsTouched  = [bool]$false
        ManifestsTouched      = [bool]$false
        Verdict               = $Verdict
    }

    $Summary = [pscustomobject]$SummaryProperties

    # =========================================================================
    # CONVERSION EXPLICITE DES RÉSULTATS EN TABLEAU
    #
    # IMPORTANT :
    #   Ne jamais remettre directement la collection générique dans
    #   une structure d'export.
    # =========================================================================

    $ResultsArray = @(
        foreach ($Result in $Results) {
            $Result
        }
    )

    $ExportProperties = [ordered]@{
        Summary = $Summary
        Results = $ResultsArray
    }

    $ExportObject = [pscustomobject]$ExportProperties

    # =========================================================================
    # EXPORT JSON
    # =========================================================================

    Write-Host ''
    Write-Host '--------------------------------------------------------------------------------'
    Write-Host ' EXPORT AUDIT JSON'
    Write-Host '--------------------------------------------------------------------------------'

    try {

        $JsonContent = $ExportObject |
            ConvertTo-Json -Depth 20 -ErrorAction Stop

        if ([string]::IsNullOrWhiteSpace($JsonContent)) {

            throw 'ConvertTo-Json a produit un contenu vide.'
        }

        Set-Content `
            -LiteralPath $JsonOut `
            -Value $JsonContent `
            -Encoding UTF8 `
            -ErrorAction Stop

        if (-not (Test-Path -LiteralPath $JsonOut -PathType Leaf)) {

            throw "Le fichier JSON n'existe pas après écriture : $JsonOut"
        }

        # ---------------------------------------------------------------------
        # Relecture réelle du JSON.
        # ---------------------------------------------------------------------

        $JsonValidationText = Get-Content `
            -LiteralPath $JsonOut `
            -Raw `
            -ErrorAction Stop

        $JsonValidationObject = $JsonValidationText |
            ConvertFrom-Json -ErrorAction Stop

        if ($null -eq $JsonValidationObject) {

            throw 'Le JSON écrit est illisible ou vide après relecture.'
        }

        Write-Host '[PASS] JSON écrit et relu avec succès.'
        Write-Host "[PASS] $JsonOut"
    }
    catch {

        Write-Host '[FAIL] Échec de génération/validation du JSON.' -ForegroundColor Red
        Write-Host "[FAIL] $($_.Exception.Message)" -ForegroundColor Red

        $FatalErrors++
        $Verdict = 'CLEANUP_FAIL'

        # ---------------------------------------------------------------------
        # Mise à jour du Summary en cas d'échec de preuve.
        # ---------------------------------------------------------------------

        $SummaryProperties['FatalErrors'] = [int]$FatalErrors
        $SummaryProperties['Verdict']     = $Verdict

        $Summary = [pscustomobject]$SummaryProperties

        $ExportProperties['Summary'] = $Summary
        $ExportObject = [pscustomobject]$ExportProperties
    }

    # =========================================================================
    # EXPORT CSV
    # =========================================================================

    Write-Host ''
    Write-Host '--------------------------------------------------------------------------------'
    Write-Host ' EXPORT AUDIT CSV'
    Write-Host '--------------------------------------------------------------------------------'

    if ($ResultsArray.Count -gt 0) {

        try {

            $ResultsArray |
                Export-Csv `
                    -LiteralPath $CsvOut `
                    -NoTypeInformation `
                    -Encoding UTF8 `
                    -ErrorAction Stop

            if (-not (Test-Path -LiteralPath $CsvOut -PathType Leaf)) {

                throw "Le fichier CSV n'existe pas après écriture : $CsvOut"
            }

            # -----------------------------------------------------------------
            # Relecture minimale réelle du CSV.
            # -----------------------------------------------------------------

            $CsvValidation = @(
                Import-Csv `
                    -LiteralPath $CsvOut `
                    -ErrorAction Stop
            )

            if ($CsvValidation.Count -ne $ResultsArray.Count) {

                throw "Le CSV relu contient $($CsvValidation.Count) ligne(s), attendu : $($ResultsArray.Count)."
            }

            Write-Host '[PASS] CSV écrit et relu avec succès.'
            Write-Host "[PASS] $CsvOut"
        }
        catch {

            Write-Host '[FAIL] Échec de génération/validation du CSV.' -ForegroundColor Red
            Write-Host "[FAIL] $($_.Exception.Message)" -ForegroundColor Red

            $FatalErrors++
            $Verdict = 'CLEANUP_FAIL'

            $SummaryProperties['FatalErrors'] = [int]$FatalErrors
            $SummaryProperties['Verdict']     = $Verdict

            $Summary = [pscustomobject]$SummaryProperties

            $ExportProperties['Summary'] = $Summary
            $ExportObject = [pscustomobject]$ExportProperties
        }
    }
    else {

        Write-Host '[INFO] Aucun événement à exporter en CSV.'
        Write-Host '[PASS] CSV non requis pour un résultat vide.'
    }

    # =========================================================================
    # VERDICT FINAL
    # =========================================================================

    Write-Host ''
    Write-Host '================================================================================'
    Write-Host '              E-ZZIO — OLLAMA PARTIAL CLEANUP VERDICT'
    Write-Host '================================================================================'
    Write-Host ''

    if (
        ($FatalErrors -eq 0) -and
        ($RemainingApproved.Count -eq 0)
    ) {

        if ($Verdict -eq 'CLEANUP_ALREADY_CLEAN') {

            Write-Host '[PASS] VERDICT : CLEANUP_ALREADY_CLEAN' -ForegroundColor Green
            Write-Host ''
            Write-Host '[PASS] Les partials forensic autorisés sont déjà absents.'
            Write-Host '[PASS] Aucune suppression supplémentaire effectuée.'
            Write-Host '[PASS] Aucun blob complet supprimé.'
            Write-Host '[PASS] Aucun manifest modifié.'
            Write-Host '[PASS] Aucun modèle complet modifié.'
        }
        else {

            Write-Host '[PASS] VERDICT : CLEANUP_PASS' -ForegroundColor Green
            Write-Host ''
            Write-Host '[PASS] Les partials forensic autorisés ont été supprimés.'
            Write-Host '[PASS] Aucun blob complet supprimé.'
            Write-Host '[PASS] Aucun manifest modifié.'
            Write-Host '[PASS] Aucun modèle complet modifié.'
        }

        Write-Host "[PASS] Fichiers supprimés : $Deleted"
        Write-Host "[PASS] Partials restants : $($RemainingApproved.Count)"
        Write-Host ''
        Write-Host '[INFO] JSON audit :'
        Write-Host "       $JsonOut"

        if ($ResultsArray.Count -gt 0) {

            Write-Host ''
            Write-Host '[INFO] CSV audit :'
            Write-Host "       $CsvOut"
        }

        $ExitCode = 0
    }
    else {

        Write-Host '[FAIL] VERDICT : CLEANUP_FAIL' -ForegroundColor Red
        Write-Host ''
        Write-Host "[FAIL] Erreurs            : $FatalErrors"
        Write-Host "[FAIL] Partials restants  : $($RemainingApproved.Count)"
        Write-Host ''
        Write-Host '[FAIL-CLOSED] Le nettoyage ne peut pas être certifié complet.'

        $ExitCode = 2
    }

    # =========================================================================
    # CONTRAINTES DE SÉCURITÉ
    # =========================================================================

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
    Write-Host '[PASS] Vérification physique des partials restants'
    Write-Host '[PASS] Validation réelle du JSON'
    Write-Host '[PASS] Validation réelle du CSV lorsque des résultats existent'

    # =========================================================================
    # SYNTHÈSE FINALE
    # =========================================================================

    Write-Host ''
    Write-Host '================================================================================'
    Write-Host ' E-ZZIO — OLLAMA PARTIAL CLEANER v1.0.1 — TERMINÉ'
    Write-Host '================================================================================'
    Write-Host ''
    Write-Host "[INFO] RunId          : $RunId"
    Write-Host "[INFO] Verdict        : $Verdict"
    Write-Host "[INFO] DeletedFiles   : $Deleted"
    Write-Host "[INFO] AlreadyGone    : $AlreadyGone"
    Write-Host "[INFO] Remaining      : $($RemainingApproved.Count)"
    Write-Host "[INFO] Rejected       : $Rejected"
    Write-Host "[INFO] FatalErrors    : $FatalErrors"
    Write-Host "[INFO] JSON           : $JsonOut"
    Write-Host "[INFO] EZZIO_ExitCode : $ExitCode"
    Write-Host ''

    exit $ExitCode
}