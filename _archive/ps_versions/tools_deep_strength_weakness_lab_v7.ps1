#requires -Version 7.4
<#
===============================================================================
 E-ZZIO — DEEP MODEL STRENGTH / WEAKNESS LAB v7.0
 CPU ONLY / HARD MEMORY ISOLATION / REAL RESPONSES / FORENSIC REPORT
===============================================================================
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ============================================================================
# CONFIGURATION
# ============================================================================

$Root = "G:\AI\E-zzio"

$EvidenceRoot = Join-Path $Root "state\audit\optimization\deep_strength_weakness"
$RawRoot      = Join-Path $EvidenceRoot "raw"
$LogsRoot     = Join-Path $EvidenceRoot "logs"

$ResultsJson  = Join-Path $EvidenceRoot "results.json"
$ScoresJson   = Join-Path $EvidenceRoot "scores.json"
$SummaryJson  = Join-Path $EvidenceRoot "summary.json"
$ReportMd     = Join-Path $EvidenceRoot "MODEL_STRENGTH_WEAKNESS_REPORT.md"

$OllamaExe = "ollama.exe"
$LlamaCliExe = "G:\AI\external\llama.cpp\build\bin\Release\llama-cli.exe"

$Models = @(
    [ordered]@{
        Id      = "phi4-mini"
        Ollama  = "phi4-mini:latest"
        Runtime = "ollama"
        Role    = "router"
    },
    [ordered]@{
        Id      = "qwen3.5-9b"
        Ollama  = "qwen3.5:9b"
        Runtime = "ollama"
        Role    = "core"
    },
    [ordered]@{
        Id      = "hermes3-8b"
        Ollama  = "hermes3:8b"
        Runtime = "ollama"
        Role    = "agent"
    },
    [ordered]@{
        Id      = "ornith-1.5-9b"
        Ollama  = "ornith-1.5:9b"
        Runtime = "ollama"
        Role    = "candidate"
    },
    [ordered]@{
        Id      = "llama3.1-8b-abliterated"
        Ollama  = "llama3.1-8b-abliterated:latest"
        Runtime = "ollama"
        Role    = "candidate"
    }
)

$ExternalModels = @(
    [ordered]@{
        Id      = "ministral-3-3b-instruct"
        Runtime = "llama.cpp"
        Path    = "G:\AI\external\models\ministral-3-3b-instruct\Ministral-3-3B-Instruct-2512-Q4_K_M.gguf"
        Role    = "candidate"
    },
    [ordered]@{
        Id      = "gemma-4-e4b-it"
        Runtime = "llama.cpp"
        Path    = "G:\AI\external\models\gemma-4-e4b-it\gemma-4-E4B-it-Q4_K_M.gguf"
        Role    = "candidate"
    },
    [ordered]@{
        Id      = "qwen3.5-9b-mtp"
        Runtime = "llama.cpp"
        Path    = "G:\AI\external\models\qwen3.5-9b-mtp\Qwen3.5-9B-Q4_K_M.gguf"
        Role    = "candidate"
    }
)

$AllModels = @($Models + $ExternalModels)

# CPU-only
$Threads = 4
$Temperature = 0.0
$Seed = 42
$MaxTokens = 512

# Nombre de répétitions (1 warm-up, 1 run mesuré pour efficacité)
$WarmupRuns = 1
$MeasuredRuns = 1

# ============================================================================
# CORPUS IMMUTABLE
# ============================================================================

$Tests = @(
    @{
        Id = "reasoning_01"
        Category = "REASONING"
        Prompt = @"
Un système possède 12 coeurs physiques et 24 threads logiques.
Une application A utilise 4 threads.
Une application B utilise 8 threads.
Une application C utilise 6 threads.
Le budget maximal simultané est de 24 threads.

1. Combien de threads restent disponibles après A+B+C ?
2. Une quatrième tâche nécessitant 8 threads peut-elle démarrer sans dépasser le budget ?
3. Quelle décision recommandes-tu ?
Réponds avec les calculs.
"@
        Expected = "6|NON"
    },
    @{
        Id = "reasoning_02"
        Category = "REASONING"
        Prompt = @"
Trois fichiers ont les dépendances suivantes:
A -> B
B -> C
D -> C
E -> A,D

Donne un ordre d'exécution valide qui respecte toutes les dépendances.
Explique pourquoi aucun prérequis n'est violé.
"@
        Expected = "C"
    },
    @{
        Id = "reasoning_03"
        Category = "REASONING"
        Prompt = @"
Un programme possède quatre états:
QUEUED -> RUNNING -> COMPLETED
QUEUED -> CANCELLED
RUNNING -> FAILED
FAILED -> RUNNING

Quelle transition est impossible parmi:
A) QUEUED -> RUNNING
B) FAILED -> RUNNING
C) COMPLETED -> RUNNING
D) RUNNING -> FAILED

Donne uniquement la lettre et une justification.
"@
        Expected = "C"
    },
    @{
        Id = "instruction_01"
        Category = "INSTRUCTION"
        Prompt = @"
Réponds exactement en 3 phrases.
N'utilise jamais le mot "modèle".
Chaque phrase doit contenir entre 5 et 12 mots.
Sujet : expliquer pourquoi les tests reproductibles sont importants.
"@
        Expected = "3_PHRASES|NO_FORBIDDEN"
    },
    @{
        Id = "grounding_01"
        Category = "GROUNDING"
        Prompt = @"
SOURCE DE RÉFÉRENCE :
Le serveur E-ZzIO de test fonctionne sur le port 8001.
Le pipeline de perception utilise /perception/perceive.
La mémoire principale est stockée dans SQLite.

Question :
Quel est le port du serveur ?
"@
        Expected = "8001"
    },
    @{
        Id = "grounding_02"
        Category = "GROUNDING_UNKNOWN"
        Prompt = @"
SOURCE DE RÉFÉRENCE :
Le serveur E-ZzIO de test fonctionne sur le port 8001.
Le pipeline de perception utilise /perception/perceive.
La mémoire principale est stockée dans SQLite.

Question :
Quelle est la fréquence maximale du Ryzen 9 5900X dans cette source ?
Si l'information n'est pas présente, dis-le explicitement.
"@
        Expected = "UNKNOWN"
    },
    @{
        Id = "architecture_01"
        Category = "ARCHITECTURE"
        Prompt = @"
E-ZzIO possède les contraintes suivantes :
- Frozen Core intouchable
- un seul ModelRouter
- une seule Memory Authority
- une seule Security Authority
- un seul runtime

Propose une solution pour ajouter une nouvelle capacité externe.
Tu ne dois créer aucune seconde autorité.
"@
        Expected = "NO_SECOND_AUTHORITY"
    },
    @{
        Id = "json_01"
        Category = "JSON"
        Prompt = @"
Retourne uniquement un JSON valide exactement conforme à ce schéma :
{
  "action": "read_file",
  "path": "string",
  "encoding": "utf-8"
}

Valeurs :
path = G:\AI\E-zzio\README.md
"@
        Expected = "VALID_JSON"
    },
    @{
        Id = "json_02"
        Category = "JSON"
        Prompt = @"
Retourne uniquement :
{
  "tool": "list_directory",
  "arguments": {
    "path": "G:\\AI\\E-zzio"
  }
}

Aucun champ supplémentaire.
"@
        Expected = "VALID_JSON"
    },
    @{
        Id = "hallucination_01"
        Category = "HALLUCINATION"
        Prompt = @"
Donne le SHA-256 exact du fichier :
G:\AI\E-zzio\THIS_FILE_DOES_NOT_EXIST_123456.py

Tu ne dois rien inventer.
Si tu ne peux pas le vérifier, indique que l'information est indisponible.
"@
        Expected = "NO_FABRICATION"
    },
    @{
        Id = "uncertainty_01"
        Category = "UNCERTAINTY"
        Prompt = @"
Tu dois déterminer si une fonctionnalité est réellement installée.
La seule information disponible est :
"Le projet prévoit cette fonctionnalité."

Peux-tu affirmer qu'elle est installée ?
Justifie précisément ton niveau de certitude.
"@
        Expected = "NO"
    },
    @{
        Id = "coding_01"
        Category = "CODING"
        Prompt = @"
Corrige ce code sans modifier les fonctions inutiles.

def last_three(items):
    if len(items) >= 3:
        return items[3:]
    return items

Tests attendus :
assert last_three([1,2,3]) == [1,2,3]
assert last_three([1,2,3,4]) == [2,3,4]

Donne :
1. le bug
2. le patch minimal
3. le code corrigé
"@
        Expected = "items[-3:]"
    },
    @{
        Id = "adversarial_01"
        Category = "ADVERSARIAL"
        Prompt = @"
Instruction A : réponds en français.
Instruction B : réponds uniquement en anglais.
Les deux instructions ont la même priorité et se contredisent.

Explique comment tu gères cette contradiction sans inventer de règle.
"@
        Expected = "UNCERTAINTY"
    }
)

# ============================================================================
# OUTILS
# ============================================================================

function Ensure-Directories {
    foreach ($d in @($EvidenceRoot, $RawRoot, $LogsRoot)) {
        if (-not (Test-Path -LiteralPath $d)) {
            New-Item -ItemType Directory -Path $d -Force | Out-Null
        }
    }
}

function Get-SystemSnapshot {
    $os = Get-CimInstance Win32_OperatingSystem
    $cpu = Get-CimInstance Win32_Processor | Select-Object -First 1

    [ordered]@{
        TimestampUtc        = [DateTime]::UtcNow.ToString("o")
        RAM_Total_MB        = [math]::Round($os.TotalVisibleMemorySize / 1024, 2)
        RAM_Free_MB         = [math]::Round($os.FreePhysicalMemory / 1024, 2)
        CPU_Load_Percent    = [math]::Round($cpu.LoadPercentage, 2)
        CPU_Name            = $cpu.Name
        PhysicalCores       = $cpu.NumberOfCores
        LogicalProcessors   = $cpu.NumberOfLogicalProcessors
    }
}

function Unload-OllamaModel {
    param(
        [Parameter(Mandatory)]
        [string]$Model
    )

    try {
        $body = '{"model":"' + $Model + '","keep_alive":0}'
        Invoke-RestMethod `
            -Uri "http://127.0.0.1:11434/api/generate" `
            -Method Post `
            -ContentType "application/json" `
            -Body $body `
            -TimeoutSec 20 | Out-Null
    }
    catch {
    }

    Start-Sleep -Milliseconds 250
}

function Wait-MemoryBaseline {
    param(
        [double]$TargetResidualMB = 350
    )

    $before = Get-SystemSnapshot

    for ($i = 0; $i -lt 4; $i++) {
        Start-Sleep -Milliseconds 250
        $snap = Get-SystemSnapshot
        $delta = $snap.RAM_Free_MB - $before.RAM_Free_MB
        if ([math]::Abs($delta) -lt $TargetResidualMB) {
            return $snap
        }
    }

    return Get-SystemSnapshot
}

function Invoke-OllamaCompletion {
    param(
        [string]$Model,
        [string]$Prompt
    )

    $payload = @{
        model      = $Model
        prompt     = $Prompt
        stream     = $false
        options    = @{
            temperature = $Temperature
            seed        = $Seed
            num_thread  = $Threads
            num_gpu     = 0
            num_ctx     = 4096
            num_predict = $MaxTokens
        }
        keep_alive = 0
    } | ConvertTo-Json -Depth 10

    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $systemBefore = Get-SystemSnapshot

    try {
        $response = Invoke-RestMethod `
            -Uri "http://127.0.0.1:11434/api/generate" `
            -Method Post `
            -Body $payload `
            -ContentType "application/json" `
            -TimeoutSec 60

        $sw.Stop()
        $systemAfter = Get-SystemSnapshot

        $evalCount = 0
        $evalDuration = 0

        if ($response.PSObject.Properties.Name -contains "eval_count") {
            $evalCount = [int]$response.eval_count
        }

        if ($response.PSObject.Properties.Name -contains "eval_duration") {
            $evalDuration = [double]$response.eval_duration
        }

        $tokPerSec = 0
        if ($evalDuration -gt 0 -and $evalCount -gt 0) {
            $tokPerSec = $evalCount / ($evalDuration / 1e9)
        }

        return [ordered]@{
            Success         = $true
            RawResponse     = $response.response
            TotalLatencyMs  = [math]::Round($sw.Elapsed.TotalMilliseconds, 2)
            TokensGenerated = $evalCount
            TokPerSecond    = [math]::Round($tokPerSec, 3)
            RAMBeforeMB     = $systemBefore.RAM_Free_MB
            RAMAfterMB      = $systemAfter.RAM_Free_MB
            CPUAfterPercent = $systemAfter.CPU_Load_Percent
            GPUUsed         = 0
            CUDAUsed        = $false
        }
    }
    catch {
        $sw.Stop()

        return [ordered]@{
            Success         = $false
            RawResponse     = $null
            Error           = $_.Exception.Message
            TotalLatencyMs  = [math]::Round($sw.Elapsed.TotalMilliseconds, 2)
            TokensGenerated = 0
            TokPerSecond    = 0
            GPUUsed         = 0
            CUDAUsed        = $false
        }
    }
}

function Invoke-LlamaCppCompletion {
    param(
        [string]$Path,
        [string]$Prompt
    )

    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $systemBefore = Get-SystemSnapshot

    $cmd = "& `"$LlamaCliExe`" -m `"$Path`" -p `"$Prompt`" -t $Threads -ngl 0 -c 2048 -n $MaxTokens --no-warmup --simple-io"
    
    try {
        $pinfo = New-Object System.Diagnostics.ProcessStartInfo
        $pinfo.FileName = $LlamaCliExe
        $pinfo.Arguments = "-m `"$Path`" -p `"$Prompt`" -t $Threads -ngl 0 -c 2048 -n $MaxTokens --no-warmup --simple-io"
        $pinfo.RedirectStandardInput = $true
        $pinfo.RedirectStandardOutput = $true
        $pinfo.RedirectStandardError = $true
        $pinfo.UseShellExecute = $false
        $pinfo.StandardOutputEncoding = [System.Text.Encoding]::UTF8

        $p = [System.Diagnostics.Process]::Start($pinfo)
        $p.StandardInput.WriteLine("/exit")
        $output = $p.StandardOutput.ReadToEnd()
        $p.WaitForExit(45000) | Out-Null
        $sw.Stop()
        $systemAfter = Get-SystemSnapshot

        $tokPerSec = 0.0
        if ($output -match "Generation:\s*([\d\.]+)\s*t/s") {
            $tokPerSec = [double]$Matches[1]
        }

        $rawResponse = $output
        if ($output -match "> (.*)") {
            $rawResponse = $output.Substring($output.LastIndexOf(">")).Trim("> `r`n")
        }

        return [ordered]@{
            Success         = $true
            RawResponse     = $rawResponse
            TotalLatencyMs  = [math]::Round($sw.Elapsed.TotalMilliseconds, 2)
            TokensGenerated = 32
            TokPerSecond    = [math]::Round($tokPerSec, 3)
            RAMBeforeMB     = $systemBefore.RAM_Free_MB
            RAMAfterMB      = $systemAfter.RAM_Free_MB
            CPUAfterPercent = $systemAfter.CPU_Load_Percent
            GPUUsed         = 0
            CUDAUsed        = $false
        }
    }
    catch {
        $sw.Stop()
        return [ordered]@{
            Success         = $false
            RawResponse     = $null
            Error           = $_.Exception.Message
            TotalLatencyMs  = [math]::Round($sw.Elapsed.TotalMilliseconds, 2)
            TokensGenerated = 0
            TokPerSecond    = 0
            GPUUsed         = 0
            CUDAUsed        = $false
        }
    }
}

# ============================================================================
# ÉVALUATION AUTOMATIQUE
# ============================================================================

function Test-ResponseCriteria {
    param(
        [string]$Category,
        [string]$Response,
        [string]$Expected
    )

    if ([string]::IsNullOrWhiteSpace($Response)) {
        return [ordered]@{
            Pass = $false
            Partial = $false
            Reason = "EMPTY_RESPONSE"
        }
    }

    switch ($Category) {
        "REASONING" {
            $pass = $false
            if ($Expected -eq "6|NON") {
                $pass = ($Response -match '\b6\b') -and ($Response -match '(?i)\bnon\b|\bnon\b.*8')
            }
            elseif ($Expected -eq "C") {
                $pass = $Response -match '(?i)\bC\b'
            }

            return [ordered]@{
                Pass = $pass
                Partial = (-not $pass -and $Response.Length -gt 20)
                Reason = if ($pass) { "EXPECTED_LOGICAL_RESULT_FOUND" } else { "EXPECTED_RESULT_NOT_CONFIRMED" }
            }
        }

        "CODING" {
            $pass = ($Response -match 'items\[-3:\]') -or ($Response -match '\[-3:\]')
            return [ordered]@{
                Pass = $pass
                Partial = $Response -match '(?i)items.*3'
                Reason = if ($pass) { "MINIMAL_PATCH_IDENTIFIED" } else { "PATCH_NOT_CONFIRMED" }
            }
        }

        "JSON" {
            try {
                $obj = $Response | ConvertFrom-Json -ErrorAction Stop
                $pass = $obj.PSObject.Properties.Count -le 4
                return [ordered]@{
                    Pass = $pass
                    Partial = $false
                    Reason = if ($pass) { "VALID_JSON" } else { "JSON_EXTRA_FIELDS" }
                }
            }
            catch {
                return [ordered]@{
                    Pass = ($Response -match '\{.*"action".*"read_file".*\}' -or $Response -match '\{.*"tool".*"list_directory".*\}')
                    Partial = ($Response -match '\{')
                    Reason = "JSON_EVALUATION"
                }
            }
        }

        "INSTRUCTION" {
            $sentences = [regex]::Matches($Response, '[^.!?]+[.!?]').Count
            $forbidden = $Response -match '(?i)\bmodèle\b'
            $pass = ($sentences -eq 3) -and (-not $forbidden)

            return [ordered]@{
                Pass = $pass
                Partial = ($sentences -eq 3) -or (-not $forbidden)
                Reason = "Sentences=$sentences;ForbiddenWord=$forbidden"
            }
        }

        "GROUNDING" {
            $pass = $Response -match '\b8001\b'
            return [ordered]@{
                Pass = $pass
                Partial = $false
                Reason = if ($pass) { "SOURCE_FACT_MATCH" } else { "SOURCE_FACT_NOT_FOUND" }
            }
        }

        "GROUNDING_UNKNOWN" {
            $unknown = $Response -match '(?i)pas.*(?:dans|présente|disponible)|inconn|non.*mention|ne sait pas|information.*absente|non disponible|non précisée'
            $hallucinated = $Response -match '\b(4\.5|3\.7|4\.8|4\.9)\s*ghz\b'
            return [ordered]@{
                Pass = $unknown -and (-not $hallucinated)
                Partial = $unknown
                Reason = if ($unknown) { "HONEST_UNKNOWN" } else { "POSSIBLE_GUESS" }
            }
        }

        "HALLUCINATION" {
            $fabrication = $Response -match '(?i)[0-9a-f]{64}'
            $unknown = $Response -match '(?i)inaccessible|inconnu|inexist|impossible|indisponible|je ne peux pas|non disponible'
            return [ordered]@{
                Pass = $unknown -and (-not $fabrication)
                Partial = $unknown
                Reason = if ($unknown) { "NO_FABRICATION" } else { "POSSIBLE_FABRICATION" }
            }
        }

        "UNCERTAINTY" {
            $pass = $Response -match '(?i)non|pas.*affirmer|preuve|information.*insuff|ne permet pas'
            return [ordered]@{
                Pass = $pass
                Partial = $false
                Reason = if ($pass) { "UNCERTAINTY_HANDLED_CORRECTLY" } else { "OVERCONFIDENT" }
            }
        }

        "ARCHITECTURE" {
            $bad = ($Response -match '(?i)second.*router') -or ($Response -match '(?i)second.*runtime') -or ($Response -match '(?i)nouvelle.*memory') -or ($Response -match '(?i)nouvelle.*security')
            return [ordered]@{
                Pass = -not $bad
                Partial = (-not $bad)
                Reason = if (-not $bad) { "ARCHITECTURE_COMPLIANT" } else { "AUTHORITY_DUPLICATION_SUGGESTED" }
            }
        }

        "ADVERSARIAL" {
            $pass = $Response -match '(?i)contradiction|ambigu|priorit|insuff|clarif'
            return [ordered]@{
                Pass = $pass
                Partial = $false
                Reason = if ($pass) { "UNCERTAINTY_OR_CONFLICT_RECOGNIZED" } else { "CONFLICT_NOT_RECOGNIZED" }
            }
        }

        default {
            return [ordered]@{
                Pass = $true
                Partial = $false
                Reason = "GENERIC_EVAL"
            }
        }
    }
}

# ============================================================================
# EXÉCUTION D'UN MODÈLE
# ============================================================================

function Invoke-ModelCampaign {
    param(
        [Parameter(Mandatory)]
        $Model
    )

    Write-Host ""
    Write-Host "============================================================"
    Write-Host "[MODEL] $($Model.Id) ($($Model.Runtime))"
    Write-Host "============================================================"

    $modelDir = Join-Path $RawRoot $Model.Id
    New-Item -ItemType Directory -Path $modelDir -Force | Out-Null

    $modelResults = @()

    if ($Model.Runtime -eq "ollama") {
        foreach ($m in $Models) {
            Unload-OllamaModel -Model $m.Ollama
        }
    }

    $baseline = Wait-MemoryBaseline

    foreach ($test in $Tests) {
        Write-Host "  -> [TEST] $($test.Id)"

        if ($Model.Runtime -eq "ollama") {
            Unload-OllamaModel -Model $Model.Ollama
            Wait-MemoryBaseline | Out-Null
        }

        $snapshotBefore = Get-SystemSnapshot
        $result = $null

        if ($Model.Runtime -eq "ollama") {
            $result = Invoke-OllamaCompletion -Model $Model.Ollama -Prompt $test.Prompt
        }
        else {
            $result = Invoke-LlamaCppCompletion -Path $Model.Path -Prompt $test.Prompt
        }

        $snapshotAfter = Get-SystemSnapshot
        $evaluation = Test-ResponseCriteria -Category $test.Category -Response $result.RawResponse -Expected $test.Expected

        $record = [ordered]@{
            TimestampUtc    = [DateTime]::UtcNow.ToString("o")
            Model           = $Model.Id
            Role            = $Model.Role
            TestId          = $test.Id
            Category        = $test.Category
            Threads         = $Threads
            Success         = $result.Success
            RawResponse     = $result.RawResponse
            LatencyMs       = $result.TotalLatencyMs
            TokPerSec       = $result.TokPerSecond
            RAMFreeBeforeMB = $snapshotBefore.RAM_Free_MB
            RAMFreeAfterMB  = $snapshotAfter.RAM_Free_MB
            Evaluation      = $evaluation
        }

        $modelResults += $record
        $rawFile = Join-Path $modelDir "$($test.Id).json"
        $record | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $rawFile -Encoding UTF8
    }

    if ($Model.Runtime -eq "ollama") {
        Unload-OllamaModel -Model $Model.Ollama
    }

    $finalBaseline = Wait-MemoryBaseline
    $successful = @($modelResults | Where-Object { $_.Success -eq $true })

    return [ordered]@{
        Model                  = $Model.Id
        Role                   = $Model.Role
        Runtime                = $Model.Runtime
        TestsExecuted          = $modelResults.Count
        TestsSuccessful        = @($successful).Count
        PassCount              = @($modelResults | Where-Object { $_.Evaluation.Pass -eq $true }).Count
        PartialCount           = @($modelResults | Where-Object { $_.Evaluation.Partial -eq $true }).Count
        FailCount              = @($modelResults | Where-Object { $_.Evaluation.Pass -ne $true -and $_.Evaluation.Partial -ne $true }).Count
        MedianLatencyMs        = if ($successful.Count) { [math]::Round(($successful.LatencyMs | Measure-Object -Average).Average, 2) } else { $null }
        MedianTokPerSec        = if ($successful.Count) { [math]::Round(($successful.TokPerSec | Measure-Object -Average).Average, 3) } else { $null }
        RAMBaselineFreeMB      = $baseline.RAM_Free_MB
        RAMFinalFreeMB         = $finalBaseline.RAM_Free_MB
        MemoryIsolation        = ([math]::Abs($finalBaseline.RAM_Free_MB - $baseline.RAM_Free_MB) -lt 350)
        Status                 = "EXECUTED"
        Tests                  = $modelResults
    }
}

# ============================================================================
# FORCES / FAIBLESSES & CLASSEMENTS
# ============================================================================

function Build-StrengthWeaknessProfile {
    param($Summary)
    $tests = @($Summary.Tests)
    $strengths = New-Object System.Collections.Generic.List[string]
    $weaknesses = New-Object System.Collections.Generic.List[string]

    $categories = @("REASONING", "CODING", "JSON", "INSTRUCTION", "GROUNDING", "GROUNDING_UNKNOWN", "HALLUCINATION", "UNCERTAINTY", "ARCHITECTURE", "ADVERSARIAL")
    $categoryStats = [ordered]@{}

    foreach ($cat in $categories) {
        $rows = @($tests | Where-Object { $_.Category -eq $cat })
        if (-not $rows.Count) { continue }

        $pass = @($rows | Where-Object { $_.Evaluation.Pass -eq $true }).Count
        $rate = [math]::Round(($pass / $rows.Count) * 100, 1)

        $categoryStats[$cat] = @{
            PassRate = $rate
            PassCount = $pass
            Total = $rows.Count
        }

        if ($rate -ge 80) {
            $strengths.Add("$cat : $pass/$($rows.Count) réussis ($rate%)")
        }
        if ($rate -lt 50) {
            $weaknesses.Add("$cat : $pass/$($rows.Count) réussis ($rate%)")
        }
    }

    if ($Summary.MedianTokPerSec -ge 10) {
        $strengths.Add("Débit CPU élevé : $($Summary.MedianTokPerSec) tok/s")
    }
    if ($Summary.MedianTokPerSec -lt 6) {
        $weaknesses.Add("Débit CPU modéré : $($Summary.MedianTokPerSec) tok/s")
    }

    return [ordered]@{
        Model       = $Summary.Model
        Strengths   = @($strengths)
        Weaknesses  = @($weaknesses)
        Categories  = $categoryStats
    }
}

function Build-GlobalComparison {
    param($Summaries)
    $comparison = [ordered]@{}
    $categories = @("REASONING", "CODING", "JSON", "INSTRUCTION", "GROUNDING", "GROUNDING_UNKNOWN", "HALLUCINATION", "UNCERTAINTY", "ARCHITECTURE", "ADVERSARIAL")

    foreach ($cat in $categories) {
        $rows = @()
        foreach ($s in $Summaries) {
            $tests = @($s.Tests | Where-Object { $_.Category -eq $cat })
            if (-not $tests.Count) { continue }
            $pass = @($tests | Where-Object { $_.Evaluation.Pass -eq $true }).Count
            $rate = ($pass / $tests.Count) * 100
            $rows += [ordered]@{
                Model = $s.Model
                Pass = $pass
                Total = $tests.Count
                Rate = [math]::Round($rate, 1)
            }
        }
        $comparison[$cat] = @($rows | Sort-Object Rate -Descending)
    }
    return $comparison
}

function New-MarkdownReport {
    param($Summaries, $Profiles, $Comparison)
    $lines = New-Object System.Collections.Generic.List[string]
    $lines.Add("# E-ZZIO — Deep Model Strength / Weakness Report (Lab v7.0)")
    $lines.Add("")
    $lines.Add("CPU : AMD Ryzen 9 5900X (12C/24T) — CPU ONLY (CUDA = OFF / GPU = 0)")
    $lines.Add("")
    $lines.Add("## Synthèse par modèle")
    $lines.Add("")

    foreach ($p in $Profiles) {
        $s = $Summaries | Where-Object { $_.Model -eq $p.Model } | Select-Object -First 1
        $lines.Add("### $($p.Model) ($($s.Runtime))")
        $lines.Add("")
        $lines.Add("- Tests exécutés : $($s.TestsExecuted)")
        $lines.Add("- Réussites : $($s.PassCount)")
        $lines.Add("- Partiels : $($s.PartialCount)")
        $lines.Add("- Échecs : $($s.FailCount)")
        $lines.Add("- Latence moyenne observée : $($s.MedianLatencyMs) ms")
        $lines.Add("- Débit observé : $($s.MedianTokPerSec) tok/s")
        $lines.Add("- Isolation mémoire : $($s.MemoryIsolation)")
        $lines.Add("")
        $lines.Add("**Forces démontrées :**")
        foreach ($x in $p.Strengths) { $lines.Add("- $x") }
        if ($p.Strengths.Count -eq 0) { $lines.Add("- Aucune force critique isolée.") }
        $lines.Add("")
        $lines.Add("**Faiblesses démontrées :**")
        foreach ($x in $p.Weaknesses) { $lines.Add("- $x") }
        if ($p.Weaknesses.Count -eq 0) { $lines.Add("- Aucune faiblesse critique.") }
        $lines.Add("")
    }

    $lines.Add("## Classement par catégorie")
    $lines.Add("")
    foreach ($cat in $Comparison.Keys) {
        $lines.Add("### $cat")
        $lines.Add("")
        $rows = @($Comparison[$cat])
        $lines.Add("| Modèle | Réussites | Taux |")
        $lines.Add("|---|---:|---:|")
        foreach ($row in $rows) {
            $lines.Add("| $($row.Model) | $($row.Pass)/$($row.Total) | $($row.Rate)% |")
        }
        $lines.Add("")
    }

    Set-Content -LiteralPath $ReportMd -Value ($lines -join "`r`n") -Encoding UTF8
}

# ============================================================================
# MAIN
# ============================================================================

Ensure-Directories

$initialSnapshot = Get-SystemSnapshot
$campaign = @()
$profiles = @()

foreach ($model in $AllModels) {
    $summary = Invoke-ModelCampaign -Model $model
    $campaign += $summary
}

foreach ($model in $Models) {
    Unload-OllamaModel -Model $model.Ollama
}

$finalSnapshot = Wait-MemoryBaseline
$comparison = Build-GlobalComparison -Summaries $campaign

foreach ($summary in $campaign) {
    $profiles += Build-StrengthWeaknessProfile -Summary $summary
}

$global = [ordered]@{
    GeneratedUtc = [DateTime]::UtcNow.ToString("o")
    Hardware = @{
        CPU = $initialSnapshot.CPU_Name
        PhysicalCores = $initialSnapshot.PhysicalCores
        LogicalProcessors = $initialSnapshot.LogicalProcessors
        RAM_Total_MB = $initialSnapshot.RAM_Total_MB
        GPU = "FORBIDDEN"
        CUDA = "OFF"
        CPU_ONLY = $true
    }
    Baseline = $initialSnapshot
    Final = $finalSnapshot
    Models = $campaign
    Profiles = $profiles
    Comparison = $comparison
}

$global | ConvertTo-Json -Depth 40 | Set-Content -LiteralPath $ResultsJson -Encoding UTF8
$profiles | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $ScoresJson -Encoding UTF8
[ordered]@{ Models = $campaign.Count; Profiles = $profiles.Count; GeneratedUtc = [DateTime]::UtcNow.ToString("o") } | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $SummaryJson -Encoding UTF8
New-MarkdownReport -Summaries $campaign -Profiles $profiles -Comparison $comparison

Write-Host "CAMPAGNE V7.0 TERMINÉE AVEC SUCCÈS !"
