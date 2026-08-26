#requires -Version 7.4
# =============================================================================
# E-ZZIO — MODEL QUALIFICATION GATE
# Version : 4.3.3 (FORENSIC HARDENED)
# Mode    : CPU-ONLY / SINGLE-MODEL-SWITCH / FORENSIC / POTENTIAL-PROFILING
# =============================================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# =============================================================================
# [0/18] CONFIGURATION & INITIALISATION
# =============================================================================

$Version = '4.3.3'
$Root = Split-Path -Parent$MyInvocation.MyCommand.Path
$AuditRoot = Join-Path$Root 'audit\model_gate_v4.3.3'

if (-not (Test-Path -LiteralPath $AuditRoot)) {
    New-Item -ItemType Directory -Path $AuditRoot -Force | Out-Null
}

$RunId = Get-Date -Format 'yyyyMMdd_HHmmss'$LogPath     = Join-Path $AuditRoot "forensic_$RunId.log"
$JsonPath    = Join-Path $AuditRoot "qualification_$RunId.json"
$CsvPath     = Join-Path $AuditRoot "qualification_$RunId.csv"
$SummaryPath = Join-Path $AuditRoot "summary_$RunId.txt"

$OllamaHost = 'http://127.0.0.1:11434'

# -------------------------------------------------------------------------
# DÉTECTION MATÉRIELLE
# -------------------------------------------------------------------------
$CpuName = 'UNKNOWN'
$CpuCores = 0$CpuThreads = [Environment]::ProcessorCount
$TotalRamGB = 0.0$AvailableRamGB = 0.0

try {
    $cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
    if ($null -ne$cpu) {
        $CpuName = [string]$cpu.Name
        $CpuCores = [int]$cpu.NumberOfCores
        $CpuThreads = [int]$cpu.NumberOfLogicalProcessors
    }
} catch { $CpuName = 'UNKNOWN' }

try {
    $os = Get-CimInstance Win32_OperatingSystem
    if ($null -ne$os) {
        $TotalRamGB     = [math]::Round(([double]$os.TotalVisibleMemorySize / 1MB), 2)
        $AvailableRamGB = [math]::Round(([double]$os.FreePhysicalMemory / 1MB), 2)
    }
} catch { $TotalRamGB = 0.0; $AvailableRamGB = 0.0 }

# -------------------------------------------------------------------------
# PARAMÈTRES D'EXÉCUTION
# -------------------------------------------------------------------------
$WarmupRuns        = 1$StabilityRuns     = 2
$MaxModels         = 0$RequestTimeoutSec = 300
$SwitchTimeoutSec  = 180$KeepAlive         = '10m'
$ForceCpuOnly      =$true
$NumGpu            = 0$Temperature       = 0

# -------------------------------------------------------------------------
# SEUILS CONTRACTUELS
# -------------------------------------------------------------------------
$Thresholds = [ordered]@{
    MinOverallScore       = 60
    MinCapabilityScore    = 60
    MinReliabilityScore   = 70
    MinInstructionScore   = 60
    MinReasoningScore     = 50
    MinCodeScore          = 50
    MinFrenchScore        = 50
    MinStructuredScore    = 50
    MinContextScore       = 50
    MinStabilityScore     = 70
    MaxFailureRatePercent = 20
}

# =============================================================================
# [1/18] JOURNALISATION FORENSIC
# =============================================================================

function Write-Forensic {
    param(
        [Parameter(Mandatory)] [string]$Message,
        [ValidateSet('INFO','PASS','WARN','FAIL','SWITCH','TEST','METRIC')]
        [string]$Level = 'INFO'
    )
    $timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss.fff'
    $line = '[{0}] [{1}] {2}' -f$timestamp, $Level,$Message
    Add-Content -LiteralPath $LogPath -Value$line -Encoding UTF8

    switch ($Level) {
        'PASS'   { Write-Host $line -ForegroundColor Green }
        'WARN'   { Write-Host $line -ForegroundColor Yellow }
        'FAIL'   { Write-Host $line -ForegroundColor Red }
        'SWITCH' { Write-Host $line -ForegroundColor Cyan }
        'TEST'   { Write-Host $line -ForegroundColor Magenta }
        'METRIC' { Write-Host $line -ForegroundColor DarkCyan }
        default  { Write-Host $line }
    }
}

function Write-Section {
    param([Parameter(Mandatory)] [string]$Title)
    Write-Host ''
    Write-Host ('=' * 82)
    Write-Host $Title
    Write-Host ('=' * 82)
}

# =============================================================================
# [2/18] CONVERSIONS SÉCURISÉES (FIX DÉBORDEMENT 64-BIT)
# =============================================================================

function Convert-ToDoubleSafe {
    param([AllowNull()] $Value)
    if ($null -eq$Value) { return 0.0 }
    try { return [double]$Value } catch { return 0.0 }
}

function Convert-ToInt64Safe {
    param([AllowNull()] $Value)
    if ($null -eq$Value) { return 0L }
    try { return [int64]$Value } catch { return 0L }
}

function Convert-ToIntSafe {
    param([AllowNull()] $Value)
    if ($null -eq$Value) { return 0 }
    try { return [int]$Value } catch { return 0 }
}

# =============================================================================
# [3/18] INTERFACE API OLLAMA & DÉTECTION DES MODÈLES
# =============================================================================

function Test-OllamaAvailable {
    try {
        Invoke-RestMethod -Uri "$OllamaHost/api/tags" -Method Get -TimeoutSec 10 | Out-Null
        return $true
    } catch { return $false }
}

function Get-OllamaModels {
    try {
        $response = Invoke-RestMethod -Uri "$OllamaHost/api/tags" -Method Get -TimeoutSec 20
        if ($null -eq$response.models) { return @() }

        return @(
            $response.models | ForEach-Object {
                $family = [string]$_.details.family
                $name   = [string]$_.name
                $isEmbedding = ($family -match '(?i)bert\vert{}nomic\vert{}embedding') -or ($name -match '(?i)embed|bge|nomic-embed')

                [PSCustomObject]@{
                    Name        = $name
                    SizeBytes   = Convert-ToInt64Safe $_.size
                    SizeGB      = [math]::Round(((Convert-ToDoubleSafe $_.size) / 1GB), 2)
                    Parameter   = [string]$_.details.parameter_size
                    Quant       = [string]$_.details.quantization_level
                    Family      = $family
                    Format      = [string]$_.details.format
                    IsEmbedding = $isEmbedding
                }
            }
        )
    } catch {
        throw "Impossible de récupérer les modèles Ollama : $($_.Exception.Message)"
    }
}

function Get-OllamaRunningModels {
    try {
        $response = Invoke-RestMethod -Uri "$OllamaHost/api/ps" -Method Get -TimeoutSec 15
        if ($null -eq$response.models) { return @() }
        return @($response.models)
    } catch {
        Write-Forensic -Message "Lecture /api/ps impossible : $($_.Exception.Message)" -Level WARN
        return @()
    }
}

function Get-RunningModelNames {
    $running = @(Get-OllamaRunningModels)$names = New-Object System.Collections.Generic.List[string]
    foreach ($item in$running) {
        if ($null -ne$item.name) { $names.Add([string]$item.name) }
        elseif ($null -ne$item.model) { $names.Add([string]$item.model) }
    }
    return @($names)
}

function Get-RunningModelRecord {
    param([Parameter(Mandatory)] [string]$Model)$running = @(Get-OllamaRunningModels)
    foreach ($item in $running) {$name = if ($null -ne$item.name) { [string]$item.name } else { [string]$item.model }
        if ($name -eq $Model) { return$item }
    }
    return $null
}

# =============================================================================
# [4/18] GOUVERNANCE STRICTE : ISOLATION MONO-MODÈLE
# =============================================================================

function Assert-SingleModel {
    $running = @(Get-RunningModelNames)
    if ($running.Count -gt 1) {
        Write-Forensic -Message "FAIL-CLOSED : plusieurs modèles actifs : $($running -join ', ')" -Level FAIL
        throw 'SINGLE_MODEL_VIOLATION'
    }
    if ($running.Count -eq 1) {
        Write-Forensic -Message "Modèle actif confirmé : $($running[0])" -Level INFO
        return $running[0]
    }
    Write-Forensic -Message 'Runtime EMPTY : 0 modèle actif.' -Level PASS
    return $null
}

function Wait-RuntimeEmpty {
    param([int]$Attempts = 8, [int]$DelayMs = 250)
    for ($i = 1; $i -le$Attempts; $i++) {$running = @(Get-RunningModelNames)
        if ($running.Count -eq 0) {
            Write-Forensic -Message "Runtime EMPTY confirmé à la tentative $i/$Attempts." -Level PASS
            return $true
        }
        if ($running.Count -gt 1) {
            Write-Forensic -Message "Plusieurs modèles détectés pendant cleanup : $($running -join ', ')" -Level FAIL
            throw 'MULTIPLE_MODELS_DURING_CLEANUP'
        }
        Start-Sleep -Milliseconds $DelayMs
    }
    Write-Forensic -Message 'Runtime non vide après toutes les tentatives.' -Level FAIL
    return $false
}

# =============================================================================
# [5/18] DÉCHARGEMENT PROPRE
# =============================================================================

function Unload-OllamaModel {
    param([Parameter(Mandatory)] [string]$Model)
    Write-Forensic -Message "LIBERATION -> $Model" -Level SWITCH

    $payload = @{
        model      = $Model
        prompt     = ''
        stream     = $false
        keep_alive = 0
        options    = @{ num_gpu = 0 }
    } | ConvertTo-Json -Depth 8

    try {
        Invoke-RestMethod -Uri "$OllamaHost/api/generate" -Method Post -ContentType 'application/json' -Body $payload -TimeoutSec 60 | Out-Null
    } catch {
        Write-Forensic -Message "API unload échouée pour $Model : $($_.Exception.Message)" -Level WARN
    }

    if (Wait-RuntimeEmpty) {
        Write-Forensic -Message "Modèle $Model libéré via API." -Level PASS
        return $true
    }
    return $false
}

function Clear-OllamaRuntime {
    Write-Forensic -Message 'NETTOYAGE GLOBAL DU RUNTIME OLLAMA' -Level SWITCH
    $running = @(Get-RunningModelNames)

    if ($running.Count -gt 1) {
        Write-Forensic -Message "FAIL-CLOSED : plusieurs modèles actifs : $($running -join ', ')" -Level FAIL
        throw 'MULTIPLE_ACTIVE_MODELS'
    }
    if ($running.Count -eq 1) {
        $released = Unload-OllamaModel -Model$running[0]
        if (-not $released) { throw 'RUNTIME_CLEANUP_FAILED' }
    }
    if (-not (Wait-RuntimeEmpty)) { throw 'RUNTIME_NOT_EMPTY' }
}

# =============================================================================
# [6/18] VÉRIFICATION CPU-ONLY
# =============================================================================

function Assert-CpuOnly {
    param([Parameter(Mandatory)] [string]$Model)
    $record = Get-RunningModelRecord -Model$Model

    if ($null -eq $record -or [string]::IsNullOrWhiteSpace([string]$record.processor)) {
        Write-Forensic -Message "Champ processor absent de /api/ps pour $Model (supposé CPU)." -Level WARN
        return [PSCustomObject]@{ Verified = $false; Processor = 'UNKNOWN' }
    }

    $processor = [string]$record.processor
    Write-Forensic -Message "Processor Ollama : $processor" -Level INFO

    if ($processor -match '(?i)CPU') {
        Write-Forensic -Message "CPU-ONLY confirmé pour $Model." -Level PASS
        return [PSCustomObject]@{ Verified = $true; Processor =$processor }
    }

    Write-Forensic -Message "CPU-ONLY VIOLATION : processor=$processor" -Level FAIL
    throw 'GPU_PROCESSING_DETECTED'
}

# =============================================================================
# [7/18] COMMUTATION DE MODÈLE (SWITCH)
# =============================================================================

function Switch-OllamaModel {
    param([Parameter(Mandatory)] [string]$Model)
    Write-Forensic -Message "========== SWITCH -> $Model ==========" -Level SWITCH
    Clear-OllamaRuntime

    $payload = @{
        model      = $Model
        prompt     = 'E-ZZIO SWITCH PROBE. Réponds uniquement READY.'
        stream     = $false
        keep_alive = $KeepAlive
        options    = @{
            temperature = 0
            num_predict = 16
            num_gpu     = $NumGpu
        }
    } | ConvertTo-Json -Depth 10

    $wallStart = Get-Date
    try {
        $response = Invoke-RestMethod -Uri "$OllamaHost/api/generate" -Method Post -ContentType 'application/json' -Body $payload -TimeoutSec$SwitchTimeoutSec
    } catch {
        Write-Forensic -Message "Échec switch/load $Model : $($_.Exception.Message)" -Level FAIL
        throw 'MODEL_LOAD_FAILED'
    }

    $wallMs = ((Get-Date) -$wallStart).TotalMilliseconds
    $running = @(Get-RunningModelNames)

    if ($running.Count -ne 1) { throw 'POST_SWITCH_CARDINALITY_FAILURE' }
    if ($running[0] -ne$Model) { throw 'POST_SWITCH_WRONG_MODEL' }

    $cpuState = Assert-CpuOnly -Model$Model
    $loadNs   = Convert-ToDoubleSafe$response.load_duration
    $loadMs   = [math]::Round(($loadNs / 1000000), 3)
    if ($loadMs -le 0) { $loadMs = [math]::Round($wallMs, 3) }

    Write-Forensic -Message ("SWITCH OK | Model={0} | Load={1}ms | Wall={2}ms | Active=1 | Processor={3}" -f `
        $Model,$loadMs, [math]::Round($wallMs,3),$cpuState.Processor) -Level PASS

    return [PSCustomObject]@{
        Model       = $Model
        LoadMs      = $loadMs
        WallMs      = [math]::Round($wallMs, 3)
        Processor   = $cpuState.Processor
        CpuVerified = $cpuState.Verified
    }
}

# =============================================================================
# [8/18] EXTRACTION ROBUSTE DES RÉPONSES ET BALISES <THINK>
# =============================================================================

function Get-ResponseParts {
    param([Parameter(Mandatory)] $ApiResponse)

    $rawFinal = ''$thinking = ''

    if ($null -ne$ApiResponse.response) {
        $rawFinal = [string]$ApiResponse.response
    }
    elseif ($null -ne$ApiResponse.message -and $null -ne$ApiResponse.message.content) {
        $rawFinal = [string]$ApiResponse.message.content
    }

    if ($null -ne$ApiResponse.thinking) {
        $thinking = [string]$ApiResponse.thinking
    }
    elseif ($null -ne$ApiResponse.message -and $null -ne$ApiResponse.message.thinking) {
        $thinking = [string]$ApiResponse.message.thinking
    }

    # Extraction des balises <think>...</think> si intégrées dans le texte brut
    if ($rawFinal -match '(?s)<think>(.*?)</think>') {
        $extractedThinking =$Matches[1].Trim()
        if ([string]::IsNullOrWhiteSpace($thinking)) {
            $thinking =$extractedThinking
        } else {
            $thinking += "`n" + $extractedThinking
        }
        $rawFinal = ($rawFinal -replace '(?s)<think>.*?</think>', '').Trim()
    }

    $final = $rawFinal.Trim()
    $thinking = $thinking.Trim()

    # Normalisation stricte des sauts de ligne en format Unix LF
    $final = $final -replace "\r\n", "`n" -replace "\r", "`n"
    $thinking = $thinking -replace "\r\n", "`n" -replace "\r", "`n"

    $combined = if ($thinking.Length -gt 0 -and $final.Length -gt 0) { "$thinking`n$final" }
                elseif ($thinking.Length -gt 0) { $thinking } else {$final }

    $status = 'EMPTY_OUTPUT'
    if ($final.Length -gt 0 -and $thinking.Length -gt 0) {$status = 'FINAL_AND_THINKING' }
    elseif ($final.Length -gt 0) {$status = 'FINAL_RESPONSE' }
    elseif ($thinking.Length -gt 0) {$status = 'THINKING_ONLY' }

    return [PSCustomObject]@{
        FinalResponse  = $final
        Thinking       = $thinking
        CombinedOutput = $combined
        FinalChars     = $final.Length
        ThinkingChars  = $thinking.Length
        CombinedChars  = $combined.Length
        OutputStatus   = $status
    }
}

# =============================================================================
# [9/18] ÉVALUATION DÉTERMINISTE DES RÉPONSES
# =============================================================================

function Evaluate-Response {
    param(
        [Parameter(Mandatory)] [string]$TestId,
        [Parameter(Mandatory)] [string]$Category,
        [AllowEmptyString()]   [string]$Response,
        [AllowEmptyString()]   [string]$Thinking,
        [string]$ExpectedExact     = '',
        [string]$ExpectedContains  = '',
        [string]$ForbiddenPattern  = ''
    )

    $text = if ($null -ne$Response) { $Response.Trim() } else { '' }$reasons = New-Object System.Collections.Generic.List[string]
    $score = 0$hardPass = $false$hardCheck = 'NOT_APPLICABLE'

    if ($text.Length -eq 0) {$reasons.Add('final response empty')
        if ($Thinking.Trim().Length -gt 0) {$reasons.Add('thinking present') }
        return [PSCustomObject]@{
            TestId    = $TestId
            Category  = $Category
            Score     = 0
            HardPass  = $false
            HardCheck = 'EMPTY_FINAL_RESPONSE'
            Reasons   = @($reasons)
        }
    }

    $score += 20$reasons.Add('non-empty final response')

    # Correspondance exacte
    if ($ExpectedExact.Length -gt 0) {
        $normExpected =$ExpectedExact.Trim() -replace "\r\n", "`n" -replace "\r", "`n"
        if ($text -ceq $normExpected) {
            $hardPass  = $true
            $hardCheck = 'EXACT_MATCH'
            $score += 80
            $reasons.Add('exact match')
        } else {
            $hardCheck = 'EXACT_MISMATCH'
            $reasons.Add('exact mismatch')
        }
    }

    # Contenu requis (séparateur |)
    if ($ExpectedContains.Length -gt 0) {
        $containsParts = @($ExpectedContains -split '\|')
        $found = 0
        foreach ($part in $containsParts) {
            if ($part.Length -gt 0 -and $text.IndexOf($part, [System.StringComparison]::OrdinalIgnoreCase) -ge 0) {
                $found++
            }
        }
        if ($containsParts.Count -gt 0 -and $found -eq $containsParts.Count) {
            $hardPass = $true
            if ($hardCheck -eq 'NOT_APPLICABLE') { $hardCheck = 'EXPECTED_CONTENT_FOUND' }
            $score += 50
            $reasons.Add('expected content found')
        } else {
            $reasons.Add("expected content $found/$($containsParts.Count)")
        }
    }

    # Motifs interdits
    if ($ForbiddenPattern.Length -gt 0) {
        if ($text -match $ForbiddenPattern) {
            $hardPass = $false
            $reasons.Add('forbidden pattern detected')
        } else {
            $score += 10
            $reasons.Add('forbidden pattern absent')
        }
    }

    # Heuristiques par catégorie
    switch ($Category) {
        'General' {
            if ($text.Length -ge 100) { $score += 15; $reasons.Add('adequate answer length') }
            if ($text -match '(?i)architecture|séparation|audit|exécution|politique') {
                $score += 15; $reasons.Add('technical vocabulary')
            }
        }
        'Instruction' {
            $lines = @($text -split '\n' | Where-Object { $_.Trim().Length -gt 0 })
            if ($lines.Count -eq 3) { $score += 20; $reasons.Add('three non-empty lines') }
            if ($text -match '(?m)^\s*ALPHA\s*$' -and $text -match '(?m)^\s*BETA\s*$' -and $text -match '(?m)^\s*GAMMA\s*$') {
                $score += 50; $reasons.Add('instruction tokens correct')
            }
        }
        'Reasoning' {
            if ($text -match '(?i)\d+') { $score += 15; $reasons.Add('numeric reasoning evidence') }
            if ($text -match '(?i)donc|car|puisque|étape|calcul|ensuite|final') {
                $score += 20; $reasons.Add('reasoning language')
            }
        }
        'Code' {
            if ($text -match '(?i)def\s+\w+\s*\(|function\s+\w+') { $score += 25; $reasons.Add('function declaration') }
            if ($text -match '(?i)return|param\s*\(|if\s*\(') { $score += 20; $reasons.Add('control/return syntax') }
            if ($text -match '(?i)null|none|\$null') { $score += 15; $reasons.Add('null handling') }
            if ($text -match '(?i)```') { $score -= 10; $reasons.Add('markdown fence penalty') }
        }
        'Structured' {
            $cleanJson = $text -replace '(?s)^```(?:json)?\s*', '' -replace '```\s*$', ''
            try {
                $parsed = $cleanJson.Trim() | ConvertFrom-Json -ErrorAction Stop
                if ($null -ne $parsed) {
                    $score += 60; $reasons.Add('valid JSON')
                    if ($parsed.status -eq 'PASS' -and [int]$parsed.score -eq 100 -and $parsed.mode -eq 'CPU') {
                        $hardPass  = $true
                        $hardCheck = 'JSON_SCHEMA_MATCH'
                        $score += 20
                        $reasons.Add('expected JSON fields correct')
                    }
                }
            } catch { $reasons.Add('invalid JSON') }
        }
        'French' {
            if ($text -match '(?i)\b(le|la|les|des|une|dans|avec|pour|est|sont|modèle|latence|débit|fiabilité)\b') {
                $score += 30; $reasons.Add('French lexical evidence')
            }
            if ($text.Length -ge 100) { $score += 20; $reasons.Add('adequate French response') }
        }
        'Context' {
            if ($text -match '(?i)\b91\b') {
                $score += 60; $hardPass = $true; $hardCheck = 'CONTEXT_VALUE_MATCH'
                $reasons.Add('context value recovered')
            }
        }
        'Robustness' {
            if ($text -match '(?i)fausse?|incorrect|pas nécessairement|dépend') {
                $score += 35; $reasons.Add('counterexample/correction evidence')
            }
            if ($text -match '(?i)capacité|qualité|latence|raisonnement|performance') {
                $score += 25; $reasons.Add('distinction capability/performance')
            }
        }
        'Stability' {
            if ($text.Length -ge 40) { $score += 30; $reasons.Add('stable response length') }
        }
    }

    if ($score -lt 0) { $score = 0 }
    if ($score -gt 100) { $score = 100 }

    return [PSCustomObject]@{
        TestId    = $TestId
        Category  = $Category
        Score     = [int]$score
        HardPass  = $hardPass
        HardCheck = $hardCheck
        Reasons   = @($reasons)
    }
}

# =============================================================================
# [10/18] EXÉCUTION D'UN TEST UNITAIRE
# =============================================================================

function Invoke-ModelTest {
    param(
        [Parameter(Mandatory)] [string]$Model,
        [Parameter(Mandatory)] [string]$TestId,
        [Parameter(Mandatory)] [string]$Category,
        [Parameter(Mandatory)] [string]$Prompt,
        [int]$MaxTokens = 350,
        [string]$ExpectedExact    = '',
        [string]$ExpectedContains = '',
        [string]$ForbiddenPattern = ''
    )

    Write-Forensic -Message "TEST $TestId | $Category" -Level TEST
    $active = Assert-SingleModel
    if ($active -ne $Model) { throw 'ACTIVE_MODEL_MISMATCH' }

    $payload = @{
        model      = $Model
        prompt     = $Prompt
        stream     = $false
        keep_alive = $KeepAlive
        options    = @{
            temperature = $Temperature
            num_predict = $MaxTokens
            num_gpu     = $NumGpu
        }
    } | ConvertTo-Json -Depth 10

    $wallStart = Get-Date
    try {
        $apiResponse = Invoke-RestMethod -Uri "$OllamaHost/api/generate" -Method Post -ContentType 'application/json' -Body $payload -TimeoutSec $RequestTimeoutSec
        $wallMs = ((Get-Date) - $wallStart).TotalMilliseconds
    } catch {
        $wallMs = ((Get-Date) - $wallStart).TotalMilliseconds
        Write-Forensic -Message "TEST $TestId API ERROR : $($_.Exception.Message)" -Level FAIL

        return [PSCustomObject]@{
            TestId               = $TestId
            Category             = $Category
            Success              = $false
            OutputStatus         = 'API_ERROR'
            Score                = 0
            HardPass             = $false
            HardCheck            = 'API_ERROR'
            FinalResponse        = ''
            Thinking             = ''
            CombinedOutput       = ''
            FinalChars           = 0
            ThinkingChars        = 0
            CombinedChars        = 0
            WallMs               = [math]::Round($wallMs, 3)
            TotalDurationMs      = 0.0
            LoadDurationMs       = 0.0
            PromptEvalDurationMs = 0.0
            EvalDurationMs       = 0.0
            PromptTokens         = 0
            GeneratedTokens      = 0
            TokensPerSecond      = 0.0
            ResponsePreview      = ''
            Reasons              = @($_.Exception.Message)
            Error                = $_.Exception.Message
        }
    }

    $parts           = Get-ResponseParts -ApiResponse $apiResponse
    $totalNs         = Convert-ToDoubleSafe $apiResponse.total_duration
    $loadNs          = Convert-ToDoubleSafe $apiResponse.load_duration
    $promptEvalNs    = Convert-ToDoubleSafe $apiResponse.prompt_eval_duration
    $evalNs          = Convert-ToDoubleSafe $apiResponse.eval_duration
    $promptTokens    = Convert-ToIntSafe $apiResponse.prompt_eval_count
    $generatedTokens = Convert-ToIntSafe $apiResponse.eval_count

    $totalMs      = [math]::Round(($totalNs / 1000000), 3)
    $loadMs       = [math]::Round(($loadNs / 1000000), 3)
    $promptEvalMs = [math]::Round(($promptEvalNs / 1000000), 3)
    $evalMs       = [math]::Round(($evalNs / 1000000), 3)

    $tps = 0.0
    if ($generatedTokens -gt 0 -and $evalMs -gt 0) {
        $tps = [math]::Round(($generatedTokens / ($evalMs / 1000)), 3)
    }

    $evaluation = Evaluate-Response `
        -TestId $TestId `
        -Category $Category `
        -Response $parts.FinalResponse `
        -Thinking $parts.Thinking `
        -ExpectedExact $ExpectedExact `
        -ExpectedContains $ExpectedContains `
        -ForbiddenPattern $ForbiddenPattern

    $success = ($parts.FinalResponse.Length -gt 0)
    if (-not $success) {
        if ($parts.Thinking.Length -gt 0) {
            Write-Forensic -Message "TEST $TestId : FINAL RESPONSE vide, mais THINKING présent ($($parts.ThinkingChars) chars)." -Level WARN
        } else {
            Write-Forensic -Message "TEST $TestId : sortie totalement vide." -Level WARN
        }
    }

    $preview = if ($parts.FinalResponse.Length -gt 300) { $parts.FinalResponse.Substring(0, 300) } else { $parts.FinalResponse }

    $result = [PSCustomObject]@{
        TestId               = $TestId
        Category             = $Category
        Success              = $success
        OutputStatus         = $parts.OutputStatus
        Score                = $evaluation.Score
        HardPass             = $evaluation.HardPass
        HardCheck            = $evaluation.HardCheck
        FinalResponse        = $parts.FinalResponse
        Thinking             = $parts.Thinking
        CombinedOutput       = $parts.CombinedOutput
        FinalChars           = $parts.FinalChars
        ThinkingChars        = $parts.ThinkingChars
        CombinedChars        = $parts.CombinedChars
        WallMs               = [math]::Round($wallMs, 3)
        TotalDurationMs      = $totalMs
        LoadDurationMs       = $loadMs
        PromptEvalDurationMs = $promptEvalMs
        EvalDurationMs       = $evalMs
        PromptTokens         = $promptTokens
        GeneratedTokens      = $generatedTokens
        TokensPerSecond      = $tps
        ResponsePreview      = $preview
        Reasons              = @($evaluation.Reasons)
        Error                = $null
    }

    Write-Forensic -Message ("RESULT {0} | Score={1} | HardPass={2} | Status={3} | Wall={4}ms | Load={5}ms | Prompt={6}ms | Eval={7}ms | Tokens={8} | TPS={9} | Thinking={10}chars | Final={11}chars" -f `
        $TestId, $result.Score, $result.HardPass, $result.OutputStatus, $result.WallMs, $result.LoadDurationMs, `
        $result.PromptEvalDurationMs, $result.EvalDurationMs, $result.GeneratedTokens, $result.TokensPerSecond, `
        $result.ThinkingChars, $result.FinalChars) -Level METRIC

    return $result
}

# =============================================================================
# [11/18] BATTERIE DE TESTS STANDARDISÉE
# =============================================================================

$Tests = @(
    [PSCustomObject]@{
        Id               = 'GEN-01'
        Category         = 'General'
        Prompt           = "Réponds en français à cette question :`nPourquoi une architecture logicielle robuste doit-elle séparer les politiques de décision, l'exécution et l'audit ?`nDonne une réponse techniquement précise, structurée et concise."
        MaxTokens        = 450
        ExpectedExact    = ''
        ExpectedContains = 'politique|exécution|audit'
        ForbiddenPattern = ''
    },
    [PSCustomObject]@{
        Id               = 'INS-01'
        Category         = 'Instruction'
        Prompt           = "Réponds exactement avec trois lignes.`nLigne 1 : ALPHA`nLigne 2 : BETA`nLigne 3 : GAMMA`nN'ajoute absolument aucun autre texte ni raisonnement."
        MaxTokens        = 128
        ExpectedExact    = "ALPHA`nBETA`nGAMMA"
        ExpectedContains = ''
        ForbiddenPattern = '(?i)explication|voici|bien sûr|```'
    },
    [PSCustomObject]@{
        Id               = 'REASON-01'
        Category         = 'Reasoning'
        Prompt           = "Un système possède 3 files.`nLa première contient 12 tâches.`nLa deuxième contient deux fois moins de tâches que la première.`nLa troisième contient 5 tâches de plus que la deuxième.`nCombien de tâches y a-t-il au total ? Explique brièvement le calcul."
        MaxTokens        = 350
        ExpectedExact    = ''
        ExpectedContains = '29' # 12 + 6 + 11 = 29
        ForbiddenPattern = ''
    },
    [PSCustomObject]@{
        Id               = 'REASON-02'
        Category         = 'Reasoning'
        Prompt           = "Un programme reçoit 100 unités.`nIl dépense 30 %.`nPuis il dépense encore 20 unités.`nIl reçoit ensuite 10 unités.`nQuelle est la quantité finale ? Montre les étapes du calcul."
        MaxTokens        = 350
        ExpectedExact    = ''
        ExpectedContains = '60' # 100 - 30 - 20 + 10 = 60
        ForbiddenPattern = ''
    },
    [PSCustomObject]@{
        Id               = 'CODE-01'
        Category         = 'Code'
        Prompt           = "Écris une fonction Python appelée safe_divide(a, b) qui retourne a / b et retourne None lorsque b vaut zéro.`nDonne uniquement le code brut sans markdown."
        MaxTokens        = 256
        ExpectedExact    = ''
        ExpectedContains = 'safe_divide|return'
        ForbiddenPattern = ''
    },
    [PSCustomObject]@{
        Id               = 'CODE-02'
        Category         = 'Code'
        Prompt           = "Écris une fonction PowerShell Get-SafeValue qui accepte un paramètre [object]`$Value et retourne `$Value uniquement s'il n'est pas `$null. Sinon elle retourne une chaîne vide.`nDonne uniquement le code."
        MaxTokens        = 256
        ExpectedExact    = ''
        ExpectedContains = 'Get-SafeValue|$null'
        ForbiddenPattern = ''
    },
    [PSCustomObject]@{
        Id               = 'JSON-01'
        Category         = 'Structured'
        Prompt           = "Retourne uniquement un JSON valide, sans markdown :`n{`n  `"status`": `"PASS`",`n  `"score`": 100,`n  `"mode`": `"CPU`"`n}"
        MaxTokens        = 180
        ExpectedExact    = ''
        ExpectedContains = ''
        ForbiddenPattern = '```'
    },
    [PSCustomObject]@{
        Id               = 'FR-01'
        Category         = 'French'
        Prompt           = "Explique en français, avec un vocabulaire technique naturel, la différence entre latence, débit et fiabilité pour un modèle IA local.`nDonne un exemple concret."
        MaxTokens        = 400
        ExpectedExact    = ''
        ExpectedContains = 'latence|débit|fiabilité'
        ForbiddenPattern = ''
    },
    [PSCustomObject]@{
        Id               = 'ROB-01'
        Category         = 'Robustness'
        Prompt           = "Analyse cette affirmation : `"Un modèle plus rapide est nécessairement plus intelligent.`"`nDis si elle est vraie ou fausse et explique pourquoi."
        MaxTokens        = 350
        ExpectedExact    = ''
        ExpectedContains = 'rapide|capacité|performance'
        ForbiddenPattern = ''
    },
    [PSCustomObject]@{
        Id               = 'CTX-01'
        Category         = 'Context'
        Prompt           = "Mémorise mentalement ces quatre éléments :`nAZUR = 17`nBUS = 42`nEZZIO = 91`nSWITCH = 63`nPuis réponds uniquement par la valeur correspondant à EZZIO."
        MaxTokens        = 128
        ExpectedExact    = '91'
        ExpectedContains = ''
        ForbiddenPattern = ''
    }
)

# =============================================================================
# [12/18] AGRÉGATION ET NOTATION PAR CATÉGORIE
# =============================================================================

function Get-CategoryScore {
    param(
        [Parameter(Mandatory)] [array]$Results,
        [Parameter(Mandatory)] [string]$Category
    )
    $items = @($Results | Where-Object { $_.Category -eq $Category })
    if ($items.Count -eq 0) { return 0.0 }
    $scores = @($items | ForEach-Object { [double]$_.Score })
    if ($scores.Count -eq 0) { return 0.0 }
    return [math]::Round((($scores | Measure-Object -Average).Average), 2)
}

# =============================================================================
# [13/18] QUALIFICATION D'UN MODÈLE
# =============================================================================

function Test-Model {
    param([Parameter(Mandatory)] [PSCustomObject]$Model)

    Write-Section "[MODEL] $($Model.Name)"
    Write-Forensic -Message "Début qualification : $($Model.Name)" -Level INFO

    $switchResult = Switch-OllamaModel -Model $Model.Name
    $results = New-Object System.Collections.Generic.List[object]

    # Warmup
    for ($w = 1; $w -le $WarmupRuns; $w++) {
        Write-Forensic -Message "Warmup $w/$WarmupRuns : $($Model.Name)" -Level INFO
        $warmupPayload = @{
            model      = $Model.Name
            prompt     = 'Réponds simplement READY.'
            stream     = $false
            keep_alive = $KeepAlive
            options    = @{
                temperature = 0
                num_predict = 16
                num_gpu     = $NumGpu
            }
        } | ConvertTo-Json -Depth 10

        try {
            Invoke-RestMethod -Uri "$OllamaHost/api/generate" -Method Post -ContentType 'application/json' -Body $warmupPayload -TimeoutSec 120 | Out-Null
        } catch {
            Write-Forensic -Message "Warmup échoué : $($_.Exception.Message)" -Level WARN
        }
    }

    # Exécution des tests principaux
    foreach ($test in $Tests) {
        $r = Invoke-ModelTest `
            -Model $Model.Name `
            -TestId $test.Id `
            -Category $test.Category `
            -Prompt $test.Prompt `
            -MaxTokens $test.MaxTokens `
            -ExpectedExact $test.ExpectedExact `
            -ExpectedContains $test.ExpectedContains `
            -ForbiddenPattern $test.ForbiddenPattern

        $r | Add-Member -NotePropertyName Model -NotePropertyValue $Model.Name -Force
        $results.Add($r)
    }

    # Tests de stabilité
    Write-Forensic -Message "Tests stabilité : $StabilityRuns exécutions." -Level INFO
    for ($s = 1; $s -le $StabilityRuns; $s++) {
        $stable = Invoke-ModelTest `
            -Model $Model.Name `
            -TestId "STAB-$s" `
            -Category 'Stability' `
            -Prompt "Réponds en français en une phrase concise :`nquel est le rôle principal d'un journal forensic ?" `
            -MaxTokens 180 `
            -ExpectedExact '' `
            -ExpectedContains 'journal|audit|forensic|trace' `
            -ForbiddenPattern ''

        $stable | Add-Member -NotePropertyName Model -NotePropertyValue $Model.Name -Force
        $results.Add($stable)
    }

    $allResults = @($results)
    $successful = @($allResults | Where-Object { $_.Success -eq $true })
    $failed     = @($allResults | Where-Object { $_.Success -ne $true })

    $avgScore = 0.0
    if ($allResults.Count -gt 0) {
        $avgScore = [math]::Round((($allResults | Measure-Object Score -Average).Average), 2)
    }

    $avgTPS = 0.0
    if ($successful.Count -gt 0) {
        $avgTPS = [math]::Round((($successful | Measure-Object TokensPerSecond -Average).Average), 3)
    }

    $avgLatency = 0.0
    if ($successful.Count -gt 0) {
        $avgLatency = [math]::Round((($successful | Measure-Object EvalDurationMs -Average).Average), 3)
    }

    $failureRate = 100.0
    if ($allResults.Count -gt 0) {
        $failureRate = [math]::Round(($failed.Count / $allResults.Count * 100), 2)
    }

    # Calcul des scores par catégorie
    $instructionScore = Get-CategoryScore -Results $allResults -Category 'Instruction'
    $reasoningScore   = Get-CategoryScore -Results $allResults -Category 'Reasoning'
    $codeScore        = Get-CategoryScore -Results $allResults -Category 'Code'
    $frenchScore      = Get-CategoryScore -Results $allResults -Category 'French'
    $structuredScore  = Get-CategoryScore -Results $allResults -Category 'Structured'
    $contextScore     = Get-CategoryScore -Results $allResults -Category 'Context'
    $generalScore     = Get-CategoryScore -Results $allResults -Category 'General'
    $robustnessScore  = Get-CategoryScore -Results $allResults -Category 'Robustness'
    $stabilityScore   = Get-CategoryScore -Results $allResults -Category 'Stability'

    $hardPassResults = @($allResults | Where-Object { $_.HardPass -eq $true })
    $hardPassRate    = if ($allResults.Count -gt 0) { [math]::Round(($hardPassResults.Count / $allResults.Count * 100), 2) } else { 0.0 }

    # CAPABILITY (Pondération indépendante de la vitesse)
    $capabilityScore = [math]::Round((
        ($instructionScore * 0.18) +
        ($reasoningScore   * 0.25) +
        ($codeScore        * 0.20) +
        ($frenchScore      * 0.10) +
        ($structuredScore  * 0.10) +
        ($contextScore     * 0.07) +
        ($generalScore     * 0.05) +
        ($robustnessScore  * 0.05)
    ), 2)

    # PERFORMANCE (40 TPS = référence)
    $performanceScore = [math]::Min(100, [math]::Round(($avgTPS / 40 * 100), 2))

    # RELIABILITY
    $reliabilityScore = [math]::Round((
        ($stabilityScore * 0.50) +
        ($hardPassRate   * 0.20) +
        ((100 - $failureRate) * 0.30)
    ), 2)

    # OVERALL SCORE
    $overallScore = [math]::Round((
        ($capabilityScore  * 0.60) +
        ($reliabilityScore * 0.25) +
        ($performanceScore * 0.15)
    ), 2)

    # Qualification contractuelle
    $qualified = (
        $overallScore       -ge $Thresholds.MinOverallScore -and
        $capabilityScore    -ge $Thresholds.MinCapabilityScore -and
        $reliabilityScore   -ge $Thresholds.MinReliabilityScore -and
        $instructionScore   -ge $Thresholds.MinInstructionScore -and
        $reasoningScore     -ge $Thresholds.MinReasoningScore -and
        $codeScore          -ge $Thresholds.MinCodeScore -and
        $frenchScore        -ge $Thresholds.MinFrenchScore -and
        $structuredScore    -ge $Thresholds.MinStructuredScore -and
        $contextScore       -ge $Thresholds.MinContextScore -and
        $stabilityScore     -ge $Thresholds.MinStabilityScore -and
        $failureRate        -le $Thresholds.MaxFailureRatePercent
    )

    $verdict = if ($qualified) { 'QUALIFIED' } elseif ($overallScore -ge 45) { 'PARTIAL' } else { 'FAIL' }

    $thinkingTests = @($allResults | Where-Object { $_.ThinkingChars -gt 0 })
    $thinkingPresenceRate = if ($allResults.Count -gt 0) { [math]::Round(($thinkingTests.Count / $allResults.Count * 100), 2) } else { 0.0 }

    $profile = [PSCustomObject]@{
        RunId                = $RunId
        Version              = $Version
        Model                = $Model.Name
        ParameterSize        = $Model.Parameter
        Quantization         = $Model.Quant
        Family               = $Model.Family
        Format               = $Model.Format
        SizeGB               = $Model.SizeGB
        CpuOnly              = $switchResult.CpuVerified
        Processor            = $switchResult.Processor
        SwitchMs             = $switchResult.LoadMs
        SwitchWallMs         = $switchResult.WallMs
        CapabilityScore      = $capabilityScore
        ReliabilityScore     = $reliabilityScore
        PerformanceScore     = $performanceScore
        OverallScore         = $overallScore
        InstructionScore     = $instructionScore
        ReasoningScore       = $reasoningScore
        CodeScore            = $codeScore
        FrenchScore          = $frenchScore
        StructuredScore      = $structuredScore
        ContextScore         = $contextScore
        GeneralScore         = $generalScore
        RobustnessScore      = $robustnessScore
        StabilityScore       = $stabilityScore
        HardPassRate         = $hardPassRate
        ThinkingPresenceRate = $thinkingPresenceRate
        AvgEvalLatencyMs     = $avgLatency
        AvgTokensPerSec      = $avgTPS
        FailureRate          = $failureRate
        TestsTotal           = $allResults.Count
        TestsSuccessful      = $successful.Count
        TestsFailed          = $failed.Count
        Verdict              = $verdict
        Tests                = $allResults
    }

    $profileLevel = if ($verdict -eq 'QUALIFIED') { 'PASS' } elseif ($verdict -eq 'PARTIAL') { 'WARN' } else { 'FAIL' }
    Write-Forensic -Message ("PROFILE {0} | CAP={1} | REL={2} | PERF={3} | OVERALL={4} | HARDPASS={5}% | THINKING={6}% | TPS={7} | FAIL={8}% | VERDICT={9}" -f `
        $Model.Name, $capabilityScore, $reliabilityScore, $performanceScore, $overallScore, `
        $hardPassRate, $thinkingPresenceRate, $avgTPS, $failureRate, $verdict) -Level $profileLevel

    return $profile
}

# =============================================================================
# [14/18] AFFICHAGE DE L'ENVIRONNEMENT
# =============================================================================

Write-Section "[0/18] E-ZZIO MODEL QUALIFICATION GATE v$Version"

Write-Forensic -Message "Version=$Version | RunId=$RunId" -Level INFO
Write-Forensic -Message "CPU=$CpuName | Cores=$CpuCores | Threads=$CpuThreads | RAM=${TotalRamGB}GB | Available=${AvailableRamGB}GB" -Level INFO
Write-Forensic -Message "MODE=CPU-ONLY | NUM_GPU=$NumGpu | SINGLE_MODEL_ONLY=TRUE" -Level INFO
Write-Forensic -Message "OllamaHost=$OllamaHost" -Level INFO

# =============================================================================
# [15/18] VÉRIFICATION DE LA DISPONIBILITÉ D'OLLAMA
# =============================================================================

Write-Section "[1/18] OLLAMA AVAILABILITY"

$ollamaCommand = Get-Command ollama -ErrorAction SilentlyContinue
if ($null -eq $ollamaCommand) {
    Write-Forensic -Message 'ollama.exe introuvable dans PATH.' -Level FAIL
    throw 'OLLAMA_NOT_FOUND'
}
Write-Forensic -Message "Ollama executable : $($ollamaCommand.Source)" -Level PASS

if (-not (Test-OllamaAvailable)) {
    Write-Forensic -Message "Ollama API inaccessible sur $OllamaHost." -Level FAIL
    throw 'OLLAMA_API_UNAVAILABLE'
}
Write-Forensic -Message 'Ollama API disponible.' -Level PASS

# =============================================================================
# [16/18] INVENTAIRE ET FILTRAGE DES MODÈLES
# =============================================================================

Write-Section "[2/18] MODEL INVENTORY"

$allModels = @(Get-OllamaModels)
if ($allModels.Count -eq 0) {
    Write-Forensic -Message 'Aucun modèle Ollama détecté.' -Level FAIL
    throw 'NO_MODELS'
}

# Séparation des modèles génératifs et vectoriels
$models            = @($allModels | Where-Object { -not $_.IsEmbedding })
$embeddingProfiles = @($allModels | Where-Object { $_.IsEmbedding })

if ($MaxModels -gt 0 -and $models.Count -gt $MaxModels) {
    $models = @($models | Select-Object -First $MaxModels)
}

Write-Forensic -Message "$($models.Count) modèle(s) génératif(s) à qualifier, $($embeddingProfiles.Count) modèle(s) d'embedding ignoré(s)." -Level PASS

foreach ($m in $models) {
    Write-Host ('  - {0} | {1} GB | params={2} | quant={3} | family={4}' -f `
        $m.Name, $m.SizeGB, $m.Parameter, $m.Quant, $m.Family)
}

# =============================================================================
# [17/18] PURGE INITIALE DU RUNTIME
# =============================================================================

Write-Section "[3/18] INITIAL RUNTIME CLEANUP"

$initial = @(Get-RunningModelNames)
Write-Forensic -Message "Etat initial : $($initial.Count) modèle(s) actif(s)." -Level INFO

if ($initial.Count -gt 0) {
    Write-Host "`nModèle(s) actuellement actif(s) :"
    foreach ($name in $initial) { Write-Host "  * $name" }
}

Clear-OllamaRuntime
Write-Forensic -Message 'PRECHECK OK : 0 modèle actif.' -Level PASS

# =============================================================================
# [18/18] EXÉCUTION DE LA QUALIFICATION & EXPORTS
# =============================================================================

Write-Section "[4/18] QUALIFICATION BATTERY"

$profiles    = New-Object System.Collections.Generic.List[object]
$totalModels = $models.Count
$modelIndex  = 0

foreach ($model in $models) {
    $modelIndex++
    Write-Host "`n>>> MODÈLE $modelIndex/$totalModels : $($model.Name)" -ForegroundColor Cyan
    Write-Forensic -Message "START MODEL $modelIndex/$totalModels : $($model.Name)" -Level SWITCH

    try {
        $profile = Test-Model -Model $model
        $profiles.Add($profile)
    } catch {
        Write-Forensic -Message "Qualification interrompue pour $($model.Name) : $($_.Exception.Message)" -Level FAIL
        $profiles.Add([PSCustomObject]@{
            RunId                = $RunId
            Version              = $Version
            Model                = $model.Name
            ParameterSize        = $model.Parameter
            Quantization         = $model.Quant
            Family               = $model.Family
            Format               = $model.Format
            SizeGB               = $model.SizeGB
            CpuOnly              = $false
            Processor            = 'UNKNOWN'
            SwitchMs             = 0
            SwitchWallMs         = 0
            CapabilityScore      = 0
            ReliabilityScore     = 0
            PerformanceScore     = 0
            OverallScore         = 0
            InstructionScore     = 0
            ReasoningScore       = 0
            CodeScore            = 0
            FrenchScore          = 0
            StructuredScore      = 0
            ContextScore         = 0
            GeneralScore         = 0
            RobustnessScore      = 0
            StabilityScore       = 0
            HardPassRate         = 0
            ThinkingPresenceRate = 0
            AvgEvalLatencyMs     = 0
            AvgTokensPerSec      = 0
            FailureRate          = 100
            TestsTotal           = 0
            TestsSuccessful      = 0
            TestsFailed          = 0
            Verdict              = 'FAIL'
            FatalError           = $_.Exception.Message
            Tests                = @()
        })
    } finally {
        $active = @(Get-RunningModelNames)
        if ($active.Count -gt 1) { throw 'MULTIPLE_MODELS_AFTER_TEST' }
        if ($active.Count -eq 1) {
            $released = Unload-OllamaModel -Model $active[0]
            if (-not $released) { throw 'POST_MODEL_UNLOAD_FAILURE' }
        }
        if (-not (Wait-RuntimeEmpty)) { throw 'POST_MODEL_RUNTIME_NOT_EMPTY' }
        Write-Forensic -Message "Modèle $($model.Name) complètement libéré du runtime." -Level PASS
    }
}

# --- CLASSEMENT FINAL ---
Write-Section "[5/18] FINAL RANKING"

$ranking = @($profiles | Sort-Object -Property OverallScore -Descending)
$rank = 0

foreach ($profile in $ranking) {
    $rank++
    Write-Host "`n#$rank  $($profile.Model)" -ForegroundColor White
    Write-Host "     OVERALL      : $($profile.OverallScore)/100"
    Write-Host "     CAPABILITY   : $($profile.CapabilityScore)/100"
    Write-Host "     RELIABILITY  : $($profile.ReliabilityScore)/100"
    Write-Host "     PERFORMANCE  : $($profile.PerformanceScore)/100"
    Write-Host "     REASONING    : $($profile.ReasoningScore)/100"
    Write-Host "     CODE         : $($profile.CodeScore)/100"
    Write-Host "     INSTRUCTION  : $($profile.InstructionScore)/100"
    Write-Host "     FRENCH       : $($profile.FrenchScore)/100"
    Write-Host "     HARD PASS    : $($profile.HardPassRate)%"
    Write-Host "     THINKING     : $($profile.ThinkingPresenceRate)%"
    Write-Host "     AVG TPS      : $($profile.AvgTokensPerSec)"
    Write-Host "     FAILURE      : $($profile.FailureRate)%"
    Write-Host "     VERDICT      : $($profile.Verdict)"
}

# --- EXPORT JSON ---
$export = [PSCustomObject]@{
    Schema          = 'EZZIO-MODEL-QUALIFICATION-4.3.3'
    RunId           = $RunId
    Timestamp       = (Get-Date).ToString('o')
    Environment     = [PSCustomObject]@{
        CPU              = $CpuName
        Cores            = $CpuCores
        Threads          = $CpuThreads
        RAM_GB           = $TotalRamGB
        Available_RAM_GB = $AvailableRamGB
        GPU_Mode         = 'DISABLED'
        NumGPU           = $NumGpu
        OllamaHost       = $OllamaHost
    }
    ModelsQualified = $profiles.Count
    Ranking         = $ranking
    Profiles        = $profiles
}
$export | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $JsonPath -Encoding UTF8
Write-Forensic -Message "JSON exporté : $JsonPath" -Level PASS

# --- EXPORT CSV ---
$profiles | Select-Object RunId, Version, Model, ParameterSize, Quantization, Family, Format, SizeGB, `
    CpuOnly, Processor, SwitchMs, OverallScore, CapabilityScore, ReliabilityScore, PerformanceScore, `
    InstructionScore, ReasoningScore, CodeScore, FrenchScore, StructuredScore, ContextScore, `
    HardPassRate, ThinkingPresenceRate, AvgEvalLatencyMs, AvgTokensPerSec, FailureRate, Verdict |
    Export-Csv -LiteralPath $CsvPath -NoTypeInformation -Encoding UTF8
Write-Forensic -Message "CSV exporté : $CsvPath" -Level PASS

# --- RAPPORT TEXTE ---
$best = $ranking | Select-Object -First 1
$summary = @"
==================================================================================
E-ZZIO — MODEL QUALIFICATION GATE v$Version
==================================================================================
RUN ID          : $RunId
CPU             : $CpuName ($CpuCores c / $CpuThreads t)
RAM             : $TotalRamGB GB (Disponible: $AvailableRamGB GB)
GPU MODE        : DISABLED (num_gpu = 0)
OLLAMA HOST     : $OllamaHost

MODELS
------
QUALIFIED : $(@($profiles | Where-Object { $_.Verdict -eq 'QUALIFIED' }).Count)
PARTIAL   : $(@($profiles | Where-Object { $_.Verdict -eq 'PARTIAL' }).Count)
FAIL      : $(@($profiles | Where-Object { $_.Verdict -eq 'FAIL' }).Count)
TOTAL     : $($profiles.Count)

BEST MODEL
----------
NOM         : $(if ($best) { $best.Model } else { 'NONE' })
OVERALL     : $(if ($best) { $best.OverallScore } else { 0 })/100
CAPABILITY  : $(if ($best) { $best.CapabilityScore } else { 0 })/100
RELIABILITY : $(if ($best) { $best.ReliabilityScore } else { 0 })/100
AVG TPS     : $(if ($best) { $best.AvgTokensPerSec } else { 0 })
VERDICT     : $(if ($best) { $best.Verdict } else { 'NONE' })
==================================================================================
"@
Set-Content -LiteralPath $SummaryPath -Value $summary -Encoding UTF8
Write-Forensic -Message "Summary exporté : $SummaryPath" -Level PASS

# --- PURGE FINALE ---
Clear-OllamaRuntime
Write-Forensic -Message 'Runtime Ollama propre : 0 modèle actif.' -Level PASS
Write-Host "`n=================================================================================="
Write-Host 'EXECUTION TERMINEE — SINGLE-MODEL RUNTIME CONFIRMED CLEAN' -ForegroundColor Green
Write-Host '=================================================================================='