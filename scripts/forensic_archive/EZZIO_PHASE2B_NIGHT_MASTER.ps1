#requires -Version 7.0
<#
===============================================================================
 E-ZZIO — PHASE 2B NIGHT MASTER
 Version : 1.1.0
 Mode    : FORENSIC / FAIL-CLOSED / READ-ONLY FIRST

 DEFAULT
 -------
 Recherche + audit statique uniquement.
 Aucune execution du moteur Phase 2B.

 SWITCHES
 --------
 -PrepareRunner
     Cree un runner separe. Ne lance rien.

 -RunDryRun
     Autorise explicitement le lancement du moteur avec -DryRun.

 -PrepareRunner -RunDryRun
     Prepare puis lance le DryRun.

 -ExpectedFileCount
     Contrat corpus attendu.

 -BatchSize
     Taille de batch transmise au moteur.
===============================================================================
#>

[CmdletBinding()]
param(
    [switch]$PrepareRunner,

    [switch]$RunDryRun,

    [int]$BatchSize = 2000,

    [int64]$ExpectedFileCount = 176064
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ============================================================================
# CONFIGURATION
# ============================================================================

$Root = (Get-Location).Path

$NightRoot = Join-Path `
    $Root `
    'tools\semantic_model\structural_graph\.night_run'

if (-not (Test-Path -LiteralPath $NightRoot -PathType Container)) {
    New-Item `
        -ItemType Directory `
        -LiteralPath $NightRoot `
        -Force |
        Out-Null
}

$Timestamp = (
    Get-Date
).ToUniversalTime().ToString('yyyyMMdd_HHmmss')

$Report = Join-Path `
    $NightRoot `
    "PHASE2B_MASTER_FORENSIC_$Timestamp.txt"

$PreparedRunner = Join-Path `
    $NightRoot `
    "PHASE2B_PREPARED_RUNNER_$Timestamp.ps1"

# ============================================================================
# REPORTING
# ============================================================================

function Write-Report {
    param(
        [AllowEmptyString()]
        [string]$Text
    )

    Add-Content `
        -LiteralPath $Report `
        -Value $Text `
        -Encoding UTF8
}

function Info {
    param([string]$Text)

    Write-Host $Text -ForegroundColor Gray
    Write-Report $Text
}

function Good {
    param([string]$Text)

    Write-Host $Text -ForegroundColor Green
    Write-Report $Text
}

function Warn {
    param([string]$Text)

    Write-Host $Text -ForegroundColor Yellow
    Write-Report $Text
}

function Fail {
    param([string]$Text)

    Write-Host $Text -ForegroundColor Red
    Write-Report $Text
}

function Section {
    param([string]$Title)

    $Line = '=' * 79

    Write-Host ''
    Write-Host $Line -ForegroundColor Cyan
    Write-Host " $Title" -ForegroundColor Cyan
    Write-Host $Line -ForegroundColor Cyan

    Write-Report ''
    Write-Report $Line
    Write-Report " $Title"
    Write-Report $Line
}

# ============================================================================
# INITIALISATION
# ============================================================================

Set-Content `
    -LiteralPath $Report `
    -Value 'E-ZZIO — PHASE 2B NIGHT MASTER' `
    -Encoding UTF8

Write-Report "UTC : $((Get-Date).ToUniversalTime().ToString('o'))"
Write-Report "ROOT: $Root"
Write-Report 'MODE: FORENSIC / FAIL-CLOSED / READ-ONLY FIRST'
Write-Report "PREPARE RUNNER: $PrepareRunner"
Write-Report "RUN DRY RUN   : $RunDryRun"
Write-Report "BATCH SIZE    : $BatchSize"
Write-Report "EXPECTED FILES: $ExpectedFileCount"

Section '1 — ENVIRONNEMENT'

Info "[ROOT] $Root"
Info "[REPORT] $Report"
Info "[PREPARE] $PrepareRunner"
Info "[RUN DRYRUN] $RunDryRun"

if ($BatchSize -le 0) {
    throw 'INVALID_BATCH_SIZE'
}

if ($ExpectedFileCount -le 0) {
    throw 'INVALID_EXPECTED_FILE_COUNT'
}

# ============================================================================
# RECHERCHE DU MOTEUR
# ============================================================================

Section '2 — RECHERCHE FORENSIQUE DU MOTEUR PHASE 2B'

$candidates = @(
    Get-ChildItem `
        -LiteralPath $Root `
        -Recurse `
        -File `
        -Filter '*.ps1' `
        -ErrorAction SilentlyContinue |
    Where-Object {
        $_.Name -match '^Phase2B_v\d+.*\.ps1$' -or
        $_.Name -match 'PHASE2B.*CONTENT.*TRUTH' -or
        $_.Name -match 'CONTENT.*TRUTH.*ENGINE'
    } |
    Sort-Object FullName
)

if ($candidates.Count -eq 0) {
    Fail '[FAIL-CLOSED] Aucun moteur Phase 2B trouve.'
    throw 'PHASE2B_ENGINE_NOT_FOUND'
}

Info "[FOUND] $($candidates.Count) candidat(s)"

foreach ($candidate in $candidates) {

    $CandidateHash = (
        Get-FileHash `
            -LiteralPath $candidate.FullName `
            -Algorithm SHA256
    ).Hash.ToLowerInvariant()

    Info " - $($candidate.FullName)"
    Info "   SIZE = $($candidate.Length)"
    Info "   SHA  = $CandidateHash"
}

# ============================================================================
# SELECTION VERSION
# ============================================================================

Section '3 — SELECTION DU MOTEUR'

$versioned = @(
    $candidates |
    Where-Object {
        $_.Name -match '^Phase2B_v(\d+).*\.ps1$'
    } |
    Sort-Object {
        $Match = [regex]::Match(
            $_.Name,
            '^Phase2B_v(\d+)'
        )

        if ($Match.Success) {
            [int]$Match.Groups[1].Value
        }
        else {
            -1
        }
    } -Descending
)

if ($versioned.Count -gt 0) {
    $Script = $versioned[0].FullName
}
else {
    $Script = $candidates[0].FullName
}

$Engine = Get-Item -LiteralPath $Script

$EngineHash = (
    Get-FileHash `
        -LiteralPath $Script `
        -Algorithm SHA256
).Hash.ToLowerInvariant()

Good "[SELECTED] $($Engine.FullName)"
Info "[SIZE] $($Engine.Length) bytes"
Info "[SHA ] $EngineHash"

Write-Report "SELECTED ENGINE: $($Engine.FullName)"
Write-Report "ENGINE SIZE    : $($Engine.Length)"
Write-Report "ENGINE SHA256  : $EngineHash"

# ============================================================================
# PARSE STATIQUE
# ============================================================================

Section '4 — PARSEUR POWERSHELL STATIQUE'

$tokens = $null
$ParseErrors = $null

[System.Management.Automation.Language.Parser]::ParseFile(
    $Script,
    [ref]$tokens,
    [ref]$ParseErrors
) | Out-Null

$TokenCount = @($tokens).Count
$ParseErrorCount = @($ParseErrors).Count

Info "[TOKENS] $TokenCount"
Info "[PARSE ERRORS] $ParseErrorCount"

Write-Report "TOKEN COUNT: $TokenCount"
Write-Report "PARSE ERRORS: $ParseErrorCount"

if ($ParseErrorCount -ne 0) {

    Fail '[FAIL-CLOSED] Erreur(s) syntaxique(s) detectee(s).'

    foreach ($ParseError in $ParseErrors) {

        $Message = '{0} @ line {1}, col {2}' -f `
            $ParseError.Message,
            $ParseError.Extent.StartLineNumber,
            $ParseError.Extent.StartColumnNumber

        Fail "  $Message"
    }

    throw 'PHASE2B_STATIC_SYNTAX_FAILURE'
}

Good '[PASS] Syntaxe PowerShell valide.'

# ============================================================================
# LECTURE STATIQUE DES PARAMETRES
# ============================================================================

Section '5 — CONTRAT DES PARAMETRES'

$ParameterPatterns = [ordered]@{
    ResumeLatest      = '\[switch\]\$ResumeLatest'
    DryRun            = '\[switch\]\$DryRun'
    BatchSize         = '\[int\]\$BatchSize'
    ExpectedFileCount = '\[int64\]\$ExpectedFileCount'
}

$ParameterFailures = 0

foreach ($Entry in $ParameterPatterns.GetEnumerator()) {

    $Found = Select-String `
        -LiteralPath $Script `
        -Pattern $Entry.Value `
        -Quiet

    if ($Found) {
        Good "[PASS] $($Entry.Key)"
        Write-Report "[PASS] PARAMETER $($Entry.Key)"
    }
    else {
        Fail "[FAIL] $($Entry.Key)"
        Write-Report "[FAIL] PARAMETER $($Entry.Key)"
        $ParameterFailures++
    }
}

if ($ParameterFailures -gt 0) {
    throw 'PHASE2B_PARAMETER_CONTRACT_FAILURE'
}

# ============================================================================
# MECANISMES DE SECURITE
# ============================================================================

Section '6 — MECANISMES DE SECURITE'

$SecurityPatterns = [ordered]@{
    StrictMode      = 'Set-StrictMode'
    ErrorPreference = '\$ErrorActionPreference'
    Mutex           = '\bMutex\b'
    FileHash        = '\bGet-FileHash\b'
    SHA256          = '\bSHA256\b'
    FromJson        = '\bConvertFrom-Json\b'
    ToJson          = '\bConvertTo-Json\b'
    DryRun          = '\bDryRun\b'
    ResumeLatest    = '\bResumeLatest\b'
    Checkpoint      = '\bcheckpoint\b'
    ChainHash       = '\bChainHash\b'
    FileStream      = '\bFileStream\b'
    CryptoStream    = '\bCryptoStream\b'
}

foreach ($Entry in $SecurityPatterns.GetEnumerator()) {

    $Count = @(
        Select-String `
            -LiteralPath $Script `
            -Pattern $Entry.Value
    ).Count

    if ($Count -gt 0) {
        Info "[OBSERVED] $($Entry.Key) = $Count"
    }
    else {
        Warn "[ABSENT] $($Entry.Key)"
    }

    Write-Report "SECURITY $($Entry.Key) = $Count"
}

# ============================================================================
# DETECTION DES MUTATIONS REELLES
# ============================================================================

Section '7 — ANALYSE DES PRIMITIVES DE MUTATION'

$MutationPatterns = [ordered]@{
    RemoveItem      = '\bRemove-Item\b'
    MoveItem        = '\bMove-Item\b'
    CopyItem        = '\bCopy-Item\b'
    FileDelete      = '\[System\.IO\.File\]::Delete\b'
    DirectoryDelete = '\[System\.IO\.Directory\]::Delete\b'
    WriteAllText    = '\[System\.IO\.File\]::WriteAllText\b'
    WriteAllBytes   = '\[System\.IO\.File\]::WriteAllBytes\b'
    SetContent      = '\bSet-Content\b'
    AddContent      = '\bAdd-Content\b'
    OutFile         = '\bOut-File\b'
    NewItem         = '\bNew-Item\b'
}

$MutationHits = 0

foreach ($Entry in $MutationPatterns.GetEnumerator()) {

    $Hits = @(
        Select-String `
            -LiteralPath $Script `
            -Pattern $Entry.Value
    )

    if ($Hits.Count -gt 0) {

        $MutationHits += $Hits.Count

        Warn "[OBSERVED] $($Entry.Key) = $($Hits.Count)"

        foreach ($Hit in $Hits) {

            $LineText = $Hit.Line.Trim()

            Info "  line $($Hit.LineNumber): $LineText"

            Write-Report `
                "MUTATION $($Entry.Key) line=$($Hit.LineNumber): $LineText"
        }
    }
}

Write-Report "TOTAL MUTATION PRIMITIVES: $MutationHits"

if ($MutationHits -eq 0) {
    Good '[PASS] Aucune primitive de mutation detectee.'
}
else {
    Warn "[FORENSIC] $MutationHits primitive(s) de mutation observee(s)."
    Warn '[NOTE] Presence statique != execution.'
}

# ============================================================================
# INVENTAIRE
# ============================================================================

Section '8 — INVENTAIRE'

$LineCount = @(
    Get-Content `
        -LiteralPath $Script `
        -ErrorAction Stop
).Count

Info "[LINES] $LineCount"
Info "[TOKENS] $TokenCount"
Info "[BYTES] $($Engine.Length)"
Info "[SHA256] $EngineHash"

Write-Report "LINE COUNT : $LineCount"
Write-Report "TOKEN COUNT: $TokenCount"
Write-Report "BYTE COUNT : $($Engine.Length)"
Write-Report "SHA256     : $EngineHash"

# ============================================================================
# CONTRAT CORPUS
# ============================================================================

Section '9 — CONTRAT CORPUS'

Info "[EXPECTED FILE COUNT] $ExpectedFileCount"
Info "[BATCH SIZE] $BatchSize"

Write-Report "EXPECTED FILE COUNT: $ExpectedFileCount"
Write-Report "BATCH SIZE: $BatchSize"

# ============================================================================
# PREPARATION RUNNER
# ============================================================================

if ($PrepareRunner) {

    Section '10 — PREPARATION DU RUNNER'

    $RunnerLines = @(
        '#requires -Version 7.0'
        ''
        '[CmdletBinding()]'
        'param('
        '    [switch]$Run'
        ')'
        ''
        'Set-StrictMode -Version Latest'
        '$ErrorActionPreference = ''Stop'''
        ''
        ('$Engine = ''{0}''' -f $Script.Replace('''', ''''''))
        ('$ExpectedHash = ''{0}''' -f $EngineHash)
        '$BatchSize = 2000'
        ('$ExpectedFileCount = {0}' -f $ExpectedFileCount)
        ''
        'Write-Host ''============================================================'' -ForegroundColor Cyan'
        'Write-Host '' E-ZZIO — PHASE 2B PREPARED RUNNER'' -ForegroundColor Cyan'
        'Write-Host ''============================================================'' -ForegroundColor Cyan'
        ''
        'Write-Host "[ENGINE] $Engine"'
        ''
        'if (-not (Test-Path -LiteralPath $Engine -PathType Leaf)) {'
        '    throw ''ENGINE_NOT_FOUND'''
        '}'
        ''
        '$CurrentHash = (Get-FileHash -LiteralPath $Engine -Algorithm SHA256).Hash.ToLowerInvariant()'
        ''
        'if ($CurrentHash -ne $ExpectedHash) {'
        '    throw ''FAIL-CLOSED: ENGINE_HASH_CHANGED'''
        '}'
        ''
        'Write-Host "[HASH PASS] $CurrentHash" -ForegroundColor Green'
        ''
        'if (-not $Run) {'
        '    Write-Host ''[SAFE] Aucun lancement demande.'' -ForegroundColor Green'
        '    return'
        '}'
        ''
        'Write-Host ''[AUTHORIZED] Lancement explicite en DryRun.'' -ForegroundColor Yellow'
        ''
        '& $Engine -DryRun -BatchSize $BatchSize -ExpectedFileCount $ExpectedFileCount'
        ''
        'if ($LASTEXITCODE -ne 0) {'
        '    throw "PHASE2B_DRYRUN_FAILED: exit=$LASTEXITCODE"'
        '}'
        ''
        'Write-Host ''[PASS] DryRun termine.'' -ForegroundColor Green'
    )

    Set-Content `
        -LiteralPath $PreparedRunner `
        -Value $RunnerLines `
        -Encoding UTF8

    $RunnerHash = (
        Get-FileHash `
            -LiteralPath $PreparedRunner `
            -Algorithm SHA256
    ).Hash.ToLowerInvariant()

    Good "[RUNNER CREATED] $PreparedRunner"
    Info "[RUNNER SHA256] $RunnerHash"

    Write-Report "RUNNER: $PreparedRunner"
    Write-Report "RUNNER SHA256: $RunnerHash"
}
else {
    Info '[SKIP] Aucun runner demande.'
}

# ============================================================================
# EXECUTION EXPLICITE DU DRYRUN
# ============================================================================

$ExecutionDecision = 'DENIED_BY_DEFAULT'

if ($RunDryRun) {

    Section '11 — DRYRUN EXPLICITEMENT DEMANDE'

    $PreExecHash = (
        Get-FileHash `
            -LiteralPath $Script `
            -Algorithm SHA256
    ).Hash.ToLowerInvariant()

    Info "[AUDIT HASH] $EngineHash"
    Info "[CURRENT HASH] $PreExecHash"

    if ($PreExecHash -ne $EngineHash) {

        Fail '[FAIL-CLOSED] Le moteur a change depuis son audit.'
        throw 'ENGINE_HASH_CHANGED_BEFORE_EXECUTION'
    }

    Good '[HASH VERIFIED] Identite du moteur confirmee.'

    Warn '[EXECUTION] Le moteur va etre invoque avec -DryRun.'

    & $Script `
        -DryRun `
        -BatchSize $BatchSize `
        -ExpectedFileCount $ExpectedFileCount

    $ExitCode = $LASTEXITCODE

    Write-Report "NATIVE EXIT CODE: $ExitCode"

    if ($ExitCode -ne 0) {
        Fail "[FAIL] Exit code = $ExitCode"
        throw "PHASE2B_DRYRUN_FAILED_$ExitCode"
    }

    Good '[PASS] DryRun Phase 2B termine.'

    $ExecutionDecision = 'AUTHORIZED_DRYRUN'
}
else {
    Good '[SAFE] Aucun lancement du moteur.'
    $ExecutionDecision = 'DENIED_BY_DEFAULT'
}

# ============================================================================
# VERDICT
# ============================================================================

Section '12 — VERDICT FORENSIC'

Write-Report "ENGINE      : $Script"
Write-Report "SHA256      : $EngineHash"
Write-Report "SIZE        : $($Engine.Length)"
Write-Report "LINES       : $LineCount"
Write-Report "TOKENS      : $TokenCount"
Write-Report "MUTATIONS   : $MutationHits"
Write-Report "EXECUTION   : $ExecutionDecision"
Write-Report "REPORT      : $Report"

Good '============================================================'
Good ' E-ZZIO — PHASE 2B NIGHT MASTER TERMINE'
Good '============================================================'

Info "ENGINE     : $Script"
Info "SIZE       : $($Engine.Length) bytes"
Info "SHA256     : $EngineHash"
Info "LINES      : $LineCount"
Info "TOKENS     : $TokenCount"
Info "MUTATIONS  : $MutationHits"
Info "EXECUTION  : $ExecutionDecision"
Info "REPORT     : $Report"

if ($PrepareRunner) {
    Info "RUNNER     : $PreparedRunner"
}

Write-Host ''
Good 'FIN — FAIL-CLOSED / FORENSIC'
