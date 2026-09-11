#requires -Version 7.0

[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$Root   = 'G:\AI\E-zzio'
$Engine = Join-Path $Root 'Phase2B_v5.2.ps1'

if (-not (Test-Path -LiteralPath $Engine -PathType Leaf)) {
    throw "FAIL-CLOSED: ENGINE_NOT_FOUND: $Engine"
}

$raw = Get-Content -LiteralPath $Engine -Raw
$sourceLines = Get-Content -LiteralPath $Engine

$tokens = $null
$errors = $null

[System.Management.Automation.Language.Parser]::ParseFile(
    $Engine,
    [ref]$tokens,
    [ref]$errors
) | Out-Null

if (@($errors).Count -gt 0) {
    foreach ($e in $errors) {
        Write-Host (
            "[FAIL] {0} @ line {1}, col {2}" -f
            $e.Message,
            $e.Extent.StartLineNumber,
            $e.Extent.StartColumnNumber
        ) -ForegroundColor Red
    }

    throw 'FAIL-CLOSED: ENGINE_PARSE_FAILURE'
}

$hash = (
    Get-FileHash -LiteralPath $Engine -Algorithm SHA256
).Hash.ToLowerInvariant()

Write-Host '============================================================' -ForegroundColor Cyan
Write-Host ' E-ZZIO — PHASE 2B DRYRUN READ-ONLY CERTIFIER' -ForegroundColor Cyan
Write-Host '============================================================' -ForegroundColor Cyan
Write-Host ''
Write-Host "[ENGINE] $Engine"
Write-Host "[SHA256] $hash"
Write-Host ''

# --------------------------------------------------------------------------
# 1. DRYRUN CONTRACT
# --------------------------------------------------------------------------

$drySwitch = [regex]::IsMatch(
    $raw,
    '(?m)\[switch\]\s*\$DryRun'
)

$dryGateMatch = [regex]::Match(
    $raw,
    '(?m)^\s*if\s*\(\s*\$DryRun\s*\)'
)

if (-not $drySwitch) {
    throw 'FAIL-CLOSED: DRYRUN_PARAMETER_MISSING'
}

if (-not $dryGateMatch.Success) {
    throw 'FAIL-CLOSED: DRYRUN_GATE_MISSING'
}

$dryGateLine = (
    $sourceLines |
    Select-String -Pattern '^\s*if\s*\(\s*\$DryRun\s*\)' |
    Select-Object -First 1
).LineNumber

Write-Host '[1] DRYRUN CONTRACT' -ForegroundColor Yellow
Write-Host "[PASS] DryRun parameter : $drySwitch"
Write-Host "[PASS] DryRun gate      : line $dryGateLine"
Write-Host ''

# --------------------------------------------------------------------------
# 2. MUTATION PRIMITIVES
# --------------------------------------------------------------------------

$patterns = @(
    'Remove-Item',
    'Move-Item',
    'Copy-Item',
    'New-Item',
    'Set-Content',
    'Add-Content',
    'Out-File',
    'WriteAllText',
    'WriteAllBytes',
    'FileStream',
    'CreateDirectory',
    'File\.Delete',
    'Directory\.Delete',
    'File\.Move',
    'File\.Copy',
    'File\.Replace'
)

$mutations = [System.Collections.Generic.List[object]]::new()

foreach ($pattern in $patterns) {

    $hits = @(
        Select-String `
            -LiteralPath $Engine `
            -Pattern "(?<![\w-])$pattern(?![\w-])"
    )

    foreach ($hit in $hits) {

        if ($hit.LineNumber -lt $dryGateLine) {

            $mutations.Add(
                [pscustomobject]@{
                    Pattern = $pattern
                    Line    = $hit.LineNumber
                    Text    = $hit.Line.Trim()
                }
            )
        }
    }
}

$mutations = @(
    $mutations |
    Sort-Object Line, Pattern -Unique
)

Write-Host '[2] MUTATIONS BEFORE DRYRUN GATE' -ForegroundColor Yellow
Write-Host "[COUNT] $($mutations.Count)"

foreach ($m in $mutations) {
    Write-Host (
        "[OBSERVED] line {0} | {1} | {2}" -f
        $m.Line,
        $m.Pattern,
        $m.Text
    )
}

Write-Host ''

# --------------------------------------------------------------------------
# 3. STRICT READ-ONLY VERDICT
# --------------------------------------------------------------------------

Write-Host '[3] FINAL VERDICT' -ForegroundColor Yellow

if ($mutations.Count -eq 0) {

    $Verdict = 'DRYRUN_READONLY_CERTIFIED'

    Write-Host '[PASS] Aucun primitive de mutation avant DryRun.' -ForegroundColor Green
    Write-Host '[CERTIFICATION] 100%' -ForegroundColor Green
}
else {

    $Verdict = 'DRYRUN_NOT_READONLY'

    Write-Host '[FAIL] Primitive(s) de mutation avant DryRun détectée(s).' -ForegroundColor Red
    Write-Host '[FAIL-CLOSED] DryRun READ-ONLY non certifiable.' -ForegroundColor Red
    Write-Host '[CERTIFICATION] 0%' -ForegroundColor Red
}

Write-Host ''
Write-Host '============================================================' -ForegroundColor Cyan
Write-Host " VERDICT : $Verdict" -ForegroundColor $(
    if ($Verdict -eq 'DRYRUN_READONLY_CERTIFIED') {
        'Green'
    }
    else {
        'Red'
    }
)
Write-Host ' EXECUTION : NONE' -ForegroundColor Green
Write-Host '============================================================' -ForegroundColor Cyan

if ($Verdict -ne 'DRYRUN_READONLY_CERTIFIED') {
    exit 10
}

exit 0
