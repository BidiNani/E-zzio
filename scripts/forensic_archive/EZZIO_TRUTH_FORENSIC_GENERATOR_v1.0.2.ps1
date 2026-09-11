# ============================================================================
# E-ZZIO — TRUTH FORENSIC GENERATOR v1.0.2
# ============================================================================
# MODE:
#   READ-ONLY
#   FAIL-CLOSED
#   NO EXECUTION
#   NO MUTATION OF PROJECT
#
# PURPOSE:
#   Générer un état forensic complet et reproductible du projet E-ZZIO.
#
# IMPORTANT:
#   - Aucun script découvert n'est exécuté.
#   - Aucun fichier projet n'est modifié.
#   - Les rapports sont écrits uniquement dans un nouveau dossier de run.
#   - Les erreurs du scanner deviennent elles-mêmes des findings.
#   - Aucun "CERTIFIED" déclaratif.
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

$GeneratorVersion = '1.0.2'
$StartedUtc = [DateTime]::UtcNow

if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) {
    throw "PROJECT_ROOT_NOT_FOUND: $ProjectRoot"
}

$ProjectRoot = [IO.Path]::GetFullPath($ProjectRoot)

$RunStamp = Get-Date -Format 'yyyyMMdd_HHmmss_fff'
$RandomPart = ([guid]::NewGuid().ToString('N')).Substring(0,12)

$RunId = "${RunStamp}_${RandomPart}"

$ReportRoot = Join-Path $ProjectRoot '_EZZIO_TRUTH_REPORTS'
$RunRoot = Join-Path $ReportRoot $RunId

$Paths = @{
    Root       = $RunRoot
    Inventory  = Join-Path $RunRoot 'INVENTORY'
    Findings   = Join-Path $RunRoot 'FINDINGS'
    Reports    = Join-Path $RunRoot 'REPORTS'
    Hashes     = Join-Path $RunRoot 'HASHES'
    Metrics    = Join-Path $RunRoot 'METRICS'
}

foreach ($Path in $Paths.Values) {
    [void](New-Item -ItemType Directory -Path $Path -Force)
}

$Findings = [System.Collections.Generic.List[object]]::new()
$Inventory = [System.Collections.Generic.List[object]]::new()
$HashRecords = [System.Collections.Generic.List[object]]::new()

# ============================================================================
# HELPERS
# ============================================================================

function Add-Finding {
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

    $Finding = [PSCustomObject]@{
        Severity = $Severity
        Code     = $Code
        Path     = $Path
        Message  = $Message
        Evidence = $Evidence
    }

    [void]$Findings.Add($Finding)
}

function Get-RelativePathSafe {
    param(
        [Parameter(Mandatory)]
        [string]$FullPath
    )

    try {
        return [IO.Path]::GetRelativePath($ProjectRoot, $FullPath)
    }
    catch {
        return $FullPath
    }
}

function Get-SafeExtension {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    $Extension = [IO.Path]::GetExtension($Path)

    if ([string]::IsNullOrWhiteSpace($Extension)) {
        return ''
    }

    return $Extension.ToLowerInvariant()
}

function Get-FileCategory {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    $Extension = Get-SafeExtension -Path $Path

    switch ($Extension) {
        '.ps1'    { return 'POWERSHELL' }
        '.psm1'   { return 'POWERSHELL_MODULE' }
        '.psd1'   { return 'POWERSHELL_DATA' }
        '.json'   { return 'JSON' }
        '.jsonl'  { return 'JSONL' }
        '.db'     { return 'SQLITE_OR_DB' }
        '.sqlite' { return 'SQLITE_OR_DB' }
        '.sqlite3'{ return 'SQLITE_OR_DB' }
        default   { return 'OTHER' }
    }
}

function Get-FileHashSafe {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    try {
        return (Get-FileHash -LiteralPath $Path -Algorithm SHA256 -ErrorAction Stop).Hash
    }
    catch {
        Add-Finding `
            -Severity 'ERROR' `
            -Code 'HASH_READ_FAILURE' `
            -Path (Get-RelativePathSafe $Path) `
            -Message $_.Exception.Message

        return $null
    }
}

function Test-PowerShellSyntax {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    $Relative = Get-RelativePathSafe $Path

    try {
        $Tokens = $null
        $ParseErrors = $null

        $Ast = [System.Management.Automation.Language.Parser]::ParseFile(
            $Path,
            [ref]$Tokens,
            [ref]$ParseErrors
        )

        if ($null -ne $ParseErrors -and $ParseErrors.Count -gt 0) {

            foreach ($ErrorRecord in $ParseErrors) {

                $ExtentText = ''

                try {
                    if ($null -ne $ErrorRecord.Extent) {
                        $ExtentText = [string]$ErrorRecord.Extent.Text
                    }
                }
                catch {
                    $ExtentText = ''
                }

                $Evidence = [PSCustomObject]@{
                    ErrorId  = [string]$ErrorRecord.ErrorId
                    Message  = [string]$ErrorRecord.Message
                    Extent   = $ExtentText
                    Line     = if ($null -ne $ErrorRecord.Extent) {
                        $ErrorRecord.Extent.StartLineNumber
                    } else {
                        $null
                    }
                    Column   = if ($null -ne $ErrorRecord.Extent) {
                        $ErrorRecord.Extent.StartColumnNumber
                    } else {
                        $null
                    }
                }

                Add-Finding `
                    -Severity 'CRITICAL' `
                    -Code 'POWERSHELL_SYNTAX_ERROR' `
                    -Path $Relative `
                    -Message ([string]$ErrorRecord.Message) `
                    -Evidence $Evidence
            }

            return [PSCustomObject]@{
                Path       = $Relative
                Parseable  = $false
                ErrorCount = $ParseErrors.Count
            }
        }

        return [PSCustomObject]@{
            Path       = $Relative
            Parseable  = $true
            ErrorCount = 0
        }
    }
    catch {
        Add-Finding `
            -Severity 'CRITICAL' `
            -Code 'POWERSHELL_PARSER_FAILURE' `
            -Path $Relative `
            -Message $_.Exception.Message

        return [PSCustomObject]@{
            Path       = $Relative
            Parseable  = $false
            ErrorCount = 1
        }
    }
}

function Test-JsonSyntax {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    $Relative = Get-RelativePathSafe $Path

    try {
        $Raw = Get-Content -LiteralPath $Path -Raw -ErrorAction Stop

        if ([string]::IsNullOrWhiteSpace($Raw)) {
            Add-Finding `
                -Severity 'WARNING' `
                -Code 'JSON_EMPTY_FILE' `
                -Path $Relative `
                -Message 'JSON file is empty.'

            return [PSCustomObject]@{
                Path      = $Relative
                Parseable = $false
                Empty     = $true
            }
        }

        [void]($Raw | ConvertFrom-Json -ErrorAction Stop)

        return [PSCustomObject]@{
            Path      = $Relative
            Parseable = $true
            Empty     = $false
        }
    }
    catch {
        Add-Finding `
            -Severity 'CRITICAL' `
            -Code 'JSON_SYNTAX_ERROR' `
            -Path $Relative `
            -Message $_.Exception.Message

        return [PSCustomObject]@{
            Path      = $Relative
            Parseable = $false
            Empty     = $false
        }
    }
}

# ============================================================================
# HEADER
# ============================================================================

Write-Host ''
Write-Host '============================================================================' -ForegroundColor Cyan
Write-Host ' E-ZZIO — TRUTH FORENSIC GENERATOR v1.0.2' -ForegroundColor Cyan
Write-Host '============================================================================' -ForegroundColor Cyan
Write-Host ''
Write-Host "PROJECT : $ProjectRoot"
Write-Host "RUN ID  : $RunId"
Write-Host 'MODE    : READ-ONLY / FAIL-CLOSED / NO EXECUTION'
Write-Host ''

# ============================================================================
# MANIFEST
# ============================================================================

$Manifest = [PSCustomObject]@{
    Generator       = 'EZZIO_TRUTH_FORENSIC_GENERATOR'
    Version         = $GeneratorVersion
    RunId           = $RunId
    ProjectRoot     = $ProjectRoot
    StartedUtc      = $StartedUtc.ToString('o')
    PowerShell      = $PSVersionTable.PSVersion.ToString()
    OS              = [Environment]::OSVersion.VersionString
    ReadOnly        = $true
    FailClosed      = $true
    ExecutionOfCode = $false
}

$Manifest |
    ConvertTo-Json -Depth 20 |
    Set-Content -LiteralPath (Join-Path $Paths.Root 'RUN_MANIFEST.json') -Encoding UTF8

# ============================================================================
# [1/8] DISCOVERY
# ============================================================================

Write-Host '[1/8] Découverte des fichiers...' -ForegroundColor Yellow

try {
    $Files = @(
        Get-ChildItem `
            -LiteralPath $ProjectRoot `
            -File `
            -Recurse `
            -Force `
            -ErrorAction Stop |
        Where-Object {
            $_.FullName -notlike "$ReportRoot\*"
        }
    )
}
catch {
    Add-Finding `
        -Severity 'CRITICAL' `
        -Code 'DISCOVERY_FAILURE' `
        -Message $_.Exception.Message

    $Files = @()
}

Write-Host "      Fichiers découverts : $($Files.Count)"

# ============================================================================
# [2/8] INVENTORY + HASH
# ============================================================================

Write-Host ''
Write-Host '[2/8] Inventaire et SHA-256...' -ForegroundColor Yellow

$Index = 0

foreach ($File in $Files) {

    $Index++

    if (($Index % 250) -eq 0 -or $Index -eq 1) {
        Write-Host "      [$Index/$($Files.Count)] $($File.Name)"
    }

    $Relative = Get-RelativePathSafe $File.FullName
    $Category = Get-FileCategory $File.FullName
    $Extension = Get-SafeExtension $File.FullName

    $Hash = Get-FileHashSafe $File.FullName

    $Record = [PSCustomObject]@{
        Path         = $Relative
        FullPathHash = $Hash
        Name         = $File.Name
        Extension    = $Extension
        Category     = $Category
        LengthBytes  = $File.Length
        LastWriteUtc = $File.LastWriteTimeUtc.ToString('o')
    }

    [void]$Inventory.Add($Record)

    $HashRecord = [PSCustomObject]@{
        Path       = $Relative
        SHA256     = $Hash
        LengthByte = $File.Length
    }

    [void]$HashRecords.Add($HashRecord)
}

$Inventory |
    ConvertTo-Json -Depth 10 |
    Set-Content `
        -LiteralPath (Join-Path $Paths.Inventory 'EZZIO_INVENTORY.json') `
        -Encoding UTF8

$HashRecords |
    Export-Csv `
        -LiteralPath (Join-Path $Paths.Hashes 'EZZIO_SHA256.csv') `
        -NoTypeInformation `
        -Encoding UTF8

# ============================================================================
# [3/8] POWERSHELL SYNTAX
# ============================================================================

Write-Host ''
Write-Host '[3/8] Analyse syntaxique PowerShell...' -ForegroundColor Yellow

$PowerShellFiles = @(
    $Files |
    Where-Object {
        $Ext = Get-SafeExtension $_.FullName
        $Ext -in @('.ps1','.psm1','.psd1')
    }
)

$PsResults = [System.Collections.Generic.List[object]]::new()

$Index = 0

foreach ($File in $PowerShellFiles) {

    $Index++

    Write-Host "      [$Index/$($PowerShellFiles.Count)] $($File.Name)"

    $Result = Test-PowerShellSyntax -Path $File.FullName

    [void]$PsResults.Add($Result)
}

$PsResults |
    ConvertTo-Json -Depth 20 |
    Set-Content `
        -LiteralPath (Join-Path $Paths.Findings 'POWERSHELL_SYNTAX.json') `
        -Encoding UTF8

# ============================================================================
# [4/8] JSON SYNTAX
# ============================================================================

Write-Host ''
Write-Host '[4/8] Analyse syntaxique JSON...' -ForegroundColor Yellow

$JsonFiles = @(
    $Files |
    Where-Object {
        (Get-SafeExtension $_.FullName) -eq '.json'
    }
)

$JsonResults = [System.Collections.Generic.List[object]]::new()

$Index = 0

foreach ($File in $JsonFiles) {

    $Index++

    Write-Host "      [$Index/$($JsonFiles.Count)] $($File.Name)"

    $Result = Test-JsonSyntax -Path $File.FullName

    [void]$JsonResults.Add($Result)
}

$JsonResults |
    ConvertTo-Json -Depth 20 |
    Set-Content `
        -LiteralPath (Join-Path $Paths.Findings 'JSON_SYNTAX.json') `
        -Encoding UTF8

# ============================================================================
# [5/8] STATISTICS
# ============================================================================

Write-Host ''
Write-Host '[5/8] Calcul des statistiques...' -ForegroundColor Yellow

$ByCategory = @{}

foreach ($Item in $Inventory) {

    $Key = [string]$Item.Category

    if (-not $ByCategory.ContainsKey($Key)) {
        $ByCategory[$Key] = 0
    }

    $ByCategory[$Key]++
}

$ByExtension = @{}

foreach ($Item in $Inventory) {

    $Key = [string]$Item.Extension

    if ([string]::IsNullOrWhiteSpace($Key)) {
        $Key = '[NO_EXTENSION]'
    }

    if (-not $ByExtension.ContainsKey($Key)) {
        $ByExtension[$Key] = 0
    }

    $ByExtension[$Key]++
}

$TotalBytes = [int64]0

foreach ($Item in $Inventory) {
    $TotalBytes += [int64]$Item.LengthBytes
}

$Statistics = [PSCustomObject]@{
    RunId              = $RunId
    TotalFiles         = $Inventory.Count
    TotalBytes         = $TotalBytes
    PowerShellFiles    = $PowerShellFiles.Count
    JsonFiles          = $JsonFiles.Count
    FindingsTotal      = $Findings.Count
    CriticalFindings   = @($Findings | Where-Object Severity -eq 'CRITICAL').Count
    ErrorFindings      = @($Findings | Where-Object Severity -eq 'ERROR').Count
    WarningFindings    = @($Findings | Where-Object Severity -eq 'WARNING').Count
    Categories         = $ByCategory
    Extensions         = $ByExtension
}

$Statistics |
    ConvertTo-Json -Depth 30 |
    Set-Content `
        -LiteralPath (Join-Path $Paths.Metrics 'STATISTICS.json') `
        -Encoding UTF8

# ============================================================================
# [6/8] FINDINGS
# ============================================================================

Write-Host ''
Write-Host '[6/8] Construction des findings forensic...' -ForegroundColor Yellow

$Critical = @(
    $Findings |
    Where-Object {
        [string]$_.Severity -eq 'CRITICAL'
    }
)

$Errors = @(
    $Findings |
    Where-Object {
        [string]$_.Severity -eq 'ERROR'
    }
)

$Warnings = @(
    $Findings |
    Where-Object {
        [string]$_.Severity -eq 'WARNING'
    }
)

$FindingsPath = Join-Path $Paths.Findings 'EZZIO_TRUTH_FORENSIC_FINDINGS.json'

$Findings |
    ConvertTo-Json -Depth 40 |
    Set-Content -LiteralPath $FindingsPath -Encoding UTF8

$Findings |
    Select-Object Severity,Code,Path,Message |
    Export-Csv `
        -LiteralPath (Join-Path $Paths.Findings 'EZZIO_TRUTH_FORENSIC_FINDINGS.csv') `
        -NoTypeInformation `
        -Encoding UTF8

# ============================================================================
# [7/8] VERDICT
# ============================================================================

Write-Host ''
Write-Host '[7/8] Calcul du verdict...' -ForegroundColor Yellow

$Verdict = 'CERTIFIED'

if ($Critical.Count -gt 0) {
    $Verdict = 'FAIL'
}
elseif ($Errors.Count -gt 0) {
    $Verdict = 'FAIL'
}

$CompletedUtc = [DateTime]::UtcNow

$VerdictObject = [PSCustomObject]@{
    GeneratorVersion = $GeneratorVersion
    RunId             = $RunId
    Verdict           = $Verdict
    Certified         = ($Verdict -eq 'CERTIFIED')
    TotalFindings     = $Findings.Count
    Critical          = $Critical.Count
    Errors            = $Errors.Count
    Warnings          = $Warnings.Count
    StartedUtc        = $StartedUtc.ToString('o')
    CompletedUtc      = $CompletedUtc.ToString('o')
    DurationSeconds   = ($CompletedUtc - $StartedUtc).TotalSeconds
    Rule              = 'CERTIFIED iff Critical == 0 AND Errors == 0'
}

$VerdictObject |
    ConvertTo-Json -Depth 20 |
    Set-Content `
        -LiteralPath (Join-Path $Paths.Root 'VERDICT.json') `
        -Encoding UTF8

# ============================================================================
# [8/8] RAPPORT FINAL
# ============================================================================

Write-Host ''
Write-Host '[8/8] Génération du rapport final...' -ForegroundColor Yellow

$ReportLines = [System.Collections.Generic.List[string]]::new()

[void]$ReportLines.Add('============================================================================')
[void]$ReportLines.Add('E-ZZIO — TRUTH FORENSIC REPORT')
[void]$ReportLines.Add('============================================================================')
[void]$ReportLines.Add('')
[void]$ReportLines.Add("Generator Version : $GeneratorVersion")
[void]$ReportLines.Add("Run ID            : $RunId")
[void]$ReportLines.Add("Project           : $ProjectRoot")
[void]$ReportLines.Add("Mode              : READ-ONLY / FAIL-CLOSED / NO EXECUTION")
[void]$ReportLines.Add('')
[void]$ReportLines.Add('-------------------- INVENTORY --------------------------------------------')
[void]$ReportLines.Add("Total files       : $($Inventory.Count)")
[void]$ReportLines.Add("Total bytes       : $TotalBytes")
[void]$ReportLines.Add("PowerShell files  : $($PowerShellFiles.Count)")
[void]$ReportLines.Add("JSON files        : $($JsonFiles.Count)")
[void]$ReportLines.Add('')
[void]$ReportLines.Add('-------------------- FINDINGS ---------------------------------------------')
[void]$ReportLines.Add("Total findings    : $($Findings.Count)")
[void]$ReportLines.Add("CRITICAL          : $($Critical.Count)")
[void]$ReportLines.Add("ERROR             : $($Errors.Count)")
[void]$ReportLines.Add("WARNING           : $($Warnings.Count)")
[void]$ReportLines.Add('')
[void]$ReportLines.Add('-------------------- VERDICT ----------------------------------------------')
[void]$ReportLines.Add("VERDICT           : $Verdict")
[void]$ReportLines.Add("CERTIFIED         : $($VerdictObject.Certified)")
[void]$ReportLines.Add('')
[void]$ReportLines.Add('Rule: CERTIFIED iff Critical == 0 AND Errors == 0')
[void]$ReportLines.Add('')
[void]$ReportLines.Add('-------------------- CRITICAL FINDINGS ------------------------------------')

if ($Critical.Count -eq 0) {
    [void]$ReportLines.Add('NONE')
}
else {
    foreach ($Finding in $Critical) {
        [void]$ReportLines.Add(
            "[CRITICAL] $($Finding.Code) | $($Finding.Path) | $($Finding.Message)"
        )
    }
}

[void]$ReportLines.Add('')
[void]$ReportLines.Add('-------------------- OUTPUTS ----------------------------------------------')
[void]$ReportLines.Add((Join-Path $Paths.Root 'RUN_MANIFEST.json'))
[void]$ReportLines.Add((Join-Path $Paths.Root 'VERDICT.json'))
[void]$ReportLines.Add((Join-Path $Paths.Inventory 'EZZIO_INVENTORY.json'))
[void]$ReportLines.Add((Join-Path $Paths.Hashes 'EZZIO_SHA256.csv'))
[void]$ReportLines.Add((Join-Path $Paths.Findings 'POWERSHELL_SYNTAX.json'))
[void]$ReportLines.Add((Join-Path $Paths.Findings 'JSON_SYNTAX.json'))
[void]$ReportLines.Add((Join-Path $Paths.Findings 'EZZIO_TRUTH_FORENSIC_FINDINGS.json'))
[void]$ReportLines.Add((Join-Path $Paths.Findings 'EZZIO_TRUTH_FORENSIC_FINDINGS.csv'))
[void]$ReportLines.Add((Join-Path $Paths.Metrics 'STATISTICS.json'))

$ReportPath = Join-Path $Paths.Reports 'EZZIO_TRUTH_FORENSIC_REPORT.txt'

$ReportLines |
    Set-Content -LiteralPath $ReportPath -Encoding UTF8

# ============================================================================
# FINAL CONSOLE
# ============================================================================

Write-Host ''
Write-Host '============================================================================' -ForegroundColor Cyan
Write-Host ' E-ZZIO — TRUTH FORENSIC COMPLETE' -ForegroundColor Cyan
Write-Host '============================================================================' -ForegroundColor Cyan
Write-Host ''
Write-Host "RUN ID       : $RunId"
Write-Host "FILES        : $($Inventory.Count)"
Write-Host "FINDINGS     : $($Findings.Count)"
Write-Host "CRITICAL     : $($Critical.Count)"
Write-Host "ERROR        : $($Errors.Count)"
Write-Host "WARNING      : $($Warnings.Count)"
Write-Host ''

if ($Verdict -eq 'CERTIFIED') {
    Write-Host 'VERDICT      : CERTIFIED' -ForegroundColor Green
}
else {
    Write-Host 'VERDICT      : FAIL' -ForegroundColor Red
}

Write-Host ''
Write-Host "REPORT ROOT  : $RunRoot"
Write-Host "FINDINGS     : $FindingsPath"
Write-Host "VERDICT      : $(Join-Path $Paths.Root 'VERDICT.json')"
Write-Host "REPORT       : $ReportPath"
Write-Host ''

if ($Verdict -ne 'CERTIFIED') {
    Write-Host 'FAIL-CLOSED : le projet ne peut pas être déclaré CERTIFIED.' -ForegroundColor Red
}
else {
    Write-Host 'QUALITY GATE : aucun CRITICAL/ERROR détecté.' -ForegroundColor Green
}

Write-Host ''

exit 0
