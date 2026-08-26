#requires -Version 7.4

<#
===============================================================================
 E-ZZIO — TRUTH SUPER FORENSIC REPAIR LAB v5.0.0
===============================================================================

PURPOSE
    Forensic candidate-repair laboratory for PowerShell parser failures.

DESIGN
    READ-ONLY SOURCE
    CANDIDATE-ONLY
    FAIL-CLOSED
    NO EXECUTION OF CANDIDATES
    NO AUTOMATIC PROMOTION
    NO AUTOMATIC SOURCE MUTATION
    DETERMINISTIC STRATEGY ISOLATION

IMPORTANT
    This engine NEVER modifies original project sources.

    A candidate is accepted only when:
        Candidate parser errors < Baseline parser errors
        AND no regression is introduced
        AND the candidate remains syntactically parseable as measured
        AND the original source hash remains unchanged.

    CERTIFIED is NEVER granted by this engine.

===============================================================================
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ============================================================================
# 0 — CONSTANTS
# ============================================================================

$EngineName   = 'E-ZZIO — TRUTH SUPER FORENSIC REPAIR LAB'
$ScriptVersion = '5.0.0'

$ProjectRoot = 'G:\AI\E-zzio'

$ReportsRoot = Join-Path $ProjectRoot '_EZZIO_TRUTH_REPORTS'

$SourceMutation       = $false
$ExecutionPerformed   = $false
$PromotionPerformed   = $false
$Certified            = $false
$CertifiedAuthorized  = $false

$RunId = (
    '{0}_{1}_{2}' -f
    (Get-Date).ToUniversalTime().ToString('yyyyMMdd_HHmmss_fff'),
    ([guid]::NewGuid().ToString('N').Substring(0,12))
)

$Workbench = Join-Path `
    $ReportsRoot `
    "${RunId}\SUPER_FORENSIC_REPAIR_LAB"

$CandidatesRoot = Join-Path $Workbench 'CANDIDATES'
$AcceptedRoot   = Join-Path $Workbench 'ACCEPTED_CANDIDATES'
$RejectedRoot   = Join-Path $Workbench 'REJECTED_CANDIDATES'
$EvidenceRoot   = Join-Path $Workbench 'EVIDENCE'
$ReportsDir     = Join-Path $Workbench 'REPORTS'
$LogsRoot       = Join-Path $Workbench 'LOGS'

$BaselineRoot   = Join-Path $Workbench 'BASELINE'

# ============================================================================
# 1 — BASIC FUNCTIONS
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
        [string]$Number,

        [Parameter(Mandatory)]
        [string]$Text
    )

    Write-Host ''
    Write-Host "[$Number] $Text" -ForegroundColor White
}

function Write-Info {
    param(
        [Parameter(Mandatory)]
        [string]$Name,

        [AllowEmptyString()]
        [string]$Value
    )

    Write-Host ('      {0,-28}: {1}' -f $Name, $Value)
}

function Ensure-Directory {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Container)) {
        [void](New-Item -ItemType Directory -Path $Path -Force)
    }
}

function Write-Utf8NoBom {
    param(
        [Parameter(Mandatory)]
        [string]$Path,

        [AllowEmptyString()]
        [string]$Content
    )

    $parent = Split-Path -Parent $Path

    if ($parent) {
        Ensure-Directory -Path $parent
    }

    $utf8 = [System.Text.UTF8Encoding]::new($false)

    [System.IO.File]::WriteAllText(
        $Path,
        $Content,
        $utf8
    )
}

function Read-TextSafe {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    return [System.IO.File]::ReadAllText(
        $Path,
        [System.Text.UTF8Encoding]::new($false)
    )
}

function Get-Sha256 {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    return (
        Get-FileHash `
            -LiteralPath $Path `
            -Algorithm SHA256
    ).Hash
}

function Get-RelativePathSafe {
    param(
        [Parameter(Mandatory)]
        [string]$Root,

        [Parameter(Mandatory)]
        [string]$Path
    )

    $rootFull = [System.IO.Path]::GetFullPath($Root)
    $pathFull = [System.IO.Path]::GetFullPath($Path)

    $relative = [System.IO.Path]::GetRelativePath(
        $rootFull,
        $pathFull
    )

    return $relative.Replace(
        [System.IO.Path]::DirectorySeparatorChar,
        '/'
    )
}

function Test-IsInsideRoot {
    param(
        [Parameter(Mandatory)]
        [string]$Root,

        [Parameter(Mandatory)]
        [string]$Path
    )

    $rootFull = (
        [System.IO.Path]::GetFullPath($Root)
    ).TrimEnd('\','/')

    $pathFull = (
        [System.IO.Path]::GetFullPath($Path)
    )

    return (
        $pathFull.StartsWith(
            $rootFull + [System.IO.Path]::DirectorySeparatorChar,
            [System.StringComparison]::OrdinalIgnoreCase
        )
    ) -or (
        $pathFull.Equals(
            $rootFull,
            [System.StringComparison]::OrdinalIgnoreCase
        )
    )
}

# ============================================================================
# 2 — POWERSHELL PARSER
# ============================================================================

function Get-PowerShellParseResult {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    $tokens = $null
    $parseErrors = $null

    try {
        $ast = [System.Management.Automation.Language.Parser]::ParseFile(
            $Path,
            [ref]$tokens,
            [ref]$parseErrors
        )

        $errorRecords = @()

        if ($null -ne $parseErrors) {
            foreach ($parseError in @($parseErrors)) {

                if ($null -eq $parseError) {
                    continue
                }

                $message = ''

                try {
                    $message = [string]$parseError.Message
                }
                catch {
                    $message = 'UNKNOWN_PARSER_ERROR'
                }

                $line = 0
                $column = 0

                try {
                    if ($null -ne $parseError.Extent) {
                        $line = [int]$parseError.Extent.StartLineNumber
                        $column = [int]$parseError.Extent.StartColumnNumber
                    }
                }
                catch {
                    $line = 0
                    $column = 0
                }

                $errorRecords += [pscustomobject]@{
                    Message = $message
                    Line    = $line
                    Column  = $column
                }
            }
        }

        return [pscustomobject]@{
            Path       = $Path
            ErrorCount = @($errorRecords).Count
            Errors     = @($errorRecords)
            Parsed     = (@($errorRecords).Count -eq 0)
            Exception  = $null
        }
    }
    catch {
        return [pscustomobject]@{
            Path       = $Path
            ErrorCount = 1
            Errors     = @(
                [pscustomobject]@{
                    Message = $_.Exception.Message
                    Line    = 0
                    Column  = 0
                }
            )
            Parsed     = $false
            Exception  = $_.Exception.Message
        }
    }
}

# ============================================================================
# 3 — LAST REPAIR DOSSIER DISCOVERY
# ============================================================================

function Find-LatestRepairDossier {
    param(
        [Parameter(Mandatory)]
        [string]$Root
    )

    if (-not (Test-Path -LiteralPath $Root -PathType Container)) {
        throw "Reports root absent: $Root"
    }

    $runs = @(
        Get-ChildItem `
            -LiteralPath $Root `
            -Directory `
            -ErrorAction Stop |
        Sort-Object LastWriteTimeUtc -Descending
    )

    foreach ($run in $runs) {

        $candidate = Join-Path `
            $run.FullName `
            'REPAIR_DOSSIER'

        if (Test-Path -LiteralPath $candidate -PathType Container) {

            $matrix = Join-Path `
                $candidate `
                'ROOT_CAUSE_MATRIX.json'

            if (Test-Path -LiteralPath $matrix -PathType Leaf) {
                return $candidate
            }
        }
    }

    throw 'Aucun REPAIR_DOSSIER valide contenant ROOT_CAUSE_MATRIX.json n''a été trouvé.'
}

# ============================================================================
# 4 — ROOT MATRIX LOADING
# ============================================================================

function Load-RootMatrix {
    param(
        [Parameter(Mandatory)]
        [string]$Dossier
    )

    $matrixPath = Join-Path `
        $Dossier `
        'ROOT_CAUSE_MATRIX.json'

    if (-not (Test-Path -LiteralPath $matrixPath -PathType Leaf)) {
        throw "ROOT_CAUSE_MATRIX.json absent: $matrixPath"
    }

    $raw = Read-TextSafe -Path $matrixPath

    if ([string]::IsNullOrWhiteSpace($raw)) {
        throw "ROOT_CAUSE_MATRIX.json est vide."
    }

    try {
        $data = $raw | ConvertFrom-Json -Depth 100
    }
    catch {
        throw "ROOT_CAUSE_MATRIX.json invalide: $($_.Exception.Message)"
    }

    $records = @()

    if ($data -is [System.Collections.IEnumerable] -and
        -not ($data -is [string])) {

        foreach ($item in @($data)) {
            if ($null -ne $item) {
                $records += $item
            }
        }
    }
    else {
        $records += $data
    }

    return [pscustomobject]@{
        Path    = $matrixPath
        Raw     = $data
        Records = @($records)
    }
}

# ============================================================================
# 5 — TARGET EXTRACTION
# ============================================================================

function Get-StringPropertiesRecursive {
    param(
        [Parameter(Mandatory)]
        [AllowNull()]
        [object]$Object,

        [int]$Depth = 0
    )

    if ($null -eq $Object) {
        return @()
    }

    if ($Depth -gt 12) {
        return @()
    }

    $results = @()

    if ($Object -is [string]) {
        if (-not [string]::IsNullOrWhiteSpace($Object)) {
            $results += $Object
        }

        return @($results)
    }

    if ($Object -is [System.Collections.IDictionary]) {

        foreach ($key in $Object.Keys) {
            $value = $Object[$key]

            $results += Get-StringPropertiesRecursive `
                -Object $value `
                -Depth ($Depth + 1)
        }

        return @($results)
    }

    if ($Object -is [System.Collections.IEnumerable] -and
        -not ($Object -is [string])) {

        foreach ($item in @($Object)) {
            $results += Get-StringPropertiesRecursive `
                -Object $item `
                -Depth ($Depth + 1)
        }

        return @($results)
    }

    try {
        foreach ($property in $Object.PSObject.Properties) {

            if ($null -eq $property) {
                continue
            }

            $value = $null

            try {
                $value = $property.Value
            }
            catch {
                continue
            }

            $results += Get-StringPropertiesRecursive `
                -Object $value `
                -Depth ($Depth + 1)
        }
    }
    catch {
        # Intentionally ignored:
        # forensic discovery must remain fail-closed.
    }

    return @($results)
}

function Resolve-TargetFiles {
    param(
        [Parameter(Mandatory)]
        [string]$ProjectRoot,

        [Parameter(Mandatory)]
        [object]$Matrix
    )

    $strings = @(
        Get-StringPropertiesRecursive `
            -Object $Matrix.Raw
    )

    $paths = New-Object `
        'System.Collections.Generic.HashSet[string]' `
        ([System.StringComparer]::OrdinalIgnoreCase)

    foreach ($candidateString in $strings) {

        if ([string]::IsNullOrWhiteSpace($candidateString)) {
            continue
        }

        $value = $candidateString.Trim()

        $possible = $null

        if ([System.IO.Path]::IsPathRooted($value)) {
            $possible = $value
        }
        elseif (
            $value -match '(?i)\.(ps1|psm1|psd1)$' -or
            $value -match '(?i)[\\/].+\.(ps1|psm1|psd1)$'
        ) {
            $possible = Join-Path $ProjectRoot $value
        }

        if ($null -eq $possible) {
            continue
        }

        try {
            $full = [System.IO.Path]::GetFullPath($possible)
        }
        catch {
            continue
        }

        if (-not (Test-IsInsideRoot `
                    -Root $ProjectRoot `
                    -Path $full)) {
            continue
        }

        if (-not (Test-Path -LiteralPath $full -PathType Leaf)) {
            continue
        }

        $extension = [System.IO.Path]::GetExtension($full)

        if ($extension -notin @('.ps1','.psm1','.psd1')) {
            continue
        }

        [void]$paths.Add($full)
    }

    return @(
        $paths |
        Sort-Object
    )
}

# ============================================================================
# 6 — SAFE TEXT TRANSFORM ENGINE
# ============================================================================

function Invoke-Strategy {
    param(
        [Parameter(Mandatory)]
        [string]$StrategyId,

        [Parameter(Mandatory)]
        [string]$Content
    )

    $changed = $false
    $result = $Content
    $description = ''

    switch ($StrategyId) {

        'SMART_QUOTES' {

            $before = $result

            $result = $result.Replace([char]0x2018, [char]0x27)
            $result = $result.Replace([char]0x2019, [char]0x27)
            $result = $result.Replace([char]0x201C, [char]0x22)
            $result = $result.Replace([char]0x201D, [char]0x22)

            $changed = ($result -cne $before)

            $description = 'Normalize typographic apostrophes and quotation marks.'
        }

        'UNICODE_DASHES' {

            $before = $result

            $result = $result.Replace([char]0x2010, [char]0x2D)
            $result = $result.Replace([char]0x2011, [char]0x2D)
            $result = $result.Replace([char]0x2012, [char]0x2D)
            $result = $result.Replace([char]0x2013, [char]0x2D)
            $result = $result.Replace([char]0x2014, [char]0x2D)
            $result = $result.Replace([char]0x2212, [char]0x2D)

            $changed = ($result -cne $before)

            $description = 'Normalize Unicode dash characters.'
        }

        'INVISIBLE_CHARS' {

            $before = $result

            $result = $result.Replace([char]0x200B, '')
            $result = $result.Replace([char]0x200C, '')
            $result = $result.Replace([char]0x200D, '')
            $result = $result.Replace([char]0xFEFF, '')
            $result = $result.Replace([char]0x2060, '')

            $changed = ($result -cne $before)

            $description = 'Remove known zero-width/invisible Unicode characters.'
        }

        'NUL_CHARS' {

            $before = $result

            $result = $result.Replace([char]0, '')

            $changed = ($result -cne $before)

            $description = 'Remove NUL characters.'
        }

        'MARKDOWN_FENCES' {

            $before = $result

            $lines = $result -split "`r?`n"

            $kept = New-Object `
                'System.Collections.Generic.List[string]'

            foreach ($line in $lines) {

                if ($line -match '^\s*```(?:powershell|pwsh|ps1)?\s*$') {
                    continue
                }

                $kept.Add($line)
            }

            $result = $kept -join [Environment]::NewLine

            $changed = ($result -cne $before)

            $description = 'Remove Markdown code-fence marker lines.'
        }

        'CONSOLE_PROMPTS' {

            $before = $result

            $lines = $result -split "`r?`n"

            $kept = New-Object `
                'System.Collections.Generic.List[string]'

            foreach ($line in $lines) {

                if (
                    $line -match '^\s*PS\s+[A-Za-z]:\\' -or
                    $line -match '^\s*>>\s*$'
                ) {
                    continue
                }

                $kept.Add($line)
            }

            $result = $kept -join [Environment]::NewLine

            $changed = ($result -cne $before)

            $description = 'Remove obvious captured PowerShell console prompt lines.'
        }

        'BACKTICK_WHITESPACE' {

            $before = $result

            $result = [regex]::Replace(
                $result,
                '(?m)`[ \t]+$',
                '`'
            )

            $changed = ($result -cne $before)

            $description = 'Normalize whitespace following PowerShell continuation backticks.'
        }

        'LINE_ENDINGS' {

            $before = $result

            $normalized = $result.Replace("`r`n", "`n")
            $normalized = $normalized.Replace("`r", "`n")
            $result = $normalized.Replace("`n", [Environment]::NewLine)

            $changed = ($result -cne $before)

            $description = 'Normalize line endings.'
        }

        'TRANSCRIPT_MARKERS' {

            $before = $result

            $lines = $result -split "`r?`n"

            $kept = New-Object `
                'System.Collections.Generic.List[string]'

            foreach ($line in $lines) {

                if (
                    $line -match '^\s*Appuie sur ENTREE' -or
                    $line -match '^\s*============================================================================\s*$' -and
                    $line -notmatch '(?i)E-ZZIO'
                ) {
                    continue
                }

                $kept.Add($line)
            }

            $result = $kept -join [Environment]::NewLine

            $changed = ($result -cne $before)

            $description = 'Remove obvious transcript-only terminal markers.'
        }

        default {
            throw "Unknown strategy: $StrategyId"
        }
    }

    return [pscustomobject]@{
        StrategyId = $StrategyId
        Changed    = $changed
        Content    = $result
        Description = $description
    }
}

# ============================================================================
# 7 — CANDIDATE WRITE
# ============================================================================

function Write-CandidateContent {
    param(
        [Parameter(Mandatory)]
        [string]$Path,

        [Parameter(Mandatory)]
        [string]$Content
    )

    Write-Utf8NoBom `
        -Path $Path `
        -Content $Content
}

# ============================================================================
# 8 — RESULT OBJECT
# ============================================================================

function New-ResultRecord {
    param(
        [string]$SourcePath,
        [string]$CandidatePath,
        [string]$StrategyId,
        [int]$BaselineErrors,
        [int]$CandidateErrors,
        [bool]$Changed,
        [string]$Verdict,
        [string]$Reason,
        [string]$BaselineHash,
        [string]$CandidateHash
    )

    return [pscustomobject]@{
        SourcePath       = $SourcePath
        CandidatePath    = $CandidatePath
        RelativePath     = ''
        StrategyId       = $StrategyId
        BaselineErrors   = $BaselineErrors
        CandidateErrors  = $CandidateErrors
        Improvement      = $BaselineErrors - $CandidateErrors
        Changed          = $Changed
        Verdict          = $Verdict
        Reason           = $Reason
        BaselineHash     = $BaselineHash
        CandidateHash    = $CandidateHash
        TimestampUtc     = [DateTime]::UtcNow.ToString('o')
    }
}

# ============================================================================
# 9 — MAIN
# ============================================================================

try {

    Write-Banner "$EngineName v$ScriptVersion"

    Write-Info 'PROJECT' $ProjectRoot
    Write-Info 'MODE' 'READ-ONLY / CANDIDATE-ONLY / FAIL-CLOSED'
    Write-Info 'QUALITY' 'FORENSIC / DETERMINISTIC / CERTIFICATION-GRADE'
    Write-Info 'SOURCE MUTATION' 'DISABLED'
    Write-Info 'EXECUTION' 'DISABLED'
    Write-Info 'PROMOTION' 'DISABLED'

    # ------------------------------------------------------------------------
    # [1] ENVIRONMENT
    # ------------------------------------------------------------------------

    Write-Step '1/18' 'Validation environnement...'

    if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) {
        throw "Projet introuvable: $ProjectRoot"
    }

    if ($PSVersionTable.PSVersion.Major -lt 7) {
        throw 'PowerShell 7+ requis.'
    }

    Write-Info 'POWERSHELL' $PSVersionTable.PSVersion.ToString()
    Write-Info 'ENVIRONMENT' 'PASS'

    # ------------------------------------------------------------------------
    # [2] DOSSIER
    # ------------------------------------------------------------------------

    Write-Step '2/18' 'Recherche du dernier REPAIR_DOSSIER...'

    $RepairDossier = Find-LatestRepairDossier `
        -Root $ReportsRoot

    Write-Info 'DOSSIER' $RepairDossier
    Write-Info 'DISCOVERY' 'PASS'

    # ------------------------------------------------------------------------
    # [3] MATRIX
    # ------------------------------------------------------------------------

    Write-Step '3/18' 'Chargement de la Root-Cause Matrix...'

    $Matrix = Load-RootMatrix `
        -Dossier $RepairDossier

    $RootCauseCount = @($Matrix.Records).Count

    Write-Info 'ROOT CAUSES' $RootCauseCount

    if ($RootCauseCount -eq 0) {
        throw 'Root-Cause Matrix vide.'
    }

    # ------------------------------------------------------------------------
    # [4] TARGET FILES
    # ------------------------------------------------------------------------

    Write-Step '4/18' 'Identification forensic des fichiers cibles...'

    $TargetFiles = @(
        Resolve-TargetFiles `
            -ProjectRoot $ProjectRoot `
            -Matrix $Matrix
    )

    Write-Info 'TARGET FILES' $TargetFiles.Count

    if ($TargetFiles.Count -eq 0) {
        throw 'Aucun fichier PowerShell cible identifiable dans la Root-Cause Matrix.'
    }

    # ------------------------------------------------------------------------
    # [5] WORKBENCH
    # ------------------------------------------------------------------------

    Write-Step '5/18' 'Création du laboratoire forensic...'

    foreach ($directory in @(
        $Workbench,
        $CandidatesRoot,
        $AcceptedRoot,
        $RejectedRoot,
        $EvidenceRoot,
        $ReportsDir,
        $LogsRoot,
        $BaselineRoot
    )) {
        Ensure-Directory -Path $directory
    }

    Write-Info 'RUN ID' $RunId
    Write-Info 'WORKBENCH' $Workbench
    Write-Info 'WORKBENCH' 'PASS'

    # ------------------------------------------------------------------------
    # [6] BASELINE
    # ------------------------------------------------------------------------

    Write-Step '6/18' 'Construction du baseline SHA-256 + parser original...'

    $BaselineRecords = New-Object `
        'System.Collections.Generic.List[object]'

    $TotalBaselineErrors = 0

    foreach ($sourcePath in $TargetFiles) {

        $hash = Get-Sha256 -Path $sourcePath

        $parse = Get-PowerShellParseResult `
            -Path $sourcePath

        $relative = Get-RelativePathSafe `
            -Root $ProjectRoot `
            -Path $sourcePath

        $BaselineRecords.Add(
            [pscustomobject]@{
                SourcePath       = $sourcePath
                RelativePath     = $relative
                Hash              = $hash
                ParserErrors      = $parse.ErrorCount
                ParserResult      = $parse
            }
        )

        $TotalBaselineErrors += $parse.ErrorCount
    }

    Write-Info 'BASELINE FILES' $BaselineRecords.Count
    Write-Info 'PARSER ERRORS' $TotalBaselineErrors

    $baselineJson = Join-Path `
        $EvidenceRoot `
        'ORIGINAL_BASELINE.json'

    $BaselineRecords |
        ForEach-Object {
            [pscustomobject]@{
                SourcePath   = $_.SourcePath
                RelativePath = $_.RelativePath
                SHA256       = $_.Hash
                ParserErrors = $_.ParserErrors
                Errors       = @($_.ParserResult.Errors)
            }
        } |
        ConvertTo-Json -Depth 20 |
        Set-Content `
            -LiteralPath $baselineJson `
            -Encoding utf8

    # ------------------------------------------------------------------------
    # [7] CLONING
    # ------------------------------------------------------------------------

    Write-Step '7/18' 'Clonage strict des sources...'

    $CloneRecords = New-Object `
        'System.Collections.Generic.List[object]'

    foreach ($baseline in @($BaselineRecords)) {

        $candidatePath = Join-Path `
            $CandidatesRoot `
            $baseline.RelativePath

        $candidateParent = Split-Path `
            -Parent `
            $candidatePath

        Ensure-Directory `
            -Path $candidateParent

        Copy-Item `
            -LiteralPath $baseline.SourcePath `
            -Destination $candidatePath `
            -Force

        $candidateHash = Get-Sha256 `
            -Path $candidatePath

        if ($candidateHash -ne $baseline.Hash) {
            throw "Clone SHA-256 mismatch: $($baseline.SourcePath)"
        }

        $CloneRecords.Add(
            [pscustomobject]@{
                SourcePath    = $baseline.SourcePath
                RelativePath  = $baseline.RelativePath
                CandidatePath = $candidatePath
                BaselineHash  = $baseline.Hash
            }
        )
    }

    Write-Info 'CLONED' $CloneRecords.Count

    # ------------------------------------------------------------------------
    # [8] STRATEGIES
    # ------------------------------------------------------------------------

    Write-Step '8/18' 'Chargement des stratégies de réparation...'

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

    foreach ($strategy in $Strategies) {
        Write-Host "      - $strategy"
    }

    # ------------------------------------------------------------------------
    # [9] FORENSIC SCAN
    # ------------------------------------------------------------------------

    Write-Step '9/18' 'Scan isolé de toutes les stratégies sur tous les candidats...'

    $AllResults = New-Object `
        'System.Collections.Generic.List[object]'

    $AttemptCount = 0
    $ChangedCount = 0
    $ImprovedCount = 0
    $AcceptedCount = 0
    $RejectedCount = 0
    $RegressionCount = 0
    $NoChangeCount = 0

    foreach ($clone in @($CloneRecords)) {

        $sourceContent = Read-TextSafe `
            -Path $clone.CandidatePath

        $baselineParse = Get-PowerShellParseResult `
            -Path $clone.CandidatePath

        foreach ($strategy in $Strategies) {

            $AttemptCount++

            $trial = Invoke-Strategy `
                -StrategyId $strategy `
                -Content $sourceContent

            if (-not $trial.Changed) {

                $NoChangeCount++

                $record = New-ResultRecord `
                    -SourcePath $clone.SourcePath `
                    -CandidatePath '' `
                    -StrategyId $strategy `
                    -BaselineErrors $baselineParse.ErrorCount `
                    -CandidateErrors $baselineParse.ErrorCount `
                    -Changed $false `
                    -Verdict 'NO_CHANGE' `
                    -Reason 'Strategy produced byte-equivalent semantic text.' `
                    -BaselineHash $clone.BaselineHash `
                    -CandidateHash $clone.BaselineHash

                $record.RelativePath = $clone.RelativePath

                $AllResults.Add($record)

                continue
            }

            $ChangedCount++

            $strategySafeName = (
                $strategy -replace '[^A-Za-z0-9_.-]', '_'
            )

            $relativeName = (
                $clone.RelativePath `
                -replace '[\\/]', '__' `
                -replace '[^A-Za-z0-9_.-]', '_'
            )

            $trialDir = Join-Path `
                $Workbench `
                'TRIALS'

            Ensure-Directory -Path $trialDir

            $trialName = '{0}__{1}__{2}' -f `
                $strategySafeName,
                $relativeName,
                $AttemptCount

            $trialPath = Join-Path `
                $trialDir `
                ($trialName + '.ps1')

            Write-CandidateContent `
                -Path $trialPath `
                -Content $trial.Content

            $candidateParse = Get-PowerShellParseResult `
                -Path $trialPath

            $candidateHash = Get-Sha256 `
                -Path $trialPath

            $improvement = (
                $baselineParse.ErrorCount -
                $candidateParse.ErrorCount
            )

            $verdict = 'REJECTED'
            $reason = ''

            if (-not $trial.Changed) {

                $verdict = 'NO_CHANGE'
                $reason = 'No textual change.'
            }
            elseif ($candidateParse.ErrorCount -lt $baselineParse.ErrorCount) {

                $verdict = 'IMPROVED'
                $reason = 'Parser error count strictly decreased.'

                $ImprovedCount++
            }
            elseif ($candidateParse.ErrorCount -gt $baselineParse.ErrorCount) {

                $verdict = 'REGRESSION'
                $reason = 'Parser error count increased.'

                $RegressionCount++
            }
            else {

                $verdict = 'REJECTED'
                $reason = 'No parser improvement.'
            }

            $record = New-ResultRecord `
                -SourcePath $clone.SourcePath `
                -CandidatePath $trialPath `
                -StrategyId $strategy `
                -BaselineErrors $baselineParse.ErrorCount `
                -CandidateErrors $candidateParse.ErrorCount `
                -Changed $true `
                -Verdict $verdict `
                -Reason $reason `
                -BaselineHash $clone.BaselineHash `
                -CandidateHash $candidateHash

            $record.RelativePath = $clone.RelativePath

            $AllResults.Add($record)
        }
    }

    Write-Info 'ATTEMPTS' $AttemptCount
    Write-Info 'CHANGED TRIALS' $ChangedCount
    Write-Info 'IMPROVED TRIALS' $ImprovedCount
    Write-Info 'REGRESSIONS' $RegressionCount

    # ------------------------------------------------------------------------
    # [10] SELECT BEST CANDIDATE PER SOURCE
    # ------------------------------------------------------------------------

    Write-Step '10/18' 'Sélection déterministe du meilleur candidat par fichier...'

    $Selected = New-Object `
        'System.Collections.Generic.List[object]'

    $grouped = @(
        $AllResults |
        Where-Object {
            $_.Verdict -eq 'IMPROVED' -and
            -not [string]::IsNullOrWhiteSpace($_.CandidatePath)
        } |
        Group-Object SourcePath
    )

    foreach ($group in $grouped) {

        $best = @(
            $group.Group |
            Sort-Object `
                @{Expression='Improvement';Descending=$true},
                @{Expression='CandidateErrors';Ascending=$true},
                @{Expression='StrategyId';Ascending=$true}
        ) |
        Select-Object -First 1

        if ($null -ne $best) {
            $Selected.Add($best)
        }
    }

    # ------------------------------------------------------------------------
    # [11] CANDIDATE ACCEPTANCE
    # ------------------------------------------------------------------------

    Write-Step '11/18' 'Validation stricte des candidats améliorés...'

    $Accepted = New-Object `
        'System.Collections.Generic.List[object]'

    foreach ($candidate in @($Selected)) {

        if (-not (Test-Path `
                -LiteralPath $candidate.CandidatePath `
                -PathType Leaf)) {
            continue
        }

        $finalParse = Get-PowerShellParseResult `
            -Path $candidate.CandidatePath

        $sourceHashAfter = Get-Sha256 `
            -Path $candidate.SourcePath

        if ($sourceHashAfter -ne $candidate.BaselineHash) {
            throw "SOURCE MUTATION DETECTED: $($candidate.SourcePath)"
        }

        if ($finalParse.ErrorCount -ge $candidate.BaselineErrors) {
            continue
        }

        $acceptedPath = Join-Path `
            $AcceptedRoot `
            $candidate.RelativePath

        Ensure-Directory `
            -Path (Split-Path -Parent $acceptedPath)

        Copy-Item `
            -LiteralPath $candidate.CandidatePath `
            -Destination $acceptedPath `
            -Force

        $acceptedHash = Get-Sha256 `
            -Path $acceptedPath

        if ($acceptedHash -ne $candidate.CandidateHash) {
            throw "Accepted candidate hash mismatch: $acceptedPath"
        }

        $Accepted.Add(
            [pscustomobject]@{
                SourcePath       = $candidate.SourcePath
                RelativePath     = $candidate.RelativePath
                StrategyId       = $candidate.StrategyId
                CandidatePath    = $acceptedPath
                BaselineErrors   = $candidate.BaselineErrors
                FinalErrors      = $finalParse.ErrorCount
                Improvement      = (
                    $candidate.BaselineErrors -
                    $finalParse.ErrorCount
                )
                BaselineHash     = $candidate.BaselineHash
                CandidateHash    = $acceptedHash
            }
        )
    }

    $AcceptedCount = $Accepted.Count

    $RejectedCount = @(
        $AllResults |
        Where-Object {
            $_.Verdict -in @(
                'REJECTED',
                'REGRESSION',
                'NO_CHANGE'
            )
        }
    ).Count

    Write-Info 'IMPROVED' $ImprovedCount
    Write-Info 'ACCEPTED' $AcceptedCount
    Write-Info 'REJECTED' $RejectedCount
    Write-Info 'REGRESSIONS' $RegressionCount

    # ------------------------------------------------------------------------
    # [12] SOURCE INTEGRITY
    # ------------------------------------------------------------------------

    Write-Step '12/18' 'Vérification SHA-256 finale des sources originales...'

    $SourceMutations = New-Object `
        'System.Collections.Generic.List[object]'

    foreach ($baseline in @($BaselineRecords)) {

        $afterHash = Get-Sha256 `
            -Path $baseline.SourcePath

        if ($afterHash -ne $baseline.Hash) {

            $SourceMutations.Add(
                [pscustomobject]@{
                    Path   = $baseline.SourcePath
                    Before = $baseline.Hash
                    After  = $afterHash
                }
            )
        }
    }

    if ($SourceMutations.Count -gt 0) {
        $SourceMutation = $true

        throw 'SOURCE MUTATION DETECTED — FAIL-CLOSED.'
    }

    Write-Info 'SOURCE MUTATIONS' 0
    Write-Info 'SOURCE INTEGRITY' 'PASS'

    # ------------------------------------------------------------------------
    # [13] GLOBAL VERDICT
    # ------------------------------------------------------------------------

    Write-Step '13/18' 'Calcul du verdict global...'

    $GlobalImprovement = (
        @($Accepted) |
        Measure-Object -Property Improvement -Sum
    ).Sum

    if ($null -eq $GlobalImprovement) {
        $GlobalImprovement = 0
    }

    $FinalParserErrors = (
        $TotalBaselineErrors -
        [int]$GlobalImprovement
    )

    if ($TotalBaselineErrors -gt 0) {

        $ImprovementRatio = [math]::Round(
            (
                [double]$GlobalImprovement /
                [double]$TotalBaselineErrors
            ) * 100,
            2
        )
    }
    else {
        $ImprovementRatio = 0
    }

    if ($AcceptedCount -gt 0) {
        $GlobalVerdict = 'IMPROVEMENT-CANDIDATES-AVAILABLE / FAIL-CLOSED'
    }
    else {
        $GlobalVerdict = 'NO-IMPROVEMENT / FAIL-CLOSED'
    }

    Write-Info 'GLOBAL IMPROVEMENT' $GlobalImprovement
    Write-Info 'IMPROVEMENT RATIO' "$ImprovementRatio %"
    Write-Info 'VERDICT' $GlobalVerdict

    # ------------------------------------------------------------------------
    # [14] EVIDENCE
    # ------------------------------------------------------------------------

    Write-Step '14/18' 'Écriture des preuves forensic...'

    $resultsPath = Join-Path `
        $EvidenceRoot `
        'CANDIDATE_RESULTS.json'

    $AllResults |
        ConvertTo-Json -Depth 30 |
        Set-Content `
            -LiteralPath $resultsPath `
            -Encoding utf8

    $acceptedPath = Join-Path `
        $EvidenceRoot `
        'ACCEPTED_CANDIDATES.json'

    $Accepted |
        ConvertTo-Json -Depth 30 |
        Set-Content `
            -LiteralPath $acceptedPath `
            -Encoding utf8

    $sourceIntegrityPath = Join-Path `
        $EvidenceRoot `
        'SOURCE_INTEGRITY.json'

    @(
        foreach ($baseline in @($BaselineRecords)) {

            [pscustomobject]@{
                Path   = $baseline.SourcePath
                Before = $baseline.Hash
                After  = Get-Sha256 -Path $baseline.SourcePath
                Equal  = (
                    $baseline.Hash -eq
                    (Get-Sha256 -Path $baseline.SourcePath)
                )
            }
        }
    ) |
    ConvertTo-Json -Depth 20 |
    Set-Content `
        -LiteralPath $sourceIntegrityPath `
        -Encoding utf8

    # ------------------------------------------------------------------------
    # [15] MANIFEST
    # ------------------------------------------------------------------------

    Write-Step '15/18' 'Génération du manifeste forensic...'

    $Manifest = [ordered]@{
        Engine                = $EngineName
        Version               = $ScriptVersion
        RunId                 = $RunId
        TimestampUtc          = [DateTime]::UtcNow.ToString('o')

        ProjectRoot           = $ProjectRoot
        RepairDossier         = $RepairDossier
        Workbench             = $Workbench

        RootCauses            = $RootCauseCount
        TargetFiles           = $TargetFiles.Count

        BaselineParserErrors  = $TotalBaselineErrors
        FinalCandidateErrors  = $FinalParserErrors

        RepairAttempts        = $AttemptCount
        ChangedTrials         = $ChangedCount
        ImprovedTrials        = $ImprovedCount
        AcceptedCandidates    = $AcceptedCount
        RejectedCandidates    = $RejectedCount
        RegressionCandidates  = $RegressionCount
        NoChangeTrials        = $NoChangeCount

        GlobalImprovement     = $GlobalImprovement
        ImprovementRatio      = $ImprovementRatio

        SourceMutation        = $SourceMutation
        ExecutionPerformed    = $ExecutionPerformed
        PromotionPerformed    = $PromotionPerformed

        Certified             = $Certified
        CertifiedAuthorized   = $CertifiedAuthorized

        Verdict               = $GlobalVerdict

        Strategies            = $Strategies

        SecurityModel         = [ordered]@{
            OriginalSourcesWritableByEngine = $false
            CandidateExecution             = $false
            AutomaticPromotion             = $false
            CertifiedByRepairEngine        = $false
        }
    }

    $ManifestPath = Join-Path `
        $ReportsDir `
        'SUPER_FORENSIC_REPAIR_V5_MANIFEST.json'

    $Manifest |
        ConvertTo-Json -Depth 50 |
        Set-Content `
            -LiteralPath $ManifestPath `
            -Encoding utf8

    # ------------------------------------------------------------------------
    # [16] REPORT
    # ------------------------------------------------------------------------

    Write-Step '16/18' 'Génération du rapport final...'

    $ReportPath = Join-Path `
        $ReportsDir `
        'SUPER_FORENSIC_REPAIR_V5_REPORT.txt'

    $reportLines = @(
        '============================================================================'
        ' E-ZZIO — TRUTH SUPER FORENSIC REPAIR LAB v5.0.0'
        '============================================================================'
        ''
        "RUN ID                  : $RunId"
        "PROJECT                 : $ProjectRoot"
        "REPAIR DOSSIER         : $RepairDossier"
        "WORKBENCH              : $Workbench"
        ''
        "ROOT CAUSES             : $RootCauseCount"
        "TARGET FILES            : $($TargetFiles.Count)"
        "BASELINE PARSER ERRORS : $TotalBaselineErrors"
        "FINAL CANDIDATE ERRORS : $FinalParserErrors"
        "GLOBAL IMPROVEMENT     : $GlobalImprovement"
        "IMPROVEMENT RATIO      : $ImprovementRatio %"
        ''
        "REPAIR ATTEMPTS        : $AttemptCount"
        "CHANGED TRIALS         : $ChangedCount"
        "IMPROVED TRIALS       : $ImprovedCount"
        "ACCEPTED CANDIDATES    : $AcceptedCount"
        "REJECTED CANDIDATES    : $RejectedCount"
        "REGRESSIONS            : $RegressionCount"
        "NO CHANGE              : $NoChangeCount"
        ''
        "SOURCE MUTATION        : $SourceMutation"
        "EXECUTION             : $ExecutionPerformed"
        "PROMOTION             : $PromotionPerformed"
        "CERTIFIED             : $Certified"
        "CERTIFIED AUTHORIZED  : $CertifiedAuthorized"
        ''
        "VERDICT                : $GlobalVerdict"
        ''
        "ACCEPTED ROOT          : $AcceptedRoot"
        "EVIDENCE               : $EvidenceRoot"
        "REPORT                 : $ReportPath"
        "MANIFEST               : $ManifestPath"
        ''
        'FAIL-CLOSED : aucune source originale n''a été modifiée.'
        'FAIL-CLOSED : aucun code candidat n''a été exécuté.'
        'FAIL-CLOSED : aucun candidat n''a été promu automatiquement.'
        'FAIL-CLOSED : CERTIFIED n''est jamais accordé par ce moteur.'
        '============================================================================'
    )

    Write-Utf8NoBom `
        -Path $ReportPath `
        -Content ($reportLines -join [Environment]::NewLine)

    # ------------------------------------------------------------------------
    # [17] FINAL FORENSIC GATE
    # ------------------------------------------------------------------------

    Write-Step '17/18' 'Gates finales forensic...'

    if ($SourceMutation) {
        throw 'Final gate failure: source mutation.'
    }

    if ($ExecutionPerformed) {
        throw 'Final gate failure: execution occurred.'
    }

    if ($PromotionPerformed) {
        throw 'Final gate failure: promotion occurred.'
    }

    if ($Certified -or $CertifiedAuthorized) {
        throw 'Final gate failure: unauthorized certification state.'
    }

    foreach ($baseline in @($BaselineRecords)) {

        $currentHash = Get-Sha256 `
            -Path $baseline.SourcePath

        if ($currentHash -ne $baseline.Hash) {
            throw "Final SHA-256 mismatch: $($baseline.SourcePath)"
        }
    }

    Write-Info 'SOURCE INTEGRITY' 'PASS'
    Write-Info 'EXECUTION GATE' 'PASS'
    Write-Info 'PROMOTION GATE' 'PASS'
    Write-Info 'CERTIFICATION GATE' 'PASS'

    # ------------------------------------------------------------------------
    # [18] COMPLETE
    # ------------------------------------------------------------------------

    Write-Step '18/18' 'Finalisation...'

    Write-Host ''
    Write-Host '============================================================================' -ForegroundColor Green
    Write-Host ' E-ZZIO — TRUTH SUPER FORENSIC REPAIR LAB v5.0.0 COMPLETE' -ForegroundColor Green
    Write-Host '============================================================================' -ForegroundColor Green

    Write-Info 'RUN ID' $RunId
    Write-Info 'ROOT CAUSES' $RootCauseCount
    Write-Info 'TARGET FILES' $TargetFiles.Count
    Write-Info 'PARSER BASELINE' $TotalBaselineErrors
    Write-Info 'PARSER FINAL' $FinalParserErrors
    Write-Info 'GLOBAL IMPROVEMENT' $GlobalImprovement
    Write-Info 'IMPROVEMENT RATIO' "$ImprovementRatio %"
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
    Write-Info 'EVIDENCE' $EvidenceRoot
    Write-Info 'REPORT' $ReportPath
    Write-Info 'MANIFEST' $ManifestPath

    Write-Host ''
    Write-Host "VERDICT : $GlobalVerdict" -ForegroundColor Cyan

    Write-Host ''
    Write-Host 'FAIL-CLOSED : les sources originales restent intactes.' -ForegroundColor Yellow
    Write-Host 'FAIL-CLOSED : aucun code candidat n''a été exécuté.' -ForegroundColor Yellow
    Write-Host 'FAIL-CLOSED : aucun candidat n''a été promu automatiquement.' -ForegroundColor Yellow
    Write-Host '============================================================================' -ForegroundColor Green
    Write-Host ''

    Read-Host 'Appuie sur ENTREE pour terminer'
}
catch {

    $failureMessage = $_.Exception.Message

    Write-Host ''
    Write-Host '============================================================================' -ForegroundColor Red
    Write-Host ' E-ZZIO — TRUTH SUPER FORENSIC REPAIR LAB v5.0.0 FAILED / FAIL-CLOSED' -ForegroundColor Red
    Write-Host '============================================================================' -ForegroundColor Red
    Write-Host ''

    Write-Host "ERROR : $failureMessage" -ForegroundColor Red
    Write-Host ''

    Write-Host "SOURCE MUTATION : $SourceMutation"
    Write-Host "EXECUTION       : $ExecutionPerformed"
    Write-Host "PROMOTION       : $PromotionPerformed"
    Write-Host "CERTIFIED       : $Certified"
    Write-Host ''

    Write-Host 'Aucune promotion de candidat.' -ForegroundColor Yellow
    Write-Host 'Aucun CERTIFIED autorisé.' -ForegroundColor Yellow
    Write-Host 'Les sources originales restent intactes.' -ForegroundColor Yellow
    Write-Host ''

    Write-Host '============================================================================' -ForegroundColor Red
    Write-Host ''

    Read-Host 'Appuie sur ENTREE pour terminer'
}