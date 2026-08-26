#requires -Version 7.4
# =============================================================================
# E-ZZIO — MODEL QUALIFICATION GATE
# Version : 4.3.1
# Mode    : CPU-ONLY / SINGLE-MODEL-SWITCH / FORENSIC / POTENTIAL-PROFILING
# =============================================================================
#
# OBJECTIF
# --------
# Mesurer le potentiel réel des modèles Ollama locaux sans confondre :
#
#   CAPABILITY   = capacité sur tâches déterministes
#   RELIABILITY  = stabilité / taux d'échec
#   PERFORMANCE  = vitesse d'exécution
#
# GARANTIE RUNTIME
# ----------------
#   0 ou 1 modèle actif.
#   Jamais 2 ou 3 modèles simultanément.
#   Chaque modèle est chargé individuellement.
#   Chaque modèle est libéré avant le suivant.
#   Le runtime final doit revenir à 0 modèle actif.
#
# IMPORTANT
# ---------
# Les modèles d'embeddings sont inventoriés mais exclus de la batterie
# conversationnelle. Les tester avec /api/generate fausserait leur profil.
#
# SORTIES
# -------
# audit\model_gate_v4.3.1\
#
#   qualification_<RunId>.json
#   qualification_<RunId>.csv
#   forensic_<RunId>.log
#   summary_<RunId>.txt
#
# EXÉCUTION
# ---------
# cd G:\AI\E-zzio
#
# pwsh.exe -NoProfile -ExecutionPolicy Bypass -File `
#   .\EZZIO_Model_Qualification_Gate_v4.3.1.ps1
#
# =============================================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# =============================================================================
# [0/18] CONFIGURATION
# =============================================================================

$Version = '4.3.1'

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

$AuditRoot = Join-Path `
    $Root `
    'audit\model_gate_v4.3.1'

if (-not (Test-Path -LiteralPath $AuditRoot)) {
    New-Item `
        -ItemType Directory `
        -Path $AuditRoot `
        -Force |
        Out-Null
}

$RunId = Get-Date -Format 'yyyyMMdd_HHmmss'

$LogPath = Join-Path `
    $AuditRoot `
    "forensic_$RunId.log"

$JsonPath = Join-Path `
    $AuditRoot `
    "qualification_$RunId.json"

$CsvPath = Join-Path `
    $AuditRoot `
    "qualification_$RunId.csv"

$SummaryPath = Join-Path `
    $AuditRoot `
    "summary_$RunId.txt"

$OllamaHost = 'http://127.0.0.1:11434'

# -------------------------------------------------------------------------
# CPU / RAM
# -------------------------------------------------------------------------

$CpuName = 'UNKNOWN'
$CpuCores = 0
$CpuThreads = [Environment]::ProcessorCount
$TotalRamGB = 0
$AvailableRamGB = 0

try {
    $cpu = Get-CimInstance Win32_Processor |
        Select-Object -First 1

    if ($null -ne $cpu) {
        $CpuName = [string]$cpu.Name
        $CpuCores = [int]$cpu.NumberOfCores
        $CpuThreads = [int]$cpu.NumberOfLogicalProcessors
    }
}
catch {
    $CpuName = 'UNKNOWN'
}

try {
    $os = Get-CimInstance Win32_OperatingSystem

    if ($null -ne $os) {

        $TotalRamGB = [math]::Round(
            [double]$os.TotalVisibleMemorySize / 1MB,
            2
        )

        $AvailableRamGB = [math]::Round(
            [double]$os.FreePhysicalMemory / 1MB,
            2
        )
    }
}
catch {
    $TotalRamGB = 0
    $AvailableRamGB = 0
}

# -------------------------------------------------------------------------
# TEST CONFIGURATION
# -------------------------------------------------------------------------

$WarmupRuns = 1
$StabilityRuns = 2

# 0 = tous les modèles.
$MaxModels = 0

# -------------------------------------------------------------------------
# RUNTIME
# -------------------------------------------------------------------------

$KeepAlive = '5m'
$SwitchTimeoutSec = 180
$TestTimeoutSec = 300
$UnloadRetries = 8
$UnloadDelayMs = 500

# -------------------------------------------------------------------------
# PERFORMANCE REFERENCE
# -------------------------------------------------------------------------

$ReferenceTPS = 40

# -------------------------------------------------------------------------
# THRESHOLDS
# -------------------------------------------------------------------------

$Thresholds = [ordered]@{

    MinOverallScore       = 60
    MinReliabilityScore   = 70

    MinInstructionScore   = 60
    MinReasoningScore     = 50
    MinCodeScore          = 50
    MinFrenchScore        = 50

    MinStabilityScore     = 70

    MaxFailureRatePercent = 20
}

# =============================================================================
# [1/18] FORENSIC OUTPUT
# =============================================================================

function Write-Forensic {

    param(
        [Parameter(Mandatory)]
        [string]$Message,

        [ValidateSet(
            'INFO',
            'PASS',
            'WARN',
            'FAIL',
            'SWITCH',
            'TEST',
            'METRIC'
        )]
        [string]$Level = 'INFO'
    )

    $timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss.fff'

    $line = '[{0}] [{1}] {2}' -f `
        $timestamp,
        $Level,
        $Message

    Add-Content `
        -LiteralPath $LogPath `
        -Value $line `
        -Encoding UTF8

    switch ($Level) {

        'PASS' {
            Write-Host $line -ForegroundColor Green
        }

        'WARN' {
            Write-Host $line -ForegroundColor Yellow
        }

        'FAIL' {
            Write-Host $line -ForegroundColor Red
        }

        'SWITCH' {
            Write-Host $line -ForegroundColor Cyan
        }

        'TEST' {
            Write-Host $line -ForegroundColor Magenta
        }

        'METRIC' {
            Write-Host $line -ForegroundColor DarkCyan
        }

        default {
            Write-Host $line
        }
    }
}

function Write-Section {

    param(
        [Parameter(Mandatory)]
        [string]$Title
    )

    Write-Host ''
    Write-Host ('=' * 82)
    Write-Host $Title
    Write-Host ('=' * 82)
}

# =============================================================================
# [2/18] OLLAMA API
# =============================================================================

function Test-OllamaAvailable {

    try {

        $null = Invoke-RestMethod `
            -Uri "$OllamaHost/api/tags" `
            -Method Get `
            -TimeoutSec 10

        return $true
    }
    catch {

        return $false
    }
}

function Get-OllamaModels {

    try {

        $response = Invoke-RestMethod `
            -Uri "$OllamaHost/api/tags" `
            -Method Get `
            -TimeoutSec 15

        if ($null -eq $response.models) {
            return @()
        }

        return @(
            $response.models |
                ForEach-Object {

                    $family = [string]$_.details.family
                    $name = [string]$_.name

                    $isEmbedding = $false

                    if ($family -match '(?i)bert|nomic|embedding') {
                        $isEmbedding = $true
                    }

                    if ($name -match '(?i)embed|bge|nomic-embed') {
                        $isEmbedding = $true
                    }

                    [PSCustomObject]@{

                        Name = $name

                        SizeBytes = [int64]$_.size

                        SizeGB = [math]::Round(
                            [double]$_.size / 1GB,
                            2
                        )

                        Parameter = [string]$_.details.parameter_size

                        Quant = [string]$_.details.quantization_level

                        Family = $family

                        IsEmbedding = $isEmbedding
                    }
                }
        )
    }
    catch {

        throw (
            'Impossible de récupérer les modèles Ollama : ' +
            $_.Exception.Message
        )
    }
}

function Get-OllamaRunningModels {

    try {

        $response = Invoke-RestMethod `
            -Uri "$OllamaHost/api/ps" `
            -Method Get `
            -TimeoutSec 10

        if ($null -eq $response.models) {
            return @()
        }

        return @($response.models)
    }
    catch {

        Write-Forensic `
            -Message (
                'Lecture /api/ps impossible : ' +
                $_.Exception.Message
            ) `
            -Level WARN

        return @()
    }
}

function Get-RunningModelNames {

    $running = @(Get-OllamaRunningModels)

    $names = @(
        $running |
            ForEach-Object {

                if ($null -ne $_.name) {
                    [string]$_.name
                }
                elseif ($null -ne $_.model) {
                    [string]$_.model
                }
            }
    )

    return @(
        $names |
            Where-Object {
                -not [string]::IsNullOrWhiteSpace($_)
            }
    )
}

# =============================================================================
# [3/18] SINGLE MODEL RUNTIME
# =============================================================================

function Assert-SingleModel {

    $running = @(Get-RunningModelNames)

    if ($running.Count -gt 1) {

        Write-Forensic `
            -Message (
                'VIOLATION SINGLE-MODEL : ' +
                "$($running.Count) modèles actifs : " +
                ($running -join ', ')
            ) `
            -Level FAIL

        throw 'SINGLE_MODEL_VIOLATION'
    }

    if ($running.Count -eq 1) {

        Write-Forensic `
            -Message (
                "Modèle actif confirmé : $($running[0])"
            ) `
            -Level INFO

        return $running[0]
    }

    return $null
}

function Wait-RuntimeEmpty {

    for (
        $attempt = 1;
        $attempt -le $UnloadRetries;
        $attempt++
    ) {

        $running = @(Get-RunningModelNames)

        if ($running.Count -eq 0) {

            Write-Forensic `
                -Message (
                    "Runtime EMPTY confirmé à la tentative " +
                    "$attempt/$UnloadRetries."
                ) `
                -Level PASS

            return $true
        }

        Start-Sleep -Milliseconds $UnloadDelayMs
    }

    $remaining = @(Get-RunningModelNames)

    Write-Forensic `
        -Message (
            'Runtime non vide après nettoyage : ' +
            ($remaining -join ', ')
        ) `
        -Level FAIL

    return $false
}

function Unload-OllamaModel {

    param(
        [Parameter(Mandatory)]
        [string]$Model
    )

    Write-Forensic `
        -Message "LIBERATION -> $Model" `
        -Level SWITCH

    $payload = @{
        model = $Model
        prompt = ''
        stream = $false
        keep_alive = 0
    } |
        ConvertTo-Json -Depth 8

    try {

        Invoke-RestMethod `
            -Uri "$OllamaHost/api/generate" `
            -Method Post `
            -ContentType 'application/json' `
            -Body $payload `
            -TimeoutSec 60 |
            Out-Null
    }
    catch {

        Write-Forensic `
            -Message (
                "API unload signal pour $Model : " +
                $_.Exception.Message
            ) `
            -Level WARN
    }

    if (Wait-RuntimeEmpty) {

        Write-Forensic `
            -Message (
                "Modèle $Model libéré via API."
            ) `
            -Level PASS

        return $true
    }

    return $false
}

function Clear-OllamaRuntime {

    Write-Forensic `
        -Message 'NETTOYAGE GLOBAL DU RUNTIME OLLAMA' `
        -Level SWITCH

    $running = @(Get-RunningModelNames)

    if ($running.Count -gt 1) {

        Write-Forensic `
            -Message (
                'FAIL-CLOSED : plusieurs modèles actifs avant nettoyage : ' +
                ($running -join ', ')
            ) `
            -Level FAIL

        throw 'MULTIPLE_MODELS_BEFORE_CLEANUP'
    }

    if ($running.Count -eq 1) {

        $released = Unload-OllamaModel `
            -Model $running[0]

        if (-not $released) {

            throw 'MODEL_RELEASE_FAILED'
        }
    }

    if (-not (Wait-RuntimeEmpty)) {

        throw 'RUNTIME_NOT_EMPTY'
    }

    return $true
}

function Switch-OllamaModel {

    param(
        [Parameter(Mandatory)]
        [string]$Model
    )

    Write-Forensic `
        -Message "========== SWITCH -> $Model ==========" `
        -Level SWITCH

    $preRunning = @(Get-RunningModelNames)

    if ($preRunning.Count -gt 1) {

        throw 'PRE_SWITCH_MULTIPLE_MODELS'
    }

    if ($preRunning.Count -eq 1) {

        if ($preRunning[0] -ne $Model) {

            $released = Unload-OllamaModel `
                -Model $preRunning[0]

            if (-not $released) {

                throw 'PREVIOUS_MODEL_UNLOAD_FAILED'
            }
        }
        else {

            # Même modèle déjà chargé :
            # on le libère afin que chaque qualification reparte
            # d'un état propre.
            $released = Unload-OllamaModel `
                -Model $preRunning[0]

            if (-not $released) {

                throw 'CURRENT_MODEL_RESET_FAILED'
            }
        }
    }

    if (-not (Wait-RuntimeEmpty)) {

        throw 'RUNTIME_NOT_EMPTY_BEFORE_LOAD'
    }

    $payload = @{
        model = $Model
        prompt = 'E-ZZIO MODEL QUALIFICATION GATE SWITCH PROBE. Reply READY.'
        stream = $false
        keep_alive = $KeepAlive
        options = @{
            temperature = 0
            num_predict = 8
        }
    } |
        ConvertTo-Json -Depth 8

    $start = Get-Date

    try {

        $response = Invoke-RestMethod `
            -Uri "$OllamaHost/api/generate" `
            -Method Post `
            -ContentType 'application/json' `
            -Body $payload `
            -TimeoutSec $SwitchTimeoutSec
    }
    catch {

        Write-Forensic `
            -Message (
                "Echec chargement $Model : " +
                $_.Exception.Message
            ) `
            -Level FAIL

        throw 'MODEL_LOAD_FAILED'
    }

    $wallMs = (
        (Get-Date) - $start
    ).TotalMilliseconds

    $loadMs = 0

    if ($null -ne $response.load_duration) {

        $loadMs = [math]::Round(
            [double]$response.load_duration / 1000000,
            3
        )
    }

    $runningAfter = @(Get-RunningModelNames)

    if ($runningAfter.Count -ne 1) {

        Write-Forensic `
            -Message (
                "Post-switch invalide : " +
                "$($runningAfter.Count) modèle(s) actif(s)."
            ) `
            -Level FAIL

        throw 'POST_SWITCH_CARDINALITY_FAILURE'
    }

    if ($runningAfter[0] -ne $Model) {

        Write-Forensic `
            -Message (
                "Mauvais modèle actif : $($runningAfter[0]) " +
                "au lieu de $Model."
            ) `
            -Level FAIL

        throw 'POST_SWITCH_WRONG_MODEL'
    }

    Write-Forensic `
        -Message (
            "SWITCH OK | Model=$Model | " +
            "Load=$loadMs ms | Wall=$([math]::Round($wallMs,3)) ms | " +
            'Active=1'
        ) `
        -Level PASS

    return [PSCustomObject]@{

        Model = $Model
        LoadMs = [math]::Round($loadMs, 3)
        WallMs = [math]::Round($wallMs, 3)
        ActiveModels = 1
    }
}

# =============================================================================
# [4/18] RESPONSE EVALUATION
# =============================================================================

function Evaluate-Response {

    param(
        [Parameter(Mandatory)]
        [string]$Category,

        [Parameter(Mandatory)]
        [string]$Prompt,

        [AllowEmptyString()]
        [string]$Response
    )

    if ($null -eq $Response) {
        $Response = ''
    }

    $text = $Response.Trim()

    $score = 0

    $hardPass = $false

    $reasons = New-Object `
        System.Collections.Generic.List[string]

    # -------------------------------------------------------------------------
    # EMPTY RESPONSE
    # -------------------------------------------------------------------------

    if ([string]::IsNullOrWhiteSpace($text)) {

        $reasons.Add('empty-response')

        return [PSCustomObject]@{

            Score = 0
            HardPass = $false
            Reasons = @($reasons)
        }
    }

    $score += 20
    $reasons.Add('non-empty')

    # -------------------------------------------------------------------------
    # INSTRUCTION
    # -------------------------------------------------------------------------

    if ($Category -eq 'Instruction') {

        $expectedLines = @(
            'ALPHA',
            'BETA',
            'GAMMA'
        )

        $lines = @(
            $text -split '\r?\n' |
                Where-Object {
                    -not [string]::IsNullOrWhiteSpace($_)
                } |
                ForEach-Object {
                    $_.Trim()
                }
        )

        if (
            $lines.Count -eq 3 -and
            $lines[0] -eq 'ALPHA' -and
            $lines[1] -eq 'BETA' -and
            $lines[2] -eq 'GAMMA'
        ) {

            $score = 100
            $hardPass = $true
            $reasons.Add('exact-three-line-match')
        }
        else {

            $matchCount = 0

            foreach ($expected in $expectedLines) {

                if ($text -match "(?m)^$expected$") {
                    $matchCount++
                }
            }

            $score += $matchCount * 20

            if ($lines.Count -le 4) {
                $score += 10
            }

            $reasons.Add(
                "instruction-matches=$matchCount"
            )
        }
    }

    # -------------------------------------------------------------------------
    # REASONING
    # -------------------------------------------------------------------------

    if ($Category -eq 'Reasoning') {

        if ($Prompt -match '12 tâches') {

            # 12 + 6 + 11 = 29
            if ($text -match '(?<!\d)29(?!\d)') {

                $score += 50
                $reasons.Add('expected-result-29')
            }

            if (
                $text -match '(?i)12' -and
                $text -match '(?i)6' -and
                $text -match '(?i)11'
            ) {

                $score += 20
                $reasons.Add('intermediate-values')
            }
        }

        elseif ($Prompt -match '100 unités') {

            # 100 - 30 - 20 + 10 = 60
            if ($text -match '(?<!\d)60(?!\d)') {

                $score += 50
                $reasons.Add('expected-result-60')
            }

            if (
                $text -match '(?i)30' -and
                $text -match '(?i)20' -and
                $text -match '(?i)10'
            ) {

                $score += 20
                $reasons.Add('intermediate-values')
            }
        }

        if (
            $text -match '(?i)donc|car|puisque|étape|calcul|ensuite'
        ) {

            $score += 10
            $reasons.Add('reasoning-evidence')
        }

        if ($score -ge 70) {
            $hardPass = $true
        }
    }

    # -------------------------------------------------------------------------
    # CODE
    # -------------------------------------------------------------------------

    if ($Category -eq 'Code') {

        if ($Prompt -match 'safe_divide') {

            if ($text -match '(?i)def\s+safe_divide') {
                $score += 35
                $reasons.Add('python-function')
            }

            if ($text -match '(?i)return\s+a\s*/\s*b') {
                $score += 25
                $reasons.Add('division')
            }

            if ($text -match '(?i)b\s*==\s*0') {
                $score += 20
                $reasons.Add('zero-division-guard')
            }

            if ($text -match '(?i)return\s+None') {
                $score += 20
                $reasons.Add('none-return')
            }
        }

        elseif ($Prompt -match 'Get-SafeValue') {

            if ($text -match '(?i)function\s+Get-SafeValue') {
                $score += 35
                $reasons.Add('powershell-function')
            }

            if ($text -match '\[object\]\s*\$Value') {
                $score += 25
                $reasons.Add('typed-parameter')
            }

            if ($text -match '(?i)\$null') {
                $score += 20
                $reasons.Add('null-handling')
            }

            if (
                $text -match '(?i)Write-Output|return'
            ) {

                $score += 20
                $reasons.Add('return-path')
            }
        }

        if ($score -ge 70) {
            $hardPass = $true
        }
    }

    # -------------------------------------------------------------------------
    # JSON
    # -------------------------------------------------------------------------

    if ($Category -eq 'Structured') {

        try {

            $json = $text |
                ConvertFrom-Json `
                    -ErrorAction Stop

            if ($null -ne $json) {

                $score += 50
                $reasons.Add('valid-json')
            }

            if ([string]$json.status -eq 'PASS') {

                $score += 20
                $reasons.Add('status-pass')
            }

            if ([int]$json.score -eq 100) {

                $score += 15
                $reasons.Add('score-100')
            }

            if ([string]$json.mode -eq 'CPU') {

                $score += 15
                $reasons.Add('mode-cpu')
            }

            if ($score -ge 80) {
                $hardPass = $true
            }
        }
        catch {

            $reasons.Add('invalid-json')
        }
    }

    # -------------------------------------------------------------------------
    # FRENCH
    # -------------------------------------------------------------------------

    if ($Category -eq 'French') {

        if (
            $text -match `
                '(?i)\b(le|la|les|des|une|dans|avec|pour|est|sont|entre|débit|latence|fiabilité)\b'
        ) {

            $score += 40
            $reasons.Add('french-lexical-evidence')
        }

        if ($text.Length -ge 120) {

            $score += 20
            $reasons.Add('adequate-length')
        }

        if (
            $text -match '(?i)latence' -and
            $text -match '(?i)débit' -and
            $text -match '(?i)fiabilité'
        ) {

            $score += 40
            $reasons.Add('three-concepts-covered')
        }

        if ($score -ge 70) {
            $hardPass = $true
        }
    }

    # -------------------------------------------------------------------------
    # ROBUSTNESS
    # -------------------------------------------------------------------------

    if ($Category -eq 'Robustness') {

        if (
            $text -match '(?i)fausse|faux|pas nécessairement|cela dépend'
        ) {

            $score += 40
            $reasons.Add('claim-rejected')
        }

        if (
            $text -match '(?i)capacité|qualité|raisonnement|intelligence|performance'
        ) {

            $score += 30
            $reasons.Add('conceptual-distinction')
        }

        if ($text.Length -ge 100) {

            $score += 20
            $reasons.Add('explanation-present')
        }

        if ($score -ge 70) {
            $hardPass = $true
        }
    }

    # -------------------------------------------------------------------------
    # GENERAL
    # -------------------------------------------------------------------------

    if ($Category -eq 'General') {

        if ($text.Length -ge 100) {

            $score += 20
            $reasons.Add('adequate-response')
        }

        if ($text.Length -ge 300) {

            $score += 20
            $reasons.Add('substantive-response')
        }

        if (
            $text -match `
                '(?i)politique|exécution|audit|séparation|responsabilité'
        ) {

            $score += 30
            $reasons.Add('technical-content')
        }

        if (
            $text -match `
                '(?i)architecture|sécurité|forensic|contrôle'
        ) {

            $score += 30
            $reasons.Add('architecture-evidence')
        }

        if ($score -ge 70) {
            $hardPass = $true
        }
    }

    if ($score -gt 100) {
        $score = 100
    }

    return [PSCustomObject]@{

        Score = [int]$score
        HardPass = $hardPass
        Reasons = @($reasons)
    }
}

# =============================================================================
# [5/18] MODEL TEST
# =============================================================================

function Invoke-ModelTest {

    param(
        [Parameter(Mandatory)]
        [string]$Model,

        [Parameter(Mandatory)]
        [string]$TestId,

        [Parameter(Mandatory)]
        [string]$Category,

        [Parameter(Mandatory)]
        [string]$Prompt,

        [int]$MaxTokens = 256
    )

    Write-Forensic `
        -Message "TEST $TestId | $Category" `
        -Level TEST

    $active = Assert-SingleModel

    if ($active -ne $Model) {

        Write-Forensic `
            -Message (
                "Mauvais modèle actif : $active | attendu : $Model"
            ) `
            -Level FAIL

        throw 'ACTIVE_MODEL_MISMATCH'
    }

    $payload = @{
        model = $Model
        prompt = $Prompt
        stream = $false
        keep_alive = $KeepAlive
        options = @{
            temperature = 0
            num_predict = $MaxTokens
        }
    } |
        ConvertTo-Json -Depth 8

    $start = Get-Date

    try {

        $response = Invoke-RestMethod `
            -Uri "$OllamaHost/api/generate" `
            -Method Post `
            -ContentType 'application/json' `
            -Body $payload `
            -TimeoutSec $TestTimeoutSec

        $wallMs = (
            (Get-Date) - $start
        ).TotalMilliseconds

        $loadMs = 0
        $promptMs = 0
        $evalMs = 0

        if ($null -ne $response.load_duration) {

            $loadMs = [math]::Round(
                [double]$response.load_duration / 1000000,
                3
            )
        }

        if ($null -ne $response.prompt_eval_duration) {

            $promptMs = [math]::Round(
                [double]$response.prompt_eval_duration / 1000000,
                3
            )
        }

        if ($null -ne $response.eval_duration) {

            $evalMs = [math]::Round(
                [double]$response.eval_duration / 1000000,
                3
            )
        }

        $text = ''

        if ($null -ne $response.response) {
            $text = [string]$response.response
        }

        # IMPORTANT :
        # Evaluate-Response accepte désormais explicitement une réponse vide.
        $evaluation = Evaluate-Response `
            -Category $Category `
            -Prompt $Prompt `
            -Response $text

        $generatedTokens = 0
        $promptTokens = 0

        if ($null -ne $response.eval_count) {
            $generatedTokens = [int]$response.eval_count
        }

        if ($null -ne $response.prompt_eval_count) {
            $promptTokens = [int]$response.prompt_eval_count
        }

        $tps = 0

        if (
            $generatedTokens -gt 0 -and
            $evalMs -gt 0
        ) {

            $tps = [math]::Round(
                $generatedTokens /
                ($evalMs / 1000),
                3
            )
        }

        $success = (
            -not [string]::IsNullOrWhiteSpace($text)
        )

        if (-not $success) {

            Write-Forensic `
                -Message (
                    "TEST $TestId : réponse vide. " +
                    'Echec enregistré sans crash du Gate.'
                ) `
                -Level WARN
        }

        $preview = ''

        if ($text.Length -gt 300) {
            $preview = $text.Substring(0,300)
        }
        else {
            $preview = $text
        }

        $result = [PSCustomObject]@{

            Model = $Model
            TestId = $TestId
            Category = $Category

            Success = $success

            Score = [int]$evaluation.Score
            HardPass = [bool]$evaluation.HardPass

            DurationMs = [math]::Round($wallMs,3)
            LoadMs = [math]::Round($loadMs,3)
            PromptMs = [math]::Round($promptMs,3)
            EvalMs = [math]::Round($evalMs,3)

            PromptTokens = $promptTokens
            GeneratedTokens = $generatedTokens

            TokensPerSecond = $tps

            ResponseChars = $text.Length
            ResponsePreview = $preview

            Reasons = @($evaluation.Reasons)

            Error = $null
        }

        Write-Forensic `
            -Message (
                'RESULT {0} | Score={1} | HardPass={2} | ' +
                'Wall={3}ms | Load={4}ms | Prompt={5}ms | ' +
                'Eval={6}ms | Tokens={7} | TPS={8}' -f
                $TestId,
                $result.Score,
                $result.HardPass,
                $result.DurationMs,
                $result.LoadMs,
                $result.PromptMs,
                $result.EvalMs,
                $result.GeneratedTokens,
                $result.TokensPerSecond
            ) `
            -Level METRIC

        return $result
    }
    catch {

        Write-Forensic `
            -Message (
                "TEST $TestId FAIL : " +
                $_.Exception.Message
            ) `
            -Level FAIL

        return [PSCustomObject]@{

            Model = $Model
            TestId = $TestId
            Category = $Category

            Success = $false
            Score = 0
            HardPass = $false

            DurationMs = 0
            LoadMs = 0
            PromptMs = 0
            EvalMs = 0

            PromptTokens = 0
            GeneratedTokens = 0

            TokensPerSecond = 0

            ResponseChars = 0
            ResponsePreview = ''

            Reasons = @('exception')

            Error = $_.Exception.Message
        }
    }
}

# =============================================================================
# [6/18] TEST BATTERY
# =============================================================================

$Tests = @(

    [PSCustomObject]@{
        Id = 'GEN-01'
        Category = 'General'
        Prompt = @'
Réponds en français à cette question :
Pourquoi une architecture logicielle robuste doit-elle séparer
les politiques de décision, l'exécution et l'audit ?

Donne une réponse structurée et techniquement précise.
'@
        MaxTokens = 300
    },

    [PSCustomObject]@{
        Id = 'INS-01'
        Category = 'Instruction'
        Prompt = @'
Réponds exactement avec trois lignes.
Ligne 1 : ALPHA
Ligne 2 : BETA
Ligne 3 : GAMMA
N'ajoute absolument aucun autre texte.
'@
        MaxTokens = 80
    },

    [PSCustomObject]@{
        Id = 'REASON-01'
        Category = 'Reasoning'
        Prompt = @'
Un système possède 3 files.

La première contient 12 tâches.
La deuxième contient deux fois moins de tâches que la première.
La troisième contient 5 tâches de plus que la deuxième.

Combien de tâches y a-t-il au total ?
Explique brièvement le calcul.
'@
        MaxTokens = 180
    },

    [PSCustomObject]@{
        Id = 'REASON-02'
        Category = 'Reasoning'
        Prompt = @'
Un programme reçoit 100 unités.
Il dépense 30 %, puis 20 unités supplémentaires.
Il reçoit ensuite 10 unités.

Quelle est la quantité finale ?
Montre les étapes du calcul.
'@
        MaxTokens = 180
    },

    [PSCustomObject]@{
        Id = 'CODE-01'
        Category = 'Code'
        Prompt = @'
Écris une fonction Python appelée safe_divide(a, b)
qui retourne a / b et retourne None lorsque b vaut zéro.

Donne uniquement le code.
'@
        MaxTokens = 180
    },

    [PSCustomObject]@{
        Id = 'CODE-02'
        Category = 'Code'
        Prompt = @'
Écris une fonction PowerShell Get-SafeValue qui accepte
un paramètre [object]$Value et retourne $Value uniquement
s'il n'est pas $null. Sinon elle retourne une chaîne vide.

Donne uniquement le code.
'@
        MaxTokens = 180
    },

    [PSCustomObject]@{
        Id = 'JSON-01'
        Category = 'Structured'
        Prompt = @'
Retourne uniquement un JSON valide, sans markdown :

{
  "status": "PASS",
  "score": 100,
  "mode": "CPU"
}
'@
        MaxTokens = 120
    },

    [PSCustomObject]@{
        Id = 'FR-01'
        Category = 'French'
        Prompt = @'
Explique en français, avec un vocabulaire technique naturel,
la différence entre latence, débit et fiabilité pour un modèle IA local.
'@
        MaxTokens = 250
    },

    [PSCustomObject]@{
        Id = 'ROB-01'
        Category = 'Robustness'
        Prompt = @'
Tu dois analyser cette affirmation :

"Un modèle plus rapide est nécessairement plus intelligent."

Dis si elle est vraie ou fausse et explique pourquoi.
Ne te contente pas de répéter l'affirmation.
'@
        MaxTokens = 220
    },

    [PSCustomObject]@{
        Id = 'CTX-01'
        Category = 'General'
        Prompt = @'
Mémorise mentalement ces quatre éléments :

AZUR = 17
BUS = 42
EZZIO = 91
SWITCH = 63

Puis réponds :
Quelle valeur correspond à EZZIO ?
'@
        MaxTokens = 120
    }
)

# =============================================================================
# [7/18] CATEGORY SCORE
# =============================================================================

function Get-CategoryScore {

    param(
        [array]$Results,

        [string]$Category
    )

    $items = @(
        $Results |
            Where-Object {
                $_.Category -eq $Category
            }
    )

    if ($items.Count -eq 0) {
        return 0
    }

    return [math]::Round(
        (
            ($items | Measure-Object -Property Score -Average).Average
        ),
        2
    )
}

# =============================================================================
# [8/18] MODEL QUALIFICATION
# =============================================================================

function Test-Model {

    param(
        [Parameter(Mandatory)]
        [PSCustomObject]$Model,

        [int]$Index,

        [int]$Total
    )

    Write-Section "[MODEL] $($Model.Name)"

    Write-Forensic `
        -Message (
            "Début qualification : $($Model.Name)"
        ) `
        -Level INFO

    # -------------------------------------------------------------------------
    # SWITCH
    # -------------------------------------------------------------------------

    $switchResult = Switch-OllamaModel `
        -Model $Model.Name

    $results = New-Object `
        System.Collections.Generic.List[object]

    # -------------------------------------------------------------------------
    # WARMUP
    # -------------------------------------------------------------------------

    for (
        $w = 1;
        $w -le $WarmupRuns;
        $w++
    ) {

        Write-Forensic `
            -Message (
                "Warmup $w/$WarmupRuns : $($Model.Name)"
            ) `
            -Level INFO

        $warmupPayload = @{
            model = $Model.Name
            prompt = 'Réponds simplement : READY'
            stream = $false
            keep_alive = $KeepAlive
            options = @{
                temperature = 0
                num_predict = 16
            }
        } |
            ConvertTo-Json -Depth 8

        try {

            Invoke-RestMethod `
                -Uri "$OllamaHost/api/generate" `
                -Method Post `
                -ContentType 'application/json' `
                -Body $warmupPayload `
                -TimeoutSec $TestTimeoutSec |
                Out-Null
        }
        catch {

            Write-Forensic `
                -Message (
                    "Warmup échoué : " +
                    $_.Exception.Message
                ) `
                -Level WARN
        }
    }

    # -------------------------------------------------------------------------
    # BATTERY
    # -------------------------------------------------------------------------

    foreach ($test in $Tests) {

        $r = Invoke-ModelTest `
            -Model $Model.Name `
            -TestId $test.Id `
            -Category $test.Category `
            -Prompt $test.Prompt `
            -MaxTokens $test.MaxTokens

        $results.Add($r)
    }

    # -------------------------------------------------------------------------
    # STABILITY
    # -------------------------------------------------------------------------

    Write-Forensic `
        -Message (
            "Tests de stabilité : $StabilityRuns exécutions."
        ) `
        -Level INFO

    $stabilityScores = New-Object `
        System.Collections.Generic.List[int]

    for (
        $s = 1;
        $s -le $StabilityRuns;
        $s++
    ) {

        $stable = Invoke-ModelTest `
            -Model $Model.Name `
            -TestId "STAB-$s" `
            -Category 'General' `
            -Prompt @'
Réponds en une phrase :
quel est le rôle principal d'un journal forensic ?
'@ `
            -MaxTokens 100

        $stabilityScores.Add(
            [int]$stable.Score
        )

        $results.Add($stable)
    }

    # -------------------------------------------------------------------------
    # AGGREGATION
    # -------------------------------------------------------------------------

    $allResults = @($results)

    $successful = @(
        $allResults |
            Where-Object {
                $_.Success -eq $true
            }
    )

    $failed = @(
        $allResults |
            Where-Object {
                $_.Success -ne $true
            }
    )

    $avgScore = 0

    if ($allResults.Count -gt 0) {

        $avgScore = [math]::Round(
            (
                ($allResults |
                    Measure-Object `
                        -Property Score `
                        -Average).Average
            ),
            2
        )
    }

    $avgTPS = 0

    if ($successful.Count -gt 0) {

        $avgTPS = [math]::Round(
            (
                ($successful |
                    Measure-Object `
                        -Property TokensPerSecond `
                        -Average).Average
            ),
            3
        )
    }

    $avgLatency = 0

    if ($successful.Count -gt 0) {

        $avgLatency = [math]::Round(
            (
                ($successful |
                    Measure-Object `
                        -Property DurationMs `
                        -Average).Average
            ),
            2
        )
    }

    $failureRate = 100

    if ($allResults.Count -gt 0) {

        $failureRate = [math]::Round(
            (
                $failed.Count /
                $allResults.Count
            ) * 100,
            2
        )
    }

    $instructionScore = Get-CategoryScore `
        -Results $allResults `
        -Category 'Instruction'

    $reasoningScore = Get-CategoryScore `
        -Results $allResults `
        -Category 'Reasoning'

    $codeScore = Get-CategoryScore `
        -Results $allResults `
        -Category 'Code'

    $frenchScore = Get-CategoryScore `
        -Results $allResults `
        -Category 'French'

    $structuredScore = Get-CategoryScore `
        -Results $allResults `
        -Category 'Structured'

    $generalScore = Get-CategoryScore `
        -Results $allResults `
        -Category 'General'

    $robustnessScore = Get-CategoryScore `
        -Results $allResults `
        -Category 'Robustness'

    # -------------------------------------------------------------------------
    # STABILITY
    # -------------------------------------------------------------------------

    $stabilityScore = 0

    if ($stabilityScores.Count -gt 0) {

        $stabilityScore = [math]::Round(
            (
                ($stabilityScores |
                    Measure-Object -Average).Average
            ),
            2
        )
    }

    # -------------------------------------------------------------------------
    # CAPABILITY
    # -------------------------------------------------------------------------

    $capabilityScore = [math]::Round(
        (
            ($instructionScore * 0.18) +
            ($reasoningScore * 0.25) +
            ($codeScore * 0.20) +
            ($frenchScore * 0.10) +
            ($structuredScore * 0.10) +
            ($generalScore * 0.10) +
            ($robustnessScore * 0.07)
        ),
        2
    )

    # -------------------------------------------------------------------------
    # PERFORMANCE
    # -------------------------------------------------------------------------

    $performanceScore = 0

    if ($avgTPS -gt 0) {

        $performanceScore = [math]::Min(
            100,
            [math]::Round(
                (
                    $avgTPS /
                    $ReferenceTPS
                ) * 100,
                2
            )
        )
    }

    # -------------------------------------------------------------------------
    # RELIABILITY
    # -------------------------------------------------------------------------

    $reliabilityScore = [math]::Round(
        (
            ($stabilityScore * 0.60) +
            ((100 - $failureRate) * 0.40)
        ),
        2
    )

    # -------------------------------------------------------------------------
    # OVERALL
    # -------------------------------------------------------------------------

    $overall = [math]::Round(
        (
            ($capabilityScore * 0.55) +
            ($reliabilityScore * 0.25) +
            ($performanceScore * 0.20)
        ),
        2
    )

    # -------------------------------------------------------------------------
    # VERDICT
    # -------------------------------------------------------------------------

    $verdict = 'FAIL'

    if (
        $overall -ge $Thresholds.MinOverallScore -and
        $reliabilityScore -ge $Thresholds.MinReliabilityScore -and
        $instructionScore -ge $Thresholds.MinInstructionScore -and
        $reasoningScore -ge $Thresholds.MinReasoningScore -and
        $codeScore -ge $Thresholds.MinCodeScore -and
        $frenchScore -ge $Thresholds.MinFrenchScore -and
        $stabilityScore -ge $Thresholds.MinStabilityScore -and
        $failureRate -le $Thresholds.MaxFailureRatePercent
    ) {

        $verdict = 'QUALIFIED'
    }
    elseif ($overall -ge 50) {

        $verdict = 'PARTIAL'
    }

    # -------------------------------------------------------------------------
    # PROFILE
    # -------------------------------------------------------------------------

    $profile = [PSCustomObject]@{

        RunId = $RunId
        Version = $Version

        Model = $Model.Name

        ParameterSize = $Model.Parameter
        Quantization = $Model.Quant
        Family = $Model.Family

        SizeGB = $Model.SizeGB

        IsEmbedding = $Model.IsEmbedding

        CapabilityScore = $capabilityScore
        ReliabilityScore = $reliabilityScore
        PerformanceScore = $performanceScore

        OverallScore = $overall

        InstructionScore = $instructionScore
        ReasoningScore = $reasoningScore
        CodeScore = $codeScore
        FrenchScore = $frenchScore
        StructuredScore = $structuredScore
        GeneralScore = $generalScore
        RobustnessScore = $robustnessScore
        StabilityScore = $stabilityScore

        AvgLatencyMs = $avgLatency
        AvgTokensPerSec = $avgTPS

        FailureRate = $failureRate

        TestsTotal = $allResults.Count
        TestsSuccessful = $successful.Count
        TestsFailed = $failed.Count

        SwitchMs = $switchResult.LoadMs
        SwitchWallMs = $switchResult.WallMs

        Verdict = $verdict

        Tests = $allResults
    }

    $logLevel = 'FAIL'

    if ($verdict -eq 'QUALIFIED') {
        $logLevel = 'PASS'
    }
    elseif ($verdict -eq 'PARTIAL') {
        $logLevel = 'WARN'
    }

    Write-Forensic `
        -Message (
            "PROFILE $($Model.Name) | " +
            "CAP=$capabilityScore | " +
            "REL=$reliabilityScore | " +
            "PERF=$performanceScore | " +
            "OVERALL=$overall | " +
            "VERDICT=$verdict"
        ) `
        -Level $logLevel

    return $profile
}

# =============================================================================
# [9/18] HEADER
# =============================================================================

Write-Section `
    "[0/18] E-ZZIO MODEL QUALIFICATION GATE v$Version"

Write-Forensic `
    -Message "Version=$Version | RunId=$RunId" `
    -Level INFO

Write-Forensic `
    -Message (
        "CPU=$CpuName | Cores=$CpuCores | " +
        "Threads=$CpuThreads | RAM=${TotalRamGB}GB | " +
        "Available=${AvailableRamGB}GB"
    ) `
    -Level INFO

Write-Host ''
Write-Host "CPU              : $CpuName"
Write-Host "CORES            : $CpuCores"
Write-Host "THREADS          : $CpuThreads"
Write-Host "TOTAL RAM        : $TotalRamGB GB"
Write-Host "AVAILABLE RAM    : $AvailableRamGB GB"
Write-Host "OLLAMA HOST      : $OllamaHost"
Write-Host "RUN ID           : $RunId"

# =============================================================================
# [10/18] OLLAMA AVAILABILITY
# =============================================================================

Write-Section '[1/18] OLLAMA AVAILABILITY'

$ollamaCommand = Get-Command `
    ollama `
    -ErrorAction SilentlyContinue

if ($null -eq $ollamaCommand) {

    Write-Forensic `
        -Message 'ollama.exe introuvable dans PATH.' `
        -Level FAIL

    throw 'OLLAMA_NOT_FOUND'
}

Write-Forensic `
    -Message (
        "Ollama executable : $($ollamaCommand.Source)"
    ) `
    -Level PASS

if (-not (Test-OllamaAvailable)) {

    Write-Forensic `
        -Message (
            "Ollama API inaccessible sur $OllamaHost."
        ) `
        -Level FAIL

    throw 'OLLAMA_API_UNAVAILABLE'
}

Write-Forensic `
    -Message 'Ollama API disponible.' `
    -Level PASS

# =============================================================================
# [11/18] INVENTORY
# =============================================================================

Write-Section '[2/18] MODEL INVENTORY'

$models = @(Get-OllamaModels)

if ($models.Count -eq 0) {

    Write-Forensic `
        -Message 'Aucun modèle Ollama détecté.' `
        -Level FAIL

    throw 'NO_MODELS'
}

if (
    $MaxModels -gt 0 -and
    $models.Count -gt $MaxModels
) {

    $models = @(
        $models |
            Select-Object -First $MaxModels
    )
}

Write-Forensic `
    -Message (
        "$($models.Count) modèle(s) détecté(s)."
    ) `
    -Level PASS

foreach ($m in $models) {

    $type = 'GENERATIVE'

    if ($m.IsEmbedding) {
        $type = 'EMBEDDING'
    }

    Write-Host (
        '  - {0} | {1} GB | params={2} | ' +
        'quant={3} | family={4} | type={5}' -f
        $m.Name,
        $m.SizeGB,
        $m.Parameter,
        $m.Quant,
        $m.Family,
        $type
    )
}

# =============================================================================
# [12/18] INITIAL RUNTIME CLEANUP
# =============================================================================

Write-Section '[3/18] INITIAL RUNTIME CLEANUP'

$initialRunning = @(Get-RunningModelNames)

Write-Forensic `
    -Message (
        "Etat initial : $($initialRunning.Count) modèle(s) actif(s)."
    ) `
    -Level INFO

if ($initialRunning.Count -gt 0) {

    Write-Host ''
    Write-Host 'Modèle(s) actuellement actif(s) :'

    foreach ($running in $initialRunning) {
        Write-Host "  * $running"
    }
}

if ($initialRunning.Count -gt 1) {

    Write-Forensic `
        -Message (
            'FAIL-CLOSED : plusieurs modèles actifs avant le Gate.'
        ) `
        -Level FAIL

    throw 'INITIAL_MULTIPLE_MODELS'
}

Clear-OllamaRuntime | Out-Null

Write-Forensic `
    -Message 'PRECHECK OK : 0 modèle actif.' `
    -Level PASS

# =============================================================================
# [13/18] QUALIFICATION
# =============================================================================

Write-Section '[4/18] QUALIFICATION BATTERY'

$profiles = New-Object `
    System.Collections.Generic.List[object]

$totalModels = $models.Count
$modelIndex = 0

foreach ($model in $models) {

    $modelIndex++

    Write-Host ''
    Write-Host (
        ">>> MODELE $modelIndex/$totalModels : $($model.Name)"
    ) -ForegroundColor Cyan

    # -------------------------------------------------------------------------
    # EMBEDDING MODELS
    # -------------------------------------------------------------------------

    if ($model.IsEmbedding) {

        Write-Forensic `
            -Message (
                "SKIP $($model.Name) : modèle d'embedding, " +
                'non comparable à une batterie conversationnelle.'
            ) `
            -Level WARN

        $profiles.Add(
            [PSCustomObject]@{

                RunId = $RunId
                Version = $Version

                Model = $model.Name

                ParameterSize = $model.Parameter
                Quantization = $model.Quant
                Family = $model.Family
                SizeGB = $model.SizeGB

                IsEmbedding = $true

                CapabilityScore = 0
                ReliabilityScore = 0
                PerformanceScore = 0
                OverallScore = 0

                InstructionScore = 0
                ReasoningScore = 0
                CodeScore = 0
                FrenchScore = 0
                StructuredScore = 0
                GeneralScore = 0
                RobustnessScore = 0
                StabilityScore = 0

                AvgLatencyMs = 0
                AvgTokensPerSec = 0

                FailureRate = 0

                TestsTotal = 0
                TestsSuccessful = 0
                TestsFailed = 0

                SwitchMs = 0
                SwitchWallMs = 0

                Verdict = 'SKIP-EMBEDDING'

                Tests = @()
            }
        )

        continue
    }

    # -------------------------------------------------------------------------
    # GENERATIVE MODEL
    # -------------------------------------------------------------------------

    try {

        $profile = Test-Model `
            -Model $model `
            -Index $modelIndex `
            -Total $totalModels

        $profiles.Add($profile)
    }
    catch {

        Write-Forensic `
            -Message (
                "Qualification interrompue pour $($model.Name) : " +
                $_.Exception.Message
            ) `
            -Level FAIL

        $profiles.Add(
            [PSCustomObject]@{

                RunId = $RunId
                Version = $Version

                Model = $model.Name

                ParameterSize = $model.Parameter
                Quantization = $model.Quant
                Family = $model.Family
                SizeGB = $model.SizeGB

                IsEmbedding = $false

                CapabilityScore = 0
                ReliabilityScore = 0
                PerformanceScore = 0
                OverallScore = 0

                InstructionScore = 0
                ReasoningScore = 0
                CodeScore = 0
                FrenchScore = 0
                StructuredScore = 0
                GeneralScore = 0
                RobustnessScore = 0
                StabilityScore = 0

                AvgLatencyMs = 0
                AvgTokensPerSec = 0

                FailureRate = 100

                TestsTotal = 0
                TestsSuccessful = 0
                TestsFailed = 0

                SwitchMs = 0
                SwitchWallMs = 0

                Verdict = 'FAIL'

                Tests = @()

                FatalError = $_.Exception.Message
            }
        )
    }
    finally {

        # ---------------------------------------------------------------------
        # GARANTIE : après chaque modèle, runtime vide.
        # ---------------------------------------------------------------------

        $active = @(Get-RunningModelNames)

        if ($active.Count -gt 1) {

            Write-Forensic `
                -Message (
                    'VIOLATION SINGLE-MODEL après qualification.'
                ) `
                -Level FAIL

            throw 'MULTIPLE_MODELS_AFTER_TEST'
        }

        if ($active.Count -eq 1) {

            $released = Unload-OllamaModel `
                -Model $active[0]

            if (-not $released) {

                Write-Forensic `
                    -Message (
                        "Impossible de libérer $($active[0]) " +
                        'après qualification.'
                    ) `
                    -Level FAIL

                throw 'POST_MODEL_UNLOAD_FAILURE'
            }
        }

        if (-not (Wait-RuntimeEmpty)) {

            throw 'POST_MODEL_RUNTIME_NOT_EMPTY'
        }

        Write-Forensic `
            -Message (
                "Runtime propre après modèle $($model.Name)."
            ) `
            -Level PASS
    }
}

# =============================================================================
# [14/18] RANKING
# =============================================================================

Write-Section '[6/18] FINAL RANKING'

$ranking = @(
    $profiles |
        Where-Object {
            $_.Verdict -ne 'SKIP-EMBEDDING'
        } |
        Sort-Object `
            -Property OverallScore `
            -Descending
)

$rank = 0

foreach ($profile in $ranking) {

    $rank++

    Write-Host ''
    Write-Host (
        "#{0}  {1}" -f
        $rank,
        $profile.Model
    ) -ForegroundColor White

    Write-Host (
        "     OVERALL       : {0}/100" -f
        $profile.OverallScore
    )

    Write-Host (
        "     CAPABILITY    : {0}/100" -f
        $profile.CapabilityScore
    )

    Write-Host (
        "     RELIABILITY   : {0}/100" -f
        $profile.ReliabilityScore
    )

    Write-Host (
        "     PERFORMANCE   : {0}/100" -f
        $profile.PerformanceScore
    )

    Write-Host (
        "     INSTRUCTION   : {0}/100" -f
        $profile.InstructionScore
    )

    Write-Host (
        "     REASONING     : {0}/100" -f
        $profile.ReasoningScore
    )

    Write-Host (
        "     CODE          : {0}/100" -f
        $profile.CodeScore
    )

    Write-Host (
        "     FRENCH        : {0}/100" -f
        $profile.FrenchScore
    )

    Write-Host (
        "     STRUCTURED    : {0}/100" -f
        $profile.StructuredScore
    )

    Write-Host (
        "     ROBUSTNESS    : {0}/100" -f
        $profile.RobustnessScore
    )

    Write-Host (
        "     AVG TPS       : {0}" -f
        $profile.AvgTokensPerSec
    )

    Write-Host (
        "     FAILURE       : {0}%" -f
        $profile.FailureRate
    )

    Write-Host (
        "     VERDICT       : {0}" -f
        $profile.Verdict
    )
}

# =============================================================================
# [15/18] EMBEDDING INVENTORY
# =============================================================================

Write-Section '[7/18] EMBEDDING MODELS — INVENTORY ONLY'

$embeddingProfiles = @(
    $profiles |
        Where-Object {
            $_.Verdict -eq 'SKIP-EMBEDDING'
        }
)

foreach ($embedding in $embeddingProfiles) {

    Write-Host (
        "  SKIP | {0} | {1} GB | {2}" -f
        $embedding.Model,
        $embedding.SizeGB,
        $embedding.Family
    ) -ForegroundColor Yellow
}

# =============================================================================
# [16/18] EXPORT JSON
# =============================================================================

Write-Section '[8/18] JSON EXPORT'

$best = $ranking |
    Select-Object -First 1

$export = [PSCustomObject]@{

    Schema = 'EZZIO-MODEL-QUALIFICATION-4.3.1'

    RunId = $RunId

    Timestamp = (
        Get-Date
    ).ToString('o')

    Environment = [PSCustomObject]@{

        CPU = $CpuName
        Cores = $CpuCores
        Threads = $CpuThreads

        RAM_GB = $TotalRamGB
        Available_RAM_GB = $AvailableRamGB

        GPU_Mode = 'DISABLED'

        OllamaHost = $OllamaHost
    }

    Configuration = [PSCustomObject]@{

        SingleModelOnly = $true

        WarmupRuns = $WarmupRuns

        StabilityRuns = $StabilityRuns

        MaxModels = $MaxModels

        KeepAlive = $KeepAlive

        ReferenceTPS = $ReferenceTPS

        Thresholds = $Thresholds
    }

    ModelsDetected = $models.Count

    ModelsQualified = $ranking.Count

    ModelsSkippedEmbedding = $embeddingProfiles.Count

    BestModel = if ($null -ne $best) {
        $best.Model
    }
    else {
        $null
    }

    Ranking = @(
        for (
            $i = 0;
            $i -lt $ranking.Count;
            $i++
        ) {

            [PSCustomObject]@{

                Rank = $i + 1

                Model = $ranking[$i].Model

                Overall = $ranking[$i].OverallScore

                Capability = $ranking[$i].CapabilityScore

                Reliability = $ranking[$i].ReliabilityScore

                Performance = $ranking[$i].PerformanceScore

                Reasoning = $ranking[$i].ReasoningScore

                Code = $ranking[$i].CodeScore

                French = $ranking[$i].FrenchScore

                Verdict = $ranking[$i].Verdict
            }
        }
    )

    Profiles = @($profiles)
}

$export |
    ConvertTo-Json -Depth 20 |
    Set-Content `
        -LiteralPath $JsonPath `
        -Encoding UTF8

Write-Forensic `
    -Message (
        "JSON exporté : $JsonPath"
    ) `
    -Level PASS

# =============================================================================
# [17/18] CSV + SUMMARY
# =============================================================================

Write-Section '[9/18] CSV EXPORT'

$profiles |
    Select-Object `
        RunId,
        Version,
        Model,
        ParameterSize,
        Quantization,
        Family,
        SizeGB,
        IsEmbedding,
        OverallScore,
        CapabilityScore,
        ReliabilityScore,
        PerformanceScore,
        InstructionScore,
        ReasoningScore,
        CodeScore,
        FrenchScore,
        StructuredScore,
        GeneralScore,
        RobustnessScore,
        StabilityScore,
        AvgLatencyMs,
        AvgTokensPerSec,
        FailureRate,
        TestsTotal,
        TestsSuccessful,
        TestsFailed,
        SwitchMs,
        SwitchWallMs,
        Verdict |
    Export-Csv `
        -LiteralPath $CsvPath `
        -NoTypeInformation `
        -Encoding UTF8

Write-Forensic `
    -Message (
        "CSV exporté : $CsvPath"
    ) `
    -Level PASS

# -------------------------------------------------------------------------
# SUMMARY
# -------------------------------------------------------------------------

Write-Section '[10/18] SUMMARY'

if ($null -eq $best) {

    $bestName = 'NONE'
    $bestOverall = 0
    $bestCapability = 0
    $bestReliability = 0
    $bestPerformance = 0
    $bestReasoning = 0
    $bestCode = 0
    $bestFrench = 0
    $bestTPS = 0
    $bestFailure = 100
    $bestVerdict = 'NO-GENERATIVE-MODEL'
}
else {

    $bestName = $best.Model
    $bestOverall = $best.OverallScore
    $bestCapability = $best.CapabilityScore
    $bestReliability = $best.ReliabilityScore
    $bestPerformance = $best.PerformanceScore
    $bestReasoning = $best.ReasoningScore
    $bestCode = $best.CodeScore
    $bestFrench = $best.FrenchScore
    $bestTPS = $best.AvgTokensPerSec
    $bestFailure = $best.FailureRate
    $bestVerdict = $best.Verdict
}

$qualifiedCount = @(
    $profiles |
        Where-Object {
            $_.Verdict -eq 'QUALIFIED'
        }
).Count

$partialCount = @(
    $profiles |
        Where-Object {
            $_.Verdict -eq 'PARTIAL'
        }
).Count

$failedCount = @(
    $profiles |
        Where-Object {
            $_.Verdict -eq 'FAIL'
        }
).Count

$summary = @"

===============================================================================
E-ZZIO — MODEL QUALIFICATION GATE v$Version
===============================================================================

RUN ID
------
$RunId

ENVIRONMENT
-----------
CPU              : $CpuName
CORES            : $CpuCores
THREADS          : $CpuThreads
TOTAL RAM        : $TotalRamGB GB
AVAILABLE RAM    : $AvailableRamGB GB
GPU MODE         : DISABLED
OLLAMA HOST      : $OllamaHost

RUNTIME GUARANTEE
-----------------
SINGLE MODEL ONLY : ENABLED
PREVIOUS RELEASE  : REQUIRED
POST-SWITCH CHECK : REQUIRED
FINAL CLEANUP     : REQUIRED
FINAL ACTIVE      : 0

MODEL INVENTORY
---------------
DETECTED          : $($models.Count)
GENERATIVE        : $($ranking.Count)
EMBEDDING SKIPPED : $($embeddingProfiles.Count)

RESULT COUNTS
-------------
QUALIFIED         : $qualifiedCount
PARTIAL           : $partialCount
FAIL              : $failedCount

BEST MODEL
----------
$bestName

OVERALL
-------
$bestOverall / 100

CAPABILITY
----------
$bestCapability / 100

RELIABILITY
-----------
$bestReliability / 100

PERFORMANCE
-----------
$bestPerformance / 100

REASONING
---------
$bestReasoning / 100

CODE
----
$bestCode / 100

FRENCH
------
$bestFrench / 100

AVERAGE TOKENS/SECOND
---------------------
$bestTPS

FAILURE RATE
------------
$bestFailure %

VERDICT
-------
$bestVerdict

===============================================================================
INTERPRETATION
===============================================================================

CAPABILITY
----------
Mesure la qualité des réponses sur raisonnement, code, instructions,
français, JSON, robustesse et tâches générales.

RELIABILITY
-----------
Mesure la capacité à produire des réponses valides de manière répétable.

PERFORMANCE
-----------
Mesure la vitesse de génération. Elle ne constitue PAS une mesure
directe de l'intelligence du modèle.

IMPORTANT
---------
Un modèle plus lent peut être beaucoup plus capable.
Un modèle plus rapide peut être moins bon sur les tâches complexes.

Le Gate cherche donc à séparer :
    CAPACITE
    FIABILITE
    VITESSE

Les modèles d'embeddings ne sont pas classés dans la compétition
conversationnelle afin de ne pas produire un classement artificiel.

===============================================================================
"@

Set-Content `
    -LiteralPath $SummaryPath `
    -Value $summary `
    -Encoding UTF8

Write-Forensic `
    -Message (
        "Summary exporté : $SummaryPath"
    ) `
    -Level PASS

# =============================================================================
# [18/18] FINAL CLEANUP + FAIL-CLOSED
# =============================================================================

Write-Section '[FINAL] RUNTIME CLEANUP'

$finalRunning = @(Get-RunningModelNames)

if ($finalRunning.Count -gt 1) {

    Write-Forensic `
        -Message (
            'FAIL-CLOSED FINAL : plusieurs modèles encore actifs : ' +
            ($finalRunning -join ', ')
        ) `
        -Level FAIL

    throw 'FINAL_MULTIPLE_MODELS'
}

if ($finalRunning.Count -eq 1) {

    Write-Forensic `
        -Message (
            "Libération finale : $($finalRunning[0])"
        ) `
        -Level SWITCH

    $released = Unload-OllamaModel `
        -Model $finalRunning[0]

    if (-not $released) {

        Write-Forensic `
            -Message (
                'Impossible de confirmer la libération finale.'
            ) `
            -Level FAIL

        throw 'FINAL_UNLOAD_FAILED'
    }
}

$finalCheck = @(Get-RunningModelNames)

if ($finalCheck.Count -ne 0) {

    Write-Forensic `
        -Message (
            'FAIL-CLOSED : le runtime Ollama n''est pas vide.'
        ) `
        -Level FAIL

    throw 'FINAL_RUNTIME_NOT_EMPTY'
}

Write-Forensic `
    -Message (
        'Runtime Ollama propre : 0 modèle actif.'
    ) `
    -Level PASS

# =============================================================================
# FINAL CONSOLE
# =============================================================================

Write-Host ''
Write-Host ('=' * 82)
Write-Host (
    "E-ZZIO — MODEL QUALIFICATION GATE v$Version — FINISHED"
)
Write-Host ('=' * 82)

Write-Host ''
Write-Host "MODELS DETECTED       : $($models.Count)"
Write-Host "GENERATIVE TESTED     : $($ranking.Count)"
Write-Host "EMBEDDING SKIPPED     : $($embeddingProfiles.Count)"

Write-Host ''
Write-Host (
    "QUALIFIED             : $qualifiedCount"
) -ForegroundColor Green

Write-Host (
    "PARTIAL               : $partialCount"
) -ForegroundColor Yellow

Write-Host (
    "FAIL                  : $failedCount"
) -ForegroundColor Red

Write-Host ''
Write-Host 'SINGLE MODEL          : ENFORCED'
Write-Host 'CPU ONLY              : ENABLED'
Write-Host 'GPU                   : DISABLED'
Write-Host 'FINAL ACTIVE MODELS   : 0'

if ($null -ne $best) {

    Write-Host ''
    Write-Host (
        "BEST MODEL            : {0}" -f
        $best.Model
    ) -ForegroundColor Cyan

    Write-Host (
        "BEST OVERALL          : {0}/100" -f
        $best.OverallScore
    ) -ForegroundColor Cyan

    Write-Host (
        "BEST CAPABILITY       : {0}/100" -f
        $best.CapabilityScore
    ) -ForegroundColor Cyan

    Write-Host (
        "BEST REASONING        : {0}/100" -f
        $best.ReasoningScore
    ) -ForegroundColor Cyan

    Write-Host (
        "BEST CODE             : {0}/100" -f
        $best.CodeScore
    ) -ForegroundColor Cyan

    Write-Host (
        "BEST PERFORMANCE      : {0}/100" -f
        $best.PerformanceScore
    ) -ForegroundColor Cyan
}

Write-Host ''
Write-Host "JSON                  : $JsonPath"
Write-Host "CSV                   : $CsvPath"
Write-Host "SUMMARY               : $SummaryPath"
Write-Host "FORENSIC LOG          : $LogPath"

Write-Host ''
Write-Host ('=' * 82)
Write-Host 'EXECUTION TERMINEE — RUNTIME SINGLE-MODEL CLEAN'
Write-Host ('=' * 82)