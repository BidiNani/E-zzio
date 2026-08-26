#requires -Version 7.4

<#
===============================================================================
 E-ZZIO — TRUTH SUPER FORENSIC REPAIR LAB v5.2.0
===============================================================================

MODE
    READ-ONLY
    CANDIDATE-ONLY
    FAIL-CLOSED

QUALITY
    FORENSIC
    DETERMINISTIC
    CERTIFICATION-GRADE

SECURITY CONTRACT
    - Aucune modification des sources originales.
    - Aucun code candidat exécuté.
    - Aucune promotion automatique.
    - Aucun CERTIFIED.
    - Toute stratégie doit démontrer une amélioration réelle du parser.
    - Toute régression rejette le candidat.
    - Les erreurs du moteur lui-même provoquent FAIL-CLOSED.

IMPORTANT
    Cette version corrige notamment :
      * Replace(char,char) utilisé avec une chaîne vide
      * variables PowerShell réservées / automatiques
      * objets TrialContent absents
      * chaînes vides passées à des paramètres obligatoires
      * génération de RunId fragile
      * évaluations candidates non déterministes

===============================================================================
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ============================================================================
# CONFIGURATION
# ============================================================================

$EngineName   = 'E-ZZIO — TRUTH SUPER FORENSIC REPAIR LAB'
$ScriptVersion = '5.2.0'

$ProjectRoot = 'G:\AI\E-zzio'

$ReportsRoot = Join-Path $ProjectRoot '_EZZIO_TRUTH_REPORTS'

$SourceMutation      = $false
$ExecutionPerformed  = $false
$PromotionPerformed  = $false
$Certified           = $false
$CertifiedAuthorized = $false

# ============================================================================
# HELPERS
# ============================================================================

function Write-Banner {
    param(
        [Parameter(Mandatory)]
        [string]$Title
    )

    Write-Host ''
    Write-Host '============================================================================' -ForegroundColor Cyan
    Write-Host " $Title" -ForegroundColor Cyan
    Write-Host '============================================================================' -ForegroundColor Cyan
}

function Write-Step {
    param(
        [Parameter(Mandatory)]
        [string]$Step,

        [Parameter(Mandatory)]
        [string]$Title
    )

    Write-Host ''
    Write-Host "[$Step] $Title" -ForegroundColor White
}

function Write-Field {
    param(
        [Parameter(Mandatory)]
        [string]$Name,

        [AllowEmptyString()]
        [string]$Value
    )

    Write-Host ("      {0,-28}: {1}" -f $Name,$Value)
}

function Assert-Directory {
    param(
        [Parameter(Mandatory)]
        [string]$Path,

        [Parameter(Mandatory)]
        [string]$Name
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Container)) {
        throw "$Name introuvable : $Path"
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
        throw "$Name introuvable : $Path"
    }
}

function New-RunId {
    $utc = [DateTime]::UtcNow

    $timestamp = $utc.ToString(
        'yyyyMMdd_HHmmss_fff',
        [Globalization.CultureInfo]::InvariantCulture
    )

    $guidPart = [Guid]::NewGuid().ToString('N').Substring(0,12)

    return "${timestamp}_${guidPart}"
}

function Get-FileSha256 {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash
}

function Read-Utf8File {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    return [System.IO.File]::ReadAllText(
        $Path,
        [System.Text.UTF8Encoding]::new($false)
    )
}

function Write-Utf8NoBom {
    param(
        [Parameter(Mandatory)]
        [string]$Path,

        [Parameter(Mandatory)]
        [AllowEmptyString()]
        [string]$Content
    )

    $parent = Split-Path -Parent $Path

    if (-not [string]::IsNullOrWhiteSpace($parent)) {
        [System.IO.Directory]::CreateDirectory($parent) | Out-Null
    }

    $encoding = [System.Text.UTF8Encoding]::new($false)

    [System.IO.File]::WriteAllText(
        $Path,
        $Content,
        $encoding
    )
}

function ConvertTo-SafeLines {
    param(
        [AllowNull()]
        [AllowEmptyString()]
        [string]$Content
    )

    if ($null -eq $Content) {
        return @()
    }

    if ($Content.Length -eq 0) {
        return @()
    }

    return @(
        $Content -split "`r?`n",-1
    )
}

function Normalize-LineEndings {
    param(
        [Parameter(Mandatory)]
        [string]$Content
    )

    return (
        $Content `
            .Replace("`r`n","`n") `
            .Replace("`r","`n")
    )
}

function Get-ParserDiagnostics {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    $diagnostics = [System.Collections.Generic.List[object]]::new()

    try {
        $tokens = $null
        $parseErrors = $null

        [System.Management.Automation.Language.Parser]::ParseFile(
            $Path,
            [ref]$tokens,
            [ref]$parseErrors
        ) | Out-Null

        if ($null -ne $parseErrors) {
            foreach ($parseItem in @($parseErrors)) {

                $message = [string]$parseItem.Message

                $lineNumber = 0
                $columnNumber = 0

                if ($null -ne $parseItem.Extent) {
                    $lineNumber = [int]$parseItem.Extent.StartLineNumber
                    $columnNumber = [int]$parseItem.Extent.StartColumnNumber
                }

                $diagnostics.Add(
                    [pscustomobject]@{
                        Message      = $message
                        Line         = $lineNumber
                        Column       = $columnNumber
                        ExtentText   = if ($null -ne $parseItem.Extent) {
                            [string]$parseItem.Extent.Text
                        }
                        else {
                            ''
                        }
                    }
                )
            }
        }
    }
    catch {
        $diagnostics.Add(
            [pscustomobject]@{
                Message    = "Parser invocation failure: $($_.Exception.Message)"
                Line       = 0
                Column     = 0
                ExtentText = ''
            }
        )
    }

    return @($diagnostics)
}

function Get-ParserErrorCount {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    return @(
        Get-ParserDiagnostics -Path $Path
    ).Count
}

function Get-TextFingerprint {
    param(
        [Parameter(Mandatory)]
        [string]$Content
    )

    $bytes = [System.Text.UTF8Encoding]::new($false).GetBytes($Content)

    $hash = [System.Security.Cryptography.SHA256]::Create()

    try {
        return (
            $hash.ComputeHash($bytes) |
            ForEach-Object { $_.ToString('x2') }
        ) -join ''
    }
    finally {
        $hash.Dispose()
    }
}

# ============================================================================
# SAFE TEXT TRANSFORMATIONS
# ============================================================================

function Remove-InvisibleCharacters {
    param(
        [Parameter(Mandatory)]
        [string]$Content
    )

    # IMPORTANT :
    # On utilise Regex.Replace(string,string) pour les suppressions.
    # AUCUN Replace(char,char) avec ''.

    $result = $Content

    $result = [regex]::Replace(
        $result,
        '[\u0000]',
        ''
    )

    $result = [regex]::Replace(
        $result,
        '[\u200B\u200C\u200D\uFEFF]',
        ''
    )

    return $result
}

function Normalize-SmartQuotes {
    param(
        [Parameter(Mandatory)]
        [string]$Content
    )

    $result = $Content

    $result = $result.Replace([string][char]0x2018, "'")
    $result = $result.Replace([string][char]0x2019, "'")
    $result = $result.Replace([string][char]0x201A, "'")
    $result = $result.Replace([string][char]0x201B, "'")

    $result = $result.Replace([string][char]0x201C, '"')
    $result = $result.Replace([string][char]0x201D, '"')
    $result = $result.Replace([string][char]0x201E, '"')
    $result = $result.Replace([string][char]0x201F, '"')

    return $result
}

function Normalize-UnicodeDashes {
    param(
        [Parameter(Mandatory)]
        [string]$Content
    )

    $result = $Content

    $result = $result.Replace([string][char]0x2010, '-')
    $result = $result.Replace([string][char]0x2011, '-')
    $result = $result.Replace([string][char]0x2012, '-')
    $result = $result.Replace([string][char]0x2013, '-')
    $result = $result.Replace([string][char]0x2014, '-')
    $result = $result.Replace([string][char]0x2015, '-')

    return $result
}

function Remove-MarkdownFences {
    param(
        [Parameter(Mandatory)]
        [string]$Content
    )

    $result = [regex]::Replace(
        $Content,
        '(?m)^\s*```(?:powershell|pwsh|ps1)?\s*$',
        ''
    )

    $result = [regex]::Replace(
        $result,
        '(?m)^\s*```\s*$',
        ''
    )

    return $result
}

function Remove-ConsolePrompts {
    param(
        [Parameter(Mandatory)]
        [string]$Content
    )

    $result = [regex]::Replace(
        $Content,
        '(?m)^\s*PS\s+[A-Za-z]:\\.*?>\s?',
        ''
    )

    $result = [regex]::Replace(
        $result,
        '(?m)^\s*>>\s?',
        ''
    )

    return $result
}

function Normalize-BacktickWhitespace {
    param(
        [Parameter(Mandatory)]
        [string]$Content
    )

    # Suppression des espaces invisibles placés après un backtick.
    # On conserve le backtick lui-même.
    return [regex]::Replace(
        $Content,
        '(?m)`[ \t]+$',
        '`'
    )
}

function Normalize-LineEndingStrategy {
    param(
        [Parameter(Mandatory)]
        [string]$Content
    )

    return Normalize-LineEndings -Content $Content
}

function Remove-TranscriptMarkers {
    param(
        [Parameter(Mandatory)]
        [string]$Content
    )

    $result = $Content

    $result = [regex]::Replace(
        $result,
        '(?m)^\s*PS\s+[A-Za-z]:\\.*?>.*$',
        ''
    )

    $result = [regex]::Replace(
        $result,
        '(?m)^\s*Appuie sur ENTREE.*$',
        ''
    )

    return $result
}

# ============================================================================
# STRATEGY APPLICATION
# ============================================================================

function Invoke-RepairStrategy {
    param(
        [Parameter(Mandatory)]
        [string]$Strategy,

        [Parameter(Mandatory)]
        [string]$Content
    )

    switch ($Strategy) {

        'SMART_QUOTES' {
            return Normalize-SmartQuotes -Content $Content
        }

        'UNICODE_DASHES' {
            return Normalize-UnicodeDashes -Content $Content
        }

        'INVISIBLE_CHARS' {
            return Remove-InvisibleCharacters -Content $Content
        }

        'MARKDOWN_FENCES' {
            return Remove-MarkdownFences -Content $Content
        }

        'CONSOLE_PROMPTS' {
            return Remove-ConsolePrompts -Content $Content
        }

        'BACKTICK_WHITESPACE' {
            return Normalize-BacktickWhitespace -Content $Content
        }

        'NUL_CHARS' {
            return [regex]::Replace(
                $Content,
                '[\u0000]',
                ''
            )
        }

        'LINE_ENDINGS' {
            return Normalize-LineEndingStrategy -Content $Content
        }

        'TRANSCRIPT_MARKERS' {
            return Remove-TranscriptMarkers -Content $Content
        }

        default {
            throw "Stratégie inconnue : $Strategy"
        }
    }
}

# ============================================================================
# CANDIDATE WRITER
# ============================================================================

function Write-CandidateContent {
    param(
        [Parameter(Mandatory)]
        [string]$Path,

        [Parameter(Mandatory)]
        [AllowEmptyString()]
        [string]$Content
    )

    Write-Utf8NoBom `
        -Path $Path `
        -Content $Content
}

# ============================================================================
# MAIN
# ============================================================================

try {

    Write-Banner "$EngineName v$ScriptVersion"

    Write-Field 'PROJECT' $ProjectRoot
    Write-Field 'MODE' 'READ-ONLY / CANDIDATE-ONLY / FAIL-CLOSED'
    Write-Field 'QUALITY' 'FORENSIC / DETERMINISTIC / CERTIFICATION-GRADE'
    Write-Field 'SOURCE MUTATION' 'DISABLED'
    Write-Field 'EXECUTION' 'DISABLED'
    Write-Field 'PROMOTION' 'DISABLED'

    # ========================================================================
    # 1
    # ========================================================================

    Write-Step '1/18' 'Validation environnement...'

    Assert-Directory `
        -Path $ProjectRoot `
        -Name 'PROJECT ROOT'

    Assert-Directory `
        -Path $ReportsRoot `
        -Name 'REPORT ROOT'

    $psVersion = $PSVersionTable.PSVersion.ToString()

    Write-Field 'POWERSHELL' $psVersion
    Write-Field 'ENVIRONMENT' 'PASS'

    # ========================================================================
    # 2
    # ========================================================================

    Write-Step '2/18' 'Recherche du dernier REPAIR_DOSSIER...'

    $repairDossiers = @(
        Get-ChildItem `
            -LiteralPath $ReportsRoot `
            -Directory `
            -ErrorAction Stop |
        Where-Object {
            Test-Path `
                -LiteralPath (Join-Path $_.FullName 'REPAIR_DOSSIER') `
                -PathType Container
        } |
        Sort-Object LastWriteTimeUtc -Descending
    )

    if ($repairDossiers.Count -eq 0) {
        throw 'Aucun REPAIR_DOSSIER trouvé.'
    }

    $RepairDossier = Join-Path `
        $repairDossiers[0].FullName `
        'REPAIR_DOSSIER'

    $MatrixPath = Join-Path `
        $RepairDossier `
        'ROOT_CAUSE_MATRIX.json'

    Assert-Directory `
        -Path $RepairDossier `
        -Name 'REPAIR_DOSSIER'

    Assert-File `
        -Path $MatrixPath `
        -Name 'ROOT_CAUSE_MATRIX.json'

    Write-Field 'DOSSIER' $RepairDossier
    Write-Field 'MATRIX' $MatrixPath
    Write-Field 'DISCOVERY' 'PASS'

    # ========================================================================
    # 3
    # ========================================================================

    Write-Step '3/18' 'Chargement de la Root-Cause Matrix...'

    $matrixRaw = Read-Utf8File -Path $MatrixPath

    if ([string]::IsNullOrWhiteSpace($matrixRaw)) {
        throw 'ROOT_CAUSE_MATRIX.json est vide.'
    }

    $matrix = $matrixRaw | ConvertFrom-Json

    $rootCauseItems = @()

    if ($matrix -is [System.Collections.IEnumerable] -and
        $matrix -isnot [string]) {

        $rootCauseItems = @($matrix)

    }
    elseif ($null -ne $matrix.RootCauses) {

        $rootCauseItems = @($matrix.RootCauses)

    }
    elseif ($null -ne $matrix.RootCauseMatrix) {

        $rootCauseItems = @($matrix.RootCauseMatrix)

    }
    else {

        $properties = @(
            $matrix.PSObject.Properties
        )

        $rootCauseItems = @(
            $properties |
            Where-Object {
                $_.Name -match 'Root|Cause|Issue|Problem'
            } |
            ForEach-Object {
                $_.Value
            }
        )
    }

    $RootCauseCount = $rootCauseItems.Count

    Write-Field 'ROOT CAUSES' $RootCauseCount

    # ========================================================================
    # 4
    # ========================================================================

    Write-Step '4/18' 'Identification forensic des fichiers cibles...'

    $candidatePathSet = [System.Collections.Generic.HashSet[string]]::new(
        [System.StringComparer]::OrdinalIgnoreCase
    )

    foreach ($rootItem in $rootCauseItems) {

        foreach ($propertyName in @(
            'File',
            'FilePath',
            'Path',
            'SourceFile',
            'TargetFile',
            'TargetPath'
        )) {

            $property = $rootItem.PSObject.Properties[$propertyName]

            if ($null -eq $property) {
                continue
            }

            $rawPath = [string]$property.Value

            if ([string]::IsNullOrWhiteSpace($rawPath)) {
                continue
            }

            $resolvedPath = $rawPath

            if (-not [System.IO.Path]::IsPathRooted($resolvedPath)) {
                $resolvedPath = Join-Path $ProjectRoot $resolvedPath
            }

            try {
                $resolvedPath = [System.IO.Path]::GetFullPath($resolvedPath)
            }
            catch {
                continue
            }

            if (-not $resolvedPath.StartsWith(
                $ProjectRoot,
                [System.StringComparison]::OrdinalIgnoreCase
            )) {
                continue
            }

            if (Test-Path -LiteralPath $resolvedPath -PathType Leaf) {

                $extension = [System.IO.Path]::GetExtension($resolvedPath)

                if ($extension -ieq '.ps1' -or
                    $extension -ieq '.psm1' -or
                    $extension -ieq '.psd1') {

                    [void]$candidatePathSet.Add($resolvedPath)
                }
            }
        }
    }

    # Fallback forensic scan si la matrice ne fournit pas directement les
    # chemins exploitables.
    if ($candidatePathSet.Count -eq 0) {

        $fallbackFiles = @(
            Get-ChildItem `
                -LiteralPath $ProjectRoot `
                -Recurse `
                -File `
                -ErrorAction SilentlyContinue |
            Where-Object {
                $_.Extension -in @('.ps1','.psm1','.psd1') -and
                $_.FullName -notmatch '\\_EZZIO_TRUTH_REPORTS\\'
            }
        )

        foreach ($file in $fallbackFiles) {
            [void]$candidatePathSet.Add($file.FullName)
        }
    }

    $TargetPaths = @(
        $candidatePathSet |
        Sort-Object
    )

    $TargetFileCount = $TargetPaths.Count

    if ($TargetFileCount -eq 0) {
        throw 'Aucun fichier PowerShell cible détecté.'
    }

    Write-Field 'TARGET FILES' $TargetFileCount

    # ========================================================================
    # 5
    # ========================================================================

    Write-Step '5/18' 'Création du laboratoire forensic...'

    $RunId = New-RunId

    $RunRoot = Join-Path `
        $ReportsRoot `
        $RunId

    $Workbench = Join-Path `
        $RunRoot `
        'SUPER_FORENSIC_REPAIR_LAB'

    $CandidatesRoot = Join-Path `
        $Workbench `
        'CANDIDATES'

    $EvidenceRoot = Join-Path `
        $Workbench `
        'EVIDENCE'

    $ReportsPath = Join-Path `
        $Workbench `
        'REPORTS'

    $AcceptedRoot = Join-Path `
        $Workbench `
        'ACCEPTED_CANDIDATES'

    foreach ($directory in @(
        $Workbench,
        $CandidatesRoot,
        $EvidenceRoot,
        $ReportsPath,
        $AcceptedRoot
    )) {
        [System.IO.Directory]::CreateDirectory($directory) | Out-Null
    }

    Write-Field 'RUN ID' $RunId
    Write-Field 'WORKBENCH' $Workbench
    Write-Field 'WORKBENCH' 'PASS'

    # ========================================================================
    # 6
    # ========================================================================

    Write-Step '6/18' 'Construction du baseline SHA-256 + parser original...'

    $BaselineRecords = [System.Collections.Generic.List[object]]::new()

    foreach ($targetPath in $TargetPaths) {

        $relativePath = [System.IO.Path]::GetRelativePath(
            $ProjectRoot,
            $targetPath
        )

        $sourceContent = Read-Utf8File -Path $targetPath

        $diagnostics = @(
            Get-ParserDiagnostics -Path $targetPath
        )

        $BaselineRecords.Add(
            [pscustomobject]@{
                SourcePath       = $targetPath
                RelativePath     = $relativePath
                OriginalHash     = Get-FileSha256 -Path $targetPath
                OriginalSize     = (Get-Item -LiteralPath $targetPath).Length
                OriginalErrors   = $diagnostics.Count
                Diagnostics      = @($diagnostics)
                Content          = $sourceContent
            }
        )
    }

    $OriginalErrorCount = (
        $BaselineRecords |
        Measure-Object -Property OriginalErrors -Sum
    ).Sum

    if ($null -eq $OriginalErrorCount) {
        $OriginalErrorCount = 0
    }

    Write-Field 'BASELINE FILES' $BaselineRecords.Count
    Write-Field 'PARSER ERRORS' $OriginalErrorCount

    # ========================================================================
    # 7
    # ========================================================================

    Write-Step '7/18' 'Clonage strict des sources...'

    foreach ($baseline in $BaselineRecords) {

        $candidatePath = Join-Path `
            $CandidatesRoot `
            $baseline.RelativePath

        $candidateParent = Split-Path `
            -Parent `
            $candidatePath

        [System.IO.Directory]::CreateDirectory(
            $candidateParent
        ) | Out-Null

        # Copie de bytes / texte dans zone isolée uniquement.
        Copy-Item `
            -LiteralPath $baseline.SourcePath `
            -Destination $candidatePath `
            -Force

        $candidateHash = Get-FileSha256 -Path $candidatePath

        if ($candidateHash -ne $baseline.OriginalHash) {
            throw "Clonage SHA-256 invalide : $($baseline.SourcePath)"
        }
    }

    Write-Field 'CLONED' $BaselineRecords.Count

    # ========================================================================
    # 8
    # ========================================================================

    Write-Step '8/18' 'Revalidation parser des candidats clonés...'

    $CandidateBaselineRecords = [System.Collections.Generic.List[object]]::new()

    foreach ($baseline in $BaselineRecords) {

        $candidatePath = Join-Path `
            $CandidatesRoot `
            $baseline.RelativePath

        $candidateDiagnostics = @(
            Get-ParserDiagnostics -Path $candidatePath
        )

        $CandidateBaselineRecords.Add(
            [pscustomobject]@{
                RelativePath   = $baseline.RelativePath
                CandidatePath  = $candidatePath
                ParserErrors   = $candidateDiagnostics.Count
                Diagnostics    = @($candidateDiagnostics)
                Hash           = Get-FileSha256 -Path $candidatePath
            }
        )
    }

    $CandidateBaselineErrorCount = (
        $CandidateBaselineRecords |
        Measure-Object -Property ParserErrors -Sum
    ).Sum

    if ($null -eq $CandidateBaselineErrorCount) {
        $CandidateBaselineErrorCount = 0
    }

    Write-Field 'CANDIDATE BASELINE' $CandidateBaselineErrorCount

    # ========================================================================
    # 9
    # ========================================================================

    Write-Step '9/18' 'Construction de la file des erreurs parser...'

    $ErrorQueue = [System.Collections.Generic.List[object]]::new()

    foreach ($record in $CandidateBaselineRecords) {

        foreach ($diagnosticItem in @($record.Diagnostics)) {

            $ErrorQueue.Add(
                [pscustomobject]@{
                    RelativePath = $record.RelativePath
                    CandidatePath = $record.CandidatePath
                    Message      = [string]$diagnosticItem.Message
                    Line         = [int]$diagnosticItem.Line
                    Column       = [int]$diagnosticItem.Column
                    ExtentText   = [string]$diagnosticItem.ExtentText
                }
            )
        }
    }

    Write-Field 'ERROR QUEUE' $ErrorQueue.Count

    # ========================================================================
    # 10
    # ========================================================================

    Write-Step '10/18' 'Chargement des stratégies de réparation...'

    $Strategies = @(
        'SMART_QUOTES'
        'UNICODE_DASHES'
        'INVISIBLE_CHARS'
        'MARKDOWN_FENCES'
        'CONSOLE_PROMPTS'
        'BACKTICK_WHITESPACE'
        'NUL_CHARS'
        'LINE_ENDINGS'
        'TRANSCRIPT_MARKERS'
    )

    Write-Field 'STRATEGIES' $Strategies.Count

    foreach ($strategyName in $Strategies) {
        Write-Host "      - $strategyName"
    }

    # ========================================================================
    # 11
    # ========================================================================

    Write-Step '11/18' 'Scan de toutes les stratégies sur tous les candidats...'

    $TrialRoot = Join-Path `
        $Workbench `
        'TRIALS'

    [System.IO.Directory]::CreateDirectory($TrialRoot) | Out-Null

    $TrialResults = [System.Collections.Generic.List[object]]::new()

    $attemptCounter = 0

    foreach ($baseline in $BaselineRecords) {

        $candidatePath = Join-Path `
            $CandidatesRoot `
            $baseline.RelativePath

        $baseContent = Read-Utf8File -Path $candidatePath

        foreach ($strategyName in $Strategies) {

            $attemptCounter++

            $trialId = '{0:D5}' -f $attemptCounter

            $trialDirectory = Join-Path `
                $TrialRoot `
                $trialId

            [System.IO.Directory]::CreateDirectory(
                $trialDirectory
            ) | Out-Null

            $trialRelative = $baseline.RelativePath

            $trialPath = Join-Path `
                $trialDirectory `
                $trialRelative

            $trialParent = Split-Path `
                -Parent `
                $trialPath

            [System.IO.Directory]::CreateDirectory(
                $trialParent
            ) | Out-Null

            $trialContent = $null
            $strategyException = $null

            try {

                $trialContent = Invoke-RepairStrategy `
                    -Strategy $strategyName `
                    -Content $baseContent

                if ($null -eq $trialContent) {
                    $trialContent = $baseContent
                }

                # Écriture exclusivement dans TRIALS.
                Write-CandidateContent `
                    -Path $trialPath `
                    -Content ([string]$trialContent)
            }
            catch {

                $strategyException = $_.Exception.Message
            }

            $trialErrors = -1
            $trialHash = ''

            if ($null -eq $strategyException) {

                $trialErrors = Get-ParserErrorCount `
                    -Path $trialPath

                $trialHash = Get-FileSha256 `
                    -Path $trialPath
            }

            $baselineErrors = [int]$baseline.OriginalErrors

            $delta = $baselineErrors - $trialErrors

            $status = 'REJECTED'

            if ($null -ne $strategyException) {
                $status = 'STRATEGY_ERROR'
            }
            elseif ($trialErrors -lt $baselineErrors) {
                $status = 'IMPROVED'
            }
            elseif ($trialErrors -gt $baselineErrors) {
                $status = 'REGRESSION'
            }
            elseif ($trialHash -eq $baseline.OriginalHash) {
                $status = 'NO_CHANGE'
            }
            else {
                $status = 'EQUAL_ERROR_COUNT'
            }

            $TrialResults.Add(
                [pscustomobject]@{
                    TrialId          = $trialId
                    RelativePath     = $baseline.RelativePath
                    SourcePath       = $baseline.SourcePath
                    Strategy         = $strategyName
                    BaselineErrors   = $baselineErrors
                    TrialErrors      = $trialErrors
                    Improvement      = $delta
                    BaselineHash     = $baseline.OriginalHash
                    TrialHash        = $trialHash
                    Status           = $status
                    StrategyError    = if ($null -eq $strategyException) {
                        ''
                    }
                    else {
                        $strategyException
                    }
                }
            )
        }
    }

    Write-Field 'ATTEMPTS' $TrialResults.Count

    # ========================================================================
    # 12
    # ========================================================================

    Write-Step '12/18' 'Sélection stricte des améliorations...'

    $ImprovedTrials = @(
        $TrialResults |
        Where-Object {
            $_.Status -eq 'IMPROVED' -and
            $_.Improvement -gt 0 -and
            $_.TrialErrors -ge 0
        } |
        Sort-Object `
            @{Expression='Improvement';Descending=$true},
            @{Expression='TrialErrors';Descending=$false},
            @{Expression='Strategy';Descending=$false},
            @{Expression='RelativePath';Descending=$false}
    )

    $RegressionTrials = @(
        $TrialResults |
        Where-Object {
            $_.Status -eq 'REGRESSION'
        }
    )

    $AcceptedTrials = @(
        $ImprovedTrials
    )

    # Aucune promotion. Les accepted sont uniquement des candidats
    # forensic ayant mathématiquement réduit le nombre d'erreurs.
    foreach ($acceptedTrial in $AcceptedTrials) {

        $sourceTrialPath = Join-Path `
            $TrialRoot `
            $acceptedTrial.TrialId

        $destinationPath = Join-Path `
            $AcceptedRoot `
            $acceptedTrial.RelativePath

        $destinationParent = Split-Path `
            -Parent `
            $destinationPath

        [System.IO.Directory]::CreateDirectory(
            $destinationParent
        ) | Out-Null

        Copy-Item `
            -LiteralPath (
                Join-Path `
                    $sourceTrialPath `
                    $acceptedTrial.RelativePath
            ) `
            -Destination $destinationPath `
            -Force
    }

    $AcceptedCount = $AcceptedTrials.Count

    $RejectedCount = @(
        $TrialResults |
        Where-Object {
            $_.Status -ne 'IMPROVED'
        }
    ).Count

    $RegressionCount = $RegressionTrials.Count

    Write-Field 'IMPROVED' $ImprovedTrials.Count
    Write-Field 'ACCEPTED' $AcceptedCount
    Write-Field 'REJECTED' $RejectedCount
    Write-Field 'REGRESSIONS' $RegressionCount

    # ========================================================================
    # 13
    # ========================================================================

    Write-Step '13/18' 'Vérification de l''intégrité des sources originales...'

    $SourceMutationCount = 0

    $IntegrityRecords = [System.Collections.Generic.List[object]]::new()

    foreach ($baseline in $BaselineRecords) {

        $currentHash = Get-FileSha256 `
            -Path $baseline.SourcePath

        $mutated = $currentHash -ne $baseline.OriginalHash

        if ($mutated) {
            $SourceMutationCount++
        }

        $IntegrityRecords.Add(
            [pscustomobject]@{
                Path          = $baseline.SourcePath
                RelativePath  = $baseline.RelativePath
                BaselineHash  = $baseline.OriginalHash
                CurrentHash   = $currentHash
                Mutated       = $mutated
            }
        )
    }

    if ($SourceMutationCount -ne 0) {
        throw "SOURCE MUTATION DETECTED : $SourceMutationCount"
    }

    Write-Field 'SOURCE MUTATIONS' $SourceMutationCount
    Write-Field 'SOURCE INTEGRITY' 'PASS'

    # ========================================================================
    # 14
    # ========================================================================

    Write-Step '14/18' 'Calcul du verdict global...'

    $GlobalImprovement = (
        $TrialResults |
        Where-Object {
            $_.Improvement -gt 0
        } |
        Measure-Object -Property Improvement -Sum
    ).Sum

    if ($null -eq $GlobalImprovement) {
        $GlobalImprovement = 0
    }

    $OriginalTotal = [int]$OriginalErrorCount

    if ($OriginalTotal -gt 0) {

        $ImprovementRatio = [math]::Round(
            (
                [double]$GlobalImprovement /
                [double]$OriginalTotal
            ) * 100,
            2
        )
    }
    else {
        $ImprovementRatio = 0
    }

    if ($AcceptedCount -gt 0) {

        $GlobalVerdict = 'IMPROVEMENT-CANDIDATES / FAIL-CLOSED'
    }
    else {

        $GlobalVerdict = 'NO-IMPROVEMENT / FAIL-CLOSED'
    }

    Write-Field 'GLOBAL IMPROVEMENT' $GlobalImprovement
    Write-Field 'IMPROVEMENT RATIO' "$ImprovementRatio %"
    Write-Field 'VERDICT' $GlobalVerdict

    # ========================================================================
    # 15
    # ========================================================================

    Write-Step '15/18' 'Vérification de l''absence d''exécution...'

    # Ce moteur ne contient volontairement aucun Invoke-Expression,
    # aucune & sur les candidats et aucun lancement de processus.
    $ExecutionPerformed = $false

    Write-Field 'EXECUTION' 'DISABLED'
    Write-Field 'EXECUTION PERFORMED' $ExecutionPerformed

    # ========================================================================
    # 16
    # ========================================================================

    Write-Step '16/18' 'Génération des preuves forensic...'

    $EvidencePath = Join-Path `
        $EvidenceRoot `
        'TRIAL_RESULTS.json'

    $IntegrityPath = Join-Path `
        $EvidenceRoot `
        'SOURCE_INTEGRITY.json'

    $BaselinePath = Join-Path `
        $EvidenceRoot `
        'BASELINE.json'

    $StrategiesPath = Join-Path `
        $EvidenceRoot `
        'STRATEGIES.json'

    @($TrialResults) |
        ConvertTo-Json -Depth 20 |
        Set-Content `
            -LiteralPath $EvidencePath `
            -Encoding utf8

    @($IntegrityRecords) |
        ConvertTo-Json -Depth 20 |
        Set-Content `
            -LiteralPath $IntegrityPath `
            -Encoding utf8

    @(
        $BaselineRecords |
        ForEach-Object {
            [pscustomobject]@{
                SourcePath     = $_.SourcePath
                RelativePath   = $_.RelativePath
                OriginalHash   = $_.OriginalHash
                OriginalSize   = $_.OriginalSize
                OriginalErrors = $_.OriginalErrors
            }
        }
    ) |
        ConvertTo-Json -Depth 20 |
        Set-Content `
            -LiteralPath $BaselinePath `
            -Encoding utf8

    @($Strategies) |
        ConvertTo-Json -Depth 10 |
        Set-Content `
            -LiteralPath $StrategiesPath `
            -Encoding utf8

    Write-Field 'EVIDENCE' 'PASS'

    # ========================================================================
    # 17
    # ========================================================================

    Write-Step '17/18' 'Génération du manifeste forensic...'

    $ManifestPath = Join-Path `
        $ReportsPath `
        'SUPER_FORENSIC_REPAIR_LAB_V5_MANIFEST.json'

    $Manifest = [ordered]@{
        Engine                  = $EngineName
        Version                 = $ScriptVersion
        RunId                   = $RunId
        TimestampUtc            = [DateTime]::UtcNow.ToString('o')
        ProjectRoot             = $ProjectRoot
        RepairDossier           = $RepairDossier

        RootCauses              = $RootCauseCount
        TargetFiles             = $TargetFileCount

        BaselineParserErrors    = $OriginalErrorCount
        CandidateBaselineErrors = $CandidateBaselineErrorCount

        TrialCount              = $TrialResults.Count
        ImprovedTrials          = $ImprovedTrials.Count
        AcceptedCandidates      = $AcceptedCount
        RejectedCandidates      = $RejectedCount
        RegressionCandidates    = $RegressionCount

        GlobalImprovement       = $GlobalImprovement
        ImprovementRatio        = $ImprovementRatio

        SourceMutationCount     = $SourceMutationCount
        SourceMutation          = $SourceMutation

        ExecutionPerformed      = $ExecutionPerformed
        PromotionPerformed      = $PromotionPerformed

        Certified               = $Certified
        CertifiedAuthorized     = $CertifiedAuthorized

        Verdict                 = $GlobalVerdict

        Contracts               = [ordered]@{
            OriginalSourceMutation = $false
            CandidateExecution     = $false
            AutomaticPromotion     = $false
            CertificationGrant    = $false
        }
    }

    $Manifest |
        ConvertTo-Json -Depth 30 |
        Set-Content `
            -LiteralPath $ManifestPath `
            -Encoding utf8

    Write-Field 'MANIFEST' $ManifestPath

    # ========================================================================
    # 18
    # ========================================================================

    Write-Step '18/18' 'Génération du rapport final...'

    $ReportPath = Join-Path `
        $ReportsPath `
        'SUPER_FORENSIC_REPAIR_LAB_V5_REPORT.txt'

    $reportLines = @(
        '============================================================================'
        ' E-ZZIO — TRUTH SUPER FORENSIC REPAIR LAB v5.2.0'
        '============================================================================'
        ''
        "RUN ID                  : $RunId"
        "PROJECT                 : $ProjectRoot"
        "REPAIR DOSSIER         : $RepairDossier"
        ''
        "ROOT CAUSES             : $RootCauseCount"
        "TARGET FILES            : $TargetFileCount"
        "BASELINE PARSER ERRORS : $OriginalErrorCount"
        "CANDIDATE BASELINE     : $CandidateBaselineErrorCount"
        ''
        "STRATEGIES              : $($Strategies.Count)"
        "TRIALS                  : $($TrialResults.Count)"
        "IMPROVED                : $($ImprovedTrials.Count)"
        "ACCEPTED                : $AcceptedCount"
        "REJECTED                : $RejectedCount"
        "REGRESSIONS             : $RegressionCount"
        ''
        "GLOBAL IMPROVEMENT      : $GlobalImprovement"
        "IMPROVEMENT RATIO      : $ImprovementRatio %"
        ''
        "SOURCE MUTATION         : $SourceMutation"
        "SOURCE MUTATION COUNT   : $SourceMutationCount"
        "EXECUTION               : $ExecutionPerformed"
        "PROMOTION               : $PromotionPerformed"
        "CERTIFIED               : $Certified"
        "CERTIFIED AUTHORIZED    : $CertifiedAuthorized"
        ''
        "VERDICT                 : $GlobalVerdict"
        ''
        "WORKBENCH               : $Workbench"
        "CANDIDATES              : $CandidatesRoot"
        "ACCEPTED CANDIDATES    : $AcceptedRoot"
        "EVIDENCE                : $EvidenceRoot"
        "REPORT                  : $ReportPath"
        "MANIFEST                : $ManifestPath"
        ''
        'FAIL-CLOSED : les sources originales n''ont pas été modifiées.'
        'FAIL-CLOSED : aucun candidat n''a été exécuté.'
        'FAIL-CLOSED : aucun candidat n''a été promu vers le projet réel.'
        'FAIL-CLOSED : CERTIFIED n''est jamais accordé par ce laboratoire.'
        ''
        '============================================================================'
    )

    Write-Utf8NoBom `
        -Path $ReportPath `
        -Content ($reportLines -join [Environment]::NewLine)

    # ========================================================================
    # FINAL INTEGRITY
    # ========================================================================

    $finalIntegrityFailures = @(
        $IntegrityRecords |
        Where-Object {
            $_.Mutated -eq $true
        }
    ).Count

    if ($finalIntegrityFailures -ne 0) {
        throw "Final integrity failure : $finalIntegrityFailures"
    }

    Write-Host ''
    Write-Host '============================================================================' -ForegroundColor Green
    Write-Host ' E-ZZIO — TRUTH SUPER FORENSIC REPAIR LAB v5.2.0 COMPLETE' -ForegroundColor Green
    Write-Host '============================================================================' -ForegroundColor Green

    Write-Field 'RUN ID' $RunId
    Write-Field 'ROOT CAUSES' $RootCauseCount
    Write-Field 'TARGET FILES' $TargetFileCount
    Write-Field 'PARSER BASELINE' $OriginalErrorCount
    Write-Field 'TRIALS' $TrialResults.Count
    Write-Field 'IMPROVED' $ImprovedTrials.Count
    Write-Field 'ACCEPTED' $AcceptedCount
    Write-Field 'REJECTED' $RejectedCount
    Write-Field 'REGRESSIONS' $RegressionCount
    Write-Field 'GLOBAL IMPROVEMENT' $GlobalImprovement
    Write-Field 'IMPROVEMENT RATIO' "$ImprovementRatio %"

    Write-Host ''
    Write-Host 'SOURCE MUTATION         : 0' -ForegroundColor Green
    Write-Host 'EXECUTION              : DISABLED' -ForegroundColor Green
    Write-Host 'PROMOTION              : DISABLED' -ForegroundColor Green
    Write-Host 'CERTIFIED              : NOT AUTHORIZED' -ForegroundColor Yellow

    Write-Host ''
    Write-Field 'WORKBENCH' $Workbench
    Write-Field 'EVIDENCE' $EvidenceRoot
    Write-Field 'ACCEPTED CANDIDATES' $AcceptedRoot
    Write-Field 'REPORT' $ReportPath
    Write-Field 'MANIFEST' $ManifestPath

    Write-Host ''
    Write-Host "VERDICT : $GlobalVerdict" -ForegroundColor Cyan

    Write-Host ''
    Write-Host 'FAIL-CLOSED : les sources originales restent intactes.' -ForegroundColor Yellow
    Write-Host 'FAIL-CLOSED : aucun candidat n''est exécuté.' -ForegroundColor Yellow
    Write-Host 'FAIL-CLOSED : aucune promotion automatique.' -ForegroundColor Yellow
    Write-Host 'FAIL-CLOSED : CERTIFIED reste interdit à ce moteur.' -ForegroundColor Yellow
    Write-Host '============================================================================' -ForegroundColor Green
    Write-Host ''

    Read-Host 'Appuie sur ENTREE pour terminer' | Out-Null
}
catch {

    Write-Host ''
    Write-Host '============================================================================' -ForegroundColor Red
    Write-Host ' E-ZZIO — TRUTH SUPER FORENSIC REPAIR LAB FAILED / FAIL-CLOSED' -ForegroundColor Red
    Write-Host '============================================================================' -ForegroundColor Red
    Write-Host ''

    Write-Host "ERROR : $($_.Exception.Message)" -ForegroundColor Red

    if ($null -ne $_.InvocationInfo) {
        Write-Host "LINE  : $($_.InvocationInfo.ScriptLineNumber)" -ForegroundColor Red
        Write-Host "POS   : $($_.InvocationInfo.OffsetInLine)" -ForegroundColor Red
    }

    Write-Host ''
    Write-Host "SOURCE MUTATION : $SourceMutation"
    Write-Host "EXECUTION       : $ExecutionPerformed"
    Write-Host "PROMOTION       : $PromotionPerformed"
    Write-Host "CERTIFIED       : $Certified"
    Write-Host ''
    Write-Host 'Aucune promotion de candidat.' -ForegroundColor Yellow
    Write-Host 'Aucun CERTIFIED autorisé.' -ForegroundColor Yellow
    Write-Host 'Les sources originales restent intactes.' -ForegroundColor Yellow
    Write-Host '============================================================================' -ForegroundColor Red
    Write-Host ''

    Read-Host 'Appuie sur ENTREE pour terminer' | Out-Null
}