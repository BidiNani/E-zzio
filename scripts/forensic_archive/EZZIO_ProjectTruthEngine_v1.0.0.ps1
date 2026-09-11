# ============================================================================
# E-ZZIO — PROJECT TRUTH ENGINE
# Version : 1.0.0
#
# Mode:
#   READ-ONLY SOURCE ANALYSIS
#
# Purpose:
#   Establish a forensic, machine-readable truth state of the E-ZZIO project.
#
# Guarantees:
#   - source files are never modified
#   - every discovered file receives a SHA-256 identity
#   - unreadable files are explicitly recorded
#   - PowerShell files receive syntax analysis
#   - every run has a unique RunId
#   - results are written as JSON + JSONL + TXT
#
# IMPORTANT:
#   This version detects.
#   This version does NOT repair.
# ============================================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ============================================================================
# CONFIGURATION
# ============================================================================

$ProjectRoot = 'G:\AI\E-zzio'

if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) {
    throw "PROJECT_ROOT_NOT_FOUND: $ProjectRoot"
}

$RunId = (
    Get-Date -Format 'yyyyMMdd_HHmmss_fff'
) + '_' + (
    [guid]::NewGuid().ToString('N')
)

$RunUtc = [DateTime]::UtcNow.ToString(
    'o',
    [Globalization.CultureInfo]::InvariantCulture
)

$OutputRoot = Join-Path `
    $ProjectRoot `
    '.ezzio\truth'

$RunRoot = Join-Path `
    $OutputRoot `
    $RunId

New-Item `
    -ItemType Directory `
    -Path $RunRoot `
    -Force |
    Out-Null

$StatePath = Join-Path `
    $RunRoot `
    'PROJECT_TRUTH.json'

$FactsPath = Join-Path `
    $RunRoot `
    'PROJECT_FACTS.jsonl'

$ReportPath = Join-Path `
    $RunRoot `
    'PROJECT_TRUTH_REPORT.txt'

# ============================================================================
# COUNTERS
# ============================================================================

$FilesDiscovered = 0
$FilesHashed = 0
$FilesRead = 0
$FilesUnreadable = 0
$PowerShellFiles = 0
$PowerShellSyntaxPass = 0
$PowerShellSyntaxFail = 0
$ProblemsDetected = 0

# ============================================================================
# COLLECTIONS
# ============================================================================

$Files = [System.Collections.Generic.List[object]]::new()
$Facts = [System.Collections.Generic.List[object]]::new()
$Problems = [System.Collections.Generic.List[object]]::new()

# ============================================================================
# HELPERS
# ============================================================================

function Add-Fact {
    param(
        [Parameter(Mandatory)]
        [string]$FactType,

        [Parameter(Mandatory)]
        [hashtable]$Data
    )

    $Fact = [ordered]@{
        RunId    = $RunId
        FactType = $FactType
        TimestampUtc = [DateTime]::UtcNow.ToString(
            'o',
            [Globalization.CultureInfo]::InvariantCulture
        )
    }

    foreach ($Key in $Data.Keys) {
        $Fact[$Key] = $Data[$Key]
    }

    $Facts.Add([pscustomobject]$Fact)
}

function Add-Problem {
    param(
        [Parameter(Mandatory)]
        [string]$ProblemType,

        [Parameter(Mandatory)]
        [string]$Path,

        [Parameter(Mandatory)]
        [string]$Evidence,

        [Parameter(Mandatory)]
        [string]$Severity
    )

    $Problem = [ordered]@{
        ProblemId = 'P-' + (
            '{0:D6}' -f ($Problems.Count + 1)
        )

        RunId = $RunId
        ProblemType = $ProblemType
        Path = $Path
        Severity = $Severity
        Evidence = $Evidence
        DetectedUtc = [DateTime]::UtcNow.ToString(
            'o',
            [Globalization.CultureInfo]::InvariantCulture
        )
    }

    $Problems.Add([pscustomobject]$Problem)

    Add-Fact `
        -FactType 'PROBLEM' `
        -Data $Problem

    $script:ProblemsDetected++
}

function Get-RelativeProjectPath {
    param(
        [Parameter(Mandatory)]
        [string]$FullPath
    )

    $Root = $ProjectRoot.TrimEnd(
        [System.IO.Path]::DirectorySeparatorChar,
        [System.IO.Path]::AltDirectorySeparatorChar
    )

    if ($FullPath.StartsWith(
        $Root,
        [System.StringComparison]::OrdinalIgnoreCase
    )) {
        return $FullPath.Substring($Root.Length).TrimStart(
            [System.IO.Path]::DirectorySeparatorChar,
            [System.IO.Path]::AltDirectorySeparatorChar
        )
    }

    return $FullPath
}

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
        return $null
    }
}

function Get-PowerShellSyntaxState {
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

        $ErrorDetails = @(
            $Errors |
                ForEach-Object {
                    [ordered]@{
                        Message = [string]$_.Message
                        Extent = if ($null -ne $_.Extent) {
                            [ordered]@{
                                StartLineNumber =
                                    $_.Extent.StartLineNumber

                                StartColumnNumber =
                                    $_.Extent.StartColumnNumber

                                EndLineNumber =
                                    $_.Extent.EndLineNumber

                                EndColumnNumber =
                                    $_.Extent.EndColumnNumber
                            }
                        }
                        else {
                            $null
                        }
                    }
                }
        )

        return [pscustomobject]@{
            Status = 'FAIL'
            ErrorCount = $ErrorCount
            Errors = $ErrorDetails
        }
    }
    catch {
        return [pscustomobject]@{
            Status = 'ERROR'
            ErrorCount = 1
            Errors = @(
                [ordered]@{
                    Message = $_.Exception.Message
                }
            )
        }
    }
}

# ============================================================================
# HEADER
# ============================================================================

Write-Host ''
Write-Host '============================================================' `
    -ForegroundColor Cyan

Write-Host ' E-ZZIO — PROJECT TRUTH ENGINE v1.0.0' `
    -ForegroundColor Cyan

Write-Host '============================================================' `
    -ForegroundColor Cyan

Write-Host ''
Write-Host "PROJECT ROOT : $ProjectRoot"
Write-Host "RUN ID       : $RunId"
Write-Host "RUN UTC      : $RunUtc"
Write-Host "MODE         : READ-ONLY"
Write-Host ''

# ============================================================================
# ROOT FACT
# ============================================================================

Add-Fact `
    -FactType 'PROJECT_ROOT' `
    -Data @{
        Path = $ProjectRoot
    }

# ============================================================================
# FILE DISCOVERY
# ============================================================================

Write-Host 'DISCOVERY' -ForegroundColor DarkCyan
Write-Host '------------------------------------------------------------'

$Discovered = @(
    Get-ChildItem `
        -LiteralPath $ProjectRoot `
        -File `
        -Recurse `
        -Force `
        -ErrorAction SilentlyContinue |
        Where-Object {
            $_.FullName -notlike "$OutputRoot\*"
        } |
        Sort-Object FullName
)

$FilesDiscovered = $Discovered.Count

Write-Host "Files discovered : $FilesDiscovered"

# ============================================================================
# FILE ANALYSIS
# ============================================================================

foreach ($Item in $Discovered) {

    $RelativePath = Get-RelativeProjectPath `
        -FullPath $Item.FullName

    $Extension = $Item.Extension.ToLowerInvariant()

    $Hash = Get-SafeSha256 `
        -Path $Item.FullName

    if ($null -ne $Hash) {
        $FilesHashed++
    }
    else {
        Add-Problem `
            -ProblemType 'HASH_FAILURE' `
            -Path $RelativePath `
            -Severity 'HIGH' `
            -Evidence 'SHA-256 calculation failed.'
    }

    $ReadStatus = 'UNKNOWN'
    $ReadError = $null
    $ContentBytes = 0

    try {

        $Stream = [System.IO.File]::Open(
            $Item.FullName,
            [System.IO.FileMode]::Open,
            [System.IO.FileAccess]::Read,
            [System.IO.FileShare]::ReadWrite
        )

        try {
            $ContentBytes = $Stream.Length
            $ReadStatus = 'READABLE'
            $FilesRead++
        }
        finally {
            $Stream.Dispose()
        }
    }
    catch {

        $ReadStatus = 'UNREADABLE'
        $ReadError = $_.Exception.Message
        $FilesUnreadable++

        Add-Problem `
            -ProblemType 'UNREADABLE_FILE' `
            -Path $RelativePath `
            -Severity 'HIGH' `
            -Evidence $ReadError
    }

    $Syntax = $null

    if ($Extension -eq '.ps1') {

        $PowerShellFiles++

        if ($ReadStatus -eq 'READABLE') {

            $Syntax = Get-PowerShellSyntaxState `
                -Path $Item.FullName

            if ($Syntax.Status -eq 'PASS') {
                $PowerShellSyntaxPass++
            }
            elseif ($Syntax.Status -eq 'FAIL') {
                $PowerShellSyntaxFail++

                Add-Problem `
                    -ProblemType 'POWERSHELL_SYNTAX_ERROR' `
                    -Path $RelativePath `
                    -Severity 'HIGH' `
                    -Evidence (
                        (
                            $Syntax.Errors |
                                ForEach-Object {
                                    $_.Message
                                }
                        ) -join ' | '
                    )
            }
            else {
                $PowerShellSyntaxFail++

                Add-Problem `
                    -ProblemType 'POWERSHELL_PARSER_ERROR' `
                    -Path $RelativePath `
                    -Severity 'HIGH' `
                    -Evidence (
                        (
                            $Syntax.Errors |
                                ForEach-Object {
                                    $_.Message
                                }
                        ) -join ' | '
                    )
            }
        }
    }

    $FileRecord = [ordered]@{
        RunId = $RunId
        Path = $RelativePath
        FullPath = $Item.FullName
        Extension = $Extension
        Name = $Item.Name
        Directory = $Item.DirectoryName
        LengthBytes = $Item.Length
        HashAlgorithm = 'SHA256'
        SHA256 = $Hash
        LastWriteTimeUtc = $Item.LastWriteTimeUtc.ToString(
            'o',
            [Globalization.CultureInfo]::InvariantCulture
        )
        ReadStatus = $ReadStatus
        ReadError = $ReadError
        ContentBytes = $ContentBytes
        PowerShellSyntax = $Syntax
    }

    $Files.Add([pscustomobject]$FileRecord)

    Add-Fact `
        -FactType 'FILE' `
        -Data @{
            Path = $RelativePath
            FullPath = $Item.FullName
            Extension = $Extension
            LengthBytes = $Item.Length
            SHA256 = $Hash
            ReadStatus = $ReadStatus
        }
}

# ============================================================================
# PROJECT HASH
# ============================================================================

$CanonicalFileList = @(
    $Files |
        Sort-Object Path |
        ForEach-Object {
            '{0}|{1}|{2}' -f
                $_.Path,
                $_.LengthBytes,
                $_.SHA256
        }
)

$CanonicalText = $CanonicalFileList -join "`n"

$ProjectHashBytes = [System.Text.Encoding]::UTF8.GetBytes($CanonicalText)

$ProjectSha256 = (
    [System.Security.Cryptography.SHA256]::Create()
).ComputeHash($ProjectHashBytes)

$ProjectIdentityHash = (
    -join (
        $ProjectSha256 |
            ForEach-Object {
                $_.ToString('x2')
            }
    )
)

Add-Fact `
    -FactType 'PROJECT_IDENTITY' `
    -Data @{
        ProjectSha256 = $ProjectIdentityHash
        FileCount = $Files.Count
    }

# ============================================================================
# FINAL STATE
# ============================================================================

$State = [ordered]@{

    Product = 'E-ZZIO'

    Component = 'Project Truth Engine'

    Version = '1.0.0'

    Mode = 'READ_ONLY'

    RunId = $RunId

    RunUtc = $RunUtc

    ProjectRoot = $ProjectRoot

    ProjectIdentitySha256 = $ProjectIdentityHash

    Statistics = [ordered]@{
        FilesDiscovered = $FilesDiscovered
        FilesHashed = $FilesHashed
        FilesRead = $FilesRead
        FilesUnreadable = $FilesUnreadable
        PowerShellFiles = $PowerShellFiles
        PowerShellSyntaxPass = $PowerShellSyntaxPass
        PowerShellSyntaxFail = $PowerShellSyntaxFail
        ProblemsDetected = $ProblemsDetected
    }

    Files = @(
        $Files
    )

    Problems = @(
        $Problems
    )

    Guarantees = [ordered]@{
        SourceMutation = $false
        HashingAttempted = $true
        DeterministicFileOrdering = $true
        ProblemsExplicitlyRecorded = $true
        RepairPerformed = $false
    }
}

# ============================================================================
# WRITE JSON
# ============================================================================

$StateJson = $State |
    ConvertTo-Json `
        -Depth 30

[System.IO.File]::WriteAllText(
    $StatePath,
    $StateJson,
    [System.Text.UTF8Encoding]::new($false)
)

# ============================================================================
# WRITE JSONL
# ============================================================================

$FactsLines = foreach ($Fact in $Facts) {
    $Fact |
        ConvertTo-Json `
            -Compress `
            -Depth 20
}

[System.IO.File]::WriteAllLines(
    $FactsPath,
    $FactsLines,
    [System.Text.UTF8Encoding]::new($false)
)

# ============================================================================
# HUMAN REPORT
# ============================================================================

$Report = [System.Collections.Generic.List[string]]::new()

$Report.Add('E-ZZIO — PROJECT TRUTH ENGINE v1.0.0')
$Report.Add('============================================================')
$Report.Add('')
$Report.Add("RunId       : $RunId")
$Report.Add("RunUtc      : $RunUtc")
$Report.Add("ProjectRoot : $ProjectRoot")
$Report.Add("Mode        : READ_ONLY")
$Report.Add('')
$Report.Add('STATISTICS')
$Report.Add('------------------------------------------------------------')
$Report.Add("Files discovered       : $FilesDiscovered")
$Report.Add("Files hashed           : $FilesHashed")
$Report.Add("Files readable         : $FilesRead")
$Report.Add("Files unreadable       : $FilesUnreadable")
$Report.Add("PowerShell files       : $PowerShellFiles")
$Report.Add("PowerShell syntax PASS : $PowerShellSyntaxPass")
$Report.Add("PowerShell syntax FAIL : $PowerShellSyntaxFail")
$Report.Add("Problems detected      : $ProblemsDetected")
$Report.Add('')
$Report.Add("PROJECT IDENTITY SHA256")
$Report.Add('------------------------------------------------------------')
$Report.Add($ProjectIdentityHash)
$Report.Add('')

if ($Problems.Count -eq 0) {

    $Report.Add('FORENSIC STATUS')
    $Report.Add('------------------------------------------------------------')
    $Report.Add('NO PROBLEMS DETECTED')
}
else {

    $Report.Add('FORENSIC STATUS')
    $Report.Add('------------------------------------------------------------')
    $Report.Add('PROBLEMS DETECTED')
    $Report.Add('')

    foreach ($Problem in $Problems) {

        $Report.Add(
            '[{0}] {1} | {2} | {3}' -f
                $Problem.ProblemId,
                $Problem.Severity,
                $Problem.ProblemType,
                $Problem.Path
        )

        $Report.Add(
            "  Evidence: $($Problem.Evidence)"
        )
    }
}

$Report.Add('')
$Report.Add('OUTPUT')
$Report.Add('------------------------------------------------------------')
$Report.Add("JSON  : $StatePath")
$Report.Add("JSONL : $FactsPath")
$Report.Add("TXT   : $ReportPath")
$Report.Add('')
$Report.Add('REPAIR PERFORMED : NO')
$Report.Add('SOURCE MUTATION  : NO')

[System.IO.File]::WriteAllLines(
    $ReportPath,
    $Report,
    [System.Text.UTF8Encoding]::new($false)
)

# ============================================================================
# CONSOLE SUMMARY
# ============================================================================

Write-Host ''
Write-Host '============================================================' `
    -ForegroundColor Cyan

Write-Host ' PROJECT TRUTH COMPLETE' `
    -ForegroundColor Cyan

Write-Host '============================================================' `
    -ForegroundColor Cyan

Write-Host ''
Write-Host "FILES DISCOVERED : $FilesDiscovered"
Write-Host "FILES HASHED     : $FilesHashed"
Write-Host "FILES READ       : $FilesRead"
Write-Host "UNREADABLE       : $FilesUnreadable"
Write-Host "PS1 FILES        : $PowerShellFiles"
Write-Host "PS1 SYNTAX PASS  : $PowerShellSyntaxPass"
Write-Host "PS1 SYNTAX FAIL  : $PowerShellSyntaxFail"
Write-Host "PROBLEMS         : $ProblemsDetected"
Write-Host ''
Write-Host "PROJECT SHA256   : $ProjectIdentityHash"
Write-Host ''
Write-Host "JSON             : $StatePath"
Write-Host "JSONL            : $FactsPath"
Write-Host "REPORT           : $ReportPath"
Write-Host ''

if ($ProblemsDetected -eq 0) {

    Write-Host 'FORENSIC STATUS  : CLEAN' `
        -ForegroundColor Green
}
else {

    Write-Host 'FORENSIC STATUS  : PROBLEMS DETECTED' `
        -ForegroundColor Yellow
}

Write-Host 'REPAIR           : NOT PERFORMED' `
    -ForegroundColor DarkGray

Write-Host 'SOURCE MUTATION  : NONE' `
    -ForegroundColor Green

Write-Host ''