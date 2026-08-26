````powershell
#requires -Version 7.4
<#
===============================================================================
 E-ZZIO — MODEL QUALIFICATION GATE
 Version : 4.0.0
 Mode    : FULL INSTALLED MODELS / CPU-ONLY / BLIND / FORENSIC / FAIL-CLOSED
===============================================================================

OBJECTIF
--------
Benchmark exhaustif de TOUS les modèles réellement installés dans Ollama.

AUCUNE modification :
    - model_policy.json
    - runtime
    - router
    - ledger
    - configuration E-ZZIO

Le benchmark est READ-ONLY vis-à-vis du dépôt E-ZZIO.

Les seuls fichiers créés sont les artefacts du benchmark dans :
    state\performance\model_qualification_v4\

PRINCIPES
---------
1. Découverte physique via "ollama list".
2. Aucun modèle n'est exclu silencieusement.
3. Modèles génératifs -> batterie complète.
4. Modèles embedding -> batterie embedding dédiée.
5. Un seul modèle chargé à la fois.
6. keep_alive=0.
7. Ordre des modèles randomisé.
8. Prompts identiques pour tous les modèles d'une même catégorie.
9. Aucun ancien score utilisé pour le verdict.
10. Aucun changement automatique de policy.
11. Toute anomalie est enregistrée.
12. Verdict fail-closed.

===============================================================================
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ============================================================================
# [0/12] CONFIGURATION
# ============================================================================

$Version = '4.0.0'

$Root = 'G:\AI\E-zzio'

$OutputRoot = Join-Path `
    $Root `
    'state\performance\model_qualification_v4'

$RunId = Get-Date -Format 'yyyyMMdd_HHmmss'
$RunDir = Join-Path $OutputRoot $RunId

$JsonReport = Join-Path $RunDir "MODEL_QUALIFICATION_V4_${RunId}.json"
$CsvReport  = Join-Path $RunDir "MODEL_QUALIFICATION_V4_${RunId}.csv"
$TxtReport  = Join-Path $RunDir "MODEL_QUALIFICATION_V4_${RunId}.txt"

$OllamaHost = 'http://127.0.0.1:11434'

# ---------------------------------------------------------------------------
# CPU ONLY
# ---------------------------------------------------------------------------

$env:OLLAMA_NUM_GPU = '0'
$env:CUDA_VISIBLE_DEVICES = ''
$env:ROCR_VISIBLE_DEVICES = ''
$env:HIP_VISIBLE_DEVICES = ''
$env:OLLAMA_KEEP_ALIVE = '0'

# ---------------------------------------------------------------------------
# Benchmark parameters
# ---------------------------------------------------------------------------

$RequestTimeoutSec = 180
$StableRuns = 2
$WarmupRuns = 1

$MaxGeneratedTokens = 256

$RandomSeed = Get-Random -Minimum 100000 -Maximum 999999

# ============================================================================
# [1/12] CONSOLE / FILE HELPERS
# ============================================================================

New-Item -ItemType Directory -Force -Path $RunDir | Out-Null

$script:PassCount = 0
$script:WarnCount = 0
$script:FailCount = 0
$script:InfoCount = 0

function Write-Section {
    param(
        [Parameter(Mandatory)]
        [string]$Title
    )

    Write-Host ''
    Write-Host ('=' * 78)
    Write-Host " $Title"
    Write-Host ('=' * 78)
}

function Write-Info {
    param([string]$Message)

    $script:InfoCount++
    Write-Host "[INFO] $Message"
}

function Write-Pass {
    param([string]$Message)

    $script:PassCount++
    Write-Host "[PASS] $Message"
}

function Write-Warn {
    param([string]$Message)

    $script:WarnCount++
    Write-Host "[WARN] $Message"
}

function Write-Fail {
    param([string]$Message)

    $script:FailCount++
    Write-Host "[FAIL] $Message"
}

function Write-TextReport {
    param([string]$Line)

    Add-Content -LiteralPath $TxtReport -Value $Line -Encoding UTF8
}

# ============================================================================
# [2/12] ENVIRONMENT
# ============================================================================

Write-Section "[2/12] ENVIRONMENT FORENSIC"

Write-Info "E-ZZIO ROOT : $Root"
Write-Info "RUN ID      : $RunId"
Write-Info "VERSION     : $Version"
Write-Info "CPU MODE    : CPU-ONLY"
Write-Info "GPU         : DISABLED"
Write-Info "SEED        : $RandomSeed"

$Cpu = Get-CimInstance Win32_Processor |
    Select-Object -First 1

$Os = Get-CimInstance Win32_OperatingSystem |
    Select-Object -First 1

$TotalRamGB = [math]::Round(
    [double]$Os.TotalVisibleMemorySize / 1MB,
    2
)

$FreeRamGB = [math]::Round(
    [double]$Os.FreePhysicalMemory / 1MB,
    2
)

Write-Info "CPU : $($Cpu.Name)"
Write-Info "CPU CORES : $($Cpu.NumberOfCores)"
Write-Info "CPU THREADS : $($Cpu.NumberOfLogicalProcessors)"
Write-Info "RAM TOTAL : ${TotalRamGB} GB"
Write-Info "RAM FREE  : ${FreeRamGB} GB"

# ============================================================================
# [3/12] OLLAMA HEALTH
# ============================================================================

Write-Section "[3/12] OLLAMA HEALTH"

try {
    $TagsResponse = Invoke-RestMethod `
        -Uri "$OllamaHost/api/tags" `
        -Method Get `
        -TimeoutSec 20

    Write-Pass "Ollama API reachable."
}
catch {
    Write-Fail "Ollama API unavailable : $($_.Exception.Message)"
    throw
}

# ============================================================================
# [4/12] DISCOVERY — ALL INSTALLED MODELS
# ============================================================================

Write-Section "[4/12] PHYSICAL MODEL DISCOVERY"

$Models = @(
    $TagsResponse.models
)

if ($Models.Count -eq 0) {
    Write-Fail "Aucun modèle Ollama détecté."
    throw "No Ollama models installed."
}

Write-Info "Models discovered : $($Models.Count)"

$Discovered = foreach ($Model in $Models) {

    $Name = [string]$Model.name

    $SizeGB = if ($null -ne $Model.size) {
        [math]::Round(
            [double]$Model.size / 1GB,
            3
        )
    }
    else {
        0
    }

    $Family = if ($null -ne $Model.details.family) {
        [string]$Model.details.family
    }
    else {
        ''
    }

    $ParameterSize = if ($null -ne $Model.details.parameter_size) {
        [string]$Model.details.parameter_size
    }
    else {
        ''
    }

    $Quantization = if ($null -ne $Model.details.quantization_level) {
        [string]$Model.details.quantization_level
    }
    else {
        ''
    }

    [pscustomobject]@{
        Name           = $Name
        SizeGB         = $SizeGB
        Family         = $Family
        ParameterSize  = $ParameterSize
        Quantization   = $Quantization
    }
}

$Discovered |
    Sort-Object Name |
    ForEach-Object {
        Write-Info (
            "{0} | {1} GB | {2} | {3} | {4}" -f `
            $_.Name,
            $_.SizeGB,
            $_.Family,
            $_.ParameterSize,
            $_.Quantization
        )
    }

# ============================================================================
# [5/12] CAPABILITY CLASSIFICATION
# ============================================================================

Write-Section "[5/12] CAPABILITY CLASSIFICATION"

function Test-EmbeddingCapability {
    param(
        [Parameter(Mandatory)]
        [string]$Model
    )

    try {
        $Body = @{
            model = $Model
            input = 'E-ZZIO capability probe'
        } | ConvertTo-Json -Depth 10

        $Response = Invoke-RestMethod `
            -Uri "$OllamaHost/api/embed" `
            -Method Post `
            -ContentType 'application/json' `
            -Body $Body `
            -TimeoutSec 30

        return $true
    }
    catch {
        return $false
    }
}

function Test-GenerateCapability {
    param(
        [Parameter(Mandatory)]
        [string]$Model
    )

    try {

        $Body = @{
            model = $Model
            prompt = 'Reply with exactly: EZZIO_PROBE_OK'
            stream = $false
            keep_alive = 0
            options = @{
                temperature = 0
                seed = 424242
                num_predict = 16
            }
        } | ConvertTo-Json -Depth 10

        $Response = Invoke-RestMethod `
            -Uri "$OllamaHost/api/generate" `
            -Method Post `
            -ContentType 'application/json' `
            -Body $Body `
            -TimeoutSec 60

        return ($null -ne $Response.response)
    }
    catch {
        return $false
    }
}

$Capabilities = @()

foreach ($Model in $Discovered) {

    Write-Info "Capability probe : $($Model.Name)"

    $CanGenerate = Test-GenerateCapability -Model $Model.Name
    $CanEmbed    = Test-EmbeddingCapability -Model $Model.Name

    $Class = if ($CanGenerate) {
        'GENERATIVE'
    }
    elseif ($CanEmbed) {
        'EMBEDDING'
    }
    else {
        'UNSUPPORTED'
    }

    $Capabilities += [pscustomobject]@{
        Name       = $Model.Name
        SizeGB     = $Model.SizeGB
        Family     = $Model.Family
        Parameters = $Model.ParameterSize
        Quant      = $Model.Quantization
        Generate   = $CanGenerate
        Embedding  = $CanEmbed
        Class      = $Class
    }

    switch ($Class) {
        'GENERATIVE' {
            Write-Pass "$($Model.Name) -> GENERATIVE"
        }

        'EMBEDDING' {
            Write-Pass "$($Model.Name) -> EMBEDDING"
        }

        default {
            Write-Warn "$($Model.Name) -> UNSUPPORTED"
        }
    }
}

# ============================================================================
# [6/12] BLIND PROMPTS
# ============================================================================

Write-Section "[6/12] BLIND FORENSIC TEST MATRIX"

$Tests = @(
    [pscustomobject]@{
        Id = 'S01'
        Name = 'ShortResponse'
        Prompt = 'Réponds exactement avec cette chaîne : EZZIO_OK'
        Validator = 'Exact'
        Expected = 'EZZIO_OK'
    }

    [pscustomobject]@{
        Id = 'S02'
        Name = 'PowerShell'
        Prompt = @'
Produce only valid PowerShell 7 code.

Task:
Create a variable named $EzzioValue containing the integer 42 and print it.

No markdown fences.
'@
        Validator = 'PowerShell'
        Expected = '$EzzioValue'
    }

    [pscustomobject]@{
        Id = 'S03'
        Name = 'Python'
        Prompt = @'
Produce only valid Python 3 code.

Task:
Create a variable named value containing the integer 42 and print it.

No markdown fences.
'@
        Validator = 'Python'
        Expected = 'value'
    }

    [pscustomobject]@{
        Id = 'S04'
        Name = 'StrictJSON'
        Prompt = @'
Return ONLY valid JSON.

Required object:
{
  "ok": true,
  "value": 42,
  "name": "EZZIO"
}

No markdown.
'@
        Validator = 'JSON'
        Expected = 'ok'
    }

    [pscustomobject]@{
        Id = 'S05'
        Name = 'Logic'
        Prompt = @'
A system has 3 workers.
Worker A completes a task in 4 seconds.
Worker B completes it in 6 seconds.
Worker C completes it in 12 seconds.

If they work independently in parallel, what is the combined task rate in tasks per second?

Return:
1) the formula
2) the numerical result
3) one short explanation
'@
        Validator = 'Logic'
        Expected = '0.5'
    }

    [pscustomobject]@{
        Id = 'S06'
        Name = 'NegationPreservation'
        Prompt = @'
Repeat the following two facts exactly in meaning without removing the word NOT:

"The system must NOT authorize 10.0.0.99."
"NOT is a mandatory constraint."

Do not invent anything.
'@
        Validator = 'Semantic'
        Expected = 'NOT'
    }

    [pscustomobject]@{
        Id = 'S07'
        Name = 'Context'
        Prompt = @'
Read these constraints:

A = 17
B = 25
C = 8
D = 4

Compute:
(A + B) * C - D

Return only the integer.
'@
        Validator = 'Exact'
        Expected = '332'
    }

    [pscustomobject]@{
        Id = 'S08'
        Name = 'CodeReasoning'
        Prompt = @'
Explain briefly what this Python function returns for input 5.

def f(x):
    if x < 0:
        return "A"
    if x == 0:
        return "B"
    if x % 2 == 0:
        return "C"
    return "D"

Return only the final letter.
'@
        Validator = 'Exact'
        Expected = 'D'
    }

    [pscustomobject]@{
        Id = 'S09'
        Name = 'FrenchInstruction'
        Prompt = 'Réponds uniquement : CERTIFICATION FORENSIC OK'
        Validator = 'Exact'
        Expected = 'CERTIFICATION FORENSIC OK'
    }

    [pscustomobject]@{
        Id = 'S10'
        Name = 'Abstention'
        Prompt = @'
You are not allowed to invent unknown facts.

Question:
What is the exact SHA-256 hash of an arbitrary file that has not been provided?

Return exactly:
ABSTAIN
'@
        Validator = 'Contains'
        Expected = 'ABSTAIN'
    }
)

# ============================================================================
# [7/12] VALIDATORS
# ============================================================================

Write-Section "[7/12] FORENSIC VALIDATORS"

function Normalize-Reply {
    param([string]$Text)

    if ($null -eq $Text) {
        return ''
    }

    return $Text.Trim()
}

function Validate-Exact {
    param(
        [string]$Reply,
        [string]$Expected
    )

    return ((Normalize-Reply $Reply) -eq $Expected)
}

function Validate-Contains {
    param(
        [string]$Reply,
        [string]$Expected
    )

    return (
        (Normalize-Reply $Reply).ToUpperInvariant().Contains(
            $Expected.ToUpperInvariant()
        )
    )
}

function Remove-CodeFence {
    param([string]$Text)

    $Value = Normalize-Reply $Text

    $Value = $Value -replace '^\s*```[a-zA-Z0-9_-]*\s*', ''
    $Value = $Value -replace '\s*```\s*$', ''

    return $Value.Trim()
}

function Validate-Python {
    param([string]$Reply)

    $Temp = Join-Path `
        $RunDir `
        ("python_{0}.py" -f ([guid]::NewGuid().ToString('N')))

    try {

        $Code = Remove-CodeFence $Reply

        if ([string]::IsNullOrWhiteSpace($Code)) {
            return [pscustomobject]@{
                Pass = $false
                Detail = 'EMPTY'
            }
        }

        Set-Content `
            -LiteralPath $Temp `
            -Value $Code `
            -Encoding UTF8

        $Process = Start-Process `
            -FilePath 'python' `
            -ArgumentList @('-m', 'py_compile', $Temp) `
            -NoNewWindow `
            -Wait `
            -PassThru `
            -RedirectStandardOutput (Join-Path $RunDir 'py.out') `
            -RedirectStandardError (Join-Path $RunDir 'py.err')

        return [pscustomobject]@{
            Pass   = ($Process.ExitCode -eq 0)
            Detail = "exit=$($Process.ExitCode)"
        }
    }
    catch {
        return [pscustomobject]@{
            Pass   = $false
            Detail = $_.Exception.Message
        }
    }
    finally {
        Remove-Item `
            -LiteralPath $Temp `
            -Force `
            -ErrorAction SilentlyContinue
    }
}

function Validate-PowerShell {
    param([string]$Reply)

    $Temp = Join-Path `
        $RunDir `
        ("powershell_{0}.ps1" -f ([guid]::NewGuid().ToString('N')))

    try {

        $Code = Remove-CodeFence $Reply

        if ([string]::IsNullOrWhiteSpace($Code)) {
            return [pscustomobject]@{
                Pass = $false
                Detail = 'EMPTY'
            }
        }

        Set-Content `
            -LiteralPath $Temp `
            -Value $Code `
            -Encoding UTF8

        $Errors = $null

        $Ast = [System.Management.Automation.Language.Parser]::ParseFile(
            $Temp,
            [ref]$null,
            [ref]$Errors
        )

        return [pscustomobject]@{
            Pass   = ($null -eq $Errors -or $Errors.Count -eq 0)
            Detail = "syntax_errors=$($Errors.Count)"
        }
    }
    catch {
        return [pscustomobject]@{
            Pass   = $false
            Detail = $_.Exception.Message
        }
    }
    finally {
        Remove-Item `
            -LiteralPath $Temp `
            -Force `
            -ErrorAction SilentlyContinue
    }
}

function Validate-JSON {
    param([string]$Reply)

    try {

        $JsonText = Remove-CodeFence $Reply

        if ([string]::IsNullOrWhiteSpace($JsonText)) {
            return [pscustomobject]@{
                Pass = $false
                Detail = 'EMPTY'
            }
        }

        $Object = $JsonText | ConvertFrom-Json -ErrorAction Stop

        $Ok = (
            $Object.ok -eq $true -and
            [int]$Object.value -eq 42 -and
            [string]$Object.name -eq 'EZZIO'
        )

        return [pscustomobject]@{
            Pass   = $Ok
            Detail = if ($Ok) { 'schema_ok' } else { 'schema_mismatch' }
        }
    }
    catch {
        return [pscustomobject]@{
            Pass   = $false
            Detail = $_.Exception.Message
        }
    }
}

function Validate-Semantic {
    param([string]$Reply)

    $Value = Normalize-Reply $Reply

    $Pass = (
        $Value.ToUpperInvariant().Contains('NOT') -and
        $Value.Contains('10.0.0.99')
    )

    return [pscustomobject]@{
        Pass   = $Pass
        Detail = if ($Pass) { 'required_constraints_preserved' } else { 'constraint_loss' }
    }
}

function Validate-Reply {
    param(
        [string]$Validator,
        [string]$Reply,
        [string]$Expected
    )

    switch ($Validator) {

        'Exact' {
            return [pscustomobject]@{
                Pass = Validate-Exact $Reply $Expected
                Detail = 'exact_match'
            }
        }

        'Contains' {
            return [pscustomobject]@{
                Pass = Validate-Contains $Reply $Expected
                Detail = 'required_token'
            }
        }

        'PowerShell' {
            return Validate-PowerShell $Reply
        }

        'Python' {
            return Validate-Python $Reply
        }

        'JSON' {
            return Validate-JSON $Reply
        }

        'Semantic' {
            return Validate-Semantic $Reply
        }

        'Logic' {
            return [pscustomobject]@{
                Pass = (
                    (Normalize-Reply $Reply) -match '0\.5'
                )
                Detail = 'expected_rate'
            }
        }

        default {
            return [pscustomobject]@{
                Pass = $false
                Detail = 'UNKNOWN_VALIDATOR'
            }
        }
    }
}

# ============================================================================
# [8/12] SYSTEM RESOURCE SAMPLING
# ============================================================================

Write-Section "[8/12] RESOURCE MONITOR"

function Get-OllamaProcesses {

    Get-Process -ErrorAction SilentlyContinue |
        Where-Object {
            $_.ProcessName -match '^ollama'
        }
}

function Get-ProcessMemoryMB {

    $Processes = @(Get-OllamaProcesses)

    if ($Processes.Count -eq 0) {
        return 0
    }

    $Bytes = (
        $Processes |
            Measure-Object -Property WorkingSet64 -Sum
    ).Sum

    return [math]::Round(
        [double]$Bytes / 1MB,
        2
    )
}

# ============================================================================
# [9/12] GENERATIVE BENCHMARK
# ============================================================================

Write-Section "[9/12] GENERATIVE FORENSIC BENCHMARK"

$GenerativeModels = @(
    $Capabilities |
        Where-Object { $_.Class -eq 'GENERATIVE' }
)

if ($GenerativeModels.Count -eq 0) {
    Write-Warn "Aucun modèle génératif."
}

$Random = [System.Random]::new($RandomSeed)

$ShuffledModels = @(
    $GenerativeModels |
        Sort-Object { $Random.Next() }
)

$Results = [System.Collections.Generic.List[object]]::new()

foreach ($Model in $ShuffledModels) {

    Write-Host ''
    Write-Host ('-' * 78)
    Write-Host "MODEL : $($Model.Name)"
    Write-Host ('-' * 78)

    # ------------------------------------------------------------------------
    # Unload previous model
    # ------------------------------------------------------------------------

    try {

        $UnloadBody = @{
            model = $Model.Name
            prompt = ''
            keep_alive = 0
        } | ConvertTo-Json

        Invoke-RestMethod `
            -Uri "$OllamaHost/api/generate" `
            -Method Post `
            -ContentType 'application/json' `
            -Body $UnloadBody `
            -TimeoutSec 30 `
            | Out-Null
    }
    catch {
        Write-Warn "Unload probe : $($_.Exception.Message)"
    }

    Start-Sleep -Milliseconds 500

    # ------------------------------------------------------------------------
    # Warmup
    # ------------------------------------------------------------------------

    for ($Warm = 1; $Warm -le $WarmupRuns; $Warm++) {

        try {

            $WarmBody = @{
                model = $Model.Name
                prompt = 'Reply exactly: WARMUP_OK'
                stream = $false
                keep_alive = 0
                options = @{
                    temperature = 0
                    seed = 424242
                    num_predict = 16
                }
            } | ConvertTo-Json -Depth 10

            Invoke-RestMethod `
                -Uri "$OllamaHost/api/generate" `
                -Method Post `
                -ContentType 'application/json' `
                -Body $WarmBody `
                -TimeoutSec $RequestTimeoutSec `
                | Out-Null
        }
        catch {
            Write-Warn "Warmup failed : $($_.Exception.Message)"
        }
    }

    $ModelResults = [System.Collections.Generic.List[object]]::new()

    foreach ($Test in $Tests) {

        Write-Host "[TEST] $($Test.Id) $($Test.Name)"

        $Runs = [System.Collections.Generic.List[object]]::new()

        for ($Run = 1; $Run -le $StableRuns; $Run++) {

            $BeforeRam = Get-ProcessMemoryMB

            $Body = @{
                model = $Model.Name
                prompt = $Test.Prompt
                stream = $false
                keep_alive = 0
                options = @{
                    temperature = 0
                    seed = 424242
                    num_predict = $MaxGeneratedTokens
                }
            } | ConvertTo-Json -Depth 10

            $Started = [System.Diagnostics.Stopwatch]::StartNew()

            try {

                $Response = Invoke-RestMethod `
                    -Uri "$OllamaHost/api/generate" `
                    -Method Post `
                    -ContentType 'application/json' `
                    -Body $Body `
                    -TimeoutSec $RequestTimeoutSec

                $Started.Stop()

                $Reply = [string]$Response.response

                $AfterRam = Get-ProcessMemoryMB

                $ElapsedMs = $Started.ElapsedMilliseconds

                $Eval = Validate-Reply `
                    -Validator $Test.Validator `
                    -Reply $Reply `
                    -Expected $Test.Expected

                $EvalPass = [bool]$Eval.Pass

                $TokenCount = 0

                if ($null -ne $Response.eval_count) {
                    $TokenCount = [int]$Response.eval_count
                }

                $EvalDurationNs = 0

                if ($null -ne $Response.eval_duration) {
                    $EvalDurationNs = [int64]$Response.eval_duration
                }

                $TokPerSec = if ($EvalDurationNs -gt 0 -and $TokenCount -gt 0) {
                    [math]::Round(
                        $TokenCount /
                        ($EvalDurationNs / 1e9),
                        3
                    )
                }
                else {
                    0
                }

                $RunResult = [pscustomobject]@{
                    Run            = $Run
                    Pass           = $EvalPass
                    Detail         = [string]$Eval.Detail
                    ElapsedMs      = $ElapsedMs
                    EvalCount      = $TokenCount
                    TokPerSec      = $TokPerSec
                    RamBeforeMB    = $BeforeRam
                    RamAfterMB     = $AfterRam
                    RamDeltaMB     = [math]::Round(
                        $AfterRam - $BeforeRam,
                        2
                    )
                    ReplyChars     = $Reply.Length
                    Reply          = $Reply
                    Error          = $null
                }

                $Runs.Add($RunResult)

                if ($EvalPass) {
                    Write-Pass "$($Model.Name) / $($Test.Id) / run $Run"
                }
                else {
                    Write-Fail (
                        "$($Model.Name) / $($Test.Id) / run $Run -> " +
                        "$($Eval.Detail)"
                    )
                }
            }
            catch {

                $Started.Stop()

                $Runs.Add(
                    [pscustomobject]@{
                        Run         = $Run
                        Pass        = $false
                        Detail      = 'REQUEST_FAILED'
                        ElapsedMs   = $Started.ElapsedMilliseconds
                        EvalCount   = 0
                        TokPerSec   = 0
                        RamBeforeMB = $BeforeRam
                        RamAfterMB  = Get-ProcessMemoryMB
                        RamDeltaMB  = 0
                        ReplyChars  = 0
                        Reply       = ''
                        Error       = $_.Exception.Message
                    }
                )

                Write-Fail "$($Model.Name) / $($Test.Id) / run $Run -> REQUEST_FAILED"
            }
        }

        $PassedRuns = @(
            $Runs |
                Where-Object { $_.Pass }
        )

        $Pass = (
            $PassedRuns.Count -eq $StableRuns
        )

        $AvgMs = if ($Runs.Count -gt 0) {
            [math]::Round(
                (
                    $Runs |
                        Measure-Object -Property ElapsedMs -Average
                ).Average,
                2
            )
        }
        else {
            0
        }

        $AvgTokSec = if ($Runs.Count -gt 0) {
            [math]::Round(
                (
                    $Runs |
                        Measure-Object -Property TokPerSec -Average
                ).Average,
                3
            )
        }
        else {
            0
        }

        $ModelResults.Add(
            [pscustomobject]@{
                TestId       = $Test.Id
                TestName     = $Test.Name
                Validator    = $Test.Validator
                Pass         = $Pass
                Runs         = $Runs
                AvgMs        = $AvgMs
                AvgTokSec    = $AvgTokSec
            }
        )
    }

    # ------------------------------------------------------------------------
    # Determinism test
    # ------------------------------------------------------------------------

    Write-Host '[TEST] DETERMINISM'

    $DetPrompt = @'
Return exactly:
EZZIO_DETERMINISM_ANCHOR
'@

    $DetReplies = @()

    for ($Run = 1; $Run -le 3; $Run++) {

        try {

            $DetBody = @{
                model = $Model.Name
                prompt = $DetPrompt
                stream = $false
                keep_alive = 0
                options = @{
                    temperature = 0
                    seed = 987654
                    num_predict = 32
                }
            } | ConvertTo-Json -Depth 10

            $DetResponse = Invoke-RestMethod `
                -Uri "$OllamaHost/api/generate" `
                -Method Post `
                -ContentType 'application/json' `
                -Body $DetBody `
                -TimeoutSec $RequestTimeoutSec

            $DetReplies += [string]$DetResponse.response
        }
        catch {
            $DetReplies += ''
        }
    }

    $Deterministic = (
        $DetReplies.Count -eq 3 -and
        $DetReplies[0] -eq $DetReplies[1] -and
        $DetReplies[1] -eq $DetReplies[2]
    )

    if ($Deterministic) {
        Write-Pass "$($Model.Name) deterministic."
    }
    else {
        Write-Warn "$($Model.Name) non-deterministic."
    }

    # ------------------------------------------------------------------------
    # Model score
    # ------------------------------------------------------------------------

    $PassedTests = @(
        $ModelResults |
            Where-Object { $_.Pass }
    ).Count

    $TotalTests = $ModelResults.Count

    $Score = if ($TotalTests -gt 0) {
        [math]::Round(
            ($PassedTests / $TotalTests) * 100,
            2
        )
    }
    else {
        0
    }

    $AverageSpeed = if ($ModelResults.Count -gt 0) {
        [math]::Round(
            (
                $ModelResults |
                    Measure-Object -Property AvgTokSec -Average
            ).Average,
            3
        )
    }
    else {
        0
    }

    $AverageLatency = if ($ModelResults.Count -gt 0) {
        [math]::Round(
            (
                $ModelResults |
                    Measure-Object -Property AvgMs -Average
            ).Average,
            2
        )
    }
    else {
        0
    }

    $PeakRam = if ($ModelResults.Count -gt 0) {

        $AllRuns = @(
            $ModelResults |
                ForEach-Object { $_.Runs }
        )

        if ($AllRuns.Count -gt 0) {
            [math]::Round(
                (
                    $AllRuns |
                        Measure-Object -Property RamAfterMB -Maximum
                ).Maximum,
                2
            )
        }
        else {
            0
        }
    }
    else {
        0
    }

    $Verdict = if ($Score -eq 100 -and $Deterministic) {
        'QUALIFIED'
    }
    elseif ($Score -ge 70) {
        'PARTIAL'
    }
    else {
        'FAILED'
    }

    if ($Verdict -eq 'QUALIFIED') {
        Write-Pass "$($Model.Name) => QUALIFIED ($Score%)"
    }
    elseif ($Verdict -eq 'PARTIAL') {
        Write-Warn "$($Model.Name) => PARTIAL ($Score%)"
    }
    else {
        Write-Fail "$($Model.Name) => FAILED ($Score%)"
    }

    $Results.Add(
        [pscustomobject]@{
            Name             = $Model.Name
            Class            = $Model.Class
            SizeGB           = $Model.SizeGB
            Parameters       = $Model.Parameters
            Quantization     = $Model.Quant
            TestsPassed      = $PassedTests
            TestsTotal       = $TotalTests
            ScorePercent     = $Score
            Deterministic    = $Deterministic
            AverageTokSec    = $AverageSpeed
            AverageLatencyMs = $AverageLatency
            PeakRamMB        = $PeakRam
            Verdict          = $Verdict
            Tests            = $ModelResults
            DeterminismRuns  = $DetReplies
        }
    )
}

# ============================================================================
# [10/12] EMBEDDING BENCHMARK
# ============================================================================

Write-Section "[10/12] EMBEDDING FORENSIC BENCHMARK"

$EmbeddingModels = @(
    $Capabilities |
        Where-Object { $_.Embedding }
)

$EmbeddingResults = [System.Collections.Generic.List[object]]::new()

foreach ($Model in $EmbeddingModels) {

    Write-Host ''
    Write-Host ('-' * 78)
    Write-Host "EMBEDDING MODEL : $($Model.Name)"
    Write-Host ('-' * 78)

    $Samples = @(
        'E-ZZIO forensic certification',
        'Decision Ledger cryptographic evidence',
        'Sovereign context memory',
        'Hardware Governor resource policy'
    )

    $Latencies = [System.Collections.Generic.List[double]]::new()
    $Dimensions = [System.Collections.Generic.List[int]]::new()
    $Successes = 0

    foreach ($Sample in $Samples) {

        $Body = @{
            model = $Model.Name
            input = $Sample
        } | ConvertTo-Json -Depth 10

        $Watch = [System.Diagnostics.Stopwatch]::StartNew()

        try {

            $Response = Invoke-RestMethod `
                -Uri "$OllamaHost/api/embed" `
                -Method Post `
                -ContentType 'application/json' `
                -Body $Body `
                -TimeoutSec $RequestTimeoutSec

            $Watch.Stop()

            $Latencies.Add(
                [double]$Watch.ElapsedMilliseconds
            )

            if ($null -ne $Response.embeddings) {

                $Vector = @(
                    $Response.embeddings[0]
                )

                $Dimensions.Add(
                    [int]$Vector.Count
                )

                $Successes++

                Write-Pass "$($Model.Name) embedding sample."
            }
            else {
                Write-Fail "$($Model.Name) missing embeddings."
            }
        }
        catch {

            $Watch.Stop()

            Write-Fail (
                "$($Model.Name) embedding failed : " +
                $_.Exception.Message
            )
        }
    }

    $AvgEmbeddingMs = if ($Latencies.Count -gt 0) {
        [math]::Round(
            (
                $Latencies |
                    Measure-Object -Average
            ).Average,
            2
        )
    }
    else {
        0
    }

    $Dimension = if ($Dimensions.Count -gt 0) {
        $Dimensions[0]
    }
    else {
        0
    }

    $EmbeddingVerdict = if (
        $Successes -eq $Samples.Count -and
        $Dimension -gt 0
    ) {
        'QUALIFIED'
    }
    else {
        'FAILED'
    }

    $EmbeddingResults.Add(
        [pscustomobject]@{
            Name          = $Model.Name
            Class         = 'EMBEDDING'
            SizeGB        = $Model.SizeGB
            Parameters    = $Model.Parameters
            Quantization  = $Model.Quant
            SamplesPassed = $Successes
            SamplesTotal  = $Samples.Count
            Dimension     = $Dimension
            AverageMs     = $AvgEmbeddingMs
            Verdict       = $EmbeddingVerdict
        }
    )
}

# ============================================================================
# [11/12] FINAL FORENSIC REPORT
# ============================================================================

Write-Section "[11/12] FINAL FORENSIC REPORT"

$FinishedAt = Get-Date

$Qualified = @(
    $Results |
        Where-Object { $_.Verdict -eq 'QUALIFIED' }
)

$Partial = @(
    $Results |
        Where-Object { $_.Verdict -eq 'PARTIAL' }
)

$Failed = @(
    $Results |
        Where-Object { $_.Verdict -eq 'FAILED' }
)

$AllModelsCount = $Capabilities.Count
$GenerativeCount = $GenerativeModels.Count
$EmbeddingCount = $EmbeddingModels.Count

$Report = [ordered]@{

    schema_version = '4.0.0'

    benchmark = [ordered]@{
        name = 'E-ZZIO MODEL QUALIFICATION GATE'
        version = $Version
        run_id = $RunId
        started_at = $RunId
        finished_at = $FinishedAt.ToString('o')
        seed = $RandomSeed
        cpu_only = $true
        gpu_disabled = $true
        keep_alive = 0
        stable_runs = $StableRuns
        warmup_runs = $WarmupRuns
        max_generated_tokens = $MaxGeneratedTokens
        policy_modified = $false
        router_modified = $false
        ledger_modified = $false
    }

    environment = [ordered]@{
        cpu = $Cpu.Name
        cores = $Cpu.NumberOfCores
        threads = $Cpu.NumberOfLogicalProcessors
        ram_total_gb = $TotalRamGB
        ram_free_gb_start = $FreeRamGB
        ollama_host = $OllamaHost
        powershell = $PSVersionTable.PSVersion.ToString()
    }

    inventory = [ordered]@{
        total_models = $AllModelsCount
        generative_models = $GenerativeCount
        embedding_models = $EmbeddingCount
        models = $Capabilities
    }

    generative_results = $Results

    embedding_results = $EmbeddingResults

    summary = [ordered]@{
        qualified = $Qualified.Count
        partial = $Partial.Count
        failed = $Failed.Count
        unsupported = @(
            $Capabilities |
                Where-Object { $_.Class -eq 'UNSUPPORTED' }
        ).Count
    }

    ranking = @(
        $Results |
            Sort-Object `
                @{Expression='ScorePercent';Descending=$true},
                @{Expression='AverageTokSec';Descending=$true},
                @{Expression='AverageLatencyMs';Ascending=$true} |
            Select-Object `
                Name,
                ScorePercent,
                Deterministic,
                AverageTokSec,
                AverageLatencyMs,
                PeakRamMB,
                Verdict
    )

    integrity = [ordered]@{
        old_policy_used = $false
        old_benchmark_scores_used = $false
        automatic_policy_change = $false
        source_of_truth = 'physical Ollama inventory + fresh benchmark'
    }
}

$Json = $Report |
    ConvertTo-Json -Depth 30

Set-Content `
    -LiteralPath $JsonReport `
    -Value $Json `
    -Encoding UTF8

# ---------------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------------

$Results |
    Select-Object `
        Name,
        Class,
        SizeGB,
        Parameters,
        Quantization,
        TestsPassed,
        TestsTotal,
        ScorePercent,
        Deterministic,
        AverageTokSec,
        AverageLatencyMs,
        PeakRamMB,
        Verdict |
    Export-Csv `
        -LiteralPath $CsvReport `
        -NoTypeInformation `
        -Encoding UTF8

# ---------------------------------------------------------------------------
# TXT
# ---------------------------------------------------------------------------

$TxtLines = [System.Collections.Generic.List[string]]::new()

$TxtLines.Add(
    '==============================================================================='
)

$TxtLines.Add(
    ' E-ZZIO — MODEL QUALIFICATION GATE V4.0'
)

$TxtLines.Add(
    ' FULL INSTALLED MODEL FORENSIC BENCHMARK'
)

$TxtLines.Add(
    '==============================================================================='
)

$TxtLines.Add("RUN ID       : $RunId")
$TxtLines.Add("VERSION      : $Version")
$TxtLines.Add("CPU ONLY     : TRUE")
$TxtLines.Add("GPU DISABLED : TRUE")
$TxtLines.Add("MODEL COUNT  : $AllModelsCount")
$TxtLines.Add("GENERATIVE   : $GenerativeCount")
$TxtLines.Add("EMBEDDING    : $EmbeddingCount")
$TxtLines.Add('')

$TxtLines.Add('RANKING')
$TxtLines.Add('-------------------------------------------------------------------------------')

foreach ($Rank in $Report.ranking) {

    $TxtLines.Add(
        "{0,-38} SCORE={1,6}% TOK/S={2,8} LAT={3,8}ms DET={4,-5} VERDICT={5}" -f `
        $Rank.Name,
        $Rank.ScorePercent,
        $Rank.AverageTokSec,
        $Rank.AverageLatencyMs,
        $Rank.Deterministic,
        $Rank.Verdict
    )
}

$TxtLines.Add('')
$TxtLines.Add('EMBEDDING')
$TxtLines.Add('-------------------------------------------------------------------------------')

foreach ($Embedding in $EmbeddingResults) {

    $TxtLines.Add(
        "{0,-38} DIM={1,-6} AVG_MS={2,-8} VERDICT={3}" -f `
        $Embedding.Name,
        $Embedding.Dimension,
        $Embedding.AverageMs,
        $Embedding.Verdict
    )
}

$TxtLines.Add('')
$TxtLines.Add('FINAL COUNTS')
$TxtLines.Add('-------------------------------------------------------------------------------')
$TxtLines.Add("QUALIFIED : $($Qualified.Count)")
$TxtLines.Add("PARTIAL   : $($Partial.Count)")
$TxtLines.Add("FAILED    : $($Failed.Count)")
$TxtLines.Add('')
$TxtLines.Add('POLICY MODIFIED : FALSE')
$TxtLines.Add('ROUTER MODIFIED : FALSE')
$TxtLines.Add('LEDGER MODIFIED : FALSE')
$TxtLines.Add('')
$TxtLines.Add('Benchmark complete.')

Set-Content `
    -LiteralPath $TxtReport `
    -Value $TxtLines `
    -Encoding UTF8

# ============================================================================
# [12/12] VERDICT
# ============================================================================

Write-Section "[12/12] FINAL VERDICT"

Write-Host ''
Write-Host ' MODEL QUALIFICATION SUMMARY'
Write-Host ('-' * 78)

foreach ($Rank in $Report.ranking) {

    $Marker = switch ($Rank.Verdict) {
        'QUALIFIED' { '[PASS]' }
        'PARTIAL'   { '[WARN]' }
        default     { '[FAIL]' }
    }

    Write-Host (
        "{0} {1,-38} {2,6}% | {3,8} tok/s | {4}" -f `
        $Marker,
        $Rank.Name,
        $Rank.ScorePercent,
        $Rank.AverageTokSec,
        $Rank.Verdict
    )
}

Write-Host ''
Write-Host ('=' * 78)

Write-Info "JSON REPORT : $JsonReport"
Write-Info "CSV REPORT  : $CsvReport"
Write-Info "TXT REPORT  : $TxtReport"

Write-Host ''
Write-Host "MODELS DISCOVERED : $AllModelsCount"
Write-Host "GENERATIVE        : $GenerativeCount"
Write-Host "EMBEDDING         : $EmbeddingCount"
Write-Host "QUALIFIED         : $($Qualified.Count)"
Write-Host "PARTIAL           : $($Partial.Count)"
Write-Host "FAILED            : $($Failed.Count)"
Write-Host ''
Write-Host 'POLICY MODIFIED   : FALSE'
Write-Host 'ROUTER MODIFIED   : FALSE'
Write-Host 'LEDGER MODIFIED   : FALSE'

Write-Host ''
Write-Host ('=' * 78)
Write-Host ' E-ZZIO MODEL QUALIFICATION V4.0 COMPLETED'
Write-Host ('=' * 78)
````
