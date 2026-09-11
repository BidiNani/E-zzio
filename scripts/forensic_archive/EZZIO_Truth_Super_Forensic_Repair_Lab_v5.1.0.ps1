#requires -Version 7.4

<#
===============================================================================
 E-ZZIO — TRUTH SUPER FORENSIC REPAIR LAB v5.1.0
===============================================================================

PURPOSE
    Forensic candidate repair laboratory.

SECURITY MODEL
    READ-ONLY SOURCE
    CANDIDATE-ONLY
    FAIL-CLOSED
    NO SOURCE MUTATION
    NO EXECUTION OF CANDIDATES
    NO AUTOMATIC PROMOTION
    NO CERTIFICATION AUTHORITY

IMPORTANT
    This engine may create candidate files and forensic reports.
    It NEVER writes into the original E-ZZIO source files.

===============================================================================
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ============================================================================
# CONFIGURATION
# ============================================================================

$EngineName   = 'E-ZZIO — TRUTH SUPER FORENSIC REPAIR LAB'
$ScriptVersion = '5.1.0'
$ProjectRoot  = 'G:\AI\E-zzio'

$ReportsRoot = Join-Path $ProjectRoot '_EZZIO_TRUTH_REPORTS'

$SourceMutation      = $false
$ExecutionPerformed  = $false
$PromotionPerformed  = $false
$Certified           = $false
$CertifiedAuthorized = $false

# ============================================================================
# SAFE RUN ID
# ============================================================================

$TimestampPart = [DateTime]::UtcNow.ToString('yyyyMMdd_HHmmss_fff')
$RandomPart = [Guid]::NewGuid().ToString('N').Substring(0,12)

$RunId = $TimestampPart + '_' + $RandomPart

# ============================================================================
# UI
# ============================================================================

function Write-Banner {
    param(
        [string]$Title
    )

    Write-Host ''
    Write-Host '============================================================================' -ForegroundColor Cyan
    Write-Host (' ' + $Title) -ForegroundColor Cyan
    Write-Host '============================================================================' -ForegroundColor Cyan
}

function Write-Step {
    param(
        [string]$Number,
        [string]$Text
    )

    Write-Host ''
    Write-Host ('[' + $Number + '] ' + $Text) -ForegroundColor White
}

function Write-Info {
    param(
        [string]$Name,
        [object]$Value
    )

    $label = $Name.PadRight(28)
    Write-Host ('      ' + $label + ': ' + [string]$Value)
}

function Write-Utf8NoBom {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,

        [Parameter(Mandatory = $true)]
        [AllowEmptyString()]
        [string]$Content
    )

    $utf8 = [System.Text.UTF8Encoding]::new($false)
    [System.IO.File]::WriteAllText($Path, $Content, $utf8)
}

# ============================================================================
# VALIDATION
# ============================================================================

function Assert-Project {
    if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) {
        throw 'PROJECT ROOT DOES NOT EXIST: ' + $ProjectRoot
    }

    if (-not (Test-Path -LiteralPath $ReportsRoot -PathType Container)) {
        New-Item -ItemType Directory -Path $ReportsRoot -Force | Out-Null
    }

    $psVersion = $PSVersionTable.PSVersion

    if ($psVersion.Major -lt 7) {
        throw 'PowerShell 7+ is required.'
    }
}

# ============================================================================
# SHA-256
# ============================================================================

function Get-FileHashSafe {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw 'File not found: ' + $Path
    }

    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash
}

# ============================================================================
# POWERSHELL PARSER
# ============================================================================

function Get-PowerShellParseResult {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $tokens = $null
    $parseErrors = $null

    $ast = [System.Management.Automation.Language.Parser]::ParseFile(
        $Path,
        [ref]$tokens,
        [ref]$parseErrors
    )

    $records = @()

    foreach ($parseIssue in @($parseErrors)) {

        $lineNumber = 0
        $columnNumber = 0

        if ($null -ne $parseIssue.Extent) {
            $lineNumber = $parseIssue.Extent.StartLineNumber
            $columnNumber = $parseIssue.Extent.StartColumnNumber
        }

        $records += [pscustomobject]@{
            File       = $Path
            ErrorId    = [string]$parseIssue.ErrorId
            Message    = [string]$parseIssue.Message
            Line       = $lineNumber
            Column     = $columnNumber
            Text       = [string]$parseIssue.Extent.Text
        }
    }

    return [pscustomobject]@{
        Path       = $Path
        AST        = $ast
        Errors     = @($records)
        ErrorCount = @($records).Count
    }
}

# ============================================================================
# SOURCE TEXT
# ============================================================================

function Read-TextSafe {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    return [System.IO.File]::ReadAllText($Path)
}

# ============================================================================
# STRATEGY APPLICATION
# ============================================================================

function Invoke-Strategy {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Strategy,

        [Parameter(Mandatory = $true)]
        [string]$Content
    )

    $result = $Content

    switch ($Strategy) {

        'SMART_QUOTES' {
            $result = $result.Replace([char]0x2018, [char]0x27)
            $result = $result.Replace([char]0x2019, [char]0x27)
            $result = $result.Replace([char]0x201C, [char]0x22)
            $result = $result.Replace([char]0x201D, [char]0x22)
        }

        'UNICODE_DASHES' {
            $result = $result.Replace([char]0x2013, [char]0x2D)
            $result = $result.Replace([char]0x2014, [char]0x2D)
            $result = $result.Replace([char]0x2212, [char]0x2D)
        }

        'INVISIBLE_CHARS' {
            $result = $result.Replace([char]0x200B, '')
            $result = $result.Replace([char]0x200C, '')
            $result = $result.Replace([char]0x200D, '')
            $result = $result.Replace([char]0xFEFF, '')
            $result = $result.Replace([char]0x00A0, ' ')
        }

        'MARKDOWN_FENCES' {
            $result = [regex]::Replace(
                $result,
                '(?m)^\s*```(?:powershell|pwsh|ps1)?\s*$',
                ''
            )
        }

        'CONSOLE_PROMPTS' {
            $result = [regex]::Replace(
                $result,
                '(?m)^\s*(?:PS\s+[A-Za-z]:\\.*?>|>>)\s*',
                ''
            )
        }

        'BACKTICK_WHITESPACE' {
            $result = [regex]::Replace(
                $result,
                '(?m)`[ \t]+\r?$',
                '`'
            )
        }

        'NUL_CHARS' {
            $result = $result.Replace([char]0x0000, '')
        }

        'LINE_ENDINGS' {
            $result = $result.Replace("`r`n", "`n")
            $result = $result.Replace("`r", "`n")
            $result = $result.Replace("`n", [Environment]::NewLine)
        }

        'TRANSCRIPT_MARKERS' {
            $result = [regex]::Replace(
                $result,
                '(?m)^\s*(?:Appuie sur ENTREE.*|La fenêtre reste ouverte\..*|PS G:\\.*?>.*)$',
                ''
            )
        }

        default {
            throw 'Unknown repair strategy: ' + $Strategy
        }
    }

    return $result
}

# ============================================================================
# CANDIDATE WRITE
# ============================================================================

function Write-Candidate {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,

        [Parameter(Mandatory = $true)]
        [AllowEmptyString()]
        [string]$Content
    )

    Write-Utf8NoBom -Path $Path -Content $Content
}

# ============================================================================
# SAFE TARGET DISCOVERY
# ============================================================================

function Get-TargetFilesFromMatrix {
    param(
        [Parameter(Mandatory = $true)]
        [string]$MatrixPath
    )

    $raw = Get-Content -LiteralPath $MatrixPath -Raw -Encoding UTF8

    if ([string]::IsNullOrWhiteSpace($raw)) {
        throw 'ROOT CAUSE MATRIX IS EMPTY.'
    }

    $matrix = $raw | ConvertFrom-Json

    $paths = New-Object System.Collections.Generic.List[string]

    foreach ($record in @($matrix)) {

        $possibleProperties = @(
            'File',
            'Path',
            'FilePath',
            'TargetFile',
            'TargetPath',
            'SourceFile'
        )

        foreach ($propertyName in $possibleProperties) {

            $property = $record.PSObject.Properties[$propertyName]

            if ($null -eq $property) {
                continue
            }

            $candidatePath = [string]$property.Value

            if ([string]::IsNullOrWhiteSpace($candidatePath)) {
                continue
            }

            if (-not [System.IO.Path]::IsPathRooted($candidatePath)) {
                $candidatePath = Join-Path $ProjectRoot $candidatePath
            }

            $candidatePath = [System.IO.Path]::GetFullPath($candidatePath)

            if (
                $candidatePath.StartsWith(
                    [System.IO.Path]::GetFullPath($ProjectRoot),
                    [System.StringComparison]::OrdinalIgnoreCase
                )
            ) {
                if (Test-Path -LiteralPath $candidatePath -PathType Leaf) {
                    if (-not $paths.Contains($candidatePath)) {
                        $paths.Add($candidatePath)
                    }
                }
            }

            break
        }
    }

    return @($paths)
}

# ============================================================================
# ROOT MATRIX DISCOVERY
# ============================================================================

function Find-LatestRepairDossier {
    $directories = @(
        Get-ChildItem `
            -LiteralPath $ReportsRoot `
            -Directory `
            -ErrorAction Stop |
        Where-Object {
            $_.Name -match '^\d{8}_\d{6}_\d{3}_'
        } |
        Sort-Object LastWriteTimeUtc -Descending
    )

    foreach ($directory in $directories) {

        $repairDossier = Join-Path `
            $directory.FullName `
            'REPAIR_DOSSIER'

        $matrixPath = Join-Path `
            $repairDossier `
            'ROOT_CAUSE_MATRIX.json'

        if (
            (Test-Path -LiteralPath $repairDossier -PathType Container) -and
            (Test-Path -LiteralPath $matrixPath -PathType Leaf)
        ) {
            return [pscustomobject]@{
                RootDirectory = $directory.FullName
                RepairDossier = $repairDossier
                MatrixPath    = $matrixPath
            }
        }
    }

    throw 'NO VALID REPAIR_DOSSIER FOUND.'
}

# ============================================================================
# MAIN
# ============================================================================

$Workbench = $null
$Reports = $null
$CandidatesRoot = $null
$EvidenceRoot = $null
$AcceptedRoot = $null

$SourceFiles = @()
$BaselineRecords = @()
$CandidateRecords = @()
$AttemptRecords = @()

$RootCauseCount = 0
$TargetFileCount = 0
$BaselineErrorCount = 0
$FinalErrorCount = 0
$AttemptCount = 0
$AcceptedCount = 0
$RejectedCount = 0
$RegressionCount = 0
$ImprovedCount = 0

$GlobalImprovement = 0
$GlobalVerdict = 'NOT_EVALUATED'

try {

    Write-Banner ($EngineName + ' v' + $ScriptVersion)

    Write-Info 'PROJECT' $ProjectRoot
    Write-Info 'MODE' 'READ-ONLY / CANDIDATE-ONLY / FAIL-CLOSED'
    Write-Info 'QUALITY' 'FORENSIC / DETERMINISTIC / CERTIFICATION-GRADE'
    Write-Info 'SOURCE MUTATION' 'DISABLED'
    Write-Info 'EXECUTION' 'DISABLED'
    Write-Info 'PROMOTION' 'DISABLED'

    # ========================================================================
    # 1
    # ========================================================================

    Write-Step '1/18' 'Validation environnement...'

    Assert-Project

    Write-Info 'POWERSHELL' $PSVersionTable.PSVersion.ToString()
    Write-Info 'ENVIRONMENT' 'PASS'

    # ========================================================================
    # 2
    # ========================================================================

    Write-Step '2/18' 'Recherche du dernier REPAIR_DOSSIER...'

    $dossierInfo = Find-LatestRepairDossier

    $RepairDossier = $dossierInfo.RepairDossier
    $MatrixPath = $dossierInfo.MatrixPath

    Write-Info 'DOSSIER' $RepairDossier
    Write-Info 'MATRIX' $MatrixPath
    Write-Info 'DISCOVERY' 'PASS'

    # ========================================================================
    # 3
    # ========================================================================

    Write-Step '3/18' 'Chargement de la Root-Cause Matrix...'

    $matrixRaw = Get-Content `
        -LiteralPath $MatrixPath `
        -Raw `
        -Encoding UTF8

    if ([string]::IsNullOrWhiteSpace($matrixRaw)) {
        throw 'ROOT CAUSE MATRIX EMPTY.'
    }

    $matrix = @(
        $matrixRaw | ConvertFrom-Json
    )

    $RootCauseCount = $matrix.Count

    Write-Info 'ROOT CAUSES' $RootCauseCount

    # ========================================================================
    # 4
    # ========================================================================

    Write-Step '4/18' 'Identification forensic des fichiers cibles...'

    $SourceFiles = @(
        Get-TargetFilesFromMatrix -MatrixPath $MatrixPath
    )

    $TargetFileCount = $SourceFiles.Count

    if ($TargetFileCount -eq 0) {
        throw 'NO TARGET FILES RESOLVED FROM ROOT CAUSE MATRIX.'
    }

    Write-Info 'TARGET FILES' $TargetFileCount

    # ========================================================================
    # 5
    # ========================================================================

    Write-Step '5/18' 'Création du laboratoire forensic...'

    $RunDirectory = Join-Path `
        $ReportsRoot `
        $RunId

    $Workbench = Join-Path `
        $RunDirectory `
        'SUPER_FORENSIC_REPAIR_LAB'

    $CandidatesRoot = Join-Path `
        $Workbench `
        'CANDIDATES'

    $EvidenceRoot = Join-Path `
        $Workbench `
        'EVIDENCE'

    $AcceptedRoot = Join-Path `
        $Workbench `
        'ACCEPTED_CANDIDATES'

    $Reports = Join-Path `
        $Workbench `
        'REPORTS'

    foreach ($directoryPath in @(
        $Workbench,
        $CandidatesRoot,
        $EvidenceRoot,
        $AcceptedRoot,
        $Reports
    )) {
        New-Item `
            -ItemType Directory `
            -Path $directoryPath `
            -Force |
        Out-Null
    }

    Write-Info 'RUN ID' $RunId
    Write-Info 'WORKBENCH' $Workbench
    Write-Info 'WORKBENCH' 'PASS'

    # ========================================================================
    # 6
    # ========================================================================

    Write-Step '6/18' 'Construction du baseline SHA-256 + parser original...'

    foreach ($sourcePath in $SourceFiles) {

        $sourceHash = Get-FileHashSafe -Path $sourcePath
        $parse = Get-PowerShellParseResult -Path $sourcePath

        $BaselineRecords += [pscustomobject]@{
            SourcePath = $sourcePath
            SHA256 = $sourceHash
            ParserErrors = $parse.ErrorCount
            ParserErrorRecords = @($parse.Errors)
        }
    }

    $BaselineErrorCount = (
        @(
            $BaselineRecords |
            ForEach-Object { [int]$_.ParserErrors }
        ) |
        Measure-Object -Sum
    ).Sum

    Write-Info 'BASELINE FILES' $BaselineRecords.Count
    Write-Info 'PARSER ERRORS' $BaselineErrorCount

    # ========================================================================
    # 7
    # ========================================================================

    Write-Step '7/18' 'Clonage strict des sources...'

    foreach ($sourcePath in $SourceFiles) {

        $relative = $sourcePath.Substring(
            $ProjectRoot.Length
        ).TrimStart('\')

        $candidatePath = Join-Path `
            $CandidatesRoot `
            $relative

        $candidateDirectory = Split-Path `
            -Parent `
            $candidatePath

        if (-not (Test-Path -LiteralPath $candidateDirectory -PathType Container)) {
            New-Item `
                -ItemType Directory `
                -Path $candidateDirectory `
                -Force |
            Out-Null
        }

        Copy-Item `
            -LiteralPath $sourcePath `
            -Destination $candidatePath `
            -Force

        $CandidateRecords += [pscustomobject]@{
            SourcePath = $sourcePath
            CandidatePath = $candidatePath
        }
    }

    Write-Info 'CLONED' $CandidateRecords.Count

    # ========================================================================
    # 8
    # ========================================================================

    Write-Step '8/18' 'Revalidation parser des candidats clonés...'

    $candidateBaselineErrors = 0

    foreach ($candidate in $CandidateRecords) {

        $parse = Get-PowerShellParseResult `
            -Path $candidate.CandidatePath

        $candidateBaselineErrors += $parse.ErrorCount
    }

    Write-Info 'CANDIDATE BASELINE' $candidateBaselineErrors

    if ($candidateBaselineErrors -ne $BaselineErrorCount) {
        throw (
            'CLONE PARSER BASELINE MISMATCH. ORIGINAL=' +
            $BaselineErrorCount +
            ' CANDIDATE=' +
            $candidateBaselineErrors
        )
    }

    # ========================================================================
    # 9
    # ========================================================================

    Write-Step '9/18' 'Construction de la file des erreurs parser...'

    $ErrorQueue = New-Object System.Collections.Generic.List[object]

    foreach ($candidate in $CandidateRecords) {

        $parse = Get-PowerShellParseResult `
            -Path $candidate.CandidatePath

        foreach ($parseIssue in @($parse.Errors)) {

            $ErrorQueue.Add(
                [pscustomobject]@{
                    SourcePath = $candidate.SourcePath
                    CandidatePath = $candidate.CandidatePath
                    ErrorId = [string]$parseIssue.ErrorId
                    Message = [string]$parseIssue.Message
                    Line = [int]$parseIssue.Line
                    Column = [int]$parseIssue.Column
                    Text = [string]$parseIssue.Text
                }
            )
        }
    }

    Write-Info 'ERROR QUEUE' $ErrorQueue.Count

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

    Write-Info 'STRATEGIES' $Strategies.Count

    foreach ($strategyName in $Strategies) {
        Write-Host ('      - ' + $strategyName)
    }

    # ========================================================================
    # 11
    # ========================================================================

    Write-Step '11/18' 'Scan de toutes les stratégies sur tous les candidats...'

    $attemptIndex = 0

    foreach ($candidate in $CandidateRecords) {

        $originalContent = Read-TextSafe `
            -Path $candidate.CandidatePath

        foreach ($strategyName in $Strategies) {

            $attemptIndex++

            $trialPath = Join-Path `
                $EvidenceRoot `
                (
                    'trial_' +
                    $attemptIndex.ToString('D5') +
                    '_' +
                    $strategyName +
                    '.ps1'
                )

            $trialContent = Invoke-Strategy `
                -Strategy $strategyName `
                -Content $originalContent

            $changed = $trialContent -cne $originalContent

            if (-not $changed) {

                $AttemptRecords += [pscustomobject]@{
                    AttemptId = $attemptIndex
                    SourcePath = $candidate.SourcePath
                    Strategy = $strategyName
                    Changed = $false
                    OriginalErrors = 0
                    TrialErrors = 0
                    Improvement = 0
                    Status = 'NO_CHANGE'
                    TrialPath = $null
                }

                continue
            }

            Write-Candidate `
                -Path $trialPath `
                -Content $trialContent

            $originalParse = Get-PowerShellParseResult `
                -Path $candidate.CandidatePath

            $trialParse = Get-PowerShellParseResult `
                -Path $trialPath

            $improvement = (
                $originalParse.ErrorCount -
                $trialParse.ErrorCount
            )

            $status = 'REJECTED'

            if ($improvement -gt 0) {
                $status = 'IMPROVED'
            }
            elseif ($improvement -lt 0) {
                $status = 'REGRESSION'
            }

            $AttemptRecords += [pscustomobject]@{
                AttemptId = $attemptIndex
                SourcePath = $candidate.SourcePath
                Strategy = $strategyName
                Changed = $true
                OriginalErrors = $originalParse.ErrorCount
                TrialErrors = $trialParse.ErrorCount
                Improvement = $improvement
                Status = $status
                TrialPath = $trialPath
            }
        }
    }

    $AttemptCount = $AttemptRecords.Count

    Write-Info 'ATTEMPTS' $AttemptCount

    # ========================================================================
    # 12
    # ========================================================================

    Write-Step '12/18' 'Sélection stricte des améliorations...'

    $ImprovedRecords = @(
        $AttemptRecords |
        Where-Object {
            $_.Status -eq 'IMPROVED'
        }
    )

    $RegressionRecords = @(
        $AttemptRecords |
        Where-Object {
            $_.Status -eq 'REGRESSION'
        }
    )

    $RejectedRecords = @(
        $AttemptRecords |
        Where-Object {
            $_.Status -eq 'REJECTED'
        }
    )

    $ImprovedCount = $ImprovedRecords.Count
    $RegressionCount = $RegressionRecords.Count
    $RejectedCount = $RejectedRecords.Count

    # Strict acceptance:
    # only candidates with fewer parser errors are eligible.
    # No candidate is promoted into the source tree.

    $AcceptedRecords = @()

    foreach ($record in $ImprovedRecords) {

        $acceptedPath = Join-Path `
            $AcceptedRoot `
            (
                'candidate_' +
                $record.AttemptId.ToString('D5') +
                '_' +
                $record.Strategy +
                '.ps1'
            )

        Copy-Item `
            -LiteralPath $record.TrialPath `
            -Destination $acceptedPath `
            -Force

        $AcceptedRecords += [pscustomobject]@{
            AttemptId = $record.AttemptId
            SourcePath = $record.SourcePath
            Strategy = $record.Strategy
            OriginalErrors = $record.OriginalErrors
            CandidateErrors = $record.TrialErrors
            Improvement = $record.Improvement
            AcceptedPath = $acceptedPath
        }
    }

    $AcceptedCount = $AcceptedRecords.Count

    Write-Info 'IMPROVED' $ImprovedCount
    Write-Info 'ACCEPTED' $AcceptedCount
    Write-Info 'REJECTED' $RejectedCount
    Write-Info 'REGRESSIONS' $RegressionCount

    # ========================================================================
    # 13
    # ========================================================================

    Write-Step '13/18' 'Calcul du meilleur résultat candidat...'

    if ($AcceptedCount -gt 0) {

        $GlobalImprovement = (
            $AcceptedRecords |
            Measure-Object -Property Improvement -Maximum
        ).Maximum

        if ($null -eq $GlobalImprovement) {
            $GlobalImprovement = 0
        }

        $GlobalVerdict = 'IMPROVEMENT-DETECTED / PROMOTION-DISABLED'
    }
    else {

        $GlobalImprovement = 0
        $GlobalVerdict = 'NO-IMPROVEMENT / FAIL-CLOSED'
    }

    $FinalErrorCount = (
        $BaselineErrorCount -
        $GlobalImprovement
    )

    $ImprovementRatio = 0

    if ($BaselineErrorCount -gt 0) {
        $ImprovementRatio = [math]::Round(
            (
                $GlobalImprovement /
                [double]$BaselineErrorCount
            ) * 100,
            2
        )
    }

    Write-Info 'GLOBAL IMPROVEMENT' $GlobalImprovement
    Write-Info 'IMPROVEMENT RATIO' ($ImprovementRatio.ToString() + ' %')
    Write-Info 'VERDICT' $GlobalVerdict

    # ========================================================================
    # 14
    # ========================================================================

    Write-Step '14/18' 'Vérification cryptographique finale des sources...'

    $SourceMutationRecords = @()

    foreach ($baselineRecord in $BaselineRecords) {

        $currentHash = Get-FileHashSafe `
            -Path $baselineRecord.SourcePath

        $same = (
            $currentHash -eq $baselineRecord.SHA256
        )

        $SourceMutationRecords += [pscustomobject]@{
            Path = $baselineRecord.SourcePath
            BeforeSHA256 = $baselineRecord.SHA256
            AfterSHA256 = $currentHash
            Unchanged = $same
        }

        if (-not $same) {
            $SourceMutation = $true
        }
    }

    if ($SourceMutation) {
        throw 'SOURCE MUTATION DETECTED.'
    }

    Write-Info 'SOURCE MUTATIONS' 0
    Write-Info 'SOURCE INTEGRITY' 'PASS'

    # ========================================================================
    # 15
    # ========================================================================

    Write-Step '15/18' 'Revalidation indépendante des candidats acceptés...'

    $AcceptedValidation = @()

    foreach ($accepted in $AcceptedRecords) {

        $validation = Get-PowerShellParseResult `
            -Path $accepted.AcceptedPath

        $AcceptedValidation += [pscustomobject]@{
            AttemptId = $accepted.AttemptId
            Strategy = $accepted.Strategy
            Path = $accepted.AcceptedPath
            ParserErrors = $validation.ErrorCount
            Valid = (
                $validation.ErrorCount -lt
                $accepted.OriginalErrors
            )
        }
    }

    $InvalidAccepted = @(
        $AcceptedValidation |
        Where-Object {
            $_.Valid -eq $false
        }
    )

    if ($InvalidAccepted.Count -gt 0) {
        throw 'ACCEPTED CANDIDATE FAILED INDEPENDENT VALIDATION.'
    }

    Write-Info 'VALIDATED ACCEPTED' $AcceptedValidation.Count

    # ========================================================================
    # 16
    # ========================================================================

    Write-Step '16/18' 'Génération des preuves forensic...'

    $EvidencePath = Join-Path `
        $EvidenceRoot `
        'CANDIDATE_RESULTS.json'

    $EvidenceObject = [ordered]@{
        Engine = $EngineName
        Version = $ScriptVersion
        RunId = $RunId
        TimestampUtc = [DateTime]::UtcNow.ToString('o')
        BaselineParserErrors = $BaselineErrorCount
        AttemptCount = $AttemptCount
        ImprovedCount = $ImprovedCount
        AcceptedCount = $AcceptedCount
        RejectedCount = $RejectedCount
        RegressionCount = $RegressionCount
        Attempts = @($AttemptRecords)
        Accepted = @($AcceptedValidation)
    }

    $EvidenceObject |
        ConvertTo-Json -Depth 30 |
        Set-Content `
            -LiteralPath $EvidencePath `
            -Encoding utf8

    # ========================================================================
    # 17
    # ========================================================================

    Write-Step '17/18' 'Génération du manifeste forensic...'

    $ManifestPath = Join-Path `
        $Reports `
        'SUPER_FORENSIC_REPAIR_LAB_V5_MANIFEST.json'

    $Manifest = [ordered]@{
        Engine = $EngineName
        Version = $ScriptVersion
        RunId = $RunId
        TimestampUtc = [DateTime]::UtcNow.ToString('o')

        ProjectRoot = $ProjectRoot
        RepairDossier = $RepairDossier
        Workbench = $Workbench

        RootCauses = $RootCauseCount
        TargetFiles = $TargetFileCount

        BaselineParserErrors = $BaselineErrorCount
        FinalCandidateErrors = $FinalErrorCount

        GlobalImprovement = $GlobalImprovement
        ImprovementRatioPercent = $ImprovementRatio

        RepairAttempts = $AttemptCount
        ImprovedCandidates = $ImprovedCount
        AcceptedCandidates = $AcceptedCount
        RejectedCandidates = $RejectedCount
        RegressionCandidates = $RegressionCount

        SourceMutation = $SourceMutation
        ExecutionPerformed = $ExecutionPerformed
        PromotionPerformed = $PromotionPerformed

        Certified = $Certified
        CertifiedAuthorized = $CertifiedAuthorized

        Verdict = $GlobalVerdict
    }

    $Manifest |
        ConvertTo-Json -Depth 30 |
        Set-Content `
            -LiteralPath $ManifestPath `
            -Encoding utf8

    # ========================================================================
    # 18
    # ========================================================================

    Write-Step '18/18' 'Génération du rapport final...'

    $ReportPath = Join-Path `
        $Reports `
        'SUPER_FORENSIC_REPAIR_LAB_V5_REPORT.txt'

    $reportLines = @(
        '============================================================================'
        ' E-ZZIO — TRUTH SUPER FORENSIC REPAIR LAB v5.1.0'
        '============================================================================'
        ''
        ('RUN ID                  : ' + $RunId)
        ('PROJECT                 : ' + $ProjectRoot)
        ('REPAIR DOSSIER         : ' + $RepairDossier)
        ''
        ('ROOT CAUSES             : ' + $RootCauseCount)
        ('TARGET FILES            : ' + $TargetFileCount)
        ('BASELINE PARSER ERRORS : ' + $BaselineErrorCount)
        ('BEST CANDIDATE ERRORS  : ' + $FinalErrorCount)
        ('GLOBAL IMPROVEMENT     : ' + $GlobalImprovement)
        ('IMPROVEMENT RATIO      : ' + $ImprovementRatio + ' %')
        ''
        ('REPAIR ATTEMPTS        : ' + $AttemptCount)
        ('IMPROVED CANDIDATES    : ' + $ImprovedCount)
        ('ACCEPTED CANDIDATES    : ' + $AcceptedCount)
        ('REJECTED CANDIDATES    : ' + $RejectedCount)
        ('REGRESSIONS            : ' + $RegressionCount)
        ''
        ('SOURCE MUTATION        : ' + $SourceMutation)
        ('EXECUTION              : ' + $ExecutionPerformed)
        ('PROMOTION              : ' + $PromotionPerformed)
        ('CERTIFIED              : ' + $Certified)
        ('CERTIFIED AUTHORIZED   : ' + $CertifiedAuthorized)
        ''
        ('VERDICT                : ' + $GlobalVerdict)
        ''
        ('WORKBENCH              : ' + $Workbench)
        ('ACCEPTED CANDIDATES    : ' + $AcceptedRoot)
        ('EVIDENCE               : ' + $EvidencePath)
        ('REPORT                 : ' + $ReportPath)
        ('MANIFEST               : ' + $ManifestPath)
        ''
        'FAIL-CLOSED : les sources originales restent intactes.'
        'FAIL-CLOSED : aucun code candidat n''a été exécuté.'
        'FAIL-CLOSED : aucune promotion vers le projet réel n''a été effectuée.'
        'FAIL-CLOSED : CERTIFIED n''est jamais accordé par ce laboratoire.'
        '============================================================================'
    )

    Write-Utf8NoBom `
        -Path $ReportPath `
        -Content ($reportLines -join [Environment]::NewLine)

    # ========================================================================
    # FINAL
    # ========================================================================

    Write-Host ''
    Write-Host '============================================================================' -ForegroundColor Green
    Write-Host ' E-ZZIO — TRUTH SUPER FORENSIC REPAIR LAB v5.1.0 COMPLETE' -ForegroundColor Green
    Write-Host '============================================================================' -ForegroundColor Green

    Write-Info 'RUN ID' $RunId
    Write-Info 'ROOT CAUSES' $RootCauseCount
    Write-Info 'TARGET FILES' $TargetFileCount
    Write-Info 'PARSER BASELINE' $BaselineErrorCount
    Write-Info 'BEST CANDIDATE' $FinalErrorCount
    Write-Info 'GLOBAL IMPROVEMENT' $GlobalImprovement
    Write-Info 'ATTEMPTS' $AttemptCount
    Write-Info 'IMPROVED' $ImprovedCount
    Write-Info 'ACCEPTED' $AcceptedCount
    Write-Info 'REJECTED' $RejectedCount
    Write-Info 'REGRESSIONS' $RegressionCount

    Write-Host ''
    Write-Host 'SOURCE MUTATION         : 0' -ForegroundColor Green
    Write-Host 'EXECUTION              : DISABLED' -ForegroundColor Green
    Write-Host 'PROMOTION              : DISABLED' -ForegroundColor Green
    Write-Host 'CERTIFIED              : NOT AUTHORIZED' -ForegroundColor Yellow

    Write-Host ''
    Write-Info 'WORKBENCH' $Workbench
    Write-Info 'ACCEPTED CANDIDATES' $AcceptedRoot
    Write-Info 'EVIDENCE' $EvidencePath
    Write-Info 'REPORT' $ReportPath
    Write-Info 'MANIFEST' $ManifestPath

    Write-Host ''
    Write-Host ('VERDICT : ' + $GlobalVerdict) -ForegroundColor Cyan

    Write-Host ''
    Write-Host 'FAIL-CLOSED : les sources originales restent intactes.' -ForegroundColor Yellow
    Write-Host 'FAIL-CLOSED : aucun candidat n''est promu automatiquement.' -ForegroundColor Yellow
    Write-Host 'FAIL-CLOSED : aucun candidat n''est exécuté.' -ForegroundColor Yellow
    Write-Host '============================================================================' -ForegroundColor Green
    Write-Host ''

    Read-Host 'Appuie sur ENTREE pour terminer'

}
catch {

    Write-Host ''
    Write-Host '============================================================================' -ForegroundColor Red
    Write-Host ' E-ZZIO — TRUTH SUPER FORENSIC REPAIR LAB v5.1.0 FAILED / FAIL-CLOSED' -ForegroundColor Red
    Write-Host '============================================================================' -ForegroundColor Red
    Write-Host ''

    Write-Host ('ERROR : ' + $_.Exception.Message) -ForegroundColor Red

    if ($_.InvocationInfo) {
        Write-Host ''
        Write-Host ('LINE : ' + $_.InvocationInfo.ScriptLineNumber) -ForegroundColor DarkYellow
        Write-Host ('POSITION : ' + $_.InvocationInfo.OffsetInLine) -ForegroundColor DarkYellow
    }

    Write-Host ''
    Write-Host ('SOURCE MUTATION : ' + $SourceMutation)
    Write-Host ('EXECUTION       : ' + $ExecutionPerformed)
    Write-Host ('PROMOTION       : ' + $PromotionPerformed)
    Write-Host ''
    Write-Host 'Aucune promotion de candidat.' -ForegroundColor Yellow
    Write-Host 'Aucun CERTIFIED autorisé.' -ForegroundColor Yellow
    Write-Host 'Les sources originales restent intactes.' -ForegroundColor Yellow
    Write-Host '============================================================================' -ForegroundColor Red
    Write-Host ''

    Read-Host 'Appuie sur ENTREE pour terminer'
}