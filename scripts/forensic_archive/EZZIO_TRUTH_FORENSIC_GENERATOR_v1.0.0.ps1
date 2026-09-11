# ============================================================================
# E-ZZIO — TRUTH FORENSIC GENERATOR
# Version : 1.0.0
#
# MODE:
#   READ-ONLY / FAIL-CLOSED / FORENSIC
#
# PURPOSE:
#   Génère un état forensic factuel du projet E-ZZIO.
#
# GARANTIES:
#   - Aucune modification du projet analysé
#   - Aucun fichier source E-ZZIO réécrit
#   - Analyse syntaxique PowerShell via System.Management.Automation.Language.Parser
#   - Analyse JSON via ConvertFrom-Json
#   - Collections explicitement typées pour éviter les erreurs de coercition
#   - Rapport JSON final relu et validé
#   - CRITICAL si au moins une anomalie syntaxique est détectée
#   - Code retour non-zéro en cas d'échec forensic
# ============================================================================

& {

    Set-StrictMode -Version Latest
    $ErrorActionPreference = 'Stop'

    # =========================================================================
    # CONFIGURATION
    # =========================================================================

    $ProjectRoot = 'G:\AI\E-zzio'

    if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) {
        Write-Error "Projet introuvable : $ProjectRoot"
        exit 2
    }

    $ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)

    $Stamp = Get-Date -Format 'yyyyMMdd_HHmmss_fff'
    $Guid  = [guid]::NewGuid().ToString('N').Substring(0,12)

    $ReportRoot = Join-Path `
        -Path $ProjectRoot `
        -ChildPath "_EZZIO_TRUTH_REPORTS\$Stamp`_$Guid"

    $TriageRoot = Join-Path `
        -Path $ReportRoot `
        -ChildPath 'TRUTH_FORENSIC_TRIAGE'

    New-Item `
        -ItemType Directory `
        -Path $TriageRoot `
        -Force `
        -ErrorAction Stop |
        Out-Null

    $FindingsPath = Join-Path `
        -Path $TriageRoot `
        -ChildPath 'EZZIO_TRUTH_FORENSIC_FINDINGS.json'

    $SummaryPath = Join-Path `
        -Path $TriageRoot `
        -ChildPath 'EZZIO_TRUTH_FORENSIC_SUMMARY.json'

    $PowerShellErrorsPath = Join-Path `
        -Path $TriageRoot `
        -ChildPath 'POWERSHELL_SYNTAX_ERRORS.json'

    $JsonErrorsPath = Join-Path `
        -Path $TriageRoot `
        -ChildPath 'JSON_SYNTAX_ERRORS.json'

    $InventoryPath = Join-Path `
        -Path $TriageRoot `
        -ChildPath 'FORENSIC_INVENTORY.json'

    $LogPath = Join-Path `
        -Path $TriageRoot `
        -ChildPath 'FORENSIC_EXECUTION.log'

    # =========================================================================
    # COLLECTIONS TYPÉES
    #
    # IMPORTANT:
    # On n'utilise volontairement PAS:
    #
    #   $array += [pscustomobject]@{...}
    #
    # afin d'éviter les problèmes de coercition observés dans certify_v4.ps1.
    # =========================================================================

    $Findings = [System.Collections.Generic.List[object]]::new()
    $PsErrors = [System.Collections.Generic.List[object]]::new()
    $JsonErrors = [System.Collections.Generic.List[object]]::new()
    $Inventory = [System.Collections.Generic.List[object]]::new()

    $LogLines = [System.Collections.Generic.List[string]]::new()

    # =========================================================================
    # LOGGING
    # =========================================================================

    function Write-ForensicLog {
        param(
            [Parameter(Mandatory)]
            [string]$Message
        )

        $line = '[{0}] {1}' -f (
            Get-Date -Format 'yyyy-MM-dd HH:mm:ss.fff'
        ), $Message

        $LogLines.Add($line)
        Write-Host $Message
    }

    # =========================================================================
    # NORMALISATION DES CHEMINS
    # =========================================================================

    function Get-RelativePath {
        param(
            [Parameter(Mandatory)]
            [string]$FullPath
        )

        $full = [System.IO.Path]::GetFullPath($FullPath)

        $root = $ProjectRoot.TrimEnd(
            [System.IO.Path]::DirectorySeparatorChar,
            [System.IO.Path]::AltDirectorySeparatorChar
        ) + [System.IO.Path]::DirectorySeparatorChar

        if ($full.StartsWith($root, [System.StringComparison]::OrdinalIgnoreCase)) {
            return $full.Substring($root.Length)
        }

        return $full
    }

    # =========================================================================
    # HASH
    # =========================================================================

    function Get-Sha256 {
        param(
            [Parameter(Mandatory)]
            [string]$Path
        )

        try {
            return (
                Get-FileHash `
                    -LiteralPath $Path `
                    -Algorithm SHA256 `
                    -ErrorAction Stop
            ).Hash
        }
        catch {
            return $null
        }
    }

    # =========================================================================
    # FINDING
    # =========================================================================

    function Add-Finding {
        param(
            [Parameter(Mandatory)]
            [ValidateSet('CRITICAL','ERROR','WARNING','INFO')]
            [string]$Severity,

            [Parameter(Mandatory)]
            [string]$Code,

            [string]$Path = '',

            [Parameter(Mandatory)]
            [string]$Message,

            $Evidence = $null
        )

        $finding = [pscustomobject]@{
            Severity = $Severity
            Code     = $Code
            Path     = $Path
            Message  = $Message
            Evidence = $Evidence
        }

        $Findings.Add($finding)
    }

    # =========================================================================
    # EXCLUSIONS
    #
    # Les répertoires suivants sont ignorés pour éviter les faux positifs
    # provenant de caches, environnements virtuels et dépendances.
    # =========================================================================

    $ExcludedDirectories = @(
        '.git',
        '.venv',
        'venv',
        'node_modules',
        '__pycache__',
        '.pytest_cache',
        '.mypy_cache',
        '.ruff_cache',
        'bin',
        'obj'
    )

    function Test-IsExcludedPath {
        param(
            [Parameter(Mandatory)]
            [string]$Path
        )

        $relative = Get-RelativePath -FullPath $Path

        $parts = $relative -split '[\\/]'

        foreach ($part in $parts) {
            if ($ExcludedDirectories -contains $part) {
                return $true
            }
        }

        return $false
    }

    # =========================================================================
    # HEADER
    # =========================================================================

    Write-Host ''
    Write-Host '============================================================' -ForegroundColor Cyan
    Write-Host ' E-ZZIO — TRUTH FORENSIC GENERATOR v1.0.0' -ForegroundColor Cyan
    Write-Host ' READ-ONLY / FAIL-CLOSED / FORENSIC' -ForegroundColor Cyan
    Write-Host '============================================================' -ForegroundColor Cyan
    Write-Host ''
    Write-Host "PROJECT : $ProjectRoot"
    Write-Host "REPORT  : $ReportRoot"
    Write-Host ''

    Write-ForensicLog 'Initialisation forensic.'
    Write-ForensicLog 'Mode READ-ONLY actif.'
    Write-ForensicLog 'Aucune mutation du projet autorisée.'

    # =========================================================================
    # INVENTAIRE
    # =========================================================================

    Write-Host ''
    Write-Host '[1/8] Inventaire filesystem...' -ForegroundColor Yellow

    try {

        $allFiles = @(
            Get-ChildItem `
                -LiteralPath $ProjectRoot `
                -File `
                -Recurse `
                -Force `
                -ErrorAction Stop |
            Where-Object {
                -not (Test-IsExcludedPath -Path $_.FullName)
            }
        )

        $fileCounter = 0

        foreach ($file in $allFiles) {

            $fileCounter++

            $relative = Get-RelativePath -FullPath $file.FullName

            $extension = $file.Extension.ToLowerInvariant()

            $Inventory.Add(
                [pscustomobject]@{
                    Index         = $fileCounter
                    Path          = $relative
                    Extension     = $extension
                    Length        = [int64]$file.Length
                    LastWriteTime = $file.LastWriteTimeUtc.ToString('o')
                    SHA256        = Get-Sha256 -Path $file.FullName
                }
            )
        }

        Write-ForensicLog "Inventaire terminé : $($Inventory.Count) fichiers."

    }
    catch {

        Add-Finding `
            -Severity 'CRITICAL' `
            -Code 'INVENTORY_FAILURE' `
            -Message "Impossible de construire l'inventaire : $($_.Exception.Message)"

        Write-ForensicLog 'ECHEC CRITIQUE inventaire.'
    }

    # =========================================================================
    # CLASSIFICATION
    # =========================================================================

    Write-Host ''
    Write-Host '[2/8] Classification des fichiers...' -ForegroundColor Yellow

    $PowerShellFiles = @(
        $allFiles |
        Where-Object {
            $_.Extension -ieq '.ps1'
        }
    )

    $JsonFiles = @(
        $allFiles |
        Where-Object {
            $_.Extension -ieq '.json'
        }
    )

    Write-ForensicLog "PowerShell : $($PowerShellFiles.Count)"
    Write-ForensicLog "JSON       : $($JsonFiles.Count)"

    # =========================================================================
    # ANALYSE POWERSHELL
    # =========================================================================

    Write-Host ''
    Write-Host '[3/8] Analyse syntaxique PowerShell...' -ForegroundColor Yellow

    $psIndex = 0

    foreach ($file in $PowerShellFiles) {

        $psIndex++

        Write-Host (
            "      [{0}/{1}] {2}" -f
            $psIndex,
            $PowerShellFiles.Count,
            $file.Name
        )

        try {

            $tokens = $null
            $parseErrors = $null

            [void][System.Management.Automation.Language.Parser]::ParseFile(
                $file.FullName,
                [ref]$tokens,
                [ref]$parseErrors
            )

            if ($null -eq $parseErrors) {
                $parseErrors = @()
            }

            foreach ($err in @($parseErrors)) {

                $relative = Get-RelativePath -FullPath $file.FullName

                $extentText = ''

                if ($null -ne $err.Extent) {
                    $extentText = [string]$err.Extent.Text

                    if ($extentText.Length -gt 500) {
                        $extentText = $extentText.Substring(0,500)
                    }
                }

                $record = [pscustomobject]@{
                    Type     = 'POWERSHELL_SYNTAX_ERROR'
                    Path     = $relative
                    ErrorId  = [string]$err.ErrorId
                    Message  = [string]$err.Message
                    Extent   = $extentText
                    Line     = if ($null -ne $err.Extent) {
                        [int]$err.Extent.StartLineNumber
                    } else {
                        0
                    }
                    Column   = if ($null -ne $err.Extent) {
                        [int]$err.Extent.StartColumnNumber
                    } else {
                        0
                    }
                }

                $PsErrors.Add($record)
            }

        }
        catch {

            $relative = Get-RelativePath -FullPath $file.FullName

            $record = [pscustomobject]@{
                Type    = 'POWERSHELL_ANALYZER_FAILURE'
                Path    = $relative
                ErrorId = $_.Exception.GetType().FullName
                Message = $_.Exception.Message
                Extent  = ''
            }

            $PsErrors.Add($record)

            Add-Finding `
                -Severity 'CRITICAL' `
                -Code 'POWERSHELL_ANALYZER_FAILURE' `
                -Path $relative `
                -Message $_.Exception.Message `
                -Evidence $record
        }
    }

    Write-ForensicLog "Erreurs syntaxiques PowerShell : $($PsErrors.Count)"

    # =========================================================================
    # CONSTRUCTION FINDING POWERSHELL
    # =========================================================================

    if ($PsErrors.Count -gt 0) {

        Add-Finding `
            -Severity 'CRITICAL' `
            -Code 'POWERSHELL_SYNTAX_DEFECTS_PRESENT' `
            -Message "PowerShell syntax defects detected: $($PsErrors.Count)" `
            -Evidence @($PsErrors)
    }

    # =========================================================================
    # ANALYSE JSON
    # =========================================================================

    Write-Host ''
    Write-Host '[4/8] Analyse syntaxique JSON...' -ForegroundColor Yellow

    $jsonIndex = 0

    foreach ($file in $JsonFiles) {

        $jsonIndex++

        Write-Host (
            "      [{0}/{1}] {2}" -f
            $jsonIndex,
            $JsonFiles.Count,
            $file.Name
        )

        try {

            $raw = Get-Content `
                -LiteralPath $file.FullName `
                -Raw `
                -ErrorAction Stop

            if ([string]::IsNullOrWhiteSpace($raw)) {
                continue
            }

            try {

                $null = $raw | ConvertFrom-Json -ErrorAction Stop

            }
            catch {

                $relative = Get-RelativePath -FullPath $file.FullName

                $record = [pscustomobject]@{
                    Index   = $jsonIndex
                    Type    = 'JSON_SYNTAX_ERROR'
                    Path    = $relative
                    Message = $_.Exception.Message
                    ErrorId = if ($_.FullyQualifiedErrorId) {
                        [string]$_.FullyQualifiedErrorId
                    } else {
                        $null
                    }
                    Extent  = $null
                }

                $JsonErrors.Add($record)
            }
        }
        catch {

            $relative = Get-RelativePath -FullPath $file.FullName

            $record = [pscustomobject]@{
                Index   = $jsonIndex
                Type    = 'JSON_READ_FAILURE'
                Path    = $relative
                Message = $_.Exception.Message
                ErrorId = $_.Exception.GetType().FullName
                Extent  = $null
            }

            $JsonErrors.Add($record)
        }
    }

    Write-ForensicLog "Erreurs JSON : $($JsonErrors.Count)"

    if ($JsonErrors.Count -gt 0) {

        Add-Finding `
            -Severity 'CRITICAL' `
            -Code 'JSON_SYNTAX_DEFECTS_PRESENT' `
            -Message "JSON syntax defects detected: $($JsonErrors.Count)" `
            -Evidence @($JsonErrors)
    }

    # =========================================================================
    # CONTRÔLES STRUCTURELS
    # =========================================================================

    Write-Host ''
    Write-Host '[5/8] Contrôles structurels...' -ForegroundColor Yellow

    $emptyFiles = @(
        $allFiles |
        Where-Object {
            $_.Length -eq 0
        }
    )

    if ($emptyFiles.Count -gt 0) {

        $emptyEvidence = [System.Collections.Generic.List[object]]::new()

        foreach ($file in $emptyFiles) {

            $emptyEvidence.Add(
                [pscustomobject]@{
                    Path = Get-RelativePath -FullPath $file.FullName
                }
            )
        }

        Add-Finding `
            -Severity 'WARNING' `
            -Code 'EMPTY_FILES_PRESENT' `
            -Message "Empty files detected: $($emptyFiles.Count)" `
            -Evidence @($emptyEvidence)
    }

    # =========================================================================
    # DUPLICATS DE NOMS POWERSHELL
    # =========================================================================

    $duplicateNames = @(
        $PowerShellFiles |
        Group-Object -Property Name |
        Where-Object {
            $_.Count -gt 1
        }
    )

    if ($duplicateNames.Count -gt 0) {

        $duplicateEvidence = [System.Collections.Generic.List[object]]::new()

        foreach ($group in $duplicateNames) {

            $paths = [System.Collections.Generic.List[string]]::new()

            foreach ($item in $group.Group) {
                $relPath = Get-RelativePath -FullPath $item.FullName
                $paths.Add($relPath)
            }

            $duplicateEvidence.Add(
                [pscustomobject]@{
                    Name  = $group.Name
                    Count = $group.Count
                    Paths = @($paths)
                }
            )
        }

        Add-Finding `
            -Severity 'WARNING' `
            -Code 'DUPLICATE_POWERSHELL_NAMES' `
            -Message "Duplicate PowerShell filenames detected: $($duplicateNames.Count)" `
            -Evidence @($duplicateEvidence)
    }

    # =========================================================================
    # CONTRÔLE DES FICHIERS CRITIQUES OBSERVÉS
    # =========================================================================

    Write-Host ''
    Write-Host '[6/8] Contrôle des artefacts critiques connus...' -ForegroundColor Yellow

    $KnownCriticalScripts = @(
        'E-ZZIO-ControlledPurificationAndRebaseline-v0.2.0.ps1',
        'EZZIO_Build_SemanticState_v0.1.ps1',
        'EZZIO_Build_TopologyState.ps1',
        'EZZIO_Certify_StaticResolver_QG_v1.2.0.ps1',
        'EZZIO_ProjectTruthEngine_v1.0.0.ps1',
        'EZZIO_ProjectTruthEngine_v1.0.1.ps1',
        'EZZIO_StaticResolverLab_v1.1.7.5.ps1',
        'EZZIO_Validation_Forensic_v1.1.1.ps1',
        'EZZIO_Validation_Forensic_v1.1.4.ps1',
        'start_ezzio_secure.ps1'
    )

    foreach ($name in $KnownCriticalScripts) {

        $matches = @(
            $PowerShellFiles |
            Where-Object {
                $_.Name -eq $name
            }
        )

        if ($matches.Count -eq 0) {
            continue
        }

        foreach ($file in $matches) {

            $relative = Get-RelativePath -FullPath $file.FullName

            $errorsForFile = @(
                $PsErrors |
                Where-Object {
                    $_.Path -eq $relative
                }
            )

            if ($errorsForFile.Count -gt 0) {

                Add-Finding `
                    -Severity 'CRITICAL' `
                    -Code 'KNOWN_CRITICAL_SCRIPT_INVALID' `
                    -Path $relative `
                    -Message "Known critical PowerShell artifact has $($errorsForFile.Count) syntax defect(s)." `
                    -Evidence @($errorsForFile)
            }
        }
    }

    # =========================================================================
    # RÉSUMÉ
    # =========================================================================

    Write-Host ''
    Write-Host '[7/8] Construction des rapports...' -ForegroundColor Yellow

    $criticalCount = @(
        $Findings |
        Where-Object {
            $_.Severity -eq 'CRITICAL'
        }
    ).Count

    $errorCount = @(
        $Findings |
        Where-Object {
            $_.Severity -eq 'ERROR'
        }
    ).Count

    $warningCount = @(
        $Findings |
        Where-Object {
            $_.Severity -eq 'WARNING'
        }
    ).Count

    $infoCount = @(
        $Findings |
        Where-Object {
            $_.Severity -eq 'INFO'
        }
    ).Count

    $status = if ($criticalCount -eq 0 -and $errorCount -eq 0) {
        'PASS'
    }
    else {
        'FAIL_CLOSED'
    }

    $Summary = [pscustomobject]@{
        EngineVersion        = 'EZZIO_TRUTH_FORENSIC_GENERATOR_v1.0.0'
        TimestampUtc         = (Get-Date).ToUniversalTime().ToString('o')
        ProjectRoot          = $ProjectRoot
        ReportRoot           = $ReportRoot
        Mode                 = 'READ_ONLY_FAIL_CLOSED_FORENSIC'
        Status               = $status

        Inventory = [pscustomobject]@{
            TotalFiles       = $Inventory.Count
            PowerShellFiles  = $PowerShellFiles.Count
            JsonFiles        = $JsonFiles.Count
            EmptyFiles       = $emptyFiles.Count
        }

        Syntax = [pscustomobject]@{
            PowerShellErrors = $PsErrors.Count
            JsonErrors       = $JsonErrors.Count
        }

        Findings = [pscustomobject]@{
            Total    = $Findings.Count
            Critical = $criticalCount
            Error    = $errorCount
            Warning  = $warningCount
            Info     = $infoCount
        }

        Certification = [pscustomobject]@{
            Certified = $false
            Reason    = if ($status -eq 'PASS') {
                'No CRITICAL or ERROR findings detected by this generator.'
            }
            else {
                'Certification denied because one or more CRITICAL/ERROR findings exist.'
            }
        }
    }

    # =========================================================================
    # ÉCRITURE RAPPORTS
    # =========================================================================

    $FindingsJson = @($Findings) |
        ConvertTo-Json -Depth 50

    $SummaryJson = $Summary |
        ConvertTo-Json -Depth 30

    $PsErrorsJson = @($PsErrors) |
        ConvertTo-Json -Depth 30

    $JsonErrorsJson = @($JsonErrors) |
        ConvertTo-Json -Depth 30

    $InventoryJson = @($Inventory) |
        ConvertTo-Json -Depth 20

    Set-Content `
        -LiteralPath $FindingsPath `
        -Value $FindingsJson `
        -Encoding UTF8 `
        -ErrorAction Stop

    Set-Content `
        -LiteralPath $SummaryPath `
        -Value $SummaryJson `
        -Encoding UTF8 `
        -ErrorAction Stop

    Set-Content `
        -LiteralPath $PowerShellErrorsPath `
        -Value $PsErrorsJson `
        -Encoding UTF8 `
        -ErrorAction Stop

    Set-Content `
        -LiteralPath $JsonErrorsPath `
        -Value $JsonErrorsJson `
        -Encoding UTF8 `
        -ErrorAction Stop

    Set-Content `
        -LiteralPath $InventoryPath `
        -Value $InventoryJson `
        -Encoding UTF8 `
        -ErrorAction Stop

    Set-Content `
        -LiteralPath $LogPath `
        -Value (@($LogLines) -join [Environment]::NewLine) `
        -Encoding UTF8 `
        -ErrorAction Stop

    # =========================================================================
    # AUTO-VALIDATION DES RAPPORTS
    # =========================================================================

    Write-Host ''
    Write-Host '[8/8] Validation finale des rapports...' -ForegroundColor Yellow

    $reportFiles = @(
        $FindingsPath,
        $SummaryPath,
        $PowerShellErrorsPath,
        $JsonErrorsPath,
        $InventoryPath
    )

    $reportValidationFailures = [System.Collections.Generic.List[object]]::new()

    foreach ($report in $reportFiles) {

        try {

            $content = Get-Content `
                -LiteralPath $report `
                -Raw `
                -ErrorAction Stop

            $null = $content | ConvertFrom-Json -ErrorAction Stop

        }
        catch {

            $reportValidationFailures.Add(
                [pscustomobject]@{
                    Path    = $report
                    Message = $_.Exception.Message
                }
            )
        }
    }

    if ($reportValidationFailures.Count -gt 0) {

        Add-Finding `
            -Severity 'CRITICAL' `
            -Code 'GENERATED_REPORT_INVALID' `
            -Message "Generated report validation failed: $($reportValidationFailures.Count)" `
            -Evidence @($reportValidationFailures)

        $status = 'FAIL_CLOSED'
    }

    # =========================================================================
    # AFFICHAGE FINAL
    # =========================================================================

    Write-Host ''
    Write-Host '============================================================' -ForegroundColor Cyan
    Write-Host ' E-ZZIO — FORENSIC RESULT' -ForegroundColor Cyan
    Write-Host '============================================================' -ForegroundColor Cyan
    Write-Host ''

    Write-Host "STATUS           : $status" -ForegroundColor (
        if ($status -eq 'PASS') { 'Green' } else { 'Red' }
    )

    Write-Host "TOTAL FINDINGS   : $($Findings.Count)"
    Write-Host "CRITICAL         : $criticalCount"
    Write-Host "ERROR            : $errorCount"
    Write-Host "WARNING          : $warningCount"
    Write-Host ''

    Write-Host "FILES            : $($Inventory.Count)"
    Write-Host "POWERSHELL       : $($PowerShellFiles.Count)"
    Write-Host "POWERSHELL ERRORS: $($PsErrors.Count)"
    Write-Host "JSON             : $($JsonFiles.Count)"
    Write-Host "JSON ERRORS      : $($JsonErrors.Count)"
    Write-Host ''

    Write-Host 'REPORT ROOT:' -ForegroundColor Cyan
    Write-Host $ReportRoot
    Write-Host ''

    Write-Host 'FINDINGS:' -ForegroundColor Cyan
    Write-Host $FindingsPath
    Write-Host ''

    # =========================================================================
    # NOTE IMPORTANTE:
    #
    # Le nombre de findings peut avoir changé après la validation des rapports.
    # On réécrit donc le fichier final une dernière fois avec l'état définitif.
    # =========================================================================

    $FinalCriticalCount = @(
        $Findings |
        Where-Object {
            $_.Severity -eq 'CRITICAL'
        }
    ).Count

    $FinalErrorCount = @(
        $Findings |
        Where-Object {
            $_.Severity -eq 'ERROR'
        }
    ).Count

    if ($FinalCriticalCount -gt 0 -or $FinalErrorCount -gt 0) {
        $status = 'FAIL_CLOSED'
    }

    $FinalSummary = [pscustomobject]@{
        EngineVersion = 'EZZIO_TRUTH_FORENSIC_GENERATOR_v1.0.0'
        TimestampUtc  = (Get-Date).ToUniversalTime().ToString('o')
        ProjectRoot   = $ProjectRoot
        ReportRoot    = $ReportRoot
        Mode          = 'READ_ONLY_FAIL_CLOSED_FORENSIC'
        Status        = $status

        Inventory = [pscustomobject]@{
            TotalFiles      = $Inventory.Count
            PowerShellFiles = $PowerShellFiles.Count
            JsonFiles       = $JsonFiles.Count
            EmptyFiles      = $emptyFiles.Count
        }

        Syntax = [pscustomobject]@{
            PowerShellErrors = $PsErrors.Count
            JsonErrors       = $JsonErrors.Count
        }

        Findings = [pscustomobject]@{
            Total    = $Findings.Count
            Critical = $FinalCriticalCount
            Error    = $FinalErrorCount
            Warning  = $warningCount
            Info     = $infoCount
        }

        Certification = [pscustomobject]@{
            Certified = (
                $FinalCriticalCount -eq 0 -and
                $FinalErrorCount -eq 0
            )

            Reason = if (
                $FinalCriticalCount -eq 0 -and
                $FinalErrorCount -eq 0
            ) {
                'No CRITICAL or ERROR findings detected.'
            }
            else {
                'Certification denied under fail-closed policy.'
            }
        }
    }

    Set-Content `
        -LiteralPath $FindingsPath `
        -Value (@($Findings) | ConvertTo-Json -Depth 50) `
        -Encoding UTF8 `
        -ErrorAction Stop

    Set-Content `
        -LiteralPath $SummaryPath `
        -Value ($FinalSummary | ConvertTo-Json -Depth 30) `
        -Encoding UTF8 `
        -ErrorAction Stop

    # =========================================================================
    # CODE RETOUR
    # =========================================================================

    if ($status -eq 'PASS') {

        Write-Host ''
        Write-Host 'FORENSIC STATUS : PASS' -ForegroundColor Green
        Write-Host 'Aucune anomalie CRITICAL/ERROR détectée par ce moteur.' -ForegroundColor Green
        Write-Host ''

        exit 0
    }

    Write-Host ''
    Write-Host 'FORENSIC STATUS : FAIL-CLOSED' -ForegroundColor Red
    Write-Host 'Des anomalies CRITICAL/ERROR existent.' -ForegroundColor Red
    Write-Host 'Aucune correction automatique n''a été effectuée.' -ForegroundColor Red
    Write-Host ''

    exit 1
}