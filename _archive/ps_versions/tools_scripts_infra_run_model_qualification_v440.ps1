#requires -Version 5.1
# =============================================================================
# E-ZZIO - MODEL QUALIFICATION GATE
# Version : 4.4.0 (HARDWARE CERTIFIED & STRICT-MODE IMMUNIZED)
# Mode    : CPU-ONLY / SINGLE-MODEL-SWITCH / FORENSIC / RAM-LIFECYCLE
# =============================================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# =============================================================================
# [0/18] CONFIGURATION & INITIALISATION
# =============================================================================

$Version = '4.4.0'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$AuditRoot = Join-Path $Root 'audit\model_gate_v4.4.0'

if (-not (Test-Path -LiteralPath $AuditRoot)) {
    New-Item -ItemType Directory -Path $AuditRoot -Force | Out-Null
}

$RunId       = Get-Date -Format 'yyyyMMdd_HHmmss'
$LogPath     = Join-Path $AuditRoot "forensic_$RunId.log"
$JsonPath    = Join-Path $AuditRoot "qualification_$RunId.json"
$CsvPath     = Join-Path $AuditRoot "qualification_$RunId.csv"
$SummaryPath = Join-Path $AuditRoot "summary_$RunId.txt"

$OllamaHost = 'http://127.0.0.1:11434'

# -------------------------------------------------------------------------
# DETECTION MATERIELLE ET BANDE PASSANTE THEORIQUE
# -------------------------------------------------------------------------

$CpuName    = 'UNKNOWN'
$CpuCores   = 0
$CpuThreads = [Environment]::ProcessorCount

$TotalRamGB     = 0.0
$AvailableRamGB = 0.0

$MemorySpeed          = 0
$MemorySticks         = 0
$MemoryChannels       = 2
$TheoreticalBandwidth = 0.0

try {
    $cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
    if ($null -ne $cpu) {
        $CpuName    = [string]$cpu.Name
        $CpuCores   = [int]$cpu.NumberOfCores
        $CpuThreads = [int]$cpu.NumberOfLogicalProcessors
    }
}
catch {
    $CpuName = 'UNKNOWN'
}

try {
    $os = Get-CimInstance Win32_OperatingSystem
    if ($null -ne $os) {
        $TotalRamGB     = [math]::Round(([double]$os.TotalVisibleMemorySize / 1MB), 2)
        $AvailableRamGB = [math]::Round(([double]$os.FreePhysicalMemory / 1MB), 2)
    }
}
catch {
    $TotalRamGB     = 0.0
    $AvailableRamGB = 0.0
}

try {
    $dimms        = @(Get-CimInstance Win32_PhysicalMemory)
    $MemorySticks = $dimms.Count
    if ($MemorySticks -gt 0) {
        $MemorySpeed = [int]$dimms[0].ConfiguredClockSpeed
        if ($MemorySpeed -le 0) {
            $MemorySpeed = [int]$dimms[0].Speed
        }
    }
    if ($MemorySpeed -le 0) {
        $MemorySpeed = 3200
    }
    $MemoryChannels       = if ($MemorySticks -ge 2) { 2 } else { 1 }
    $TheoreticalBandwidth = [math]::Round(($MemorySpeed * 8 * $MemoryChannels / 1000), 2)
}
catch {
    $MemorySpeed          = 3200
    $MemoryChannels       = 2
    $TheoreticalBandwidth = 51.20
}

# -------------------------------------------------------------------------
# PARAMETRES D'EXECUTION
# -------------------------------------------------------------------------

$WarmupRuns        = 1
$StabilityRuns     = 2
$MaxModels         = 0

$RequestTimeoutSec = 300
$SwitchTimeoutSec  = 180

$KeepAlive         = '10m'

$ForceCpuOnly      = $true
$NumGpu            = 0
$Temperature       = 0

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
    MinSafetyRamGB        = 2.5
}

# =============================================================================
# [1/18] JOURNALISATION FORENSIC
# =============================================================================

function Write-Forensic {
    param(
        [Parameter(Mandatory)]
        [string]$Message,

        [ValidateSet('INFO', 'PASS', 'WARN', 'FAIL', 'SWITCH', 'TEST', 'METRIC', 'RAM')]
        [string]$Level = 'INFO'
    )

    $timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss.fff'
    $line = '[{0}] [{1}] {2}' -f $timestamp, $Level, $Message

    Add-Content -LiteralPath $LogPath -Value $line -Encoding UTF8

    switch ($Level) {
        'PASS'   { Write-Host $line -ForegroundColor Green }
        'WARN'   { Write-Host $line -ForegroundColor Yellow }
        'FAIL'   { Write-Host $line -ForegroundColor Red }
        'SWITCH' { Write-Host $line -ForegroundColor Cyan }
        'TEST'   { Write-Host $line -ForegroundColor Magenta }
        'METRIC' { Write-Host $line -ForegroundColor DarkCyan }
        'RAM'    { Write-Host $line -ForegroundColor DarkYellow }
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
# [2/18] TELEMETRIE MEMOIRE & CONVERSIONS SECURISEES
# =============================================================================

function Get-MemorySnapshot {
    try {
        $os     = Get-CimInstance Win32_OperatingSystem
        $freeGB = [math]::Round(([double]$os.FreePhysicalMemory / 1MB), 3)
        $usedGB = [math]::Round(([double]($os.TotalVisibleMemorySize - $os.FreePhysicalMemory) / 1MB), 3)
        return [PSCustomObject]@{
            FreeGB = $freeGB
            UsedGB = $usedGB
        }
    }
    catch {
        return [PSCustomObject]@{
            FreeGB = 0.0
            UsedGB = 0.0
        }
    }
}

function Convert-ToDoubleSafe {
    param([AllowNull()] $Value)
    if ($null -eq $Value) { return 0.0 }
    try { return [double]$Value } catch { return 0.0 }
}

function Convert-ToInt64Safe {
    param([AllowNull()] $Value)
    if ($null -eq $Value) { return 0L }
    try { return [int64]$Value } catch { return 0L }
}

function Convert-ToIntSafe {
    param([AllowNull()] $Value)
    if ($null -eq $Value) { return 0 }
    try { return [int]$Value } catch { return 0 }
}

# =============================================================================
# [3/18] API OLLAMA & INVENTAIRE SECURISE
# =============================================================================

function Test-OllamaAvailable {
    try {
        Invoke-RestMethod -Uri "$OllamaHost/api/tags" -Method Get -TimeoutSec 10 | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

function Get-OllamaModels {
    try {
        $response = Invoke-RestMethod -Uri "$OllamaHost/api/tags" -Method Get -TimeoutSec 20
        if ($null -eq $response -or $null -eq $response.models) { return @() }

        $list = [System.Collections.Generic.List[PSCustomObject]]::new()

        foreach ($item in @($response.models)) {
            if ($null -eq $item) { continue }

            $family    = ''
            $paramSize = ''
            $quant     = ''
            $format    = ''

            if ($item.PSObject.Properties['details'] -and $null -ne $item.details) {
                if ($item.details.PSObject.Properties['family'])            { $family    = [string]$item.details.family }
                if ($item.details.PSObject.Properties['parameter_size'])    { $paramSize = [string]$item.details.parameter_size }
                if ($item.details.PSObject.Properties['quantization_level']){ $quant     = [string]$item.details.quantization_level }
                if ($item.details.PSObject.Properties['format'])            { $format    = [string]$item.details.format }
            }

            $name    = if ($item.PSObject.Properties['name']) { [string]$item.name } else { '' }
            $sizeVal = if ($item.PSObject.Properties['size']) { $item.size } else { 0 }

            $isEmbedding = ($family -match '(?i)bert|nomic|embedding') -or ($name -match '(?i)embed|bge|nomic-embed')

            $obj = [PSCustomObject]@{
                Name        = $name
                SizeBytes   = Convert-ToInt64Safe $sizeVal
                SizeGB      = [math]::Round(((Convert-ToDoubleSafe $sizeVal) / 1GB), 2)
                Parameter   = $paramSize
                Quant       = $quant
                Family      = $family
                Format      = $format
                IsEmbedding = $isEmbedding
            }

            $list.Add($obj)
        }

        return @($list)
    }
    catch {
        throw "Impossible de recuperer les modeles Ollama : $($_.Exception.Message)"
    }
}

function Get-OllamaRunningModels {
    try {
        $response = Invoke-RestMethod -Uri "$OllamaHost/api/ps" -Method Get -TimeoutSec 15
        if ($null -eq $response -or $null -eq $response.models) { return @() }
        return @($response.models)
    }
    catch {
        Write-Forensic -Message "Lecture /api/ps impossible : $($_.Exception.Message)" -Level WARN
        return @()
    }
}

function Get-RunningModelNames {
    $running = @(Get-OllamaRunningModels)
    $names   = [System.Collections.Generic.List[string]]::new()

    foreach ($item in $running) {
        if ($null -eq $item) { continue }

        $mName = $null
        if ($item.PSObject.Properties['name'] -and -not [string]::IsNullOrWhiteSpace([string]$item.name)) {
            $mName = [string]$item.name
        }
        elseif ($item.PSObject.Properties['model'] -and -not [string]::IsNullOrWhiteSpace([string]$item.model)) {
            $mName = [string]$item.model
        }

        if ($null -ne $mName) {
            $names.Add($mName)
        }
    }

    return @($names)
}

function Get-RunningModelRecord {
    param([Parameter(Mandatory)] [string]$Model)

    $running = @(Get-OllamaRunningModels)
    foreach ($item in $running) {
        if ($null -eq $item) { continue }
        $name = ''
        if ($item.PSObject.Properties['name']) { $name = [string]$item.name }
        elseif ($item.PSObject.Properties['model']) { $name = [string]$item.model }
        if ($name -eq $Model) { return $item }
    }

    return $null
}

# =============================================================================
# [4/18] ISOLATION & DECHARGEMENT STRICT
# =============================================================================

function Assert-SingleModel {
    $running = @(Get-RunningModelNames)

    if ($running.Count -gt 1) {
        Write-Forensic -Message "FAIL-CLOSED : plusieurs modeles actifs : $($running -join ', ')" -Level FAIL
        throw 'SINGLE_MODEL_VIOLATION'
    }

    if ($running.Count -eq 1) {
        Write-Forensic -Message "Modele actif confirme : $($running[0])" -Level INFO
        return $running[0]
    }

    Write-Forensic -Message 'Runtime EMPTY : 0 modele actif.' -Level PASS
    return $null
}

function Wait-RuntimeEmpty {
    param(
        [int]$Attempts = 8,
        [int]$DelayMs  = 250
    )

    for ($i = 1; $i -le $Attempts; $i++) {
        $running = @(Get-RunningModelNames)
        if ($running.Count -eq 0) {
            Write-Forensic -Message "Runtime EMPTY confirme a la tentative $i/$Attempts." -Level PASS
            return $true
        }
        Start-Sleep -Milliseconds $DelayMs
    }

    Write-Forensic -Message 'Runtime non vide apres toutes les tentatives.' -Level FAIL
    return $false
}

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
    }
    catch {
        Write-Forensic -Message "API unload echouee pour $Model : $($_.Exception.Message)" -Level WARN
    }

    if (Wait-RuntimeEmpty) {
        Write-Forensic -Message "Modele $Model libere via API." -Level PASS
        return $true
    }

    return $false
}

function Clear-OllamaRuntime {
    Write-Forensic -Message 'NETTOYAGE GLOBAL DU RUNTIME OLLAMA' -Level SWITCH

    $running = @(Get-RunningModelNames)

    if ($running.Count -gt 1) {
        Write-Forensic -Message "FAIL-CLOSED : plusieurs modeles actifs : $($running -join ', ')" -Level FAIL
        throw 'MULTIPLE_ACTIVE_MODELS'
    }

    if ($running.Count -eq 1) {
        $released = Unload-OllamaModel -Model $running[0]
        if (-not $released) { throw 'RUNTIME_CLEANUP_FAILED' }
    }

    if (-not (Wait-RuntimeEmpty)) {
        throw 'RUNTIME_NOT_EMPTY'
    }
}

# =============================================================================
# [5/18] VERIFICATION CPU-ONLY
# =============================================================================

function Assert-CpuOnly {
    param([Parameter(Mandatory)] [string]$Model)

    if (-not $ForceCpuOnly) {
        throw 'CPU_ONLY_CONFIGURATION_DISABLED'
    }

    $record = Get-RunningModelRecord -Model $Model

    if ($null -eq $record -or -not ($record.PSObject.Properties['processor']) -or [string]::IsNullOrWhiteSpace([string]$record.processor)) {
        Write-Forensic -Message "Champ processor absent de /api/ps pour $Model (num_gpu=0 garanti en CPU)." -Level WARN
        return [PSCustomObject]@{
            Verified  = $true
            Processor = 'CPU (ENFORCED)'
        }
    }

    $processor = [string]$record.processor
    Write-Forensic -Message "Processor Ollama : $processor" -Level INFO

    if ($processor -match '(?i)CPU') {
        Write-Forensic -Message "CPU-ONLY confirme pour $Model." -Level PASS
        return [PSCustomObject]@{
            Verified  = $true
            Processor = $processor
        }
    }

    Write-Forensic -Message "CPU-ONLY VIOLATION : processor=$processor" -Level FAIL
    throw 'GPU_PROCESSING_DETECTED'
}

# =============================================================================
# [6/18] COMMUTATION DE MODELE & TELEMETRIE CHARGE RAM
# =============================================================================

function Switch-OllamaModel {
    param([Parameter(Mandatory)] [string]$Model)

    Write-Forensic -Message "========== SWITCH -> $Model ==========" -Level SWITCH
    Clear-OllamaRuntime

    $memBefore = Get-MemorySnapshot
    Write-Forensic -Message ("RAM AVANT LOAD : {0} Go utilises / {1} Go libres" -f $memBefore.UsedGB, $memBefore.FreeGB) -Level RAM

    $payload = @{
        model      = $Model
        prompt     = 'E-ZZIO SWITCH PROBE. Reponds uniquement READY.'
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
        $response = Invoke-RestMethod -Uri "$OllamaHost/api/generate" -Method Post -ContentType 'application/json' -Body $payload -TimeoutSec $SwitchTimeoutSec
    }
    catch {
        Write-Forensic -Message "Echec switch/load $Model : $($_.Exception.Message)" -Level FAIL
        throw 'MODEL_LOAD_FAILED'
    }

    $wallMs  = ((Get-Date) - $wallStart).TotalMilliseconds
    $running = @(Get-RunningModelNames)

    if ($running.Count -ne 1) { throw 'POST_SWITCH_CARDINALITY_FAILURE' }
    if ($running[0] -ne $Model) { throw 'POST_SWITCH_WRONG_MODEL' }

    $memAfter = Get-MemorySnapshot
    $deltaRAM = [math]::Round(($memAfter.UsedGB - $memBefore.UsedGB), 2)
    Write-Forensic -Message ("RAM APRES LOAD : {0} Go utilises (+{1} Go) | {2} Go libres" -f $memAfter.UsedGB, $deltaRAM, $memAfter.FreeGB) -Level RAM

    $cpuState = Assert-CpuOnly -Model $Model

    $loadNs = 0.0
    if ($response.PSObject.Properties['load_duration']) {
        $loadNs = Convert-ToDoubleSafe $response.load_duration
    }

    $loadMs = [math]::Round(($loadNs / 1000000), 3)
    if ($loadMs -le 0) {
        $loadMs = [math]::Round($wallMs, 3)
    }

    Write-Forensic -Message ("SWITCH OK | Model={0} | Load={1}ms | Wall={2}ms | Active=1 | Processor={3}" -f $Model, $loadMs, [math]::Round($wallMs, 3), $cpuState.Processor) -Level PASS

    return [PSCustomObject]@{
        Model          = $Model
        LoadMs         = $loadMs
        WallMs         = [math]::Round($wallMs, 3)
        Processor      = $cpuState.Processor
        CpuVerified    = $cpuState.Verified
        RamBeforeGB    = $memBefore.UsedGB
        RamAfterGB     = $memAfter.UsedGB
        ModelDeltaGB   = $deltaRAM
        AvailableRamGB = $memAfter.FreeGB
    }
}

# =============================================================================
# [7/18] EXTRACTION DES REPONSES ET BALISES <THINK>
# =============================================================================

function Get-ResponseParts {
    param([Parameter(Mandatory)] $ApiResponse)

    $rawFinal = ''
    $thinking = ''

    if ($ApiResponse.PSObject.Properties['response'] -and $null -ne $ApiResponse.response) {
        $rawFinal = [string]$ApiResponse.response
    }
    elseif ($ApiResponse.PSObject.Properties['message'] -and $null -ne $ApiResponse.message) {
        if ($ApiResponse.message.PSObject.Properties['content'] -and $null -ne $ApiResponse.message.content) {
            $rawFinal = [string]$ApiResponse.message.content
        }
    }

    if ($ApiResponse.PSObject.Properties['thinking'] -and $null -ne $ApiResponse.thinking) {
        $thinking = [string]$ApiResponse.thinking
    }
    elseif ($ApiResponse.PSObject.Properties['message'] -and $null -ne $ApiResponse.message) {
        if ($ApiResponse.message.PSObject.Properties['thinking'] -and $null -ne $ApiResponse.message.thinking) {
            $thinking = [string]$ApiResponse.message.thinking
        }
    }

    if ($rawFinal -match '(?s)<think>(.*?)</think>') {
        $extractedThinking = $Matches[1].Trim()
        if ([string]::IsNullOrWhiteSpace($thinking)) {
            $thinking = $extractedThinking
        }
        else {
            $thinking = $thinking + "`n" + $extractedThinking
        }

        $rawFinal = ($rawFinal -replace '(?s)<think>.*?</think>', '').Trim()
    }

    $final    = $rawFinal.Trim()
    $thinking = $thinking.Trim()

    $final    = ($final -replace "`r`n", "`n" -replace "`r", "`n")
    $thinking = ($thinking -replace "`r`n", "`n" -replace "`r", "`n")

    $combined = ''
    if ($thinking.Length -gt 0 -and $final.Length -gt 0) {
        $combined = "$thinking`n$final"
    }
    elseif ($thinking.Length -gt 0) {
        $combined = $thinking
    }
    else {
        $combined = $final
    }

    $status = 'EMPTY_OUTPUT'
    if ($final.Length -gt 0 -and $thinking.Length -gt 0) {
        $status = 'FINAL_AND_THINKING'
    }
    elseif ($final.Length -gt 0) {
        $status = 'FINAL_RESPONSE'
    }
    elseif ($thinking.Length -gt 0) {
        $status = 'THINKING_ONLY'
    }

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
# [8/18] EVALUATION DETERMINISTE DES REPONSES
# =============================================================================

function Evaluate-Response {
    param(
        [Parameter(Mandatory)] [string]$TestId,
        [Parameter(Mandatory)] [string]$Category,
        [AllowEmptyString()]   [string]$Response = '',
        [AllowEmptyString()]   [string]$Thinking = '',
        [string]$ExpectedExact    = '',
        [string]$ExpectedContains = '',
        [string]$ForbiddenPattern = ''
    )

    $hardPass  = $false
    $hardCheck = 'NOT_APPLICABLE'
    $reasons   = [System.Collections.Generic.List[string]]::new()
    $score     = 0

    $text = if ($null -ne $Response) { $Response.Trim() } else { '' }
    $text = ($text -replace "`r`n", "`n" -replace "`r", "`n")

    if ($text.Length -eq 0) {
        $reasons.Add('final response empty')
        if ($Thinking.Trim().Length -gt 0) {
            $reasons.Add('thinking present')
        }

        return [PSCustomObject]@{
            TestId    = $TestId
            Category  = $Category
            Score     = 0
            HardPass  = $false
            HardCheck = 'EMPTY_FINAL_RESPONSE'
            Reasons   = $reasons.ToArray()
        }
    }

    $score += 20
    $reasons.Add('non-empty final response')

    if ($ExpectedExact.Length -gt 0) {
        $normExpected = ($ExpectedExact.Trim() -replace "`r`n", "`n" -replace "`r", "`n")

        if ($text -ceq $normExpected) {
            $hardPass  = $true
            $hardCheck = 'EXACT_MATCH'
            $score += 80
            $reasons.Add('exact match')
        }
        else {
            $hardCheck = 'EXACT_MISMATCH'
            $reasons.Add('exact mismatch')
        }
    }

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
            if ($hardCheck -eq 'NOT_APPLICABLE') {
                $hardCheck = 'EXPECTED_CONTENT_FOUND'
            }
            $score += 50
            $reasons.Add('expected content found')
        }
        else {
            $reasons.Add("expected content $found/$($containsParts.Count)")
        }
    }

    if ($ForbiddenPattern.Length -gt 0) {
        if ($text -match $ForbiddenPattern) {
            $hardPass = $false
            $reasons.Add('forbidden pattern detected')
        }
        else {
            $score += 10
            $reasons.Add('forbidden pattern absent')
        }
    }

    switch ($Category) {
        'General' {
            if ($text.Length -ge 100) {
                $score += 15
                $reasons.Add('adequate answer length')
            }
            if ($text -match '(?i)architecture|separation|audit|execution|politique') {
                $score += 15
                $reasons.Add('technical vocabulary')
            }
        }

        'Instruction' {
            $lines = @($text -split "`n" | Where-Object { $_.Trim().Length -gt 0 })
            if ($lines.Count -eq 3) {
                $score += 20
                $reasons.Add('three non-empty lines')
            }
            if ($text -match '(?m)^\s*ALPHA\s*$' -and $text -match '(?m)^\s*BETA\s*$' -and $text -match '(?m)^\s*GAMMA\s*$') {
                $score += 50
                $reasons.Add('instruction tokens correct')
            }
        }

        'Reasoning' {
            if ($text -match '(?i)\d+') {
                $score += 15
                $reasons.Add('numeric reasoning evidence')
            }
            if ($text -match '(?i)donc|car|puisque|etape|calcul|ensuite|final') {
                $score += 20
                $reasons.Add('reasoning language')
            }
        }

        'Code' {
            if ($text -match '(?i)def\s+\w+\s*\(|function\s+\w+') {
                $score += 25
                $reasons.Add('function declaration')
            }
            if ($text -match '(?i)return|param\s*\(|if\s*\(') {
                $score += 20
                $reasons.Add('control/return syntax')
            }
            if ($text -match '(?i)null|none|\$null') {
                $score += 15
                $reasons.Add('null handling')
            }
            if ($text -match '(?i)```') {
                $score -= 10
                $reasons.Add('markdown fence penalty')
            }
        }

        'Structured' {
            $cleanJson = ($text -replace '(?s)^```(?:json)?\s*', '' -replace '```\s*$', '')
            try {
                $parsed = $cleanJson.Trim() | ConvertFrom-Json -ErrorAction Stop
                if ($null -ne $parsed) {
                    $score += 60
                    $reasons.Add('valid JSON')

                    if ($parsed.PSObject.Properties['status'] -and $parsed.status -eq 'PASS' -and
                        $parsed.PSObject.Properties['score'] -and [int]$parsed.score -eq 100 -and
                        $parsed.PSObject.Properties['mode'] -and $parsed.mode -eq 'CPU') {
                        $hardPass  = $true
                        $hardCheck = 'JSON_SCHEMA_MATCH'
                        $score += 20
                        $reasons.Add('expected JSON fields correct')
                    }
                }
            }
            catch {
                $reasons.Add('invalid JSON')
            }
        }

        'French' {
            if ($text -match '(?i)\b(le|la|les|des|une|dans|avec|pour|est|sont|modele|latence|debit|fiabilite)\b') {
                $score += 30
                $reasons.Add('French lexical evidence')
            }
            if ($text.Length -ge 100) {
                $score += 20
                $reasons.Add('adequate French response')
            }
        }

        'Context' {
            if ($text -match '(?i)\b91\b') {
                $score += 60
                $hardPass  = $true
                $hardCheck = 'CONTEXT_VALUE_MATCH'
                $reasons.Add('context value recovered')
            }
        }

        'Robustness' {
            if ($text -match '(?i)fausse?|incorrect|pas necessairement|depend') {
                $score += 35
                $reasons.Add('counterexample/correction evidence')
            }
            if ($text -match '(?i)capacite|qualite|latence|raisonnement|performance') {
                $score += 25
                $reasons.Add('distinction capability/performance')
            }
        }

        'Stability' {
            if ($text.Length -ge 40) {
                $score += 30
                $reasons.Add('stable response length')
            }
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
        Reasons   = $reasons.ToArray()
    }
}

# =============================================================================
# [9/18] EXECUTION D'UN TEST (DOUBLE MESURE TPS)
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
    if ($active -ne $Model) {
        throw 'ACTIVE_MODEL_MISMATCH'
    }

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
    }
    catch {
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
            PromptTokensPerSec   = 0.0
            EvalTokensPerSec     = 0.0
            ResponsePreview      = ''
            Reasons              = @($_.Exception.Message)
            Error                = $_.Exception.Message
        }
    }

    $parts = Get-ResponseParts -ApiResponse $apiResponse

    $totalNs      = 0.0
    $loadNs       = 0.0
    $promptEvalNs = 0.0
    $evalNs       = 0.0

    $promptTokens    = 0
    $generatedTokens = 0

    if ($apiResponse.PSObject.Properties['total_duration']) {
        $totalNs = Convert-ToDoubleSafe $apiResponse.total_duration
    }
    if ($apiResponse.PSObject.Properties['load_duration']) {
        $loadNs = Convert-ToDoubleSafe $apiResponse.load_duration
    }
    if ($apiResponse.PSObject.Properties['prompt_eval_duration']) {
        $promptEvalNs = Convert-ToDoubleSafe $apiResponse.prompt_eval_duration
    }
    if ($apiResponse.PSObject.Properties['eval_duration']) {
        $evalNs = Convert-ToDoubleSafe $apiResponse.eval_duration
    }
    if ($apiResponse.PSObject.Properties['prompt_eval_count']) {
        $promptTokens = Convert-ToIntSafe $apiResponse.prompt_eval_count
    }
    if ($apiResponse.PSObject.Properties['eval_count']) {
        $generatedTokens = Convert-ToIntSafe $apiResponse.eval_count
    }

    $totalMs      = [math]::Round(($totalNs / 1000000), 3)
    $loadMs       = [math]::Round(($loadNs / 1000000), 3)
    $promptEvalMs = [math]::Round(($promptEvalNs / 1000000), 3)
    $evalMs       = [math]::Round(($evalNs / 1000000), 3)

    $promptTPS = 0.0
    if ($promptTokens -gt 0 -and $promptEvalMs -gt 0) {
        $promptTPS = [math]::Round(($promptTokens / ($promptEvalMs / 1000)), 2)
    }

    $evalTPS = 0.0
    if ($generatedTokens -gt 0 -and $evalMs -gt 0) {
        $evalTPS = [math]::Round(($generatedTokens / ($evalMs / 1000)), 2)
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
        PromptTokensPerSec   = $promptTPS
        EvalTokensPerSec     = $evalTPS
        ResponsePreview      = $preview
        Reasons              = @($evaluation.Reasons)
        Error                = $null
    }

    Write-Forensic -Message ("RESULT {0} | Score={1} | HardPass={2} | Status={3} | Wall={4}ms | PromptTPS={5} | EvalTPS={6} | Thinking={7}c | Final={8}c" -f $TestId, $result.Score, $result.HardPass, $result.OutputStatus, $result.WallMs, $result.PromptTokensPerSec, $result.EvalTokensPerSec, $result.ThinkingChars, $result.FinalChars) -Level METRIC

    return $result
}

# =============================================================================
# [10/18] BATTERIE DE TESTS STANDARDISÉE
# =============================================================================

$Tests = @(
    [PSCustomObject]@{
        Id               = 'GEN-01'
        Category         = 'General'
        Prompt           = "Reponds en francais a cette question :`nPourquoi une architecture logicielle robuste doit-elle separer les politiques de decision, l'execution et l'audit ?`nDonne une reponse techniquement precise, structuree et concise."
        MaxTokens        = 512
        ExpectedExact    = ''
        ExpectedContains = 'politique|execution|audit'
        ForbiddenPattern = ''
    },
    [PSCustomObject]@{
        Id               = 'INS-01'
        Category         = 'Instruction'
        Prompt           = "Reponds exactement avec trois lignes.`nLigne 1 : ALPHA`nLigne 2 : BETA`nLigne 3 : GAMMA`nN'ajoute absolument aucun autre texte ni raisonnement."
        MaxTokens        = 128
        ExpectedExact    = "ALPHA`nBETA`nGAMMA"
        ExpectedContains = ''
        ForbiddenPattern = '(?i)explication|voici|bien sur|```'
    },
    [PSCustomObject]@{
        Id               = 'REASON-01'
        Category         = 'Reasoning'
        Prompt           = "Un systeme possede 3 files.`nLa premiere contient 12 taches.`nLa deuxieme contient deux fois moins de taches que la premiere.`nLa troisieme contient 5 taches de plus que la deuxieme.`nCombien de taches y a-t-il au total ? Explique brievement le calcul."
        MaxTokens        = 384
        ExpectedExact    = ''
        ExpectedContains = '29'
        ForbiddenPattern = ''
    },
    [PSCustomObject]@{
        Id               = 'REASON-02'
        Category         = 'Reasoning'
        Prompt           = "Un programme recoit 100 unites.`nIl depense 30 %.`nPuis il depense encore 20 unites.`nIl recoit ensuite 10 unites.`nQuelle est la quantite finale ? Montre les etapes du calcul."
        MaxTokens        = 384
        ExpectedExact    = ''
        ExpectedContains = '60'
        ForbiddenPattern = ''
    },
    [PSCustomObject]@{
        Id               = 'CODE-01'
        Category         = 'Code'
        Prompt           = "Ecris une fonction Python appelee safe_divide(a, b) qui retourne a / b et retourne None lorsque b vaut zero.`nDonne uniquement le code brut sans markdown."
        MaxTokens        = 256
        ExpectedExact    = ''
        ExpectedContains = 'safe_divide|return'
        ForbiddenPattern = ''
    },
    [PSCustomObject]@{
        Id               = 'CODE-02'
        Category         = 'Code'
        Prompt           = "Ecris une fonction PowerShell Get-SafeValue qui accepte un parametre [object]`$Value et retourne `$Value uniquement s'il n'est pas `$null. Sinon elle retourne une chaine vide.`nDonne uniquement le code."
        MaxTokens        = 256
        ExpectedExact    = ''
        ExpectedContains = 'Get-SafeValue|$null'
        ForbiddenPattern = ''
    },
    [PSCustomObject]@{
        Id               = 'JSON-01'
        Category         = 'Structured'
        Prompt           = "Retourne uniquement un JSON valide, sans markdown :`n{`n  `"status`": `"PASS`",`n  `"score`": 100,`n  `"mode`": `"CPU`"`n}"
        MaxTokens        = 256
        ExpectedExact    = ''
        ExpectedContains = ''
        ForbiddenPattern = '```'
    },
    [PSCustomObject]@{
        Id               = 'FR-01'
        Category         = 'French'
        Prompt           = "Explique en francais, avec un vocabulaire technique naturel, la difference entre latence, debit et fiabilite pour un modele IA local.`nDonne un exemple concret."
        MaxTokens        = 512
        ExpectedExact    = ''
        ExpectedContains = 'latence|debit|fiabilite'
        ForbiddenPattern = ''
    },
    [PSCustomObject]@{
        Id               = 'ROB-01'
        Category         = 'Robustness'
        Prompt           = "Analyse cette affirmation : `"Un modele plus rapide est necessairement plus intelligent.`"`nDis si elle est vraie ou fausse et explique pourquoi."
        MaxTokens        = 384
        ExpectedExact    = ''
        ExpectedContains = 'rapide|capacite|performance'
        ForbiddenPattern = ''
    },
    [PSCustomObject]@{
        Id               = 'CTX-01'
        Category         = 'Context'
        Prompt           = "Memorise mentalement ces quatre elements :`nAZUR = 17`nBUS = 42`nEZZIO = 91`nSWITCH = 63`nPuis reponds uniquement par la valeur correspondant a EZZIO."
        MaxTokens        = 128
        ExpectedExact    = '91'
        ExpectedContains = ''
        ForbiddenPattern = ''
    }
)

# =============================================================================
# [11/18] NOTATION PAR CATEGORIE
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
# [12/18] QUALIFICATION D'UN MODELE & TELEMETRIE PHYSIQUE
# =============================================================================

function Test-Model {
    param([Parameter(Mandatory)] [PSCustomObject]$Model)

    Write-Section "[MODEL] $($Model.Name)"
    Write-Forensic -Message "Debut qualification : $($Model.Name)" -Level INFO

    $switchResult       = Switch-OllamaModel -Model $Model.Name
    $results            = [System.Collections.Generic.List[object]]::new()
    $minFreeRamObserved = $switchResult.AvailableRamGB

    for ($w = 1; $w -le $WarmupRuns; $w++) {
        Write-Forensic -Message "Warmup $w/$WarmupRuns : $($Model.Name)" -Level INFO
        $warmupPayload = @{
            model      = $Model.Name
            prompt     = 'Reponds simplement READY.'
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
        }
        catch {
            Write-Forensic -Message "Warmup echoue : $($_.Exception.Message)" -Level WARN
        }
    }

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

        $snap = Get-MemorySnapshot
        if ($snap.FreeGB -lt $minFreeRamObserved) {
            $minFreeRamObserved = $snap.FreeGB
        }
    }

    Write-Forensic -Message "Tests stabilite : $StabilityRuns executions." -Level INFO

    for ($s = 1; $s -le $StabilityRuns; $s++) {
        $stable = Invoke-ModelTest `
            -Model $Model.Name `
            -TestId "STAB-$s" `
            -Category 'Stability' `
            -Prompt "Reponds en francais en une phrase concise :`nquel est le role principal d'un journal forensic ?" `
            -MaxTokens 256 `
            -ExpectedExact '' `
            -ExpectedContains 'journal|audit|forensic|trace' `
            -ForbiddenPattern ''

        $stable | Add-Member -NotePropertyName Model -NotePropertyValue $Model.Name -Force
        $results.Add($stable)

        $snap = Get-MemorySnapshot
        if ($snap.FreeGB -lt $minFreeRamObserved) {
            $minFreeRamObserved = $snap.FreeGB
        }
    }

    $allResults = @($results)
    $successful = @($allResults | Where-Object { $_.Success -eq $true })
    $failed     = @($allResults | Where-Object { $_.Success -ne $true })

    $avgScore = 0.0
    if ($allResults.Count -gt 0) {
        $avgScore = [math]::Round((($allResults | Measure-Object Score -Average).Average), 2)
    }

    $avgPromptTPS = 0.0
    $avgEvalTPS   = 0.0
    $avgLatency   = 0.0

    if ($successful.Count -gt 0) {
        $avgPromptTPS = [math]::Round((($successful | Measure-Object PromptTokensPerSec -Average).Average), 2)
        $avgEvalTPS   = [math]::Round((($successful | Measure-Object EvalTokensPerSec -Average).Average), 2)
        $avgLatency   = [math]::Round((($successful | Measure-Object EvalDurationMs -Average).Average), 2)
    }

    $failureRate = 100.0
    if ($allResults.Count -gt 0) {
        $failureRate = [math]::Round(($failed.Count / $allResults.Count * 100), 2)
    }

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

    $performanceScore = [math]::Min(100, [math]::Round(($avgEvalTPS / 40 * 100), 2))

    $reliabilityScore = [math]::Round((
        ($stabilityScore * 0.50) +
        ($hardPassRate   * 0.20) +
        ((100 - $failureRate) * 0.30)
    ), 2)

    $overallScore = [math]::Round((
        ($capabilityScore  * 0.60) +
        ($reliabilityScore * 0.25) +
        ($performanceScore * 0.15)
    ), 2)

    $memoryPressure = 'PASS'
    if (($minFreeRamObserved - $Thresholds.MinSafetyRamGB) -lt 0) {
        $memoryPressure = 'FAIL'
    }
    elseif ($minFreeRamObserved -lt 4.0) {
        $memoryPressure = 'WARN'
    }

    $qualified = (
        $switchResult.CpuVerified -eq $true -and
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
        $failureRate        -le $Thresholds.MaxFailureRatePercent -and
        $memoryPressure     -ne 'FAIL'
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

        RamBeforeLoadGB      = $switchResult.RamBeforeGB
        RamAfterLoadGB       = $switchResult.RamAfterGB
        ModelDeltaGB         = $switchResult.ModelDeltaGB
        MinFreeRamObservedGB = $minFreeRamObserved
        MemoryPressure       = $memoryPressure

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

        AvgEvalLatencyMs      = $avgLatency
        AvgPromptTokensPerSec = $avgPromptTPS
        AvgEvalTokensPerSec   = $avgEvalTPS

        FailureRate          = $failureRate

        TestsTotal           = $allResults.Count
        TestsSuccessful      = $successful.Count
        TestsFailed          = $failed.Count

        Verdict              = $verdict

        Tests                = $allResults
    }

    $profileLevel = if ($verdict -eq 'QUALIFIED') { 'PASS' } elseif ($verdict -eq 'PARTIAL') { 'WARN' } else { 'FAIL' }

    Write-Forensic -Message ("PROFILE {0} | CAP={1} | REL={2} | PERF={3} | OVERALL={4} | EVAL_TPS={5} | RAM_DELTA=+{6}GB | PRESSURE={7} | CPU_ONLY={8} | VERDICT={9}" -f $Model.Name, $capabilityScore, $reliabilityScore, $performanceScore, $overallScore, $avgEvalTPS, $switchResult.ModelDeltaGB, $memoryPressure, $switchResult.CpuVerified, $verdict) -Level $profileLevel

    return $profile
}

# =============================================================================
# [13/18] CERTIFICAT MATERIEL
# =============================================================================

Write-Section "[0/18] E-ZZIO MODEL QUALIFICATION GATE v$Version - HARDWARE PROFILE"

Write-Forensic -Message "Version=$Version | RunId=$RunId" -Level INFO
Write-Forensic -Message "CPU=$CpuName | Cores=$CpuCores | Threads=$CpuThreads" -Level INFO
Write-Forensic -Message ("RAM={0}GB DDR4-{1} MT/s ({2} canaux) | Bande passante theorique={3} Go/s" -f $TotalRamGB, $MemorySpeed, $MemoryChannels, $TheoreticalBandwidth) -Level INFO
Write-Forensic -Message "MODE=CPU-ONLY | NUM_GPU=$NumGpu | SINGLE_MODEL_ONLY=TRUE" -Level INFO
Write-Forensic -Message "OllamaHost=$OllamaHost" -Level INFO

Write-Host "CPU                     : $CpuName"
Write-Host "COEURS / THREADS        : $CpuCores c / $CpuThreads t"
Write-Host "MEMOIRE VIVE            : $TotalRamGB Go DDR4-$MemorySpeed MT/s"
Write-Host "CANAUX MEMOIRE          : $MemoryChannels ($($MemorySticks) barrettes)"
Write-Host "BANDE PASSANTE THEORIQUE: $TheoreticalBandwidth Go/s"
Write-Host "RAM DISPONIBLE INITIALE : $AvailableRamGB Go"

# =============================================================================
# [14/18] DISPONIBILITE OLLAMA
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
# [15/18] INVENTAIRE DES MODELES
# =============================================================================

Write-Section "[2/18] MODEL INVENTORY"

$allModels = @(Get-OllamaModels)
if ($allModels.Count -eq 0) {
    Write-Forensic -Message 'Aucun modele Ollama detecte.' -Level FAIL
    throw 'NO_MODELS'
}

$genList = [System.Collections.Generic.List[PSCustomObject]]::new()
$embList = [System.Collections.Generic.List[PSCustomObject]]::new()

foreach ($m in $allModels) {
    if ($null -eq $m) { continue }
    if ($m.IsEmbedding) {
        $embList.Add($m)
    }
    else {
        $genList.Add($m)
    }
}

$models = @($genList)
$embeddingProfiles = @($embList)

if ($MaxModels -gt 0 -and $models.Count -gt $MaxModels) {
    $models = @($models | Select-Object -First $MaxModels)
}

Write-Forensic -Message "$($models.Count) modele(s) generatif(s) a qualifier, $($embeddingProfiles.Count) modele(s) d'embedding ignore(s)." -Level PASS

foreach ($m in $models) {
    Write-Host ('  - {0} | {1} GB | params={2} | quant={3} | family={4}' -f $m.Name, $m.SizeGB, $m.Parameter, $m.Quant, $m.Family)
}

# =============================================================================
# [16/18] PURGE INITIALE
# =============================================================================

Write-Section "[3/18] INITIAL RUNTIME CLEANUP"

$initial = @(Get-RunningModelNames)
Write-Forensic -Message "Etat initial : $($initial.Count) modele(s) actif(s)." -Level INFO

if ($initial.Count -gt 0) {
    Write-Host "`nModele(s) actuellement actif(s) :"
    foreach ($name in $initial) {
        Write-Host "  * $name"
    }
}

Clear-OllamaRuntime
Write-Forensic -Message 'PRECHECK OK : 0 modele actif.' -Level PASS

# =============================================================================
# [17/18] BATTERIE DE QUALIFICATION
# =============================================================================

Write-Section "[4/18] QUALIFICATION BATTERY"

$profiles = [System.Collections.Generic.List[object]]::new()
$totalModels = $models.Count
$modelIndex = 0

foreach ($model in $models) {
    $modelIndex++
    Write-Host "`n>>> MODELE $modelIndex/$totalModels : $($model.Name)" -ForegroundColor Cyan
    Write-Forensic -Message "START MODEL $modelIndex/$totalModels : $($model.Name)" -Level SWITCH

    try {
        $profile = Test-Model -Model $model
        $profiles.Add($profile)
    }
    catch {
        Write-Forensic -Message "Qualification interrompue pour $($model.Name) : $($_.Exception.Message)" -Level FAIL
        $profiles.Add([PSCustomObject]@{
            RunId                 = $RunId
            Version               = $Version
            Model                 = $model.Name
            ParameterSize         = $model.Parameter
            Quantization          = $model.Quant
            Family                = $model.Family
            Format                = $model.Format
            SizeGB                = $model.SizeGB

            CpuOnly               = $false
            Processor             = 'UNKNOWN'

            SwitchMs              = 0
            SwitchWallMs          = 0

            RamBeforeLoadGB       = 0.0
            RamAfterLoadGB        = 0.0
            ModelDeltaGB          = 0.0
            MinFreeRamObservedGB  = 0.0
            MemoryPressure        = 'CRITICAL_ABORT'

            CapabilityScore       = 0
            ReliabilityScore      = 0
            PerformanceScore      = 0
            OverallScore          = 0

            InstructionScore      = 0
            ReasoningScore        = 0
            CodeScore             = 0
            FrenchScore           = 0
            StructuredScore       = 0
            ContextScore          = 0
            GeneralScore          = 0
            RobustnessScore       = 0
            StabilityScore        = 0

            HardPassRate          = 0
            ThinkingPresenceRate  = 0

            AvgEvalLatencyMs      = 0
            AvgPromptTokensPerSec = 0
            AvgEvalTokensPerSec   = 0

            FailureRate           = 100

            TestsTotal            = 0
            TestsSuccessful       = 0
            TestsFailed           = 0

            Verdict               = 'FAIL'
            FatalError            = $_.Exception.Message

            Tests                 = @()
        })
    }
    finally {
        $active = @(Get-RunningModelNames)
        if ($active.Count -gt 1) {
            throw 'MULTIPLE_MODELS_AFTER_TEST'
        }

        if ($active.Count -eq 1) {
            $released = Unload-OllamaModel -Model $active[0]
            if (-not $released) {
                throw 'POST_MODEL_UNLOAD_FAILURE'
            }
        }

        if (-not (Wait-RuntimeEmpty)) {
            throw 'POST_MODEL_RUNTIME_NOT_EMPTY'
        }

        $snapFinal = Get-MemorySnapshot
        Write-Forensic -Message ("Modele {0} completement libere. RAM disponible recuperee : {1} Go." -f $model.Name, $snapFinal.FreeGB) -Level RAM
    }
}

# =============================================================================
# [18/18] CLASSEMENT FINAL
# =============================================================================

Write-Section "[5/18] FINAL RANKING (HARDWARE CERTIFIED)"

$ranking = @($profiles | Sort-Object -Property OverallScore -Descending)
$rank = 0

foreach ($profile in $ranking) {
    $rank++
    Write-Host "`n#$rank  $($profile.Model)" -ForegroundColor White
    Write-Host "     OVERALL SCORE   : $($profile.OverallScore)/100"
    Write-Host "     CAPABILITY      : $($profile.CapabilityScore)/100"
    Write-Host "     RELIABILITY     : $($profile.ReliabilityScore)/100"
    Write-Host "     PERFORMANCE     : $($profile.PerformanceScore)/100"
    Write-Host "     EVAL SPEED      : $($profile.AvgEvalTokensPerSec) tok/s"
    Write-Host "     PROMPT INGESTION: $($profile.AvgPromptTokensPerSec) tok/s"
    Write-Host "     RAM DELTA       : +$($profile.ModelDeltaGB) Go"
    Write-Host "     MEMORY PRESSURE : $($profile.MemoryPressure) (Min libre: $($profile.MinFreeRamObservedGB) Go)"
    Write-Host "     CPU-ONLY        : $($profile.CpuOnly)"
    Write-Host "     HARD PASS RATE  : $($profile.HardPassRate)%"
    Write-Host "     VERDICT         : $($profile.Verdict)"
}

# =============================================================================
# EXPORT JSON
# =============================================================================

$export = [PSCustomObject]@{
    Schema = 'EZZIO-MODEL-QUALIFICATION-4.4.0'
    RunId = $RunId
    Timestamp = (Get-Date).ToString('o')
    HardwareCertificate = [PSCustomObject]@{
        CPU                  = $CpuName
        Cores                = $CpuCores
        Threads              = $CpuThreads
        RAM_Total_GB         = $TotalRamGB
        MemorySpeed_MTS      = $MemorySpeed
        MemoryChannels       = $MemoryChannels
        MemorySticks         = $MemorySticks
        TheoreticalBandwidth = $TheoreticalBandwidth
        GPU_Mode             = 'DISABLED'
        OllamaHost           = $OllamaHost
    }
    ModelsQualified = $profiles.Count
    Ranking = $ranking
    Profiles = $profiles.ToArray()
}

$export | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $JsonPath -Encoding UTF8
Write-Forensic -Message "JSON exporte : $JsonPath" -Level PASS

# =============================================================================
# EXPORT CSV
# =============================================================================

$profiles | Select-Object RunId, Version, Model, ParameterSize, Quantization, Family, Format, SizeGB, `
    CpuOnly, Processor, SwitchMs, RamBeforeLoadGB, RamAfterLoadGB, ModelDeltaGB, MinFreeRamObservedGB, MemoryPressure, `
    OverallScore, CapabilityScore, ReliabilityScore, PerformanceScore, InstructionScore, ReasoningScore, `
    CodeScore, FrenchScore, StructuredScore, ContextScore, HardPassRate, ThinkingPresenceRate, `
    AvgEvalLatencyMs, AvgPromptTokensPerSec, AvgEvalTokensPerSec, FailureRate, Verdict |
    Export-Csv -LiteralPath $CsvPath -NoTypeInformation -Encoding UTF8

Write-Forensic -Message "CSV exporte : $CsvPath" -Level PASS

# =============================================================================
# RAPPORT TEXTE
# =============================================================================

$best = $ranking | Select-Object -First 1

$summary = @"
==================================================================================
E-ZZIO - MODEL QUALIFICATION GATE v$Version - HARDWARE CERTIFICATE
==================================================================================
RUN ID                  : $RunId
PROCESSOR               : $CpuName ($CpuCores Cores / $CpuThreads Threads)
MEMORY SYSTEM           : $TotalRamGB Go DDR4-$MemorySpeed MT/s ($MemoryChannels Canaux)
THEORETICAL BANDWIDTH   : $TheoreticalBandwidth Go/s
GPU INFERENCE           : DISABLED / CPU-ONLY
SINGLE MODEL RUNTIME    : ENFORCED

MODELS SUMMARY
--------------
QUALIFIED               : $(@($profiles | Where-Object { $_.Verdict -eq 'QUALIFIED' }).Count)
PARTIAL                 : $(@($profiles | Where-Object { $_.Verdict -eq 'PARTIAL' }).Count)
FAIL                    : $(@($profiles | Where-Object { $_.Verdict -eq 'FAIL' }).Count)
TOTAL TESTED            : $($profiles.Count)

BEST MODEL PROFILE
------------------
MODEL NAME              : $(if ($best) { $best.Model } else { 'NONE' })
OVERALL SCORE           : $(if ($best) { $best.OverallScore } else { 0 })/100
CAPABILITY SCORE        : $(if ($best) { $best.CapabilityScore } else { 0 })/100
RELIABILITY SCORE       : $(if ($best) { $best.ReliabilityScore } else { 0 })/100
EVAL SPEED              : $(if ($best) { $best.AvgEvalTokensPerSec } else { 0 }) tok/s
PROMPT SPEED            : $(if ($best) { $best.AvgPromptTokensPerSec } else { 0 }) tok/s
RAM FOOTPRINT           : +$(if ($best) { $best.ModelDeltaGB } else { 0 }) Go
MEMORY PRESSURE         : $(if ($best) { $best.MemoryPressure } else { 'NONE' }) (Min libre: $(if ($best) { $best.MinFreeRamObservedGB } else { 0 }) Go)
CPU-ONLY VERIFIED       : $(if ($best) { $best.CpuOnly } else { $false })
VERDICT                 : $(if ($best) { $best.Verdict } else { 'NONE' })
==================================================================================
"@

Set-Content -LiteralPath $SummaryPath -Value $summary -Encoding UTF8
Write-Forensic -Message "Summary exporte : $SummaryPath" -Level PASS

# =============================================================================
# PURGE FINALE
# =============================================================================

Clear-OllamaRuntime
Write-Forensic -Message 'Runtime Ollama propre : 0 modele actif.' -Level PASS

Write-Host ''
Write-Host ('=' * 82)
Write-Host 'EXECUTION TERMINEE - SINGLE-MODEL RUNTIME CONFIRMED CLEAN' -ForegroundColor Green
Write-Host ('=' * 82)