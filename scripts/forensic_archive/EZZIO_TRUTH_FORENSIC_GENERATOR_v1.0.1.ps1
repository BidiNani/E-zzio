# ============================================================================
# E-ZZIO — TRUTH FORENSIC GENERATOR
# Version : 1.0.1
# Mode    : READ-ONLY / FAIL-CLOSED / FORENSIC
#
# PURPOSE
#   Generate a complete factual forensic truth report for E-ZZIO.
#
# GUARANTEES
#   - NEVER executes discovered PowerShell scripts.
#   - NEVER modifies project files.
#   - NEVER repairs files automatically.
#   - Continues after individual file-analysis failures.
#   - Uses parser APIs for PowerShell syntax validation.
#   - Validates JSON independently.
#   - Validates JSONL line-by-line.
#   - Produces deterministic structured findings.
#   - CERTIFIED is possible only when all applicable gates pass.
# ============================================================================

[CmdletBinding()]
param(
    [string]$ProjectRoot = 'G:\AI\E-zzio'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ============================================================================
# CONFIGURATION
# ============================================================================

$GeneratorVersion = '1.0.1'
$StartedAt = Get-Date
$RunId = '{0}_{1}' -f `
    $StartedAt.ToString('yyyyMMdd_HHmmss_fff'), `
    ([guid]::NewGuid().ToString('N').Substring(0,12))

$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)

if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) {
    throw "Project root does not exist: $ProjectRoot"
}

$ReportsRoot = Join-Path $ProjectRoot '_EZZIO_TRUTH_REPORTS'
$RunRoot = Join-Path $ReportsRoot $RunId

$InventoryRoot = Join-Path $RunRoot 'INVENTORY'
$SyntaxRoot = Join-Path $RunRoot 'POWERSHELL_SYNTAX'
$JsonRoot = Join-Path $RunRoot 'JSON_VALIDATION'
$FindingsRoot = Join-Path $RunRoot 'TRUTH_FORENSIC_TRIAGE'
$SummaryRoot = Join-Path $RunRoot 'SUMMARY'

foreach ($directory in @(
    $ReportsRoot,
    $RunRoot,
    $InventoryRoot,
    $SyntaxRoot,
    $JsonRoot,
    $FindingsRoot,
    $SummaryRoot
)) {
    New-Item -ItemType Directory -Path $directory -Force | Out-Null
}

# ============================================================================
# COLLECTIONS
# ============================================================================

$Files = [System.Collections.Generic.List[object]]::new()
$Findings = [System.Collections.Generic.List[object]]::new()
$PowerShellResults = [System.Collections.Generic.List[object]]::new()
$JsonResults = [System.Collections.Generic.List[object]]::new()
$JsonlResults = [System.Collections.Generic.List[object]]::new()

# ============================================================================
# HELPERS
# ============================================================================

function New-Finding {
    param(
        [Parameter(Mandatory)]
        [string]$Severity,

        [Parameter(Mandatory)]
        [string]$Code,

        [string]$Path = '',

        [Parameter(Mandatory)]
        [string]$Message,

        [object]$Evidence = $null
    )

    $item = [pscustomobject]@{
        Severity = $Severity
        Code     = $Code
        Path     = $Path
        Message  = $Message
        Evidence = $Evidence
    }

    [void]$Findings.Add($item)
}

function Get-RelativePath {
    param(
        [Parameter(Mandatory)]
        [string]$FullPath
    )

    $rootUri = [System.Uri](
        (Get-Item -LiteralPath $ProjectRoot).FullName.TrimEnd('\') + '\'
    )

    $fileUri = [System.Uri](
        (Get-Item -LiteralPath $FullPath).FullName
    )

    return [System.Uri]::UnescapeDataString(
        $rootUri.MakeRelativeUri($fileUri).ToString()
    ).Replace('/', '\')
}

function Write-JsonFile {
    param(
        [Parameter(Mandatory)]
        [string]$Path,

        [Parameter(Mandatory)]
        [object]$Value,

        [int]$Depth = 50
    )

    $json = $Value | ConvertTo-Json -Depth $Depth
    [System.IO.File]::WriteAllText(
        $Path,
        $json,
        [System.Text.UTF8Encoding]::new($false)
    )
}

function Test-IsExcludedPath {
    param(
        [Parameter(Mandatory)]
        [string]$FullPath
    )

    $relative = Get-RelativePath -FullPath $FullPath

    $excludedFragments = @(
        '\.git\',
        '\node_modules\',
        '\__pycache__\',
        '\.venv\',
        '\venv\',
        '\_EZZIO_TRUTH_REPORTS\'
    )

    foreach ($fragment in $excludedFragments) {
        if ($relative.Contains($fragment)) {
            return $true
        }
    }

    return $false
}

function Get-FileKind {
    param(
        [Parameter(Mandatory)]
        [string]$Extension
    )

    switch ($Extension.ToLowerInvariant()) {
        '.ps1'  { return 'POWERSHELL' }
        '.psm1' { return 'POWERSHELL_MODULE' }
        '.psd1' { return 'POWERSHELL_DATA' }
        '.json' { return 'JSON' }
        '.jsonl' { return 'JSONL' }
        '.ndjson' { return 'JSONL' }
        '.xml'  { return 'XML' }
        '.yaml' { return 'YAML' }
        '.yml'  { return 'YAML' }
        default { return 'OTHER' }
    }
}

# ============================================================================
# HEADER
# ============================================================================

Write-Host ''
Write-Host '============================================================================' -ForegroundColor Cyan
Write-Host ' E-ZZIO — TRUTH FORENSIC GENERATOR v1.0.1' -ForegroundColor Cyan
Write-Host '============================================================================' -ForegroundColor Cyan
Write-Host ''
Write-Host "PROJECT : $ProjectRoot"
Write-Host "RUN ID  : $RunId"
Write-Host "MODE    : READ-ONLY / FAIL-CLOSED / NO EXECUTION"
Write-Host ''

# ============================================================================
# [1/8] PROJECT DISCOVERY
# ============================================================================

Write-Host '[1/8] Découverte des fichiers...' -ForegroundColor Yellow

$allFiles = @(
    Get-ChildItem `
        -LiteralPath $ProjectRoot `
        -File `
        -Recurse `
        -Force `
        -ErrorAction SilentlyContinue |
    Where-Object {
        -not (Test-IsExcludedPath -FullPath $_.FullName)
    }
)

foreach ($file in $allFiles) {
    $relative = Get-RelativePath -FullPath $file.FullName
    $kind = Get-FileKind -Extension $file.Extension

    $record = [pscustomobject]@{
        RelativePath = $relative
        FullPath     = $file.FullName
        Name         = $file.Name
        Extension    = $file.Extension
        Kind         = $kind
        Length       = [int64]$file.Length
        LastWriteUtc = $file.LastWriteTimeUtc.ToString('o')
    }

    [void]$Files.Add($record)
}

Write-Host "      Fichiers découverts : $($Files.Count)" -ForegroundColor Green

# ============================================================================
# [2/8] INVENTORY
# ============================================================================

Write-Host ''
Write-Host '[2/8] Génération de l''inventaire...' -ForegroundColor Yellow

$inventoryPath = Join-Path $InventoryRoot 'EZZIO_TRUTH_FORENSIC_INVENTORY.json'

$inventory = [pscustomobject]@{
    GeneratorVersion = $GeneratorVersion
    RunId            = $RunId
    ProjectRoot      = $ProjectRoot
    StartedAtUtc     = $StartedAt.ToUniversalTime().ToString('o')
    FileCount        = $Files.Count
    Files             = @($Files)
}

Write-JsonFile `
    -Path $inventoryPath `
    -Value $inventory `
    -Depth 20

Write-Host "      $inventoryPath" -ForegroundColor DarkGray

# ============================================================================
# [3/8] POWERSHELL SYNTAX
# ============================================================================

Write-Host ''
Write-Host '[3/8] Analyse syntaxique PowerShell...' -ForegroundColor Yellow

$psFiles = @(
    $Files |
    Where-Object {
        $_.Kind -in @(
            'POWERSHELL',
            'POWERSHELL_MODULE',
            'POWERSHELL_DATA'
        )
    }
)

$psIndex = 0

foreach ($entry in $psFiles) {

    $psIndex++

    Write-Host (
        '      [{0}/{1}] {2}' -f
        $psIndex,
        $psFiles.Count,
        $entry.RelativePath
    )

    try {

        $tokens = $null
        $errors = $null

        $ast = [System.Management.Automation.Language.Parser]::ParseFile(
            $entry.FullPath,
            [ref]$tokens,
            [ref]$errors
        )

        $errorRecords = @()

        foreach ($parseError in @($errors)) {

            $errorRecords += [pscustomobject]@{
                Type     = 'POWERSHELL_SYNTAX_ERROR'
                Path     = $entry.RelativePath
                ErrorId  = if ($null -ne $parseError.ErrorId) {
                    [string]$parseError.ErrorId
                }
                else {
                    ''
                }
                Message  = [string]$parseError.Message
                Extent   = if ($null -ne $parseError.Extent) {
                    [string]$parseError.Extent.Text
                }
                else {
                    ''
                }
            }
        }

        $result = [pscustomobject]@{
            Path            = $entry.RelativePath
            FullPath        = $entry.FullPath
            ParseSuccessful = ($errors.Count -eq 0)
            ErrorCount      = $errors.Count
            Errors          = @($errorRecords)
        }

        [void]$PowerShellResults.Add($result)

        if ($errors.Count -gt 0) {

            foreach ($errorRecord in $errorRecords) {

                New-Finding `
                    -Severity 'CRITICAL' `
                    -Code 'POWERSHELL_SYNTAX_DEFECT' `
                    -Path $entry.RelativePath `
                    -Message $errorRecord.Message `
                    -Evidence $errorRecord
            }

            Write-Host (
                "             FAIL — {0} erreur(s)" -f $errors.Count
            ) -ForegroundColor Red
        }
        else {
            Write-Host '             PASS' -ForegroundColor Green
        }

    }
    catch {

        $failure = [pscustomobject]@{
            Type    = 'POWERSHELL_ANALYSIS_FAILURE'
            Path    = $entry.RelativePath
            Message = $_.Exception.Message
        }

        $result = [pscustomobject]@{
            Path            = $entry.RelativePath
            FullPath        = $entry.FullPath
            ParseSuccessful = $false
            ErrorCount      = 1
            Errors          = @($failure)
        }

        [void]$PowerShellResults.Add($result)

        New-Finding `
            -Severity 'CRITICAL' `
            -Code 'POWERSHELL_ANALYSIS_FAILURE' `
            -Path $entry.RelativePath `
            -Message $_.Exception.Message `
            -Evidence $failure

        Write-Host '             ANALYSIS FAILURE' -ForegroundColor Red
    }
}

$syntaxErrors = @(
    $PowerShellResults |
    Where-Object {
        -not $_.ParseSuccessful
    }
)

Write-Host ''
Write-Host "      PowerShell analysés : $($PowerShellResults.Count)"
Write-Host "      PowerShell invalides : $($syntaxErrors.Count)"

# ============================================================================
# [4/8] JSON
# ============================================================================

Write-Host ''
Write-Host '[4/8] Validation JSON...' -ForegroundColor Yellow

$jsonFiles = @(
    $Files |
    Where-Object {
        $_.Kind -eq 'JSON'
    }
)

$jsonIndex = 0

foreach ($entry in $jsonFiles) {

    $jsonIndex++

    Write-Host (
        '      [{0}/{1}] {2}' -f
        $jsonIndex,
        $jsonFiles.Count,
        $entry.RelativePath
    )

    try {

        $raw = [System.IO.File]::ReadAllText(
            $entry.FullPath,
            [System.Text.UTF8Encoding]::new($false)
        )

        if ([string]::IsNullOrWhiteSpace($raw)) {

            $result = [pscustomobject]@{
                Path    = $entry.RelativePath
                Valid   = $false
                Error   = 'EMPTY_JSON_FILE'
            }

            [void]$JsonResults.Add($result)

            New-Finding `
                -Severity 'CRITICAL' `
                -Code 'JSON_EMPTY_FILE' `
                -Path $entry.RelativePath `
                -Message 'JSON file is empty.' `
                -Evidence $result

            Write-Host '             FAIL — EMPTY' -ForegroundColor Red
            continue
        }

        $null = $raw | ConvertFrom-Json -ErrorAction Stop

        $result = [pscustomobject]@{
            Path    = $entry.RelativePath
            Valid   = $true
            Error   = ''
        }

        [void]$JsonResults.Add($result)

        Write-Host '             PASS' -ForegroundColor Green
    }
    catch {

        $result = [pscustomobject]@{
            Path    = $entry.RelativePath
            Valid   = $false
            Error   = $_.Exception.Message
        }

        [void]$JsonResults.Add($result)

        New-Finding `
            -Severity 'CRITICAL' `
            -Code 'JSON_SYNTAX_DEFECT' `
            -Path $entry.RelativePath `
            -Message $_.Exception.Message `
            -Evidence $result

        Write-Host '             FAIL' -ForegroundColor Red
    }
}

# ============================================================================
# [5/8] JSONL / NDJSON
# ============================================================================

Write-Host ''
Write-Host '[5/8] Validation JSONL / NDJSON...' -ForegroundColor Yellow

$jsonlFiles = @(
    $Files |
    Where-Object {
        $_.Kind -eq 'JSONL'
    }
)

$jsonlIndex = 0

foreach ($entry in $jsonlFiles) {

    $jsonlIndex++

    Write-Host (
        '      [{0}/{1}] {2}' -f
        $jsonlIndex,
        $jsonlFiles.Count,
        $entry.RelativePath
    )

    try {

        $lines = @(
            Get-Content `
                -LiteralPath $entry.FullPath `
                -ErrorAction Stop
        )

        $lineNumber = 0
        $validLines = 0
        $invalidLines = 0
        $lineErrors = [System.Collections.Generic.List[object]]::new()

        foreach ($line in $lines) {

            $lineNumber++

            if ([string]::IsNullOrWhiteSpace($line)) {
                continue
            }

            try {
                $null = $line | ConvertFrom-Json -ErrorAction Stop
                $validLines++
            }
            catch {

                $invalidLines++

                $lineError = [pscustomobject]@{
                    Line    = $lineNumber
                    Message = $_.Exception.Message
                }

                [void]$lineErrors.Add($lineError)
            }
        }

        $result = [pscustomobject]@{
            Path         = $entry.RelativePath
            Valid        = ($invalidLines -eq 0)
            TotalLines   = $lineNumber
            ValidLines   = $validLines
            InvalidLines = $invalidLines
            Errors       = @($lineErrors)
        }

        [void]$JsonlResults.Add($result)

        if ($invalidLines -gt 0) {

            New-Finding `
                -Severity 'CRITICAL' `
                -Code 'JSONL_SYNTAX_DEFECT' `
                -Path $entry.RelativePath `
                -Message (
                    "JSONL contains {0} invalid line(s)." -f $invalidLines
                ) `
                -Evidence $result

            Write-Host (
                "             FAIL — {0} ligne(s)" -f $invalidLines
            ) -ForegroundColor Red
        }
        else {
            Write-Host '             PASS' -ForegroundColor Green
        }

    }
    catch {

        $result = [pscustomobject]@{
            Path         = $entry.RelativePath
            Valid        = $false
            TotalLines   = 0
            ValidLines   = 0
            InvalidLines = 1
            Errors       = @(
                [pscustomobject]@{
                    Line    = 0
                    Message = $_.Exception.Message
                }
            )
        }

        [void]$JsonlResults.Add($result)

        New-Finding `
            -Severity 'CRITICAL' `
            -Code 'JSONL_ANALYSIS_FAILURE' `
            -Path $entry.RelativePath `
            -Message $_.Exception.Message `
            -Evidence $result

        Write-Host '             ANALYSIS FAILURE' -ForegroundColor Red
    }
}

# ============================================================================
# [6/8] GENERIC FILE INTEGRITY OBSERVATIONS
# ============================================================================

Write-Host ''
Write-Host '[6/8] Contrôles structurels complémentaires...' -ForegroundColor Yellow

$emptyFiles = @(
    $Files |
    Where-Object {
        $_.Length -eq 0
    }
)

foreach ($empty in $emptyFiles) {

    New-Finding `
        -Severity 'WARNING' `
        -Code 'EMPTY_FILE' `
        -Path $empty.RelativePath `
        -Message 'File is physically empty.' `
        -Evidence $empty
}

Write-Host "      Fichiers vides : $($emptyFiles.Count)"

# ============================================================================
# [7/8] FINDINGS / REPORTS
# ============================================================================

Write-Host ''
Write-Host '[7/8] Génération des rapports forensic...' -ForegroundColor Yellow

$critical = @(
    $Findings |
    Where-Object {
        [string]$_.Severity -eq 'CRITICAL'
    }
)

$high = @(
    $Findings |
    Where-Object {
        [string]$_.Severity -eq 'HIGH'
    }
)

$warnings = @(
    $Findings |
    Where-Object {
        [string]$_.Severity -eq 'WARNING'
    }
)

$findingsPath = Join-Path `
    $FindingsRoot `
    'EZZIO_TRUTH_FORENSIC_FINDINGS.json'

Write-JsonFile `
    -Path $findingsPath `
    -Value @($Findings) `
    -Depth 50

$psReportPath = Join-Path `
    $SyntaxRoot `
    'EZZIO_POWERSHELL_SYNTAX_RESULTS.json'

Write-JsonFile `
    -Path $psReportPath `
    -Value @($PowerShellResults) `
    -Depth 30

$jsonReportPath = Join-Path `
    $JsonRoot `
    'EZZIO_JSON_RESULTS.json'

Write-JsonFile `
    -Path $jsonReportPath `
    -Value @($JsonResults) `
    -Depth 30

$jsonlReportPath = Join-Path `
    $JsonRoot `
    'EZZIO_JSONL_RESULTS.json'

Write-JsonFile `
    -Path $jsonlReportPath `
    -Value @($JsonlResults) `
    -Depth 30

# ============================================================================
# [8/8] FINAL VERDICT
# ============================================================================

Write-Host ''
Write-Host '[8/8] Calcul du verdict...' -ForegroundColor Yellow

$psTotal = $PowerShellResults.Count
$psPass = @(
    $PowerShellResults |
    Where-Object {
        $_.ParseSuccessful
    }
).Count

$psFail = $psTotal - $psPass

$jsonTotal = $JsonResults.Count
$jsonPass = @(
    $JsonResults |
    Where-Object {
        $_.Valid
    }
).Count

$jsonFail = $jsonTotal - $jsonPass

$jsonlTotal = $JsonlResults.Count
$jsonlPass = @(
    $JsonlResults |
    Where-Object {
        $_.Valid
    }
).Count

$jsonlFail = $jsonlTotal - $jsonlPass

$hasCritical = ($critical.Count -gt 0)

if ($hasCritical) {
    $verdict = 'FAIL'
    $certified = $false
}
else {
    $verdict = 'CERTIFIED'
    $certified = $true
}

$finishedAt = Get-Date

$summary = [pscustomobject]@{
    GeneratorVersion = $GeneratorVersion
    RunId            = $RunId
    ProjectRoot      = $ProjectRoot

    StartedAtUtc     = $StartedAt.ToUniversalTime().ToString('o')
    FinishedAtUtc    = $finishedAt.ToUniversalTime().ToString('o')

    Mode             = 'READ_ONLY_FAIL_CLOSED_NO_EXECUTION'

    FilesDiscovered  = $Files.Count

    PowerShell       = [pscustomobject]@{
        Total = $psTotal
        Pass  = $psPass
        Fail  = $psFail
    }

    JSON             = [pscustomobject]@{
        Total = $jsonTotal
        Pass  = $jsonPass
        Fail  = $jsonFail
    }

    JSONL            = [pscustomobject]@{
        Total = $jsonlTotal
        Pass  = $jsonlPass
        Fail  = $jsonlFail
    }

    Findings         = [pscustomobject]@{
        Total    = $Findings.Count
        Critical = $critical.Count
        High     = $high.Count
        Warning  = $warnings.Count
    }

    Verdict          = $verdict
    Certified        = $certified
}

$summaryPath = Join-Path `
    $SummaryRoot `
    'EZZIO_TRUTH_FORENSIC_SUMMARY.json'

Write-JsonFile `
    -Path $summaryPath `
    -Value $summary `
    -Depth 30

# ============================================================================
# HUMAN READABLE REPORT
# ============================================================================

$textReportPath = Join-Path `
    $SummaryRoot `
    'EZZIO_TRUTH_FORENSIC_SUMMARY.txt'

$reportLines = [System.Collections.Generic.List[string]]::new()

[void]$reportLines.Add('============================================================================')
[void]$reportLines.Add('E-ZZIO — TRUTH FORENSIC SUMMARY')
[void]$reportLines.Add('============================================================================')
[void]$reportLines.Add('')
[void]$reportLines.Add("Generator Version : $GeneratorVersion")
[void]$reportLines.Add("Run ID            : $RunId")
[void]$reportLines.Add("Project Root      : $ProjectRoot")
[void]$reportLines.Add("Started UTC       : $($StartedAt.ToUniversalTime().ToString('o'))")
[void]$reportLines.Add("Finished UTC      : $($finishedAt.ToUniversalTime().ToString('o'))")
[void]$reportLines.Add('')
[void]$reportLines.Add('MODE')
[void]$reportLines.Add('----')
[void]$reportLines.Add('READ-ONLY / FAIL-CLOSED / NO EXECUTION')
[void]$reportLines.Add('')
[void]$reportLines.Add('INVENTORY')
[void]$reportLines.Add('---------')
[void]$reportLines.Add("Files discovered : $($Files.Count)")
[void]$reportLines.Add('')
[void]$reportLines.Add('POWERSHELL')
[void]$reportLines.Add('----------')
[void]$reportLines.Add("Total : $psTotal")
[void]$reportLines.Add("Pass  : $psPass")
[void]$reportLines.Add("Fail  : $psFail")
[void]$reportLines.Add('')
[void]$reportLines.Add('JSON')
[void]$reportLines.Add('----')
[void]$reportLines.Add("Total : $jsonTotal")
[void]$reportLines.Add("Pass  : $jsonPass")
[void]$reportLines.Add("Fail  : $jsonFail")
[void]$reportLines.Add('')
[void]$reportLines.Add('JSONL')
[void]$reportLines.Add('-----')
[void]$reportLines.Add("Total : $jsonlTotal")
[void]$reportLines.Add("Pass  : $jsonlPass")
[void]$reportLines.Add("Fail  : $jsonlFail")
[void]$reportLines.Add('')
[void]$reportLines.Add('FINDINGS')
[void]$reportLines.Add('--------')
[void]$reportLines.Add("Total    : $($Findings.Count)")
[void]$reportLines.Add("Critical : $($critical.Count)")
[void]$reportLines.Add("High     : $($high.Count)")
[void]$reportLines.Add("Warning  : $($warnings.Count)")
[void]$reportLines.Add('')
[void]$reportLines.Add('VERDICT')
[void]$reportLines.Add('-------')
[void]$reportLines.Add($verdict)
[void]$reportLines.Add('')
[void]$reportLines.Add('============================================================================')

[System.IO.File]::WriteAllLines(
    $textReportPath,
    $reportLines,
    [System.Text.UTF8Encoding]::new($false)
)

# ============================================================================
# CONSOLE OUTPUT
# ============================================================================

Write-Host ''
Write-Host '============================================================================' -ForegroundColor Cyan
Write-Host ' E-ZZIO — TRUTH FORENSIC RESULT' -ForegroundColor Cyan
Write-Host '============================================================================' -ForegroundColor Cyan
Write-Host ''
Write-Host "RUN ID          : $RunId"
Write-Host "FILES           : $($Files.Count)"
Write-Host ''
Write-Host "POWERSHELL      : $psTotal total / $psPass PASS / $psFail FAIL"
Write-Host "JSON            : $jsonTotal total / $jsonPass PASS / $jsonFail FAIL"
Write-Host "JSONL           : $jsonlTotal total / $jsonlPass PASS / $jsonlFail FAIL"
Write-Host ''
Write-Host "TOTAL FINDINGS  : $($Findings.Count)"
Write-Host "CRITICAL        : $($critical.Count)"
Write-Host "HIGH            : $($high.Count)"
Write-Host "WARNING         : $($warnings.Count)"
Write-Host ''

if ($certified) {
    Write-Host 'VERDICT : CERTIFIED' -ForegroundColor Green
}
else {
    Write-Host 'VERDICT : FAIL' -ForegroundColor Red
}

Write-Host ''
Write-Host 'REPORT ROOT:' -ForegroundColor Cyan
Write-Host $RunRoot
Write-Host ''
Write-Host 'FINDINGS:' -ForegroundColor Cyan
Write-Host $findingsPath
Write-Host ''
Write-Host 'SUMMARY:' -ForegroundColor Cyan
Write-Host $summaryPath
Write-Host ''
Write-Host '============================================================================' -ForegroundColor Cyan

# ============================================================================
# EXIT CODE
# ============================================================================

if ($certified) {
    exit 0
}
else {
    exit 10
}