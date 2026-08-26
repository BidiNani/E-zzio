# ============================================================================
# E-ZZIO — PROJECT TRUTH ENGINE
# Version : 1.0.1
#
# MODE
#   READ-ONLY PROJECT ANALYSIS
#   FAIL-CLOSED
#   FORENSIC
#
# PURPOSE
#   Build a factual machine-readable representation of the E-ZZIO project.
#
# GUARANTEE
#   This engine never modifies source files inside the project.
#
# OUTPUT
#   A dedicated truth-report directory is created under the project root.
#   Only report artifacts are written there.
# ============================================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ============================================================================
# CONFIGURATION
# ============================================================================

$Version = '1.0.1'
$ProjectRoot = 'G:\AI\E-zzio'

$ReportRoot = Join-Path `
    $ProjectRoot `
    '_EZZIO_TRUTH_REPORTS'

$RunId = (
    Get-Date -Format 'yyyyMMdd_HHmmss_fff'
) + '_' + (
    [guid]::NewGuid().ToString('N').Substring(0, 12)
)

$RunRoot = Join-Path $ReportRoot $RunId

# ============================================================================
# SAFETY
# ============================================================================

if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) {
    throw "PROJECT_ROOT_NOT_FOUND: $ProjectRoot"
}

# ============================================================================
# SUPPORTED FILE CLASSES
# ============================================================================

$TextExtensions = @(
    '.ps1',
    '.psm1',
    '.psd1',
    '.py',
    '.pyw',
    '.json',
    '.jsonl',
    '.yaml',
    '.yml',
    '.toml',
    '.ini',
    '.cfg',
    '.conf',
    '.txt',
    '.md',
    '.rst',
    '.xml',
    '.csv',
    '.sql',
    '.sh',
    '.bat',
    '.cmd'
)

$ExcludedDirectoryNames = @(
    '.git',
    '.venv',
    'venv',
    '__pycache__',
    'node_modules',
    '.pytest_cache',
    '.mypy_cache',
    '.ruff_cache'
)

$ExcludedFileNames = @(
    'thumbs.db',
    'desktop.ini'
)

# ============================================================================
# STATE
# ============================================================================

$Files = [System.Collections.Generic.List[object]]::new()
$Problems = [System.Collections.Generic.List[object]]::new()

$Stats = [ordered]@{
    FilesDiscovered       = 0
    FilesAnalyzed         = 0
    FilesReadable         = 0
    FilesUnreadable       = 0
    EmptyFiles            = 0
    PowerShellFiles       = 0
    PowerShellSyntaxPass  = 0
    PowerShellSyntaxFail  = 0
    JsonFiles              = 0
    JsonSyntaxPass        = 0
    JsonSyntaxFail        = 0
    OtherFiles             = 0
    HashFailures           = 0
    ProblemsDetected       = 0
}

$StartedUtc = [DateTime]::UtcNow

# ============================================================================
# HELPER — SAFE RELATIVE PATH
# ============================================================================

function Get-RelativeProjectPath {
    param(
        [Parameter(Mandatory)]
        [string]$FullPath
    )

    $Root = [System.IO.Path]::GetFullPath($ProjectRoot)
    $Full = [System.IO.Path]::GetFullPath($FullPath)

    if ($Full.StartsWith($Root, [System.StringComparison]::OrdinalIgnoreCase)) {
        $Relative = $Full.Substring($Root.Length).TrimStart(
            [char]'\',
            [char]'/'
        )

        return $Relative
    }

    return $Full
}

# ============================================================================
# HELPER — FILE CLASS
# ============================================================================

function Get-FileClass {
    param(
        [Parameter(Mandatory)]
        [string]$Extension
    )

    switch ($Extension.ToLowerInvariant()) {

        '.ps1'  { return 'POWERSHELL' }
        '.psm1' { return 'POWERSHELL_MODULE' }
        '.psd1' { return 'POWERSHELL_DATA' }

        '.py'   { return 'PYTHON' }
        '.pyw'  { return 'PYTHON' }

        '.json'  { return 'JSON' }
        '.jsonl' { return 'JSONL' }

        '.yaml' { return 'YAML' }
        '.yml'  { return 'YAML' }
        '.toml' { return 'TOML' }

        '.sqlite' { return 'SQLITE' }
        '.db'     { return 'DATABASE' }

        default {
            if ($TextExtensions -contains $Extension.ToLowerInvariant()) {
                return 'TEXT'
            }

            return 'BINARY_OR_UNKNOWN'
        }
    }
}

# ============================================================================
# HELPER — SHA256
# ============================================================================

function Get-SafeSha256 {
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
        $Stats.HashFailures++

        throw (
            'HASH_FAILURE: {0}: {1}' -f
            $Path,
            $_.Exception.Message
        )
    }
}

# ============================================================================
# HELPER — POWERSHELL SYNTAX
# ============================================================================

function Test-PowerShellSyntax {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    $Tokens = $null
    $Errors = $null

    try {
        $null = [System.Management.Automation.Language.Parser]::ParseFile(
            $Path,
            [ref]$Tokens,
            [ref]$Errors
        )

        $ErrorCount = @($Errors).Count

        if ($ErrorCount -eq 0) {
            return [pscustomobject]@{
                Status = 'PASS'
                ErrorCount = 0
                Errors = @()
            }
        }

        $Details = @(
            $Errors | ForEach-Object {
                [ordered]@{
                    ErrorId = [string]$_.ErrorId
                    Message = [string]$_.Message
                    IncompleteInput = [bool]$_.IncompleteInput
                    Extent = [string]$_.Extent.Text
                }
            }
        )

        return [pscustomobject]@{
            Status = 'FAIL'
            ErrorCount = $ErrorCount
            Errors = $Details
        }
    }
    catch {
        return [pscustomobject]@{
            Status = 'FAIL'
            ErrorCount = 1
            Errors = @(
                [ordered]@{
                    ErrorId = 'PARSER_EXCEPTION'
                    Message = $_.Exception.Message
                    IncompleteInput = $false
                    Extent = ''
                }
            )
        }
    }
}

# ============================================================================
# HELPER — JSON SYNTAX
# ============================================================================

function Test-JsonSyntax {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    try {
        $Content = [System.IO.File]::ReadAllText(
            $Path,
            [System.Text.UTF8Encoding]::new($false)
        )

        $null = $Content | ConvertFrom-Json -ErrorAction Stop

        return [pscustomobject]@{
            Status = 'PASS'
            Error = $null
        }
    }
    catch {
        return [pscustomobject]@{
            Status = 'FAIL'
            Error = $_.Exception.Message
        }
    }
}

# ============================================================================
# HELPER — DIRECTORY EXCLUSION
# ============================================================================

function Test-ExcludedDirectory {
    param(
        [Parameter(Mandatory)]
        [System.IO.DirectoryInfo]$Directory
    )

    return (
        $ExcludedDirectoryNames -contains
        $Directory.Name.ToLowerInvariant()
    )
}

# ============================================================================
# INVENTORY
# ============================================================================

Write-Host ''
Write-Host '============================================================' `
    -ForegroundColor Cyan
Write-Host ' E-ZZIO PROJECT TRUTH ENGINE v1.0.1' `
    -ForegroundColor Cyan
Write-Host ' READ-ONLY / FORENSIC / FAIL-CLOSED' `
    -ForegroundColor Cyan
Write-Host '============================================================' `
    -ForegroundColor Cyan
Write-Host ''

Write-Host "PROJECT : $ProjectRoot"
Write-Host "RUN ID  : $RunId"
Write-Host ''

# ============================================================================
# REPORT DIRECTORY
# ============================================================================

New-Item `
    -ItemType Directory `
    -Path $RunRoot `
    -Force `
    -ErrorAction Stop |
    Out-Null

# ============================================================================
# DISCOVERY
# ============================================================================

Write-Host 'DISCOVERY STARTED...' -ForegroundColor DarkCyan

$DiscoveredFiles = @(
    Get-ChildItem `
        -LiteralPath $ProjectRoot `
        -File `
        -Recurse `
        -Force `
        -ErrorAction Stop |
    Where-Object {

        $Excluded = $false

        foreach ($Directory in $_.Directory.FullName.Split(
            [System.IO.Path]::DirectorySeparatorChar
        )) {
            if (
                $ExcludedDirectoryNames -contains
                $Directory.ToLowerInvariant()
            ) {
                $Excluded = $true
                break
            }
        }

        if ($Excluded) {
            return $false
        }

        if (
            $ExcludedFileNames -contains
            $_.Name.ToLowerInvariant()
        ) {
            return $false
        }

        return $true
    }
)

$Stats.FilesDiscovered = $DiscoveredFiles.Count

Write-Host (
    'FILES DISCOVERED : {0}' -f
    $Stats.FilesDiscovered
) -ForegroundColor Green

# ============================================================================
# FILE ANALYSIS
# ============================================================================

$Index = 0

foreach ($File in $DiscoveredFiles) {

    $Index++

    $RelativePath = Get-RelativeProjectPath `
        -FullPath $File.FullName

    $Extension = $File.Extension.ToLowerInvariant()
    $Class = Get-FileClass `
        -Extension $Extension

    $Status = 'UNKNOWN'
    $ReadStatus = 'NOT_TESTED'
    $Hash = $null
    $SyntaxStatus = $null
    $SyntaxErrors = @()
    $JsonStatus = $null
    $JsonError = $null
    $Problem = $null

    Write-Progress `
        -Activity 'E-ZZIO Truth Analysis' `
        -Status $RelativePath `
        -PercentComplete (
            [int](($Index / [Math]::Max(
                1,
                $DiscoveredFiles.Count
            )) * 100)
        )

    try {

        $Stats.FilesAnalyzed++

        $Length = [int64]$File.Length

        if ($Length -eq 0) {
            $Stats.EmptyFiles++
            $Problem = 'EMPTY_FILE'
        }

        # ------------------------------------------------------------
        # READ TEST
        # ------------------------------------------------------------

        try {

            $Stream = [System.IO.FileStream]::new(
                $File.FullName,
                [System.IO.FileMode]::Open,
                [System.IO.FileAccess]::Read,
                [System.IO.FileShare]::ReadWrite
            )

            try {
                $ReadStatus = 'PASS'
                $Stats.FilesReadable++
            }
            finally {
                $Stream.Dispose()
            }
        }
        catch {

            $ReadStatus = 'FAIL'
            $Stats.FilesUnreadable++

            if ($null -eq $Problem) {
                $Problem = 'UNREADABLE_FILE'
            }

            $Problems.Add(
                [ordered]@{
                    Type = 'UNREADABLE_FILE'
                    Path = $RelativePath
                    Message = $_.Exception.Message
                }
            )
        }

        # ------------------------------------------------------------
        # HASH
        # ------------------------------------------------------------

        if ($ReadStatus -eq 'PASS') {
            try {
                $Hash = Get-SafeSha256 `
                    -Path $File.FullName
            }
            catch {
                if ($null -eq $Problem) {
                    $Problem = 'HASH_FAILURE'
                }
            }
        }

        # ------------------------------------------------------------
        # POWERSHELL
        # ------------------------------------------------------------

        if (
            $Extension -eq '.ps1' -or
            $Extension -eq '.psm1' -or
            $Extension -eq '.psd1'
        ) {

            $Stats.PowerShellFiles++

            if ($ReadStatus -eq 'PASS') {

                $SyntaxResult = Test-PowerShellSyntax `
                    -Path $File.FullName

                $SyntaxStatus = $SyntaxResult.Status
                $SyntaxErrors = @($SyntaxResult.Errors)

                if ($SyntaxStatus -eq 'PASS') {
                    $Stats.PowerShellSyntaxPass++
                }
                else {
                    $Stats.PowerShellSyntaxFail++

                    if ($null -eq $Problem) {
                        $Problem = 'POWERSHELL_SYNTAX_ERROR'
                    }

                    foreach ($SyntaxError in $SyntaxErrors) {
                        $Problems.Add(
                            [ordered]@{
                                Type = 'POWERSHELL_SYNTAX_ERROR'
                                Path = $RelativePath
                                ErrorId = $SyntaxError.ErrorId
                                Message = $SyntaxError.Message
                                Extent = $SyntaxError.Extent
                            }
                        )
                    }
                }
            }
        }

        # ------------------------------------------------------------
        # JSON
        # ------------------------------------------------------------

        if ($Extension -eq '.json') {

            $Stats.JsonFiles++

            if ($ReadStatus -eq 'PASS' -and $Length -gt 0) {

                $JsonResult = Test-JsonSyntax `
                    -Path $File.FullName

                $JsonStatus = $JsonResult.Status
                $JsonError = $JsonResult.Error

                if ($JsonStatus -eq 'PASS') {
                    $Stats.JsonSyntaxPass++
                }
                else {
                    $Stats.JsonSyntaxFail++

                    if ($null -eq $Problem) {
                        $Problem = 'JSON_SYNTAX_ERROR'
                    }

                    $Problems.Add(
                        [ordered]@{
                            Type = 'JSON_SYNTAX_ERROR'
                            Path = $RelativePath
                            Message = $JsonError
                        }
                    )
                }
            }
        }

        if (
            $Class -ne 'POWERSHELL' -and
            $Class -ne 'POWERSHELL_MODULE' -and
            $Class -ne 'POWERSHELL_DATA' -and
            $Class -ne 'JSON'
        ) {
            $Stats.OtherFiles++
        }

        # ------------------------------------------------------------
        # FINAL FILE STATUS
        # ------------------------------------------------------------

        if ($null -ne $Problem) {
            $Status = 'PROBLEM_DETECTED'

            $Stats.ProblemsDetected++

            if (
                $Problem -eq 'EMPTY_FILE'
            ) {
                $Problems.Add(
                    [ordered]@{
                        Type = 'EMPTY_FILE'
                        Path = $RelativePath
                        Message = 'File contains zero bytes.'
                    }
                )
            }
        }
        else {
            $Status = 'ANALYZED'
        }

        $Files.Add(
            [ordered]@{
                Path = $RelativePath
                FullPath = $File.FullName
                Name = $File.Name
                Extension = $Extension
                Class = $Class
                SizeBytes = $Length
                LastWriteTimeUtc = $File.LastWriteTimeUtc.ToString(
                    'o'
                )
                SHA256 = $Hash
                ReadStatus = $ReadStatus
                Status = $Status
                Problem = $Problem
                PowerShellSyntax = $SyntaxStatus
                PowerShellErrors = $SyntaxErrors
                JsonSyntax = $JsonStatus
                JsonError = $JsonError
            }
        )
    }
    catch {

        $Stats.ProblemsDetected++

        $Problems.Add(
            [ordered]@{
                Type = 'ANALYSIS_EXCEPTION'
                Path = $RelativePath
                Message = $_.Exception.Message
            }
        )

        $Files.Add(
            [ordered]@{
                Path = $RelativePath
                FullPath = $File.FullName
                Name = $File.Name
                Extension = $Extension
                Class = $Class
                SizeBytes = [int64]$File.Length
                LastWriteTimeUtc = $File.LastWriteTimeUtc.ToString(
                    'o'
                )
                SHA256 = $Hash
                ReadStatus = $ReadStatus
                Status = 'ANALYSIS_EXCEPTION'
                Problem = 'ANALYSIS_EXCEPTION'
                PowerShellSyntax = $SyntaxStatus
                PowerShellErrors = $SyntaxErrors
                JsonSyntax = $JsonStatus
                JsonError = $JsonError
            }
        )
    }
}

Write-Progress `
    -Activity 'E-ZZIO Truth Analysis' `
    -Completed

# ============================================================================
# FINAL COUNTS
# ============================================================================

$FinishedUtc = [DateTime]::UtcNow

$DurationSeconds = (
    $FinishedUtc - $StartedUtc
).TotalSeconds

$MachineVerdict = 'TRUTH_ANALYSIS_COMPLETE'

if ($Stats.HashFailures -gt 0) {
    $MachineVerdict = 'FORENSIC_FAIL_CLOSED'
}

if ($Stats.FilesUnreadable -gt 0) {
    $MachineVerdict = 'FORENSIC_FAIL_CLOSED'
}

# ============================================================================
# MACHINE REPORT
# ============================================================================

$Report = [ordered]@{
    Product = 'E-ZZIO'
    Component = 'Project Truth Engine'
    Version = $Version

    Run = [ordered]@{
        RunId = $RunId
        StartedUtc = $StartedUtc.ToString('o')
        FinishedUtc = $FinishedUtc.ToString('o')
        DurationSeconds = [Math]::Round(
            $DurationSeconds,
            3
        )
    }

    Configuration = [ordered]@{
        ProjectRoot = $ProjectRoot
        Mode = 'READ_ONLY'
        FailClosed = $true
        SourceMutationAllowed = $false
    }

    Verdict = $MachineVerdict

    Statistics = $Stats

    Problems = @($Problems)

    Files = @($Files)
}

# ============================================================================
# WRITE REPORTS
# ============================================================================

$JsonReportPath = Join-Path `
    $RunRoot `
    'EZZIO_PROJECT_TRUTH.json'

$ProblemsPath = Join-Path `
    $RunRoot `
    'EZZIO_PROJECT_PROBLEMS.json'

$InventoryPath = Join-Path `
    $RunRoot `
    'EZZIO_PROJECT_INVENTORY.json'

$SummaryPath = Join-Path `
    $RunRoot `
    'EZZIO_PROJECT_SUMMARY.txt'

$Report |
    ConvertTo-Json `
        -Depth 20 |
    Set-Content `
        -LiteralPath $JsonReportPath `
        -Encoding utf8

@($Problems) |
    ConvertTo-Json `
        -Depth 20 |
    Set-Content `
        -LiteralPath $ProblemsPath `
        -Encoding utf8

@($Files) |
    ConvertTo-Json `
        -Depth 20 |
    Set-Content `
        -LiteralPath $InventoryPath `
        -Encoding utf8

$SummaryLines = @(
    'E-ZZIO PROJECT TRUTH ENGINE'
    '============================'
    ''
    "Version              = $Version"
    "RunId                = $RunId"
    "ProjectRoot          = $ProjectRoot"
    "Mode                 = READ_ONLY"
    "SourceMutation       = FALSE"
    "Verdict              = $MachineVerdict"
    ''
    "FilesDiscovered      = $($Stats.FilesDiscovered)"
    "FilesAnalyzed        = $($Stats.FilesAnalyzed)"
    "FilesReadable        = $($Stats.FilesReadable)"
    "FilesUnreadable      = $($Stats.FilesUnreadable)"
    "EmptyFiles           = $($Stats.EmptyFiles)"
    "PowerShellFiles      = $($Stats.PowerShellFiles)"
    "PowerShellSyntaxPass = $($Stats.PowerShellSyntaxPass)"
    "PowerShellSyntaxFail = $($Stats.PowerShellSyntaxFail)"
    "JsonFiles            = $($Stats.JsonFiles)"
    "JsonSyntaxPass       = $($Stats.JsonSyntaxPass)"
    "JsonSyntaxFail       = $($Stats.JsonSyntaxFail)"
    "HashFailures         = $($Stats.HashFailures)"
    "ProblemsDetected     = $($Stats.ProblemsDetected)"
    ''
    "DurationSeconds      = $([Math]::Round($DurationSeconds, 3))"
    ''
    'REPORTS'
    "TruthReport          = $JsonReportPath"
    "Problems             = $ProblemsPath"
    "Inventory            = $InventoryPath"
)

$SummaryLines |
    Set-Content `
        -LiteralPath $SummaryPath `
        -Encoding utf8

# ============================================================================
# CONSOLE REPORT
# ============================================================================

Write-Host ''
Write-Host '============================================================' `
    -ForegroundColor Cyan
Write-Host ' E-ZZIO PROJECT TRUTH ANALYSIS COMPLETE' `
    -ForegroundColor Cyan
Write-Host '============================================================' `
    -ForegroundColor Cyan
Write-Host ''

Write-Host "FILES DISCOVERED : $($Stats.FilesDiscovered)"
Write-Host "FILES ANALYZED   : $($Stats.FilesAnalyzed)"
Write-Host "READABLE         : $($Stats.FilesReadable)"
Write-Host "UNREADABLE       : $($Stats.FilesUnreadable)"
Write-Host "EMPTY            : $($Stats.EmptyFiles)"
Write-Host ''

Write-Host "POWERSHELL FILES  : $($Stats.PowerShellFiles)"
Write-Host "PS SYNTAX PASS    : $($Stats.PowerShellSyntaxPass)"
Write-Host "PS SYNTAX FAIL    : $($Stats.PowerShellSyntaxFail)"
Write-Host ''

Write-Host "JSON FILES        : $($Stats.JsonFiles)"
Write-Host "JSON PASS         : $($Stats.JsonSyntaxPass)"
Write-Host "JSON FAIL         : $($Stats.JsonSyntaxFail)"
Write-Host ''

Write-Host "HASH FAILURES     : $($Stats.HashFailures)"
Write-Host "PROBLEMS DETECTED : $($Stats.ProblemsDetected)"
Write-Host ''

if ($MachineVerdict -eq 'TRUTH_ANALYSIS_COMPLETE') {

    Write-Host 'TRUTH STATUS : ANALYSIS COMPLETE' `
        -ForegroundColor Green
}
else {

    Write-Host 'TRUTH STATUS : FORENSIC_FAIL_CLOSED' `
        -ForegroundColor Red
}

Write-Host ''
Write-Host 'REPORTS:' -ForegroundColor DarkCyan
Write-Host "  $JsonReportPath"
Write-Host "  $ProblemsPath"
Write-Host "  $InventoryPath"
Write-Host "  $SummaryPath"
Write-Host ''

Write-Host 'IMPORTANT:' -ForegroundColor Yellow
Write-Host 'No E-ZZIO source file was modified.'
Write-Host 'This phase detects and records problems only.'
Write-Host ''
Write-Host '============================================================' `
    -ForegroundColor Cyan