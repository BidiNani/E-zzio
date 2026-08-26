# ============================================================================
# E-ZZIO — TRUTH SUPER REPAIR ENGINE v1.0.0
# ============================================================================
# MODE       : FORENSIC / FAIL-CLOSED / CANDIDATE-ONLY
# QUALITY    : DETERMINISTIC / CERTIFICATION-GRADE
#
# PURPOSE
#   Construire et tester des CANDIDATS de réparation à partir du dernier
#   REPAIR_DOSSIER sans jamais modifier les fichiers source.
#
# ABSOLUTE SAFETY CONTRACT
#   - Source mutation       : DISABLED
#   - Source deletion      : DISABLED
#   - Source move/rename   : DISABLED
#   - Script execution     : DISABLED
#   - Candidate execution  : DISABLED
#   - Automatic promotion  : DISABLED
#   - CERTIFIED assertion  : DISABLED
#
# PIPELINE
#   1. Discover latest REPAIR_DOSSIER
#   2. Validate manifest / hashes
#   3. Copy source files into isolated workbench
#   4. Parse baseline
#   5. Apply ONLY deterministic mechanical transformations
#   6. Parse candidate
#   7. Compare error count / fingerprints
#   8. Keep candidate only when strictly improved
#   9. Repeat with bounded iterations
#  10. Produce complete forensic manifest
#
# IMPORTANT
#   This engine NEVER overwrites the project source.
#   A candidate is NEVER considered CERTIFIED merely because it parses.
# ============================================================================

[CmdletBinding()]
param(
    [string]$ProjectRoot = 'G:\AI\E-zzio',

    [switch]$NoPause
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$script:FatalReason = ''
$script:SourceMutationDetected = $false
$script:ExecutionDetected = $false

# ============================================================================
# CONSTANTS
# ============================================================================

$EngineVersion = '1.0.0'

$ReportsRoot = Join-Path `
    $ProjectRoot `
    '_EZZIO_TRUTH_REPORTS'

if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) {
    throw "PROJECT_ROOT_NOT_FOUND: $ProjectRoot"
}

if (-not (Test-Path -LiteralPath $ReportsRoot -PathType Container)) {
    throw "TRUTH_REPORTS_ROOT_NOT_FOUND: $ReportsRoot"
}

# ============================================================================
# HELPERS
# ============================================================================

function Write-Section {
    param(
        [Parameter(Mandatory)]
        [string]$Title
    )

    Write-Host ''
    Write-Host '============================================================================' `
        -ForegroundColor Cyan
    Write-Host " $Title" -ForegroundColor Cyan
    Write-Host '============================================================================' `
        -ForegroundColor Cyan
}

function Write-Info {
    param(
        [string]$Label,
        [object]$Value
    )

    Write-Host ("{0,-24}: {1}" -f $Label, $Value)
}

function Get-Sha256File {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "HASH_SOURCE_NOT_FOUND: $Path"
    }

    return (
        Get-FileHash `
            -LiteralPath $Path `
            -Algorithm SHA256 `
            -ErrorAction Stop
    ).Hash.ToLowerInvariant()
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

function Get-RelativePath {
    param(
        [Parameter(Mandatory)]
        [string]$Root,

        [Parameter(Mandatory)]
        [string]$FullPath
    )

    $rootFull = [System.IO.Path]::GetFullPath($Root).TrimEnd(
        [System.IO.Path]::DirectorySeparatorChar,
        [System.IO.Path]::AltDirectorySeparatorChar
    )

    $fileFull = [System.IO.Path]::GetFullPath($FullPath)

    if ($fileFull.StartsWith(
        $rootFull + [System.IO.Path]::DirectorySeparatorChar,
        [System.StringComparison]::OrdinalIgnoreCase
    )) {
        return $fileFull.Substring(
            $rootFull.Length + 1
        )
    }

    return $fileFull
}

function Get-ParserErrors {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

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

        $line = 0
        $column = 0
        $text = ''
        $extent = ''

        if ($null -ne $errorRecord.Extent) {
            $line = [int]$errorRecord.Extent.StartLineNumber
            $column = [int]$errorRecord.Extent.StartColumnNumber
            $text = Get-SafeString $errorRecord.Extent.Text
            $extent = Get-SafeString $errorRecord.Extent.ToString()
        }

        $result.Add(
            [pscustomobject]@{
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

function Get-ParserFingerprint {
    param(
        [Parameter(Mandatory)]
        [object[]]$Errors
    )

    if ($Errors.Count -eq 0) {
        return 'PARSER_CLEAN'
    }

    return (
        @(
            $Errors |
                ForEach-Object {
                    '{0}|{1}|{2}|{3}' -f `
                        $_.ErrorId,
                        $_.Line,
                        $_.Column,
                        $_.Text
                }
        ) -join "`n"
    )
}

function Get-ParserSummary {
    param(
        [Parameter(Mandatory)]
        [object[]]$Errors
    )

    $groups = @(
        $Errors |
            Group-Object ErrorId |
            Sort-Object Name
    )

    $summary = [System.Collections.Generic.List[object]]::new()

    foreach ($group in $groups) {

        $summary.Add(
            [pscustomobject]@{
                ErrorId = $group.Name
                Count   = $group.Count
            }
        )
    }

    return @($summary)
}

function Get-FileLines {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    # IMPORTANT:
    # Always force an array. A one-line file must not become a scalar.
    $lines = @(
        Get-Content `
            -LiteralPath $Path `
            -ErrorAction Stop
    )

    return ,$lines
}

function Set-FileLines {
    param(
        [Parameter(Mandatory)]
        [string]$Path,

        [Parameter(Mandatory)]
        [AllowEmptyCollection()]
        [string[]]$Lines
    )

    # This writes ONLY to a candidate path.
    $Lines |
        Set-Content `
            -LiteralPath $Path `
            -Encoding UTF8 `
            -ErrorAction Stop
}

function Get-Context {
    param(
        [Parameter(Mandatory)]
        [string[]]$Lines,

        [Parameter(Mandatory)]
        [int]$LineNumber,

        [int]$Radius = 12
    )

    if ($Lines.Count -eq 0) {
        return @()
    }

    $target = [Math]::Max(
        1,
        [Math]::Min(
            $LineNumber,
            $Lines.Count
        )
    )

    $start = [Math]::Max(
        1,
        $target - $Radius
    )

    $end = [Math]::Min(
        $Lines.Count,
        $target + $Radius
    )

    $result = [System.Collections.Generic.List[object]]::new()

    for ($i = $start; $i -le $end; $i++) {

        $result.Add(
            [pscustomobject]@{
                LineNumber = $i
                IsTarget   = ($i -eq $target)
                Text       = [string]$Lines[$i - 1]
            }
        )
    }

    return @($result)
}

function Write-Json {
    param(
        [Parameter(Mandatory)]
        [string]$Path,

        [Parameter(Mandatory)]
        [AllowNull()]
        [object]$Object
    )

    $json = $Object |
        ConvertTo-Json `
            -Depth 50 `
            -Compress:$false `
            -ErrorAction Stop

    $json |
        Set-Content `
            -LiteralPath $Path `
            -Encoding UTF8 `
            -ErrorAction Stop
}

function Read-Json {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    return (
        Get-Content `
            -LiteralPath $Path `
            -Raw `
            -ErrorAction Stop |
            ConvertFrom-Json `
                -Depth 100 `
                -ErrorAction Stop
    )
}

function Test-OutputFile {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "OUTPUT_MISSING: $Path"
    }

    $length = (
        Get-Item `
            -LiteralPath $Path `
            -ErrorAction Stop
    ).Length

    if ($length -le 0) {
        throw "OUTPUT_EMPTY: $Path"
    }
}

function Get-LatestRepairDossier {

    $candidates = @(
        Get-ChildItem `
            -LiteralPath $ReportsRoot `
            -Directory `
            -ErrorAction Stop |
        ForEach-Object {

            $dossier = Join-Path `
                $_.FullName `
                'REPAIR_DOSSIER'

            if (Test-Path `
                -LiteralPath $dossier `
                -PathType Container
            ) {
                [pscustomobject]@{
                    RunDirectory = $_.FullName
                    Dossier      = $dossier
                    LastWrite    = $_.LastWriteTimeUtc
                }
            }
        } |
        Sort-Object LastWrite -Descending
    )

    if ($candidates.Count -eq 0) {
        throw 'NO_REPAIR_DOSSIER_FOUND'
    }

    return $candidates[0]
}

function Assert-SourceHashStable {
    param(
        [Parameter(Mandatory)]
        [hashtable]$BaselineHashes
    )

    foreach ($entry in $BaselineHashes.GetEnumerator()) {

        $path = $entry.Key
        $expected = $entry.Value

        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
            $script:SourceMutationDetected = $true
            throw "SOURCE_DISAPPEARED: $path"
        }

        $actual = Get-Sha256File -Path $path

        if ($actual -ne $expected) {
            $script:SourceMutationDetected = $true
            throw "SOURCE_HASH_CHANGED: $path"
        }
    }
}

# ============================================================================
# SAFE MECHANICAL REPAIR ENGINE
# ============================================================================

function Invoke-MechanicalCandidateRepair {
    param(
        [Parameter(Mandatory)]
        [string]$CandidatePath,

        [Parameter(Mandatory)]
        [object[]]$Errors
    )

    $lines = Get-FileLines -Path $CandidatePath

    if ($lines.Count -eq 0) {
        return [pscustomobject]@{
            Changed = $false
            Reason  = 'EMPTY_SOURCE'
            Lines   = $lines
            Actions = @()
        }
    }

    $actions = [System.Collections.Generic.List[object]]::new()

    # ------------------------------------------------------------------------
    # RULE A
    # Invalid variable reference containing ":".
    #
    # Example:
    #   "$foo:bar"
    #
    # becomes:
    #   "${foo}:bar"
    #
    # This is intentionally narrow.
    # ------------------------------------------------------------------------

    $variableErrors = @(
        $Errors |
            Where-Object {
                $_.ErrorId -eq 'InvalidVariableReferenceWithDrive'
            }
    )

    foreach ($error in $variableErrors) {

        $lineNumber = [int]$error.Line

        if ($lineNumber -lt 1 -or $lineNumber -gt $lines.Count) {
            continue
        }

        $original = [string]$lines[$lineNumber - 1]

        $candidate = $original

        $candidate = [regex]::Replace(
            $candidate,
            '\$(?<name>[A-Za-z_][A-Za-z0-9_]*)\:(?![A-Za-z0-9_])',
            '${${name}}:',
            1
        )

        if ($candidate -ne $original) {

            $lines[$lineNumber - 1] = $candidate

            $actions.Add(
                [pscustomobject]@{
                    Rule       = 'VARIABLE_COLON_DISAMBIGUATION'
                    Line       = $lineNumber
                    Before     = $original
                    After      = $candidate
                    Confidence = 'HIGH'
                }
            )
        }
    }

    # ------------------------------------------------------------------------
    # RULE B
    # Case-insensitive duplicate JSON keys are NOT repaired here.
    #
    # JSON semantics are potentially application-specific.
    # Therefore this engine deliberately refuses to mutate them.
    # ------------------------------------------------------------------------

    # ------------------------------------------------------------------------
    # RULE C
    # Empty JSON files are NOT repaired here.
    #
    # An empty JSON file can mean:
    #   - corruption
    #   - generated artifact
    #   - intentionally empty state
    #
    # No blind insertion of "{}".
    # ------------------------------------------------------------------------

    # ------------------------------------------------------------------------
    # RULE D
    # Missing braces / parentheses / strings:
    #
    # NEVER blindly inject delimiters.
    #
    # These errors require structural reconstruction and are therefore
    # classified for HUMAN / AI SOURCE REPAIR rather than guessed.
    # ------------------------------------------------------------------------

    return [pscustomobject]@{
        Changed = ($actions.Count -gt 0)
        Reason  = if ($actions.Count -gt 0) {
            'SAFE_MECHANICAL_RULES_APPLIED'
        }
        else {
            'NO_SAFE_MECHANICAL_REPAIR'
        }
        Lines   = $lines
        Actions = @($actions)
    }
}

# ============================================================================
# MAIN
# ============================================================================

try {

    Write-Section 'E-ZZIO - TRUTH SUPER REPAIR ENGINE v1.0.0'

    Write-Info 'PROJECT' $ProjectRoot
    Write-Info 'MODE' 'READ-ONLY / CANDIDATE-ONLY / FAIL-CLOSED'
    Write-Info 'QUALITY' 'FORENSIC / DETERMINISTIC / CERTIFICATION-GRADE'
    Write-Info 'SOURCE MUTATION' 'DISABLED'
    Write-Info 'EXECUTION' 'DISABLED'
    Write-Host ''

    # ========================================================================
    # [1/12] DISCOVER DOSSIER
    # ========================================================================

    Write-Host '[1/12] Recherche du dernier REPAIR_DOSSIER...' `
        -ForegroundColor Yellow

    $latest = Get-LatestRepairDossier

    Write-Info 'DOSSIER' $latest.Dossier
    Write-Host '      DISCOVERY : PASS' -ForegroundColor Green
    Write-Host ''

    # ========================================================================
    # [2/12] VALIDATE DOSSIER
    # ========================================================================

    Write-Host '[2/12] Validation des artefacts du dossier...' `
        -ForegroundColor Yellow

    $manifestPath = Join-Path `
        $latest.Dossier `
        'REPAIR_DOSSIER_MANIFEST.json'

    $matrixPath = Join-Path `
        $latest.Dossier `
        'ROOT_CAUSE_MATRIX.json'

    $hashPath = Join-Path `
        $latest.Dossier `
        'SOURCE_HASHES.json'

    foreach ($required in @(
        $manifestPath,
        $matrixPath,
        $hashPath
    )) {
        Test-OutputFile -Path $required
    }

    $manifest = Read-Json -Path $manifestPath
    $matrix = @(
        Read-Json -Path $matrixPath
    )
    $hashRecords = @(
        Read-Json -Path $hashPath
    )

    Write-Info 'ROOT MATRIX' $matrix.Count
    Write-Info 'HASH RECORDS' $hashRecords.Count
    Write-Host '      DOSSIER : PASS' -ForegroundColor Green
    Write-Host ''

    # ========================================================================
    # [3/12] BUILD BASELINE
    # ========================================================================

    Write-Host '[3/12] Construction du baseline d''intégrité...' `
        -ForegroundColor Yellow

    $baselineHashes = @{}
    $sourceRecords = [System.Collections.Generic.List[object]]::new()

    foreach ($record in $hashRecords) {

        $relative = Get-SafeString $record.Path

        if ([string]::IsNullOrWhiteSpace($relative)) {
            continue
        }

        $fullPath = Join-Path `
            $ProjectRoot `
            $relative

        if (-not (Test-Path `
            -LiteralPath $fullPath `
            -PathType Leaf
        )) {

            $sourceRecords.Add(
                [pscustomobject]@{
                    Path   = $relative
                    Exists = $false
                    Sha256 = ''
                }
            )

            continue
        }

        $hash = Get-Sha256File -Path $fullPath

        $baselineHashes[$fullPath] = $hash

        $sourceRecords.Add(
            [pscustomobject]@{
                Path   = $relative
                Exists = $true
                Sha256 = $hash
            }
        )
    }

    Write-Info 'BASELINE FILES' $sourceRecords.Count
    Write-Host '      BASELINE : PASS' -ForegroundColor Green
    Write-Host ''

    # ========================================================================
    # [4/12] CREATE WORKBENCH
    # ========================================================================

    Write-Host '[4/12] Création du SUPER REPAIR WORKBENCH...' `
        -ForegroundColor Yellow

    $now = [DateTime]::Now
    $timestamp = $now.ToString('yyyyMMdd_HHmmss_fff')

    $seed = @(
        $timestamp
        $latest.Dossier
        $EngineVersion
    ) -join '|'

    $seedHash = (
        [System.Security.Cryptography.SHA256]::HashData(
            [System.Text.Encoding]::UTF8.GetBytes($seed)
        )
    )

    $seedHex = (
        [System.BitConverter]::ToString($seedHash) -replace '-', ''
    ).ToLowerInvariant()

    $RunId = '{0}_{1}' -f `
        $timestamp,
        $seedHex.Substring(0,12)

    $WorkbenchRoot = Join-Path `
        $ProjectRoot `
        "_EZZIO_TRUTH_REPORTS\$RunId\SUPER_REPAIR_WORKBENCH"

    $CandidatesRoot = Join-Path `
        $WorkbenchRoot `
        'CANDIDATES'

    $EvidenceRoot = Join-Path `
        $WorkbenchRoot `
        'EVIDENCE'

    $DiffRoot = Join-Path `
        $WorkbenchRoot `
        'DIFFS'

    New-Item `
        -ItemType Directory `
        -Path $CandidatesRoot `
        -Force `
        -ErrorAction Stop |
        Out-Null

    New-Item `
        -ItemType Directory `
        -Path $EvidenceRoot `
        -Force `
        -ErrorAction Stop |
        Out-Null

    New-Item `
        -ItemType Directory `
        -Path $DiffRoot `
        -Force `
        -ErrorAction Stop |
        Out-Null

    Write-Info 'RUN ID' $RunId
    Write-Info 'WORKBENCH' $WorkbenchRoot
    Write-Host '      WORKBENCH : PASS' -ForegroundColor Green
    Write-Host ''

    # ========================================================================
    # [5/12] COPY SOURCES
    # ========================================================================

    Write-Host '[5/12] Clonage des sources vers la zone candidate...' `
        -ForegroundColor Yellow

    $candidateRecords = [System.Collections.Generic.List[object]]::new()

    foreach ($record in $sourceRecords) {

        if (-not $record.Exists) {
            continue
        }

        $sourcePath = Join-Path `
            $ProjectRoot `
            $record.Path

        $candidatePath = Join-Path `
            $CandidatesRoot `
            $record.Path

        $candidateDirectory = Split-Path `
            -Parent `
            $candidatePath

        New-Item `
            -ItemType Directory `
            -Path $candidateDirectory `
            -Force `
            -ErrorAction Stop |
            Out-Null

        Copy-Item `
            -LiteralPath $sourcePath `
            -Destination $candidatePath `
            -Force `
            -ErrorAction Stop

        $candidateHash = Get-Sha256File `
            -Path $candidatePath

        if ($candidateHash -ne $record.Sha256) {
            throw "CANDIDATE_INITIAL_HASH_MISMATCH: $($record.Path)"
        }

        $candidateRecords.Add(
            [pscustomobject]@{
                Path            = $record.Path
                SourcePath      = $sourcePath
                CandidatePath   = $candidatePath
                OriginalSha256  = $record.Sha256
                InitialSha256   = $candidateHash
            }
        )
    }

    Write-Info 'CANDIDATES' $candidateRecords.Count
    Write-Host '      CLONING : PASS' -ForegroundColor Green
    Write-Host ''

    # ========================================================================
    # [6/12] BASELINE PARSER
    # ========================================================================

    Write-Host '[6/12] Baseline parser sur les candidats...' `
        -ForegroundColor Yellow

    $baselineParser = [System.Collections.Generic.List[object]]::new()

    foreach ($candidate in $candidateRecords) {

        $extension = [System.IO.Path]::GetExtension(
            $candidate.CandidatePath
        ).ToLowerInvariant()

        if ($extension -notin @(
            '.ps1',
            '.psm1',
            '.psd1'
        )) {
            continue
        }

        $errors = Get-ParserErrors `
            -Path $candidate.CandidatePath

        $candidateErrorsPath = Join-Path `
            $EvidenceRoot `
            (
                (
                    $candidate.Path `
                        -replace '[\\/:*?"<>|]', '_'
                ) + '.baseline.json'
            )

        Write-Json `
            -Path $candidateErrorsPath `
            -Object $errors

        $baselineParser.Add(
            [pscustomobject]@{
                Path        = $candidate.Path
                ErrorCount  = $errors.Count
                Fingerprint = Get-ParserFingerprint $errors
                Errors      = @($errors)
            }
        )
    }

    Write-Info 'PARSER BASELINE' (
        @($baselineParser | Measure-Object ErrorCount -Sum).Sum
    )

    Write-Host '      PARSER : PASS' -ForegroundColor Green
    Write-Host ''

    # ========================================================================
    # [7/12] MECHANICAL REPAIR PASSES
    # ========================================================================

    Write-Host '[7/12] Tentatives de réparation mécanique...' `
        -ForegroundColor Yellow

    $repairRecords = [System.Collections.Generic.List[object]]::new()

    foreach ($candidate in $candidateRecords) {

        $extension = [System.IO.Path]::GetExtension(
            $candidate.CandidatePath
        ).ToLowerInvariant()

        if ($extension -notin @(
            '.ps1',
            '.psm1',
            '.psd1'
        )) {

            $repairRecords.Add(
                [pscustomobject]@{
                    Path              = $candidate.Path
                    Status            = 'NOT_APPLICABLE'
                    BeforeErrors      = 0
                    AfterErrors       = 0
                    Actions           = @()
                    Reason            = 'NON_POWERSHELL'
                    CandidateSha256   = Get-Sha256File `
                        -Path $candidate.CandidatePath
                }
            )

            continue
        }

        $baseline = @(
            $baselineParser |
                Where-Object {
                    $_.Path -eq $candidate.Path
                }
        )[0]

        $workingErrors = @($baseline.Errors)

        $attempt = Invoke-MechanicalCandidateRepair `
            -CandidatePath $candidate.CandidatePath `
            -Errors $workingErrors

        if (-not $attempt.Changed) {

            $repairRecords.Add(
                [pscustomobject]@{
                    Path            = $candidate.Path
                    Status          = 'NO_SAFE_REPAIR'
                    BeforeErrors    = $baseline.ErrorCount
                    AfterErrors     = $baseline.ErrorCount
                    Actions         = @()
                    Reason          = $attempt.Reason
                    CandidateSha256 = Get-Sha256File `
                        -Path $candidate.CandidatePath
                }
            )

            continue
        }

        # Write candidate modifications ONLY.
        Set-FileLines `
            -Path $candidate.CandidatePath `
            -Lines $attempt.Lines

        $afterErrors = @(
            Get-ParserErrors `
                -Path $candidate.CandidatePath
        )

        $beforeCount = $baseline.ErrorCount
        $afterCount = $afterErrors.Count

        if ($afterCount -lt $beforeCount) {

            $status = 'IMPROVED'

        }
        elseif ($afterCount -eq 0 -and $beforeCount -gt 0) {

            $status = 'PARSER_CLEAN'

        }
        else {

            # Revert candidate if the mechanical repair did not strictly
            # improve the parser state.
            Copy-Item `
                -LiteralPath $candidate.SourcePath `
                -Destination $candidate.CandidatePath `
                -Force `
                -ErrorAction Stop

            $status = 'REJECTED_NO_IMPROVEMENT'

            $afterErrors = @(
                Get-ParserErrors `
                    -Path $candidate.CandidatePath
            )

            $afterCount = $afterErrors.Count
        }

        $actionsPath = Join-Path `
            $EvidenceRoot `
            (
                (
                    $candidate.Path `
                        -replace '[\\/:*?"<>|]', '_'
                ) + '.repair.json'
            )

        Write-Json `
            -Path $actionsPath `
            -Object @(
                $attempt.Actions
            )

        $repairRecords.Add(
            [pscustomobject]@{
                Path            = $candidate.Path
                Status          = $status
                BeforeErrors    = $beforeCount
                AfterErrors     = $afterCount
                Actions         = @($attempt.Actions)
                Reason          = $attempt.Reason
                CandidateSha256 = Get-Sha256File `
                    -Path $candidate.CandidatePath
            }
        )
    }

    Write-Info 'FILES PROCESSED' $repairRecords.Count
    Write-Info 'IMPROVED' (
        @(
            $repairRecords |
                Where-Object Status -eq 'IMPROVED'
        ).Count
    )
    Write-Info 'PARSER CLEAN' (
        @(
            $repairRecords |
                Where-Object Status -eq 'PARSER_CLEAN'
        ).Count
    )
    Write-Info 'NO SAFE REPAIR' (
        @(
            $repairRecords |
                Where-Object Status -eq 'NO_SAFE_REPAIR'
        ).Count
    )
    Write-Host ''

    # ========================================================================
    # [8/12] FINAL CANDIDATE PARSER
    # ========================================================================

    Write-Host '[8/12] Revalidation finale de TOUS les candidats...' `
        -ForegroundColor Yellow

    $finalParser = [System.Collections.Generic.List[object]]::new()

    foreach ($candidate in $candidateRecords) {

        $extension = [System.IO.Path]::GetExtension(
            $candidate.CandidatePath
        ).ToLowerInvariant()

        if ($extension -notin @(
            '.ps1',
            '.psm1',
            '.psd1'
        )) {
            continue
        }

        $errors = @(
            Get-ParserErrors `
                -Path $candidate.CandidatePath
        )

        $finalParser.Add(
            [pscustomobject]@{
                Path        = $candidate.Path
                ErrorCount  = $errors.Count
                Clean       = ($errors.Count -eq 0)
                Fingerprint = Get-ParserFingerprint $errors
                Errors      = @($errors)
            }
        )
    }

    $finalParserPath = Join-Path `
        $EvidenceRoot `
        'FINAL_PARSER_RESULTS.json'

    Write-Json `
        -Path $finalParserPath `
        -Object @($finalParser)

    Write-Info 'FINAL PARSER ERRORS' (
        @(
            $finalParser |
                Measure-Object ErrorCount -Sum
        ).Sum
    )

    Write-Host ''

    # ========================================================================
    # [9/12] DIFF / HASH
    # ========================================================================

    Write-Host '[9/12] Calcul des empreintes finales et différences...' `
        -ForegroundColor Yellow

    $finalRecords = [System.Collections.Generic.List[object]]::new()

    foreach ($candidate in $candidateRecords) {

        $sourceHash = Get-Sha256File `
            -Path $candidate.SourcePath

        $candidateHash = Get-Sha256File `
            -Path $candidate.CandidatePath

        if ($sourceHash -ne $candidate.OriginalSha256) {
            $script:SourceMutationDetected = $true
            throw "SOURCE_CHANGED_DURING_REPAIR: $($candidate.Path)"
        }

        $changed = ($sourceHash -ne $candidateHash)

        $final = @(
            $finalParser |
                Where-Object {
                    $_.Path -eq $candidate.Path
                }
        )

        $finalErrorCount = 0

        if ($final.Count -gt 0) {
            $finalErrorCount = $final[0].ErrorCount
        }

        $finalRecords.Add(
            [pscustomobject]@{
                Path             = $candidate.Path
                SourceSha256     = $sourceHash
                CandidateSha256  = $candidateHash
                CandidateChanged = $changed
                FinalParserErrors = $finalErrorCount
                ParserClean      = ($finalErrorCount -eq 0)
            }
        )

        $diffPath = Join-Path `
            $DiffRoot `
            (
                (
                    $candidate.Path `
                        -replace '[\\/:*?"<>|]', '_'
                ) + '.diff.txt'
            )

        try {

            $diff = Compare-Object `
                -ReferenceObject (
                    Get-FileLines `
                        -Path $candidate.SourcePath
                ) `
                -DifferenceObject (
                    Get-FileLines `
                        -Path $candidate.CandidatePath
                ) `
                -IncludeEqual:$false `
                -ErrorAction Stop

            if ($null -eq $diff) {
                'NO_DIFFERENCE' |
                    Set-Content `
                        -LiteralPath $diffPath `
                        -Encoding UTF8
            }
            else {
                $diff |
                    Out-String |
                    Set-Content `
                        -LiteralPath $diffPath `
                        -Encoding UTF8
            }
        }
        catch {
            "DIFF_GENERATION_FAILURE: $($_.Exception.Message)" |
                Set-Content `
                    -LiteralPath $diffPath `
                    -Encoding UTF8
        }
    }

    Write-Host '      HASH / DIFF : PASS' -ForegroundColor Green
    Write-Host ''

    # ========================================================================
    # [10/12] SOURCE IMMUTABILITY GATE
    # ========================================================================

    Write-Host '[10/12] GATE IMMUTABILITÉ SOURCE...' `
        -ForegroundColor Yellow

    Assert-SourceHashStable `
        -BaselineHashes $baselineHashes

    Write-Host '      SOURCE MUTATION : 0' `
        -ForegroundColor Green
    Write-Host '      IMMUTABILITY : PASS' `
        -ForegroundColor Green
    Write-Host ''

    # ========================================================================
    # [11/12] FINAL MANIFEST
    # ========================================================================

    Write-Host '[11/12] Génération du manifeste forensic...' `
        -ForegroundColor Yellow

    $cleanCandidates = @(
        $finalRecords |
            Where-Object {
                $_.ParserClean
            }
    )

    $changedCandidates = @(
        $finalRecords |
            Where-Object {
                $_.CandidateChanged
            }
    )

    $manifestObject = [pscustomobject]@{

        Engine = [pscustomobject]@{
            Name    = 'E-ZZIO TRUTH SUPER REPAIR ENGINE'
            Version = $EngineVersion
        }

        Run = [pscustomobject]@{
            RunId        = $RunId
            SourceDossier = $latest.Dossier
            Timestamp    = $now.ToString('o')
        }

        Safety = [pscustomobject]@{
            SourceMutation       = $false
            SourceDeletion       = $false
            SourceMoveRename     = $false
            Execution            = $false
            CandidateExecution   = $false
            AutomaticPromotion   = $false
            CertificationGranted = $false
        }

        Statistics = [pscustomobject]@{
            RootCauses          = $matrix.Count
            TargetFiles         = $candidateRecords.Count
            ParserBaselineErrors = (
                @(
                    $baselineParser |
                        Measure-Object ErrorCount -Sum
                ).Sum
            )
            ParserFinalErrors = (
                @(
                    $finalParser |
                        Measure-Object ErrorCount -Sum
                ).Sum
            )
            ChangedCandidates = $changedCandidates.Count
            ParserCleanCandidates = $cleanCandidates.Count
        }

        Candidates = @($finalRecords)

        Repairs = @($repairRecords)

        Certification = [pscustomobject]@{
            Authorized = $false
            Reason = 'Candidate parsing alone does not establish semantic certification.'
            RequiredNextStep = 'Complete Truth Forensic rescan of the actual project after any human-approved source repair.'
        }
    }

    $finalManifestPath = Join-Path `
        $WorkbenchRoot `
        'SUPER_REPAIR_MANIFEST.json'

    Write-Json `
        -Path $finalManifestPath `
        -Object $manifestObject

    Write-Host '      MANIFEST : PASS' -ForegroundColor Green
    Write-Host ''

    # ========================================================================
    # [12/12] HUMAN REPORT
    # ========================================================================

    Write-Host '[12/12] Génération du rapport final...' `
        -ForegroundColor Yellow

    $reportPath = Join-Path `
        $WorkbenchRoot `
        'SUPER_REPAIR_REPORT.txt'

    $report = [System.Collections.Generic.List[string]]::new()

    $report.Add('============================================================================')
    $report.Add(' E-ZZIO - TRUTH SUPER REPAIR ENGINE v1.0.0')
    $report.Add('============================================================================')
    $report.Add('')
    $report.Add("RUN ID              : $RunId")
    $report.Add("PROJECT             : $ProjectRoot")
    $report.Add("SOURCE DOSSIER      : $($latest.Dossier)")
    $report.Add("WORKBENCH           : $WorkbenchRoot")
    $report.Add('')
    $report.Add('MODE                : READ-ONLY / CANDIDATE-ONLY / FAIL-CLOSED')
    $report.Add('SOURCE MUTATION     : DISABLED')
    $report.Add('EXECUTION           : DISABLED')
    $report.Add('AUTO PROMOTION      : DISABLED')
    $report.Add('CERTIFICATION       : NOT AUTHORIZED')
    $report.Add('')
    $report.Add('----------------------------------------------------------------------------')
    $report.Add(' STATISTICS')
    $report.Add('----------------------------------------------------------------------------')
    $report.Add("ROOT CAUSES         : $($matrix.Count)")
    $report.Add("TARGET FILES        : $($candidateRecords.Count)")
    $report.Add(
        "BASELINE PARSER ERRORS : $(
            @(
                $baselineParser |
                    Measure-Object ErrorCount -Sum
            ).Sum
        )"
    )
    $report.Add(
        "FINAL PARSER ERRORS    : $(
            @(
                $finalParser |
                    Measure-Object ErrorCount -Sum
            ).Sum
        )"
    )
    $report.Add("CHANGED CANDIDATES  : $($changedCandidates.Count)")
    $report.Add("PARSER CLEAN        : $($cleanCandidates.Count)")
    $report.Add('')
    $report.Add('----------------------------------------------------------------------------')
    $report.Add(' CANDIDATE STATUS')
    $report.Add('----------------------------------------------------------------------------')

    foreach ($item in $repairRecords) {

        $report.Add('')
        $report.Add("FILE       : $($item.Path)")
        $report.Add("STATUS     : $($item.Status)")
        $report.Add("BEFORE     : $($item.BeforeErrors)")
        $report.Add("AFTER      : $($item.AfterErrors)")
        $report.Add("REASON     : $($item.Reason)")

        if (@($item.Actions).Count -gt 0) {

            foreach ($action in @($item.Actions)) {

                $report.Add(
                    "  ACTION   : $($action.Rule) | LINE $($action.Line)"
                )
            }
        }
    }

    $report.Add('')
    $report.Add('----------------------------------------------------------------------------')
    $report.Add(' SAFETY GATES')
    $report.Add('----------------------------------------------------------------------------')
    $report.Add('SOURCE MUTATION     : 0')
    $report.Add('SOURCE DELETION     : 0')
    $report.Add('SOURCE MOVE/RENAME  : 0')
    $report.Add('EXECUTION           : 0')
    $report.Add('AUTO PROMOTION      : 0')
    $report.Add('CERTIFIED           : NOT AUTHORIZED')
    $report.Add('')
    $report.Add('A parser-clean candidate is NOT equivalent to a certified source.')
    $report.Add('Semantic validation and complete Truth Forensic rescan remain mandatory.')
    $report.Add('')
    $report.Add('----------------------------------------------------------------------------')
    $report.Add(' OUTPUTS')
    $report.Add('----------------------------------------------------------------------------')
    $report.Add("MANIFEST            : $finalManifestPath")
    $report.Add("PARSER RESULTS      : $finalParserPath")
    $report.Add("CANDIDATES          : $CandidatesRoot")
    $report.Add("EVIDENCE            : $EvidenceRoot")
    $report.Add("DIFFS               : $DiffRoot")
    $report.Add("REPORT              : $reportPath")
    $report.Add('')
    $report.Add('============================================================================')

    $report |
        Set-Content `
            -LiteralPath $reportPath `
            -Encoding UTF8 `
            -ErrorAction Stop

    Test-OutputFile -Path $finalManifestPath
    Test-OutputFile -Path $finalParserPath
    Test-OutputFile -Path $reportPath

    # ========================================================================
    # FINAL FAIL-CLOSED VERDICT
    # ========================================================================

    Write-Host ''
    Write-Host '============================================================================' `
        -ForegroundColor Green
    Write-Host ' E-ZZIO - SUPER REPAIR WORKBENCH COMPLETE' `
        -ForegroundColor Green
    Write-Host '============================================================================' `
        -ForegroundColor Green
    Write-Host ''

    Write-Info 'RUN ID' $RunId
    Write-Info 'ROOT CAUSES' $matrix.Count
    Write-Info 'TARGET FILES' $candidateRecords.Count
    Write-Info 'CHANGED CANDIDATES' $changedCandidates.Count
    Write-Info 'PARSER CLEAN CANDIDATES' $cleanCandidates.Count
    Write-Info 'SOURCE MUTATION' 0
    Write-Info 'EXECUTION' 0

    Write-Host ''

    if ($cleanCandidates.Count -gt 0) {

        Write-Host 'CANDIDATES PARSER-CLEAN : OUI' `
            -ForegroundColor Yellow

        Write-Host ''
        Write-Host 'ATTENTION : cela ne signifie PAS CERTIFIED.' `
            -ForegroundColor Yellow
    }
    else {

        Write-Host 'CANDIDATES PARSER-CLEAN : 0' `
            -ForegroundColor Red
    }

    Write-Host ''
    Write-Host 'CERTIFIED : NOT AUTHORIZED' `
        -ForegroundColor Yellow
    Write-Host ''
    Write-Host "WORKBENCH : $WorkbenchRoot" `
        -ForegroundColor Cyan
    Write-Host "REPORT    : $reportPath" `
        -ForegroundColor Cyan
    Write-Host ''
    Write-Host 'FAIL-CLOSED : les sources G:\AI\E-zzio n''ont pas été modifiées.' `
        -ForegroundColor Green
    Write-Host '============================================================================' `
        -ForegroundColor Green
}
catch {

    $script:FatalReason = $_.Exception.Message

    Write-Host ''
    Write-Host '============================================================================' `
        -ForegroundColor Red
    Write-Host ' E-ZZIO - SUPER REPAIR FAILED / FAIL-CLOSED' `
        -ForegroundColor Red
    Write-Host '============================================================================' `
        -ForegroundColor Red
    Write-Host ''
    Write-Host "ERROR : $script:FatalReason" `
        -ForegroundColor Red
    Write-Host ''
    Write-Host 'SOURCE MUTATION : ' `
        -NoNewline
    Write-Host $script:SourceMutationDetected `
        -ForegroundColor Yellow
    Write-Host 'EXECUTION       : ' `
        -NoNewline
    Write-Host $script:ExecutionDetected `
        -ForegroundColor Yellow
    Write-Host ''
    Write-Host 'Aucune promotion de candidat.' `
        -ForegroundColor Yellow
    Write-Host 'Aucun CERTIFIED autorisé.' `
        -ForegroundColor Yellow
    Write-Host '============================================================================' `
        -ForegroundColor Red
}
finally {

    if (-not $NoPause) {

        Write-Host ''
        Write-Host 'La fenêtre reste ouverte.' `
            -ForegroundColor DarkGray
        Write-Host ''
        [void](Read-Host 'Appuie sur ENTREE pour terminer')
    }
}