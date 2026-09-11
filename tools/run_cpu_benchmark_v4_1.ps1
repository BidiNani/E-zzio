Set-Location "G:\AI\E-zzio"
$ErrorActionPreference = "Stop"

# ============================================================
# E-ZZIO — CPU MODEL BENCHMARK V4.1
# Host: AMD Ryzen 9 5900X (12C / 24T) | 32 GB DDR4-3200 | NVMe
# ============================================================

$OllamaUrl = "http://127.0.0.1:11434"
$ChatUrl   = "$OllamaUrl/api/chat"

# 8 modèles génératifs actifs (hors modèles d'embedding)
$Models = @(
    "phi4-mini:latest",
    "qwen3:8b",
    "Distendo/zen-pro:latest",
    "granite4.2:latest",
    "ornith-1.5:9b",
    "mrasif/gpt-oss-20b-GGUF:Q4_K_M",
    "hf.co/unsloth/Qwen3.8-27B-GGUF:UD-Q4_K_M",
    "qwen3-coder:30b"
)

# Grille de dimensionnement CPU
$ThreadGrid  = @(8, 12, 16, 20, 24)
$ContextGrid = @(2048, 4096, 8192)

$Repeats             = 1
$ConfirmationRepeats = 2
$TimeoutSec          = 900

$KeepAliveDuringModel = "30m"
$KeepAliveAfterModel  = "0"

$ReportDir = "tools\reports"
New-Item -ItemType Directory -Path $ReportDir -Force | Out-Null

$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"

$JsonReport    = Join-Path $ReportDir "cpu_model_benchmark_v4_1_$Stamp.json"
$CsvReport     = Join-Path $ReportDir "cpu_model_benchmark_v4_1_$Stamp.csv"
$ProfileReport = Join-Path $ReportDir "cpu_model_profiles_v4_1_$Stamp.json"

Write-Host "============================================================"
Write-Host " E-ZZIO — CPU MODEL BENCHMARK V4.1 (8 MODELES GENERATIFS)"
Write-Host "============================================================"
Write-Host "CPU        : AMD Ryzen 9 5900X (12C / 24T)"
Write-Host "RAM        : 32 GB DDR4-3200"
Write-Host "GPU        : DISABLED (CPU Only)"
Write-Host "Storage    : NVMe"
Write-Host "Threads    : 8 / 12 / 16 / 20 / 24"
Write-Host "Context    : 2048 / 4096 / 8192"
Write-Host "Quality    : Floor strict >= 80 (moyenne ET chaque sous-tâche)"
Write-Host "============================================================"
Write-Host ""

# ============================================================
# HELPER DE SÉRIALISATION IMMUABLE
# ============================================================

function Convert-ToJsonSafeObject {
    param([AllowNull()][object]$InputObject)

    if ($null -eq $InputObject) { return $null }

    if ($InputObject -is [string] -or
        $InputObject -is [char] -or
        $InputObject -is [bool] -or
        $InputObject -is [byte] -or
        $InputObject -is [sbyte] -or
        $InputObject -is [int16] -or
        $InputObject -is [uint16] -or
        $InputObject -is [int32] -or
        $InputObject -is [uint32] -or
        $InputObject -is [int64] -or
        $InputObject -is [uint64] -or
        $InputObject -is [single] -or
        $InputObject -is [double] -or
        $InputObject -is [decimal] -or
        $InputObject -is [datetime] -or
        $InputObject -is [guid]) {
        return $InputObject
    }

    if ($InputObject -is [System.Collections.IDictionary]) {
        $ordered = [ordered]@{}
        foreach ($key in $InputObject.Keys) {
            $ordered[[string]$key] = Convert-ToJsonSafeObject -InputObject $InputObject[$key]
        }
        return [pscustomobject]$ordered
    }

    if ($InputObject -is [System.Collections.IEnumerable]) {
        $array = @(
            foreach ($item in $InputObject) {
                Convert-ToJsonSafeObject -InputObject $item
            }
        )
        return $array
    }

    $properties = $InputObject.PSObject.Properties
    if ($properties.Count -gt 0) {
        $ordered = [ordered]@{}
        foreach ($property in $properties) {
            if ($property.MemberType -notmatch 'Property|NoteProperty|AliasProperty|ScriptProperty') {
                continue
            }
            try {
                $ordered[[string]$property.Name] = Convert-ToJsonSafeObject -InputObject $property.Value
            }
            catch {
                $ordered[[string]$property.Name] = $null
            }
        }
        return [pscustomobject]$ordered
    }

    return [string]$InputObject
}

# ============================================================
# OLLAMA INFERENCE ENGINE
# ============================================================

function Invoke-OllamaChat {
    param(
        [Parameter(Mandatory)][string]$Model,
        [Parameter(Mandatory)][AllowEmptyString()][string]$Prompt,
        [Parameter(Mandatory)][int]$Threads,
        [Parameter(Mandatory)][int]$Context,
        [Parameter(Mandatory)][int]$Predict,
        [Parameter(Mandatory)][double]$Temperature,
        [Parameter(Mandatory)][string]$KeepAlive
    )

    $payload = @{
        model    = $Model
        messages = @(
            @{
                role    = "user"
                content = $Prompt
            }
        )
        stream = $false
        think  = $false
        options = @{
            num_gpu     = 0
            num_thread  = $Threads
            num_ctx     = $Context
            num_predict = $Predict
            temperature = $Temperature
        }
        keep_alive = $KeepAlive
    } | ConvertTo-Json -Depth 20

    $sw = [System.Diagnostics.Stopwatch]::StartNew()

    try {
        $response = Invoke-WebRequest `
            -Uri $ChatUrl `
            -Method POST `
            -ContentType "application/json" `
            -Body $payload `
            -TimeoutSec $TimeoutSec

        $sw.Stop()

        if ($response.StatusCode -ne 200) {
            throw "HTTP $($response.StatusCode)"
        }

        $json = $response.Content | ConvertFrom-Json
        $content = ""

        if ($null -ne $json.message -and $null -ne $json.message.content) {
            $content = [string]$json.message.content
        }

        $completionTokens = [int]($json.eval_count ?? 0)
        $promptTokens     = [int]($json.prompt_eval_count ?? 0)
        $evalDurationNs   = [double]($json.eval_duration ?? 0)
        $promptDurationNs = [double]($json.prompt_eval_duration ?? 0)

        $evalSec   = if ($evalDurationNs -gt 0) { $evalDurationNs / 1e9 } else { 0.0 }
        $promptSec = if ($promptDurationNs -gt 0) { $promptDurationNs / 1e9 } else { 0.0 }

        $generationTps = if ($completionTokens -gt 0 -and $evalSec -gt 0) {
            $completionTokens / $evalSec
        } else { 0.0 }

        $promptTps = if ($promptTokens -gt 0 -and $promptSec -gt 0) {
            $promptTokens / $promptSec
        } else { 0.0 }

        return [pscustomobject]@{
            Success          = $true
            HttpStatus       = [int]$response.StatusCode
            Content          = $content
            WallClockMs      = [math]::Round($sw.Elapsed.TotalMilliseconds, 2)
            CompletionTokens = $completionTokens
            PromptTokens     = $promptTokens
            TokensPerSecond  = [math]::Round($generationTps, 4)
            PromptTPS        = [math]::Round($promptTps, 4)
            EvalDurationMs   = [math]::Round($evalSec * 1000.0, 2)
            PromptEvalMs     = [math]::Round($promptSec * 1000.0, 2)
            TotalDurationMs  = [double]($json.total_duration ?? 0) / 1e6
            LoadDurationMs   = [double]($json.load_duration ?? 0) / 1e6
            Raw              = $json
            Error            = $null
        }
    }
    catch {
        $sw.Stop()

        return [pscustomobject]@{
            Success          = $false
            HttpStatus       = 0
            Content          = ""
            WallClockMs      = [math]::Round($sw.Elapsed.TotalMilliseconds, 2)
            CompletionTokens = 0
            PromptTokens     = 0
            TokensPerSecond  = 0.0
            PromptTPS        = 0.0
            EvalDurationMs   = 0.0
            PromptEvalMs     = 0.0
            TotalDurationMs  = 0.0
            LoadDurationMs   = 0.0
            Raw              = $null
            Error            = $_.Exception.Message
        }
    }
}

# ============================================================
# INTROSPECTION MODELE
# ============================================================

function Get-ModelInfo {
    param([Parameter(Mandatory)][string]$Model)

    try {
        $payload = @{ model = $Model } | ConvertTo-Json

        $response = Invoke-WebRequest `
            -Uri "$OllamaUrl/api/show" `
            -Method POST `
            -ContentType "application/json" `
            -Body $payload `
            -TimeoutSec 30

        $json    = $response.Content | ConvertFrom-Json
        $details = $json.details

        return [pscustomobject]@{
            Model          = $Model
            ParameterSize  = [string]($details.parameter_size ?? "")
            Family         = [string]($details.family ?? "")
            Quantization   = [string]($details.quantization_level ?? "")
            Format         = [string]($details.format ?? "")
            ParameterCount = [string]($details.parameter_count ?? "")
        }
    }
    catch {
        return [pscustomobject]@{
            Model          = $Model
            ParameterSize  = ""
            Family         = ""
            Quantization   = ""
            Format         = ""
            ParameterCount = ""
        }
    }
}

# ============================================================
# VALIDATEURS DETERMINISTES
# ============================================================

function Get-CompetenceScore {
    param(
        [Parameter(Mandatory)][string]$Benchmark,
        [AllowEmptyString()][string]$Content
    )

    $text = ($Content ?? "").Trim()
    if ([string]::IsNullOrWhiteSpace($text)) { return 0.0 }

    switch ($Benchmark) {

        "GENERAL" {
            $score = 0.0
            if ($text.Length -ge 40)  { $score += 20.0 }
            if ($text.Length -ge 100) { $score += 20.0 }
            if ($text -match "(?i)\b(raison|car|donc|parce)\b") { $score += 20.0 }
            if ($text -match "[.!?]") { $score += 20.0 }
            if ($text -notmatch "(?i)je ne sais pas|cannot answer|impossible") { $score += 20.0 }
            return [math]::Min(100.0, $score)
        }

        "REASONING" {
            $score = 0.0
            if ($text -match "(?i)\bRESULTAT\s*[:=]\s*32\b") {
                $score += 60.0
            }
            elseif ($text -match "\b32\b" -and ($text -match "\b14\b" -or $text -match "\b6\b" -or $text -match "\b3\b")) {
                $score += 35.0
            }
            if ($text -match "(?i)14.*6.*3|6.*3.*14") { $score += 20.0 }
            if ($text -match "(?i)priorit|multiplication|ordre") { $score += 20.0 }
            return [math]::Min(100.0, $score)
        }

        "CODE" {
            $score = 0.0
            if ($text -match "(?i)\bdef\s+\w+\s*\(") { $score += 30.0 }
            if ($text -match "(?i)\breturn\b") { $score += 20.0 }
            if ($text -match "(?i)\b(None|null|empty)\b") { $score += 15.0 }
            if ($text -match "(?i)\b(False|True)\b") { $score += 15.0 }
            if ($text -notmatch "(?is)explanation") { $score += 20.0 }
            return [math]::Min(100.0, $score)
        }

        "JSON" {
            try {
                $clean = $text.Trim()
                if ($clean -match "^```") { return 0.0 }
                if ($clean -notmatch "^\s*\{" -or $clean -notmatch "\}\s*$") { return 0.0 }

                $data =$clean | ConvertFrom-Json
                if ($null -eq$data) { return 0.0 }

                $score = 0.0
                if ($data.status -eq "ok") { $score += 25.0 }
                if ($data.provider -eq "ollama") { $score += 25.0 }
                if ($data.cpu_only -eq $true) {$score += 25.0 }
                if ($null -ne$data.score -and [int]$data.score -eq 100) {$score += 25.0 }
                return [math]::Min(100.0, $score)
            }
            catch {
                return 0.0
            }
        }

        "INSTRUCTION" {
            # Découpage robuste évitant les faux positifs sur abréviations
            $sentences = @($text -split "(?<=[a-zA-Z0-9]{2,}[.!?])\s+") | Where-Object {
                -not [string]::IsNullOrWhiteSpace($_)
            }

            $score = 0.0
            if ($sentences.Count -eq 3) {$score += 50.0 }
            elseif ($sentences.Count -eq 2 -or $sentences.Count -eq 4) {$score += 35.0 }
            if ($text -notmatch "```") { $score += 25.0 }
            if ($text.Length -ge 40) { $score += 25.0 }
            return [math]::Min(100.0, $score)
        }

        default { return 0.0 }
    }
}

# ============================================================
# BENCHMARKS DE COMPETENCE
# ============================================================

$Benchmarks = @(
    [pscustomobject]@{
        Name    = "GENERAL"
        Predict = 160
        Prompt  = "Explique en francais pourquoi, dans une architecture multi-modeles, le modele doit etre selectionne avant l'execution de la tache. Donne une reponse precise et autonome."
    }
    [pscustomobject]@{
        Name    = "REASONING"
        Predict = 180
        Prompt  = "Resous exactement ce calcul : 14 + 6 * 3. Explique brievement la regle de priorite utilisee. Termine obligatoirement par : RESULTAT=32"
    }
    [pscustomobject]@{
        Name    = "CODE"
        Predict = 220
        Prompt  = "Ecris une fonction Python nommee safe_get(data, key) qui retourne data[key] lorsque la cle existe, et False lorsque data est None, que key n'existe pas, ou qu'une erreur de type empeche l'acces. Retourne uniquement le code Python."
    }
    [pscustomobject]@{
        Name    = "JSON"
        Predict = 120
        Prompt  = 'Retourne UNIQUEMENT cet objet JSON et rien d''autre :' + "`n" + '{' + "`n" + '  "status": "ok",' + "`n" + '  "provider": "ollama",' + "`n" + '  "cpu_only": true,' + "`n" + '  "score": 100' + "`n" + '}'
    }
    [pscustomobject]@{
        Name    = "INSTRUCTION"
        Predict = 120
        Prompt  = "Reponds en francais avec exactement trois phrases. Utilise uniquement des points comme fin de phrase. Ne donne aucun code et ne fais aucune liste. Sujet : pourquoi un routeur canonique doit rester l'autorite unique de selection du modele."
    }
)

# ============================================================
# BENCHMARKS DE TUNING
# ============================================================

$TuneBenchmarks = @(
    [pscustomobject]@{
        Name    = "INSTRUCTION"
        Predict = 128
        Prompt  = "Reponds en francais avec exactement trois phrases. Utilise uniquement des points comme fin de phrase. Ne donne aucun code et ne fais aucune liste. Sujet : pourquoi un routeur canonique doit rester l'autorite unique de selection du modele."
    }
    [pscustomobject]@{
        Name    = "REASONING"
        Predict = 180 # Évite la troncature prématurée du raisonnement
        Prompt  = "Resous exactement : 14 + 6 * 3. Explique brievement l'ordre des operations. Termine obligatoirement par : RESULTAT=32"
    }
    [pscustomobject]@{
        Name    = "JSON"
        Predict = 96
        Prompt  = 'Retourne UNIQUEMENT cet objet JSON et aucun texte autour :' + "`n" + '{' + "`n" + '  "status": "ok",' + "`n" + '  "provider": "ollama",' + "`n" + '  "cpu_only": true,' + "`n" + '  "score": 100' + "`n" + '}'
    }
)

# ============================================================
# GENERATEUR NIAH
# ============================================================

function New-NiahPrompt {
    param(
        [Parameter(Mandatory)][int]$TargetTokens,
        [Parameter(Mandatory)][string]$Needle,
        [Parameter(Mandatory)][double]$Depth,
        [Parameter(Mandatory)][bool]$Decoy
    )

    $filler = @(
        "L'architecture E-ZzIO separe decouverte qualification routage et execution. ",
        "Les modeles locaux sont consideres comme des capacites disponibles dans un environnement controle. ",
        "Le routeur doit conserver une autorite unique sur la selection du modele. "
    )

    $sentences = [math]::Max(20, [int][math]::Floor($TargetTokens / 16))
    $pivot     = [int][math]::Floor($sentences * $Depth)

    $before = ""
    $after  = ""

    for ($i = 0; $i -lt $pivot; $i++) { $before += $filler[$i % $filler.Count] }
    for ($i = $pivot; $i -lt $sentences; $i++) { $after += $filler[$i % $filler.Count] }

    $needleLine = "[CONFIDENTIEL: KEY_742=$Needle]"
    $decoyLine  = if ($Decoy) { "[NOTE: KEY_742=FAUSSE_VALEUR_IGNOREZ]" } else { "" }

    return "Document technique :`n`n" + $before + "`n" + $needleLine + "`n" + $decoyLine + "`n" + $after + "`n`nConsigne :`nTrouve la valeur associee a KEY_742.`n`nReponds UNIQUEMENT sous la forme :`nVALEUR=<valeur>"
}

# ============================================================
# CONTROLE DE L'INVENTAIRE
# ============================================================

Write-Host "[1/5] Verification daemon Ollama..."

try {
    $tags = Invoke-RestMethod -Uri "$OllamaUrl/api/tags" -Method GET -TimeoutSec 10
    Write-Host "[PASS] Ollama operationnel."
}
catch {
    throw ("[FAIL-CLOSED] Ollama indisponible : {0}" -f $_.Exception.Message)
}

$availableNames = @($tags.models | ForEach-Object { [string]$_.name })
$missingModels  = @($Models | Where-Object { $_ -notin $availableNames })

if ($missingModels.Count -gt 0) {
    Write-Host ""
    Write-Host "[FAIL-CLOSED] Modeles absents de l'inventaire local :"
    foreach ($m in $missingModels) { Write-Host "  - $m" }
    throw "[FAIL-CLOSED] Corrige les tags ou telecharge les modeles avant execution."
}

Write-Host ""
Write-Host "[2/5] Introspection /api/show..."

$ModelInfo = @{}

foreach ($model in $Models) {
    $info = Get-ModelInfo -Model $model
    $ModelInfo[$model] = $info

    Write-Host (
        "[PROFILE] {0,-44} size={1,-8} family={2,-14} quant={3,-10}" -f `
        $model, $info.ParameterSize, $info.Family, $info.Quantization
    )
}

$AllResults          = New-Object System.Collections.Generic.List[object]
$TuningResults       = New-Object System.Collections.Generic.List[object]
$RecommendedProfiles = New-Object System.Collections.Generic.List[object]

# ============================================================
# BOUCLE PRINCIPALE (ISOLE MODELE PAR MODELE)
# ============================================================

foreach ($model in $Models) {

    Write-Host ""
    Write-Host "============================================================"
    Write-Host "[MODEL] $model"
    Write-Host "============================================================"

    Write-Host "[WARMUP] Chargement..."

    $warmup = Invoke-OllamaChat `
        -Model $model -Prompt "Reponds simplement OK." `
        -Threads 8 -Context 2048 -Predict 16 -Temperature 0.0 `
        -KeepAlive $KeepAliveDuringModel

    if (-not $warmup.Success) {
        Write-Host ("[WARN] Warmup echoue : {0}" -f $warmup.Error)
    }
    else {
        Write-Host "[PASS] Warmup termine."
    }

    # 1. Compétences de référence (12 threads / 4096 ctx)
    foreach ($benchmark in $Benchmarks) {

        Write-Host ""
        Write-Host ("  [COMPETENCE] {0}" -f $benchmark.Name)

        for ($repeat = 1; $repeat -le $Repeats; $repeat++) {

            $result = Invoke-OllamaChat `
                -Model $model -Prompt $benchmark.Prompt `
                -Threads 12 -Context 4096 -Predict $benchmark.Predict `
                -Temperature 0.0 -KeepAlive $KeepAliveDuringModel

            $score = if ($result.Success) {
                Get-CompetenceScore -Benchmark $benchmark.Name -Content $result.Content
            } else { 0.0 }

            $AllResults.Add([pscustomobject]@{
                Model            = $model
                Benchmark        = $benchmark.Name
                Threads          = 12
                Context          = 4096
                Predict          = $benchmark.Predict
                Repeat           = $repeat
                Success          = $result.Success
                Score            = $score
                WallClockMs      = $result.WallClockMs
                TokensPerSecond  = $result.TokensPerSecond
                PromptTPS        = $result.PromptTPS
                CompletionTokens = $result.CompletionTokens
                PromptTokens     = $result.PromptTokens
                ContentLength    = $result.Content.Length
                Content          = $result.Content
                Error            = $result.Error
                Depth            = $null
                Decoy            = $null
            })

            Write-Host (
                "      score={0,6:N1} latency={1,9:N0}ms gen_tok/s={2,7:N2}" -f `
                $score, $result.WallClockMs, $result.TokensPerSecond
            )
        }
    }

    # 2. NIAH (2k / 4k / 8k)
    foreach ($ctx in $ContextGrid) {
        foreach ($depth in @(0.15, 0.50, 0.85)) {

            $safePrefix = $model.Substring(0, [math]::Min(12, $model.Length))
            $safePrefix = $safePrefix.ToUpper().Replace("/", "_").Replace(":", "_").Replace("-", "_").Replace(".", "_")
            $needle = "SEC_${safePrefix}_${ctx}"

            foreach ($decoy in @($false, $true)) {

                $prompt = New-NiahPrompt -TargetTokens ($ctx - 300) -Needle $needle -Depth $depth -Decoy $decoy

                $result = Invoke-OllamaChat `
                    -Model $model -Prompt $prompt `
                    -Threads 12 -Context $ctx -Predict 64 `
                    -Temperature 0.0 -KeepAlive $KeepAliveDuringModel

                $score = 0.0
                if ($result.Success) {
                    $expected = [regex]::Escape($needle)
                    if ($result.Content -match ("^\s*VALEUR=" + $expected + "\s*$")) {
                        $score = 100.0
                    }
                }

                $AllResults.Add([pscustomobject]@{
                    Model            = $model
                    Benchmark        = "NIAH"
                    Threads          = 12
                    Context          = $ctx
                    Predict          = 64
                    Repeat           = 1
                    Success          = $result.Success
                    Score            = $score
                    WallClockMs      = $result.WallClockMs
                    TokensPerSecond  = $result.TokensPerSecond
                    PromptTPS        = $result.PromptTPS
                    CompletionTokens = $result.CompletionTokens
                    PromptTokens     = $result.PromptTokens
                    ContentLength    = $result.Content.Length
                    Content          = $result.Content
                    Error            = $result.Error
                    Depth            = $depth
                    Decoy            = $decoy
                })

                Write-Host (
                    "      [NIAH] ctx={0,5} depth={1:N2} decoy={2,-5} score={3,6:N1} prompt_tok/s={4,7:N2}" -f `
                    $ctx, $depth, $decoy, $score, $result.PromptTPS
                )
            }
        }
    }

    # 3. Grid-Search Tuning CPU
    Write-Host ""
    Write-Host "  [TUNING] Scan threads x contexte..."

    $modelTuningRaw = New-Object System.Collections.Generic.List[object]

    foreach ($threads in $ThreadGrid) {
        foreach ($ctx in $ContextGrid) {

            $taskScores = @{}
            $taskTps    = @{}

            foreach ($benchmark in $TuneBenchmarks) {

                $result = Invoke-OllamaChat `
                    -Model $model -Prompt $benchmark.Prompt `
                    -Threads $threads -Context $ctx -Predict $benchmark.Predict `
                    -Temperature 0.0 -KeepAlive $KeepAliveDuringModel

                if ($result.Success) {
                    $taskScores[$benchmark.Name] = Get-CompetenceScore -Benchmark $benchmark.Name -Content $result.Content
                    $taskTps[$benchmark.Name]    = [double]$result.TokensPerSecond
                }
                else {
                    $taskScores[$benchmark.Name] = 0.0
                    $taskTps[$benchmark.Name]    = 0.0
                }
            }

            $scoreValues  = @($taskScores.Values | ForEach-Object { [double]$_ })
            $avgQuality   = ($scoreValues | Measure-Object -Average).Average
            $minTaskScore = ($scoreValues | Measure-Object -Minimum).Minimum
            $avgTps       = (@($taskTps.Values | ForEach-Object { [double]$_ }) | Measure-Object -Average).Average

            $qualityGate = ($avgQuality -ge 80.0) -and ($minTaskScore -ge 80.0)

            $modelTuningRaw.Add([pscustomobject]@{
                Model            = $model
                Threads          = $threads
                Context          = $ctx
                AverageScore     = [math]::Round($avgQuality, 2)
                MinTaskScore     = [math]::Round($minTaskScore, 2)
                InstructionScore = [math]::Round($taskScores["INSTRUCTION"], 2)
                ReasoningScore   = [math]::Round($taskScores["REASONING"], 2)
                JsonScore        = [math]::Round($taskScores["JSON"], 2)
                AverageTPS       = [math]::Round($avgTps, 4)
                QualityGate      = $qualityGate
            })
        }
    }

    $maxTps = ($modelTuningRaw | Measure-Object -Property AverageTPS -Maximum).Maximum
    if ($null -eq $maxTps -or $maxTps -le 0) { $maxTps = 1.0 }

    foreach ($row in $modelTuningRaw) {
        $speedNorm = [math]::Min(100.0, [double](($row.AverageTPS / $maxTps) * 100.0))
        $combined  = if (-not $row.QualityGate) { 0.0 } else {
            [math]::Min(100.0, [double](($row.AverageScore * 0.75) + ($speedNorm * 0.25)))
        }

        $TuningResults.Add([pscustomobject]@{
            Model            = $row.Model
            Threads          = $row.Threads
            Context          = $row.Context
            AverageScore     = $row.AverageScore
            MinTaskScore     = $row.MinTaskScore
            InstructionScore = $row.InstructionScore
            ReasoningScore   = $row.ReasoningScore
            JsonScore        = $row.JsonScore
            AverageTPS       = $row.AverageTPS
            SpeedNorm        = [math]::Round($speedNorm, 2)
            CombinedUtility  = [math]::Round($combined, 2)
            QualityGate      = $row.QualityGate
        })

        $status = if ($row.QualityGate) { "VALID" } else { "REJECT" }
        Write-Host (
            "    T={0,2} C={1,5} avg={2,6:N1} min={3,6:N1} TPS={4,6:N2} utility={5,6:N2} [{6}]" -f `
            $row.Threads, $row.Context, $row.AverageScore, $row.MinTaskScore, $row.AverageTPS, $combined, $status
        )
    }

    # 4. Sélection déterministe & Confirmation
    $modelResults = @($TuningResults | Where-Object { $_.Model -eq $model })
    $eligible     = @($modelResults | Where-Object { $_.QualityGate -eq $true })

    $competenceRows = @($AllResults | Where-Object { $_.Model -eq $model -and $_.Benchmark -ne "NIAH" })
    $scores = @{}
    foreach ($b in $Benchmarks) {
        $rows = @($competenceRows | Where-Object { $_.Benchmark -eq $b.Name })
        $scores[$b.Name] = if ($rows.Count -gt 0) {
            [math]::Round(($rows | Measure-Object -Property Score -Average).Average, 2)
        } else { 0.0 }
    }

    $niahRows = @($AllResults | Where-Object { $_.Model -eq $model -and $_.Benchmark -eq "NIAH" })
    $niahByContext = [ordered]@{}
    foreach ($ctx in $ContextGrid) {
        $ctxRows = @($niahRows | Where-Object { $_.Context -eq $ctx })
        $niahByContext[[string]$ctx] = if ($ctxRows.Count -gt 0) {
            [math]::Round(($ctxRows | Measure-Object -Property Score -Average).Average, 2)
        } else { 0.0 }
    }

    if ($eligible.Count -eq 0) {
        Write-Host ("[NO_VALID_PROFILE] {0} : aucun profil >= 80." -f $model) -ForegroundColor Yellow

        $RecommendedProfiles.Add([pscustomobject]@{
            Model        = $model
            Status       = "NO_VALID_PROFILE"
            Reason       = "No CPU configuration achieved average >= 80 and minimum task score >= 80."
            Host         = [pscustomobject]@{ CPU = "AMD Ryzen 9 5900X"; Cores = 12; Threads = 24; RAM_GB = 32; RAM = "DDR4-3200"; GPU = "NONE"; Storage = "NVMe" }
            ModelInfo    = $ModelInfo[$model]
            CPU          = $null
            Utility      = $null
            Competencies = [pscustomobject]@{ GENERAL = $scores["GENERAL"]; REASONING = $scores["REASONING"]; CODE = $scores["CODE"]; JSON = $scores["JSON"]; INSTRUCTION = $scores["INSTRUCTION"] }
            LongContext  = $niahByContext
        })
    }
    else {
        $candidate = $eligible |
            Sort-Object `
                @{Expression = {$_.CombinedUtility}; Descending = $true},
                @{Expression = {$_.Threads}; Descending = $false},
                @{Expression = {$_.Context}; Descending = $false} |
            Select-Object -First 1

        Write-Host ""
        Write-Host (
            "  [CONFIRMATION] T={0} C={1} -> {2} passe(s) supplementaire(s)" -f `
            $candidate.Threads, $candidate.Context, $ConfirmationRepeats
        )

        $confirmScores = New-Object System.Collections.Generic.List[double]
        $confirmTps    = New-Object System.Collections.Generic.List[double]
        $confirmMin    = New-Object System.Collections.Generic.List[double]

        $confirmScores.Add($candidate.AverageScore)
        $confirmMin.Add($candidate.MinTaskScore)
        $confirmTps.Add($candidate.AverageTPS)

        for ($c = 1; $c -le $ConfirmationRepeats; $c++) {

            $cTaskScores = @{}
            $cTaskTps    = @{}

            foreach ($benchmark in $TuneBenchmarks) {

                $result = Invoke-OllamaChat `
                    -Model $model -Prompt $benchmark.Prompt `
                    -Threads $candidate.Threads -Context $candidate.Context -Predict $benchmark.Predict `
                    -Temperature 0.0 -KeepAlive $KeepAliveDuringModel

                if ($result.Success) {
                    $cTaskScores[$benchmark.Name] = Get-CompetenceScore -Benchmark $benchmark.Name -Content $result.Content
                    $cTaskTps[$benchmark.Name]    = [double]$result.TokensPerSecond
                }
                else {
                    $cTaskScores[$benchmark.Name] = 0.0
                    $cTaskTps[$benchmark.Name]    = 0.0
                }
            }

            $cScoreValues = @($cTaskScores.Values | ForEach-Object { [double]$_ })
            $confirmScores.Add(($cScoreValues | Measure-Object -Average).Average)
            $confirmMin.Add(($cScoreValues | Measure-Object -Minimum).Minimum)
            $confirmTps.Add((@($cTaskTps.Values | ForEach-Object { [double]$_ }) | Measure-Object -Average).Average)
        }

        $finalAvgQuality  = ($confirmScores | Measure-Object -Average).Average
        $finalMinTask     = ($confirmMin | Measure-Object -Minimum).Minimum
        $finalAvgTps      = ($confirmTps | Measure-Object -Average).Average
        $finalQualityGate = ($finalAvgQuality -ge 80.0) -and ($finalMinTask -ge 80.0)

        $finalSpeedNorm = [math]::Min(100.0, [double](($finalAvgTps / $maxTps) * 100.0))
        $finalUtility   = if (-not $finalQualityGate) { 0.0 } else {
            [math]::Min(100.0, [double](($finalAvgQuality * 0.75) + ($finalSpeedNorm * 0.25)))
        }

        Write-Host (
            "  [CONFIRME] avg={0:N1} (etait {1:N1}) min={2:N1} tps={3:N2} (etait {4:N2}) gate={5}" -f `
            $finalAvgQuality, $candidate.AverageScore, $finalMinTask, $finalAvgTps, $candidate.AverageTPS, $finalQualityGate
        )

        if (-not $finalQualityGate) {
            Write-Host "  [REPLI] Confirmation echouee -> repli sur le 2e profil eligible." -ForegroundColor Yellow

            $fallback = @($eligible | Where-Object {
                -not ($_.Threads -eq $candidate.Threads -and $_.Context -eq $candidate.Context)
            }) | Sort-Object `
                @{Expression = {$_.CombinedUtility}; Descending = $true},
                @{Expression = {$_.Threads}; Descending = $false},
                @{Expression = {$_.Context}; Descending = $false} |
                Select-Object -First 1

            if ($null -eq $fallback) {
                $RecommendedProfiles.Add([pscustomobject]@{
                    Model        = $model
                    Status       = "NO_VALID_PROFILE"
                    Reason       = "Winning candidate failed confirmation and no fallback remained."
                    Host         = [pscustomobject]@{ CPU = "AMD Ryzen 9 5900X"; Cores = 12; Threads = 24; RAM_GB = 32; RAM = "DDR4-3200"; GPU = "NONE"; Storage = "NVMe" }
                    ModelInfo    = $ModelInfo[$model]
                    CPU          = $null
                    Utility      = $null
                    Competencies = [pscustomobject]@{ GENERAL = $scores["GENERAL"]; REASONING = $scores["REASONING"]; CODE = $scores["CODE"]; JSON = $scores["JSON"]; INSTRUCTION = $scores["INSTRUCTION"] }
                    LongContext  = $niahByContext
                })
            }
            else {
                $RecommendedProfiles.Add([pscustomobject]@{
                    Model     = $model
                    Status    = "VALIDATED"
                    Reason    = "Fallback profile after winning candidate failed confirmation."
                    Host      = [pscustomobject]@{ CPU = "AMD Ryzen 9 5900X"; Cores = 12; Threads = 24; RAM_GB = 32; RAM = "DDR4-3200"; GPU = "NONE"; Storage = "NVMe" }
                    ModelInfo = $ModelInfo[$model]
                    CPU       = [pscustomobject]@{ NumGPU = 0; NumThread = $fallback.Threads; NumCtx = $fallback.Context; NumPredict = 128; Temperature = 0.0; Parallel = 1; MaxLoadedModels = 1; KeepAlive = "10m" }
                    Utility   = [pscustomobject]@{ AverageQuality = $fallback.AverageScore; MinTaskScore = $fallback.MinTaskScore; Instruction = $fallback.InstructionScore; Reasoning = $fallback.ReasoningScore; JSON = $fallback.JsonScore; AverageTPS = $fallback.AverageTPS; SpeedNorm = $fallback.SpeedNorm; CombinedUtility = $fallback.CombinedUtility; QualityGate = $fallback.QualityGate; ConfirmationPassed = $false }
                    Competencies = [pscustomobject]@{ GENERAL = $scores["GENERAL"]; REASONING = $scores["REASONING"]; CODE = $scores["CODE"]; JSON = $scores["JSON"]; INSTRUCTION = $scores["INSTRUCTION"] }
                    LongContext  = $niahByContext
                })

                Write-Host (
                    "[CERTIFIED-FALLBACK] {0} -> T={1} CTX={2} utility={3:N1}" -f `
                    $model, $fallback.Threads, $fallback.Context, $fallback.CombinedUtility
                ) -ForegroundColor Yellow
            }
        }
        else {
            $RecommendedProfiles.Add([pscustomobject]@{
                Model     = $model
                Status    = "VALIDATED"
                Reason    = "Certified optimal profile meeting strict task threshold >= 80, confirmed over $($ConfirmationRepeats + 1) passes."
                Host      = [pscustomobject]@{ CPU = "AMD Ryzen 9 5900X"; Cores = 12; Threads = 24; RAM_GB = 32; RAM = "DDR4-3200"; GPU = "NONE"; Storage = "NVMe" }
                ModelInfo = $ModelInfo[$model]
                CPU       = [pscustomobject]@{ NumGPU = 0; NumThread = $candidate.Threads; NumCtx = $candidate.Context; NumPredict = 128; Temperature = 0.0; Parallel = 1; MaxLoadedModels = 1; KeepAlive = "10m" }
                Utility   = [pscustomobject]@{
                    AverageQuality     = [math]::Round($finalAvgQuality, 2)
                    MinTaskScore       = [math]::Round($finalMinTask, 2)
                    AverageTPS         = [math]::Round($finalAvgTps, 4)
                    SpeedNorm          = [math]::Round($finalSpeedNorm, 2)
                    CombinedUtility    = [math]::Round($finalUtility, 2)
                    QualityGate        = $finalQualityGate
                    ConfirmationPasses = $ConfirmationRepeats + 1
                    ConfirmationPassed = $true
                }
                Competencies = [pscustomobject]@{ GENERAL = $scores["GENERAL"]; REASONING = $scores["REASONING"]; CODE = $scores["CODE"]; JSON = $scores["JSON"]; INSTRUCTION = $scores["INSTRUCTION"] }
                LongContext  = $niahByContext
            })

            Write-Host (
                "[CERTIFIED] {0} -> T={1} CTX={2} utility={3:N1} avg={4:N1} min={5:N1} tok/s={6:N2}" -f `
                $model, $candidate.Threads, $candidate.Context, $finalUtility, $finalAvgQuality, $finalMinTask, $finalAvgTps
            ) -ForegroundColor Green
        }
    }

    # Déchargement propre du modèle
    Write-Host ""
    Write-Host "[UNLOAD] Déchargement du modèle de la mémoire..."
    $null = Invoke-OllamaChat `
        -Model $model -Prompt "unload" -Threads 8 -Context 2048 -Predict 1 `
        -Temperature 0.0 -KeepAlive $KeepAliveAfterModel

    Write-Host "[MODEL COMPLETE] $model"
}

# ============================================================
# EXPORT PROPRE ET SÉCURISÉ
# ============================================================

Write-Host ""
Write-Host "[5/5] Export des rapports..."

$RankedProfiles = @(
    $RecommendedProfiles |
    Where-Object { $_.Status -eq "VALIDATED" } |
    Sort-Object @{Expression = {$_.Utility.CombinedUtility}; Descending = $true}
)

$JsonPayload = [pscustomobject]@{
    GeneratedAt = (Get-Date).ToString("o")

    Host = [pscustomobject]@{
        CPU = "AMD Ryzen 9 5900X"; CoresPhysical = 12; ThreadsLogical = 24
        RAM_GB = 32; RAM_Type = "DDR4-3200"; GPU = "NONE"; Storage = "NVMe"
    }

    Ollama = [pscustomobject]@{
        BaseUrl = $OllamaUrl; NumParallel = 1; MaxLoadedModels = 1
        KeepAliveDuringModel = $KeepAliveDuringModel; KeepAliveAfterModel = $KeepAliveAfterModel
    }

    BenchmarkPolicy = [pscustomobject]@{
        ThreadGrid = $ThreadGrid; ContextGrid = $ContextGrid
        ScanRepeats = $Repeats; ConfirmationRepeats = $ConfirmationRepeats
        MinimumTaskScore = 80.0; MinimumAverage = 80.0
        QualityWeight = 0.75; SpeedWeight = 0.25; GPU = 0
        NIAHDepths = @(0.15, 0.50, 0.85); NIAHDecoy = $true
    }

    Models              = $Models
    ModelInfo           = $ModelInfo
    RawResults          = $AllResults
    CpuTuning           = $TuningResults
    RecommendedProfiles = $RecommendedProfiles
    CertifiedProfiles   = $RankedProfiles
}

(Convert-ToJsonSafeObject -InputObject $JsonPayload) | ConvertTo-Json -Depth 40 | Set-Content -Path $JsonReport -Encoding utf8
$AllResults | Export-Csv -Path $CsvReport -NoTypeInformation -Encoding utf8
(Convert-ToJsonSafeObject -InputObject $RecommendedProfiles) | ConvertTo-Json -Depth 40 | Set-Content -Path $ProfileReport -Encoding utf8

Write-Host ""
Write-Host "============================================================"
Write-Host " BENCHMARK CPU V4.1 TERMINE"
Write-Host "============================================================"

if ($RankedProfiles.Count -eq 0) {
    Write-Host "[FAIL-CLOSED] Aucun profil CPU certifié." -ForegroundColor Red
}
else {
    $rank = 1
    foreach ($p in $RankedProfiles) {
        Write-Host ("#{0} {1}" -f $rank, $p.Model)
        Write-Host ("    utility={0:N1} avg={1:N1} min={2:N1} tok/s={3:N2}" -f $p.Utility.CombinedUtility, $p.Utility.AverageQuality, $p.Utility.MinTaskScore, $p.Utility.AverageTPS)
        Write-Host ("    threads={0} ctx={1} gpu={2}" -f $p.CPU.NumThread, $p.CPU.NumCtx, $p.CPU.NumGPU)
        $rank++
    }
}

Write-Host ""
Write-Host "RAPPORT JSON : $JsonReport"
Write-Host "RAPPORT CSV  : $CsvReport"
Write-Host "PROFILS      : $ProfileReport"
Write-Host "============================================================"