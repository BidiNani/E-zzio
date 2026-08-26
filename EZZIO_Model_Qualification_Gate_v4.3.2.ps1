#requires -Version 7.4
# =============================================================================
# E-ZZIO — MODEL QUALIFICATION GATE
# Version : 4.3.2
# Mode    : CPU-ONLY / SINGLE-MODEL-SWITCH / FORENSIC / POTENTIAL-PROFILING
# =============================================================================
#
# OBJECTIF
# --------
# Mesurer le potentiel relatif réel des modèles Ollama installés localement.
#
# GARANTIES
# ---------
# 1. UN SEUL MODELE ACTIF A LA FOIS.
# 2. Nettoyage runtime avant chaque switch.
# 3. keep_alive = 0 pour libération.
# 4. Vérification /api/ps après chaque transition.
# 5. Aucun accès direct à une propriété Ollama non garantie.
# 6. Une réponse vide est un ECHEC DE TEST, pas un crash du Gate.
# 7. Une erreur API est distinguée d'une faiblesse du modèle.
# 8. Performance et capacité sont séparées.
# 9. Les modèles ne sont jamais supprimés.
# 10. Fail-closed sur violation du contrat SINGLE-MODEL.
#
# MACHINE CIBLE
# -------------
# AMD Ryzen 9 5900X
# 12 cores / 24 threads
# 32 GB RAM
# CPU ONLY
#
# SORTIES
# --------
# .\audit\model_gate_v4.3.2\
#
#   qualification_<RunId>.json
#   qualification_<RunId>.csv
#   forensic_<RunId>.log
#   summary_<RunId>.txt
#
# =============================================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# =============================================================================
# [0/18] CONFIGURATION
# =============================================================================

$Version = '4.3.2'

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

$AuditRoot = Join-Path `
    $Root `
    'audit\model_gate_v4.3.2'

New-Item `
    -ItemType Directory `
    -Path $AuditRoot `
    -Force |
    Out-Null

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
# CPU
# -------------------------------------------------------------------------

$CpuThreadsRequested = 12

$CpuName = 'UNKNOWN'
$CpuCores = 0
$CpuThreadsDetected = [Environment]::ProcessorCount
$TotalRamGB = 0
$AvailableRamGB = 0

try {

    $cpu = Get-CimInstance `
        Win32_Processor |
        Select-Object -First 1

    if ($null -ne $cpu) {

        $CpuName = [string]$cpu.Name
        $CpuCores = [int]$cpu.NumberOfCores
        $CpuThreadsDetected = [int]$cpu.NumberOfLogicalProcessors
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

$MaxModels = 0

$DefaultTimeoutSec = 300
$SwitchTimeoutSec = 300
$UnloadTimeoutSec = 60

# -------------------------------------------------------------------------
# SCORING
# -------------------------------------------------------------------------

$Thresholds = [ordered]@{

    MinOverallScore       = 60
    MinReliabilityScore   = 70
    MinInstructionScore   = 60
    MinReasoningScore     = 50
    MinCodeScore          = 50
    MinFrenchScore        = 50
    MinStructuredScore    = 50
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
# [2/18] SAFE PROPERTY ACCESS
# =============================================================================
#
# IMPORTANT :
# Ollama /api/ps ne garantit pas que toutes les propriétés existent.
#
# On NE fait donc jamais :
#
#   $model.processor
#
# sans vérification.
#
# =============================================================================

function Get-SafeProperty {

    param(

        [AllowNull()]
        [object]$Object,

        [Parameter(Mandatory)]
        [string]$Name,

        [object]$Default = $null
    )

    if ($null -eq $Object) {
        return $Default
    }

    $property = $Object.PSObject.Properties[$Name]

    if ($null -eq $property) {
        return $Default
    }

    if ($null -eq $property.Value) {
        return $Default
    }

    return $property.Value
}

function Get-SafeString {

    param(

        [AllowNull()]
        [object]$Object,

        [Parameter(Mandatory)]
        [string]$Name,

        [string]$Default = ''
    )

    $value = Get-SafeProperty `
        -Object $Object `
        -Name $Name `
        -Default $Default

    if ($null -eq $value) {
        return $Default
    }

    return [string]$value
}

# =============================================================================
# [3/18] OLLAMA API
# =============================================================================

function Test-OllamaAvailable {

    try {

        Invoke-RestMethod `
            -Uri "$OllamaHost/api/tags" `
            -Method Get `
            -TimeoutSec 10 |
            Out-Null

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
            -TimeoutSec 20

        $modelsProperty = $response.PSObject.Properties['models']

        if ($null -eq $modelsProperty) {
            return @()
        }

        if ($null -eq $modelsProperty.Value) {
            return @()
        }

        return @(
            $modelsProperty.Value |
                ForEach-Object {

                    $details = Get-SafeProperty `
                        -Object $_ `
                        -Name 'details' `
                        -Default $null

                    $size = Get-SafeProperty `
                        -Object $_ `
                        -Name 'size' `
                        -Default 0

                    [PSCustomObject]@{

                        Name = Get-SafeString `
                            -Object $_ `
                            -Name 'name'

                        SizeBytes = [int64]$size

                        SizeGB = [math]::Round(
                            [double]$size / 1GB,
                            2
                        )

                        Parameter = Get-SafeString `
                            -Object $details `
                            -Name 'parameter_size' `
                            -Default 'unknown'

                        Quant = Get-SafeString `
                            -Object $details `
                            -Name 'quantization_level' `
                            -Default 'unknown'

                        Family = Get-SafeString `
                            -Object $details `
                            -Name 'family' `
                            -Default 'unknown'
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
            -TimeoutSec 15

        $modelsProperty = $response.PSObject.Properties['models']

        if ($null -eq $modelsProperty) {
            return @()
        }

        if ($null -eq $modelsProperty.Value) {
            return @()
        }

        return @($modelsProperty.Value)
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

    $names = New-Object System.Collections.Generic.List[string]

    foreach ($item in $running) {

        $name = Get-SafeString `
            -Object $item `
            -Name 'name'

        if ([string]::IsNullOrWhiteSpace($name)) {

            $name = Get-SafeString `
                -Object $item `
                -Name 'model'
        }

        if (-not [string]::IsNullOrWhiteSpace($name)) {
            $names.Add($name)
        }
    }

    return @($names)
}

# =============================================================================
# [4/18] RUNTIME FORENSIC STATE
# =============================================================================

function Get-RuntimeState {

    $running = @(Get-OllamaRunningModels)

    $entries = New-Object System.Collections.Generic.List[object]

    foreach ($item in $running) {

        $name = Get-SafeString `
            -Object $item `
            -Name 'name' `
            -Default ''

        if ([string]::IsNullOrWhiteSpace($name)) {

            $name = Get-SafeString `
                -Object $item `
                -Name 'model' `
                -Default ''
        }

        # processor est OPTIONNEL.
        $processor = Get-SafeString `
            -Object $item `
            -Name 'processor' `
            -Default 'unknown'

        $size = Get-SafeProperty `
            -Object $item `
            -Name 'size' `
            -Default 0

        $context = Get-SafeProperty `
            -Object $item `
            -Name 'context_length' `
            -Default 0

        $entries.Add(
            [PSCustomObject]@{

                Name = $name
                Processor = $processor
                SizeBytes = [int64]$size
                SizeGB = if ([double]$size -gt 0) {
                    [math]::Round(
                        [double]$size / 1GB,
                        2
                    )
                }
                else {
                    0
                }
                ContextLength = [int]$context
            }
        )
    }

    return @($entries)
}

function Assert-RuntimeCardinality {

    param(
        [int]$ExpectedMaximum = 1
    )

    $running = @(Get-RunningModelNames)

    if ($running.Count -gt $ExpectedMaximum) {

        Write-Forensic `
            -Message (
                'VIOLATION SINGLE-MODEL : ' +
                "$($running.Count) modèles actifs : " +
                ($running -join ', ')
            ) `
            -Level FAIL

        throw 'SINGLE_MODEL_VIOLATION'
    }

    return $running
}

function Wait-RuntimeEmpty {

    param(
        [int]$Attempts = 8,
        [int]$DelayMs = 250
    )

    for ($i = 1; $i -le $Attempts; $i++) {

        $running = @(Get-RunningModelNames)

        if ($running.Count -eq 0) {

            Write-Forensic `
                -Message (
                    "Runtime EMPTY confirmé à la tentative " +
                    "$i/$Attempts."
                ) `
                -Level PASS

            return $true
        }

        Start-Sleep -Milliseconds $DelayMs
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

# =============================================================================
# [5/18] UNLOAD
# =============================================================================

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
        options = @{
            num_thread = $CpuThreadsRequested
        }
    } |
        ConvertTo-Json -Depth 8

    try {

        Invoke-RestMethod `
            -Uri "$OllamaHost/api/generate" `
            -Method Post `
            -ContentType 'application/json' `
            -Body $payload `
            -TimeoutSec $UnloadTimeoutSec |
            Out-Null
    }
    catch {

        Write-Forensic `
            -Message (
                "Libération API signalée en erreur pour $Model : " +
                $_.Exception.Message
            ) `
            -Level WARN
    }

    if (-not (Wait-RuntimeEmpty)) {

        return $false
    }

    Write-Forensic `
        -Message "Modèle $Model libéré via API." `
        -Level PASS

    return $true
}

function Clear-OllamaRuntime {

    Write-Forensic `
        -Message 'NETTOYAGE GLOBAL DU RUNTIME OLLAMA' `
        -Level SWITCH

    $running = @(Get-RunningModelNames)

    if ($running.Count -eq 0) {

        Write-Forensic `
            -Message 'Runtime déjà EMPTY.' `
            -Level PASS

        return $true
    }

    if ($running.Count -gt 1) {

        Write-Forensic `
            -Message (
                'Plusieurs modèles actifs détectés avant nettoyage : ' +
                ($running -join ', ')
            ) `
            -Level FAIL

        # On tente néanmoins le nettoyage explicite de chaque modèle.
        foreach ($model in $running) {

            $null = Unload-OllamaModel -Model $model
        }
    }
    else {

        $null = Unload-OllamaModel -Model $running[0]
    }

    if (-not (Wait-RuntimeEmpty)) {

        throw 'RUNTIME_CLEANUP_FAILED'
    }

    return $true
}

# =============================================================================
# [6/18] RESPONSE EXTRACTION
# =============================================================================
#
# Ollama peut exposer :
#
#   response
#
# ou, selon endpoint / format :
#
#   message.content
#
# On capture également le RAW response pour le forensic.
#
# =============================================================================

function Get-OllamaResponseText {

    param(
        [AllowNull()]
        [object]$Response
    )

    if ($null -eq $Response) {
        return ''
    }

    $direct = Get-SafeString `
        -Object $Response `
        -Name 'response' `
        -Default ''

    if (-not [string]::IsNullOrWhiteSpace($direct)) {
        return $direct
    }

    $message = Get-SafeProperty `
        -Object $Response `
        -Name 'message' `
        -Default $null

    if ($null -ne $message) {

        $content = Get-SafeString `
            -Object $message `
            -Name 'content' `
            -Default ''

        if (-not [string]::IsNullOrWhiteSpace($content)) {
            return $content
        }
    }

    return ''
}

function Get-OllamaMetricInt {

    param(

        [AllowNull()]
        [object]$Response,

        [Parameter(Mandatory)]
        [string]$Name
    )

    $value = Get-SafeProperty `
        -Object $Response `
        -Name $Name `
        -Default 0

    try {
        return [int]$value
    }
    catch {
        return 0
    }
}

# =============================================================================
# [7/18] MODEL SWITCH
# =============================================================================

function Switch-OllamaModel {

    param(

        [Parameter(Mandatory)]
        [string]$Model,

        [int]$Index = 0,

        [int]$Total = 0
    )

    Write-Forensic `
        -Message (
            "========== SWITCH -> $Model =========="
        ) `
        -Level SWITCH

    # ---------------------------------------------------------------------
    # ZERO MODEL BEFORE LOAD
    # ---------------------------------------------------------------------

    Clear-OllamaRuntime

    $pre = @(Get-RunningModelNames)

    if ($pre.Count -ne 0) {

        throw 'PRE_SWITCH_RUNTIME_NOT_EMPTY'
    }

    # ---------------------------------------------------------------------
    # LOAD PROBE
    # ---------------------------------------------------------------------

    $payload = @{
        model = $Model

        prompt = 'E-ZZIO QUALIFICATION SWITCH PROBE. Réponds READY.'

        stream = $false

        keep_alive = '5m'

        options = @{
            temperature = 0
            num_predict = 8
            num_thread = $CpuThreadsRequested
        }
    } |
        ConvertTo-Json -Depth 10

    $wallStart = Get-Date

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
        (Get-Date) - $wallStart
    ).TotalMilliseconds

    # ---------------------------------------------------------------------
    # POST SWITCH
    # ---------------------------------------------------------------------

    $post = @(Get-RuntimeState)

    if ($post.Count -ne 1) {

        Write-Forensic `
            -Message (
                "Post-switch invalide : $($post.Count) modèle(s) actif(s)."
            ) `
            -Level FAIL

        throw 'POST_SWITCH_CARDINALITY_FAILURE'
    }

    $activeName = $post[0].Name

    if ($activeName -ne $Model) {

        Write-Forensic `
            -Message (
                "Mauvais modèle actif : $activeName ; attendu : $Model"
            ) `
            -Level FAIL

        throw 'POST_SWITCH_WRONG_MODEL'
    }

    $loadMs = Get-OllamaMetricInt `
        -Response $response `
        -Name 'load_duration'

    # Ollama renvoie généralement des nanosecondes.
    $loadMs = [math]::Round(
        [double]$loadMs / 1000000,
        2
    )

    # processor est optionnel.
    $processor = $post[0].Processor

    Write-Forensic `
        -Message (
            "SWITCH OK | Model=$Model | " +
            "Load=$loadMs ms | " +
            "Wall=$([math]::Round($wallMs,3)) ms | " +
            "Processor=$processor | Active=1"
        ) `
        -Level PASS

    return [PSCustomObject]@{

        Model = $Model
        Index = $Index
        Total = $Total

        LoadMs = $loadMs
        WallMs = [math]::Round($wallMs, 3)

        Processor = $processor
        ActiveModels = 1
    }
}

# =============================================================================
# [8/18] RESPONSE SCORING
# =============================================================================

function Evaluate-Response {

    param(

        [Parameter(Mandatory)]
        [string]$Category,

        [Parameter(Mandatory)]
        [string]$TestId,

        [AllowEmptyString()]
        [string]$Prompt = '',

        [AllowEmptyString()]
        [string]$Response = ''
    )

    $text = ''

    if ($null -ne $Response) {
        $text = $Response.Trim()
    }

    $score = 0
    $hardPass = $false

    $reasons = New-Object System.Collections.Generic.List[string]

    # ---------------------------------------------------------------------
    # EMPTY
    # ---------------------------------------------------------------------

    if ([string]::IsNullOrWhiteSpace($text)) {

        return [PSCustomObject]@{

            TestId = $TestId
            Category = $Category

            Score = 0
            HardPass = $false

            ResponseChars = 0

            Reasons = @('EMPTY_RESPONSE')
        }
    }

    # ---------------------------------------------------------------------
    # GENERAL BASE
    # ---------------------------------------------------------------------

    $score += 20
    $reasons.Add('NON_EMPTY')

    # ---------------------------------------------------------------------
    # INSTRUCTION
    # ---------------------------------------------------------------------

    switch ($TestId) {

        'INS-01' {

            $lines = @(
                $text -split "`r?`n" |
                    Where-Object {
                        -not [string]::IsNullOrWhiteSpace($_)
                    }
            )

            if ($lines.Count -eq 3) {

                if (
                    $lines[0].Trim() -eq 'ALPHA' -and
                    $lines[1].Trim() -eq 'BETA' -and
                    $lines[2].Trim() -eq 'GAMMA'
                ) {

                    $score = 100
                    $hardPass = $true
                    $reasons.Add('EXACT_THREE_LINE_MATCH')
                }
                else {

                    $score += 20
                    $reasons.Add('THREE_LINES_BUT_CONTENT_MISMATCH')
                }
            }
            else {

                $score += 5
                $reasons.Add('LINE_COUNT_MISMATCH')
            }
        }

        'REASON-01' {

            if ($text -match '\b23\b') {

                $score += 45
                $reasons.Add('EXPECTED_RESULT_23')
            }

            if (
                $text -match '(?i)12' -and
                $text -match '(?i)6' -and
                $text -match '(?i)11'
            ) {

                $score += 15
                $reasons.Add('INTERMEDIATE_VALUES_PRESENT')
            }

            if (
                $text -match '(?i)donc|car|puisque|étape|calcul|d''abord|ensuite'
            ) {

                $score += 15
                $reasons.Add('REASONING_EVIDENCE')
            }

            if ($text -match '\b23\b') {
                $hardPass = $true
            }
        }

        'REASON-02' {

            if ($text -match '\b80\b') {

                $score += 45
                $reasons.Add('EXPECTED_RESULT_80')
            }

            if (
                $text -match '(?i)100' -and
                $text -match '(?i)70' -and
                $text -match '(?i)80'
            ) {

                $score += 20
                $reasons.Add('INTERMEDIATE_VALUES_PRESENT')
            }

            if (
                $text -match '(?i)donc|car|puisque|étape|calcul|d''abord|ensuite'
            ) {

                $score += 15
                $reasons.Add('REASONING_EVIDENCE')
            }

            if ($text -match '\b80\b') {
                $hardPass = $true
            }
        }

        'CODE-01' {

            if ($text -match '(?i)def\s+safe_divide') {

                $score += 35
                $reasons.Add('FUNCTION_NAME')
            }

            if ($text -match '(?i)return\s+a\s*/\s*b') {

                $score += 25
                $reasons.Add('DIVISION')
            }

            if ($text -match '(?i)b\s*==\s*0') {

                $score += 20
                $reasons.Add('ZERO_GUARD')
            }

            if ($text -match '(?i)return\s+None') {

                $score += 10
                $reasons.Add('NONE_RETURN')
            }

            if (
                $text -match '(?i)def\s+safe_divide' -and
                $text -match '(?i)b\s*==\s*0' -and
                $text -match '(?i)return\s+None'
            ) {

                $hardPass = $true
            }
        }

        'CODE-02' {

            if ($text -match '(?i)function\s+Get-SafeValue') {

                $score += 35
                $reasons.Add('FUNCTION_NAME')
            }

            if ($text -match '\[object\]\$Value') {

                $score += 20
                $reasons.Add('OBJECT_PARAMETER')
            }

            if ($text -match '(?i)\$null') {

                $score += 15
                $reasons.Add('NULL_CHECK')
            }

            if ($text -match '(?i)return') {

                $score += 10
                $reasons.Add('RETURN')
            }

            if (
                $text -match '(?i)Get-SafeValue' -and
                $text -match '\$null'
            ) {

                $hardPass = $true
            }
        }

        'JSON-01' {

            try {

                $json = $text | ConvertFrom-Json -ErrorAction Stop

                $status = Get-SafeString `
                    -Object $json `
                    -Name 'status'

                $score += 50
                $reasons.Add('VALID_JSON')

                if ($status -eq 'PASS') {

                    $score += 20
                    $reasons.Add('STATUS_PASS')
                }

                $jsonScore = Get-SafeProperty `
                    -Object $json `
                    -Name 'score' `
                    -Default -1

                if ([int]$jsonScore -eq 100) {

                    $score += 15
                    $reasons.Add('SCORE_100')
                }

                $mode = Get-SafeString `
                    -Object $json `
                    -Name 'mode'

                if ($mode -eq 'CPU') {

                    $score += 15
                    $reasons.Add('CPU_MODE')
                }

                if (
                    $status -eq 'PASS' -and
                    [int]$jsonScore -eq 100 -and
                    $mode -eq 'CPU'
                ) {

                    $hardPass = $true
                }
            }
            catch {

                $reasons.Add('INVALID_JSON')
            }
        }

        'FR-01' {

            if (
                $text -match '(?i)\blatence\b'
            ) {

                $score += 20
                $reasons.Add('LATENCY')
            }

            if (
                $text -match '(?i)\bdébit\b|\bthroughput\b'
            ) {

                $score += 20
                $reasons.Add('THROUGHPUT')
            }

            if (
                $text -match '(?i)\bfiabilité\b'
            ) {

                $score += 20
                $reasons.Add('RELIABILITY')
            }

            if (
                $text -match '(?i)\bmodèle\b|\bmodèles\b'
            ) {

                $score += 10
                $reasons.Add('AI_MODEL_CONTEXT')
            }

            if ($text.Length -ge 150) {

                $score += 15
                $reasons.Add('ADEQUATE_LENGTH')
            }

            if (
                $text -match '(?i)\blatence\b' -and
                $text -match '(?i)\bdébit\b' -and
                $text -match '(?i)\bfiabilité\b'
            ) {

                $hardPass = $true
            }
        }

        'ROB-01' {

            if (
                $text -match '(?i)fausse|faux|non|pas nécessairement|incorrecte'
            ) {

                $score += 40
                $reasons.Add('CLAIM_REJECTED')
            }

            if (
                $text -match '(?i)rapide|vitesse|latence|performance'
            ) {

                $score += 20
                $reasons.Add('PERFORMANCE_DISTINCTION')
            }

            if (
                $text -match '(?i)capacité|raisonnement|qualité|intelligence'
            ) {

                $score += 20
                $reasons.Add('CAPABILITY_DISTINCTION')
            }

            if (
                $text -match '(?i)nécessairement'
            ) {

                $score += 10
                $reasons.Add('NUANCE')
            }

            if (
                $text -match '(?i)fausse|faux|non|pas nécessairement'
            ) {

                $hardPass = $true
            }
        }

        'CTX-01' {

            if ($text -match '\b91\b') {

                $score = 100
                $hardPass = $true
                $reasons.Add('EXPECTED_MEMORY_RESULT')
            }
        }

        default {

            if ($text.Length -ge 80) {

                $score += 20
                $reasons.Add('ADEQUATE_LENGTH')
            }

            if ($text.Length -ge 250) {

                $score += 10
                $reasons.Add('DETAILED_RESPONSE')
            }
        }
    }

    if ($score -gt 100) {
        $score = 100
    }

    return [PSCustomObject]@{

        TestId = $TestId
        Category = $Category

        Score = [int]$score
        HardPass = $hardPass

        ResponseChars = $text.Length

        Reasons = @($reasons)
    }
}

# =============================================================================
# [9/18] TEST EXECUTION
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
        [AllowEmptyString()]
        [string]$Prompt,

        [int]$MaxTokens = 256
    )

    Write-Forensic `
        -Message "TEST $TestId | $Category" `
        -Level TEST

    # ---------------------------------------------------------------------
    # ACTIVE MODEL CHECK
    # ---------------------------------------------------------------------

    $active = @(Get-RunningModelNames)

    if ($active.Count -ne 1) {

        Write-Forensic `
            -Message (
                "Contrat runtime invalide avant $TestId : " +
                "$($active.Count) modèle(s)."
            ) `
            -Level FAIL

        throw 'TEST_RUNTIME_CARDINALITY_FAILURE'
    }

    if ($active[0] -ne $Model) {

        Write-Forensic `
            -Message (
                "Mauvais modèle actif : $($active[0]) ; " +
                "attendu : $Model"
            ) `
            -Level FAIL

        throw 'ACTIVE_MODEL_MISMATCH'
    }

    Write-Forensic `
        -Message "Modèle actif confirmé : $Model" `
        -Level INFO

    # ---------------------------------------------------------------------
    # REQUEST
    # ---------------------------------------------------------------------

    $payload = @{

        model = $Model

        prompt = $Prompt

        stream = $false

        keep_alive = '5m'

        options = @{

            temperature = 0

            num_predict = $MaxTokens

            num_thread = $CpuThreadsRequested
        }

    } |
        ConvertTo-Json -Depth 10

    $wallStart = Get-Date

    try {

        $response = Invoke-RestMethod `
            -Uri "$OllamaHost/api/generate" `
            -Method Post `
            -ContentType 'application/json' `
            -Body $payload `
            -TimeoutSec $DefaultTimeoutSec
    }
    catch {

        Write-Forensic `
            -Message (
                "TEST $TestId API ERROR : " +
                $_.Exception.Message
            ) `
            -Level FAIL

        return [PSCustomObject]@{

            Model = $Model
            TestId = $TestId
            Category = $Category

            Success = $false
            ApiSuccess = $false
            ResponseEmpty = $false

            Score = 0
            HardPass = $false

            WallMs = 0
            LoadMs = 0
            PromptMs = 0
            EvalMs = 0

            PromptTokens = 0
            GeneratedTokens = 0
            TokensPerSecond = 0

            ResponseChars = 0
            ResponsePreview = ''

            ErrorType = 'API_ERROR'
            Error = $_.Exception.Message

            Reasons = @('API_ERROR')
        }
    }

    $wallMs = (
        (Get-Date) - $wallStart
    ).TotalMilliseconds

    # ---------------------------------------------------------------------
    # TIMINGS
    # ---------------------------------------------------------------------

    $loadNs = Get-OllamaMetricInt `
        -Response $response `
        -Name 'load_duration'

    $promptNs = Get-OllamaMetricInt `
        -Response $response `
        -Name 'prompt_eval_duration'

    $evalNs = Get-OllamaMetricInt `
        -Response $response `
        -Name 'eval_duration'

    $loadMs = [math]::Round(
        [double]$loadNs / 1000000,
        3
    )

    $promptMs = [math]::Round(
        [double]$promptNs / 1000000,
        3
    )

    $evalMs = [math]::Round(
        [double]$evalNs / 1000000,
        3
    )

    $promptTokens = Get-OllamaMetricInt `
        -Response $response `
        -Name 'prompt_eval_count'

    $generatedTokens = Get-OllamaMetricInt `
        -Response $response `
        -Name 'eval_count'

    # ---------------------------------------------------------------------
    # RESPONSE
    # ---------------------------------------------------------------------

    $text = Get-OllamaResponseText `
        -Response $response

    $responseEmpty = [string]::IsNullOrWhiteSpace($text)

    # ---------------------------------------------------------------------
    # EVALUATION
    # ---------------------------------------------------------------------

    $evaluation = Evaluate-Response `
        -Category $Category `
        -TestId $TestId `
        -Prompt $Prompt `
        -Response $text

    $tps = 0

    if (
        $generatedTokens -gt 0 -and
        $evalNs -gt 0
    ) {

        $tps = [math]::Round(
            $generatedTokens /
            ([double]$evalNs / 1000000000),
            3
        )
    }

    # ---------------------------------------------------------------------
    # RESULT
    # ---------------------------------------------------------------------

    $success = (
        -not $responseEmpty
    )

    $errorType = $null
    $errorText = $null

    if ($responseEmpty) {

        $errorType = 'EMPTY_RESPONSE'

        $errorText = (
            'Ollama a terminé la requête sans texte exploitable.'
        )

        Write-Forensic `
            -Message (
                "TEST $TestId : réponse vide. " +
                'Echec enregistré sans crash du Gate.'
            ) `
            -Level WARN
    }

    $preview = ''

    if (-not $responseEmpty) {

        $preview = if ($text.Length -gt 300) {

            $text.Substring(0,300)
        }
        else {

            $text
        }
    }

    Write-Forensic `
        -Message (
            'RESULT ' +
            "$TestId | " +
            "Score=$($evaluation.Score) | " +
            "HardPass=$($evaluation.HardPass) | " +
            "Wall=$([math]::Round($wallMs,3))ms | " +
            "Load=$loadMs ms | " +
            "Prompt=$promptMs ms | " +
            "Eval=$evalMs ms | " +
            "Tokens=$generatedTokens | " +
            "TPS=$tps"
        ) `
        -Level METRIC

    return [PSCustomObject]@{

        Model = $Model
        TestId = $TestId
        Category = $Category

        Success = $success
        ApiSuccess = $true
        ResponseEmpty = $responseEmpty

        Score = $evaluation.Score
        HardPass = $evaluation.HardPass

        WallMs = [math]::Round(
            $wallMs,
            3
        )

        LoadMs = $loadMs
        PromptMs = $promptMs
        EvalMs = $evalMs

        PromptTokens = $promptTokens
        GeneratedTokens = $generatedTokens
        TokensPerSecond = $tps

        ResponseChars = $evaluation.ResponseChars
        ResponsePreview = $preview

        ErrorType = $errorType
        Error = $errorText

        Reasons = @(
            $evaluation.Reasons
        )
    }
}

# =============================================================================
# [10/18] TEST BATTERY
# =============================================================================

$Tests = @(

    [PSCustomObject]@{

        Id = 'GEN-01'
        Category = 'General'

        Prompt = @'
Réponds en français à cette question :
Pourquoi une architecture logicielle robuste doit-elle séparer
les politiques de décision, l'exécution et l'audit ?

Donne une réponse structurée, techniquement précise et concrète.
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
s'il n'est pas $null.

Sinon elle retourne une chaîne vide.

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

Donne un exemple concret pour chacun.
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

Puis réponds uniquement avec la valeur correspondant à EZZIO.
'@

        MaxTokens = 80
    }
)

# =============================================================================
# [11/18] CATEGORY AGGREGATION
# =============================================================================

function Get-CategoryScore {

    param(

        [array]$Results,

        [Parameter(Mandatory)]
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
            $items |
                Measure-Object -Property Score -Average
        ).Average,
        2
    )
}

function Get-HardPassRate {

    param(
        [array]$Results
    )

    if ($Results.Count -eq 0) {
        return 0
    }

    $passes = @(
        $Results |
            Where-Object {
                $_.HardPass -eq $true
            }
    ).Count

    return [math]::Round(
        ($passes / $Results.Count) * 100,
        2
    )
}

# =============================================================================
# [12/18] MODEL QUALIFICATION
# =============================================================================

function Test-Model {

    param(

        [Parameter(Mandatory)]
        [PSCustomObject]$Model,

        [int]$Index = 0,

        [int]$Total = 0
    )

    Write-Section "[MODEL] $($Model.Name)"

    Write-Forensic `
        -Message (
            "Début qualification : $($Model.Name)"
        ) `
        -Level INFO

    # ---------------------------------------------------------------------
    # SWITCH
    # ---------------------------------------------------------------------

    $switchResult = Switch-OllamaModel `
        -Model $Model.Name `
        -Index $Index `
        -Total $Total

    $results = New-Object System.Collections.Generic.List[object]

    # ---------------------------------------------------------------------
    # WARMUP
    # ---------------------------------------------------------------------

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

            keep_alive = '5m'

            options = @{

                temperature = 0

                num_predict = 16

                num_thread = $CpuThreadsRequested
            }

        } |
            ConvertTo-Json -Depth 8

        try {

            Invoke-RestMethod `
                -Uri "$OllamaHost/api/generate" `
                -Method Post `
                -ContentType 'application/json' `
                -Body $warmupPayload `
                -TimeoutSec 120 |
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

    # ---------------------------------------------------------------------
    # BATTERY
    # ---------------------------------------------------------------------

    foreach ($test in $Tests) {

        $result = Invoke-ModelTest `
            -Model $Model.Name `
            -TestId $test.Id `
            -Category $test.Category `
            -Prompt $test.Prompt `
            -MaxTokens $test.MaxTokens

        $results.Add($result)
    }

    # ---------------------------------------------------------------------
    # STABILITY
    # ---------------------------------------------------------------------

    Write-Forensic `
        -Message (
            "Tests de stabilité : $StabilityRuns exécutions."
        ) `
        -Level INFO

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
Réponds en une phrase concise :
quel est le rôle principal d'un journal forensic ?
'@ `
            -MaxTokens 100

        $results.Add($stable)
    }

    # ---------------------------------------------------------------------
    # AGGREGATION
    # ---------------------------------------------------------------------

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

    $apiFailures = @(
        $allResults |
            Where-Object {
                $_.ApiSuccess -ne $true
            }
    )

    $emptyResponses = @(
        $allResults |
            Where-Object {
                $_.ResponseEmpty -eq $true
            }
    )

    $avgScore = if ($allResults.Count -gt 0) {

        [math]::Round(
            (
                $allResults |
                    Measure-Object -Property Score -Average
            ).Average,
            2
        )
    }
    else {
        0
    }

    $avgTPS = if ($successful.Count -gt 0) {

        [math]::Round(
            (
                $successful |
                    Measure-Object `
                        -Property TokensPerSecond `
                        -Average
            ).Average,
            3
        )
    }
    else {
        0
    }

    $avgLatency = if ($successful.Count -gt 0) {

        [math]::Round(
            (
                $successful |
                    Measure-Object `
                        -Property WallMs `
                        -Average
            ).Average,
            2
        )
    }
    else {
        0
    }

    $failureRate = if ($allResults.Count -gt 0) {

        [math]::Round(
            ($failed.Count / $allResults.Count) * 100,
            2
        )
    }
    else {
        100
    }

    $hardPassRate = Get-HardPassRate `
        -Results $allResults

    # ---------------------------------------------------------------------
    # CATEGORIES
    # ---------------------------------------------------------------------

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

    # ---------------------------------------------------------------------
    # STABILITY
    # ---------------------------------------------------------------------

    $stabilityResults = @(
        $allResults |
            Where-Object {
                $_.TestId -like 'STAB-*'
            }
    )

    $stabilityScore = if ($stabilityResults.Count -gt 0) {

        [math]::Round(
            (
                $stabilityResults |
                    Measure-Object `
                        -Property Score `
                        -Average
            ).Average,
            2
        )
    }
    else {
        0
    }

    # ---------------------------------------------------------------------
    # CAPABILITY
    #
    # La capacité ne dépend PAS du TPS.
    # ---------------------------------------------------------------------

    $capabilityScore = [math]::Round(

        (
            ($instructionScore * 0.20) +
            ($reasoningScore * 0.25) +
            ($codeScore * 0.20) +
            ($frenchScore * 0.10) +
            ($structuredScore * 0.10) +
            ($generalScore * 0.15)
        ),

        2
    )

    # ---------------------------------------------------------------------
    # PERFORMANCE
    #
    # 40 TPS = 100.
    # Ce score ne prétend PAS mesurer l'intelligence.
    # ---------------------------------------------------------------------

    $performanceScore = [math]::Min(

        100,

        [math]::Round(
            ($avgTPS / 40) * 100,
            2
        )
    )

    # ---------------------------------------------------------------------
    # RELIABILITY
    # ---------------------------------------------------------------------

    $reliabilityScore = [math]::Round(

        (
            ($stabilityScore * 0.45) +
            ($hardPassRate * 0.30) +
            ((100 - $failureRate) * 0.25)
        ),

        2
    )

    # ---------------------------------------------------------------------
    # OVERALL
    # ---------------------------------------------------------------------

    $overall = [math]::Round(

        (
            ($capabilityScore * 0.60) +
            ($reliabilityScore * 0.25) +
            ($performanceScore * 0.15)
        ),

        2
    )

    # ---------------------------------------------------------------------
    # VERDICT
    # ---------------------------------------------------------------------

    $verdict = 'FAIL'

    if (
        $overall -ge $Thresholds.MinOverallScore -and
        $reliabilityScore -ge $Thresholds.MinReliabilityScore -and
        $instructionScore -ge $Thresholds.MinInstructionScore -and
        $reasoningScore -ge $Thresholds.MinReasoningScore -and
        $codeScore -ge $Thresholds.MinCodeScore -and
        $frenchScore -ge $Thresholds.MinFrenchScore -and
        $structuredScore -ge $Thresholds.MinStructuredScore -and
        $stabilityScore -ge $Thresholds.MinStabilityScore -and
        $failureRate -le $Thresholds.MaxFailureRatePercent
    ) {

        $verdict = 'QUALIFIED'
    }
    elseif ($overall -ge 50) {

        $verdict = 'PARTIAL'
    }

    # ---------------------------------------------------------------------
    # PROFILE
    # ---------------------------------------------------------------------

    $profile = [PSCustomObject]@{

        RunId = $RunId
        Version = $Version

        Model = $Model.Name

        ParameterSize = $Model.Parameter
        Quantization = $Model.Quant
        Family = $Model.Family
        SizeGB = $Model.SizeGB

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

        StabilityScore = $stabilityScore
        HardPassRate = $hardPassRate

        AvgLatencyMs = $avgLatency
        AvgTokensPerSec = $avgTPS

        FailureRate = $failureRate

        TestsTotal = $allResults.Count
        TestsSuccessful = $successful.Count
        TestsFailed = $failed.Count

        ApiFailures = $apiFailures.Count
        EmptyResponses = $emptyResponses.Count

        SwitchMs = $switchResult.LoadMs
        SwitchWallMs = $switchResult.WallMs
        Processor = $switchResult.Processor

        Verdict = $verdict

        Tests = $allResults
    }

    $level = if ($verdict -eq 'QUALIFIED') {

        'PASS'
    }
    elseif ($verdict -eq 'PARTIAL') {

        'WARN'
    }
    else {

        'FAIL'
    }

    Write-Forensic `
        -Message (
            "PROFILE $($Model.Name) | " +
            "CAP=$capabilityScore | " +
            "REL=$reliabilityScore | " +
            "PERF=$performanceScore | " +
            "OVERALL=$overall | " +
            "HARDPASS=$hardPassRate% | " +
            "FAIL=$failureRate% | " +
            "VERDICT=$verdict"
        ) `
        -Level $level

    return $profile
}

# =============================================================================
# [13/18] ENVIRONMENT
# =============================================================================

Write-Section "[0/18] E-ZZIO MODEL QUALIFICATION GATE v$Version"

Write-Host ''
Write-Host "CPU NAME              : $CpuName"
Write-Host "CPU CORES             : $CpuCores"
Write-Host "CPU THREADS DETECTED  : $CpuThreadsDetected"
Write-Host "CPU THREADS REQUESTED : $CpuThreadsRequested"
Write-Host "TOTAL RAM             : ${TotalRamGB} GB"
Write-Host "AVAILABLE RAM         : ${AvailableRamGB} GB"
Write-Host "OLLAMA HOST           : $OllamaHost"
Write-Host "RUN ID                : $RunId"

Write-Forensic `
    -Message (
        "Version=$Version | " +
        "RunId=$RunId"
    ) `
    -Level INFO

Write-Forensic `
    -Message (
        "CPU=$CpuName | " +
        "Cores=$CpuCores | " +
        "Threads=$CpuThreadsDetected | " +
        "RAM=${TotalRamGB}GB"
    ) `
    -Level INFO

Write-Forensic `
    -Message (
        "Benchmark threads requested=$CpuThreadsRequested"
    ) `
    -Level INFO

# =============================================================================
# [14/18] OLLAMA AVAILABILITY
# =============================================================================

Write-Section "[1/18] OLLAMA AVAILABILITY"

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
            "Ollama API inaccessible : $OllamaHost"
        ) `
        -Level FAIL

    throw 'OLLAMA_API_UNAVAILABLE'
}

Write-Forensic `
    -Message 'Ollama API disponible.' `
    -Level PASS

# =============================================================================
# [15/18] INVENTORY
# =============================================================================

Write-Section "[2/18] MODEL INVENTORY"

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
        "$($models.Count) modèle(s) à qualifier."
    ) `
    -Level PASS

foreach ($m in $models) {

    Write-Host (
        '  - {0} | {1} GB | params={2} | quant={3} | family={4}' -f
        $m.Name,
        $m.SizeGB,
        $m.Parameter,
        $m.Quant,
        $m.Family
    )
}

# =============================================================================
# [16/18] INITIAL CLEANUP
# =============================================================================

Write-Section "[3/18] INITIAL RUNTIME CLEANUP"

$initial = @(Get-RuntimeState)

Write-Forensic `
    -Message (
        "Etat initial : $($initial.Count) modèle(s) actif(s)."
    ) `
    -Level INFO

if ($initial.Count -gt 0) {

    Write-Host ''
    Write-Host 'Modèle(s) actuellement actif(s) :'

    foreach ($item in $initial) {

        Write-Host "  * $($item.Name)"
    }
}

Clear-OllamaRuntime

$precheck = @(Get-RunningModelNames)

if ($precheck.Count -ne 0) {

    Write-Forensic `
        -Message (
            'PRECHECK FAILED : runtime non vide.'
        ) `
        -Level FAIL

    throw 'INITIAL_RUNTIME_NOT_EMPTY'
}

Write-Forensic `
    -Message 'PRECHECK OK : 0 modèle actif.' `
    -Level PASS

# =============================================================================
# [17/18] QUALIFICATION
# =============================================================================

Write-Section "[4/18] QUALIFICATION BATTERY"

$profiles = New-Object System.Collections.Generic.List[object]

$totalModels = $models.Count
$modelIndex = 0

foreach ($model in $models) {

    $modelIndex++

    Write-Host ''
    Write-Host (
        ">>> MODELE $modelIndex/$totalModels : $($model.Name)"
    ) -ForegroundColor Cyan

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
                "Qualification interrompue pour " +
                "$($model.Name) : " +
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

                StabilityScore = 0
                HardPassRate = 0

                AvgLatencyMs = 0
                AvgTokensPerSec = 0

                FailureRate = 100

                TestsTotal = 0
                TestsSuccessful = 0
                TestsFailed = 0

                ApiFailures = 0
                EmptyResponses = 0

                SwitchMs = 0
                SwitchWallMs = 0
                Processor = 'unknown'

                Verdict = 'FAIL'

                Tests = @()

                FatalError = $_.Exception.Message
            }
        )
    }
    finally {

        # -----------------------------------------------------------------
        # ABSOLUTE CLEANUP AFTER EVERY MODEL
        # -----------------------------------------------------------------

        try {

            $active = @(Get-RunningModelNames)

            if ($active.Count -gt 1) {

                Write-Forensic `
                    -Message (
                        'VIOLATION SINGLE-MODEL après modèle : ' +
                        ($active -join ', ')
                    ) `
                    -Level FAIL

                throw 'MULTIPLE_MODELS_AFTER_TEST'
            }

            if ($active.Count -eq 1) {

                $released = Unload-OllamaModel `
                    -Model $active[0]

                if (-not $released) {

                    throw 'POST_MODEL_UNLOAD_FAILURE'
                }
            }

            if (-not (Wait-RuntimeEmpty)) {

                throw 'POST_MODEL_RUNTIME_NOT_EMPTY'
            }

            Write-Forensic `
                -Message (
                    "Modèle $($model.Name) " +
                    'complètement sorti du runtime.'
                ) `
                -Level PASS
        }
        catch {

            Write-Forensic `
                -Message (
                    'CLEANUP CRITIQUE : ' +
                    $_.Exception.Message
                ) `
                -Level FAIL

            throw
        }
    }
}

# =============================================================================
# [18/18] FINAL RANKING + EXPORT
# =============================================================================

Write-Section "[5/18] FINAL RANKING"

$ranking = @(
    $profiles |
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
    ) -ForegroundColor Cyan

    Write-Host (
        '     OVERALL      : {0}/100' -f
        $profile.OverallScore
    )

    Write-Host (
        '     CAPABILITY   : {0}/100' -f
        $profile.CapabilityScore
    )

    Write-Host (
        '     RELIABILITY  : {0}/100' -f
        $profile.ReliabilityScore
    )

    Write-Host (
        '     PERFORMANCE  : {0}/100' -f
        $profile.PerformanceScore
    )

    Write-Host (
        '     INSTRUCTION  : {0}/100' -f
        $profile.InstructionScore
    )

    Write-Host (
        '     REASONING    : {0}/100' -f
        $profile.ReasoningScore
    )

    Write-Host (
        '     CODE         : {0}/100' -f
        $profile.CodeScore
    )

    Write-Host (
        '     FRENCH       : {0}/100' -f
        $profile.FrenchScore
    )

    Write-Host (
        '     STRUCTURED   : {0}/100' -f
        $profile.StructuredScore
    )

    Write-Host (
        '     STABILITY    : {0}/100' -f
        $profile.StabilityScore
    )

    Write-Host (
        '     HARD PASS    : {0}%' -f
        $profile.HardPassRate
    )

    Write-Host (
        '     AVG TPS      : {0}' -f
        $profile.AvgTokensPerSec
    )

    Write-Host (
        '     FAILURE      : {0}%' -f
        $profile.FailureRate
    )

    Write-Host (
        '     VERDICT      : {0}' -f
        $profile.Verdict
    )
}

# =============================================================================
# EXPORT JSON
# =============================================================================

Write-Section "[6/18] JSON FORENSIC EXPORT"

$rankingExport = New-Object System.Collections.Generic.List[object]

$rank = 0

foreach ($profile in $ranking) {

    $rank++

    $rankingExport.Add(
        [PSCustomObject]@{

            Rank = $rank
            Model = $profile.Model

            Overall = $profile.OverallScore
            Capability = $profile.CapabilityScore
            Reliability = $profile.ReliabilityScore
            Performance = $profile.PerformanceScore

            Reasoning = $profile.ReasoningScore
            Code = $profile.CodeScore
            French = $profile.FrenchScore
            Instruction = $profile.InstructionScore
            Structured = $profile.StructuredScore

            TPS = $profile.AvgTokensPerSec

            FailureRate = $profile.FailureRate
            HardPassRate = $profile.HardPassRate

            Verdict = $profile.Verdict
        }
    )
}

$export = [PSCustomObject]@{

    Schema = 'EZZIO-MODEL-QUALIFICATION-4.3.2'

    RunId = $RunId

    Timestamp = (
        Get-Date
    ).ToString('o')

    Environment = [PSCustomObject]@{

        CPU = $CpuName

        Cores = $CpuCores

        ThreadsDetected = $CpuThreadsDetected

        ThreadsRequested = $CpuThreadsRequested

        RAM_GB = $TotalRamGB

        AvailableRAM_GB = $AvailableRamGB

        GPU_Mode = 'CPU_ONLY_REQUESTED'

        OllamaHost = $OllamaHost
    }

    Configuration = [PSCustomObject]@{

        SingleModelOnly = $true

        WarmupRuns = $WarmupRuns

        StabilityRuns = $StabilityRuns

        MaxModels = $MaxModels

        Thresholds = $Thresholds
    }

    ModelsQualified = $profiles.Count

    Ranking = @($rankingExport)

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
# CSV
# =============================================================================

Write-Section "[7/18] CSV EXPORT"

$profiles |
    Select-Object `
        RunId,
        Version,
        Model,
        ParameterSize,
        Quantization,
        Family,
        SizeGB,
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
        StabilityScore,
        HardPassRate,
        AvgLatencyMs,
        AvgTokensPerSec,
        FailureRate,
        TestsTotal,
        TestsSuccessful,
        TestsFailed,
        ApiFailures,
        EmptyResponses,
        SwitchMs,
        SwitchWallMs,
        Processor,
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

# =============================================================================
# SUMMARY
# =============================================================================

Write-Section "[8/18] SUMMARY"

$best = $ranking |
    Select-Object -First 1

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

if ($null -ne $best) {

    $bestModel = $best.Model
    $bestOverall = $best.OverallScore
    $bestCapability = $best.CapabilityScore
    $bestReliability = $best.ReliabilityScore
    $bestPerformance = $best.PerformanceScore
    $bestReasoning = $best.ReasoningScore
    $bestCode = $best.CodeScore
    $bestFrench = $best.FrenchScore
    $bestInstruction = $best.InstructionScore
    $bestStructured = $best.StructuredScore
    $bestTPS = $best.AvgTokensPerSec
    $bestFailure = $best.FailureRate
    $bestHardPass = $best.HardPassRate
    $bestVerdict = $best.Verdict
}
else {

    $bestModel = 'NONE'
    $bestOverall = 0
    $bestCapability = 0
    $bestReliability = 0
    $bestPerformance = 0
    $bestReasoning = 0
    $bestCode = 0
    $bestFrench = 0
    $bestInstruction = 0
    $bestStructured = 0
    $bestTPS = 0
    $bestFailure = 100
    $bestHardPass = 0
    $bestVerdict = 'FAIL'
}

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
THREADS DETECTED : $CpuThreadsDetected
THREADS REQUESTED: $CpuThreadsRequested
TOTAL RAM        : $TotalRamGB GB
AVAILABLE RAM    : $AvailableRamGB GB
GPU MODE         : CPU ONLY REQUESTED
OLLAMA HOST      : $OllamaHost

RUNTIME CONTRACT
----------------
SINGLE MODEL ONLY : ENFORCED
PRE-SWITCH CLEAN  : ENFORCED
POST-SWITCH CHECK : ENFORCED
FINAL CLEANUP     : ENFORCED
MODEL DELETION    : NEVER

QUALIFICATION
-------------
MODELS            : $($profiles.Count)
QUALIFIED         : $qualifiedCount
PARTIAL           : $partialCount
FAIL              : $failedCount

BEST MODEL
----------
$bestModel

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

INSTRUCTION
-----------
$bestInstruction / 100

REASONING
---------
$bestReasoning / 100

CODE
----
$bestCode / 100

FRENCH
------
$bestFrench / 100

STRUCTURED
----------
$bestStructured / 100

HARD PASS RATE
--------------
$bestHardPass %

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

CAPABILITY :
Mesure les performances cognitives observées sur la batterie.

RELIABILITY :
Mesure la stabilité, les HardPass et la capacité à produire
une réponse exploitable sans erreur.

PERFORMANCE :
Mesure principalement le débit de génération.

IMPORTANT :
Un modèle rapide n'est pas automatiquement plus capable.

Le classement doit donc être lu en priorité selon :

1. CAPABILITY
2. RELIABILITY
3. PERFORMANCE

===============================================================================
FILES
=====

JSON
----
$JsonPath

CSV
---
$CsvPath

FORENSIC LOG
------------
$LogPath

SUMMARY
-------
$SummaryPath

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
# FINAL CLEANUP
# =============================================================================

Write-Section "[17/18] FINAL RUNTIME CLEANUP"

try {

    Clear-OllamaRuntime

    $finalCheck = @(Get-RunningModelNames)

    if ($finalCheck.Count -ne 0) {

        Write-Forensic `
            -Message (
                'FAIL-CLOSED : modèle encore actif après cleanup final.'
            ) `
            -Level FAIL

        throw 'FINAL_RUNTIME_NOT_EMPTY'
    }

    Write-Forensic `
        -Message (
            'Runtime Ollama propre : 0 modèle actif.'
        ) `
        -Level PASS
}
catch {

    Write-Forensic `
        -Message (
            'FINAL CLEANUP FAILURE : ' +
            $_.Exception.Message
        ) `
        -Level FAIL

    throw
}

# =============================================================================
# FINAL VERDICT
# =============================================================================

Write-Section "[18/18] FINAL VERDICT"

Write-Host ''
Write-Host 'MODELS       : ' $profiles.Count
Write-Host 'QUALIFIED    : ' $qualifiedCount -ForegroundColor Green
Write-Host 'PARTIAL      : ' $partialCount -ForegroundColor Yellow
Write-Host 'FAIL         : ' $failedCount -ForegroundColor Red
Write-Host ''
Write-Host 'SINGLE MODEL : ENFORCED'
Write-Host 'CPU ONLY     : ENABLED'
Write-Host 'GPU          : NOT USED BY REQUESTS'
Write-Host ''

if ($null -ne $best) {

    Write-Host (
        'BEST MODEL   : {0}' -f
        $best.Model
    ) -ForegroundColor Cyan

    Write-Host (
        'CAPABILITY   : {0}/100' -f
        $best.CapabilityScore
    ) -ForegroundColor Cyan

    Write-Host (
        'RELIABILITY  : {0}/100' -f
        $best.ReliabilityScore
    ) -ForegroundColor Cyan

    Write-Host (
        'PERFORMANCE  : {0}/100' -f
        $best.PerformanceScore
    ) -ForegroundColor Cyan

    Write-Host (
        'OVERALL      : {0}/100' -f
        $best.OverallScore
    ) -ForegroundColor Cyan

    Write-Host (
        'VERDICT      : {0}' -f
        $best.Verdict
    ) -ForegroundColor Cyan
}

Write-Host ''
Write-Host 'JSON         : ' $JsonPath
Write-Host 'CSV          : ' $CsvPath
Write-Host 'SUMMARY      : ' $SummaryPath
Write-Host 'FORENSIC LOG : ' $LogPath
Write-Host ''

Write-Host ('=' * 82)
Write-Host (
    'E-ZZIO MODEL QUALIFICATION GATE v{0} — EXECUTION TERMINEE' -f
    $Version
)
Write-Host 'SINGLE-MODEL RUNTIME CONFIRMED CLEAN'
Write-Host ('=' * 82)