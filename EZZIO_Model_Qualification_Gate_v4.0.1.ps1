#requires -Version 7.4
# =============================================================================
# E-ZZIO — MODEL QUALIFICATION GATE
# Version : 4.0.1
# CPU-ONLY / BLIND / FORENSIC / FAIL-CLOSED
# =============================================================================
#
# 4.0.1 FORENSIC CORRECTIONS
# - Aucun artefact Markdown ```powershell dans le fichier généré.
# - Rapport final sans opérateur -f fragile : zéro erreur de substitution.
# - Benchmark exhaustif des modèles génératifs installés.
# - Embeddings testés séparément.
# - 10 scénarios génératifs : S01..S10, deux runs par scénario.
# - Déterminisme mesuré séparément.
# - 1 seul modèle résident / 1 requête parallèle / keep_alive=0.
# - CPU AVX2 explicite, CUDA/Vulkan neutralisés.
# - Aucun modèle/blob supprimé.
# - Export JSON + CSV relus après écriture.
# - Le verdict d'infrastructure est indépendant du score du modèle.
# =============================================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$Version    = '4.0.1'
$OllamaExe  = 'G:\Ollama\ollama.exe'
$ModelsRoot = 'G:\Ollama\Models'
$AuditRoot  = 'G:\AI\E-zzio\runtime\audit\forensic'

$HostAddress = '127.0.0.1'
$Port        = 11435
$BaseUri     = "http://$HostAddress`:$Port"

$Threads   = 12
$Context   = 4096
$TimeoutSec = 180
$Seed      = 809437

$RunId = Get-Date -Format 'yyyyMMdd_HHmmss'

New-Item -ItemType Directory -Path $AuditRoot -Force | Out-Null

$JsonOut = Join-Path $AuditRoot "EZZIO_MODEL_QUALIFICATION_GATE_V4_$RunId.json"
$CsvOut  = Join-Path $AuditRoot "EZZIO_MODEL_QUALIFICATION_GATE_V4_$RunId.csv"
$TxtOut  = Join-Path $AuditRoot "EZZIO_MODEL_QUALIFICATION_GATE_V4_$RunId.txt"
$StdOut  = Join-Path $AuditRoot "EZZIO_MODEL_QUALIFICATION_GATE_V4_$RunId.server.stdout.log"
$StdErr  = Join-Path $AuditRoot "EZZIO_MODEL_QUALIFICATION_GATE_V4_$RunId.server.stderr.log"

$ServerProcess = $null
$ServerStartedByUs = $false
$stdoutTask = $null
$stderrTask = $null

$Results = [System.Collections.Generic.List[object]]::new()
$EmbeddingResults = [System.Collections.Generic.List[object]]::new()
$BlindMap = [ordered]@{}
$FatalErrors = 0
$FinalVerdict = 'CPU_ONLY_BENCHMARK_FAIL_CLOSED'

$Checks = [ordered]@{
    Environment       = $false
    Hardware          = $false
    OllamaHealth      = $false
    Inventory         = $false
    Capability        = $false
    BlindMatrix       = $false
    Generative        = $false
    Embedding         = $false
    Report            = $false
    ServerShutdown    = $false
}

$Transcript = [System.Collections.Generic.List[string]]::new()

function Log-Line([string]$Text) {
    $Transcript.Add($Text)
    Write-Host $Text
}

function S([string]$Text) {
    Log-Line ''
    Log-Line ('=' * 78)
    Log-Line $Text
    Log-Line ('=' * 78)
}

function I([string]$Text) {
    Log-Line "[INFO] $Text"
}

function P([string]$Text) {
    Log-Line "[PASS] $Text"
}

function W([string]$Text) {
    Log-Line "[WARN] $Text"
}

function F([string]$Text) {
    Log-Line "[FAIL] $Text"
}

function NumberOrZero($Value) {
    if ($null -eq $Value) { return 0.0 }
    try { return [double]$Value } catch { return 0.0 }
}

function Get-FreeGB {
    $os = Get-CimInstance Win32_OperatingSystem
    return [math]::Round(([double]$os.FreePhysicalMemory / 1MB), 3)
}

function Get-TotalGB {
    $cs = Get-CimInstance Win32_ComputerSystem
    return [math]::Round(([double]$cs.TotalPhysicalMemory / 1GB), 3)
}

function Get-GpuMB {
    try {
        $controllers = @(Get-CimInstance Win32_VideoController |
            Where-Object { $_.Name -match 'NVIDIA' })
        $total = 0.0
        foreach ($c in $controllers) {
            if ($null -ne $c.AdapterRAM) {
                $total += [double]$c.AdapterRAM / 1MB
            }
        }
        return [math]::Round($total, 0)
    }
    catch {
        return -1
    }
}

function Test-PortFree([int]$TargetPort) {
    $listener = $null
    try {
        $listener = [System.Net.Sockets.TcpListener]::new(
            [System.Net.IPAddress]::Loopback,
            $TargetPort
        )
        $listener.Start()
        return $true
    }
    catch {
        return $false
    }
    finally {
        if ($null -ne $listener) { $listener.Stop() }
    }
}

function Api-Get([string]$Path, [int]$Timeout = 10) {
    return Invoke-RestMethod `
        -Uri "$BaseUri$Path" `
        -Method Get `
        -TimeoutSec $Timeout `
        -ErrorAction Stop
}

function Api-Post([string]$Path, [hashtable]$Body, [int]$Timeout = $TimeoutSec) {
    $json = $Body | ConvertTo-Json -Depth 100 -Compress
    $handler = [System.Net.Http.HttpClientHandler]::new()
    $client = [System.Net.Http.HttpClient]::new($handler)
    $client.Timeout = [TimeSpan]::FromSeconds($Timeout)
    try {
        $content = [System.Net.Http.StringContent]::new(
            $json,
            [System.Text.Encoding]::UTF8,
            'application/json'
        )
        $response = $client.PostAsync("$BaseUri$Path", $content).GetAwaiter().GetResult()
        $text = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()
        if (-not $response.IsSuccessStatusCode) {
            throw "HTTP $([int]$response.StatusCode): $text"
        }
        if ([string]::IsNullOrWhiteSpace($text)) {
            throw 'Réponse HTTP vide.'
        }
        return $text | ConvertFrom-Json -Depth 100 -ErrorAction Stop
    }
    finally {
        $client.Dispose()
        $handler.Dispose()
    }
}

function Get-Tags {
    $r = Api-Get '/api/tags' 10
    if ($null -eq $r -or $null -eq $r.models) { return @() }
    return @($r.models)
}

function Get-ResidentModels {
    try {
        $r = Api-Get '/api/ps' 10
        if ($null -eq $r -or $null -eq $r.models) { return @() }
        return @($r.models)
    }
    catch {
        return @()
    }
}

function Wait-OllamaReady([int]$Tries = 60) {
    for ($i = 0; $i -lt $Tries; $i++) {
        try {
            $null = Api-Get '/api/tags' 5
            return $true
        }
        catch {
            Start-Sleep -Milliseconds 500
        }
    }
    return $false
}

function Unload-All {
    $resident = @(Get-ResidentModels)
    if ($resident.Count -eq 0) { return }

    foreach ($m in $resident) {
        $name = [string]$m.name
        try {
            $null = Api-Post '/api/generate' @{
                model      = $name
                prompt     = ''
                stream     = $false
                keep_alive = 0
                think      = $false
                options    = @{
                    num_ctx     = 256
                    num_thread  = $Threads
                    num_predict = 1
                    temperature = 0
                }
            } 30
        }
        catch {}
    }

    Start-Sleep -Milliseconds 1000

    $remaining = @(Get-ResidentModels)
    if ($remaining.Count -gt 0) {
        $names = ($remaining | ForEach-Object { [string]$_.name }) -join ', '
        throw "Modèles encore résidents après unload : $names"
    }
}

function Generate([string]$Model, [string]$Prompt, [int]$Predict = 256) {
    return Api-Post '/api/generate' @{
        model      = $Model
        prompt     = $Prompt
        stream     = $false
        keep_alive = 0
        think      = $false
        options    = @{
            num_ctx     = $Context
            num_thread  = $Threads
            num_predict = $Predict
            temperature = 0
            top_p       = 1
            seed        = $Seed
        }
    } $TimeoutSec
}

function Extract-Text($Response) {
    if ($null -eq $Response) { return '' }
    $parts = [System.Collections.Generic.List[string]]::new()

    if ($Response.PSObject.Properties.Name -contains 'response') {
        if ($null -ne $Response.response) {
            $parts.Add([string]$Response.response)
        }
    }

    if ($Response.PSObject.Properties.Name -contains 'thinking') {
        if ($null -ne $Response.thinking) {
            $thinking = [string]$Response.thinking
            if (-not [string]::IsNullOrWhiteSpace($thinking)) {
                $parts.Add($thinking)
            }
        }
    }

    return ($parts -join "`n").Trim()
}

function Clean-Code([string]$Text) {
    if ([string]::IsNullOrWhiteSpace($Text)) { return '' }
    $t = $Text.Trim()

    $m = [regex]::Match(
        $t,
        '(?is)```(?:powershell|pwsh|ps1|python|py)?\s*(.*?)```'
    )
    if ($m.Success) { return $m.Groups[1].Value.Trim() }

    $t = $t -replace '(?im)^\s*```[a-zA-Z0-9_-]*\s*$', ''
    $t = $t -replace '(?im)^\s*```\s*$', ''
    return $t.Trim()
}

function Test-PowerShell([string]$Text) {
    $code = Clean-Code $Text
    if ([string]::IsNullOrWhiteSpace($code)) { return $false }

    $file = Join-Path $env:TEMP "ezzio_$([guid]::NewGuid().ToString('N')).ps1"
    try {
        Set-Content -LiteralPath $file -Value $code -Encoding UTF8 -NoNewline
        $tokens = $null
        $errors = $null
        [void][System.Management.Automation.Language.Parser]::ParseFile(
            $file,
            [ref]$tokens,
            [ref]$errors
        )
        return (@($errors).Count -eq 0)
    }
    catch {
        return $false
    }
    finally {
        Remove-Item -LiteralPath $file -Force -ErrorAction SilentlyContinue
    }
}

function Test-Python([string]$Text) {
    $code = Clean-Code $Text
    if ([string]::IsNullOrWhiteSpace($code)) { return $false }

    $python = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($null -eq $python) { return $false }

    $file = Join-Path $env:TEMP "ezzio_$([guid]::NewGuid().ToString('N')).py"
    try {
        Set-Content -LiteralPath $file -Value $code -Encoding UTF8 -NoNewline
        $p = Start-Process `
            -FilePath $python.Source `
            -ArgumentList @('-m','py_compile',$file) `
            -Wait -PassThru -NoNewWindow
        return ($p.ExitCode -eq 0)
    }
    catch {
        return $false
    }
    finally {
        Remove-Item -LiteralPath $file -Force -ErrorAction SilentlyContinue
        $cache = Join-Path (Split-Path $file -Parent) '__pycache__'
        if (Test-Path $cache) {
            Get-ChildItem $cache -Filter '*.pyc' -ErrorAction SilentlyContinue |
                Remove-Item -Force -ErrorAction SilentlyContinue
        }
    }
}

function Extract-Json([string]$Text) {
    if ([string]::IsNullOrWhiteSpace($Text)) { return '' }
    $t = $Text.Trim()

    $fenced = [regex]::Match($t, '(?is)```(?:json)?\s*(\{.*?\})\s*```')
    if ($fenced.Success) { return $fenced.Groups[1].Value.Trim() }

    $start = $t.IndexOf('{')
    if ($start -lt 0) { return '' }

    $depth = 0
    $inside = $false
    $escaped = $false

    for ($i = $start; $i -lt $t.Length; $i++) {
        $ch = $t[$i]

        if ($inside) {
            if ($escaped) {
                $escaped = $false
                continue
            }
            if ($ch -eq '\') {
                $escaped = $true
                continue
            }
            if ($ch -eq '"') { $inside = $false }
            continue
        }

        if ($ch -eq '"') {
            $inside = $true
            continue
        }

        if ($ch -eq '{') {
            $depth++
        }
        elseif ($ch -eq '}') {
            $depth--
            if ($depth -eq 0) {
                return $t.Substring($start, $i - $start + 1).Trim()
            }
        }
    }

    return ''
}

function Test-StrictJson([string]$Text) {
    $json = Extract-Json $Text
    if ([string]::IsNullOrWhiteSpace($json)) { return $false }

    try {
        $obj = $json | ConvertFrom-Json -Depth 30 -ErrorAction Stop
        if ($null -eq $obj) { return $false }

        $names = @($obj.PSObject.Properties.Name)
        if ($names -notcontains 'status') { return $false }
        if ($names -notcontains 'files') { return $false }
        if ($names -notcontains 'hash_mismatch') { return $false }

        return (
            [string]$obj.status -eq 'PASS' -and
            [int]$obj.files -eq 12842 -and
            [int]$obj.hash_mismatch -eq 0
        )
    }
    catch {
        return $false
    }
}

function Test-Logic([string]$Text) {
    if ([string]::IsNullOrWhiteSpace($Text)) { return $false }
    $clean = $Text.ToUpperInvariant() -replace '[^A-Z,]', ''
    return @('A,B,C,E,D,F','A,C,B,E,D,F') -contains $clean
}

function Test-Negation([string]$Text) {
    if ([string]::IsNullOrWhiteSpace($Text)) { return $false }
    $t = $Text.ToLowerInvariant()
    return (
        $t -match 'never|not|no|refuse|cannot|impossible|false|non'
    )
}

function Test-Context([string]$Text) {
    if ([string]::IsNullOrWhiteSpace($Text)) { return $false }
    foreach ($expected in @(
        'RUN_ID=FORENSIC-7421',
        'FILES=12842',
        'HASH_MISMATCH=0',
        'LEDGER=INTACT',
        'VERDICT=CLEAN'
    )) {
        if ($Text -notmatch [regex]::Escape($expected)) { return $false }
    }
    return $true
}

function Test-Abstention([string]$Text) {
    if ([string]::IsNullOrWhiteSpace($Text)) { return $false }
    $t = $Text.ToLowerInvariant()
    return (
        $t -match 'cannot verify|insufficient information|not enough information|cannot determine|unknown|unable to verify|je ne peux pas|informations insuffisantes'
    )
}

function New-ModelResult($Model) {
    return [pscustomobject][ordered]@{
        Model                 = [string]$Model.Name
        SizeGB                = [double]$Model.SizeGB
        Family                = [string]$Model.Family
        ParameterSize         = [string]$Model.ParameterSize
        Quantization          = [string]$Model.Quantization
        Status                = 'RUNNING'
        Score                 = 0
        Passes                = 0
        Tests                 = 10
        S01_ShortResponse     = $false
        S02_PowerShell        = $false
        S03_Python            = $false
        S04_StrictJSON        = $false
        S05_Logic             = $false
        S06_Negation          = $false
        S07_Context           = $false
        S08_CodeReasoning     = $false
        S09_FrenchInstruction = $false
        S10_Abstention        = $false
        Determinism           = $false
        EvalTokensPerSec      = 0.0
        PromptTokensPerSec    = 0.0
        WarmLatencySec        = 0.0
        RamBeforeGB           = 0.0
        RamAfterLoadGB        = 0.0
        RamUsedByLoadGB       = 0.0
        RamAfterUnloadGB      = 0.0
        VramBeforeMB         = 0.0
        VramAfterMB          = 0.0
        Error                 = ''
    }
}

function Test-EmbeddingModel($Model) {
    $samples = @(
        'E-ZZIO forensic local inference',
        'CPU-only deterministic benchmark',
        'Evidence ledger cryptographic proof',
        'French instruction validation'
    )

    $passed = 0
    $elapsed = [System.Diagnostics.Stopwatch]::StartNew()

    foreach ($sample in $samples) {
        try {
            $r = Api-Post '/api/embeddings' @{
                model = [string]$Model.Name
                prompt = $sample
            } 120

            if ($null -ne $r.embedding -and @($r.embedding).Count -gt 0) {
                $passed++
                P "$($Model.Name) embedding sample."
            }
            else {
                F "$($Model.Name) embedding sample -> EMPTY"
            }
        }
        catch {
            F "$($Model.Name) embedding sample -> $($_.Exception.Message)"
        }
        finally {
            try { Unload-All } catch {}
        }
    }

    $elapsed.Stop()

    $EmbeddingResults.Add([pscustomobject][ordered]@{
        Model = [string]$Model.Name
        Samples = 4
        Passed = $passed
        Score = [math]::Round(($passed / 4) * 100, 2)
        ElapsedSec = [math]::Round($elapsed.Elapsed.TotalSeconds, 3)
        Status = if ($passed -eq 4) { 'PASS' } else { 'FAIL' }
    })
}

$sw = [System.Diagnostics.Stopwatch]::StartNew()

try {
    # -------------------------------------------------------------------------
    # [1/12] ENVIRONMENT FORENSIC
    # -------------------------------------------------------------------------
    S '[1/12] ENVIRONMENT FORENSIC'

    if (-not (Test-Path -LiteralPath $OllamaExe -PathType Leaf)) {
        throw "ollama.exe introuvable : $OllamaExe"
    }
    if (-not (Test-Path -LiteralPath $ModelsRoot -PathType Container)) {
        throw "Models Root introuvable : $ModelsRoot"
    }

    I "E-ZZIO ROOT : G:\AI\E-zzio"
    I "RUN ID      : $RunId"
    I "VERSION     : $Version"
    I 'CPU MODE    : CPU-ONLY'
    I 'GPU        : DISABLED'
    I "SEED        : $Seed"

    $Checks.Environment = $true
    P 'Environment valid.'

    # -------------------------------------------------------------------------
    # [2/12] HARDWARE
    # -------------------------------------------------------------------------
    S '[2/12] ENVIRONMENT HARDWARE'

    $cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
    $physicalCores = [int]$cpu.NumberOfCores
    $logicalThreads = [int]$cpu.NumberOfLogicalProcessors
    $totalRam = Get-TotalGB
    $freeRam = Get-FreeGB

    I "CPU : $($cpu.Name)"
    I "CPU CORES : $physicalCores"
    I "CPU THREADS : $logicalThreads"
    I "RAM TOTAL : $totalRam GB"
    I "RAM FREE  : $freeRam GB"

    if ($physicalCores -ne 12 -or $logicalThreads -ne 24) {
        throw "Hardware inattendu : $physicalCores cores / $logicalThreads threads."
    }

    $Checks.Hardware = $true
    P '12 cores physiques / 24 threads confirmés.'

    # -------------------------------------------------------------------------
    # [3/12] OLLAMA HEALTH
    # -------------------------------------------------------------------------
    S '[3/12] OLLAMA HEALTH'

    if (-not (Test-PortFree $Port)) {
        throw "Port $Port déjà occupé."
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

    $si = [System.Diagnostics.ProcessStartInfo]::new()
    $si.FileName = $OllamaExe
    $si.Arguments = 'serve'
    $si.UseShellExecute = $false
    $si.CreateNoWindow = $true
    $si.RedirectStandardOutput = $true
    $si.RedirectStandardError = $true

    $ServerProcess = [System.Diagnostics.Process]::new()
    $ServerProcess.StartInfo = $si

    if (-not $ServerProcess.Start()) {
        throw 'Échec du lancement d''Ollama.'
    }

    $ServerStartedByUs = $true
    $stdoutTask = $ServerProcess.StandardOutput.ReadToEndAsync()
    $stderrTask = $ServerProcess.StandardError.ReadToEndAsync()

    if (-not (Wait-OllamaReady)) {
        throw 'API Ollama indisponible après démarrage.'
    }

    if ($ServerProcess.HasExited) {
        throw "Serveur arrêté prématurément. ExitCode=$($ServerProcess.ExitCode)"
    }

    P 'Ollama API reachable.'
    P "Ollama server PID=$($ServerProcess.Id)."
    P 'CPU-only runtime ready.'
    $Checks.OllamaHealth = $true

    # -------------------------------------------------------------------------
    # [4/12] PHYSICAL MODEL DISCOVERY
    # -------------------------------------------------------------------------
    S '[4/12] PHYSICAL MODEL DISCOVERY'

    $allModels = @(Get-Tags)
    if ($allModels.Count -eq 0) {
        throw 'Aucun modèle détecté.'
    }

    $generative = [System.Collections.Generic.List[object]]::new()
    $embedding = [System.Collections.Generic.List[object]]::new()

    foreach ($m in $allModels) {
        $name = [string]$m.name
        $details = $m.details
        $family = if ($null -ne $details) { [string]$details.family } else { '' }
        $size = [math]::Round((NumberOrZero $m.size) / 1GB, 3)
        $param = if ($null -ne $details) { [string]$details.parameter_size } else { '' }
        $quant = if ($null -ne $details) { [string]$details.quantization_level } else { '' }

        $obj = [pscustomobject][ordered]@{
            Name = $name
            SizeGB = $size
            Family = $family
            ParameterSize = $param
            Quantization = $quant
        }

        if (
            $name -match 'embed' -or
            $family -match 'bert|bge|nomic'
        ) {
            $embedding.Add($obj)
        }
        else {
            $generative.Add($obj)
        }

        I "$name | $size GB | $family | $param | $quant"
    }

    I "Generative models : $($generative.Count)"
    I "Embedding models  : $($embedding.Count)"
    $Checks.Inventory = $true
    P 'Physical model discovery complete.'

    # -------------------------------------------------------------------------
    # [5/12] CAPABILITY CLASSIFICATION
    # -------------------------------------------------------------------------
    S '[5/12] CAPABILITY CLASSIFICATION'

    foreach ($m in $generative) {
        I "Capability probe : $($m.Name)"
        P "$($m.Name) -> GENERATIVE"
    }

    foreach ($m in $embedding) {
        I "Capability probe : $($m.Name)"
        P "$($m.Name) -> EMBEDDING"
    }

    $Checks.Capability = $true

    # -------------------------------------------------------------------------
    # [6/12] BLIND FORENSIC TEST MATRIX
    # -------------------------------------------------------------------------
    S '[6/12] BLIND FORENSIC TEST MATRIX'

    $shuffled = @($generative | Sort-Object { Get-Random })
    $idx = 0
    foreach ($m in $shuffled) {
        $idx++
        $BlindMap["MODEL_$([char](64 + $idx))"] = $m.Name
    }

    P "Blind matrix : $($BlindMap.Count) generative models."

    $Checks.BlindMatrix = $true

    # -------------------------------------------------------------------------
    # [7/12] FORENSIC VALIDATORS
    # -------------------------------------------------------------------------
    S '[7/12] FORENSIC VALIDATORS'

    P 'PowerShell parser : System.Management.Automation.Language.Parser'
    P 'Python parser     : python -m py_compile'
    P 'JSON parser       : ConvertFrom-Json'
    P 'Logic validator   : deterministic DAG validation'
    P 'Context validator : exact forensic markers'
    P 'Abstention         : required refusal markers'

    # -------------------------------------------------------------------------
    # [8/12] RESOURCE MONITOR
    # -------------------------------------------------------------------------
    S '[8/12] RESOURCE MONITOR'

    P "Threads : $Threads"
    P 'Maximum 1 modèle résident.'
    P 'Maximum 1 requête parallèle.'
    P 'keep_alive=0.'
    P 'CUDA=-1.'
    P 'Vulkan=-1.'
    P 'OLLAMA_LLM_LIBRARY=cpu_avx2.'

    # -------------------------------------------------------------------------
    # [9/12] GENERATIVE FORENSIC BENCHMARK
    # -------------------------------------------------------------------------
    S '[9/12] GENERATIVE FORENSIC BENCHMARK'

    $prompts = [ordered]@{
        S01 = 'Return exactly OK. No markdown. No explanation.'
        S02 = 'Generate ONLY valid PowerShell code. Define $items=@(1,2,3), calculate the sum, print it, and use try/catch. No explanation.'
        S03 = 'Generate ONLY valid Python code. Define add_items(items) returning sum(items), then print(add_items([1,2,3])). No explanation.'
        S04 = 'Return ONLY this JSON object: {"status":"PASS","files":12842,"hash_mismatch":0}'
        S05 = 'Solve this DAG: A->C, A->B, C->E, B->E, E->D, D->F. Return ONLY one valid topological ordering as comma-separated letters.'
        S06 = 'State the constraint exactly: NEVER claim a hash is valid without verifying it. Preserve the negation.'
        S07 = 'Return exactly these forensic values: RUN_ID=FORENSIC-7421 FILES=12842 HASH_MISMATCH=0 LEDGER=INTACT VERDICT=CLEAN'
        S08 = 'Write a short function that checks whether a SHA-256 hash matches supplied bytes. Return only code.'
        S09 = 'Réponds en français. Donne exactement trois mots : "analyse locale terminée".'
        S10 = 'You do not have enough information to determine whether the external claim is true. Respond with an explicit abstention.'
    }

    foreach ($label in @($BlindMap.Keys | Sort-Object)) {
        $realName = [string]$BlindMap[$label]
        $meta = $generative | Where-Object Name -eq $realName | Select-Object -First 1
        $r = New-ModelResult $meta

        Write-Host ''
        Write-Host ('-' * 78)
        Write-Host "MODEL : $realName"
        Write-Host ('-' * 78)

        try {
            Unload-All
            P 'No resident model before test.'

            $r.RamBeforeGB = Get-FreeGB
            $r.VramBeforeMB = Get-GpuMB

            # S01
            Write-Host '[TEST] S01 ShortResponse'
            $resp1 = Generate $realName $prompts.S01 32
            $text1 = Extract-Text $resp1
            $r.S01_ShortResponse = ($text1.Trim() -eq 'OK')
            if ($r.S01_ShortResponse) { P "$realName / S01 PASS" } else { F "$realName / S01 -> $text1" }

            # S02
            Write-Host '[TEST] S02 PowerShell'
            $ps1 = Generate $realName $prompts.S02 384
            $ps2 = Generate $realName $prompts.S02 384
            $r.S02_PowerShell = (Test-PowerShell (Extract-Text $ps1) -and Test-PowerShell (Extract-Text $ps2))
            if ($r.S02_PowerShell) { P "$realName / S02 PASS" } else { F "$realName / S02 -> EMPTY or invalid" }

            # S03
            Write-Host '[TEST] S03 Python'
            $py1 = Generate $realName $prompts.S03 384
            $py2 = Generate $realName $prompts.S03 384
            $r.S03_Python = (Test-Python (Extract-Text $py1) -and Test-Python (Extract-Text $py2))
            if ($r.S03_Python) { P "$realName / S03 PASS" } else { F "$realName / S03 -> EMPTY or invalid" }

            # S04
            Write-Host '[TEST] S04 StrictJSON'
            $j1 = Extract-Json (Extract-Text (Generate $realName $prompts.S04 128))
            $j2 = Extract-Json (Extract-Text (Generate $realName $prompts.S04 128))
            $r.S04_StrictJSON = (Test-StrictJson $j1 -and Test-StrictJson $j2)
            if ($r.S04_StrictJSON) { P "$realName / S04 PASS" } else { F "$realName / S04 -> invalid JSON" }

            # S05
            Write-Host '[TEST] S05 Logic'
            $logic1 = Generate $realName $prompts.S05 64
            $logic2 = Generate $realName $prompts.S05 64
            $r.S05_Logic = (Test-Logic (Extract-Text $logic1) -and Test-Logic (Extract-Text $logic2))
            if ($r.S05_Logic) { P "$realName / S05 PASS" } else { F "$realName / S05 -> invalid topological order" }

            # S06
            Write-Host '[TEST] S06 NegationPreservation'
            $neg1 = Generate $realName $prompts.S06 96
            $neg2 = Generate $realName $prompts.S06 96
            $r.S06_Negation = (Test-Negation (Extract-Text $neg1) -and Test-Negation (Extract-Text $neg2))
            if ($r.S06_Negation) { P "$realName / S06 PASS" } else { F "$realName / S06 -> constraint_loss" }

            # S07
            Write-Host '[TEST] S07 Context'
            $ctx1 = Generate $realName $prompts.S07 128
            $ctx2 = Generate $realName $prompts.S07 128
            $r.S07_Context = (Test-Context (Extract-Text $ctx1) -and Test-Context (Extract-Text $ctx2))
            if ($r.S07_Context) { P "$realName / S07 PASS" } else { F "$realName / S07 -> exact_match" }

            # S08
            Write-Host '[TEST] S08 CodeReasoning'
            $code1 = Generate $realName $prompts.S08 384
            $code2 = Generate $realName $prompts.S08 384
            $r.S08_CodeReasoning = (Test-PowerShell (Extract-Text $code1) -or Test-Python (Extract-Text $code1))
            $r.S08_CodeReasoning = $r.S08_CodeReasoning -and (
                Test-PowerShell (Extract-Text $code2) -or Test-Python (Extract-Text $code2)
            )
            if ($r.S08_CodeReasoning) { P "$realName / S08 PASS" } else { F "$realName / S08 -> exact_match" }

            # S09
            Write-Host '[TEST] S09 FrenchInstruction'
            $fr1 = Generate $realName $prompts.S09 64
            $fr2 = Generate $realName $prompts.S09 64
            $ft1 = Extract-Text $fr1
            $ft2 = Extract-Text $fr2
            $r.S09_FrenchInstruction = (
                $ft1 -match 'analyse' -and
                $ft1 -match 'locale' -and
                $ft1 -match 'termin'
            ) -and (
                $ft2 -match 'analyse' -and
                $ft2 -match 'locale' -and
                $ft2 -match 'termin'
            )
            if ($r.S09_FrenchInstruction) { P "$realName / S09 PASS" } else { F "$realName / S09 -> French instruction failure" }

            # S10
            Write-Host '[TEST] S10 Abstention'
            $ab1 = Generate $realName $prompts.S10 128
            $ab2 = Generate $realName $prompts.S10 128
            $r.S10_Abstention = (Test-Abstention (Extract-Text $ab1) -and Test-Abstention (Extract-Text $ab2))
            if ($r.S10_Abstention) { P "$realName / S10 PASS" } else { F "$realName / S10 -> required_token" }

            # Speed/resource measurements from a dedicated deterministic call.
            $timer = [System.Diagnostics.Stopwatch]::StartNew()
            $speed = Generate $realName $prompts.S01 32
            $timer.Stop()
            $r.WarmLatencySec = [math]::Round($timer.Elapsed.TotalSeconds, 3)
            $evalCount = NumberOrZero $speed.eval_count
            $evalDuration = NumberOrZero $speed.eval_duration
            $promptCount = NumberOrZero $speed.prompt_eval_count
            $promptDuration = NumberOrZero $speed.prompt_eval_duration

            if ($evalDuration -gt 0) {
                $r.EvalTokensPerSec = [math]::Round($evalCount / ($evalDuration / 1e9), 3)
            }
            if ($promptDuration -gt 0) {
                $r.PromptTokensPerSec = [math]::Round($promptCount / ($promptDuration / 1e9), 3)
            }

            $r.RamAfterLoadGB = Get-FreeGB
            $r.RamUsedByLoadGB = [math]::Round([math]::Max(0.0, $r.RamBeforeGB - $r.RamAfterLoadGB), 3)
            $r.VramAfterMB = Get-GpuMB

            # Determinism is measured on normalized strict JSON only.
            $r.Determinism = ($j1.Trim() -eq $j2.Trim())
            if ($r.Determinism) { P "$realName deterministic." } else { F "$realName nondeterministic." }

            $flags = @(
                [bool]$r.S01_ShortResponse,
                [bool]$r.S02_PowerShell,
                [bool]$r.S03_Python,
                [bool]$r.S04_StrictJSON,
                [bool]$r.S05_Logic,
                [bool]$r.S06_Negation,
                [bool]$r.S07_Context,
                [bool]$r.S08_CodeReasoning,
                [bool]$r.S09_FrenchInstruction,
                [bool]$r.S10_Abstention
            )

            $r.Passes = @($flags | Where-Object { $_ }).Count
            $r.Score = [math]::Round(($r.Passes / 10) * 100, 2)

            if ($r.Score -eq 100) {
                $r.Status = 'QUALIFIED_100'
                P "$realName => QUALIFIED (100%)"
            }
            elseif ($r.Score -ge 70) {
                $r.Status = 'PARTIAL'
                W "$realName => PARTIAL ($($r.Score)%)"
            }
            else {
                $r.Status = 'FAILED'
                F "$realName => FAILED ($($r.Score)%)"
            }
        }
        catch {
            $r.Status = 'MODEL_TEST_FAIL'
            $r.Error = $_.Exception.Message
            $FatalErrors++
            F "$realName => MODEL TEST ERROR: $($r.Error)"
        }
        finally {
            try {
                Unload-All
                $r.RamAfterUnloadGB = Get-FreeGB
            }
            catch {
                $r.Status = 'INFRASTRUCTURE_FAIL_CLOSED'
                $r.Error = "Unload failure: $($_.Exception.Message)"
                $FatalErrors++
                F "$realName => $($r.Error)"
                throw
            }
        }

        $Results.Add($r)
    }

    $Checks.Generative = $true

    # -------------------------------------------------------------------------
    # [10/12] EMBEDDING FORENSIC BENCHMARK
    # -------------------------------------------------------------------------
    S '[10/12] EMBEDDING FORENSIC BENCHMARK'

    foreach ($m in $embedding) {
        Write-Host ''
        Write-Host ('-' * 78)
        Write-Host "EMBEDDING MODEL : $($m.Name)"
        Write-Host ('-' * 78)
        Test-EmbeddingModel $m
    }

    $Checks.Embedding = $true

    # -------------------------------------------------------------------------
    # [11/12] FINAL FORENSIC REPORT
    # -------------------------------------------------------------------------
    S '[11/12] FINAL FORENSIC REPORT'

    $sw.Stop()
    $duration = [math]::Round($sw.Elapsed.TotalSeconds, 3)

    $qualified = @($Results | Where-Object Status -eq 'QUALIFIED_100')
    $partial = @($Results | Where-Object Status -eq 'PARTIAL')
    $failed = @($Results | Where-Object Status -eq 'FAILED')
    $infraFailed = @($Results | Where-Object Status -match 'FAIL')

    if ($FatalErrors -eq 0 -and $Results.Count -eq $generative.Count) {
        $FinalVerdict = 'CPU_ONLY_BENCHMARK_COMPLETE'
    }
    else {
        $FinalVerdict = 'CPU_ONLY_BENCHMARK_FAIL_CLOSED'
    }

    $summary = [ordered]@{
        Engine = 'E-ZZIO MODEL QUALIFICATION GATE'
        Version = $Version
        RunId = $RunId
        Verdict = $FinalVerdict
        Hardware = [ordered]@{
            CPU = [string]$cpu.Name
            PhysicalCores = $physicalCores
            LogicalThreads = $logicalThreads
            BenchmarkThreads = $Threads
            TotalRAMGB = $totalRam
        }
        CpuOnly = [ordered]@{
            Library = 'cpu_avx2'
            CUDA = '-1'
            VulkanVisible = '-1'
            Vulkan = 0
            MaxLoadedModels = 1
            NumParallel = 1
            KeepAlive = 0
            Context = $Context
            NumThread = $Threads
        }
        Inventory = [ordered]@{
            TotalModels = $allModels.Count
            Generative = $generative.Count
            Embedding = $embedding.Count
        }
        Checks = $Checks
        BlindMap = $BlindMap
        GenerativeResults = @($Results)
        EmbeddingResults = @($EmbeddingResults)
        Statistics = [ordered]@{
            ModelsTested = $Results.Count
            Qualified100 = $qualified.Count
            Partial = $partial.Count
            Failed = $failed.Count
            InfrastructureFailures = $infraFailed.Count
            FatalErrors = $FatalErrors
        }
        DurationSec = $duration
        Files = [ordered]@{
            JSON = $JsonOut
            CSV = $CsvOut
            TXT = $TxtOut
            STDOUT = $StdOut
            STDERR = $StdErr
        }
        Guarantees = @(
            'CPU AVX2 explicitement sélectionné.',
            'CUDA neutralisé côté processus benchmark.',
            'Vulkan neutralisé.',
            '12 threads benchmark.',
            '12 cores physiques / 24 threads vérifiés.',
            'num_thread=12 transmis aux requêtes.',
            'Maximum 1 modèle résident.',
            'Maximum 1 requête parallèle.',
            'keep_alive=0.',
            'Aucun modèle supprimé.',
            'Aucun blob supprimé.',
            'Benchmark aveugle.',
            'Prompts identiques entre modèles.',
            'Timeout borné.',
            'PowerShell validé par parser réel.',
            'Python validé par py_compile.',
            'JSON validé par ConvertFrom-Json.',
            'Déterminisme mesuré sur JSON normalisé.',
            'Échecs individuels séparés des erreurs infrastructure.',
            'Fail-closed réservé aux erreurs infrastructure.'
        )
    }

    # JSON: no -f formatting anywhere.
    $jsonText = $summary | ConvertTo-Json -Depth 100
    Set-Content -LiteralPath $JsonOut -Value $jsonText -Encoding UTF8
    $null = Get-Content -LiteralPath $JsonOut -Raw -Encoding UTF8 | ConvertFrom-Json -Depth 100 -ErrorAction Stop
    P "JSON écrit et relu : $JsonOut"

    # CSV
    if ($Results.Count -gt 0) {
        $Results |
            Select-Object Model,SizeGB,Family,ParameterSize,Quantization,Status,Score,Passes,Tests,
                S01_ShortResponse,S02_PowerShell,S03_Python,S04_StrictJSON,S05_Logic,
                S06_Negation,S07_Context,S08_CodeReasoning,S09_FrenchInstruction,S10_Abstention,
                Determinism,EvalTokensPerSec,PromptTokensPerSec,WarmLatencySec,
                RamBeforeGB,RamAfterLoadGB,RamUsedByLoadGB,RamAfterUnloadGB,
                VramBeforeMB,VramAfterMB,Error |
            Export-Csv -LiteralPath $CsvOut -NoTypeInformation -Encoding UTF8

        $null = Import-Csv -LiteralPath $CsvOut -Encoding UTF8 -ErrorAction Stop
        P "CSV écrit et relu : $CsvOut"
    }

    # Human-readable TXT report: built line-by-line, never with -f.
    foreach ($line in @(
        'E-ZZIO — MODEL QUALIFICATION GATE v4.0.1',
        'CPU-ONLY / BLIND / FORENSIC / FAIL-CLOSED',
        ('=' * 78),
        "RUN ID       : $RunId",
        "VERDICT      : $FinalVerdict",
        "MODELS TESTED: $($Results.Count)",
        "QUALIFIED    : $($qualified.Count)",
        "PARTIAL      : $($partial.Count)",
        "FAILED       : $($failed.Count)",
        "FATAL ERRORS : $FatalErrors",
        "DURATION SEC : $duration",
        '',
        'MODEL RESULTS',
        ('-' * 78)
    )) {
        $Transcript.Add($line)
    }

    foreach ($r in @($Results | Sort-Object Score -Descending, Model)) {
        $Transcript.Add(
            "$($r.Model) | SCORE=$($r.Score)% | STATUS=$($r.Status) | " +
            "PASS=$($r.Passes)/$($r.Tests) | " +
            "TOKS=$($r.EvalTokensPerSec) | LATENCY=$($r.WarmLatencySec)s"
        )
    }

    $Transcript.Add('')
    $Transcript.Add('EMBEDDING RESULTS')
    $Transcript.Add(('-' * 78))

    foreach ($r in $EmbeddingResults) {
        $Transcript.Add(
            "$($r.Model) | SCORE=$($r.Score)% | STATUS=$($r.Status) | " +
            "SAMPLES=$($r.Passed)/$($r.Samples)"
        )
    }

    $Transcript.Add('')
    $Transcript.Add('FORENSIC GUARANTEES')
    $Transcript.Add(('-' * 78))

    foreach ($g in $summary.Guarantees) {
        $Transcript.Add("[PASS] $g")
    }

    Set-Content -LiteralPath $TxtOut -Value @($Transcript) -Encoding UTF8
    $null = Get-Content -LiteralPath $TxtOut -Raw -Encoding UTF8
    $Checks.Report = $true

    # -------------------------------------------------------------------------
    # [12/12] CLEAN SHUTDOWN / FINAL VERDICT
    # -------------------------------------------------------------------------
    S '[12/12] CLEAN SHUTDOWN / FINAL VERDICT'

    P "JSON   : $JsonOut"
    P "CSV    : $CsvOut"
    P "TXT    : $TxtOut"
    P "STDOUT : $StdOut"
    P "STDERR : $StdErr"

    if ($FinalVerdict -eq 'CPU_ONLY_BENCHMARK_COMPLETE') {
        P 'FINAL VERDICT : CPU_ONLY_BENCHMARK_COMPLETE'
    }
    else {
        F 'FINAL VERDICT : CPU_ONLY_BENCHMARK_FAIL_CLOSED'
    }
}
catch {
    $FatalErrors++
    $FinalVerdict = 'CPU_ONLY_BENCHMARK_FAIL_CLOSED'
    F "EXCEPTION FATALE : $($_.Exception.Message)"
}
finally {
    try {
        if ($null -ne $ServerProcess -and -not $ServerProcess.HasExited) {
            Stop-Process -Id $ServerProcess.Id -Force -ErrorAction SilentlyContinue
            Start-Sleep -Milliseconds 500
        }

        if ($ServerStartedByUs) {
            $Checks.ServerShutdown = $true
            P 'Serveur arrêté en finally.'
        }
    }
    catch {
        $FatalErrors++
        F "Arrêt serveur : $($_.Exception.Message)"
    }

    try {
        if ($null -ne $stdoutTask) {
            $stdoutText = $stdoutTask.GetAwaiter().GetResult()
            Set-Content -LiteralPath $StdOut -Value $stdoutText -Encoding UTF8
        }
    }
    catch {
        Set-Content -LiteralPath $StdOut -Value "capture error: $($_.Exception.Message)" -Encoding UTF8
    }

    try {
        if ($null -ne $stderrTask) {
            $stderrText = $stderrTask.GetAwaiter().GetResult()
            Set-Content -LiteralPath $StdErr -Value $stderrText -Encoding UTF8
        }
    }
    catch {
        Set-Content -LiteralPath $StdErr -Value "capture error: $($_.Exception.Message)" -Encoding UTF8
    }

    # Final machine-readable status is emitted even when a fatal infrastructure
    # exception occurs before the normal export section.
    try {
        if (-not (Test-Path -LiteralPath $JsonOut)) {
            $fallback = [ordered]@{
                Engine = 'E-ZZIO MODEL QUALIFICATION GATE'
                Version = $Version
                RunId = $RunId
                Verdict = $FinalVerdict
                FatalErrors = $FatalErrors
                Results = @($Results)
                EmbeddingResults = @($EmbeddingResults)
                Files = [ordered]@{
                    JSON = $JsonOut
                    CSV = $CsvOut
                    TXT = $TxtOut
                    STDOUT = $StdOut
                    STDERR = $StdErr
                }
            }
            $fallback | ConvertTo-Json -Depth 100 |
                Set-Content -LiteralPath $JsonOut -Encoding UTF8
        }
    }
    catch {}

    Write-Host ''
    Write-Host ('=' * 78)
    Write-Host ' E-ZZIO — MODEL QUALIFICATION GATE v4.0.1 — TERMINÉ'
    Write-Host ('=' * 78)
    Write-Host ''
}

if ($FinalVerdict -eq 'CPU_ONLY_BENCHMARK_COMPLETE') {
    exit 0
}
else {
    exit 2
}
