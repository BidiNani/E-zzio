# ============================================================================
# E-ZZIO — TRUTH FORENSIC REMEDIATION PLANNER
# Version : 1.0.0
#
# MODE
#   READ-ONLY / FORENSIC / FAIL-CLOSED
#
# PURPOSE
#   Transform the validated Truth Forensic Triage into a deterministic,
#   evidence-backed remediation plan.
#
# SAFETY
#   - NO SOURCE MUTATION
#   - NO SOURCE DELETION
#   - NO SOURCE REWRITE
#   - NO POWERSHELL EXECUTION
#   - NO AUTOMATIC CORRECTION
#   - ONLY REPORT DIRECTORY MAY BE CREATED/WRITTEN
#   - ALL SOURCE PATHS MUST REMAIN INSIDE PROJECT ROOT
#
# INPUT
#   Existing Truth Forensic Triage:
#
#   G:\AI\E-zzio\_EZZIO_TRUTH_REPORTS\
#       20260820_185842_063_bbacb75395cd\
#       TRUTH_FORENSIC_TRIAGE\
#       20260820_191019_580_f1b899c683ae\
#
# OUTPUT
#   REMEDIATION_PLAN.json
#   REMEDIATION_EVIDENCE.json
#   REMEDIATION_SUMMARY.txt
#
# ============================================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ============================================================================
# CONFIGURATION
# ============================================================================

$Version = '1.0.0'

$ProjectRoot = 'G:\AI\E-zzio'

$ParentRunId = '20260820_185842_063_bbacb75395cd'

$TriageRunId = '20260820_191019_580_f1b899c683ae'

$TriageRoot = Join-Path `
    -Path $ProjectRoot `
    -ChildPath (
        '_EZZIO_TRUTH_REPORTS\' +
        $ParentRunId +
        '\TRUTH_FORENSIC_TRIAGE\' +
        $TriageRunId
    )

$TriagePath = Join-Path `
    -Path $TriageRoot `
    -ChildPath 'EZZIO_TRUTH_FORENSIC_TRIAGE.json'

$NormalizedProblemsPath = Join-Path `
    -Path $TriageRoot `
    -ChildPath 'EZZIO_TRUTH_NORMALIZED_PROBLEMS.json'

$FindingsPath = Join-Path `
    -Path $TriageRoot `
    -ChildPath 'EZZIO_TRUTH_FORENSIC_FINDINGS.json'

$OutputRoot = Join-Path `
    -Path $TriageRoot `
    -ChildPath 'REMEDIATION_PLAN'

$PlanPath = Join-Path `
    -Path $OutputRoot `
    -ChildPath 'EZZIO_TRUTH_REMEDIATION_PLAN.json'

$EvidencePath = Join-Path `
    -Path $OutputRoot `
    -ChildPath 'EZZIO_TRUTH_REMEDIATION_EVIDENCE.json'

$SummaryPath = Join-Path `
    -Path $OutputRoot `
    -ChildPath 'EZZIO_TRUTH_REMEDIATION_SUMMARY.txt'

# ============================================================================
# PRECONDITIONS
# ============================================================================

if (
    -not (
        Test-Path `
            -LiteralPath $ProjectRoot `
            -PathType Container
    )
) {
    throw "PROJECT_ROOT_NOT_FOUND: $ProjectRoot"
}

if (
    -not (
        Test-Path `
            -LiteralPath $TriagePath `
            -PathType Leaf
    )
) {
    throw "TRIAGE_REPORT_NOT_FOUND: $TriagePath"
}

if (
    -not (
        Test-Path `
            -LiteralPath $NormalizedProblemsPath `
            -PathType Leaf
    )
) {
    throw "NORMALIZED_PROBLEMS_NOT_FOUND: $NormalizedProblemsPath"
}

if (
    -not (
        Test-Path `
            -LiteralPath $FindingsPath `
            -PathType Leaf
    )
) {
    throw "FORENSIC_FINDINGS_NOT_FOUND: $FindingsPath"
}

# ============================================================================
# HELPERS
# ============================================================================

function Get-RelativeProjectPath {

    param(
        [Parameter(Mandatory)]
        [string]$FullPath
    )

    $Root = (
        [System.IO.Path]::GetFullPath(
            $ProjectRoot
        )
    ).TrimEnd(
        [char]'\',
        [char]'/'
    )

    $Full = (
        [System.IO.Path]::GetFullPath(
            $FullPath
        )
    )

    if (
        $Full.Equals(
            $Root,
            [System.StringComparison]::OrdinalIgnoreCase
        )
    ) {
        return ''
    }

    $Prefix = $Root + [System.IO.Path]::DirectorySeparatorChar

    if (
        -not $Full.StartsWith(
            $Prefix,
            [System.StringComparison]::OrdinalIgnoreCase
        )
    ) {
        throw (
            'PATH_ESCAPE_DETECTED: {0}' -f $Full
        )
    }

    return $Full.Substring(
        $Prefix.Length
    )
}

function Test-PathInsideProject {

    param(
        [Parameter(Mandatory)]
        [string]$FullPath
    )

    try {
        $null = Get-RelativeProjectPath -FullPath $FullPath
        return $true
    }
    catch {
        return $false
    }
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

        throw (
            'HASH_FAILURE: {0}: {1}' -f
            $Path,
            $_.Exception.Message
        )
    }
}

function Get-TextContext {

    param(
        [Parameter(Mandatory)]
        [string]$Path,

        [Parameter(Mandatory)]
        [int]$LineNumber,

        [int]$Radius = 3
    )

    if (
        -not (
            Test-Path `
                -LiteralPath $Path `
                -PathType Leaf
        )
    ) {
        return @()
    }

    try {

        $Lines = @(
            Get-Content `
                -LiteralPath $Path `
                -ErrorAction Stop
        )

        if ($Lines.Count -eq 0) {
            return @()
        }

        $Start = [Math]::Max(
            1,
            $LineNumber - $Radius
        )

        $End = [Math]::Min(
            $Lines.Count,
            $LineNumber + $Radius
        )

        $Result = [System.Collections.Generic.List[object]]::new()

        for (
            $i = $Start;
            $i -le $End;
            $i++
        ) {

            $Result.Add(
                [ordered]@{
                    LineNumber = $i
                    IsTarget   = ($i -eq $LineNumber)
                    Text       = [string]$Lines[$i - 1]
                }
            )
        }

        return @($Result)
    }
    catch {

        return @(
            [ordered]@{
                LineNumber = $LineNumber
                IsTarget   = $true
                Text       = ''
                ReadError  = [string]$_.Exception.Message
            }
        )
    }
}

function Get-PropertyValue {

    param(
        [Parameter(Mandatory)]
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

function Get-ProblemSeverity {

    param(
        [Parameter(Mandatory)]
        [string]$Type
    )

    switch ($Type) {

        'POWERSHELL_SYNTAX_ERROR' {
            return 'CRITICAL'
        }

        'JSON_SYNTAX_ERROR' {
            return 'CRITICAL'
        }

        'HASH_FAILURE' {
            return 'CRITICAL'
        }

        'UNREADABLE_FILE' {
            return 'CRITICAL'
        }

        'ANALYSIS_EXCEPTION' {
            return 'CRITICAL'
        }

        'EMPTY_FILE' {
            return 'HIGH'
        }

        default {
            return 'UNKNOWN'
        }
    }
}

function Get-ProblemCategory {

    param(
        [Parameter(Mandatory)]
        [string]$Type
    )

    switch ($Type) {

        'POWERSHELL_SYNTAX_ERROR' {
            return 'SOURCE_SYNTAX'
        }

        'JSON_SYNTAX_ERROR' {
            return 'DATA_SYNTAX'
        }

        'EMPTY_FILE' {
            return 'EMPTY_ARTIFACT'
        }

        'UNREADABLE_FILE' {
            return 'ACCESS'
        }

        'HASH_FAILURE' {
            return 'INTEGRITY'
        }

        'ANALYSIS_EXCEPTION' {
            return 'ANALYSIS'
        }

        default {
            return 'UNCLASSIFIED'
        }
    }
}

# ============================================================================
# START
# ============================================================================

$StartedUtc = [DateTime]::UtcNow

Write-Host ''
Write-Host '============================================================' `
    -ForegroundColor Cyan

Write-Host ' E-ZZIO — TRUTH FORENSIC REMEDIATION PLANNER v1.0.0' `
    -ForegroundColor Cyan

Write-Host ' READ-ONLY / FORENSIC / FAIL-CLOSED' `
    -ForegroundColor Cyan

Write-Host '============================================================' `
    -ForegroundColor Cyan

Write-Host ''

Write-Host "PROJECT : $ProjectRoot"
Write-Host "PARENT  : $ParentRunId"
Write-Host "TRIAGE  : $TriageRunId"

Write-Host ''

# ============================================================================
# OUTPUT DIRECTORY
# ============================================================================

New-Item `
    -ItemType Directory `
    -Path $OutputRoot `
    -Force `
    -ErrorAction Stop |
    Out-Null

# ============================================================================
# LOAD TRIAGE
# ============================================================================

Write-Host 'LOADING TRIAGE...' `
    -ForegroundColor DarkCyan

$Triage = (
    Get-Content `
        -LiteralPath $TriagePath `
        -Raw `
        -ErrorAction Stop |
    ConvertFrom-Json `
        -ErrorAction Stop
)

$NormalizedProblems = @(
    Get-Content `
        -LiteralPath $NormalizedProblemsPath `
        -Raw `
        -ErrorAction Stop |
    ConvertFrom-Json `
        -ErrorAction Stop
)

$Findings = @(
    Get-Content `
        -LiteralPath $FindingsPath `
        -Raw `
        -ErrorAction Stop |
    ConvertFrom-Json `
        -ErrorAction Stop
)

Write-Host (
    'PROBLEMS LOADED      : {0}' -f
    $NormalizedProblems.Count
)

Write-Host (
    'FINDINGS LOADED      : {0}' -f
    $Findings.Count
)

# ============================================================================
# STATE
# ============================================================================

$PlanEntries = [System.Collections.Generic.List[object]]::new()

$EvidenceEntries = [System.Collections.Generic.List[object]]::new()

$PathFailures = [System.Collections.Generic.List[object]]::new()

$ReadFailures = [System.Collections.Generic.List[object]]::new()

$HashFailures = [System.Collections.Generic.List[object]]::new()

$PowerShellEntries = [System.Collections.Generic.List[object]]::new()

$JsonEntries = [System.Collections.Generic.List[object]]::new()

$EmptyEntries = [System.Collections.Generic.List[object]]::new()

$UnknownEntries = [System.Collections.Generic.List[object]]::new()

# ============================================================================
# FORENSIC ANALYSIS
# ============================================================================

Write-Host ''
Write-Host 'BUILDING EVIDENCE-BACKED REMEDIATION PLAN...' `
    -ForegroundColor DarkCyan

$Index = 0

$Total = [Math]::Max(
    1,
    $NormalizedProblems.Count
)

foreach ($Problem in $NormalizedProblems) {

    $Index++

    Write-Progress `
        -Activity 'E-ZZIO Remediation Planning' `
        -Status (
            [string](
                Get-PropertyValue `
                    -Object $Problem `
                    -Name 'Path'
            )
        ) `
        -PercentComplete (
            [int](($Index / $Total) * 100)
        )

    $Type = [string](
        Get-PropertyValue `
            -Object $Problem `
            -Name 'Type'
    )

    $RelativePath = [string](
        Get-PropertyValue `
            -Object $Problem `
            -Name 'Path'
    )

    $Message = [string](
        Get-PropertyValue `
            -Object $Problem `
            -Name 'Message'
    )

    $ErrorIdValue = Get-PropertyValue `
        -Object $Problem `
        -Name 'ErrorId'

    $ExtentValue = Get-PropertyValue `
        -Object $Problem `
        -Name 'Extent'

    $LineValue = Get-PropertyValue `
        -Object $Problem `
        -Name 'Line'

    $ColumnValue = Get-PropertyValue `
        -Object $Problem `
        -Name 'Column'

    $Severity = Get-ProblemSeverity `
        -Type $Type

    $Category = Get-ProblemCategory `
        -Type $Type

    # ------------------------------------------------------------------------
    # PATH VALIDATION
    # ------------------------------------------------------------------------

    if (
        [string]::IsNullOrWhiteSpace(
            $RelativePath
        )
    ) {

        $PathFailures.Add(
            [ordered]@{
                Type    = 'MISSING_PATH'
                Problem = $Problem
            }
        )

        continue
    }

    try {

        $FullPath = [System.IO.Path]::GetFullPath(
            (
                Join-Path `
                    -Path $ProjectRoot `
                    -ChildPath $RelativePath
            )
        )

        if (
            -not (
                Test-PathInsideProject `
                    -FullPath $FullPath
            )
        ) {

            throw (
                'PATH_OUTSIDE_PROJECT: {0}' -f
                $RelativePath
            )
        }
    }
    catch {

        $PathFailures.Add(
            [ordered]@{
                Type    = 'INVALID_PATH'
                Path    = $RelativePath
                Message = [string]$_.Exception.Message
            }
        )

        continue
    }

    # ------------------------------------------------------------------------
    # FILE EXISTENCE
    # ------------------------------------------------------------------------

    $Exists = Test-Path `
        -LiteralPath $FullPath `
        -PathType Leaf

    $CurrentSize = $null
    $CurrentHash = $null
    $CurrentLastWriteUtc = $null

    if ($Exists) {

        try {

            $FileInfo = Get-Item `
                -LiteralPath $FullPath `
                -Force `
                -ErrorAction Stop

            $CurrentSize = [int64]$FileInfo.Length

            $CurrentLastWriteUtc =
                $FileInfo.LastWriteTimeUtc.ToString('o')
        }
        catch {

            $ReadFailures.Add(
                [ordered]@{
                    Path    = $RelativePath
                    Type    = 'METADATA_READ_FAILURE'
                    Message = [string]$_.Exception.Message
                }
            )

            $Exists = $false
        }
    }

    # ------------------------------------------------------------------------
    # HASH CURRENT FILE
    # ------------------------------------------------------------------------

    if ($Exists) {

        try {

            $CurrentHash = Get-SafeSha256 `
                -Path $FullPath
        }
        catch {

            $HashFailures.Add(
                [ordered]@{
                    Path    = $RelativePath
                    Message = [string]$_.Exception.Message
                }
            )
        }
    }

    # ------------------------------------------------------------------------
    # CONTEXT
    # ------------------------------------------------------------------------

    $Context = @()

    if (
        $Exists -and
        $Type -eq 'POWERSHELL_SYNTAX_ERROR'
    ) {

        $LineNumber = 0

        if ($null -ne $LineValue) {

            try {
                $LineNumber = [int]$LineValue
            }
            catch {
                $LineNumber = 0
            }
        }

        if ($LineNumber -gt 0) {

            $Context = @(
                Get-TextContext `
                    -Path $FullPath `
                    -LineNumber $LineNumber `
                    -Radius 4
            )
        }
    }

    # ------------------------------------------------------------------------
    # FORENSIC CLASSIFICATION
    # ------------------------------------------------------------------------

    $RecommendedAction = 'MANUAL_REVIEW_REQUIRED'

    $RootCauseHypothesis = 'UNCLASSIFIED'

    $MutationAllowed = $false

    switch ($Type) {

        'EMPTY_FILE' {

            $RootCauseHypothesis =
                'FILE_HAS_ZERO_BYTES'

            $RecommendedAction =
                'DETERMINE_INTENT_BEFORE_ANY_RESTORATION'
        }

        'POWERSHELL_SYNTAX_ERROR' {

            $RootCauseHypothesis =
                'POWERSHELL_PARSER_REJECTS_SOURCE'

            $RecommendedAction =
                'REVIEW_EXACT_SYNTAX_ERROR_WITH_SOURCE_CONTEXT'
        }

        'JSON_SYNTAX_ERROR' {

            $RootCauseHypothesis =
                'JSON_PARSER_REJECTS_DOCUMENT'

            $RecommendedAction =
                'REVIEW_JSON_SYNTAX_AND_DOCUMENT_STRUCTURE'
        }

        'UNREADABLE_FILE' {

            $RootCauseHypothesis =
                'FILE_ACCESS_OR_IO_FAILURE'

            $RecommendedAction =
                'INVESTIGATE_ACCESS_BEFORE_RETRY'
        }

        'HASH_FAILURE' {

            $RootCauseHypothesis =
                'INTEGRITY_HASH_OPERATION_FAILED'

            $RecommendedAction =
                'FAIL_CLOSED_AND_INVESTIGATE_INTEGRITY'
        }

        'ANALYSIS_EXCEPTION' {

            $RootCauseHypothesis =
                'TRUTH_ENGINE_ANALYSIS_EXCEPTION'

            $RecommendedAction =
                'INVESTIGATE_ANALYZER_FAILURE_BEFORE_SOURCE_CHANGE'
        }

        default {

            $RootCauseHypothesis =
                'UNKNOWN_PROBLEM_TYPE'

            $RecommendedAction =
                'MANUAL_FORENSIC_REVIEW'
        }
    }

    # ------------------------------------------------------------------------
    # EVIDENCE RECORD
    # ------------------------------------------------------------------------

    $Evidence = [ordered]@{
        RelativePath       = $RelativePath
        FullPath           = $FullPath
        ExistsNow          = $Exists
        CurrentSizeBytes   = $CurrentSize
        CurrentSHA256      = $CurrentHash
        CurrentLastWriteUtc = $CurrentLastWriteUtc
        OriginalProblemType = $Type
        Severity           = $Severity
        Category           = $Category
        ErrorId            = $ErrorIdValue
        Message            = $Message
        Line               = $LineValue
        Column             = $ColumnValue
        Extent             = $ExtentValue
        SourceContext      = $Context
        MutationAllowed    = $MutationAllowed
    }

    $EvidenceEntries.Add($Evidence)

    # ------------------------------------------------------------------------
    # PLAN RECORD
    # ------------------------------------------------------------------------

    $PlanEntry = [ordered]@{
        ProblemType         = $Type
        Severity             = $Severity
        Category             = $Category
        Path                = $RelativePath
        ExistsNow            = $Exists
        CurrentSHA256       = $CurrentHash
        CurrentSizeBytes    = $CurrentSize
        ErrorId             = $ErrorIdValue
        Message             = $Message
        Line                = $LineValue
        Column              = $ColumnValue
        Extent              = $ExtentValue
        RootCauseHypothesis = $RootCauseHypothesis
        RecommendedAction   = $RecommendedAction
        MutationAllowed     = $MutationAllowed
        Status              = 'AWAITING_REVIEW'
    }

    $PlanEntries.Add($PlanEntry)

    # ------------------------------------------------------------------------
    # CATEGORY COLLECTIONS
    # ------------------------------------------------------------------------

    switch ($Type) {

        'POWERSHELL_SYNTAX_ERROR' {
            $PowerShellEntries.Add($PlanEntry)
        }

        'JSON_SYNTAX_ERROR' {
            $JsonEntries.Add($PlanEntry)
        }

        'EMPTY_FILE' {
            $EmptyEntries.Add($PlanEntry)
        }

        default {
            $UnknownEntries.Add($PlanEntry)
        }
    }
}

Write-Progress `
    -Activity 'E-ZZIO Remediation Planning' `
    -Completed

# ============================================================================
# FINDINGS CROSS-CHECK
# ============================================================================

$CriticalFindings = @(
    foreach ($Finding in $Findings) {

        $Severity = [string](
            Get-PropertyValue `
                -Object $Finding `
                -Name 'Severity'
        )

        if ($Severity -eq 'CRITICAL') {
            $Finding
        }
    }
)

$HighFindings = @(
    foreach ($Finding in $Findings) {

        $Severity = [string](
            Get-PropertyValue `
                -Object $Finding `
                -Name 'Severity'
        )

        if ($Severity -eq 'HIGH') {
            $Finding
        }
    }
)

# ============================================================================
# VERDICT
# ============================================================================

$Verdict = 'REMEDIATION_PLAN_READY'

if ($PathFailures.Count -gt 0) {

    $Verdict = 'FORENSIC_FAIL_CLOSED'
}
elseif ($ReadFailures.Count -gt 0) {

    $Verdict = 'FORENSIC_FAIL_CLOSED'
}
elseif ($HashFailures.Count -gt 0) {

    $Verdict = 'FORENSIC_FAIL_CLOSED'
}
elseif ($CriticalFindings.Count -gt 0) {

    $Verdict = 'REMEDIATION_REQUIRED_CRITICAL'
}
elseif ($PlanEntries.Count -gt 0) {

    $Verdict = 'REMEDIATION_REQUIRED'
}

$FinishedUtc = [DateTime]::UtcNow

$DurationSeconds = (
    $FinishedUtc - $StartedUtc
).TotalSeconds

# ============================================================================
# MACHINE PLAN
# ============================================================================

$Plan = [ordered]@{

    Product   = 'E-ZZIO'

    Component = 'Truth Forensic Remediation Planner'

    Version   = $Version

    Run = [ordered]@{
        ParentRunId       = $ParentRunId
        TriageRunId       = $TriageRunId
        StartedUtc        = $StartedUtc.ToString('o')
        FinishedUtc       = $FinishedUtc.ToString('o')
        DurationSeconds   = [Math]::Round(
            $DurationSeconds,
            3
        )
    }

    Configuration = [ordered]@{
        ProjectRoot           = $ProjectRoot
        Mode                  = 'READ_ONLY'
        FailClosed            = $true
        SourceMutationAllowed = $false
        SourceExecutionAllowed = $false
        AutomaticCorrection   = $false
    }

    Verdict = $Verdict

    Counts = [ordered]@{
        ProblemsAnalyzed     = $PlanEntries.Count
        CriticalFindings     = $CriticalFindings.Count
        HighFindings         = $HighFindings.Count
        PowerShellProblems   = $PowerShellEntries.Count
        JsonProblems         = $JsonEntries.Count
        EmptyFiles           = $EmptyEntries.Count
        UnknownProblems      = $UnknownEntries.Count
        PathFailures         = $PathFailures.Count
        ReadFailures         = $ReadFailures.Count
        HashFailures         = $HashFailures.Count
    }

    CriticalFindings = @(
        $CriticalFindings
    )

    HighFindings = @(
        $HighFindings
    )

    Plan = @(
        $PlanEntries
    )

    Safety = [ordered]@{
        SourceFilesModified = $false
        SourceFilesDeleted  = $false
        SourceFilesExecuted  = $false
        AutomaticCorrection = $false
    }
}

# ============================================================================
# EVIDENCE PACKAGE
# ============================================================================

$EvidencePackage = [ordered]@{

    Product   = 'E-ZZIO'

    Component = 'Truth Forensic Remediation Evidence'

    Version   = $Version

    ParentRunId = $ParentRunId

    TriageRunId = $TriageRunId

    Verdict = $Verdict

    Evidence = @(
        $EvidenceEntries
    )

    PathFailures = @(
        $PathFailures
    )

    ReadFailures = @(
        $ReadFailures
    )

    HashFailures = @(
        $HashFailures
    )
}

# ============================================================================
# WRITE JSON REPORTS
# ============================================================================

Write-Host ''
Write-Host 'WRITING REMEDIATION PLAN...' `
    -ForegroundColor DarkCyan

$Plan |
    ConvertTo-Json `
        -Depth 40 |
    Set-Content `
        -LiteralPath $PlanPath `
        -Encoding utf8 `
        -ErrorAction Stop

$EvidencePackage |
    ConvertTo-Json `
        -Depth 40 |
    Set-Content `
        -LiteralPath $EvidencePath `
        -Encoding utf8 `
        -ErrorAction Stop

# ============================================================================
# SUMMARY
# ============================================================================

$SummaryLines = @(
    'E-ZZIO — TRUTH FORENSIC REMEDIATION PLAN'
    '========================================='
    ''
    "Version                  = $Version"
    "ParentRunId              = $ParentRunId"
    "TriageRunId              = $TriageRunId"
    "ProjectRoot              = $ProjectRoot"
    'Mode                     = READ_ONLY'
    'FailClosed               = TRUE'
    'SourceMutationAllowed    = FALSE'
    'SourceExecutionAllowed  = FALSE'
    'AutomaticCorrection      = FALSE'
    ''
    "VERDICT                  = $Verdict"
    ''
    'COUNTS'
    '------'
    "ProblemsAnalyzed         = $($PlanEntries.Count)"
    "CriticalFindings         = $($CriticalFindings.Count)"
    "HighFindings             = $($HighFindings.Count)"
    "PowerShellProblems       = $($PowerShellEntries.Count)"
    "JsonProblems             = $($JsonEntries.Count)"
    "EmptyFiles               = $($EmptyEntries.Count)"
    "UnknownProblems          = $($UnknownEntries.Count)"
    "PathFailures             = $($PathFailures.Count)"
    "ReadFailures             = $($ReadFailures.Count)"
    "HashFailures             = $($HashFailures.Count)"
    ''
    'CRITICAL FINDINGS'
    '-----------------'
)

if ($CriticalFindings.Count -eq 0) {

    $SummaryLines += 'NONE'
}
else {

    foreach ($Finding in $CriticalFindings) {

        $SummaryLines += (
            '{0}' -f
            (
                ($Finding | ConvertTo-Json -Depth 20 -Compress)
            )
        )
    }
}

$SummaryLines += ''
$SummaryLines += 'POWERSHELL SYNTAX PROBLEMS'
$SummaryLines += '--------------------------'

if ($PowerShellEntries.Count -eq 0) {

    $SummaryLines += 'NONE'
}
else {

    foreach ($Entry in $PowerShellEntries) {

        $SummaryLines += (
            '[{0}] {1} :: {2} :: LINE={3} :: {4}' -f
            [string]$Entry.ErrorId,
            [string]$Entry.Path,
            [string]$Entry.Message,
            [string]$Entry.Line,
            [string]$Entry.RootCauseHypothesis
        )
    }
}

$SummaryLines += ''
$SummaryLines += 'JSON SYNTAX PROBLEMS'
$SummaryLines += '--------------------'

if ($JsonEntries.Count -eq 0) {

    $SummaryLines += 'NONE'
}
else {

    foreach ($Entry in $JsonEntries) {

        $SummaryLines += (
            '{0} :: {1}' -f
            [string]$Entry.Path,
            [string]$Entry.Message
        )
    }
}

$SummaryLines += ''
$SummaryLines += 'EMPTY FILES'
$SummaryLines += '-----------'

$SummaryLines += (
    'Count = {0}' -f
    $EmptyEntries.Count
)

$SummaryLines += ''
$SummaryLines += 'REPORTS'
$SummaryLines += '-------'
$SummaryLines += "PlanJson   = $PlanPath"
$SummaryLines += "Evidence   = $EvidencePath"
$SummaryLines += "Summary    = $SummaryPath"

$SummaryLines += ''
$SummaryLines += 'SAFETY'
$SummaryLines += '------'
$SummaryLines += 'NO SOURCE FILE WAS MODIFIED.'
$SummaryLines += 'NO SOURCE FILE WAS DELETED.'
$SummaryLines += 'NO POWERSHELL FILE WAS EXECUTED.'
$SummaryLines += 'NO AUTOMATIC CORRECTION WAS PERFORMED.'
$SummaryLines += 'THE ORIGINAL TRIAGE REPORT WAS NOT MODIFIED.'

$SummaryLines |
    Set-Content `
        -LiteralPath $SummaryPath `
        -Encoding utf8 `
        -ErrorAction Stop

# ============================================================================
# FINAL CONSOLE
# ============================================================================

Write-Host ''
Write-Host '============================================================' `
    -ForegroundColor Cyan

Write-Host ' E-ZZIO — REMEDIATION PLAN COMPLETE' `
    -ForegroundColor Cyan

Write-Host '============================================================' `
    -ForegroundColor Cyan

Write-Host ''

Write-Host "PROBLEMS ANALYZED     : $($PlanEntries.Count)"
Write-Host "CRITICAL FINDINGS     : $($CriticalFindings.Count)"
Write-Host "HIGH FINDINGS         : $($HighFindings.Count)"
Write-Host "POWERSHELL PROBLEMS   : $($PowerShellEntries.Count)"
Write-Host "JSON PROBLEMS         : $($JsonEntries.Count)"
Write-Host "EMPTY FILES           : $($EmptyEntries.Count)"
Write-Host "UNKNOWN PROBLEMS      : $($UnknownEntries.Count)"
Write-Host ''

Write-Host "PATH FAILURES         : $($PathFailures.Count)"
Write-Host "READ FAILURES         : $($ReadFailures.Count)"
Write-Host "HASH FAILURES         : $($HashFailures.Count)"
Write-Host ''

if ($Verdict -eq 'FORENSIC_FAIL_CLOSED') {

    Write-Host (
        "TRUTH STATUS          : $Verdict"
    ) -ForegroundColor Red
}
elseif ($Verdict -eq 'REMEDIATION_REQUIRED_CRITICAL') {

    Write-Host (
        "TRUTH STATUS          : $Verdict"
    ) -ForegroundColor Red
}
elseif ($Verdict -eq 'REMEDIATION_REQUIRED') {

    Write-Host (
        "TRUTH STATUS          : $Verdict"
    ) -ForegroundColor Yellow
}
else {

    Write-Host (
        "TRUTH STATUS          : $Verdict"
    ) -ForegroundColor Green
}

Write-Host ''

Write-Host 'OUTPUTS:' `
    -ForegroundColor DarkCyan

Write-Host "  $PlanPath"
Write-Host "  $EvidencePath"
Write-Host "  $SummaryPath"

Write-Host ''

Write-Host 'IMPORTANT:' `
    -ForegroundColor Yellow

Write-Host 'No E-ZZIO source file was modified.'
Write-Host 'No discovered PowerShell file was executed.'
Write-Host 'No automatic correction was performed.'
Write-Host 'The original forensic reports were not modified.'

Write-Host ''
Write-Host '============================================================' `
    -ForegroundColor Cyan