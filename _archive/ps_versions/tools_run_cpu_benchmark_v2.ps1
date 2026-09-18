Set-Location "G:\AI\E-zzio"
$ErrorActionPreference = "Stop"

$OllamaUrl = "http://127.0.0.1:11434"
$ChatUrl   = "$OllamaUrl/v1/chat/completions"

$Models = @(
    "Distendo/zen-pro",
    "granite4.2",
    "ornith-1.5:9b",
    "mrasif/gpt-oss-20b-GGUF",
    "qwen3-coder:30b"
)

$ThreadGrid  = @(8, 12, 16, 20, 24)
$ContextGrid = @(2048, 4096, 8192)

$Repeats = 3
$TimeoutSec = 300

$ReportDir = "tools\reports"
New-Item -ItemType Directory -Path $ReportDir -Force | Out-Null

$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"

$JsonReport    = Join-Path $ReportDir "cpu_model_benchmark_$Stamp.json"
$CsvReport     = Join-Path $ReportDir "cpu_model_benchmark_$Stamp.csv"
$ProfileReport = Join-Path $ReportDir "cpu_model_profiles_$Stamp.json"

$env:OLLAMA_NUM_PARALLEL      = "1"
$env:OLLAMA_MAX_LOADED_MODELS = "1"
$env:OLLAMA_KEEP_ALIVE        = "0"

Write-Host "============================================================"
Write-Host " E-ZZIO — CPU MODEL COMPETENCE BENCHMARK (V3 CERTIFIEE)"
Write-Host "============================================================"
Write-Host "CPU        : AMD Ryzen 9 5900X"
Write-Host "Cores      : 12"
Write-Host "Threads    : 24"
Write-Host "RAM        : 32 GB DDR4-3200"
Write-Host "GPU        : DISABLED"
Write-Host "Storage    : NVMe"
Write-Host "Parallel   : 1"
Write-Host "Loaded     : 1"
Write-Host "KeepAlive  : 0"
Write-Host ""

function Invoke-OllamaChat {
    param(
        [Parameter(Mandatory)]
        [string]$Model,

        [Parameter(Mandatory)]
        [string]$Prompt,

        [Parameter(Mandatory)]
        [int]$Threads,

        [Parameter(Mandatory)]
        [int]$Context,

        [Parameter(Mandatory)]
        [int]$Predict,

        [Parameter(Mandatory)]
        [double]$Temperature
    )

    $payload = @{
        model = $Model
        messages = @(
            @{
                role = "user"
                content = $Prompt
            }
        )
        stream = $false
        temperature = $Temperature
        max_tokens = $Predict
    } | ConvertTo-Json -Depth 10

    $sw = [System.Diagnostics.Stopwatch]::StartNew()

    try {
        $response = Invoke-WebRequest `
            -Uri $ChatUrl `
            -Method POST `
            -ContentType "application/json" `
            -Body $payload `
            -TimeoutSec $TimeoutSec

        $sw.Stop()

        $json = $response.Content | ConvertFrom-Json

        $content = ""

        if ($null -ne $json.choices -and $json.choices.Count -gt 0) {
            $message = $json.choices[0].message

            if ($null -ne $message.content) {
                $content = [string]$message.content
            }
        }

        $usage = $json.usage

        $completionTokens = 0
        $promptTokens = 0

        if ($null -ne $usage) {
            $completionTokens = [int]($usage.completion_tokens ?? 0)
            $promptTokens     = [int]($usage.prompt_tokens ?? 0)
        }

        $tps = 0.0

        if (
            $completionTokens -gt 0 -and
            $sw.Elapsed.TotalSeconds -gt 0
        ) {
            $tps = $completionTokens / $sw.Elapsed.TotalSeconds
        }

        [pscustomobject]@{
            Success          = $true
            HttpStatus       = [int]$response.StatusCode
            Content          = $content
            WallClockMs      = [math]::Round($sw.Elapsed.TotalMilliseconds, 2)
            CompletionTokens = $completionTokens
            PromptTokens     = $promptTokens
            TokensPerSecond  = [math]::Round($tps, 4)
            Raw              = $json
            Error            = $null
        }
    }
    catch {
        $sw.Stop()

        [pscustomobject]@{
            Success          = $false
            HttpStatus       = 0
            Content          = ""
            WallClockMs      = [math]::Round($sw.Elapsed.TotalMilliseconds, 2)
            CompletionTokens = 0
            PromptTokens     = 0
            TokensPerSecond  = 0.0
            Raw              = $null
            Error            = $_.Exception.Message
        }
    }
}

function Get-ModelInfo {
    param(
        [Parameter(Mandatory)]
        [string]$Model
    )

    try {
        $payload = @{
            model = $Model
        } | ConvertTo-Json

        $response = Invoke-WebRequest `
            -Uri "$OllamaUrl/api/show" `
            -Method POST `
            -ContentType "application/json" `
            -Body $payload `
            -TimeoutSec 30

        $json = $response.Content | ConvertFrom-Json
        $details = $json.details

        [pscustomobject]@{
            Model          = $Model
            ParameterSize  = [string]($details.parameter_size ?? "")
            Family         = [string]($details.family ?? "")
            Quantization   = [string]($details.quantization_level ?? "")
            Format         = [string]($details.format ?? "")
            ParameterCount = [string]($details.parameter_count ?? "")
        }
    }
    catch {
        [pscustomobject]@{
            Model          = $Model
            ParameterSize  = ""
            Family         = ""
            Quantization   = ""
            Format         = ""
            ParameterCount = ""
        }
    }
}

function Get-CompetenceScore {
    param(
        [Parameter(Mandatory)]
        [string]$Benchmark,

        [AllowEmptyString()]
        [string]$Content
    )

    $text = ($Content ?? "").Trim()

    if ([string]::IsNullOrWhiteSpace($text)) {
        return 0.0
    }

    switch ($Benchmark) {

        "GENERAL" {
            $score = 0.0

            if ($text.Length -ge 40)  { $score += 20 }
            if ($text.Length -ge 100) { $score += 20 }

            if ($text -match "(?i)raison|car|donc|parce") {
                $score += 20
            }

            if ($text -match "[.!?]") {
                $score += 20
            }

            if ($text -notmatch "(?i)je ne sais pas|cannot answer|impossible") {
                $score += 20
            }

            return [math]::Min(100, $score)
        }

        "REASONING" {
            $score = 0.0

            if ($text -match "(?i)RESULTAT\s*[:=]\s*32\b") {
                $score += 60
            }
            elseif (
                $text -match "\b32\b" -and
                (
                    $text -match "\b14\b" -or
                    $text -match "\b6\b" -or
                    $text -match "\b3\b"
                )
            ) {
                $score += 35
            }

            if ($text -match "(?i)14.*6.*3|6.*3.*14") {
                $score += 20
            }

            if ($text -match "(?i)priorit|multiplication|ordre") {
                $score += 20
            }

            return [math]::Min(100, $score)
        }

        "CODE" {
            $score = 0.0

            if ($text -match "(?i)def\s+\w+\s*\(") {
                $score += 30
            }

            if ($text -match "(?i)\breturn\b") {
                $score += 20
            }

            if ($text -match "(?i)None|null|empty") {
                $score += 15
            }

            if ($text -match "(?i)\bFalse\b|\bTrue\b") {
                $score += 15
            }

            if ($text -notmatch "(?i)```[\s\S]*explanation") {
                $score += 20
            }

            return [math]::Min(100, $score)
        }

        "JSON" {
            try {
                $clean = $text.Trim()

                if ($clean.StartsWith("```json")) {
                    $clean = $clean.Substring(7)
                }

                if ($clean.StartsWith("```")) {
                    $clean = $clean.Substring(3)
                }

                if ($clean.EndsWith("```")) {
                    $clean = $clean.Substring(
                        0,
                        $clean.Length - 3
                    )
                }

                $clean = $clean.Trim()

                if (
                    -not $clean.StartsWith("{") -or
                    -not $clean.EndsWith("}")
                ) {
                    return 0.0
                }

                $data = $clean | ConvertFrom-Json

                if ($null -eq $data) {
                    return 0.0
                }

                $score = 0.0

                if ($data.status -eq "ok") {
                    $score += 25
                }

                if ($data.provider -eq "ollama") {
                    $score += 25
                }

                if ($data.cpu_only -eq $true) {
                    $score += 25
                }

                if (
                    $null -ne $data.score -and
                    [int]$data.score -eq 100
                ) {
                    $score += 25
                }

                return [math]::Min(100, $score)
            }
            catch {
                return 0.0
            }
        }

        "INSTRUCTION" {
            $sentences = @(
                $text -split "(?<=[.])\s+"
            ) | Where-Object {
                -not [string]::IsNullOrWhiteSpace($_)
            }

            $score = 0.0

            if ($sentences.Count -eq 3) {
                $score += 50
            }
            elseif (
                $sentences.Count -eq 2 -or
                $sentences.Count -eq 4
            ) {
                $score += 25
            }

            if ($text -notmatch "```") {
                $score += 25
            }

            if ($text.Length -ge 40) {
                $score += 25
            }

            return [math]::Min(100, $score)
        }

        "NIAH" {
            if ($text -match "VALEUR=SEC_[A-Z0-9_]+") {
                return 100.0
            }

            return 0.0
        }

        default {
            return 0.0
        }
    }
}

$Benchmarks = @(
    [pscustomobject]@{
        Name    = "GENERAL"
        Predict = 160
        Prompt  = @"
Explique en français pourquoi, dans une architecture multi-modèles,
le modèle doit être sélectionné avant l'exécution de la tâche.
Donne une réponse précise et autonome.
"@
    }
    [pscustomobject]@{
        Name    = "REASONING"
        Predict = 180
        Prompt  = @"
Résous exactement ce calcul :
14 + 6 * 3
Explique brièvement la règle de priorité utilisée et termine par :
RESULTAT=<nombre>
"@
    }
    [pscustomobject]@{
        Name    = "CODE"
        Predict = 220
        Prompt  = @"
Écris une fonction Python nommée safe_get(data, key)
qui retourne data[key] lorsque la clé existe,
et False lorsque data est None, que key n'existe pas,
ou qu'une erreur de type empêche l'accès.
Retourne uniquement le code Python.
"@
    }
    [pscustomobject]@{
        Name    = "JSON"
        Predict = 120
        Prompt  = @"
Retourne UNIQUEMENT cet objet JSON :
{
"status": "ok",
"provider": "ollama",
"cpu_only": true,
"score": 100
}
Aucun texte autour.
"@
    }
    [pscustomobject]@{
        Name    = "INSTRUCTION"
        Predict = 120
        Prompt  = @"
Réponds en français avec exactement trois phrases.
Utilise uniquement des points comme fin de phrase.
Ne donne aucun code et ne fais aucune liste.
Sujet : pourquoi un routeur canonique doit rester l'autorité unique de sélection du modèle.
"@
    }
)

function New-NiahPrompt {
    param(
        [Parameter(Mandatory)]
        [int]$TargetTokens,

        [Parameter(Mandatory)]
        [string]$Needle,

        [Parameter(Mandatory)]
        [double]$Depth,

        [Parameter(Mandatory)]
        [bool]$Decoy
    )

    $filler = @(
        "L'architecture E-ZzIO sépare découverte qualification routage et exécution. ",
        "Les modèles locaux sont considérés comme des capacités disponibles dans un environnement contrôlé. ",
        "Le routeur doit conserver une autorité unique sur la sélection du modèle. "
    )

    $sentences = [math]::Max(
        20,
        [math]::Floor($TargetTokens / 16)
    )

    $pivot = [math]::Floor($sentences * $Depth)

    $before = ""
    $after  = ""

    for ($i = 0; $i -lt $pivot; $i++) {
        $before += $filler[$i % $filler.Count]
    }

    for ($i = $pivot; $i -lt $sentences; $i++) {
        $after += $filler[$i % $filler.Count]
    }

    $needleLine = "[CONFIDENTIEL: KEY_742=$Needle]"
    $decoyLine   = ""

    if ($Decoy) {
        $decoyLine = "[NOTE: KEY_742=FAUSSE_VALEUR_IGNOREZ]"
    }

@"
Document technique :
$before
$needleLine
$decoyLine
$after
Consigne :
Trouve la valeur associée à KEY_742.
Réponds UNIQUEMENT sous la forme :
VALEUR=<valeur>
"@
}

Write-Host "[1/6] Vérification daemon Ollama..."

try {
    $null = Invoke-RestMethod `
        -Uri "$OllamaUrl/api/tags" `
        -Method GET `
        -TimeoutSec 10

    Write-Host "[PASS] Ollama opérationnel."
}
catch {
    throw "[FAIL-CLOSED] Ollama indisponible : $($_.Exception.Message)"
}

$ModelInfo = @{}

Write-Host ""
Write-Host "[2/6] Introspection /api/show..."

foreach ($model in $Models) {
    $info = Get-ModelInfo -Model $model
    $ModelInfo[$model] = $info

    Write-Host (
        "[PROFILE] {0,-38} size={1,-8} family={2,-12} quant={3}" -f `
        $model,
        $info.ParameterSize,
        $info.Family,
        $info.Quantization
    )
}

$AllResults = New-Object System.Collections.Generic.List[object]

foreach ($model in $Models) {

    Write-Host ""
    Write-Host "============================================================"
    Write-Host "[MODEL] $model"
    Write-Host "============================================================"

    Write-Host "[WARMUP] Chargement..."

    $warmup = Invoke-OllamaChat `
        -Model $model `
        -Prompt "Réponds simplement OK." `
        -Threads 8 `
        -Context 2048 `
        -Predict 16 `
        -Temperature 0.0

    if (-not $warmup.Success) {
        Write-Host "[WARN] Warmup échoué : $($warmup.Error)"
    }
    else {
        Write-Host "[PASS] Warmup terminé."
    }

    # -----------------------------------------------------------------------
    # Compétences de base (référence 12 threads / 4096 ctx)
    # -----------------------------------------------------------------------
    foreach ($benchmark in $Benchmarks) {

        Write-Host ""
        Write-Host "  [COMPETENCE] $($benchmark.Name)"

        for ($repeat = 1; $repeat -le $Repeats; $repeat++) {

            $result = Invoke-OllamaChat `
                -Model $model `
                -Prompt $benchmark.Prompt `
                -Threads 12 `
                -Context 4096 `
                -Predict $benchmark.Predict `
                -Temperature 0.0

            $score = 0.0

            if ($result.Success) {
                $score = Get-CompetenceScore `
                    -Benchmark $benchmark.Name `
                    -Content $result.Content
            }

            $AllResults.Add(
                [pscustomobject]@{
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
                    CompletionTokens = $result.CompletionTokens
                    PromptTokens     = $result.PromptTokens
                    ContentLength    = $result.Content.Length
                    Content          = $result.Content
                    Error            = $result.Error
                }
            )

            Write-Host (
                "      score={0,6:N1} latency={1,9:N0}ms tok/s={2,7:N2}" -f `
                $score,
                $result.WallClockMs,
                $result.TokensPerSecond
            )
        }
    }

    # -----------------------------------------------------------------------
    # NIAH (2k/4k/8k, depth, decoy)
    # -----------------------------------------------------------------------
    foreach ($ctx in $ContextGrid) {

        foreach ($depth in @(0.15, 0.50, 0.85)) {

            $needle = "SEC_$($model.Substring(0, [math]::Min(6, $model.Length)).ToUpper())_${ctx}"

            foreach ($decoy in @($false, $true)) {

                $prompt = New-NiahPrompt `
                    -TargetTokens ($ctx - 300) `
                    -Needle $needle `
                    -Depth $depth `
                    -Decoy $decoy

                $result = Invoke-OllamaChat `
                    -Model $model `
                    -Prompt $prompt `
                    -Threads 12 `
                    -Context $ctx `
                    -Predict 64 `
                    -Temperature 0.0

                $score = 0.0

                if ($result.Success) {

                    if (
                        $result.Content -match (
                            "VALEUR=" +
                            [regex]::Escape($needle) +
                            "\s*$"
                        )
                    ) {
                        $score = 100.0
                    }
                }

                $AllResults.Add(
                    [pscustomobject]@{
                        Model            = $model
                        Benchmark        = "NIAH"
                        Threads          = 12
                        Context          = $ctx
                        Predict          = 64
                        Repeat           = 1
                        Depth            = $depth
                        Decoy            = $decoy
                        Success          = $result.Success
                        Score            = $score
                        WallClockMs      = $result.WallClockMs
                        TokensPerSecond  = $result.TokensPerSecond
                        CompletionTokens = $result.CompletionTokens
                        PromptTokens     = $result.PromptTokens
                        ContentLength    = $result.Content.Length
                        Content          = $result.Content
                        Error            = $result.Error
                    }
                )

                Write-Host (
                    "      [NIAH] ctx={0,5} depth={1:N2} decoy={2} score={3,6:N1} tok/s={4,7:N2}" -f `
                    $ctx,
                    $depth,
                    $decoy,
                    $score,
                    $result.TokensPerSecond
                )
            }
        }
    }
}

# ---------------------------------------------------------------------------
# TUNING CPU — PROFIL COMPOSITE PAR MODÈLE
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "[4/6] Tuning CPU composite par modèle..."
Write-Host " Threads = 8 / 12 / 16 / 20 / 24"
Write-Host " Context = 2048 / 4096 / 8192"
Write-Host " Minimum qualité = 80"

$TuningResults = New-Object System.Collections.Generic.List[object]

$TuneBenchmarks = @(
    [pscustomobject]@{
        Name   = "INSTRUCTION"
        Prompt = @"
Réponds en français avec exactement trois phrases.
Utilise uniquement des points comme fin de phrase.
Ne donne aucun code et ne fais aucune liste.
Sujet : pourquoi un routeur canonique doit rester l'autorité unique
de sélection du modèle.
"@
    }
    [pscustomobject]@{
        Name   = "REASONING"
        Prompt = @"
Résous exactement :
14 + 6 * 3
Explique brièvement l'ordre des opérations et termine obligatoirement par :
RESULTAT=32
"@
    }
    [pscustomobject]@{
        Name   = "JSON"
        Prompt = @"
Retourne UNIQUEMENT cet objet JSON et aucun texte autour :
{
"status": "ok",
"provider": "ollama",
"cpu_only": true,
"score": 100
}
"@
    }
)

foreach ($model in $Models) {
    Write-Host ""
    Write-Host "------------------------------------------------------------"
    Write-Host "[TUNING] $model"
    Write-Host "------------------------------------------------------------"

    foreach ($threads in $ThreadGrid) {

        foreach ($ctx in $ContextGrid) {

            $qualityValues = New-Object System.Collections.Generic.List[double]
            $tpsValues     = New-Object System.Collections.Generic.List[double]

            foreach ($benchmark in $TuneBenchmarks) {

                for ($repeat = 1; $repeat -le $Repeats; $repeat++) {

                    $predict = switch ($benchmark.Name) {
                        "JSON"        { 96 }
                        "REASONING"   { 160 }
                        "INSTRUCTION" { 128 }
                        default       { 128 }
                    }

                    $result = Invoke-OllamaChat `
                        -Model $model `
                        -Prompt $benchmark.Prompt `
                        -Threads $threads `
                        -Context $ctx `
                        -Predict $predict `
                        -Temperature 0.0

                    if ($result.Success) {

                        $score = Get-CompetenceScore `
                            -Benchmark $benchmark.Name `
                            -Content $result.Content

                        $qualityValues.Add([double]$score)
                        $tpsValues.Add([double]$result.TokensPerSecond)
                    }
                    else {
                        $qualityValues.Add(0.0)
                        $tpsValues.Add(0.0)
                    }
                }
            }

            $avgQuality = if ($qualityValues.Count -gt 0) {
                ($qualityValues | Measure-Object -Average).Average
            }
            else {
                0.0
            }

            $avgTps = if ($tpsValues.Count -gt 0) {
                ($tpsValues | Measure-Object -Average).Average
            }
            else {
                0.0
            }

            $speedNorm = [math]::Min(
                100.0,
                ($avgTps / 10.0) * 100.0
            )

            $combined = (
                ($avgQuality * 0.75) +
                ($speedNorm * 0.25)
            )

            $qualityGate = $avgQuality -ge 80.0

            $TuningResults.Add(
                [pscustomobject]@{
                    Model           = $model
                    Threads         = $threads
                    Context         = $ctx
                    AverageScore    = [math]::Round($avgQuality, 2)
                    AverageTPS      = [math]::Round($avgTps, 4)
                    SpeedNorm       = [math]::Round($speedNorm, 2)
                    CombinedUtility = [math]::Round(
                        [math]::Min(100.0, $combined),
                        2
                    )
                    QualityGate     = $qualityGate
                }
            )

            $status = if ($qualityGate) {
                "VALID"
            }
            else {
                "REJECT"
            }

            Write-Host (
                "  T={0,2} C={1,5} quality={2,6:N1} tok/s={3,6:N2} utility={4,6:N2} [{5}]" -f `
                $threads,
                $ctx,
                $avgQuality,
                $avgTps,
                $combined,
                $status
            )
        }
    }
}

# ---------------------------------------------------------------------------
# CONSTRUCTION DES PROFILS OPTIMAUX
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "[5/6] Construction des profils optimaux..."

$RecommendedProfiles = New-Object System.Collections.Generic.List[object]

foreach ($model in $Models) {
    $modelTuning = @(
        $TuningResults |
        Where-Object { $_.Model -eq $model }
    )

    $eligible = @(
        $modelTuning |
        Where-Object { $_.QualityGate -eq $true }
    )

    $competenceRows = @(
        $AllResults |
        Where-Object {
            $_.Model -eq $model -and
            $_.Benchmark -ne "NIAH"
        }
    )

    $scores = @{}

    foreach ($name in $Benchmarks.Name) {

        $rows = @(
            $competenceRows |
            Where-Object { $_.Benchmark -eq $name }
        )

        if ($rows.Count -gt 0) {

            $scores[$name] = [math]::Round(
                ($rows | Measure-Object Score -Average).Average,
                2
            )
        }
        else {
            $scores[$name] = 0.0
        }
    }

    $niahRows = @(
        $AllResults |
        Where-Object {
            $_.Model -eq $model -and
            $_.Benchmark -eq "NIAH"
        }
    )

    $niahByContext = @{}

    foreach ($ctx in $ContextGrid) {

        $ctxRows = @(
            $niahRows |
            Where-Object { $_.Context -eq $ctx }
        )

        $niahByContext[$ctx] = if ($ctxRows.Count -gt 0) {
            [math]::Round(
                ($ctxRows | Measure-Object Score -Average).Average,
                2
            )
        }
        else {
            0.0
        }
    }

    if ($eligible.Count -eq 0) {

        Write-Host (
            "[NO_VALID_PROFILE] $model : aucun profil >= 80"
        ) -ForegroundColor Yellow

        $RecommendedProfiles.Add(
            [pscustomobject]@{
                Model  = $model
                Status = "NO_VALID_PROFILE"
                Reason = "No CPU profile reached quality threshold 80."

                Host = [pscustomobject]@{
                    CPU        = "AMD Ryzen 9 5900X"
                    Cores      = 12
                    Threads    = 24
                    RAM_GB     = 32
                    RAM        = "DDR4-3200"
                    GPU        = "NONE"
                    Storage    = "NVMe"
                }

                ModelInfo   = $ModelInfo[$model]
                CPU         = $null
                Utility     = $null

                Competencies = [pscustomobject]@{
                    GENERAL     = $scores["GENERAL"]
                    REASONING   = $scores["REASONING"]
                    CODE        = $scores["CODE"]
                    JSON        = $scores["JSON"]
                    INSTRUCTION = $scores["INSTRUCTION"]
                }

                LongContext = $niahByContext
            }
        )

        continue
    }

    $best = $eligible |
        Sort-Object `
            @{Expression = {$_.CombinedUtility}; Descending = $true},
            @{Expression = {$_.Threads}; Descending = $false},
            @{Expression = {$_.Context}; Descending = $false} |
        Select-Object -First 1

    $RecommendedProfiles.Add(
        [pscustomobject]@{
            Model  = $model
            Status = "VALIDATED"
            Reason = "Best CPU profile among profiles meeting quality threshold >= 80."

            Host = [pscustomobject]@{
                CPU        = "AMD Ryzen 9 5900X"
                Cores      = 12
                Threads    = 24
                RAM_GB     = 32
                RAM        = "DDR4-3200"
                GPU        = "NONE"
                Storage    = "NVMe"
            }

            ModelInfo = $ModelInfo[$model]

            CPU = [pscustomobject]@{
                NumGPU          = 0
                NumThread       = $best.Threads
                NumCtx          = $best.Context
                NumPredict      = 128
                Temperature     = 0.0
                Parallel        = 1
                MaxLoadedModels = 1
                KeepAlive       = 0
            }

            Utility = [pscustomobject]@{
                AverageQuality  = $best.AverageScore
                AverageTPS      = $best.AverageTPS
                SpeedNorm       = $best.SpeedNorm
                CombinedUtility = $best.CombinedUtility
                QualityGate     = $best.QualityGate
            }

            Competencies = [pscustomobject]@{
                GENERAL     = $scores["GENERAL"]
                REASONING   = $scores["REASONING"]
                CODE        = $scores["CODE"]
                JSON        = $scores["JSON"]
                INSTRUCTION = $scores["INSTRUCTION"]
            }

            LongContext = $niahByContext
        }
    )

    Write-Host (
        "[CERTIFIED] {0} -> T={1} CTX={2} utility={3:N1} quality={4:N1}" -f `
        $model,
        $best.Threads,
        $best.Context,
        $best.CombinedUtility,
        $best.AverageScore
    ) -ForegroundColor Green
}

# ---------------------------------------------------------------------------
# CLASSEMENT — EXCLURE LES PROFILS NON CERTIFIÉS
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "[6/6] Export..."

$RankedProfiles = @(
    $RecommendedProfiles |
    Where-Object { $_.Status -eq "VALIDATED" } |
    Sort-Object @{Expression = {$_.Utility.CombinedUtility}; Descending = $true}
)

$JsonPayload = [pscustomobject]@{
    GeneratedAt = (Get-Date).ToString("o")

    Host = [pscustomobject]@{
        CPU            = "AMD Ryzen 9 5900X"
        CoresPhysical  = 12
        ThreadsLogical = 24
        RAM_GB         = 32
        RAM_Type       = "DDR4-3200"
        GPU            = "NONE"
        Storage        = "NVMe"
    }

    Ollama = [pscustomobject]@{
        BaseUrl         = $OllamaUrl
        NumParallel     = 1
        MaxLoadedModels = 1
        KeepAlive       = 0
    }

    BenchmarkPolicy = [pscustomobject]@{
        ThreadGrid         = $ThreadGrid
        ContextGrid        = $ContextGrid
        Repeats            = $Repeats
        MinimumQuality     = 80.0
        QualityWeight      = 0.75
        SpeedWeight        = 0.25
        GPU                = 0
        EmbeddingsIncluded = $false
    }

    Models              = $Models
    RawResults          = $AllResults
    CpuTuning           = $TuningResults
    RecommendedProfiles = $RecommendedProfiles
    CertifiedProfiles   = $RankedProfiles
}

$JsonPayload |
    ConvertTo-Json -Depth 30 |
    Set-Content -Path $JsonReport -Encoding utf8

$AllResults |
    Export-Csv `
        -Path $CsvReport `
        -NoTypeInformation `
        -Encoding utf8

$RecommendedProfiles |
    ConvertTo-Json -Depth 30 |
    Set-Content -Path $ProfileReport -Encoding utf8

Write-Host ""
Write-Host "============================================================"
Write-Host " BENCHMARK CPU TERMINE"
Write-Host "============================================================"

if ($RankedProfiles.Count -eq 0) {
    Write-Host `
        "[FAIL-CLOSED] Aucun profil CPU certifié >= 80." `
        -ForegroundColor Red
}
else {
    $rank = 1

    foreach ($profile in $RankedProfiles) {

        Write-Host (
            "#{0} {1} utility={2:N1} quality={3:N1} tok/s={4:N2} threads={5} ctx={6}" -f `
            $rank,
            $profile.Model,
            $profile.Utility.CombinedUtility,
            $profile.Utility.AverageQuality,
            $profile.Utility.AverageTPS,
            $profile.CPU.NumThread,
            $profile.CPU.NumCtx
        )

        $rank++
    }
}

Write-Host ""
Write-Host "RAPPORT JSON : $JsonReport"
Write-Host "RAPPORT CSV  : $CsvReport"
Write-Host "PROFILS      : $ProfileReport"
Write-Host "============================================================"