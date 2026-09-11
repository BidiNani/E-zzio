#requires -Version 7.0
<#
===============================================================================
 E-ZZIO — TRUTH SUPER REPAIR ENGINE v3.0.1
===============================================================================

PURPOSE
-------
Forensic candidate-only repair engine.

SECURITY MODEL
--------------
READ-ONLY SOURCE
CANDIDATE-ONLY
FAIL-CLOSED
NO SOURCE MUTATION
NO EXECUTION OF PROJECT CODE
NO AUTOMATIC PROMOTION
NO CERTIFICATION

IMPORTANT
---------
This engine may create candidate copies under _EZZIO_TRUTH_REPORTS only.

The original project source tree is never written by this engine.

v3.0.1 HARDENING
-----------------
- No chained .Replace() expressions
- No use of reserved/read-only variable $Error
- Empty-string-safe helper parameters
- Strict deterministic parser collection
- Explicit candidate/source hash comparison
- Candidate parser validation before acceptance
- Candidate rejection on regression
- Candidate rejection when parser errors are unchanged
- Candidate acceptance only when parser errors strictly decrease
- No automatic promotion
===============================================================================
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ============================================================================
# CONFIGURATION
# ============================================================================

$EngineName   = 'E-ZZIO — TRUTH SUPER REPAIR ENGINE'
$ScriptVersion = '3.0.1'

$ProjectRoot = 'G:\AI\E-zzio'

$ReportsRoot = Join-Path $ProjectRoot '_EZZIO_TRUTH_REPORTS'

$SourceMutation      = $false
$ExecutionPerformed  = $false
$PromotionPerformed  = $false
$Certified           = $false
$CertifiedAuthorized = $false

$RunId = '{0}_{1}' -f `
    (Get-Date).ToUniversalTime().ToString('yyyyMMdd_HHmmss_fff'), `
    ([Guid]::NewGuid().ToString('N').Substring(0,12))

$RunRoot   = Join-Path $ReportsRoot $RunId
$Workbench = Join-Path $RunRoot 'SUPER_REPAIR_WORKBENCH'

$CandidatesRoot = Join-Path $Workbench 'CANDIDATES'
$AcceptedRoot   = Join-Path $Workbench 'ACCEPTED_CANDIDATES'
$RejectedRoot   = Join-Path $Workbench 'REJECTED_CANDIDATES'
$AmbiguousRoot  = Join-Path $Workbench 'AMBIGUOUS_CANDIDATES'
$Reports        = Join-Path $Workbench 'REPORTS'
$EvidenceRoot   = Join-Path $Workbench 'EVIDENCE'

# ============================================================================
# OUTPUT HELPERS
# ============================================================================

function Write-Banner {
    param(
        [Parameter(Mandatory)]
        [string]$Title
    )

    Write-Host ''
    Write-Host '============================================================================' -ForegroundColor DarkCyan
    Write-Host " $Title" -ForegroundColor Cyan
    Write-Host '============================================================================' -ForegroundColor DarkCyan
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
        [string]$Label,

        [AllowNull()]
        [AllowEmptyString()]
        [object]$Value
    )

    $padding = 28
    $labelText = $Label.PadRight($padding)
    Write-Host ("      {0}: {1}" -f $labelText, $Value)
}

function Write-Status {
    param(
        [Parameter(Mandatory)]
        [string]$Label,

        [Parameter(Mandatory)]
        [string]$Value,

        [ConsoleColor]$Color = [ConsoleColor]::Green
    )

    Write-Host ("      {0,-28}: {1}" -f $Label,$Value) -ForegroundColor $Color
}

# ============================================================================
# SAFE TEXT HELPERS
# ============================================================================

function Normalize-Text {
    param(
        [AllowNull()]
        [AllowEmptyString()]
        [string]$Text
    )

    if ($null -eq $Text) {
        return ''
    }

    $result = [string]$Text

    # IMPORTANT:
    # Deliberately use sequential assignments.
    # No chained .Replace() calls.
    $result = $result.Replace([char]0x2018, [char]0x27)
    $result = $result.Replace([char]0x2019, [char]0x27)
    $result = $result.Replace([char]0x201C, [char]0x22)
    $result = $result.Replace([char]0x201D, [char]0x22)
    $result = $result.Replace([char]0x2013, [char]0x2D)
    $result = $result.Replace([char]0x2014, [char]0x2D)
    $result = $result.Replace([char]0x00A0, [char]0x20)

    return $result
}

function Write-Utf8NoBom {
    param(
        [Parameter(Mandatory)]
        [string]$Path,

        [AllowNull()]
        [AllowEmptyString()]
        [string]$Content
    )

    $parent = Split-Path -Parent $Path

    if (-not [string]::IsNullOrWhiteSpace($parent)) {
        [System.IO.Directory]::CreateDirectory($parent) | Out-Null
    }

    if ($null -eq $Content) {
        $Content = ''
    }

    $utf8 = [System.Text.UTF8Encoding]::new($false)
    [System.IO.File]::WriteAllText($Path,$Content,$utf8)
}

function Read-TextFile {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "File absent : $Path"
    }

    return [System.IO.File]::ReadAllText($Path)
}

function Get-FileSha256 {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Impossible de calculer SHA-256 : fichier absent : $Path"
    }

    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

# ============================================================================
# PATH HELPERS
# ============================================================================

function Test-SafeProjectPath {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    $fullProject = [System.IO.Path]::GetFullPath($ProjectRoot)
    $fullPath    = [System.IO.Path]::GetFullPath($Path)

    if (-not $fullPath.StartsWith(
        $fullProject,
        [System.StringComparison]::OrdinalIgnoreCase
    )) {
        return $false
    }

    return $true
}

function Resolve-ProjectRelativePath {
    param(
        [Parameter(Mandatory)]
        [string]$RelativePath
    )

    $candidate = Join-Path $ProjectRoot $RelativePath
    $full      = [System.IO.Path]::GetFullPath($candidate)

    if (-not (Test-SafeProjectPath $full)) {
        throw "Path traversal détecté : $RelativePath"
    }

    return $full
}

# ============================================================================
# PARSER
# ============================================================================

function Get-PowerShellParserErrors {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Parser target absent : $Path"
    }

    $tokens = $null
    $parseErrors = $null

    [void][System.Management.Automation.Language.Parser]::ParseFile(
        $Path,
        [ref]$tokens,
        [ref]$parseErrors
    )

    $records = @()

    if ($null -ne $parseErrors) {
        foreach ($parseRecord in @($parseErrors)) {

            $extent = $null

            try {
                $extent = $parseRecord.Extent
            }
            catch {
                $extent = $null
            }

            $lineNumber = 0
            $columnNumber = 0
            $lineText = ''

            if ($null -ne $extent) {

                try {
                    $lineNumber = [int]$extent.StartLineNumber
                }
                catch {
                    $lineNumber = 0
                }

                try {
                    $columnNumber = [int]$extent.StartColumnNumber
                }
                catch {
                    $columnNumber = 0
                }

                try {
                    $lineText = [string]$extent.Text
                }
                catch {
                    $lineText = ''
                }
            }

            $message = ''

            try {
                $message = [string]$parseRecord.Message
            }
            catch {
                $message = 'Parser error'
            }

            $records += [pscustomobject]@{
                File        = $Path
                Line        = $lineNumber
                Column      = $columnNumber
                Message     = $message
                ExtentText  = $lineText
                ErrorId     = [string]$parseRecord.ErrorId
                ErrorType   = if ($null -ne $parseRecord.GetType()) {
                    $parseRecord.GetType().FullName
                }
                else {
                    ''
                }
            }
        }
    }

    return @($records)
}

function Get-ParserCount {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    return @(
        Get-PowerShellParserErrors -Path $Path
    ).Count
}

# ============================================================================
# REPAIR DOSSIER DISCOVERY
# ============================================================================

function Find-LatestRepairDossier {

    if (-not (Test-Path -LiteralPath $ReportsRoot -PathType Container)) {
        throw "Répertoire reports absent : $ReportsRoot"
    }

    $runs = @(
        Get-ChildItem `
            -LiteralPath $ReportsRoot `
            -Directory `
            -ErrorAction Stop |
        Sort-Object LastWriteTimeUtc -Descending
    )

    foreach ($run in $runs) {

        $dossier = Join-Path $run.FullName 'REPAIR_DOSSIER'

        if (Test-Path -LiteralPath $dossier -PathType Container) {

            $matrix = Join-Path $dossier 'ROOT_CAUSE_MATRIX.json'

            if (Test-Path -LiteralPath $matrix -PathType Leaf) {
                return $dossier
            }
        }
    }

    throw 'Aucun REPAIR_DOSSIER exploitable trouvé.'
}

# ============================================================================
# ROOT MATRIX
# ============================================================================

function Load-RootCauseMatrix {
    param(
        [Parameter(Mandatory)]
        [string]$Dossier
    )

    $matrixPath = Join-Path $Dossier 'ROOT_CAUSE_MATRIX.json'

    if (-not (Test-Path -LiteralPath $matrixPath -PathType Leaf)) {
        throw "ROOT_CAUSE_MATRIX.json absent."
    }

    $raw = Read-TextFile $matrixPath

    if ([string]::IsNullOrWhiteSpace($raw)) {
        throw 'ROOT_CAUSE_MATRIX.json est vide.'
    }

    $json = $raw | ConvertFrom-Json

    $records = @()

    if ($json -is [System.Array]) {
        $records = @($json)
    }
    elseif ($null -ne $json.RootCauses) {
        $records = @($json.RootCauses)
    }
    elseif ($null -ne $json.RootCauseMatrix) {
        $records = @($json.RootCauseMatrix)
    }
    elseif ($null -ne $json.Items) {
        $records = @($json.Items)
    }
    else {
        $records = @($json)
    }

    if ($records.Count -eq 0) {
        throw 'ROOT_CAUSE_MATRIX ne contient aucune cause exploitable.'
    }

    return @($records)
}

# ============================================================================
# TARGET EXTRACTION
# ============================================================================

function Get-PropertyValue {
    param(
        [Parameter(Mandatory)]
        [object]$Object,

        [Parameter(Mandatory)]
        [string[]]$Names
    )

    foreach ($name in $Names) {

        $property = $Object.PSObject.Properties |
            Where-Object {
                $_.Name -ieq $name
            } |
            Select-Object -First 1

        if ($null -ne $property) {
            return $property.Value
        }
    }

    return $null
}

function Get-TargetFilesFromMatrix {
    param(
        [Parameter(Mandatory)]
        [object[]]$Matrix
    )

    $paths = New-Object System.Collections.Generic.HashSet[string](
        [System.StringComparer]::OrdinalIgnoreCase
    )

    foreach ($record in $Matrix) {

        $possible = @(
            Get-PropertyValue $record @(
                'File',
                'FilePath',
                'Path',
                'Target',
                'TargetFile',
                'SourceFile',
                'RelativePath'
            )
        )

        foreach ($value in $possible) {

            if ($null -eq $value) {
                continue
            }

            $text = [string]$value

            if ([string]::IsNullOrWhiteSpace($text)) {
                continue
            }

            $text = $text.Trim()

            if ($text -match '^[A-Za-z]:\\') {
                $full = [System.IO.Path]::GetFullPath($text)

                if (Test-SafeProjectPath $full) {
                    [void]$paths.Add($full)
                }

                continue
            }

            if ($text -match '^[\\/]+') {
                continue
            }

            try {
                $full = Resolve-ProjectRelativePath $text

                if (Test-Path -LiteralPath $full -PathType Leaf) {
                    [void]$paths.Add($full)
                }
            }
            catch {
                continue
            }
        }
    }

    $result = @(
        $paths |
        Sort-Object
    )

    return $result
}

# ============================================================================
# ERROR QUEUE
# ============================================================================

function New-ErrorQueue {
    param(
        [Parameter(Mandatory)]
        [object[]]$TargetFiles
    )

    $queue = @()

    foreach ($target in $TargetFiles) {

        $parserRecords = @(
            Get-PowerShellParserErrors -Path $target
        )

        foreach ($parserRecord in $parserRecords) {

            $queue += [pscustomobject]@{
                QueueId    = [Guid]::NewGuid().ToString('N')
                File       = $target
                Line       = $parserRecord.Line
                Column     = $parserRecord.Column
                Message    = $parserRecord.Message
                ExtentText = $parserRecord.ExtentText
                ErrorId    = $parserRecord.ErrorId
            }
        }
    }

    return @($queue)
}

# ============================================================================
# SOURCE LINE EXTRACTION
# ============================================================================

function Get-SourceLines {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    $text = Read-TextFile $Path

    if ($null -eq $text) {
        return @()
    }

    if ($text.Length -eq 0) {
        return @()
    }

    return @(
        $text -split "`r?`n",-1
    )
}

# ============================================================================
# HYPOTHESIS GENERATORS
# ============================================================================

function New-HypothesisRecord {
    param(
        [Parameter(Mandatory)]
        [string]$Kind,

        [Parameter(Mandatory)]
        [string]$Description,

        [Parameter(Mandatory)]
        [string]$OriginalText,

        [Parameter(Mandatory)]
        [string]$CandidateText,

        [Parameter(Mandatory)]
        [int]$Line
    )

    return [pscustomobject]@{
        HypothesisId  = [Guid]::NewGuid().ToString('N')
        Kind          = $Kind
        Description   = $Description
        Line          = $Line
        OriginalText  = $OriginalText
        CandidateText = $CandidateText
    }
}

function New-MechanicalHypotheses {
    param(
        [Parameter(Mandatory)]
        [string[]]$Lines,

        [Parameter(Mandatory)]
        [object[]]$ParserRecords
    )

    $hypotheses = @()

    if ($null -eq $Lines) {
        return @()
    }

    if ($Lines.Count -eq 0) {
        return @()
    }

    foreach ($record in $ParserRecords) {

        $lineNumber = [int]$record.Line

        if ($lineNumber -lt 1) {
            continue
        }

        if ($lineNumber -gt $Lines.Count) {
            continue
        }

        $index = $lineNumber - 1
        $line  = [string]$Lines[$index]

        if ($null -eq $line) {
            $line = ''
        }

        # --------------------------------------------------------------------
        # HYPOTHESIS A
        # Normalize smart quotes only.
        # --------------------------------------------------------------------

        $normalized = Normalize-Text $line

        if ($normalized -ne $line) {

            $copy = @($Lines)
            $copy[$index] = $normalized

            $hypotheses += New-HypothesisRecord `
                -Kind 'NORMALIZE_SMART_QUOTES' `
                -Description 'Replace Unicode typographic quotes/dashes by ASCII equivalents.' `
                -OriginalText $line `
                -CandidateText $normalized `
                -Line $lineNumber
        }

        # --------------------------------------------------------------------
        # HYPOTHESIS B
        # Remove trailing PowerShell continuation marker followed by junk.
        # Conservative: only if the line ends with backtick + spaces.
        # --------------------------------------------------------------------

        if ($line -match '`\s+$') {

            $candidate = $line -replace '`\s+$','`'

            if ($candidate -ne $line) {

                $hypotheses += New-HypothesisRecord `
                    -Kind 'NORMALIZE_CONTINUATION' `
                    -Description 'Normalize trailing PowerShell continuation whitespace.' `
                    -OriginalText $line `
                    -CandidateText $candidate `
                    -Line $lineNumber
            }
        }

        # --------------------------------------------------------------------
        # HYPOTHESIS C
        # Remove trailing whitespace after a continuation backtick.
        # --------------------------------------------------------------------

        if ($line -match '`\s+$') {

            $candidate = $line.TrimEnd()

            if ($candidate -ne $line) {

                $hypotheses += New-HypothesisRecord `
                    -Kind 'TRIM_AFTER_BACKTICK' `
                    -Description 'Remove whitespace after PowerShell continuation backtick.' `
                    -OriginalText $line `
                    -CandidateText $candidate `
                    -Line $lineNumber
            }
        }
    }

    return @($hypotheses)
}

# ============================================================================
# APPLY ONE HYPOTHESIS TO A CANDIDATE COPY
# ============================================================================

function Apply-Hypothesis {
    param(
        [Parameter(Mandatory)]
        [string]$CandidatePath,

        [Parameter(Mandatory)]
        [object]$Hypothesis
    )

    $lines = @(Get-SourceLines -Path $CandidatePath)

    if ($lines.Count -eq 0) {
        return $false
    }

    $index = [int]$Hypothesis.Line - 1

    if ($index -lt 0 -or $index -ge $lines.Count) {
        return $false
    }

    $lines[$index] = [string]$Hypothesis.CandidateText

    $content = $lines -join [Environment]::NewLine

    Write-Utf8NoBom `
        -Path $CandidatePath `
        -Content $content

    return $true
}

# ============================================================================
# CANDIDATE DIRECTORY
# ============================================================================

function Get-CandidatePath {
    param(
        [Parameter(Mandatory)]
        [string]$SourcePath,

        [Parameter(Mandatory)]
        [int]$Index
    )

    $relative = $SourcePath.Substring($ProjectRoot.Length).TrimStart('\')

    $safeName = $relative `
        -replace '\\','__' `
        -replace '/','__' `
        -replace ':','_'

    $name = '{0:D4}__{1}' -f $Index,$safeName

    return Join-Path $CandidatesRoot $name
}

# ============================================================================
# CANDIDATE RECORD
# ============================================================================

function New-CandidateResult {
    param(
        [Parameter(Mandatory)]
        [object]$Hypothesis,

        [Parameter(Mandatory)]
        [string]$SourcePath,

        [Parameter(Mandatory)]
        [string]$CandidatePath,

        [Parameter(Mandatory)]
        [int]$BaselineErrors,

        [Parameter(Mandatory)]
        [int]$CandidateErrors,

        [Parameter(Mandatory)]
        [string]$SourceHash,

        [Parameter(Mandatory)]
        [string]$CandidateHash
    )

    $improvement = $BaselineErrors - $CandidateErrors

    $classification = 'REJECTED'

    if ($CandidateErrors -lt $BaselineErrors) {
        $classification = 'IMPROVED'
    }
    elseif ($CandidateErrors -gt $BaselineErrors) {
        $classification = 'REGRESSION'
    }
    else {
        $classification = 'UNCHANGED'
    }

    return [pscustomobject]@{
        HypothesisId     = $Hypothesis.HypothesisId
        Kind             = $Hypothesis.Kind
        Description      = $Hypothesis.Description
        SourcePath       = $SourcePath
        CandidatePath    = $CandidatePath
        Line             = $Hypothesis.Line
        BaselineErrors   = $BaselineErrors
        CandidateErrors  = $CandidateErrors
        Improvement      = $improvement
        Classification   = $classification
        SourceHash       = $SourceHash
        CandidateHash    = $CandidateHash
        SourceUnchanged  = ($SourceHash -eq (Get-FileSha256 -Path $SourcePath))
    }
}

# ============================================================================
# MAIN
# ============================================================================

try {

    Write-Banner "$EngineName v$ScriptVersion"

    Write-Info 'PROJECT' $ProjectRoot
    Write-Info 'MODE' 'READ-ONLY / CANDIDATE-ONLY / FAIL-CLOSED'
    Write-Info 'QUALITY' 'FORENSIC / DETERMINISTIC / CERTIFICATION-GRADE'
    Write-Info 'SOURCE MUTATION' 'DISABLED'
    Write-Info 'EXECUTION' 'DISABLED'
    Write-Info 'PROMOTION' 'DISABLED'

    # ========================================================================
    # 1
    # ========================================================================

    Write-Step '1/15' 'Validation environnement...'

    if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) {
        throw "Projet absent : $ProjectRoot"
    }

    if (-not (Test-Path -LiteralPath $ReportsRoot -PathType Container)) {
        [System.IO.Directory]::CreateDirectory($ReportsRoot) | Out-Null
    }

    Write-Status 'ENVIRONMENT' 'PASS'

    # ========================================================================
    # 2
    # ========================================================================

    Write-Step '2/15' 'Recherche du dernier REPAIR_DOSSIER...'

    $RepairDossier = Find-LatestRepairDossier

    Write-Info 'DOSSIER' $RepairDossier
    Write-Status 'DISCOVERY' 'PASS'

    # ========================================================================
    # 3
    # ========================================================================

    Write-Step '3/15' 'Chargement de la Root-Cause Matrix...'

    $RootMatrix = @(Load-RootCauseMatrix -Dossier $RepairDossier)

    $RootCauseCount = $RootMatrix.Count

    Write-Info 'ROOT CAUSES' $RootCauseCount

    if ($RootCauseCount -eq 0) {
        throw 'Aucune root cause.'
    }

    # ========================================================================
    # 4
    # ========================================================================

    Write-Step '4/15' 'Identification forensic des fichiers cibles...'

    $TargetFiles = @(
        Get-TargetFilesFromMatrix -Matrix $RootMatrix
    )

    $TargetFileCount = $TargetFiles.Count

    Write-Info 'TARGET FILES' $TargetFileCount

    if ($TargetFileCount -eq 0) {
        throw 'Aucun fichier cible PowerShell identifiable dans la matrice.'
    }

    # ========================================================================
    # 5
    # ========================================================================

    Write-Step '5/15' 'Construction du baseline original...'

    $Baseline = @()

    foreach ($target in $TargetFiles) {

        $hash = Get-FileSha256 -Path $target
        $parser = @(Get-PowerShellParserErrors -Path $target)

        $Baseline += [pscustomobject]@{
            Path         = $target
            Hash         = $hash
            ParserErrors = $parser.Count
            Errors       = @($parser)
        }
    }

    $OriginalErrorCount = (
        $Baseline |
        Measure-Object -Property ParserErrors -Sum
    ).Sum

    if ($null -eq $OriginalErrorCount) {
        $OriginalErrorCount = 0
    }

    Write-Info 'BASELINE FILES' $Baseline.Count
    Write-Info 'PARSER ERRORS' $OriginalErrorCount

    # ========================================================================
    # 6
    # ========================================================================

    Write-Step '6/15' 'Clonage strict des sources...'

    [System.IO.Directory]::CreateDirectory($RunRoot) | Out-Null
    [System.IO.Directory]::CreateDirectory($Workbench) | Out-Null
    [System.IO.Directory]::CreateDirectory($CandidatesRoot) | Out-Null
    [System.IO.Directory]::CreateDirectory($AcceptedRoot) | Out-Null
    [System.IO.Directory]::CreateDirectory($RejectedRoot) | Out-Null
    [System.IO.Directory]::CreateDirectory($AmbiguousRoot) | Out-Null
    [System.IO.Directory]::CreateDirectory($Reports) | Out-Null
    [System.IO.Directory]::CreateDirectory($EvidenceRoot) | Out-Null

    $CloneIndex = 0
    $CloneMap = @()

    foreach ($baselineRecord in $Baseline) {

        $CloneIndex++

        $candidatePath = Get-CandidatePath `
            -SourcePath $baselineRecord.Path `
            -Index $CloneIndex

        Copy-Item `
            -LiteralPath $baselineRecord.Path `
            -Destination $candidatePath `
            -Force `
            -ErrorAction Stop

        $cloneHash = Get-FileSha256 -Path $candidatePath

        if ($cloneHash -ne $baselineRecord.Hash) {
            throw "Clone SHA-256 mismatch : $($baselineRecord.Path)"
        }

        $CloneMap += [pscustomobject]@{
            Source    = $baselineRecord.Path
            Candidate = $candidatePath
            Hash      = $baselineRecord.Hash
        }
    }

    Write-Info 'CLONED' $CloneMap.Count

    # ========================================================================
    # 7
    # ========================================================================

    Write-Step '7/15' 'Revalidation parser des candidats clonés...'

    $CandidateBaseline = @()

    foreach ($clone in $CloneMap) {

        $parser = @(Get-PowerShellParserErrors -Path $clone.Candidate)

        $CandidateBaseline += [pscustomobject]@{
            Source        = $clone.Source
            Candidate     = $clone.Candidate
            ParserErrors  = $parser.Count
            Errors        = @($parser)
        }
    }

    $CandidateBaselineCount = (
        $CandidateBaseline |
        Measure-Object -Property ParserErrors -Sum
    ).Sum

    if ($null -eq $CandidateBaselineCount) {
        $CandidateBaselineCount = 0
    }

    Write-Info 'CANDIDATE BASELINE' $CandidateBaselineCount

    if ($CandidateBaselineCount -ne $OriginalErrorCount) {
        throw "Baseline clone incohérent : original=$OriginalErrorCount candidate=$CandidateBaselineCount"
    }

    # ========================================================================
    # 8
    # ========================================================================

    Write-Step '8/15' 'Construction de la file des erreurs parser...'

    $ErrorQueue = @(
        New-ErrorQueue -TargetFiles $TargetFiles
    )

    Write-Info 'ERROR QUEUE' $ErrorQueue.Count

    # ========================================================================
    # 9
    # ========================================================================

    Write-Step '9/15' 'Génération des hypothèses de réparation...'

    $Hypotheses = @()

    foreach ($baselineRecord in $Baseline) {

        $lines = @(Get-SourceLines -Path $baselineRecord.Path)

        if ($null -eq $lines) {
            $lines = @()
        }

        if ($lines.Count -eq 0) {
            continue
        }

        $fileErrors = @($baselineRecord.Errors)

        $fileHypotheses = @(
            New-MechanicalHypotheses `
                -Lines $lines `
                -ParserRecords $fileErrors
        )

        foreach ($hypothesis in $fileHypotheses) {

            $Hypotheses += [pscustomobject]@{
                SourcePath   = $baselineRecord.Path
                HypothesisId = $hypothesis.HypothesisId
                Kind         = $hypothesis.Kind
                Description  = $hypothesis.Description
                Line         = $hypothesis.Line
                OriginalText = $hypothesis.OriginalText
                CandidateText = $hypothesis.CandidateText
            }
        }
    }

    Write-Info 'HYPOTHESES' $Hypotheses.Count

    # ========================================================================
    # 10
    # ========================================================================

    Write-Step '10/15' 'Évaluation des hypothèses sur candidats isolés...'

    $Results = @()
    $AttemptIndex = 0

    foreach ($hypothesis in $Hypotheses) {

        $AttemptIndex++

        $sourcePath = $hypothesis.SourcePath

        $clone = $CloneMap |
            Where-Object {
                $_.Source -eq $sourcePath
            } |
            Select-Object -First 1

        if ($null -eq $clone) {
            continue
        }

        $attemptPath = Join-Path `
            $CandidatesRoot `
            ('ATTEMPT_{0:D5}.ps1' -f $AttemptIndex)

        Copy-Item `
            -LiteralPath $clone.Candidate `
            -Destination $attemptPath `
            -Force

        $sourceHashBefore = Get-FileSha256 -Path $sourcePath

        $applied = Apply-Hypothesis `
            -CandidatePath $attemptPath `
            -Hypothesis $hypothesis

        if (-not $applied) {
            continue
        }

        $candidateErrors = @(
            Get-PowerShellParserErrors -Path $attemptPath
        )

        $candidateHash = Get-FileSha256 -Path $attemptPath

        $baselineErrors = (
            $Baseline |
            Where-Object {
                $_.Path -eq $sourcePath
            } |
            Select-Object -First 1
        ).ParserErrors

        $result = New-CandidateResult `
            -Hypothesis $hypothesis `
            -SourcePath $sourcePath `
            -CandidatePath $attemptPath `
            -BaselineErrors $baselineErrors `
            -CandidateErrors $candidateErrors.Count `
            -SourceHash $sourceHashBefore `
            -CandidateHash $candidateHash

        $Results += $result
    }

    $AttemptCount = $Results.Count

    Write-Info 'ATTEMPTS' $AttemptCount

    # ========================================================================
    # 11
    # ========================================================================

    Write-Step '11/15' 'Sélection stricte des candidats réellement améliorés...'

    $Improved = @(
        $Results |
        Where-Object {
            $_.Classification -eq 'IMPROVED' -and
            $_.SourceUnchanged -eq $true
        }
    )

    $Regressions = @(
        $Results |
        Where-Object {
            $_.Classification -eq 'REGRESSION'
        }
    )

    $Unchanged = @(
        $Results |
        Where-Object {
            $_.Classification -eq 'UNCHANGED'
        }
    )

    $Accepted = @()
    $Rejected = @()
    $Ambiguous = @()

    # Only strictly improved candidates can enter the accepted evidence set.
    foreach ($item in $Improved) {

        $sourceName = Split-Path -Leaf $item.SourcePath
        $dest = Join-Path `
            $AcceptedRoot `
            ('{0}__{1}' -f $item.HypothesisId,$sourceName)

        Copy-Item `
            -LiteralPath $item.CandidatePath `
            -Destination $dest `
            -Force

        $Accepted += [pscustomobject]@{
            HypothesisId    = $item.HypothesisId
            Source          = $item.SourcePath
            Candidate       = $dest
            BaselineErrors  = $item.BaselineErrors
            CandidateErrors = $item.CandidateErrors
            Improvement     = $item.Improvement
            Classification  = $item.Classification
            SourceHash      = $item.SourceHash
            CandidateHash   = $item.CandidateHash
        }
    }

    foreach ($item in $Results) {

        if ($item.Classification -ne 'IMPROVED') {

            $Rejected += $item
        }
    }

    $AcceptedCount  = $Accepted.Count
    $RejectedCount  = $Rejected.Count
    $AmbiguousCount = $Ambiguous.Count
    $RegressionCount = $Regressions.Count

    Write-Info 'IMPROVED' $Improved.Count
    Write-Info 'ACCEPTED' $AcceptedCount
    Write-Info 'REJECTED' $RejectedCount
    Write-Info 'REGRESSIONS' $RegressionCount

    # ========================================================================
    # 12
    # ========================================================================

    Write-Step '12/15' 'Vérification de l''intégrité des sources originales...'

    $SourceMutationRecords = @()

    foreach ($baselineRecord in $Baseline) {

        $afterHash = Get-FileSha256 -Path $baselineRecord.Path

        $mutated = $afterHash -ne $baselineRecord.Hash

        $SourceMutationRecords += [pscustomobject]@{
            Path       = $baselineRecord.Path
            BeforeHash = $baselineRecord.Hash
            AfterHash  = $afterHash
            Mutated    = $mutated
        }

        if ($mutated) {
            $SourceMutation = $true
        }
    }

    $mutationCount = @(
        $SourceMutationRecords |
        Where-Object {
            $_.Mutated -eq $true
        }
    ).Count

    Write-Info 'SOURCE MUTATIONS' $mutationCount

    if ($SourceMutation) {
        throw 'VIOLATION CRITIQUE : une source originale a changé.'
    }

    Write-Status 'SOURCE INTEGRITY' 'PASS'

    # ========================================================================
    # 13
    # ========================================================================

    Write-Step '13/15' 'Calcul du verdict global...'

    $FinalParserErrors = $OriginalErrorCount

    if ($AcceptedCount -gt 0) {

        $best = $Accepted |
            Sort-Object Improvement -Descending |
            Select-Object -First 1

        if ($null -ne $best) {
            $FinalParserErrors = [int]$best.CandidateErrors
        }
    }

    $GlobalImprovement = $OriginalErrorCount - $FinalParserErrors

    if ($OriginalErrorCount -gt 0) {

        $ImprovementRatio = [math]::Round(
            ($GlobalImprovement / [double]$OriginalErrorCount) * 100,
            4
        )
    }
    else {
        $ImprovementRatio = 100
    }

    if ($SourceMutation) {
        $GlobalVerdict = 'FAIL-CLOSED / SOURCE-INTEGRITY-VIOLATION'
    }
    elseif ($AcceptedCount -gt 0) {
        $GlobalVerdict = 'CANDIDATE-IMPROVEMENT-DETECTED / NOT-CERTIFIED'
    }
    elseif ($OriginalErrorCount -eq 0) {
        $GlobalVerdict = 'NO-PARSER-ERRORS / NOT-CERTIFIED'
    }
    else {
        $GlobalVerdict = 'NO-IMPROVEMENT / FAIL-CLOSED'
    }

    Write-Info 'GLOBAL IMPROVEMENT' $GlobalImprovement
    Write-Info 'IMPROVEMENT RATIO' "$ImprovementRatio %"
    Write-Info 'VERDICT' $GlobalVerdict

    # ========================================================================
    # 14
    # ========================================================================

    Write-Step '14/15' 'Génération du manifeste forensic...'

    $Manifest = [ordered]@{
        Engine               = $EngineName
        Version              = $ScriptVersion
        RunId                = $RunId
        TimestampUtc         = [DateTime]::UtcNow.ToString('o')

        ProjectRoot          = $ProjectRoot
        RepairDossier        = $RepairDossier
        Workbench            = $Workbench

        RootCauses           = $RootCauseCount
        TargetFiles          = $TargetFileCount

        BaselineParserErrors = $OriginalErrorCount
        FinalCandidateErrors = $FinalParserErrors

        GlobalImprovement    = $GlobalImprovement
        ImprovementRatio     = $ImprovementRatio

        RepairAttempts       = $AttemptCount
        HypothesesGenerated  = $Hypotheses.Count

        AcceptedCandidates   = $AcceptedCount
        RejectedCandidates   = $RejectedCount
        AmbiguousCandidates  = $AmbiguousCount
        RegressionCandidates = $RegressionCount

        SourceMutation       = $SourceMutation
        ExecutionPerformed   = $ExecutionPerformed
        PromotionPerformed   = $PromotionPerformed

        Certified            = $Certified
        CertifiedAuthorized  = $CertifiedAuthorized

        Verdict              = $GlobalVerdict
    }

    $ManifestPath = Join-Path `
        $Reports `
        'SUPER_REPAIR_V3_MANIFEST.json'

    $ManifestJson = $Manifest |
        ConvertTo-Json -Depth 30

    Write-Utf8NoBom `
        -Path $ManifestPath `
        -Content $ManifestJson

    # Evidence JSON
    $EvidencePath = Join-Path `
        $EvidenceRoot `
        'CANDIDATE_RESULTS.json'

    $ResultsJson = @($Results) |
        ConvertTo-Json -Depth 30

    Write-Utf8NoBom `
        -Path $EvidencePath `
        -Content $ResultsJson

    # Source integrity evidence
    $IntegrityPath = Join-Path `
        $EvidenceRoot `
        'SOURCE_INTEGRITY.json'

    $IntegrityJson = @($SourceMutationRecords) |
        ConvertTo-Json -Depth 20

    Write-Utf8NoBom `
        -Path $IntegrityPath `
        -Content $IntegrityJson

    # ========================================================================
    # 15
    # ========================================================================

    Write-Step '15/15' 'Génération du rapport final...'

    $ReportPath = Join-Path `
        $Reports `
        'SUPER_REPAIR_V3_REPORT.txt'

    $reportLines = @(
        '============================================================================'
        ' E-ZZIO — TRUTH SUPER REPAIR ENGINE v3.0.1'
        '============================================================================'
        ''
        "RUN ID                  : $RunId"
        "PROJECT                 : $ProjectRoot"
        "REPAIR DOSSIER         : $RepairDossier"
        "WORKBENCH               : $Workbench"
        ''
        "ROOT CAUSES             : $RootCauseCount"
        "TARGET FILES            : $TargetFileCount"
        "BASELINE PARSER ERRORS : $OriginalErrorCount"
        "FINAL CANDIDATE ERRORS : $FinalParserErrors"
        "GLOBAL IMPROVEMENT     : $GlobalImprovement"
        "IMPROVEMENT RATIO      : $ImprovementRatio %"
        ''
        "HYPOTHESES GENERATED   : $($Hypotheses.Count)"
        "REPAIR ATTEMPTS        : $AttemptCount"
        "ACCEPTED CANDIDATES   : $AcceptedCount"
        "REJECTED CANDIDATES   : $RejectedCount"
        "REGRESSIONS           : $RegressionCount"
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
        "REPORT                 : $ReportPath"
        "MANIFEST               : $ManifestPath"
        "EVIDENCE               : $EvidencePath"
        "INTEGRITY              : $IntegrityPath"
        ''
        'FAIL-CLOSED : aucune source originale n''a été modifiée.'
        'FAIL-CLOSED : aucune exécution de code candidat n''a été effectuée.'
        'FAIL-CLOSED : aucune promotion automatique n''a été effectuée.'
        'FAIL-CLOSED : CERTIFIED n''est jamais accordé par ce moteur.'
        '============================================================================'
    )

    Write-Utf8NoBom `
        -Path $ReportPath `
        -Content ($reportLines -join [Environment]::NewLine)

    # ========================================================================
    # FINAL DISPLAY
    # ========================================================================

    Write-Banner "$EngineName v$ScriptVersion COMPLETE"

    Write-Info 'RUN ID' $RunId
    Write-Info 'ROOT CAUSES' $RootCauseCount
    Write-Info 'TARGET FILES' $TargetFileCount
    Write-Info 'PARSER BASELINE' $OriginalErrorCount
    Write-Info 'PARSER FINAL' $FinalParserErrors
    Write-Info 'GLOBAL IMPROVEMENT' $GlobalImprovement
    Write-Info 'ATTEMPTS' $AttemptCount
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
    Write-Info 'REPORT' $ReportPath
    Write-Info 'MANIFEST' $ManifestPath
    Write-Info 'EVIDENCE' $EvidencePath

    Write-Host ''
    Write-Host "VERDICT : $GlobalVerdict" -ForegroundColor Cyan

    Write-Host ''
    Write-Host 'FAIL-CLOSED : les sources originales restent intactes.' -ForegroundColor Yellow
    Write-Host 'FAIL-CLOSED : aucun candidat n''est promu automatiquement.' -ForegroundColor Yellow
    Write-Host 'FAIL-CLOSED : aucun code candidat n''est exécuté.' -ForegroundColor Yellow
    Write-Host '============================================================================' -ForegroundColor Green
    Write-Host ''

    Read-Host 'Appuie sur ENTREE pour terminer' | Out-Null
}
catch {

    $FailureMessage = $_.Exception.Message

    Write-Host ''
    Write-Host '============================================================================' -ForegroundColor Red
    Write-Host " $EngineName v$ScriptVersion FAILED / FAIL-CLOSED" -ForegroundColor Red
    Write-Host '============================================================================' -ForegroundColor Red
    Write-Host ''
    Write-Host "ERROR : $FailureMessage" -ForegroundColor Red
    Write-Host ''
    Write-Host "SOURCE MUTATION : $SourceMutation"
    Write-Host "EXECUTION       : $ExecutionPerformed"
    Write-Host "PROMOTION       : $PromotionPerformed"
    Write-Host ''
    Write-Host 'Aucune promotion de candidat.' -ForegroundColor Yellow
    Write-Host 'Aucun CERTIFIED autorisé.' -ForegroundColor Yellow
    Write-Host 'Les sources originales restent intactes.' -ForegroundColor Yellow
    Write-Host '============================================================================' -ForegroundColor Red
    Write-Host ''

    Read-Host 'Appuie sur ENTREE pour terminer' | Out-Null
}