# ============================================================================
# E-ZZIO — TRUTH PROBLEM FORENSIC TRIAGE
# Version : 1.0.2
#
# MODE
#   READ-ONLY / FORENSIC / FAIL-CLOSED
#
# PURPOSE
#   Analyse déterministe du rapport de problèmes produit par
#   EZZIO_ProjectTruthEngine.
#
# SAFETY
#   - Aucun fichier source E-ZZIO modifié.
#   - Aucun fichier source supprimé.
#   - Aucun fichier source réécrit.
#   - Aucun script découvert exécuté.
#   - Aucun correctif appliqué.
#   - Seuls les rapports de triage sont créés.
#
# HARDENING 1.0.2
#   - Accès aux propriétés totalement défensif sous StrictMode.
#   - ErrorId absent autorisé.
#   - Message absent autorisé.
#   - Extent absent autorisé.
#   - Type absent détecté explicitement.
#   - Path absent détecté explicitement.
#   - Rapport source validé avant analyse.
#   - Aucun appel direct fragile à une propriété optionnelle.
#   - Aucun type literal System.IO.Path dans la logique de triage.
#   - Détection des incohérences entre ProblemCount et catégories.
#   - FAIL-CLOSED si le rapport n'est pas structurellement exploitable.
# ============================================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ============================================================================
# CONFIGURATION
# ============================================================================

$Version = '1.0.2'

$ProjectRoot = 'G:\AI\E-zzio'

$ParentRunId = '20260820_185842_063_bbacb75395cd'

$TruthReportRoot = Join-Path `
    -Path $ProjectRoot `
    -ChildPath '_EZZIO_TRUTH_REPORTS'

$ParentRunRoot = Join-Path `
    -Path $TruthReportRoot `
    -ChildPath $ParentRunId

$SourceProblemsPath = Join-Path `
    -Path $ParentRunRoot `
    -ChildPath 'EZZIO_PROJECT_PROBLEMS.json'

$SourceTruthPath = Join-Path `
    -Path $ParentRunRoot `
    -ChildPath 'EZZIO_PROJECT_TRUTH.json'

$SourceInventoryPath = Join-Path `
    -Path $ParentRunRoot `
    -ChildPath 'EZZIO_PROJECT_INVENTORY.json'

$TriageRoot = Join-Path `
    -Path $ParentRunRoot `
    -ChildPath 'TRUTH_FORENSIC_TRIAGE'

$RunId = (
    Get-Date -Format 'yyyyMMdd_HHmmss_fff'
) + '_' + (
    [guid]::NewGuid().ToString('N').Substring(0, 12)
)

$RunRoot = Join-Path `
    -Path $TriageRoot `
    -ChildPath $RunId

$StartedUtc = [DateTime]::UtcNow

# ============================================================================
# CONSOLE HEADER
# ============================================================================

Write-Host ''
Write-Host '============================================================' `
    -ForegroundColor Cyan
Write-Host ' E-ZZIO — TRUTH PROBLEM FORENSIC TRIAGE v1.0.2' `
    -ForegroundColor Cyan
Write-Host ' READ-ONLY / FORENSIC / FAIL-CLOSED' `
    -ForegroundColor Cyan
Write-Host '============================================================' `
    -ForegroundColor Cyan
Write-Host ''

Write-Host "PROJECT : $ProjectRoot"
Write-Host "RUN ID  : $RunId"
Write-Host "PARENT  : $ParentRunId"
Write-Host ''

# ============================================================================
# SAFETY PRECONDITIONS
# ============================================================================

if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) {
    throw "PROJECT_ROOT_NOT_FOUND: $ProjectRoot"
}

if (-not (Test-Path -LiteralPath $ParentRunRoot -PathType Container)) {
    throw "PARENT_RUN_ROOT_NOT_FOUND: $ParentRunRoot"
}

if (-not (Test-Path -LiteralPath $SourceProblemsPath -PathType Leaf)) {
    throw "PROBLEM_REPORT_NOT_FOUND: $SourceProblemsPath"
}

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
# STATE
# ============================================================================

$Problems = [System.Collections.Generic.List[object]]::new()
$Findings = [System.Collections.Generic.List[object]]::new()

$Stats = [ordered]@{

    SourceProblemEntries       = 0
    ValidProblemEntries        = 0
    InvalidProblemEntries      = 0

    MissingType                = 0
    MissingPath                = 0
    MissingMessage             = 0
    MissingErrorId             = 0
    MissingExtent              = 0

    EmptyFileProblems          = 0
    UnreadableProblems         = 0
    HashFailureProblems        = 0
    PowerShellSyntaxProblems   = 0
    JsonSyntaxProblems         = 0
    AnalysisExceptionProblems  = 0
    OtherProblems              = 0

    UniqueProblemPaths         = 0
    DuplicateProblemEntries    = 0

    CriticalFindings           = 0
    WarningFindings            = 0
    InformationalFindings      = 0
}

$MachineVerdict = 'UNINITIALIZED'

# ============================================================================
# HELPER — SAFE PROPERTY READ
#
# IMPORTANT:
#   Never use $Object.ErrorId directly because StrictMode correctly throws
#   when the property does not exist.
# ============================================================================

function Get-SafePropertyValue {

    param(
        [Parameter(Mandatory)]
        [AllowNull()]
        [object]$Object,

        [Parameter(Mandatory)]
        [string]$Name
    )

    if ($null -eq $Object) {
        return $null
    }

    $Property = $Object.PSObject.Properties[$Name]

    if ($null -eq $Property) {
        return $null
    }

    return $Property.Value
}

# ============================================================================
# HELPER — SAFE STRING
# ============================================================================

function Get-SafeString {

    param(
        [AllowNull()]
        [object]$Value
    )

    if ($null -eq $Value) {
        return $null
    }

    return [string]$Value
}

# ============================================================================
# HELPER — NORMALIZE PROBLEM TYPE
# ============================================================================

function Get-NormalizedProblemType {

    param(
        [Parameter(Mandatory)]
        [AllowNull()]
        [object]$Problem
    )

    $TypeValue = Get-SafePropertyValue `
        -Object $Problem `
        -Name 'Type'

    if ($null -eq $TypeValue) {
        return 'MISSING_TYPE'
    }

    $Type = ([string]$TypeValue).Trim().ToUpperInvariant()

    if ([string]::IsNullOrWhiteSpace($Type)) {
        return 'EMPTY_TYPE'
    }

    return $Type
}

# ============================================================================
# HELPER — PATH NORMALIZATION
# ============================================================================

function Normalize-ProblemPath {

    param(
        [AllowNull()]
        [object]$Value
    )

    if ($null -eq $Value) {
        return $null
    }

    $Path = ([string]$Value).Trim()

    if ([string]::IsNullOrWhiteSpace($Path)) {
        return $null
    }

    return $Path
}

# ============================================================================
# HELPER — FINDING
# ============================================================================

function Add-Finding {

    param(
        [Parameter(Mandatory)]
        [ValidateSet(
            'CRITICAL',
            'WARNING',
            'INFORMATIONAL'
        )]
        [string]$Severity,

        [Parameter(Mandatory)]
        [string]$Code,

        [Parameter(Mandatory)]
        [string]$Message,

        [AllowNull()]
        [string]$Path,

        [AllowNull()]
        [object]$Evidence
    )

    $Findings.Add(
        [ordered]@{
            Severity = $Severity
            Code     = $Code
            Path     = $Path
            Message  = $Message
            Evidence = $Evidence
        }
    )

    switch ($Severity) {

        'CRITICAL' {
            $Stats.CriticalFindings++
        }

        'WARNING' {
            $Stats.WarningFindings++
        }

        'INFORMATIONAL' {
            $Stats.InformationalFindings++
        }
    }
}

# ============================================================================
# HELPER — FILE HASH
# ============================================================================

function Get-Sha256 {

    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    return (
        Get-FileHash `
            -LiteralPath $Path `
            -Algorithm SHA256 `
            -ErrorAction Stop
    ).Hash
}

# ============================================================================
# SOURCE REPORT VALIDATION
# ============================================================================

Write-Host 'READING ORIGINAL PROBLEM REPORT...' `
    -ForegroundColor DarkCyan

try {

    $SourceJson = [System.IO.File]::ReadAllText(
        $SourceProblemsPath,
        [System.Text.UTF8Encoding]::new($false)
    )

    if ([string]::IsNullOrWhiteSpace($SourceJson)) {
        throw 'SOURCE_PROBLEM_REPORT_EMPTY'
    }

    $SourceHash = Get-Sha256 -Path $SourceProblemsPath

    try {

        $ParsedProblems = $SourceJson | ConvertFrom-Json -ErrorAction Stop
    }
    catch {

        throw (
            'SOURCE_PROBLEM_REPORT_INVALID_JSON: {0}' -f
            $_.Exception.Message
        )
    }
}
catch {

    $MachineVerdict = 'FORENSIC_FAIL_CLOSED'

    throw (
        'FAIL_CLOSED_SOURCE_REPORT: {0}' -f
        $_.Exception.Message
    )
}

# ============================================================================
# SOURCE STRUCTURE NORMALIZATION
# ============================================================================

if ($null -eq $ParsedProblems) {

    $MachineVerdict = 'FORENSIC_FAIL_CLOSED'

    throw 'SOURCE_PROBLEM_REPORT_NULL'
}

# ConvertFrom-Json may return a scalar object for a single record.
# Force an array so that every cardinality is handled deterministically.

$ProblemArray = @($ParsedProblems)

$Stats.SourceProblemEntries = $ProblemArray.Count

Write-Host (
    'PROBLEMS LOADED : {0}' -f
    $Stats.SourceProblemEntries
) -ForegroundColor Green

Write-Host ''

# ============================================================================
# PROBLEM ENTRY ANALYSIS
# ============================================================================

Write-Host 'FORENSIC TRIAGE STARTED...' `
    -ForegroundColor DarkCyan

$Index = 0
$Total = [Math]::Max(
    1,
    $ProblemArray.Count
)

$PathSeen = @{}

foreach ($Problem in $ProblemArray) {

    $Index++

    Write-Progress `
        -Activity 'E-ZZIO Truth Problem Forensic Triage' `
        -Status "$Index / $Total" `
        -PercentComplete (
            [int](($Index / $Total) * 100)
        )

    # ------------------------------------------------------------------------
    # BASIC OBJECT VALIDATION
    # ------------------------------------------------------------------------

    if ($null -eq $Problem) {

        $Stats.InvalidProblemEntries++

        $Findings.Add(
            [ordered]@{
                Severity = 'CRITICAL'
                Code     = 'NULL_PROBLEM_ENTRY'
                Path     = $null
                Message  = 'Problem report contains a null entry.'
                Evidence = $null
            }
        )

        $Stats.CriticalFindings++

        continue
    }

    $Stats.ValidProblemEntries++

    # ------------------------------------------------------------------------
    # SAFE PROPERTY EXTRACTION
    # ------------------------------------------------------------------------

    $Type = Get-NormalizedProblemType `
        -Problem $Problem

    $Path = Normalize-ProblemPath (
        Get-SafePropertyValue `
            -Object $Problem `
            -Name 'Path'
    )

    $Message = Get-SafeString (
        Get-SafePropertyValue `
            -Object $Problem `
            -Name 'Message'
    )

    $ErrorId = Get-SafeString (
        Get-SafePropertyValue `
            -Object $Problem `
            -Name 'ErrorId'
    )

    $Extent = Get-SafeString (
        Get-SafePropertyValue `
            -Object $Problem `
            -Name 'Extent'
    )

    # ------------------------------------------------------------------------
    # OPTIONAL PROPERTY TELEMETRY
    # ------------------------------------------------------------------------

    if (
        $Type -eq 'MISSING_TYPE' -or
        $Type -eq 'EMPTY_TYPE'
    ) {
        $Stats.MissingType++
    }

    if ($null -eq $Path) {
        $Stats.MissingPath++
    }

    if ($null -eq $Message) {
        $Stats.MissingMessage++
    }

    if ($null -eq $ErrorId) {
        $Stats.MissingErrorId++
    }

    if ($null -eq $Extent) {
        $Stats.MissingExtent++
    }

    # ------------------------------------------------------------------------
    # PATH DUPLICATION TRACKING
    # ------------------------------------------------------------------------

    if ($null -ne $Path) {

        $PathKey = $Path.ToLowerInvariant()

        if ($PathSeen.ContainsKey($PathKey)) {

            $PathSeen[$PathKey]++
            $Stats.DuplicateProblemEntries++
        }
        else {

            $PathSeen[$PathKey] = 1
        }
    }

    # ------------------------------------------------------------------------
    # TYPE CLASSIFICATION
    # ------------------------------------------------------------------------

    switch ($Type) {

        'EMPTY_FILE' {

            $Stats.EmptyFileProblems++
        }

        'UNREADABLE_FILE' {

            $Stats.UnreadableProblems++
        }

        'HASH_FAILURE' {

            $Stats.HashFailureProblems++
        }

        'POWERSHELL_SYNTAX_ERROR' {

            $Stats.PowerShellSyntaxProblems++
        }

        'JSON_SYNTAX_ERROR' {

            $Stats.JsonSyntaxProblems++
        }

        'ANALYSIS_EXCEPTION' {

            $Stats.AnalysisExceptionProblems++
        }

        'MISSING_TYPE' {

            Add-Finding `
                -Severity 'CRITICAL' `
                -Code 'PROBLEM_ENTRY_MISSING_TYPE' `
                -Path $Path `
                -Message 'Problem entry has no Type property.' `
                -Evidence $Problem
        }

        'EMPTY_TYPE' {

            Add-Finding `
                -Severity 'CRITICAL' `
                -Code 'PROBLEM_ENTRY_EMPTY_TYPE' `
                -Path $Path `
                -Message 'Problem entry contains an empty Type.' `
                -Evidence $Problem
        }

        default {

            $Stats.OtherProblems++
        }
    }

    # ------------------------------------------------------------------------
    # MISSING PATH
    # ------------------------------------------------------------------------

    if ($null -eq $Path) {

        Add-Finding `
            -Severity 'WARNING' `
            -Code 'PROBLEM_ENTRY_MISSING_PATH' `
            -Path $null `
            -Message 'Problem entry has no usable Path property.' `
            -Evidence $Problem
    }

    # ------------------------------------------------------------------------
    # MISSING MESSAGE
    # ------------------------------------------------------------------------

    if ($null -eq $Message) {

        Add-Finding `
            -Severity 'WARNING' `
            -Code 'PROBLEM_ENTRY_MISSING_MESSAGE' `
            -Path $Path `
            -Message 'Problem entry has no usable Message property.' `
            -Evidence $Problem
    }

    # ------------------------------------------------------------------------
    # MISSING ERROR ID
    #
    # IMPORTANT:
    #   This is NOT automatically a failure.
    #
    #   EmptyFile, UnreadableFile, HashFailure, etc. legitimately do not
    #   necessarily carry a parser ErrorId.
    # ------------------------------------------------------------------------

    if ($null -eq $ErrorId) {

        if (
            $Type -eq 'POWERSHELL_SYNTAX_ERROR'
        ) {

            Add-Finding `
                -Severity 'WARNING' `
                -Code 'POWERSHELL_SYNTAX_ERROR_MISSING_ERRORID' `
                -Path $Path `
                -Message 'PowerShell syntax problem has no ErrorId.' `
                -Evidence $Problem
        }
    }

    # ------------------------------------------------------------------------
    # MISSING EXTENT
    # ------------------------------------------------------------------------

    if (
        $Type -eq 'POWERSHELL_SYNTAX_ERROR' -and
        $null -eq $Extent
    ) {

        Add-Finding `
            -Severity 'WARNING' `
            -Code 'POWERSHELL_SYNTAX_ERROR_MISSING_EXTENT' `
            -Path $Path `
            -Message 'PowerShell syntax problem has no parser extent.' `
            -Evidence $Problem
    }

    # ------------------------------------------------------------------------
    # PRESERVE NORMALIZED FORENSIC RECORD
    # ------------------------------------------------------------------------

    $Problems.Add(
        [ordered]@{
            Index      = $Index
            Type       = $Type
            Path       = $Path
            Message    = $Message
            ErrorId    = $ErrorId
            Extent     = $Extent
            Original   = $Problem
        }
    )
}

Write-Progress `
    -Activity 'E-ZZIO Truth Problem Forensic Triage' `
    -Completed

# ============================================================================
# UNIQUE PATH COUNT
# ============================================================================

$Stats.UniqueProblemPaths = $PathSeen.Keys.Count

# ============================================================================
# CROSS-CHECK WITH TRUTH REPORT
# ============================================================================

$TruthReportExists = Test-Path `
    -LiteralPath $SourceTruthPath `
    -PathType Leaf

$TruthReportHash = $null

if ($TruthReportExists) {

    try {

        $TruthReportHash = Get-Sha256 `
            -Path $SourceTruthPath
    }
    catch {

        Add-Finding `
            -Severity 'CRITICAL' `
            -Code 'TRUTH_REPORT_HASH_FAILURE' `
            -Path $SourceTruthPath `
            -Message $_.Exception.Message `
            -Evidence $null
    }
}
else {

    Add-Finding `
        -Severity 'WARNING' `
        -Code 'TRUTH_REPORT_MISSING' `
        -Path $SourceTruthPath `
        -Message 'Parent truth report is not present beside the problem report.' `
        -Evidence $null
}

# ============================================================================
# CROSS-CHECK WITH INVENTORY
# ============================================================================

$InventoryExists = Test-Path `
    -LiteralPath $SourceInventoryPath `
    -PathType Leaf

$InventoryHash = $null

if ($InventoryExists) {

    try {

        $InventoryHash = Get-Sha256 `
            -Path $SourceInventoryPath
    }
    catch {

        Add-Finding `
            -Severity 'CRITICAL' `
            -Code 'INVENTORY_HASH_FAILURE' `
            -Path $SourceInventoryPath `
            -Message $_.Exception.Message `
            -Evidence $null
    }
}
else {

    Add-Finding `
        -Severity 'WARNING' `
        -Code 'INVENTORY_MISSING' `
        -Path $SourceInventoryPath `
        -Message 'Parent inventory report is not present beside the problem report.' `
        -Evidence $null
}

# ============================================================================
# SEMANTIC FINDINGS
# ============================================================================

# ------------------------------------------------------------------------
# 1. Syntax errors are real defects, not merely metadata.
# ------------------------------------------------------------------------

if ($Stats.PowerShellSyntaxProblems -gt 0) {

    Add-Finding `
        -Severity 'CRITICAL' `
        -Code 'POWERSHELL_SYNTAX_DEFECTS_PRESENT' `
        -Path $null `
        -Message (
            'PowerShell syntax defects detected: {0}' -f
            $Stats.PowerShellSyntaxProblems
        ) `
        -Evidence (
            $Problems |
                Where-Object {
                    $_.Type -eq 'POWERSHELL_SYNTAX_ERROR'
                }
        )
}

# ------------------------------------------------------------------------
# 2. JSON syntax errors are real defects.
# ------------------------------------------------------------------------

if ($Stats.JsonSyntaxProblems -gt 0) {

    Add-Finding `
        -Severity 'CRITICAL' `
        -Code 'JSON_SYNTAX_DEFECTS_PRESENT' `
        -Path $null `
        -Message (
            'JSON syntax defects detected: {0}' -f
            $Stats.JsonSyntaxProblems
        ) `
        -Evidence (
            $Problems |
                Where-Object {
                    $_.Type -eq 'JSON_SYNTAX_ERROR'
                }
        )
}

# ------------------------------------------------------------------------
# 3. Hash/read failures are forensic blockers.
# ------------------------------------------------------------------------

if ($Stats.HashFailureProblems -gt 0) {

    Add-Finding `
        -Severity 'CRITICAL' `
        -Code 'HASH_FAILURES_PRESENT' `
        -Path $null `
        -Message (
            'Hash failures detected: {0}' -f
            $Stats.HashFailureProblems
        ) `
        -Evidence (
            $Problems |
                Where-Object {
                    $_.Type -eq 'HASH_FAILURE'
                }
        )
}

if ($Stats.UnreadableProblems -gt 0) {

    Add-Finding `
        -Severity 'CRITICAL' `
        -Code 'UNREADABLE_FILES_PRESENT' `
        -Path $null `
        -Message (
            'Unreadable files detected: {0}' -f
            $Stats.UnreadableProblems
        ) `
        -Evidence (
            $Problems |
                Where-Object {
                    $_.Type -eq 'UNREADABLE_FILE'
                }
        )
}

# ------------------------------------------------------------------------
# 4. Empty files are defects requiring classification, but not necessarily
#    forensic corruption.
# ------------------------------------------------------------------------

if ($Stats.EmptyFileProblems -gt 0) {

    Add-Finding `
        -Severity 'WARNING' `
        -Code 'EMPTY_FILES_PRESENT' `
        -Path $null `
        -Message (
            'Empty files detected: {0}. They require semantic classification ' +
            'before any correction is authorized.' -f
            $Stats.EmptyFileProblems
        ) `
        -Evidence (
            $Problems |
                Where-Object {
                    $_.Type -eq 'EMPTY_FILE'
                }
        )
}

# ============================================================================
# DUPLICATE ANALYSIS
# ============================================================================

if ($Stats.DuplicateProblemEntries -gt 0) {

    Add-Finding `
        -Severity 'INFORMATIONAL' `
        -Code 'DUPLICATE_PROBLEM_PATH_ENTRIES' `
        -Path $null `
        -Message (
            'Problem report contains {0} repeated path entries.' -f
            $Stats.DuplicateProblemEntries
        ) `
        -Evidence $null
}

# ============================================================================
# REPORT COUNTS
# ============================================================================

$TypeCounts = [ordered]@{}

foreach ($Problem in $Problems) {

    $Type = [string]$Problem.Type

    if ($TypeCounts.Contains($Type)) {

        $TypeCounts[$Type]++
    }
    else {

        $TypeCounts[$Type] = 1
    }
}

# ============================================================================
# SOURCE CONSISTENCY CHECK
# ============================================================================

$ExpectedFromTruth = $null

if ($TruthReportExists) {

    try {

        $TruthJson = [System.IO.File]::ReadAllText(
            $SourceTruthPath,
            [System.Text.UTF8Encoding]::new($false)
        )

        $TruthObject = $TruthJson | ConvertFrom-Json -ErrorAction Stop

        $StatisticsObject = Get-SafePropertyValue `
            -Object $TruthObject `
            -Name 'Statistics'

        $ExpectedFromTruth = Get-SafePropertyValue `
            -Object $StatisticsObject `
            -Name 'ProblemsDetected'
    }
    catch {

        Add-Finding `
            -Severity 'WARNING' `
            -Code 'TRUTH_REPORT_READ_FAILURE' `
            -Path $SourceTruthPath `
            -Message $_.Exception.Message `
            -Evidence $null
    }
}

if ($null -ne $ExpectedFromTruth) {

    $ExpectedProblemCount = [int64]$ExpectedFromTruth

    if (
        $ExpectedProblemCount -ne
        [int64]$Stats.SourceProblemEntries
    ) {

        Add-Finding `
            -Severity 'WARNING' `
            -Code 'PROBLEM_COUNT_MISMATCH' `
            -Path $SourceProblemsPath `
            -Message (
                'Truth report ProblemsDetected={0}, while the problem ' +
                'report contains {1} entries.' -f
                $ExpectedProblemCount,
                $Stats.SourceProblemEntries
            ) `
            -Evidence (
                [ordered]@{
                    TruthProblemsDetected = $ExpectedProblemCount
                    ProblemReportEntries   = $Stats.SourceProblemEntries
                }
            )
    }
}

# ============================================================================
# FINAL VERDICT
# ============================================================================

if (
    $Stats.InvalidProblemEntries -gt 0 -or
    $Stats.CriticalFindings -gt 0
) {

    $MachineVerdict = 'FORENSIC_FAIL_CLOSED'
}
else {

    $MachineVerdict = 'FORENSIC_TRIAGE_COMPLETE'
}

$FinishedUtc = [DateTime]::UtcNow

$DurationSeconds = (
    $FinishedUtc - $StartedUtc
).TotalSeconds

# ============================================================================
# MACHINE REPORT
# ============================================================================

$Report = [ordered]@{

    Product   = 'E-ZZIO'
    Component = 'Truth Problem Forensic Triage'
    Version   = $Version

    Run = [ordered]@{
        RunId           = $RunId
        ParentRunId     = $ParentRunId
        StartedUtc      = $StartedUtc.ToString('o')
        FinishedUtc     = $FinishedUtc.ToString('o')
        DurationSeconds = [Math]::Round(
            $DurationSeconds,
            3
        )
    }

    Configuration = [ordered]@{
        ProjectRoot           = $ProjectRoot
        Mode                  = 'READ_ONLY'
        Forensic              = $true
        FailClosed            = $true
        SourceMutationAllowed = $false

        ParentProblemReport   = $SourceProblemsPath
        ParentTruthReport     = $SourceTruthPath
        ParentInventory       = $SourceInventoryPath

        TriageRoot            = $TriageRoot
        CurrentRunRoot        = $RunRoot
    }

    SourceIntegrity = [ordered]@{
        ProblemReportSha256 = $SourceHash
        TruthReportExists   = $TruthReportExists
        TruthReportSha256   = $TruthReportHash
        InventoryExists     = $InventoryExists
        InventorySha256     = $InventoryHash
    }

    Verdict = $MachineVerdict

    Statistics = $Stats

    ProblemTypeCounts = $TypeCounts

    Findings = @(
        $Findings
    )

    Problems = @(
        $Problems
    )
}

# ============================================================================
# OUTPUT PATHS
# ============================================================================

$TriageJsonPath = Join-Path `
    -Path $RunRoot `
    -ChildPath 'EZZIO_TRUTH_FORENSIC_TRIAGE.json'

$NormalizedProblemsPath = Join-Path `
    -Path $RunRoot `
    -ChildPath 'EZZIO_TRUTH_NORMALIZED_PROBLEMS.json'

$FindingsPath = Join-Path `
    -Path $RunRoot `
    -ChildPath 'EZZIO_TRUTH_FORENSIC_FINDINGS.json'

$SummaryPath = Join-Path `
    -Path $RunRoot `
    -ChildPath 'EZZIO_TRUTH_FORENSIC_TRIAGE_SUMMARY.txt'

# ============================================================================
# WRITE MACHINE REPORTS
# ============================================================================

$Report |
    ConvertTo-Json -Depth 50 |
    Set-Content `
        -LiteralPath $TriageJsonPath `
        -Encoding utf8

@($Problems) |
    ConvertTo-Json -Depth 30 |
    Set-Content `
        -LiteralPath $NormalizedProblemsPath `
        -Encoding utf8

@($Findings) |
    ConvertTo-Json -Depth 30 |
    Set-Content `
        -LiteralPath $FindingsPath `
        -Encoding utf8

# ============================================================================
# SUMMARY
# ============================================================================

$SummaryLines = @(
    'E-ZZIO — TRUTH PROBLEM FORENSIC TRIAGE'
    '========================================'
    ''
    "Version                    = $Version"
    "RunId                      = $RunId"
    "ParentRunId               = $ParentRunId"
    "ProjectRoot                = $ProjectRoot"
    'Mode                       = READ_ONLY'
    'SourceMutationAllowed     = FALSE'
    'FailClosed                 = TRUE'
    ''
    "SourceProblemEntries       = $($Stats.SourceProblemEntries)"
    "ValidProblemEntries        = $($Stats.ValidProblemEntries)"
    "InvalidProblemEntries      = $($Stats.InvalidProblemEntries)"
    ''
    "MissingType                = $($Stats.MissingType)"
    "MissingPath                = $($Stats.MissingPath)"
    "MissingMessage             = $($Stats.MissingMessage)"
    "MissingErrorId             = $($Stats.MissingErrorId)"
    "MissingExtent              = $($Stats.MissingExtent)"
    ''
    "EmptyFileProblems          = $($Stats.EmptyFileProblems)"
    "UnreadableProblems         = $($Stats.UnreadableProblems)"
    "HashFailureProblems        = $($Stats.HashFailureProblems)"
    "PowerShellSyntaxProblems   = $($Stats.PowerShellSyntaxProblems)"
    "JsonSyntaxProblems         = $($Stats.JsonSyntaxProblems)"
    "AnalysisExceptionProblems  = $($Stats.AnalysisExceptionProblems)"
    "OtherProblems              = $($Stats.OtherProblems)"
    ''
    "UniqueProblemPaths         = $($Stats.UniqueProblemPaths)"
    "DuplicateProblemEntries    = $($Stats.DuplicateProblemEntries)"
    ''
    "CriticalFindings           = $($Stats.CriticalFindings)"
    "WarningFindings            = $($Stats.WarningFindings)"
    "InformationalFindings      = $($Stats.InformationalFindings)"
    ''
    "Verdict                    = $MachineVerdict"
    "DurationSeconds            = $([Math]::Round($DurationSeconds, 3))"
    ''
    'SOURCE'
    "ProblemReport              = $SourceProblemsPath"
    "ProblemReportSha256        = $SourceHash"
    "TruthReport                = $SourceTruthPath"
    "Inventory                  = $SourceInventoryPath"
    ''
    'OUTPUT'
    "Triage                     = $TriageJsonPath"
    "NormalizedProblems         = $NormalizedProblemsPath"
    "Findings                   = $FindingsPath"
    "Summary                    = $SummaryPath"
)

$SummaryLines |
    Set-Content `
        -LiteralPath $SummaryPath `
        -Encoding utf8

# ============================================================================
# CONSOLE RESULT
# ============================================================================

Write-Host ''
Write-Host '============================================================' `
    -ForegroundColor Cyan
Write-Host ' E-ZZIO — TRUTH FORENSIC TRIAGE COMPLETE' `
    -ForegroundColor Cyan
Write-Host '============================================================' `
    -ForegroundColor Cyan
Write-Host ''

Write-Host "PROBLEMS LOADED        : $($Stats.SourceProblemEntries)"
Write-Host "VALID ENTRIES          : $($Stats.ValidProblemEntries)"
Write-Host "INVALID ENTRIES        : $($Stats.InvalidProblemEntries)"
Write-Host ''

Write-Host "EMPTY FILE PROBLEMS    : $($Stats.EmptyFileProblems)"
Write-Host "UNREADABLE PROBLEMS    : $($Stats.UnreadableProblems)"
Write-Host "HASH FAILURES          : $($Stats.HashFailureProblems)"
Write-Host "POWERSHELL SYNTAX      : $($Stats.PowerShellSyntaxProblems)"
Write-Host "JSON SYNTAX            : $($Stats.JsonSyntaxProblems)"
Write-Host "ANALYSIS EXCEPTIONS    : $($Stats.AnalysisExceptionProblems)"
Write-Host ''

Write-Host "MISSING TYPE           : $($Stats.MissingType)"
Write-Host "MISSING PATH           : $($Stats.MissingPath)"
Write-Host "MISSING MESSAGE        : $($Stats.MissingMessage)"
Write-Host "MISSING ERRORID        : $($Stats.MissingErrorId)"
Write-Host "MISSING EXTENT         : $($Stats.MissingExtent)"
Write-Host ''

Write-Host "UNIQUE PROBLEM PATHS   : $($Stats.UniqueProblemPaths)"
Write-Host "DUPLICATE ENTRIES      : $($Stats.DuplicateProblemEntries)"
Write-Host ''

Write-Host "CRITICAL FINDINGS      : $($Stats.CriticalFindings)"
Write-Host "WARNING FINDINGS       : $($Stats.WarningFindings)"
Write-Host "INFO FINDINGS          : $($Stats.InformationalFindings)"
Write-Host ''

if ($MachineVerdict -eq 'FORENSIC_FAIL_CLOSED') {

    Write-Host 'TRUTH STATUS           : FORENSIC_FAIL_CLOSED' `
        -ForegroundColor Red
}
else {

    Write-Host 'TRUTH STATUS           : FORENSIC_TRIAGE_COMPLETE' `
        -ForegroundColor Green
}

Write-Host ''

Write-Host 'OUTPUTS:' `
    -ForegroundColor DarkCyan

Write-Host "  $TriageJsonPath"
Write-Host "  $NormalizedProblemsPath"
Write-Host "  $FindingsPath"
Write-Host "  $SummaryPath"

Write-Host ''

Write-Host 'IMPORTANT:' `
    -ForegroundColor Yellow

Write-Host 'No E-ZZIO source file was modified.'
Write-Host 'No correction was performed.'
Write-Host 'No discovered PowerShell file was executed.'
Write-Host 'This phase is forensic classification only.'

Write-Host ''
Write-Host '============================================================' `
    -ForegroundColor Cyan