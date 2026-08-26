# ============================================================================
# E-ZZIO — TRUTH ROOT-CAUSE ANALYZER v1.0.0
# ============================================================================
# PURPOSE
#   Forensic root-cause analysis of EZZIO_TRUTH_FORENSIC_FINDINGS.json.
#
# MODE
#   READ-ONLY
#   FAIL-CLOSED
#   NO EXECUTION OF TARGET SCRIPTS
#   NO PROJECT MUTATION
#   NO AUTO-REPAIR
#
# OUTPUT
#   CRITICAL_TRIAGE\
#       ROOT_CAUSE_ANALYSIS.json
#       ROOT_CAUSE_BY_FAMILY.csv
#       ROOT_CAUSE_BY_FILE.csv
#       REPAIR_PLAN.json
#       ROOT_CAUSE_REPORT.txt
#
# IMPORTANT
#   This analyzer analyzes findings.
#   It does NOT repair the project.
#   It does NOT execute discovered PowerShell scripts.
# ============================================================================

[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [string]$ProjectRoot = 'G:\AI\E-zzio',

    [Parameter(Mandatory = $false)]
    [string]$FindingsPath = '',

    [Parameter(Mandatory = $false)]
    [switch]$NoAutoDiscover
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ============================================================================
# GLOBAL CONSTANTS
# ============================================================================

$AnalyzerName    = 'EZZIO_TRUTH_ROOT_CAUSE_ANALYZER'
$AnalyzerVersion = '1.0.0'

$Script:FatalErrors = [System.Collections.Generic.List[object]]::new()

# ============================================================================
# HELPERS
# ============================================================================

function New-Id {
    param(
        [Parameter(Mandatory = $true)]
        [string]$InputText
    )

    $sha = [System.Security.Cryptography.SHA256]::Create()

    try {
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($InputText)
        $hash  = $sha.ComputeHash($bytes)

        return (
            [System.BitConverter]::ToString($hash)
        ).Replace('-', '').ToLowerInvariant().Substring(0, 16)
    }
    finally {
        $sha.Dispose()
    }
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

function Get-ErrorId {
    param(
        [AllowNull()]
        [object]$Finding
    )

    $id = Get-SafeString $Finding.ErrorId

    if ([string]::IsNullOrWhiteSpace($id)) {
        $id = Get-SafeString $Finding.Original.ErrorId
    }

    if ([string]::IsNullOrWhiteSpace($id)) {
        $id = 'UNKNOWN_ERROR_ID'
    }

    return $id
}

function Get-FindingType {
    param(
        [AllowNull()]
        [object]$Finding
    )

    $type = Get-SafeString $Finding.Type

    if ([string]::IsNullOrWhiteSpace($type)) {
        $type = Get-SafeString $Finding.Original.Type
    }

    if ([string]::IsNullOrWhiteSpace($type)) {
        $type = 'UNKNOWN'
    }

    return $type
}

function Get-FindingMessage {
    param(
        [AllowNull()]
        [object]$Finding
    )

    $message = Get-SafeString $Finding.Message

    if ([string]::IsNullOrWhiteSpace($message)) {
        $message = Get-SafeString $Finding.Original.Message
    }

    return $message
}

function Get-FindingPath {
    param(
        [AllowNull()]
        [object]$Finding
    )

    $path = Get-SafeString $Finding.Path

    if ([string]::IsNullOrWhiteSpace($path)) {
        return ''
    }

    return $path.Replace('/', '\')
}

function Test-ExternalArtifact {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $normalized = $Path.Replace('/', '\').ToLowerInvariant()

    $patterns = @(
        '\.venv\',
        '\venv\',
        '\node_modules\',
        '\site-packages\',
        '\__pycache__\',
        '\.git\',
        '\packages\',
        '\vendor\',
        '\third_party\',
        '\external\'
    )

    foreach ($pattern in $patterns) {
        if ($normalized.Contains($pattern)) {
            return $true
        }
    }

    return $false
}

function Get-ArtifactClass {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if ([string]::IsNullOrWhiteSpace($Path)) {
        return 'AGGREGATE'
    }

    if (Test-ExternalArtifact -Path $Path) {
        return 'EXTERNAL_OR_VENDOR_ARTIFACT'
    }

    if ($Path.ToLowerInvariant().EndsWith('.ps1')) {
        return 'PROJECT_POWERSHELL'
    }

    if ($Path.ToLowerInvariant().EndsWith('.json')) {
        return 'PROJECT_JSON'
    }

    return 'PROJECT_OTHER'
}

function Get-Family {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Type,

        [Parameter(Mandatory = $true)]
        [string]$ErrorId,

        [Parameter(Mandatory = $true)]
        [string]$Message,

        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $blob = (
        "$Type`n$ErrorId`n$Message`n$Path"
    ).ToLowerInvariant()

    # ------------------------------------------------------------------------
    # JSON
    # ------------------------------------------------------------------------

    if (
        $blob.Contains('json') -or
        $blob.Contains('convertfrom-json') -or
        $blob.Contains('additional text encountered') -or
        $blob.Contains('json_syntax')
    ) {
        return 'JSON_STRUCTURE'
    }

    # ------------------------------------------------------------------------
    # USING DIRECTIVES
    # ------------------------------------------------------------------------

    if (
        $ErrorId -eq 'MissingUsingStatementDirective' -or
        $ErrorId -eq 'UsingMustBeAtStartOfScript' -or
        $blob.Contains('using directive')
    ) {
        return 'POWERSHELL_USING_DIRECTIVE'
    }

    # ------------------------------------------------------------------------
    # BRACKET / PARENTHESIS / BRACE BALANCE
    # ------------------------------------------------------------------------

    if (
        $ErrorId -eq 'MissingEndParenthesisInMethodCall' -or
        $ErrorId -eq 'MissingEndParenthesisAfterStatement' -or
        $ErrorId -eq 'MissingEndCurlyBrace' -or
        $ErrorId -eq 'EndSquareBracketExpectedAtEndOfAttribute' -or
        $ErrorId -eq 'UnexpectedToken' -and (
            $Message.Contains('Unexpected token'') -or
            $Message.Contains('Unexpected token ''}') -or
            $Message.Contains('Unexpected token ''(')
        )
    ) {
        return 'POWERSHELL_DELIMITER_STRUCTURE'
    }

    # ------------------------------------------------------------------------
    # TRY/CATCH
    # ------------------------------------------------------------------------

    if (
        $ErrorId -eq 'MissingCatchOrFinally' -or
        $blob.Contains('try statement is missing')
    ) {
        return 'POWERSHELL_EXCEPTION_STRUCTURE'
    }

    # ------------------------------------------------------------------------
    # STRING TERMINATION
    # ------------------------------------------------------------------------

    if (
        $ErrorId -eq 'TerminatorExpectedAtEndOfString' -or
        $blob.Contains('string is missing the terminator')
    ) {
        return 'POWERSHELL_STRING_TERMINATION'
    }

    # ------------------------------------------------------------------------
    # VARIABLE REFERENCES
    # ------------------------------------------------------------------------

    if (
        $ErrorId -eq 'InvalidVariableReferenceWithDrive' -or
        $blob.Contains('variable reference is not valid')
    ) {
        return 'POWERSHELL_VARIABLE_REFERENCE'
    }

    # ------------------------------------------------------------------------
    # OPERATOR / EXPRESSION
    # ------------------------------------------------------------------------

    if (
        $ErrorId -eq 'ExpectedValueExpression' -or
        $blob.Contains('value expression following the') -or
        $blob.Contains('unexpected token ''ne''') -or
        $blob.Contains('operator')
    ) {
        return 'POWERSHELL_EXPRESSION_STRUCTURE'
    }

    # ------------------------------------------------------------------------
    # GENERIC POWERSHELL SYNTAX
    # ------------------------------------------------------------------------

    if (
        $Type -eq 'POWERSHELL_SYNTAX_ERROR' -or
        $blob.Contains('powershell syntax')
    ) {
        return 'POWERSHELL_SYNTAX_GENERAL'
    }

    return 'OTHER'
}

function Get-PrimaryLikelihood {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Family,

        [Parameter(Mandatory = $true)]
        [string]$ErrorId,

        [Parameter(Mandatory = $true)]
        [string]$Message
    )

    # Explicit parser errors that usually indicate a local structural defect.
    $high = @(
        'MissingEndParenthesisInMethodCall',
        'MissingEndCurlyBrace',
        'MissingCatchOrFinally',
        'TerminatorExpectedAtEndOfString',
        'EndSquareBracketExpectedAtEndOfAttribute',
        'ExpectedValueExpression',
        'InvalidVariableReferenceWithDrive',
        'MissingUsingStatementDirective'
    )

    if ($high -contains $ErrorId) {
        return 'HIGH'
    }

    if ($ErrorId -eq 'UsingMustBeAtStartOfScript') {
        return 'MEDIUM'
    }

    if ($ErrorId -eq 'UnexpectedToken') {
        return 'MEDIUM'
    }

    if ($Family -eq 'JSON_STRUCTURE') {
        return 'HIGH'
    }

    return 'LOW'
}

function Get-CauseMechanism {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Family,

        [Parameter(Mandatory = $true)]
        [string]$ErrorId,

        [Parameter(Mandatory = $true)]
        [string]$Message
    )

    switch ($Family) {

        'POWERSHELL_DELIMITER_STRUCTURE' {
            return 'Unbalanced or malformed PowerShell syntactic delimiter.'
        }

        'POWERSHELL_USING_DIRECTIVE' {
            return 'Invalid placement or malformed PowerShell using directive.'
        }

        'POWERSHELL_EXCEPTION_STRUCTURE' {
            return 'Incomplete try/catch/finally control structure.'
        }

        'POWERSHELL_STRING_TERMINATION' {
            return 'Unterminated PowerShell string literal.'
        }

        'POWERSHELL_VARIABLE_REFERENCE' {
            return 'Malformed PowerShell variable reference.'
        }

        'POWERSHELL_EXPRESSION_STRUCTURE' {
            return 'Malformed operator or expression structure.'
        }

        'JSON_STRUCTURE' {
            return 'JSON document contains invalid top-level structure or multiple JSON values.'
        }

        'POWERSHELL_SYNTAX_GENERAL' {
            return 'PowerShell parser rejected the source syntax.'
        }

        default {
            return 'No deterministic root-cause mechanism identified.'
        }
    }
}

function Get-RepairPriority {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Family,

        [Parameter(Mandatory = $true)]
        [string]$ArtifactClass
    )

    if ($ArtifactClass -eq 'EXTERNAL_OR_VENDOR_ARTIFACT') {
        return 'DEFER_EXTERNAL'
    }

    switch ($Family) {

        'POWERSHELL_STRING_TERMINATION' {
            return 'P1'
        }

        'POWERSHELL_DELIMITER_STRUCTURE' {
            return 'P1'
        }

        'POWERSHELL_EXPRESSION_STRUCTURE' {
            return 'P1'
        }

        'POWERSHELL_VARIABLE_REFERENCE' {
            return 'P1'
        }

        'POWERSHELL_EXCEPTION_STRUCTURE' {
            return 'P1'
        }

        'POWERSHELL_USING_DIRECTIVE' {
            return 'P1'
        }

        'JSON_STRUCTURE' {
            return 'P1'
        }

        default {
            return 'P2'
        }
    }
}

function Get-RootSignature {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,

        [Parameter(Mandatory = $true)]
        [string]$Family,

        [Parameter(Mandatory = $true)]
        [string]$ErrorId,

        [Parameter(Mandatory = $true)]
        [string]$Message
    )

    # The message itself is deliberately normalized so that parser cascades
    # with different wording can still converge onto one root signature.
    $normalizedMessage = $Message.ToLowerInvariant()

    $normalizedMessage = [regex]::Replace(
        $normalizedMessage,
        '\d+',
        '#'
    )

    $normalizedMessage = [regex]::Replace(
        $normalizedMessage,
        '\s+',
        ' '
    ).Trim()

    return New-Id (
        "$Path|$Family|$ErrorId|$normalizedMessage"
    )
}

function Assert-Condition {
    param(
        [Parameter(Mandatory = $true)]
        [bool]$Condition,

        [Parameter(Mandatory = $true)]
        [string]$Message
    )

    if (-not $Condition) {
        throw "INTERNAL QUALITY GATE FAILURE: $Message"
    }
}

# ============================================================================
# PROJECT ROOT VALIDATION
# ============================================================================

if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) {
    throw "ProjectRoot does not exist: $ProjectRoot"
}

# ============================================================================
# FINDINGS DISCOVERY
# ============================================================================

if ([string]::IsNullOrWhiteSpace($FindingsPath)) {

    if ($NoAutoDiscover) {
        throw 'FindingsPath is empty and NoAutoDiscover was specified.'
    }

    $reportRoot = Join-Path $ProjectRoot '_EZZIO_TRUTH_REPORTS'

    if (-not (Test-Path -LiteralPath $reportRoot -PathType Container)) {
        throw "Truth report root does not exist: $reportRoot"
    }

    $candidates = @(
        Get-ChildItem `
            -LiteralPath $reportRoot `
            -Filter 'EZZIO_TRUTH_FORENSIC_FINDINGS.json' `
            -File `
            -Recurse `
            -ErrorAction Stop |
        Sort-Object LastWriteTimeUtc -Descending
    )

    if ($candidates.Count -eq 0) {
        throw 'No EZZIO_TRUTH_FORENSIC_FINDINGS.json found.'
    }

    $FindingsPath = $candidates[0].FullName
}

if (-not (Test-Path -LiteralPath $FindingsPath -PathType Leaf)) {
    throw "Findings file does not exist: $FindingsPath"
}

# ============================================================================
# LOAD FINDINGS
# ============================================================================

Write-Host ''
Write-Host '============================================================================' -ForegroundColor Cyan
Write-Host ' E-ZZIO — TRUTH ROOT-CAUSE ANALYZER v1.0.0' -ForegroundColor Cyan
Write-Host '============================================================================' -ForegroundColor Cyan
Write-Host ''
Write-Host "PROJECT : $ProjectRoot"
Write-Host "FINDINGS: $FindingsPath"
Write-Host 'MODE    : READ-ONLY / FAIL-CLOSED / NO EXECUTION / NO MUTATION'
Write-Host ''

try {
    $rawJson = Get-Content `
        -LiteralPath $FindingsPath `
        -Raw `
        -Encoding UTF8 `
        -ErrorAction Stop

    $document = $rawJson | ConvertFrom-Json -Depth 100 -ErrorAction Stop
}
catch {
    throw "Cannot load findings JSON: $($_.Exception.Message)"
}

# ============================================================================
# NORMALIZE TOP LEVEL
# ============================================================================

$findings = [System.Collections.Generic.List[object]]::new()

if ($document -is [System.Array]) {

    foreach ($item in $document) {
        if ($null -ne $item) {
            $findings.Add($item)
        }
    }

}
elseif ($null -ne $document) {

    $findings.Add($document)
}

if ($findings.Count -eq 0) {
    throw 'Findings document contains no findings.'
}

# ============================================================================
# EXPAND AGGREGATE FINDINGS
# ============================================================================

$expanded = [System.Collections.Generic.List[object]]::new()

foreach ($container in $findings) {

    $severity = Get-SafeString $container.Severity
    $code     = Get-SafeString $container.Code
    $path     = Get-FindingPath $container

    $evidence = $container.Evidence

    if ($null -eq $evidence) {

        $expanded.Add(
            [pscustomobject]@{
                Severity = $severity
                Code     = $code
                Path     = $path
                Type     = Get-FindingType $container
                ErrorId  = Get-ErrorId $container
                Message  = Get-FindingMessage $container
                Extent   = Get-SafeString $container.Extent
                Source   = 'TOP_LEVEL'
            }
        )

        continue
    }

    $evidenceItems = @($evidence)

    foreach ($ev in $evidenceItems) {

        if ($null -eq $ev) {
            continue
        }

        $evPath = Get-FindingPath $ev

        if ([string]::IsNullOrWhiteSpace($evPath)) {
            $evPath = $path
        }

        $expanded.Add(
            [pscustomobject]@{
                Severity = $severity
                Code     = $code
                Path     = $evPath
                Type     = Get-FindingType $ev
                ErrorId  = Get-ErrorId $ev
                Message  = Get-FindingMessage $ev
                Extent   = Get-SafeString $ev.Extent
                Source   = 'EVIDENCE'
            }
        )
    }
}

if ($expanded.Count -eq 0) {
    throw 'No usable evidence was extracted from findings.'
}

# ============================================================================
# ANALYZE
# ============================================================================

Write-Host '[1/6] Classification des findings...' -ForegroundColor Yellow

$analysis = [System.Collections.Generic.List[object]]::new()

foreach ($finding in $expanded) {

    $family = Get-Family `
        -Type $finding.Type `
        -ErrorId $finding.ErrorId `
        -Message $finding.Message `
        -Path $finding.Path

    $artifactClass = Get-ArtifactClass -Path $finding.Path

    $likelihood = Get-PrimaryLikelihood `
        -Family $family `
        -ErrorId $finding.ErrorId `
        -Message $finding.Message

    $mechanism = Get-CauseMechanism `
        -Family $family `
        -ErrorId $finding.ErrorId `
        -Message $finding.Message

    $priority = Get-RepairPriority `
        -Family $family `
        -ArtifactClass $artifactClass

    $signature = Get-RootSignature `
        -Path $finding.Path `
        -Family $family `
        -ErrorId $finding.ErrorId `
        -Message $finding.Message

    $analysis.Add(
        [pscustomobject]@{
            FindingId       = New-Id (
                "$($finding.Path)|$($finding.Type)|$($finding.ErrorId)|$($finding.Message)"
            )
            Severity        = $finding.Severity
            Code            = $finding.Code
            Path            = $finding.Path
            ArtifactClass   = $artifactClass
            Type            = $finding.Type
            ErrorId         = $finding.ErrorId
            Message         = $finding.Message
            Extent          = $finding.Extent
            Family          = $family
            RootSignature   = $signature
            PrimaryLikelihood = $likelihood
            Mechanism       = $mechanism
            RepairPriority  = $priority
        }
    )
}

# ============================================================================
# DEDUPLICATE EXACT FINDINGS
# ============================================================================

Write-Host '[2/6] Déduplication déterministe...' -ForegroundColor Yellow

$uniqueFindings = @(
    $analysis |
    Group-Object FindingId |
    ForEach-Object {
        $_.Group[0]
    }
)

# ============================================================================
# ROOT SIGNATURE GROUPING
# ============================================================================

Write-Host '[3/6] Construction des causes racines...' -ForegroundColor Yellow

$rootGroups = @(
    $uniqueFindings |
    Group-Object RootSignature |
    Sort-Object Count -Descending
)

$rootCauses = [System.Collections.Generic.List[object]]::new()

$rootIndex = 0

foreach ($group in $rootGroups) {

    $rootIndex++

    $items = @($group.Group)

    $representative = $items[0]

    $isExternal = (
        $items.ArtifactClass |
        Where-Object {
            $_ -eq 'EXTERNAL_OR_VENDOR_ARTIFACT'
        }
    ).Count -gt 0

    $classification = 'ROOT_CANDIDATE'

    if ($items.Count -gt 1) {
        $classification = 'ROOT_CANDIDATE_WITH_CASCADE'
    }

    if ($isExternal) {
        $classification = 'EXTERNAL_ARTIFACT'
    }

    $rootCauses.Add(
        [pscustomobject]@{
            RootCauseId        = ('RC-{0:D4}' -f $rootIndex)
            RootSignature      = $group.Name
            Classification     = $classification
            Family             = $representative.Family
            Path               = $representative.Path
            ArtifactClass      = $representative.ArtifactClass
            ErrorIds           = @(
                $items |
                Select-Object -ExpandProperty ErrorId -Unique |
                Sort-Object
            )
            FindingCount       = $items.Count
            PrimaryLikelihood  = $representative.PrimaryLikelihood
            RepairPriority     = $representative.RepairPriority
            Mechanism          = $representative.Mechanism
            Findings           = @(
                $items |
                Select-Object `
                    FindingId,
                    Severity,
                    Type,
                    ErrorId,
                    Message,
                    Extent
            )
        }
    )
}

# ============================================================================
# FILE AGGREGATION
# ============================================================================

Write-Host '[4/6] Agrégation par fichier...' -ForegroundColor Yellow

$fileGroups = @(
    $uniqueFindings |
    Where-Object {
        -not [string]::IsNullOrWhiteSpace($_.Path)
    } |
    Group-Object Path |
    Sort-Object Count -Descending
)

$fileSummary = [System.Collections.Generic.List[object]]::new()

foreach ($group in $fileGroups) {

    $items = @($group.Group)

    $families = @(
        $items |
        Select-Object -ExpandProperty Family -Unique |
        Sort-Object
    )

    $rootCount = @(
        $items |
        Select-Object -ExpandProperty RootSignature -Unique
    ).Count

    $external = (
        $items.ArtifactClass |
        Where-Object {
            $_ -eq 'EXTERNAL_OR_VENDOR_ARTIFACT'
        }
    ).Count -gt 0

    $fileSummary.Add(
        [pscustomobject]@{
            Path             = $group.Name
            FindingCount     = $items.Count
            RootCauseCount   = $rootCount
            Families         = ($families -join ';')
            ArtifactClass    = $items[0].ArtifactClass
            ExternalArtifact = $external
            HighestPriority  = (
                $items.RepairPriority |
                Where-Object { $_ -ne 'DEFER_EXTERNAL' } |
                Select-Object -First 1
            )
        }
    )
}

# ============================================================================
# FAMILY AGGREGATION
# ============================================================================

Write-Host '[5/6] Agrégation par famille...' -ForegroundColor Yellow

$familySummary = [System.Collections.Generic.List[object]]::new()

$familyGroups = @(
    $uniqueFindings |
    Group-Object Family |
    Sort-Object Count -Descending
)

foreach ($group in $familyGroups) {

    $items = @($group.Group)

    $familySummary.Add(
        [pscustomobject]@{
            Family          = $group.Name
            FindingCount    = $items.Count
            FileCount       = @(
                $items |
                Select-Object -ExpandProperty Path -Unique
            ).Count
            RootCauseCount  = @(
                $items |
                Select-Object -ExpandProperty RootSignature -Unique
            ).Count
            P1Count         = @(
                $items |
                Where-Object {
                    $_.RepairPriority -eq 'P1'
                }
            ).Count
            ExternalCount   = @(
                $items |
                Where-Object {
                    $_.ArtifactClass -eq 'EXTERNAL_OR_VENDOR_ARTIFACT'
                }
            ).Count
        }
    )
}

# ============================================================================
# CASCADE HEURISTICS
# ============================================================================
#
# IMPORTANT:
# This is NOT a claim that parser diagnostics are mathematically proven
# dependent. The analyzer therefore calls these "CASCADE_CANDIDATE".
# Certification must not silently delete them.
# ============================================================================

$cascadeCandidates = [System.Collections.Generic.List[object]]::new()

$byFile = @(
    $uniqueFindings |
    Where-Object {
        -not [string]::IsNullOrWhiteSpace($_.Path)
    } |
    Group-Object Path
)

foreach ($fileGroup in $byFile) {

    $items = @(
        $fileGroup.Group |
        Sort-Object `
            @{ Expression = {
                switch ($_.ErrorId) {
                    'TerminatorExpectedAtEndOfString' { 1 }
                    'MissingEndParenthesisInMethodCall' { 2 }
                    'MissingEndParenthesisAfterStatement' { 3 }
                    'MissingEndCurlyBrace' { 4 }
                    'MissingCatchOrFinally' { 5 }
                    default { 100 }
                }
            }}
    )

    if ($items.Count -lt 2) {
        continue
    }

    $hasPrimaryStructural = @(
        $items |
        Where-Object {
            $_.ErrorId -in @(
                'TerminatorExpectedAtEndOfString',
                'MissingEndParenthesisInMethodCall',
                'MissingEndParenthesisAfterStatement',
                'MissingEndCurlyBrace',
                'MissingCatchOrFinally'
            )
        }
    ).Count -gt 0

    if (-not $hasPrimaryStructural) {
        continue
    }

    foreach ($item in $items) {

        if (
            $item.ErrorId -in @(
                'UnexpectedToken',
                'UsingMustBeAtStartOfScript'
            )
        ) {

            $cascadeCandidates.Add(
                [pscustomobject]@{
                    FindingId       = $item.FindingId
                    Path            = $item.Path
                    ErrorId         = $item.ErrorId
                    Family          = $item.Family
                    Classification  = 'CASCADE_CANDIDATE'
                    Reason          = 'Secondary parser diagnostic in a file containing a higher-priority structural syntax defect.'
                }
            )
        }
    }
}

# ============================================================================
# QUALITY GATES
# ============================================================================

Write-Host '[6/6] Vérification des invariants forensic...' -ForegroundColor Yellow

$totalInput = $expanded.Count
$totalUnique = $uniqueFindings.Count
$totalRoots = $rootCauses.Count
$totalFiles = $fileSummary.Count

Assert-Condition `
    -Condition ($totalInput -ge $totalUnique) `
    -Message 'Unique findings cannot exceed expanded findings.'

Assert-Condition `
    -Condition ($totalUnique -gt 0) `
    -Message 'Unique finding count is zero.'

Assert-Condition `
    -Condition ($totalRoots -gt 0) `
    -Message 'Root cause count is zero despite findings.'

$sumFamily = (
    $familySummary |
    Measure-Object -Property FindingCount -Sum
).Sum

Assert-Condition `
    -Condition ([int]$sumFamily -eq $totalUnique) `
    -Message 'Family aggregation does not reconcile with unique findings.'

$sumFiles = (
    $fileSummary |
    Measure-Object -Property FindingCount -Sum
).Sum

Assert-Condition `
    -Condition ([int]$sumFiles -eq (
        @(
            $uniqueFindings |
            Where-Object {
                -not [string]::IsNullOrWhiteSpace($_.Path)
            }
        ).Count
    )) `
    -Message 'File aggregation does not reconcile with findings having paths.'

# ============================================================================
# VERDICT
# ============================================================================

$criticalCount = @(
    $uniqueFindings |
    Where-Object {
        $_.Severity -eq 'CRITICAL'
    }
).Count

$warningCount = @(
    $uniqueFindings |
    Where-Object {
        $_.Severity -eq 'WARNING'
    }
).Count

$errorCount = @(
    $uniqueFindings |
    Where-Object {
        $_.Severity -eq 'ERROR'
    }
).Count

$unresolvedCritical = $criticalCount

$verdict = 'FAIL'

if ($unresolvedCritical -eq 0 -and $errorCount -eq 0) {
    $verdict = 'PASS_WITHOUT_CRITICALS'
}

# CERTIFIED is deliberately impossible for this analyzer.
# This tool is diagnostic only.
$certification = 'NOT_CERTIFIABLE_BY_TRIAGE_TOOL'

# ============================================================================
# OUTPUT DIRECTORY
# ============================================================================

$findingsDirectory = Split-Path -Parent $FindingsPath
$triageRoot = Join-Path $findingsDirectory 'CRITICAL_ROOT_CAUSE_ANALYSIS'

if (Test-Path -LiteralPath $triageRoot) {
    $suffix = Get-Date -Format 'yyyyMMdd_HHmmss_fff'
    $triageRoot = Join-Path `
        $findingsDirectory `
        ("CRITICAL_ROOT_CAUSE_ANALYSIS_{0}" -f $suffix)
}

New-Item `
    -ItemType Directory `
    -Path $triageRoot `
    -Force `
    -ErrorAction Stop |
    Out-Null

# ============================================================================
# ROOT CAUSE JSON
# ============================================================================

$analysisDocument = [ordered]@{
    Analyzer = [ordered]@{
        Name    = $AnalyzerName
        Version = $AnalyzerVersion
        Mode    = 'READ_ONLY_FAIL_CLOSED_NO_EXECUTION_NO_MUTATION'
    }

    Execution = [ordered]@{
        TimestampUtc = (Get-Date).ToUniversalTime().ToString('o')
        Computer     = $env:COMPUTERNAME
        PowerShell   = $PSVersionTable.PSVersion.ToString()
    }

    Input = [ordered]@{
        ProjectRoot = $ProjectRoot
        FindingsPath = $FindingsPath
        ExpandedFindings = $totalInput
        UniqueFindings   = $totalUnique
    }

    Summary = [ordered]@{
        Critical        = $criticalCount
        Error           = $errorCount
        Warning         = $warningCount
        FilesAffected   = $totalFiles
        RootCauseGroups = $totalRoots
        CascadeCandidates = $cascadeCandidates.Count
    }

    Verdict = [ordered]@{
        Verdict = $verdict
        Certification = $certification
        FailClosed = ($unresolvedCritical -gt 0)
    }

    FamilySummary = @($familySummary)

    FileSummary = @($fileSummary)

    RootCauses = @($rootCauses)

    CascadeCandidates = @($cascadeCandidates)

    QualityGates = [ordered]@{
        InputLoaded       = $true
        FindingsExpanded  = ($totalInput -gt 0)
        FindingsUnique    = ($totalUnique -gt 0)
        FamiliesReconciled = ([int]$sumFamily -eq $totalUnique)
        FilesReconciled    = $true
        FailClosed         = ($unresolvedCritical -gt 0)
        NoProjectMutation  = $true
        TargetScriptsExecuted = $false
    }
}

$jsonPath = Join-Path $triageRoot 'ROOT_CAUSE_ANALYSIS.json'

$analysisDocument |
    ConvertTo-Json -Depth 100 |
    Set-Content `
        -LiteralPath $jsonPath `
        -Encoding UTF8 `
        -ErrorAction Stop

# ============================================================================
# FAMILY CSV
# ============================================================================

$familyCsv = Join-Path $triageRoot 'ROOT_CAUSE_BY_FAMILY.csv'

$familySummary |
    Export-Csv `
        -LiteralPath $familyCsv `
        -NoTypeInformation `
        -Encoding UTF8 `
        -ErrorAction Stop

# ============================================================================
# FILE CSV
# ============================================================================

$fileCsv = Join-Path $triageRoot 'ROOT_CAUSE_BY_FILE.csv'

$fileSummary |
    Export-Csv `
        -LiteralPath $fileCsv `
        -NoTypeInformation `
        -Encoding UTF8 `
        -ErrorAction Stop

# ============================================================================
# REPAIR PLAN
# ============================================================================

$repairItems = [System.Collections.Generic.List[object]]::new()

foreach ($root in $rootCauses) {

    $repairItems.Add(
        [pscustomobject]@{
            RootCauseId       = $root.RootCauseId
            Path              = $root.Path
            ArtifactClass     = $root.ArtifactClass
            Family            = $root.Family
            FindingCount      = $root.FindingCount
            Priority          = $root.RepairPriority
            Classification    = $root.Classification
            Mechanism         = $root.Mechanism
            Action            = if (
                $root.ArtifactClass -eq 'EXTERNAL_OR_VENDOR_ARTIFACT'
            ) {
                'DO_NOT_REPAIR_AUTOMATICALLY; REVIEW_SCOPE'
            }
            else {
                'MANUAL_OR_CONTROLLED_REPAIR_REQUIRED'
            }
            Validation        = 'RE-RUN_TRUTH_FORENSIC_AFTER_REPAIR'
        }
    )
}

$repairDocument = [ordered]@{
    Mode = 'PLAN_ONLY'
    ProjectMutation = $false
    AutomaticRepair = $false
    GeneratedUtc = (Get-Date).ToUniversalTime().ToString('o')
    Items = @($repairItems)
}

$repairJsonPath = Join-Path $triageRoot 'REPAIR_PLAN.json'

$repairDocument |
    ConvertTo-Json -Depth 50 |
    Set-Content `
        -LiteralPath $repairJsonPath `
        -Encoding UTF8 `
        -ErrorAction Stop

# ============================================================================
# HUMAN REPORT
# ============================================================================

$reportPath = Join-Path $triageRoot 'ROOT_CAUSE_REPORT.txt'

$report = [System.Text.StringBuilder]::new()

[void]$report.AppendLine('============================================================================')
[void]$report.AppendLine(' E-ZZIO — TRUTH ROOT-CAUSE ANALYSIS v1.0.0')
[void]$report.AppendLine('============================================================================')
[void]$report.AppendLine('')
[void]$report.AppendLine("PROJECT ROOT : $ProjectRoot")
[void]$report.AppendLine("FINDINGS     : $FindingsPath")
[void]$report.AppendLine("GENERATED    : $((Get-Date).ToUniversalTime().ToString('o'))")
[void]$report.AppendLine('')
[void]$report.AppendLine('MODE         : READ-ONLY / FAIL-CLOSED / NO EXECUTION / NO MUTATION')
[void]$report.AppendLine('')
[void]$report.AppendLine('----------------------------------------------------------------------------')
[void]$report.AppendLine(' SUMMARY')
[void]$report.AppendLine('----------------------------------------------------------------------------')
[void]$report.AppendLine("Expanded findings : $totalInput")
[void]$report.AppendLine("Unique findings   : $totalUnique")
[void]$report.AppendLine("Critical          : $criticalCount")
[void]$report.AppendLine("Error             : $errorCount")
[void]$report.AppendLine("Warning           : $warningCount")
[void]$report.AppendLine("Files affected    : $totalFiles")
[void]$report.AppendLine("Root groups       : $totalRoots")
[void]$report.AppendLine("Cascade candidates: $($cascadeCandidates.Count)")
[void]$report.AppendLine('')
[void]$report.AppendLine("VERDICT           : $verdict")
[void]$report.AppendLine("CERTIFICATION     : $certification")
[void]$report.AppendLine('')

[void]$report.AppendLine('----------------------------------------------------------------------------')
[void]$report.AppendLine(' CAUSE FAMILIES')
[void]$report.AppendLine('----------------------------------------------------------------------------')

foreach ($row in $familySummary) {

    [void]$report.AppendLine(
        ('{0,-42} Findings={1,4} Files={2,4} Roots={3,4} P1={4,4}' -f `
            $row.Family,
            $row.FindingCount,
            $row.FileCount,
            $row.RootCauseCount,
            $row.P1Count
        )
    )
}

[void]$report.AppendLine('')
[void]$report.AppendLine('----------------------------------------------------------------------------')
[void]$report.AppendLine(' FILES')
[void]$report.AppendLine('----------------------------------------------------------------------------')

foreach ($row in $fileSummary) {

    [void]$report.AppendLine(
        ('{0,4} findings | {1,4} roots | {2}' -f `
            $row.FindingCount,
            $row.RootCauseCount,
            $row.Path
        )
    )
}

[void]$report.AppendLine('')
[void]$report.AppendLine('----------------------------------------------------------------------------')
[void]$report.AppendLine(' ROOT CAUSE GROUPS')
[void]$report.AppendLine('----------------------------------------------------------------------------')

foreach ($root in $rootCauses) {

    [void]$report.AppendLine(
        "$($root.RootCauseId) | $($root.Family) | $($root.RepairPriority) | $($root.Path)"
    )

    [void]$report.AppendLine(
        "  CLASSIFICATION : $($root.Classification)"
    )

    [void]$report.AppendLine(
        "  FINDINGS       : $($root.FindingCount)"
    )

    [void]$report.AppendLine(
        "  MECHANISM      : $($root.Mechanism)"
    )

    [void]$report.AppendLine(
        "  ERROR IDS      : $($root.ErrorIds -join ', ')"
    )

    [void]$report.AppendLine('')
}

[void]$report.AppendLine('----------------------------------------------------------------------------')
[void]$report.AppendLine(' CASCADE CANDIDATES')
[void]$report.AppendLine('----------------------------------------------------------------------------')

if ($cascadeCandidates.Count -eq 0) {

    [void]$report.AppendLine('NONE')

}
else {

    foreach ($cascade in $cascadeCandidates) {

        [void]$report.AppendLine(
            "$($cascade.Path) | $($cascade.ErrorId) | $($cascade.Classification)"
        )
    }
}

[void]$report.AppendLine('')
[void]$report.AppendLine('----------------------------------------------------------------------------')
[void]$report.AppendLine(' QUALITY GATES')
[void]$report.AppendLine('----------------------------------------------------------------------------')
[void]$report.AppendLine('Input loaded             : PASS')
[void]$report.AppendLine('Findings expanded        : PASS')
[void]$report.AppendLine('Findings deduplicated    : PASS')
[void]$report.AppendLine('Family reconciliation    : PASS')
[void]$report.AppendLine('File reconciliation      : PASS')
[void]$report.AppendLine('Target scripts executed  : NO')
[void]$report.AppendLine('Project mutation         : NO')
[void]$report.AppendLine(
    "Fail-closed              : $(if ($unresolvedCritical -gt 0) { 'ACTIVE' } else { 'NOT REQUIRED' })"
)

[void]$report.AppendLine('')
[void]$report.AppendLine('IMPORTANT:')
[void]$report.AppendLine(
    'CASCADE_CANDIDATE is a forensic hypothesis, not permission to delete a finding.'
)
[void]$report.AppendLine(
    'Every repair must be followed by a complete Truth Forensic rescan.'
)
[void]$report.AppendLine('')

$report.ToString() |
    Set-Content `
        -LiteralPath $reportPath `
        -Encoding UTF8 `
        -ErrorAction Stop

# ============================================================================
# FINAL CONSOLE OUTPUT
# ============================================================================

Write-Host ''
Write-Host '============================================================================' -ForegroundColor Green
Write-Host ' E-ZZIO — ROOT-CAUSE ANALYSIS COMPLETE' -ForegroundColor Green
Write-Host '============================================================================' -ForegroundColor Green
Write-Host ''
Write-Host "EXPANDED FINDINGS : $totalInput"
Write-Host "UNIQUE FINDINGS   : $totalUnique"
Write-Host "CRITICAL          : $criticalCount"
Write-Host "ERROR             : $errorCount"
Write-Host "WARNING           : $warningCount"
Write-Host "FILES AFFECTED    : $totalFiles"
Write-Host "ROOT CAUSES       : $totalRoots"
Write-Host "CASCADE CANDIDATES: $($cascadeCandidates.Count)"
Write-Host ''
Write-Host "VERDICT            : $verdict" -ForegroundColor Red
Write-Host ''
Write-Host "TRIAGE ROOT        : $triageRoot"
Write-Host ''
Write-Host "ANALYSIS           : $jsonPath"
Write-Host "FAMILY CSV         : $familyCsv"
Write-Host "FILE CSV           : $fileCsv"
Write-Host "REPAIR PLAN        : $repairJsonPath"
Write-Host "REPORT             : $reportPath"
Write-Host ''
Write-Host 'FAIL-CLOSED : aucune réparation automatique effectuée.' -ForegroundColor Yellow
Write-Host '============================================================================' -ForegroundColor Green
