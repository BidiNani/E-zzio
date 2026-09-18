#requires -Version 7.4
# =============================================================================
# E-ZZIO - MODEL QUALIFICATION DIAGNOSTIC
# Version : 3.0.8
# CPU-ONLY / FORENSIC / DEEP TELEMETRY / FAIL-CLOSED
#
# OBJECTIF
#   Analyser la cause racine des reponses vides ou timeouts sur les 4 modeles :
#   - mrasif/gpt-oss-20b-GGUF:Q4_K_M
#   - hf.co/mradermacher/Kiwi-4b-i1-GGUF:Q4_K_M
#   - qwen3:8b
#   - qwen3:14b
#
# HYPOTHESES FORENSIQUES A TESTER :
#   1. Budget num_predict=32 sature par les tokens de raisonnement interne (<think>).
#   2. Latence de chargement initial CPU / prompt_eval_duration sur 14B/20B > 90s.
#   3. Format du template / capture de la reponse brute API.
# =============================================================================

[CmdletBinding()]
param(
    [string[]]$Models
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# =============================================================================
# CONFIGURATION
# =============================================================================

$Version = '3.0.8'
$Mode    = 'FORENSIC_DIAGNOSTIC'

$OllamaExe  = 'G:\Ollama\ollama.exe'
$ModelsRoot = 'G:\Ollama\Models'
$AuditRoot  = 'G:\AI\E-zzio\runtime\audit\forensic'

$HostAddress = '127.0.0.1'
$Port        = 11435
$BaseUri     = "http://$HostAddress`:$Port"

$Threads    = 12
$Context    = 4096
$TimeoutSec = 180  # Plafond etendu a 180s pour tester la charge CPU sur 14B/20B

$RunId = Get-Date -Format 'yyyyMMdd_HHmmss'
$JsonOut = Join-Path $AuditRoot "EZZIO_MODEL_DIAGNOSTIC_V308_$RunId.json"

if ($null -ne $Models -and $Models.Count -gt 0) {
    $TargetModels = @($Models)
}
else {
    $TargetModels = @(
        'hf.co/mradermacher/Kiwi-4b-i1-GGUF:Q4_K_M'
        'qwen3:8b'
        'qwen3:14b'
        'mrasif/gpt-oss-20b-GGUF:Q4_K_M'
    )
}

# =============================================================================
# ETAT RUNTIME
# =============================================================================

$ServerProcess     = $null
$ServerStartedByUs = $false

$Results = [System.Collections.Generic.List[object]]::new()
$FatalErrors = 0
$OverallPass = $false

$sw = [System.Diagnostics.Stopwatch]::StartNew()

# =============================================================================
# CONSOLE & FORMATAGE
# =============================================================================

function Show-Section {
    param([Parameter(Mandatory)][string]$Text)
    Write-Host ''
    Write-Host ('-' * 80)
    Write-Host $Text
    Write-Host ('-' * 80)
}

function Write-Info {
    param([Parameter(Mandatory)][string]$Text)
    Write-Host "[INFO] $Text"
}

function Write-Pass {
    param([Parameter(Mandatory)][string]$Text)
    Write-Host "[PASS] $Text" -ForegroundColor Green
}

function Write-Fail {
    param([Parameter(Mandatory)][string]$Text)
    Write-Host "[FAIL] $Text" -ForegroundColor Red
}

function Write-Warn {
    param([Parameter(Mandatory)][string]$Text)
    Write-Host "[WARN] $Text" -ForegroundColor Yellow
}

# =============================================================================
# ACCES SUR AUX PROPRIETES
# =============================================================================

function Get-PropertyValue {
    param($Object, [Parameter(Mandatory)][string]$Name)
    if ($null -eq $Object) { return $null }
    if ($Object -is [System.Collections.IDictionary]) {
        if ($Object.Contains($Name)) { return $Object[$Name] }
        return $null
    }
    $prop = $Object.PSObject.Properties[$Name]
    if ($null -eq $prop) { return $null }
    return $prop.Value
}

function Get-StringProperty {
    param($Object, [Parameter(Mandatory)][string]$Name)
    $val = Get-PropertyValue -Object $Object -Name $Name
    if ($null -eq $val) { return '' }
    return [string]$val
}

function Get-DoubleProperty {
    param($Object, [Parameter(Mandatory)][string]$Name)
    $val = Get-PropertyValue -Object $Object -Name $Name
    if ($null -eq $val) { return 0.0 }
    try { return [double]$val } catch { return 0.0 }
}

function Get-BoolProperty {
    param($Object, [Parameter(Mandatory)][string]$Name)
    $val = Get-PropertyValue -Object $Object -Name $Name
    if ($null -eq $val) { return $false }
    try { return [bool]$val } catch { return $false }
}

# =============================================================================
# HARDWARE
# =============================================================================

function Get-FreeGB {
    try {
        $os = Get-CimInstance -ClassName Win32_OperatingSystem -ErrorAction Stop
        return [math]::Round(([double]$os.FreePhysicalMemory / 1MB), 3)
    } catch { return 0.0 }
}

function Get-TotalGB {
    try {
        $cs = Get-CimInstance -ClassName Win32_ComputerSystem -ErrorAction Stop
        return [math]::Round(([double]$cs.TotalPhysicalMemory / 1GB), 3)
    } catch { return 0.0 }
}

function Test-PortFree {
    param([Parameter(Mandatory)][int]$PortNumber)
    $listener = $null
    try {
        $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $PortNumber)
        $listener.Start()
        return $true
    } catch { return $false }
    finally {
        if ($null -ne $listener) { $listener.Stop() }
    }
}

# =============================================================================
# HTTP API OLLAMA AVEC TELEMETRIE BRUTE
# =============================================================================

function Invoke-RawApiPost {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][hashtable]$Body,
        [int]$Timeout = $TimeoutSec
    )

    $json = $Body | ConvertTo-Json -Depth 50 -Compress

    $handler = $null
    $client = $null
    $content = $null
    $response = $null
    $swReq = [System.Diagnostics.Stopwatch]::StartNew()

    try {
        $handler = [System.Net.Http.HttpClientHandler]::new()
        $client = [System.Net.Http.HttpClient]::new($handler)
        $client.Timeout = [TimeSpan]::FromSeconds($Timeout)

        $content = [System.Net.Http.StringContent]::new(
            $json,
            [System.Text.Encoding]::UTF8,
            'application/json'
        )

        $response = $client.PostAsync("$BaseUri$Path", $content).GetAwaiter().GetResult()
        $rawText = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()
        $swReq.Stop()

        $parsed = $null
        try {
            $parsed = $rawText | ConvertFrom-Json -Depth 100 -ErrorAction Stop
        } catch {}

        return [pscustomobject][ordered]@{
            StatusCode   = [int]$response.StatusCode
            IsSuccess    = $response.IsSuccessStatusCode
            ElapsedSec   = [math]::Round($swReq.Elapsed.TotalSeconds, 3)
            RawBody      = $rawText
            Parsed       = $parsed
            ErrorMessage = ''
        }
    }
    catch {
        $swReq.Stop()
        return [pscustomobject][ordered]@{
            StatusCode   = 0
            IsSuccess    = $false
            ElapsedSec   = [math]::Round($swReq.Elapsed.TotalSeconds, 3)
            RawBody      = ''
            Parsed       = $null
            ErrorMessage = $_.Exception.Message
        }
    }
    finally {
        if ($null -ne $content)  { $content.Dispose() }
        if ($null -ne $response) { $response.Dispose() }
        if ($null -ne $client)   { $client.Dispose() }
        if ($null -ne $handler)  { $handler.Dispose() }
    }
}

function Invoke-ApiGet {
    param([Parameter(Mandatory)][string]$Path, [int]$Timeout = 10)
    $handler = $null
    $client = $null
    $response = $null
    try {
        $handler = [System.Net.Http.HttpClientHandler]::new()
        $client = [System.Net.Http.HttpClient]::new($handler)
        $client.Timeout = [TimeSpan]::FromSeconds($Timeout)
        $response = $client.GetAsync("$BaseUri$Path").GetAwaiter().GetResult()
        $text = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()
        if (-not $response.IsSuccessStatusCode) { throw "HTTP $([int]$response.StatusCode): $text" }
        return ($text | ConvertFrom-Json -Depth 100 -ErrorAction Stop)
    } finally {
        if ($null -ne $response) { $response.Dispose() }
        if ($null -ne $client)   { $client.Dispose() }
        if ($null -ne $handler)  { $handler.Dispose() }
    }
}

function Get-OllamaLoadedModels {
    try {
        $resp = Invoke-ApiGet '/api/ps' 10
        if ($null -eq $resp) { return @() }
        $models = Get-PropertyValue -Object $resp -Name 'models'
        if ($null -eq $models) { return @() }
        return @($models)
    } catch { return @() }
}

function Test-OllamaReady {
    param([int]$Tries = 40)
    for ($i = 0; $i -lt $Tries; $i++) {
        try {
            $null = Invoke-ApiGet '/api/tags' 3
            return $true
        } catch { Start-Sleep -Milliseconds 500 }
    }
    return $false
}

function Unload-AllModels {
    $loaded = @(Get-OllamaLoadedModels)
    if ($loaded.Count -gt 0) {
        foreach ($model in $loaded) {
            $modelName = Get-StringProperty -Object $model -Name 'name'
            if ([string]::IsNullOrWhiteSpace($modelName)) { continue }
            try {
                $null = Invoke-RawApiPost '/api/generate' @{
                    model      = $modelName
                    prompt     = ''
                    stream     = $false
                    keep_alive = 0
                    options    = @{ num_ctx = 256; num_thread = $Threads; num_predict = 1; temperature = 0 }
                } 20
            } catch {}
        }
    }

    Start-Sleep -Milliseconds 500
    $remaining = @(Get-OllamaLoadedModels)
    if ($remaining.Count -gt 0) {
        $names = @(foreach ($item in $remaining) { Get-StringProperty -Object $item -Name 'name' })
        throw "Modeles encore residents en memoire : $($names -join ', ')"
    }
}

# =============================================================================
# EXECUTION DU DIAGNOSTIC
# =============================================================================

try {
    Write-Host ''
    Write-Host ('=' * 80)
    Write-Host '       E-ZZIO - MODEL QUALIFICATION DIAGNOSTIC v3.0.8'
    Write-Host '       CPU-ONLY / DEEP TELEMETRY / ROOT-CAUSE AUDIT'
    Write-Host ('=' * 80)

    Write-Info "Engine      : E-ZZIO MODEL QUALIFICATION DIAGNOSTIC"
    Write-Info "Version     : $Version"
    Write-Info "RunId       : $RunId"
    Write-Info "Ollama      : $OllamaExe"
    Write-Info "Models Root : $ModelsRoot"
    Write-Info "CPU Target  : Ryzen 9 5900X / 12C / 24T"
    Write-Info "Server      : $BaseUri"
    Write-Info "Threads     : $Threads"
    Write-Info "Context     : $Context"
    Write-Info "Timeout     : $TimeoutSec s"
    Write-Info "Cibles      : $($TargetModels -join ', ')"

    # -------------------------------------------------------------------------
    # [1/4] VALIDATION & DEMARRAGE SERVEUR ISOLE
    # -------------------------------------------------------------------------
    Show-Section '[1/4] VALIDATION ENVIRONNEMENT & DEMARRAGE SERVEUR'

    if (-not (Test-Path -LiteralPath $OllamaExe -PathType Leaf)) {
        throw "ollama.exe introuvable : $OllamaExe"
    }

    New-Item -Path $AuditRoot -ItemType Directory -Force | Out-Null

    if (-not (Test-PortFree $Port)) {
        Write-Warn "Port $Port occupe. Tentative de nettoyage..."
        $conns = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
        foreach ($conn in $conns) {
            Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
        }
        Start-Sleep -Milliseconds 500
        if (-not (Test-PortFree $Port)) {
            throw "Port $Port toujours occupe apres nettoyage."
        }
    }

    $env:OLLAMA_MODELS = $ModelsRoot
    $env:OLLAMA_HOST = "$HostAddress`:$Port"
    $env:OLLAMA_KEEP_ALIVE = '0'
    $env:GGML_VK_VISIBLE_DEVICES = '-1'
    $env:CUDA_VISIBLE_DEVICES = '-1'
    $env:OLLAMA_LLM_LIBRARY = 'cpu_avx2'
    $env:OLLAMA_NUM_PARALLEL = '1'
    $env:OLLAMA_VULKAN = '0'
    $env:OLLAMA_MAX_LOADED_MODELS = '1'

    $startInfo = [System.Diagnostics.ProcessStartInfo]::new()
    $startInfo.FileName = $OllamaExe
    $startInfo.Arguments = 'serve'
    $startInfo.UseShellExecute = $false
    $startInfo.CreateNoWindow = $true

    $ServerProcess = [System.Diagnostics.Process]::new()
    $ServerProcess.StartInfo = $startInfo

    if (-not $ServerProcess.Start()) {
        throw 'Impossible de demarrer Ollama.'
    }

    $ServerStartedByUs = $true
    Write-Pass "Serveur lance sur $BaseUri (PID=$($ServerProcess.Id))."

    if (-not (Test-OllamaReady)) {
        throw 'API Ollama indisponible apres demarrage.'
    }

    Write-Pass 'API Ollama /api/tags disponible.'

    # -------------------------------------------------------------------------
    # [2/4] EXECUTION DES TESTS DIAGNOSTIQUES APPROFONDIS
    # -------------------------------------------------------------------------
    Show-Section '[2/4] TESTS DIAGNOSTIQUES PAR MODELE'

    $promptSpeed = "Return exactly one short sentence confirming that the CPU-only benchmark is running.`nNo markdown."

    foreach ($model in $TargetModels) {
        Write-Host ''
        Write-Host ('=' * 80)
        Write-Host " DIAGNOSTIC APPROFONDI : $model"
        Write-Host ('=' * 80)

        $diag = [pscustomobject][ordered]@{
            ModelName        = $model
            RamBeforeGB      = Get-FreeGB
            Test32Tokens     = $null
            Test128Tokens    = $null
            RootCauseSummary = ''
        }

        try {
            Unload-AllModels
            Write-Pass 'RAM nettoyee avant test.'

            # -----------------------------------------------------------------
            # TEST A : num_predict = 32 (Condition du bench v3.0.7)
            # -----------------------------------------------------------------
            Write-Host ''
            Write-Info "--- [TEST A] num_predict = 32 (Timeout $TimeoutSec s) ---"
            $resp32 = Invoke-RawApiPost '/api/generate' @{
                model      = $model
                prompt     = $promptSpeed
                stream     = $false
                keep_alive = 0
                options    = @{
                    num_ctx     = $Context
                    num_thread  = $Threads
                    num_predict = 32
                    temperature = 0
                    top_p       = 1
                    seed        = 42
                }
            } $TimeoutSec

            $parsed32 = $resp32.Parsed
            $diag.Test32Tokens = [pscustomobject][ordered]@{
                StatusCode         = $resp32.StatusCode
                ElapsedSec         = $resp32.ElapsedSec
                ErrorMessage       = $resp32.ErrorMessage
                Done               = (Get-BoolProperty -Object $parsed32 -Name 'done')
                DoneReason         = (Get-StringProperty -Object $parsed32 -Name 'done_reason')
                TotalDurationSec   = [math]::Round((Get-DoubleProperty -Object $parsed32 -Name 'total_duration') / 1e9, 3)
                LoadDurationSec    = [math]::Round((Get-DoubleProperty -Object $parsed32 -Name 'load_duration') / 1e9, 3)
                PromptEvalCount    = (Get-DoubleProperty -Object $parsed32 -Name 'prompt_eval_count')
                PromptEvalDuration = [math]::Round((Get-DoubleProperty -Object $parsed32 -Name 'prompt_eval_duration') / 1e9, 3)
                EvalCount          = (Get-DoubleProperty -Object $parsed32 -Name 'eval_count')
                EvalDuration       = [math]::Round((Get-DoubleProperty -Object $parsed32 -Name 'eval_duration') / 1e9, 3)
                ResponseText       = (Get-StringProperty -Object $parsed32 -Name 'response')
                ResponseLength     = (Get-StringProperty -Object $parsed32 -Name 'response').Length
                RawThinking        = (Get-StringProperty -Object $parsed32 -Name 'thinking')
            }

            Write-Info "Status Code        : $($diag.Test32Tokens.StatusCode)"
            Write-Info "Elapsed Total      : $($diag.Test32Tokens.ElapsedSec) s"
            Write-Info "Done / Reason      : $($diag.Test32Tokens.Done) / $($diag.Test32Tokens.DoneReason)"
            Write-Info "Load Duration      : $($diag.Test32Tokens.LoadDurationSec) s"
            Write-Info "Prompt Eval Count  : $($diag.Test32Tokens.PromptEvalCount) tokens ($($diag.Test32Tokens.PromptEvalDuration) s)"
            Write-Info "Eval Tokens Count  : $($diag.Test32Tokens.EvalCount) tokens ($($diag.Test32Tokens.EvalDuration) s)"
            Write-Info "Response Length    : $($diag.Test32Tokens.ResponseLength)"
            Write-Info "Response Content   : '$($diag.Test32Tokens.ResponseText)'"
            if (-not [string]::IsNullOrWhiteSpace($diag.Test32Tokens.RawThinking)) {
                Write-Info "Thinking Tokens    : '$($diag.Test32Tokens.RawThinking)'"
            }
            if (-not [string]::IsNullOrWhiteSpace($diag.Test32Tokens.ErrorMessage)) {
                Write-Fail "Erreur HTTP/Reseau : $($diag.Test32Tokens.ErrorMessage)"
            }

            # -----------------------------------------------------------------
            # TEST B : num_predict = 128 (Extension du budget de sortie)
            # -----------------------------------------------------------------
            Write-Host ''
            Write-Info "--- [TEST B] num_predict = 128 (Budget étendu) ---"
            $resp128 = Invoke-RawApiPost '/api/generate' @{
                model      = $model
                prompt     = $promptSpeed
                stream     = $false
                keep_alive = 0
                options    = @{
                    num_ctx     = $Context
                    num_thread  = $Threads
                    num_predict = 128
                    temperature = 0
                    top_p       = 1
                    seed        = 42
                }
            } $TimeoutSec

            $parsed128 = $resp128.Parsed
            $diag.Test128Tokens = [pscustomobject][ordered]@{
                StatusCode         = $resp128.StatusCode
                ElapsedSec         = $resp128.ElapsedSec
                ErrorMessage       = $resp128.ErrorMessage
                Done               = (Get-BoolProperty -Object $parsed128 -Name 'done')
                DoneReason         = (Get-StringProperty -Object $parsed128 -Name 'done_reason')
                TotalDurationSec   = [math]::Round((Get-DoubleProperty -Object $parsed128 -Name 'total_duration') / 1e9, 3)
                LoadDurationSec    = [math]::Round((Get-DoubleProperty -Object $parsed128 -Name 'load_duration') / 1e9, 3)
                PromptEvalCount    = (Get-DoubleProperty -Object $parsed128 -Name 'prompt_eval_count')
                PromptEvalDuration = [math]::Round((Get-DoubleProperty -Object $parsed128 -Name 'prompt_eval_duration') / 1e9, 3)
                EvalCount          = (Get-DoubleProperty -Object $parsed128 -Name 'eval_count')
                EvalDuration       = [math]::Round((Get-DoubleProperty -Object $parsed128 -Name 'eval_duration') / 1e9, 3)
                ResponseText       = (Get-StringProperty -Object $parsed128 -Name 'response')
                ResponseLength     = (Get-StringProperty -Object $parsed128 -Name 'response').Length
                RawThinking        = (Get-StringProperty -Object $parsed128 -Name 'thinking')
            }

            Write-Info "Status Code        : $($diag.Test128Tokens.StatusCode)"
            Write-Info "Elapsed Total      : $($diag.Test128Tokens.ElapsedSec) s"
            Write-Info "Done / Reason      : $($diag.Test128Tokens.Done) / $($diag.Test128Tokens.DoneReason)"
            Write-Info "Eval Tokens Count  : $($diag.Test128Tokens.EvalCount) tokens ($($diag.Test128Tokens.EvalDuration) s)"
            Write-Info "Response Length    : $($diag.Test128Tokens.ResponseLength)"
            Write-Info "Response Content   : '$($diag.Test128Tokens.ResponseText)'"

            # -----------------------------------------------------------------
            # DÉDUCTION DE LA CAUSE RACINE
            # -----------------------------------------------------------------
            if ($diag.Test32Tokens.DoneReason -eq 'length' -and $diag.Test32Tokens.ResponseLength -eq 0 -and $diag.Test128Tokens.ResponseLength -gt 0) {
                $diag.RootCauseSummary = 'BUDGET_EXHAUSTED_BY_REASONING_TOKENS (Resoluble avec num_predict adapte)'
                Write-Pass "Cause racine identifiee : $model produit des tokens de raisonnement qui saturaient num_predict=32. Avec 128 tokens, la reponse est produite !"
            }
            elseif ($diag.Test32Tokens.ElapsedSec -gt 90.0 -or $diag.Test32Tokens.ErrorMessage -match 'Timeout') {
                $diag.RootCauseSummary = 'CPU_INFERENCE_TIMEOUT_OVER_90S (Modele trop lourd pour le seuil strict de 90s)'
                Write-Warn "Cause racine identifiee : $model requiert plus de 90s pour charger et evaluer sur CPU."
            }
            elseif ($diag.Test128Tokens.ResponseLength -eq 0) {
                $diag.RootCauseSummary = 'INHERENT_EMPTY_OUTPUT_OR_TEMPLATE_ISSUE'
                Write-Fail "Cause racine identifiee : $model renvoie une reponse vide meme avec budget etendu."
            }
            else {
                $diag.RootCauseSummary = 'FUNCTIONAL_WITH_EXTENDED_PARAMETERS'
                Write-Pass "Cause racine identifiee : Operationnel avec parametres adaptes."
            }
        }
        catch {
            $diag.RootCauseSummary = "EXCEPTION: $($_.Exception.Message)"
            Write-Fail "$model : $($diag.RootCauseSummary)"
        }
        finally {
            Unload-AllModels
        }

        $Results.Add($diag)
    }

    $OverallPass = $true
}
catch {
    $FatalErrors++
    Write-Fail "EXCEPTION FATALE : $($_.Exception.Message)"
}
finally {
    if ($ServerStartedByUs -and $null -ne $ServerProcess -and -not $ServerProcess.HasExited) {
        Stop-Process -Id $ServerProcess.Id -Force -ErrorAction SilentlyContinue
        Start-Sleep -Milliseconds 500
        Write-Pass 'Serveur Ollama arrete en finally.'
    }
}

# =============================================================================
# [3/4] EXPORT ET RELECTURE JSON
# =============================================================================

$sw.Stop()
$duration = [math]::Round($sw.Elapsed.TotalSeconds, 3)

Show-Section '[3/4] EXPORT ET RELECTURE JSON'

$report = [ordered]@{
    Engine       = 'E-ZZIO MODEL QUALIFICATION DIAGNOSTIC'
    Version      = $Version
    RunId        = $RunId
    DurationSec  = $duration
    TargetModels = $TargetModels
    Results      = @($Results)
}

$jsonValid = $false
try {
    $jsonText = $report | ConvertTo-Json -Depth 100
    Set-Content -LiteralPath $JsonOut -Value $jsonText -Encoding UTF8
    $reloaded = Get-Content -LiteralPath $JsonOut -Raw -Encoding UTF8 | ConvertFrom-Json -Depth 100 -ErrorAction Stop
    $jsonValid = $true
    Write-Pass "JSON ecrit et valide : $JsonOut"
} catch {
    Write-Fail "Erreur export JSON : $($_.Exception.Message)"
}

# =============================================================================
# [4/4] VERDICT FINAL DU DIAGNOSTIC
# =============================================================================

Show-Section '[4/4] VERDICT FINAL DU DIAGNOSTIC'

foreach ($res in $Results) {
    Write-Host "Modèle : $($res.ModelName)"
    Write-Host "  -> Cause Racine : $($res.RootCauseSummary)"
}

Write-Host ''
Write-Host ('=' * 80)
Write-Host ' DIAGNOSTIC TERMINE'
Write-Host ('=' * 80)
Write-Host ''

exit 0
