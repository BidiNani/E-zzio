# ============================================================================
# E-ZZIO — TRUTH ROOT-CAUSE REPAIR DOSSIER v1.0.1
# ============================================================================
# MODE       : READ-ONLY / FAIL-CLOSED / NO EXECUTION / NO SOURCE MUTATION
# QUALITY    : FORENSIC / DETERMINISTIC / CERTIFICATION-GRADE
#
# PURPOSE:
#   Construire un dossier technique complet et vérifiable permettant de
#   préparer une réparation contrôlée des causes racines détectées par
#   E-ZZIO Truth Root-Cause Analysis.
#
# HARD GUARANTEES:
#   - Aucun fichier source E-ZZIO modifié.
#   - Aucun fichier source E-ZZIO supprimé.
#   - Aucun déplacement / renommage.
#   - Aucun script source exécuté.
#   - Aucun auto-repair.
#   - Aucun faux CERTIFIED.
#   - SHA-256 avant analyse.
#   - SHA-256 après analyse.
#   - Toute mutation détectée => FAIL-CLOSED.
#   - Parser PowerShell direct via Parser.ParseFile().
#   - Les fichiers vides sont valides en tant que sources lisibles.
#   - Aucun contexte source ne peut provoquer une fausse réussite.
#   - Tous les artefacts JSON sont revalidés.
#   - Tous les artefacts sont vérifiés comme existants et non vides.
#   - Le dossier n'est déclaré COMPLETE que si toutes les gates passent.
#
# IMPORTANT:
#   Ce script NE REPARE RIEN.
#   Il prépare uniquement les éléments nécessaires à une réparation humaine
#   ou à une future phase de réparation explicitement contrôlée.
# ============================================================================

[CmdletBinding()]
param(
    [string]$ProjectRoot = 'G:\AI\E-zzio',

    [string]$SourceRunId = '20260820_194852_240_e38d74c08585',

    [string]$FindingsPath = 'G:\AI\E-zzio\_EZZIO_TRUTH_REPORTS\20260820_193008_236_132bbbbb5486\FINDINGS\EZZIO_TRUTH_FORENSIC_FINDINGS.json',

    [int]$ContextRadius = 12,

    [switch]$NoPause
)

# ============================================================================
# GLOBAL SAFETY
# ============================================================================

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$script:FatalReason = ''
$script:Completed = $false
$script:SourceMutationDetected = $false
$script:OutputIntegrityFailure = $false
$script:ContextExtractionFailure = $false

# ============================================================================
# HELPERS
# ============================================================================

function Write-Section {
    param(
        [Parameter(Mandatory)]
        [string]$Title,

        [ConsoleColor]$Color = [ConsoleColor]::Cyan
    )

    Write-Host ''
    Write-Host '============================================================================' -ForegroundColor $Color
    Write-Host " $Title" -ForegroundColor $Color
    Write-Host '============================================================================' -ForegroundColor $Color
}

function Get-SafeString {
    param(
        [AllowNull()]
        [object]$Value
    )

    if ($null -eq $Value) {
        return ''
    }

    return [string]$Value
}

function Get-Sha256File {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "SHA256_SOURCE_NOT_FOUND: $Path"
    }

    $hash = Get-FileHash `
        -LiteralPath $Path `
        -Algorithm SHA256 `
        -ErrorAction Stop

    return $hash.Hash.ToLowerInvariant()
}

function Assert-Directory {
    param(
        [Parameter(Mandatory)]
        [string]$Path,

        [Parameter(Mandatory)]
        [string]$Name
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Container)) {
        throw "${Name}_NOT_FOUND: $Path"
    }
}

function Assert-File {
    param(
        [Parameter(Mandatory)]
        [string]$Path,

        [Parameter(Mandatory)]
        [string]$Name
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "${Name}_NOT_FOUND: $Path"
    }
}

function Assert-NonEmptyFile {
    param(
        [Parameter(Mandatory)]
        [string]$Path,

        [Parameter(Mandatory)]
        [string]$Name
    )

    Assert-File -Path $Path -Name $Name

    $item = Get-Item -LiteralPath $Path -ErrorAction Stop

    if ([int64]$item.Length -le 0) {
        throw "${Name}_EMPTY: $Path"
    }
}

function Get-SourceLines {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    Assert-File -Path $Path -Name 'SOURCE'

    # IMPORTANT:
    # @() force systématiquement un tableau, même lorsque le fichier est vide.
    $lines = @(
        Get-Content `
            -LiteralPath $Path `
            -ErrorAction Stop
    )

    return ,$lines
}

function Get-Context {
    param(
        [AllowEmptyCollection()]
        [AllowNull()]
        [object[]]$Lines,

        [Parameter(Mandatory)]
        [int]$LineNumber,

        [int]$Radius = 12
    )

    # ------------------------------------------------------------------------
    # EMPTY FILE / EMPTY ARRAY SAFE PATH
    # ------------------------------------------------------------------------

    if ($null -eq $Lines) {
        return @()
    }

    $count = @($Lines).Count

    if ($count -eq 0) {
        return @()
    }

    if ($Radius -lt 0) {
        throw "INVALID_CONTEXT_RADIUS: $Radius"
    }

    $safeLine = $LineNumber

    if ($safeLine -lt 1) {
        $safeLine = 1
    }

    if ($safeLine -gt $count) {
        $safeLine = $count
    }

    $start = [Math]::Max(
        1,
        $safeLine - $Radius
    )

    $end = [Math]::Min(
        $count,
        $safeLine + $Radius
    )

    $result = [System.Collections.Generic.List[object]]::new()

    for ($i = $start; $i -le $end; $i++) {

        $text = ''

        if ($null -ne $Lines[$i - 1]) {
            $text = [string]$Lines[$i - 1]
        }

        $result.Add(
            [pscustomobject]@{
                LineNumber = $i
                Text       = $text
                IsTarget   = ($i -eq $safeLine)
            }
        )
    }

    return @($result)
}

function Get-ParserErrors {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    Assert-File -Path $Path -Name 'PARSER_SOURCE'

    $tokens = $null
    $errors = $null

    try {

        $null = [System.Management.Automation.Language.Parser]::ParseFile(
            $Path,
            [ref]$tokens,
            [ref]$errors
        )

    }
    catch {

        return @(
            [pscustomobject]@{
                File    = $Path
                ErrorId = 'PARSER_INVOCATION_FAILURE'
                Message = $_.Exception.Message
                Line    = 0
                Column  = 0
                Text    = ''
                Extent  = ''
            }
        )
    }

    $result = [System.Collections.Generic.List[object]]::new()

    foreach ($errorRecord in @($errors)) {

        if ($null -eq $errorRecord) {
            continue
        }

        $line   = 0
        $column = 0
        $text   = ''
        $extent = ''

        if ($null -ne $errorRecord.Extent) {

            $line = [int]$errorRecord.Extent.StartLineNumber

            $column = [int]$errorRecord.Extent.StartColumnNumber

            $text = Get-SafeString `
                $errorRecord.Extent.Text

            $extent = Get-SafeString `
                $errorRecord.Extent.ToString()
        }

        $result.Add(
            [pscustomobject]@{
                File    = $Path
                ErrorId = Get-SafeString $errorRecord.ErrorId
                Message = Get-SafeString $errorRecord.Message
                Line    = $line
                Column  = $column
                Text    = $text
                Extent  = $extent
            }
        )
    }

    return @($result)
}

function Resolve-ProjectPath {
    param(
        [Parameter(Mandatory)]
        [string]$ProjectRoot,

        [Parameter(Mandatory)]
        [string]$Path
    )

    if ([string]::IsNullOrWhiteSpace($Path)) {
        return ''
    }

    if ([System.IO.Path]::IsPathRooted($Path)) {
        return $Path
    }

    return Join-Path `
        $ProjectRoot `
        $Path
}

function Get-RelativeProjectPath {
    param(
        [Parameter(Mandatory)]
        [string]$ProjectRoot,

        [Parameter(Mandatory)]
        [string]$FullPath
    )

    $root = [System.IO.Path]::GetFullPath($ProjectRoot).TrimEnd('\')

    $full = [System.IO.Path]::GetFullPath($FullPath)

    if ($full.StartsWith(
        $root + '\',
        [System.StringComparison]::OrdinalIgnoreCase
    )) {
        return $full.Substring($root.Length + 1)
    }

    if ($full.Equals(
        $root,
        [System.StringComparison]::OrdinalIgnoreCase
    )) {
        return ''
    }

    return $full
}

function Test-JsonFile {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    Assert-NonEmptyFile `
        -Path $Path `
        -Name 'JSON_OUTPUT'

    $raw = Get-Content `
        -LiteralPath $Path `
        -Raw `
        -ErrorAction Stop

    if ([string]::IsNullOrWhiteSpace($raw)) {
        throw "JSON_EMPTY_TEXT: $Path"
    }

    try {

        $null = $raw |
            ConvertFrom-Json `
                -Depth 100 `
                -ErrorAction Stop
    }
    catch {

        throw "JSON_INVALID: $Path :: $($_.Exception.Message)"
    }

    return $true
}

function Write-JsonDeterministic {
    param(
        [Parameter(Mandatory)]
        [object]$InputObject,

        [Parameter(Mandatory)]
        [string]$Path
    )

    $json = $InputObject |
        ConvertTo-Json `
            -Depth 100 `
            -Compress:$false `
            -ErrorAction Stop

    if ([string]::IsNullOrWhiteSpace($json)) {
        throw "JSON_SERIALIZATION_EMPTY: $Path"
    }

    $json |
        Set-Content `
            -LiteralPath $Path `
            -Encoding UTF8 `
            -ErrorAction Stop

    Test-JsonFile -Path $Path | Out-Null
}

function Assert-NoSourceMutation {
    param(
        [Parameter(Mandatory)]
        [object[]]$BeforeRecords
    )

    foreach ($before in @($BeforeRecords)) {

        if (-not $before.Exists) {
            continue
        }

        if (-not (Test-Path -LiteralPath $before.FullPath -PathType Leaf)) {
            $script:SourceMutationDetected = $true

            throw "SOURCE_MUTATION_OR_DELETION_DETECTED: $($before.FullPath)"
        }

        $afterItem = Get-Item `
            -LiteralPath $before.FullPath `
            -ErrorAction Stop

        $afterHash = Get-Sha256File `
            -Path $before.FullPath

        if ($afterHash -ne $before.Sha256) {

            $script:SourceMutationDetected = $true

            throw (
                "SOURCE_MUTATION_DETECTED: {0} | BEFORE={1} | AFTER={2}" -f `
                    $before.FullPath,
                    $before.Sha256,
                    $afterHash
            )
        }

        if ([int64]$afterItem.Length -ne [int64]$before.Length) {

            $script:SourceMutationDetected = $true

            throw (
                "SOURCE_LENGTH_MUTATION_DETECTED: {0}" -f `
                    $before.FullPath
            )
        }
    }
}

# ============================================================================
# MAIN
# ============================================================================

try {

    Write-Section `
        -Title 'E-ZZIO - TRUTH ROOT-CAUSE REPAIR DOSSIER v1.0.1 SUPER' `
        -Color Cyan

    Write-Host ''
    Write-Host "PROJECT : $ProjectRoot"
    Write-Host "SOURCE  : $SourceRunId"
    Write-Host 'MODE    : READ-ONLY / FAIL-CLOSED / NO EXECUTION / NO MUTATION'
    Write-Host 'QUALITY : FORENSIC / DETERMINISTIC / CERTIFICATION-GRADE'
    Write-Host ''

    # ========================================================================
    # [0] BASE VALIDATION
    # ========================================================================

    Write-Host '[0/9] Validation environnement...' `
        -ForegroundColor Yellow

    Assert-Directory `
        -Path $ProjectRoot `
        -Name 'PROJECT_ROOT'

    Assert-File `
        -Path $FindingsPath `
        -Name 'FINDINGS'

    $SourceTriageRoot = Join-Path `
        $ProjectRoot `
        "_EZZIO_TRUTH_REPORTS\$SourceRunId\CRITICAL_ROOT_CAUSE_ANALYSIS"

    Assert-Directory `
        -Path $SourceTriageRoot `
        -Name 'SOURCE_TRIAGE_ROOT'

    $analysisPath = Join-Path `
        $SourceTriageRoot `
        'EZZIO_ROOT_CAUSE_ANALYSIS.json'

    Assert-File `
        -Path $analysisPath `
        -Name 'ROOT_CAUSE_ANALYSIS'

    Write-Host '      ENVIRONMENT : PASS' `
        -ForegroundColor Green

    # ========================================================================
    # [1] LOAD ROOT CAUSE ANALYSIS
    # ========================================================================

    Write-Host ''
    Write-Host '[1/9] Chargement du Root-Cause Analysis...' `
        -ForegroundColor Yellow

    $analysisText = Get-Content `
        -LiteralPath $analysisPath `
        -Raw `
        -ErrorAction Stop

    if ([string]::IsNullOrWhiteSpace($analysisText)) {
        throw "ROOT_CAUSE_ANALYSIS_EMPTY: $analysisPath"
    }

    try {

        $analysis = $analysisText |
            ConvertFrom-Json `
                -Depth 100 `
                -ErrorAction Stop
    }
    catch {

        throw (
            "ROOT_CAUSE_ANALYSIS_INVALID: {0}" -f `
                $_.Exception.Message
        )
    }

    if ($analysis.Verdict -ne 'FAIL') {
        throw (
            "SOURCE_ANALYSIS_NOT_FAIL_CLOSED: {0}" -f `
                $analysis.Verdict
        )
    }

    Write-Host "      VERDICT  : $($analysis.Verdict)"
    Write-Host "      ROOTS    : $($analysis.RootCauses)"
    Write-Host "      CASCADES : $($analysis.CascadeCandidates)"
    Write-Host '      ANALYSIS : PASS' `
        -ForegroundColor Green

    # ========================================================================
    # [2] EXTRACT ROOT CAUSES
    # ========================================================================

    Write-Host ''
    Write-Host '[2/9] Extraction des causes racines...' `
        -ForegroundColor Yellow

    $rootCauses = @(
        $analysis.RootCauseDetails
    )

    if ($rootCauses.Count -eq 0) {
        throw 'NO_ROOT_CAUSES_FOUND'
    }

    $targetPaths = @(
        $rootCauses |
            Where-Object {
                -not [string]::IsNullOrWhiteSpace(
                    (Get-SafeString $_.Path)
                )
            } |
            ForEach-Object {
                Get-SafeString $_.Path
            } |
            Sort-Object `
                -Unique
    )

    if ($targetPaths.Count -eq 0) {
        throw 'NO_TARGET_PATHS_FOUND'
    }

    Write-Host "      ROOT CAUSES : $($rootCauses.Count)"
    Write-Host "      FILES       : $($targetPaths.Count)"
    Write-Host '      EXTRACTION  : PASS' `
        -ForegroundColor Green

    # ========================================================================
    # [3] CREATE OUTPUT
    # ========================================================================

    Write-Host ''
    Write-Host '[3/9] Création du dossier forensic...' `
        -ForegroundColor Yellow

    $timestamp = [DateTime]::Now.ToString(
        'yyyyMMdd_HHmmss_fff'
    )

    $runSeed = @(
        $timestamp
        $SourceRunId
        $FindingsPath
        $analysisPath
    ) -join '|'

    $sha = [System.Security.Cryptography.SHA256]::Create()

    try {

        $seedBytes = [System.Text.Encoding]::UTF8.GetBytes(
            $runSeed
        )

        $seedHash = $sha.ComputeHash(
            $seedBytes
        )
    }
    finally {
        $sha.Dispose()
    }

    $seedHex = (
        [System.BitConverter]::ToString(
            $seedHash
        ) -replace '-', ''
    ).ToLowerInvariant()

    $RunId = '{0}_{1}' -f `
        $timestamp,
        $seedHex.Substring(0,12)

    $OutputRoot = Join-Path `
        $ProjectRoot `
        "_EZZIO_TRUTH_REPORTS\$RunId\REPAIR_DOSSIER"

    New-Item `
        -ItemType Directory `
        -Path $OutputRoot `
        -Force `
        -ErrorAction Stop |
        Out-Null

    $SourceContextRoot = Join-Path `
        $OutputRoot `
        'SOURCE_CONTEXT'

    New-Item `
        -ItemType Directory `
        -Path $SourceContextRoot `
        -Force `
        -ErrorAction Stop |
        Out-Null

    $SourceHashesPath = Join-Path `
        $OutputRoot `
        'SOURCE_HASHES.json'

    $ParserPath = Join-Path `
        $OutputRoot `
        'POWERSHELL_PARSER_ERRORS.json'

    $RootCausePath = Join-Path `
        $OutputRoot `
        'ROOT_CAUSE_MATRIX.json'

    $ContextPath = Join-Path `
        $OutputRoot `
        'ROOT_CAUSE_SOURCE_CONTEXT.txt'

    $ReportPath = Join-Path `
        $OutputRoot `
        'REPAIR_DOSSIER_REPORT.txt'

    $ManifestPath = Join-Path `
        $OutputRoot `
        'REPAIR_DOSSIER_MANIFEST.json'

    Write-Host "      RUN ID : $RunId"
    Write-Host "      OUTPUT : $OutputRoot"
    Write-Host '      OUTPUT : PASS' `
        -ForegroundColor Green

    # ========================================================================
    # [4] HASH ALL TARGET FILES BEFORE ANALYSIS
    # ========================================================================

    Write-Host ''
    Write-Host '[4/9] Empreinte SHA-256 des sources AVANT analyse...' `
        -ForegroundColor Yellow

    $hashRecords = [System.Collections.Generic.List[object]]::new()

    foreach ($relativePath in $targetPaths) {

        $fullPath = Resolve-ProjectPath `
            -ProjectRoot $ProjectRoot `
            -Path $relativePath

        if ([string]::IsNullOrWhiteSpace($fullPath)) {
            throw 'TARGET_PATH_EMPTY_AFTER_RESOLUTION'
        }

        if (-not (Test-Path -LiteralPath $fullPath -PathType Leaf)) {

            $hashRecords.Add(
                [pscustomobject]@{
                    Path       = $relativePath
                    FullPath   = $fullPath
                    Exists     = $false
                    Length     = [int64]0
                    Sha256     = ''
                    LastWrite  = ''
                }
            )

            continue
        }

        $item = Get-Item `
            -LiteralPath $fullPath `
            -ErrorAction Stop

        $hashRecords.Add(
            [pscustomobject]@{
                Path       = $relativePath
                FullPath   = $fullPath
                Exists     = $true
                Length     = [int64]$item.Length
                Sha256     = Get-Sha256File -Path $fullPath
                LastWrite  = $item.LastWriteTimeUtc.ToString('o')
            }
        )
    }

    Write-JsonDeterministic `
        -InputObject @($hashRecords) `
        -Path $SourceHashesPath

    Write-Host "      HASHED : $($hashRecords.Count)" `
        -ForegroundColor Green

    # ========================================================================
    # [5] DIRECT POWERSHELL PARSER
    # ========================================================================

    Write-Host ''
    Write-Host '[5/9] Revalidation directe avec Parser.ParseFile()...' `
        -ForegroundColor Yellow

    $parserRecords = [System.Collections.Generic.List[object]]::new()

    foreach ($record in @($hashRecords)) {

        if (-not $record.Exists) {
            continue
        }

        $extension = [System.IO.Path]::GetExtension(
            $record.FullPath
        ).ToLowerInvariant()

        if ($extension -notin @(
            '.ps1',
            '.psm1',
            '.psd1'
        )) {
            continue
        }

        $errors = Get-ParserErrors `
            -Path $record.FullPath

        foreach ($errorRecord in @($errors)) {

            $parserRecords.Add(
                [pscustomobject]@{
                    Path     = $record.Path
                    ErrorId  = $errorRecord.ErrorId
                    Message  = $errorRecord.Message
                    Line     = [int]$errorRecord.Line
                    Column   = [int]$errorRecord.Column
                    Text     = $errorRecord.Text
                    Extent   = $errorRecord.Extent
                    Sha256   = $record.Sha256
                }
            )
        }
    }

    Write-JsonDeterministic `
        -InputObject @($parserRecords) `
        -Path $ParserPath

    Write-Host "      PARSER ERRORS : $($parserRecords.Count)" `
        -ForegroundColor Green

    # ========================================================================
    # [6] ROOT CAUSE MATRIX
    # ========================================================================

    Write-Host ''
    Write-Host '[6/9] Construction de la matrice de réparation...' `
        -ForegroundColor Yellow

    $matrix = [System.Collections.Generic.List[object]]::new()

    foreach ($root in @($rootCauses)) {

        $path = Get-SafeString $root.Path

        if ([string]::IsNullOrWhiteSpace($path)) {
            throw "ROOT_CAUSE_EMPTY_PATH: INDEX=$($root.Index)"
        }

        $fullPath = Resolve-ProjectPath `
            -ProjectRoot $ProjectRoot `
            -Path $path

        $matchingParserErrors = @(
            $parserRecords |
                Where-Object {
                    $_.Path -eq $path
                }
        )

        $sourceExists = Test-Path `
            -LiteralPath $fullPath `
            -PathType Leaf

        $sha256 = ''

        if ($sourceExists) {
            $sha256 = Get-Sha256File `
                -Path $fullPath
        }

        $rootErrorId = Get-SafeString `
            $root.ErrorId

        $rootIndex = [int]$root.Index

        $parserMatch = @(
            $matchingParserErrors |
                Where-Object {
                    $_.ErrorId -eq $rootErrorId -and
                    [int]$_.Line -eq $rootIndex
                }
        )

        $classification =
            'ROOT_CAUSE_REQUIRES_SOURCE_INSPECTION'

        if ($parserMatch.Count -gt 0) {

            $classification =
                'CONFIRMED_BY_DIRECT_PARSER'
        }

        $matrix.Add(
            [pscustomobject]@{
                Path                = $path
                FullPath            = $fullPath
                SourceExists        = $sourceExists
                CurrentSha256       = $sha256
                RootCauseIndex      = $rootIndex
                ErrorId             = $rootErrorId
                Family              = Get-SafeString $root.Family
                Message             = Get-SafeString $root.Message
                Classification      = $classification
                DirectParserMatches = $parserMatch.Count
                RepairAllowed       = $false
                AutomaticRepair     = $false
                RequiresRescan      = $true
            }
        )
    }

    Write-JsonDeterministic `
        -InputObject @($matrix) `
        -Path $RootCausePath

    Write-Host "      MATRIX : $($matrix.Count)" `
        -ForegroundColor Green

    # ========================================================================
    # [7] SOURCE CONTEXT
    # ========================================================================

    Write-Host ''
    Write-Host '[7/9] Extraction robuste des contextes source...' `
        -ForegroundColor Yellow

    $contextLines = [System.Collections.Generic.List[string]]::new()

    $contextLines.Add(
        '============================================================================'
    )

    $contextLines.Add(
        ' E-ZZIO - ROOT-CAUSE SOURCE CONTEXT v1.0.1'
    )

    $contextLines.Add(
        '============================================================================'
    )

    $contextLines.Add('')

    $contextLines.Add(
        "RUN ID       : $RunId"
    )

    $contextLines.Add(
        "SOURCE RUN   : $SourceRunId"
    )

    $contextLines.Add(
        "PROJECT      : $ProjectRoot"
    )

    $contextLines.Add(
        'MODE         : READ-ONLY / NO EXECUTION / NO MUTATION'
    )

    $contextLines.Add(
        "CONTEXT      : +/- $ContextRadius lines"
    )

    $contextLines.Add('')

    foreach ($root in @($rootCauses)) {

        $path = Get-SafeString $root.Path

        $fullPath = Resolve-ProjectPath `
            -ProjectRoot $ProjectRoot `
            -Path $path

        $contextLines.Add(
            '----------------------------------------------------------------------------'
        )

        $contextLines.Add(
            "FILE : $path"
        )

        $contextLines.Add(
            "FULL : $fullPath"
        )

        $contextLines.Add(
            "ROOT : [$($root.Index)] $($root.ErrorId)"
        )

        $contextLines.Add(
            "FAMILY : $($root.Family)"
        )

        $contextLines.Add(
            "MESSAGE: $($root.Message)"
        )

        $contextLines.Add(
            '----------------------------------------------------------------------------'
        )

        if (-not (Test-Path `
            -LiteralPath $fullPath `
            -PathType Leaf)) {

            $contextLines.Add(
                'SOURCE FILE NOT FOUND'
            )

            $contextLines.Add('')

            continue
        }

        try {

            # IMPORTANT:
            # Le @() empêche un fichier vide de devenir une chaîne vide.
            $lines = @(
                Get-SourceLines `
                    -Path $fullPath
            )

            $targetLine = [int]$root.Index

            if ($targetLine -le 0) {
                $targetLine = 1
            }

            if ($lines.Count -eq 0) {

                $contextLines.Add(
                    'SOURCE FILE IS EMPTY — 0 LINES'
                )

                $contextLines.Add(
                    'NO SOURCE CONTEXT AVAILABLE'
                )

                $contextLines.Add('')

                continue
            }

            $context = @(
                Get-Context `
                    -Lines $lines `
                    -LineNumber $targetLine `
                    -Radius $ContextRadius
            )

            if ($context.Count -eq 0) {

                $contextLines.Add(
                    'CONTEXT EXTRACTION RETURNED ZERO LINES'
                )

                $contextLines.Add('')

                throw (
                    "CONTEXT_EMPTY_UNEXPECTED: $path"
                )
            }

            foreach ($line in @($context)) {

                $marker = ' '

                if ($line.IsTarget) {
                    $marker = '>'
                }

                $contextLines.Add(
                    (
                        '{0} {1,7}: {2}' -f `
                            $marker,
                            $line.LineNumber,
                            $line.Text
                    )
                )
            }

            $contextLines.Add('')

        }
        catch {

            $script:ContextExtractionFailure = $true

            $contextLines.Add(
                "CONTEXT EXTRACTION FAILURE: $($_.Exception.Message)"
            )

            $contextLines.Add('')

            throw
        }
    }

    if ($contextLines.Count -le 10) {
        throw 'CONTEXT_ARTIFACT_SUSPICIOUSLY_EMPTY'
    }

    $contextLines |
        Set-Content `
            -LiteralPath $ContextPath `
            -Encoding UTF8 `
            -ErrorAction Stop

    Write-Host "      CONTEXT LINES : $($contextLines.Count)" `
        -ForegroundColor Green

    # ========================================================================
    # [8] FINAL REPORT + MANIFEST
    # ========================================================================

    Write-Host ''
    Write-Host '[8/9] Génération du rapport et du manifeste...' `
        -ForegroundColor Yellow

    $report = [System.Collections.Generic.List[string]]::new()

    $report.Add(
        '============================================================================'
    )

    $report.Add(
        ' E-ZZIO - TRUTH ROOT-CAUSE REPAIR DOSSIER v1.0.1'
    )

    $report.Add(
        '============================================================================'
    )

    $report.Add('')

    $report.Add(
        "RUN ID             : $RunId"
    )

    $report.Add(
        "SOURCE RUN         : $SourceRunId"
    )

    $report.Add(
        "PROJECT            : $ProjectRoot"
    )

    $report.Add(
        "FINDINGS           : $FindingsPath"
    )

    $report.Add(
        "ROOT ANALYSIS      : $analysisPath"
    )

    $report.Add(
        'MODE               : READ-ONLY / FAIL-CLOSED / NO EXECUTION / NO MUTATION'
    )

    $report.Add(
        'QUALITY            : FORENSIC / DETERMINISTIC'
    )

    $report.Add('')

    $report.Add(
        '----------------------------------------------------------------------------'
    )

    $report.Add(
        ' SOURCE ANALYSIS'
    )

    $report.Add(
        '----------------------------------------------------------------------------'
    )

    $report.Add(
        "VERDICT            : $($analysis.Verdict)"
    )

    $report.Add(
        "CERTIFICATION      : $($analysis.Certification)"
    )

    $report.Add(
        "EXPANDED FINDINGS  : $($analysis.ExpandedFindings)"
    )

    $report.Add(
        "UNIQUE FINDINGS    : $($analysis.UniqueFindings)"
    )

    $report.Add(
        "CRITICAL           : $($analysis.Critical)"
    )

    $report.Add(
        "ERROR              : $($analysis.Error)"
    )

    $report.Add(
        "WARNING            : $($analysis.Warning)"
    )

    $report.Add(
        "FILES AFFECTED     : $($analysis.FilesAffected)"
    )

    $report.Add(
        "ROOT CAUSES        : $($analysis.RootCauses)"
    )

    $report.Add(
        "CASCADE CANDIDATES : $($analysis.CascadeCandidates)"
    )

    $report.Add('')

    $report.Add(
        '----------------------------------------------------------------------------'
    )

    $report.Add(
        ' DIRECT VALIDATION'
    )

    $report.Add(
        '----------------------------------------------------------------------------'
    )

    $report.Add(
        "TARGET FILES       : $($hashRecords.Count)"
    )

    $report.Add(
        "PARSER ERRORS      : $($parserRecords.Count)"
    )

    $report.Add(
        "ROOT MATRIX        : $($matrix.Count)"
    )

    $report.Add(
        "CONTEXT LINES      : $($contextLines.Count)"
    )

    $report.Add('')

    $report.Add(
        '----------------------------------------------------------------------------'
    )

    $report.Add(
        ' SAFETY GATES'
    )

    $report.Add(
        '----------------------------------------------------------------------------'
    )

    $report.Add(
        'SOURCE MUTATION    : 0'
    )

    $report.Add(
        'AUTO REPAIR        : DISABLED'
    )

    $report.Add(
        'EXECUTION          : DISABLED'
    )

    $report.Add(
        'DELETION           : DISABLED'
    )

    $report.Add(
        'MOVE/RENAME        : DISABLED'
    )

    $report.Add(
        'CERTIFIED          : NOT AUTHORIZED BY THIS DOSSIER'
    )

    $report.Add('')

    $report.Add(
        'Aucune réparation n''a été effectuée.'
    )

    $report.Add(
        'Toute réparation future exige un rescan Truth Forensic complet.'
    )

    $report.Add(
        'CERTIFIED exige ZERO CRITICAL, ZERO ERROR et ZERO WARNING.'
    )

    $report.Add('')

    $report.Add(
        '----------------------------------------------------------------------------'
    )

    $report.Add(
        ' OUTPUTS'
    )

    $report.Add(
        '----------------------------------------------------------------------------'
    )

    $report.Add(
        "SOURCE HASHES : $SourceHashesPath"
    )

    $report.Add(
        "PARSER ERRORS : $ParserPath"
    )

    $report.Add(
        "ROOT MATRIX   : $RootCausePath"
    )

    $report.Add(
        "SOURCE CTX    : $ContextPath"
    )

    $report.Add(
        "MANIFEST      : $ManifestPath"
    )

    $report.Add(
        "REPORT        : $ReportPath"
    )

    $report.Add('')

    $report.Add(
        '============================================================================'
    )

    $report |
        Set-Content `
            -LiteralPath $ReportPath `
            -Encoding UTF8 `
            -ErrorAction Stop

    # ------------------------------------------------------------------------
    # MANIFEST
    # ------------------------------------------------------------------------

    $manifest = [pscustomobject]@{
        SchemaVersion        = '1.0.1'
        RunId                = $RunId
        SourceRunId          = $SourceRunId
        ProjectRoot          = $ProjectRoot
        FindingsPath         = $FindingsPath
        RootCauseAnalysis    = $analysisPath
        Mode                 = 'READ_ONLY_FAIL_CLOSED'
        SourceMutation       = $false
        AutomaticRepair      = $false
        Execution            = $false
        Deletion             = $false
        MoveRename           = $false
        RootCauses           = $rootCauses.Count
        TargetFiles          = $hashRecords.Count
        ParserErrors         = $parserRecords.Count
        MatrixRecords        = $matrix.Count
        ContextLines         = $contextLines.Count
        ContextRadius        = $ContextRadius
        Certification        = $false
        DossierComplete      = $false
    }

    Write-JsonDeterministic `
        -InputObject $manifest `
        -Path $ManifestPath

    # ========================================================================
    # [9] OUTPUT INTEGRITY + SOURCE IMMUTABILITY
    # ========================================================================

    Write-Host ''
    Write-Host '[9/9] GATES FINALES : intégrité + immutabilité...' `
        -ForegroundColor Yellow

    $outputs = @(
        $SourceHashesPath
        $ParserPath
        $RootCausePath
        $ContextPath
        $ReportPath
        $ManifestPath
    )

    foreach ($output in $outputs) {

        Assert-NonEmptyFile `
            -Path $output `
            -Name 'OUTPUT'

        $length = (
            Get-Item `
                -LiteralPath $output `
                -ErrorAction Stop
        ).Length

        if ([int64]$length -le 0) {

            $script:OutputIntegrityFailure = $true

            throw "OUTPUT_EMPTY: $output"
        }
    }

    # JSON validation.
    Test-JsonFile `
        -Path $SourceHashesPath |
        Out-Null

    Test-JsonFile `
        -Path $ParserPath |
        Out-Null

    Test-JsonFile `
        -Path $RootCausePath |
        Out-Null

    Test-JsonFile `
        -Path $ManifestPath |
        Out-Null

    # ------------------------------------------------------------------------
    # SOURCE IMMUTABILITY GATE
    # ------------------------------------------------------------------------

    Assert-NoSourceMutation `
        -BeforeRecords @($hashRecords)

    # ------------------------------------------------------------------------
    # RE-HASH AND RECORD AFTER STATE
    # ------------------------------------------------------------------------

    $afterRecords = [System.Collections.Generic.List[object]]::new()

    foreach ($before in @($hashRecords)) {

        if (-not $before.Exists) {

            $afterRecords.Add(
                [pscustomobject]@{
                    Path       = $before.Path
                    FullPath   = $before.FullPath
                    Exists     = $false
                    Length     = [int64]0
                    Sha256     = ''
                    Unchanged  = $true
                }
            )

            continue
        }

        $afterItem = Get-Item `
            -LiteralPath $before.FullPath `
            -ErrorAction Stop

        $afterHash = Get-Sha256File `
            -Path $before.FullPath

        $unchanged =
            (
                $afterHash -eq $before.Sha256 -and
                [int64]$afterItem.Length -eq [int64]$before.Length
            )

        if (-not $unchanged) {

            $script:SourceMutationDetected = $true

            throw (
                "FINAL_SOURCE_IMMUTABILITY_FAILURE: {0}" -f `
                    $before.FullPath
            )
        }

        $afterRecords.Add(
            [pscustomobject]@{
                Path       = $before.Path
                FullPath   = $before.FullPath
                Exists     = $true
                Length     = [int64]$afterItem.Length
                Sha256     = $afterHash
                Unchanged  = $unchanged
            }
        )
    }

    $AfterHashesPath = Join-Path `
        $OutputRoot `
        'SOURCE_HASHES_AFTER.json'

    Write-JsonDeterministic `
        -InputObject @($afterRecords) `
        -Path $AfterHashesPath

    # ------------------------------------------------------------------------
    # UPDATE MANIFEST ONLY AFTER ALL GATES PASSED
    # ------------------------------------------------------------------------

    $manifestFinal = [pscustomobject]@{
        SchemaVersion        = '1.0.1'
        RunId                = $RunId
        SourceRunId          = $SourceRunId
        ProjectRoot          = $ProjectRoot
        FindingsPath         = $FindingsPath
        RootCauseAnalysis    = $analysisPath

        Mode                 = 'READ_ONLY_FAIL_CLOSED'

        SourceMutation       = $script:SourceMutationDetected
        AutomaticRepair      = $false
        Execution            = $false
        Deletion             = $false
        MoveRename           = $false

        RootCauses           = $rootCauses.Count
        TargetFiles          = $hashRecords.Count
        ParserErrors         = $parserRecords.Count
        MatrixRecords        = $matrix.Count
        ContextLines         = $contextLines.Count
        ContextRadius        = $ContextRadius

        Certification        = $false
        DossierComplete      = $true

        Gates                = [pscustomobject]@{
            Environment        = $true
            AnalysisValid      = $true
            RootCausesFound    = $true
            HashBefore         = $true
            ParserCompleted    = $true
            MatrixCompleted    = $true
            ContextCompleted   = $true
            OutputsValid       = $true
            JsonValid          = $true
            SourceImmutable    = $true
            AutoRepairDisabled = $true
            ExecutionDisabled  = $true
        }
    }

    Write-JsonDeterministic `
        -InputObject $manifestFinal `
        -Path $ManifestPath

    # Final manifest revalidation.
    Test-JsonFile `
        -Path $ManifestPath |
        Out-Null

    # ========================================================================
    # FINAL SUCCESS
    # ========================================================================

    $script:Completed = $true

    Write-Section `
        -Title 'E-ZZIO - REPAIR DOSSIER COMPLETE / ALL GATES PASSED' `
        -Color Green

    Write-Host ''
    Write-Host "RUN ID            : $RunId"
    Write-Host "ROOT CAUSES       : $($rootCauses.Count)"
    Write-Host "TARGET FILES      : $($hashRecords.Count)"
    Write-Host "PARSER ERRORS     : $($parserRecords.Count)"
    Write-Host "MATRIX RECORDS    : $($matrix.Count)"
    Write-Host "CONTEXT LINES     : $($contextLines.Count)"
    Write-Host ''
    Write-Host 'SOURCE MUTATION   : 0' `
        -ForegroundColor Green
    Write-Host 'AUTO REPAIR       : DISABLED' `
        -ForegroundColor Green
    Write-Host 'EXECUTION         : DISABLED' `
        -ForegroundColor Green
    Write-Host 'CERTIFIED         : NOT AUTHORIZED' `
        -ForegroundColor Yellow
    Write-Host ''
    Write-Host "DOSSIER           : $OutputRoot" `
        -ForegroundColor Cyan
    Write-Host "SOURCE HASHES     : $SourceHashesPath" `
        -ForegroundColor Cyan
    Write-Host "HASHES AFTER      : $AfterHashesPath" `
        -ForegroundColor Cyan
    Write-Host "PARSER ERRORS     : $ParserPath" `
        -ForegroundColor Cyan
    Write-Host "ROOT MATRIX       : $RootCausePath" `
        -ForegroundColor Cyan
    Write-Host "SOURCE CONTEXT    : $ContextPath" `
        -ForegroundColor Cyan
    Write-Host "MANIFEST          : $ManifestPath" `
        -ForegroundColor Cyan
    Write-Host "REPORT            : $ReportPath" `
        -ForegroundColor Cyan
    Write-Host ''
    Write-Host 'FAIL-CLOSED : aucune réparation effectuée.' `
        -ForegroundColor Yellow
    Write-Host '============================================================================' `
        -ForegroundColor Green
    Write-Host ''

}
catch {

    $script:FatalReason = $_.Exception.Message

    $script:Completed = $false

    Write-Section `
        -Title 'E-ZZIO - REPAIR DOSSIER FAILED / FAIL-CLOSED' `
        -Color Red

    Write-Host ''
    Write-Host "ERROR : $script:FatalReason" `
        -ForegroundColor Red
    Write-Host ''

    Write-Host 'SAFETY STATE :' `
        -ForegroundColor Yellow

    Write-Host '  - Aucun auto-repair.'
    Write-Host '  - Aucun script source exécuté.'
    Write-Host '  - Aucun fichier source volontairement modifié.'
    Write-Host '  - Aucun fichier source supprimé.'
    Write-Host '  - Aucun déplacement / renommage.'
    Write-Host '  - Aucun CERTIFIED autorisé.'
    Write-Host '  - Résultat du dossier : NON VALIDE / INCOMPLET.'
    Write-Host ''

    if ($script:SourceMutationDetected) {
        Write-Host '!!! SOURCE MUTATION DETECTED !!!' `
            -ForegroundColor Red
    }

    if ($script:ContextExtractionFailure) {
        Write-Host '!!! CONTEXT EXTRACTION FAILURE !!!' `
            -ForegroundColor Red
    }

    if ($script:OutputIntegrityFailure) {
        Write-Host '!!! OUTPUT INTEGRITY FAILURE !!!' `
            -ForegroundColor Red
    }

    Write-Host ''
    Write-Host 'IMPORTANT :' `
        -ForegroundColor Yellow

    Write-Host 'Le dossier doit être considéré comme FAIL-CLOSED.'
    Write-Host 'Ne pas utiliser ses résultats comme dossier de réparation certifié.'
    Write-Host ''
    Write-Host '============================================================================' `
        -ForegroundColor Red
}
finally {

    if (-not $NoPause) {

        Write-Host ''
        Write-Host 'La fenêtre reste ouverte.' `
            -ForegroundColor DarkGray

        Write-Host 'Appuie sur ENTREE pour terminer...' `
            -ForegroundColor Cyan

        [void](Read-Host)
    }
}