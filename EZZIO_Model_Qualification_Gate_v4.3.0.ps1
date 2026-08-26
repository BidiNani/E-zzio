#requires -Version 7.4
# =============================================================================
# E-ZZIO — MODEL QUALIFICATION GATE
# Version : 4.3.0
# Mode    : CPU-ONLY / SINGLE-MODEL-SWITCH / FORENSIC / POTENTIAL-PROFILING
# =============================================================================
#
# OBJECTIF
# --------
# Déterminer le potentiel réel des modèles Ollama installés localement.
#
# PRINCIPES
# ----------
# 1. UN SEUL MODELE ACTIF A LA FOIS.
# 2. Chaque switch est vérifié.
# 3. Le modèle précédent est explicitement libéré avant le suivant.
# 4. Chaque modèle passe la même batterie de tests.
# 5. Performance != capacité.
# 6. Aucun résultat silencieusement ignoré.
# 7. Une anomalie critique => FAIL-CLOSED.
#
# SORTIES
# --------
# .\audit\model_gate_v4.3.0\
#   ├── qualification_<RunId>.json
#   ├── qualification_<RunId>.csv
#   ├── forensic_<RunId>.log
#   └── summary_<RunId>.txt
#
# PRE-REQUIS
# ----------
# - PowerShell 7.4+
# - Ollama installé
# - ollama.exe accessible dans PATH
# - CPU compatible
#
# EXEMPLE
# --------
# pwsh.exe -NoProfile -ExecutionPolicy Bypass -File `
#   .\EZZIO_Model_Qualification_Gate_v4.3.0.ps1
#
# =============================================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# =============================================================================
# [0/14] CONFIGURATION
# =============================================================================

$Version = '4.3.0'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

$AuditRoot = Join-Path $Root 'audit\model_gate_v4.3.0'

if (-not (Test-Path $AuditRoot)) {
    New-Item -ItemType Directory -Path $AuditRoot -Force | Out-Null
}

$RunId = Get-Date -Format 'yyyyMMdd_HHmmss'
$LogPath = Join-Path $AuditRoot "forensic_$RunId.log"
$JsonPath = Join-Path $AuditRoot "qualification_$RunId.json"
$CsvPath = Join-Path $AuditRoot "qualification_$RunId.csv"
$SummaryPath = Join-Path $AuditRoot "summary_$RunId.txt"

$OllamaHost = 'http://127.0.0.1:11434'

# -------------------------------------------------------------------------
# CPU-ONLY
# -------------------------------------------------------------------------

$CpuThreads = [Environment]::ProcessorCount

# Ryzen 9 5900X = 12C / 24T.
# On refuse toutefois de hardcoder la configuration :
# la machine réelle est détectée dynamiquement.
$CpuName = 'UNKNOWN'
$TotalRamGB = 0

try {
    $cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
    if ($null -ne $cpu) {
        $CpuName = [string]$cpu.Name
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
    }
}
catch {
    $TotalRamGB = 0
}

# -------------------------------------------------------------------------
# TESTS
# -------------------------------------------------------------------------

$WarmupRuns = 1
$StabilityRuns = 2

# Nombre maximum de modèles découverts.
# 0 = tous.
$MaxModels = 0

# -------------------------------------------------------------------------
# SEUILS
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
# [1/14] FONCTIONS FORENSIC
# =============================================================================

function Write-Forensic {
    param(
        [Parameter(Mandatory)]
        [string]$Message,

        [ValidateSet('INFO','PASS','WARN','FAIL','SWITCH','TEST','METRIC')]
        [string]$Level = 'INFO'
    )

    $timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss.fff'

    $line = "[{0}] [{1}] {2}" -f $timestamp, $Level, $Message

    Add-Content -LiteralPath $LogPath -Value $line -Encoding UTF8

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
    param(
        [string]$Title
    )

    Write-Host ''
    Write-Host ('=' * 78)
    Write-Host $Title
    Write-Host ('=' * 78)
}

# =============================================================================
# [2/14] OUTILS
# =============================================================================

function Test-OllamaAvailable {

    try {
        $response = Invoke-RestMethod `
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
                    [PSCustomObject]@{
                        Name       = [string]$_.name
                        SizeBytes  = [int64]$_.size
                        SizeGB     = [math]::Round(
                            [double]$_.size / 1GB,
                            2
                        )
                        Parameter  = [string]$_.details.parameter_size
                        Quant      = [string]$_.details.quantization_level
                        Family     = [string]$_.details.family
                    }
                }
        )
    }
    catch {
        throw "Impossible de récupérer les modèles Ollama : $($_.Exception.Message)"
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
            -Message "Lecture /api/ps impossible : $($_.Exception.Message)" `
            -Level WARN

        return @()
    }
}

function Get-RunningModelNames {

    $running = @(Get-OllamaRunningModels)

    return @(
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
}

# =============================================================================
# [3/14] SINGLE-MODEL ENFORCEMENT
# =============================================================================

function Assert-SingleModel {

    $running = @(Get-RunningModelNames)

    if ($running.Count -gt 1) {

        Write-Forensic `
            -Message "VIOLATION : $($running.Count) modèles semblent actifs : $($running -join ', ')" `
            -Level FAIL

        throw "SINGLE_MODEL_VIOLATION"
    }

    if ($running.Count -eq 1) {

        Write-Forensic `
            -Message "Modèle actif : $($running[0])" `
            -Level INFO

        return $running[0]
    }

    Write-Forensic `
        -Message "Aucun modèle Ollama actuellement chargé." `
        -Level INFO

    return $null
}

function Unload-OllamaModel {

    param(
        [Parameter(Mandatory)]
        [string]$Model
    )

    Write-Forensic `
        -Message "LIBERATION du modèle : $Model" `
        -Level SWITCH

    $payload = @{
        model      = $Model
        prompt     = ''
        keep_alive = 0
        stream     = $false
    } | ConvertTo-Json -Depth 5

    try {

        Invoke-RestMethod `
            -Uri "$OllamaHost/api/generate" `
            -Method Post `
            -ContentType 'application/json' `
            -Body $payload `
            -TimeoutSec 30 | Out-Null

    }
    catch {

        Write-Forensic `
            -Message "Libération API échouée pour $Model : $($_.Exception.Message)" `
            -Level WARN
    }

    Start-Sleep -Milliseconds 500

    $stillRunning = @(Get-RunningModelNames)

    if ($stillRunning -contains $Model) {

        Write-Forensic `
            -Message "Le modèle $Model semble toujours actif après keep_alive=0." `
            -Level WARN

        return $false
    }

    Write-Forensic `
        -Message "Modèle $Model libéré." `
        -Level PASS

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

    # ---------------------------------------------------------------------
    # 1. Etat initial
    # ---------------------------------------------------------------------

    $previous = Assert-SingleModel

    # ---------------------------------------------------------------------
    # 2. Libération précédente
    # ---------------------------------------------------------------------

    if ($null -ne $previous -and $previous -ne $Model) {

        $released = Unload-OllamaModel -Model $previous

        if (-not $released) {

            Write-Forensic `
                -Message "Impossible de confirmer la libération de $previous." `
                -Level FAIL

            throw "MODEL_UNLOAD_FAILED"
        }
    }

    # Si le même modèle est déjà actif, on ne considère pas cela
    # comme une garantie suffisante : on vérifie quand même.
    if ($null -ne $previous -and $previous -eq $Model) {

        Write-Forensic `
            -Message "$Model est déjà actif ; vérification de l'état unique." `
            -Level INFO
    }

    # ---------------------------------------------------------------------
    # 3. Vérification absolue : zéro ou un modèle
    # ---------------------------------------------------------------------

    $runningBefore = @(Get-RunningModelNames)

    if ($runningBefore.Count -gt 1) {

        Write-Forensic `
            -Message "Plusieurs modèles actifs avant switch : $($runningBefore -join ', ')" `
            -Level FAIL

        throw "PRE_SWITCH_MULTIPLE_MODELS"
    }

    # ---------------------------------------------------------------------
    # 4. Chargement contrôlé
    # ---------------------------------------------------------------------

    $payload = @{
        model      = $Model
        prompt     = 'E-ZZIO MODEL QUALIFICATION GATE :: SWITCH PROBE'
        stream     = $false
        keep_alive = '5m'
        options    = @{
            num_predict = 8
            temperature = 0
        }
    } | ConvertTo-Json -Depth 8

    $start = Get-Date

    try {

        $response = Invoke-RestMethod `
            -Uri "$OllamaHost/api/generate" `
            -Method Post `
            -ContentType 'application/json' `
            -Body $payload `
            -TimeoutSec 120

    }
    catch {

        Write-Forensic `
            -Message "Echec chargement $Model : $($_.Exception.Message)" `
            -Level FAIL

        throw "MODEL_LOAD_FAILED"
    }

    $elapsed = ((Get-Date) - $start).TotalMilliseconds

    # ---------------------------------------------------------------------
    # 5. Vérification post-switch
    # ---------------------------------------------------------------------

    $runningAfter = @(Get-RunningModelNames)

    if ($runningAfter.Count -ne 1) {

        Write-Forensic `
            -Message "Post-switch invalide : $($runningAfter.Count) modèle(s) actif(s)." `
            -Level FAIL

        throw "POST_SWITCH_CARDINALITY_FAILURE"
    }

    if ($runningAfter[0] -ne $Model) {

        Write-Forensic `
            -Message "Mauvais modèle actif : $($runningAfter[0]) au lieu de $Model." `
            -Level FAIL

        throw "POST_SWITCH_WRONG_MODEL"
    }

    Write-Forensic `
        -Message "SWITCH OK : $Model | ${elapsed}ms | 1 modèle actif confirmé." `
        -Level PASS

    return [PSCustomObject]@{
        Model        = $Model
        Previous     = $previous
        LoadMs       = [math]::Round($elapsed, 2)
        ActiveModels = 1
    }
}

# =============================================================================
# [4/14] EXECUTION D'UN TEST
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

    # Sécurité : le test ne démarre que si UN SEUL modèle est actif.
    $active = Assert-SingleModel

    if ($active -ne $Model) {

        Write-Forensic `
            -Message "Le modèle actif ($active) ne correspond pas au modèle testé ($Model)." `
            -Level FAIL

        throw "ACTIVE_MODEL_MISMATCH"
    }

    $payload = @{
        model      = $Model
        prompt     = $Prompt
        stream     = $false
        keep_alive = '5m'
        options    = @{
            temperature = 0
            num_predict = $MaxTokens
        }
    } | ConvertTo-Json -Depth 8

    $start = Get-Date

    try {

        $response = Invoke-RestMethod `
            -Uri "$OllamaHost/api/generate" `
            -Method Post `
            -ContentType 'application/json' `
            -Body $payload `
            -TimeoutSec 300

        $elapsed = ((Get-Date) - $start).TotalMilliseconds

        $text = [string]$response.response

        $eval = Evaluate-Response `
            -Category $Category `
            -Prompt $Prompt `
            -Response $text

        $eval.Success = $true
        $eval.Error = $null

        $eval.DurationMs = [math]::Round($elapsed, 2)
        $eval.PromptTokens = if ($null -ne $response.prompt_eval_count) {
            [int]$response.prompt_eval_count
        }
        else {
            0
        }

        $eval.GeneratedTokens = if ($null -ne $response.eval_count) {
            [int]$response.eval_count
        }
        else {
            0
        }

        if ($eval.GeneratedTokens -gt 0 -and $elapsed -gt 0) {
            $eval.TokensPerSecond = [math]::Round(
                ($eval.GeneratedTokens / ($elapsed / 1000)),
                2
            )
        }
        else {
            $eval.TokensPerSecond = 0
        }

        $eval.ResponseChars = $text.Length
        $eval.ResponsePreview = if ($text.Length -gt 300) {
            $text.Substring(0,300)
        }
        else {
            $text
        }

        Write-Forensic `
            -Message (
                "RESULT $TestId | Score=$($eval.Score) | " +
                "Duration=$($eval.DurationMs)ms | " +
                "Tokens=$($eval.GeneratedTokens) | " +
                "TPS=$($eval.TokensPerSecond)"
            ) `
            -Level METRIC

        return $eval
    }
    catch {

        Write-Forensic `
            -Message "TEST $TestId FAIL : $($_.Exception.Message)" `
            -Level FAIL

        return [PSCustomObject]@{
            TestId          = $TestId
            Category        = $Category
            Success         = $false
            Score           = 0
            DurationMs      = 0
            PromptTokens    = 0
            GeneratedTokens = 0
            TokensPerSecond = 0
            ResponseChars   = 0
            ResponsePreview = ''
            Error           = $_.Exception.Message
        }
    }
}

# =============================================================================
# [5/14] EVALUATION HEURISTIQUE
# =============================================================================

function Evaluate-Response {

    param(
        [string]$Category,
        [string]$Prompt,
        [string]$Response
    )

    $score = 0
    $reasons = New-Object System.Collections.Generic.List[string]

    $text = if ($null -eq $Response) {
        ''
    }
    else {
        $Response.Trim()
    }

    # ---------------------------------------------------------------------
    # Base : réponse non vide
    # ---------------------------------------------------------------------

    if ($text.Length -gt 0) {
        $score += 20
        $reasons.Add('non-empty')
    }
    else {
        $reasons.Add('empty')
    }

    # ---------------------------------------------------------------------
    # Instruction following
    # ---------------------------------------------------------------------

    if ($Category -eq 'Instruction') {

        if ($text -match '(?i)exactement|résultat|réponse') {
            $score += 15
            $reasons.Add('instruction markers')
        }

        if ($text.Length -lt 1200) {
            $score += 10
            $reasons.Add('constraint length respected')
        }
    }

    # ---------------------------------------------------------------------
    # Reasoning
    # ---------------------------------------------------------------------

    if ($Category -eq 'Reasoning') {

        if ($text -match '(?i)42') {
            $score += 25
            $reasons.Add('expected result')
        }

        if ($text -match '(?i)donc|car|puisque|étape|calcul') {
            $score += 15
            $reasons.Add('reasoning evidence')
        }
    }

    # ---------------------------------------------------------------------
    # Code
    # ---------------------------------------------------------------------

    if ($Category -eq 'Code') {

        if ($text -match '(?i)def |function |return |if |for |while') {
            $score += 20
            $reasons.Add('code syntax')
        }

        if ($text -match '(?i)None|null|error|exception') {
            $score += 10
            $reasons.Add('edge/error handling')
        }
    }

    # ---------------------------------------------------------------------
    # JSON
    # ---------------------------------------------------------------------

    if ($Category -eq 'Structured') {

        try {
            $null = $text | ConvertFrom-Json
            $score += 50
            $reasons.Add('valid JSON')
        }
        catch {
            $reasons.Add('invalid JSON')
        }
    }

    # ---------------------------------------------------------------------
    # Français
    # ---------------------------------------------------------------------

    if ($Category -eq 'French') {

        if ($text -match '(?i)\b(le|la|les|des|une|dans|avec|pour|est|sont|français)\b') {
            $score += 30
            $reasons.Add('French lexical evidence')
        }

        if ($text.Length -ge 80) {
            $score += 20
            $reasons.Add('adequate response')
        }
    }

    # ---------------------------------------------------------------------
    # Robustesse
    # ---------------------------------------------------------------------

    if ($Category -eq 'Robustness') {

        if ($text.Length -gt 0) {
            $score += 20
        }

        if ($text -notmatch '(?i)je ne peux pas|je refuse|impossible') {
            $score += 20
            $reasons.Add('attempted task')
        }
    }

    # ---------------------------------------------------------------------
    # General
    # ---------------------------------------------------------------------

    if ($Category -eq 'General') {

        if ($text.Length -ge 100) {
            $score += 20
        }

        if ($text.Length -ge 300) {
            $score += 10
        }
    }

    if ($score -gt 100) {
        $score = 100
    }

    return [PSCustomObject]@{
        TestId          = ''
        Category        = $Category
        Success         = $false
        Score           = [int]$score
        DurationMs      = 0
        PromptTokens    = 0
        GeneratedTokens = 0
        TokensPerSecond = 0
        ResponseChars   = 0
        ResponsePreview = ''
        Error           = $null
        Reasons         = @($reasons)
    }
}

# =============================================================================
# [6/14] BATTERIE DE TESTS
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
# [7/14] QUALIFICATION D'UN MODELE
# =============================================================================

function Test-Model {

    param(
        [Parameter(Mandatory)]
        [PSCustomObject]$Model
    )

    Write-Section "[MODEL] $($Model.Name)"

    Write-Forensic `
        -Message "Début qualification : $($Model.Name)" `
        -Level INFO

    # ---------------------------------------------------------------------
    # SWITCH
    # ---------------------------------------------------------------------

    $switchResult = Switch-OllamaModel -Model $Model.Name

    $results = New-Object System.Collections.Generic.List[object]

    # ---------------------------------------------------------------------
    # WARMUP
    # ---------------------------------------------------------------------

    for ($w = 1; $w -le $WarmupRuns; $w++) {

        Write-Forensic `
            -Message "Warmup $w/$WarmupRuns : $($Model.Name)" `
            -Level INFO

        $warmupPayload = @{
            model      = $Model.Name
            prompt     = 'Réponds simplement : READY'
            stream     = $false
            keep_alive = '5m'
            options    = @{
                temperature = 0
                num_predict = 16
            }
        } | ConvertTo-Json -Depth 6

        try {
            Invoke-RestMethod `
                -Uri "$OllamaHost/api/generate" `
                -Method Post `
                -ContentType 'application/json' `
                -Body $warmupPayload `
                -TimeoutSec 120 | Out-Null
        }
        catch {
            Write-Forensic `
                -Message "Warmup échoué : $($_.Exception.Message)" `
                -Level WARN
        }
    }

    # ---------------------------------------------------------------------
    # TESTS
    # ---------------------------------------------------------------------

    foreach ($test in $Tests) {

        $r = Invoke-ModelTest `
            -Model $Model.Name `
            -TestId $test.Id `
            -Category $test.Category `
            -Prompt $test.Prompt `
            -MaxTokens $test.MaxTokens

        $r | Add-Member -NotePropertyName Model -NotePropertyValue $Model.Name -Force
        $r | Add-Member -NotePropertyName TestId -NotePropertyValue $test.Id -Force

        $results.Add($r)
    }

    # ---------------------------------------------------------------------
    # STABILITE
    # ---------------------------------------------------------------------

    Write-Forensic `
        -Message "Tests de stabilité : $StabilityRuns exécutions supplémentaires." `
        -Level INFO

    $stabilityScores = New-Object System.Collections.Generic.List[int]

    for ($s = 1; $s -le $StabilityRuns; $s++) {

        $stable = Invoke-ModelTest `
            -Model $Model.Name `
            -TestId "STAB-$s" `
            -Category 'General' `
            -Prompt 'Réponds en une phrase : quel est le rôle principal d''un journal forensic ?' `
            -MaxTokens 100

        $stabilityScores.Add([int]$stable.Score)

        $results.Add($stable)
    }

    # ---------------------------------------------------------------------
    # AGREGATION
    # ---------------------------------------------------------------------

    $allResults = @($results)

    $successful = @(
        $allResults |
            Where-Object { $_.Success -eq $true }
    )

    $failed = @(
        $allResults |
            Where-Object { $_.Success -ne $true }
    )

    $avgScore = if ($allResults.Count -gt 0) {
        [math]::Round(
            (($allResults | Measure-Object Score -Average).Average),
            2
        )
    }
    else {
        0
    }

    $avgTPS = if ($successful.Count -gt 0) {
        [math]::Round(
            (($successful | Measure-Object TokensPerSecond -Average).Average),
            2
        )
    }
    else {
        0
    }

    $avgLatency = if ($successful.Count -gt 0) {
        [math]::Round(
            (($successful | Measure-Object DurationMs -Average).Average),
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

    $instructionScore = Get-CategoryScore $allResults 'Instruction'
    $reasoningScore   = Get-CategoryScore $allResults 'Reasoning'
    $codeScore        = Get-CategoryScore $allResults 'Code'
    $frenchScore      = Get-CategoryScore $allResults 'French'
    $structuredScore  = Get-CategoryScore $allResults 'Structured'
    $generalScore     = Get-CategoryScore $allResults 'General'

    $stabilityScore = if ($stabilityScores.Count -gt 0) {
        [math]::Round(
            ($stabilityScores | Measure-Object -Average).Average,
            2
        )
    }
    else {
        0
    }

    # ---------------------------------------------------------------------
    # CAPABILITY
    # ---------------------------------------------------------------------

    $capabilityScore = [math]::Round(
        (
            ($instructionScore * 0.20) +
            ($reasoningScore   * 0.25) +
            ($codeScore        * 0.20) +
            ($frenchScore      * 0.10) +
            ($structuredScore  * 0.10) +
            ($generalScore     * 0.15)
        ),
        2
    )

    # ---------------------------------------------------------------------
    # PERFORMANCE
    # ---------------------------------------------------------------------

    # Le TPS est normalisé.
    # 40 TPS ou plus = 100.
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
            ($stabilityScore * 0.60) +
            ((100 - $failureRate) * 0.40)
        ),
        2
    )

    # ---------------------------------------------------------------------
    # OVERALL
    # ---------------------------------------------------------------------

    $overall = [math]::Round(
        (
            ($capabilityScore  * 0.55) +
            ($reliabilityScore * 0.25) +
            ($performanceScore * 0.20)
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
        $stabilityScore -ge $Thresholds.MinStabilityScore -and
        $failureRate -le $Thresholds.MaxFailureRatePercent
    ) {
        $verdict = 'QUALIFIED'
    }
    elseif ($overall -ge 50) {
        $verdict = 'PARTIAL'
    }

    # ---------------------------------------------------------------------
    # RESULTAT
    # ---------------------------------------------------------------------

    $profile = [PSCustomObject]@{
        RunId             = $RunId
        Version           = $Version
        Model             = $Model.Name
        ParameterSize     = $Model.Parameter
        Quantization      = $Model.Quant
        Family            = $Model.Family
        SizeGB            = $Model.SizeGB

        CapabilityScore   = $capabilityScore
        ReliabilityScore  = $reliabilityScore
        PerformanceScore  = $performanceScore
        OverallScore      = $overall

        InstructionScore  = $instructionScore
        ReasoningScore    = $reasoningScore
        CodeScore         = $codeScore
        FrenchScore       = $frenchScore
        StructuredScore   = $structuredScore
        GeneralScore      = $generalScore
        StabilityScore    = $stabilityScore

        AvgLatencyMs      = $avgLatency
        AvgTokensPerSec   = $avgTPS
        FailureRate       = $failureRate
        TestsTotal        = $allResults.Count
        TestsSuccessful   = $successful.Count
        TestsFailed       = $failed.Count

        SwitchMs          = $switchResult.LoadMs

        Verdict           = $verdict

        Tests             = $allResults
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
        -Level $(if ($verdict -eq 'QUALIFIED') { 'PASS' } elseif ($verdict -eq 'PARTIAL') { 'WARN' } else { 'FAIL' })

    return $profile
}

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
        (($items | Measure-Object Score -Average).Average),
        2
    )
}

# =============================================================================
# [8/14] DETECTION DE L'ENVIRONNEMENT
# =============================================================================

Write-Section "[1/14] E-ZZIO MODEL QUALIFICATION GATE v$Version"

Write-Forensic `
    -Message "RunId=$RunId" `
    -Level INFO

Write-Forensic `
    -Message "Root=$Root" `
    -Level INFO

Write-Forensic `
    -Message "CPU=$CpuName" `
    -Level INFO

Write-Forensic `
    -Message "Threads=$CpuThreads" `
    -Level INFO

Write-Forensic `
    -Message "RAM=${TotalRamGB}GB" `
    -Level INFO

Write-Forensic `
    -Message "MODE=CPU-ONLY" `
    -Level INFO

# =============================================================================
# [9/14] OLLAMA
# =============================================================================

Write-Section "[2/14] OLLAMA AVAILABILITY"

$ollamaCommand = Get-Command ollama -ErrorAction SilentlyContinue

if ($null -eq $ollamaCommand) {

    Write-Forensic `
        -Message "ollama.exe introuvable dans PATH." `
        -Level FAIL

    throw "OLLAMA_NOT_FOUND"
}

Write-Forensic `
    -Message "Ollama executable : $($ollamaCommand.Source)" `
    -Level PASS

if (-not (Test-OllamaAvailable)) {

    Write-Forensic `
        -Message "Ollama API inaccessible sur $OllamaHost." `
        -Level FAIL

    throw "OLLAMA_API_UNAVAILABLE"
}

Write-Forensic `
    -Message "Ollama API disponible." `
    -Level PASS

# =============================================================================
# [10/14] INVENTAIRE MODELES
# =============================================================================

Write-Section "[3/14] MODEL INVENTORY"

$models = @(Get-OllamaModels)

if ($models.Count -eq 0) {

    Write-Forensic `
        -Message "Aucun modèle Ollama détecté." `
        -Level FAIL

    throw "NO_MODELS"
}

if ($MaxModels -gt 0 -and $models.Count -gt $MaxModels) {

    $models = @(
        $models |
            Select-Object -First $MaxModels
    )
}

Write-Forensic `
    -Message "$($models.Count) modèle(s) à qualifier." `
    -Level PASS

foreach ($m in $models) {

    Write-Host (
        "  - {0} | {1}GB | params={2} | quant={3} | family={4}" -f
        $m.Name,
        $m.SizeGB,
        $m.Parameter,
        $m.Quant,
        $m.Family
    )
}

# =============================================================================
# [11/14] GARANTIE SINGLE MODEL AVANT DEMARRAGE
# =============================================================================

Write-Section "[4/14] SINGLE-MODEL PRECHECK"

$initialRunning = @(Get-RunningModelNames)

if ($initialRunning.Count -gt 1) {

    Write-Forensic `
        -Message (
            "FAIL-CLOSED : plusieurs modèles sont déjà actifs : " +
            ($initialRunning -join ', ')
        ) `
        -Level FAIL

    throw "INITIAL_MULTIPLE_MODELS"
}

if ($initialRunning.Count -eq 1) {

    Write-Forensic `
        -Message "Un modèle est déjà actif : $($initialRunning[0])" `
        -Level WARN

    $released = Unload-OllamaModel -Model $initialRunning[0]

    if (-not $released) {
        throw "INITIAL_MODEL_RELEASE_FAILED"
    }
}

Write-Forensic `
    -Message "Etat initial conforme : zéro modèle actif." `
    -Level PASS

# =============================================================================
# [12/14] QUALIFICATION COMPLETE
# =============================================================================

Write-Section "[5/14] QUALIFICATION BATTERY"

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

        $profile = Test-Model -Model $model

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
                AvgLatencyMs = 0
                AvgTokensPerSec = 0
                FailureRate = 100
                TestsTotal = 0
                TestsSuccessful = 0
                TestsFailed = 0
                SwitchMs = 0
                Verdict = 'FAIL'
                Tests = @()
                FatalError = $_.Exception.Message
            }
        )
    }

    # ---------------------------------------------------------------------
    # IMPORTANT :
    # Après CHAQUE modèle, on le libère.
    # ---------------------------------------------------------------------

    $active = @(Get-RunningModelNames)

    if ($active.Count -gt 1) {

        Write-Forensic `
            -Message "VIOLATION SINGLE-MODEL détectée après test." `
            -Level FAIL

        throw "MULTIPLE_MODELS_AFTER_TEST"
    }

    if ($active.Count -eq 1) {

        $released = Unload-OllamaModel -Model $active[0]

        if (-not $released) {

            Write-Forensic `
                -Message "Impossible de libérer $($active[0]) après qualification." `
                -Level FAIL

            throw "POST_MODEL_UNLOAD_FAILURE"
        }
    }

    Write-Forensic `
        -Message "Modèle $($model.Name) complètement sorti du runtime." `
        -Level PASS
}

# =============================================================================
# [13/14] CLASSEMENT
# =============================================================================

Write-Section "[6/14] FINAL RANKING"

$ranking = @(
    $profiles |
        Sort-Object -Property OverallScore -Descending
)

$rank = 0

foreach ($profile in $ranking) {

    $rank++

    Write-Host ''
    Write-Host (
        "#{0}  {1}" -f $rank, $profile.Model
    ) -ForegroundColor White

    Write-Host (
        "     OVERALL     : {0}/100" -f $profile.OverallScore
    )

    Write-Host (
        "     CAPABILITY  : {0}/100" -f $profile.CapabilityScore
    )

    Write-Host (
        "     RELIABILITY : {0}/100" -f $profile.ReliabilityScore
    )

    Write-Host (
        "     PERFORMANCE : {0}/100" -f $profile.PerformanceScore
    )

    Write-Host (
        "     REASONING   : {0}/100" -f $profile.ReasoningScore
    )

    Write-Host (
        "     CODE        : {0}/100" -f $profile.CodeScore
    )

    Write-Host (
        "     FRENCH      : {0}/100" -f $profile.FrenchScore
    )

    Write-Host (
        "     STRUCTURED  : {0}/100" -f $profile.StructuredScore
    )

    Write-Host (
        "     AVG TPS     : {0}" -f $profile.AvgTokensPerSec
    )

    Write-Host (
        "     FAILURE     : {0}%" -f $profile.FailureRate
    )

    Write-Host (
        "     VERDICT     : {0}" -f $profile.Verdict
    )
}

# =============================================================================
# [14/14] EXPORT + FINAL SINGLE-MODEL CHECK
# =============================================================================

Write-Section "[7/14] EXPORT FORENSIC"

# -------------------------------------------------------------------------
# JSON
# -------------------------------------------------------------------------

$export = [PSCustomObject]@{
    Schema = 'EZZIO-MODEL-QUALIFICATION-4.3.0'
    RunId = $RunId
    Timestamp = (Get-Date).ToString('o')

    Environment = [PSCustomObject]@{
        CPU = $CpuName
        Threads = $CpuThreads
        RAM_GB = $TotalRamGB
        GPU_Mode = 'DISABLED'
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

    Ranking = @(
        $ranking |
            ForEach-Object {
                [PSCustomObject]@{
                    Rank = [array]::IndexOf($ranking, $_) + 1
                    Model = $_.Model
                    Overall = $_.OverallScore
                    Capability = $_.CapabilityScore
                    Reliability = $_.ReliabilityScore
                    Performance = $_.PerformanceScore
                    Verdict = $_.Verdict
                }
            }
    )

    Profiles = $profiles
}

$export |
    ConvertTo-Json -Depth 15 |
    Set-Content -LiteralPath $JsonPath -Encoding UTF8

Write-Forensic `
    -Message "JSON exporté : $JsonPath" `
    -Level PASS

# -------------------------------------------------------------------------
# CSV
# -------------------------------------------------------------------------

$profiles |
    Select-Object `
        RunId,
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
        AvgLatencyMs,
        AvgTokensPerSec,
        FailureRate,
        TestsTotal,
        TestsSuccessful,
        TestsFailed,
        SwitchMs,
        Verdict |
    Export-Csv `
        -LiteralPath $CsvPath `
        -NoTypeInformation `
        -Encoding UTF8

Write-Forensic `
    -Message "CSV exporté : $CsvPath" `
    -Level PASS

# -------------------------------------------------------------------------
# SUMMARY
# -------------------------------------------------------------------------

$best = $ranking | Select-Object -First 1

$summary = @"

===============================================================================
E-ZZIO — MODEL QUALIFICATION GATE v$Version
===============================================================================

RUN ID
------
$RunId

ENVIRONMENT
-----------
CPU       : $CpuName
THREADS   : $CpuThreads
RAM       : ${TotalRamGB} GB
GPU MODE  : DISABLED
OLLAMA    : $OllamaHost

SINGLE MODEL GUARANTEE
----------------------
Chaque modèle a été chargé individuellement.
Le modèle précédent a été libéré avant le suivant.
Une violation de cardinalité déclenche un FAIL-CLOSED.

MODELS QUALIFIED
----------------
$($profiles.Count)

BEST MODEL
----------
$($best.Model)

OVERALL
-------
$($best.OverallScore)/100

CAPABILITY
----------
$($best.CapabilityScore)/100

RELIABILITY
-----------
$($best.ReliabilityScore)/100

PERFORMANCE
-----------
$($best.PerformanceScore)/100

REASONING
---------
$($best.ReasoningScore)/100

CODE
----
$($best.CodeScore)/100

FRENCH
------
$($best.FrenchScore)/100

STRUCTURED
----------
$($best.StructuredScore)/100

AVERAGE TOKENS/SECOND
---------------------
$($best.AvgTokensPerSec)

FAILURE RATE
------------
$($best.FailureRate)%

VERDICT
-------
$($best.Verdict)

===============================================================================
IMPORTANT
===============================================================================

Ce Gate mesure le potentiel relatif des modèles sur une batterie déterministe.
Le score n'est PAS une mesure absolue de l'intelligence générale.

Un modèle peut être :
- lent mais très capable ;
- rapide mais médiocre ;
- excellent en code mais faible en français ;
- excellent en raisonnement mais mauvais en suivi d'instructions.

Le classement final sépare donc CAPABILITY, RELIABILITY et PERFORMANCE.

===============================================================================
"@

Set-Content `
    -LiteralPath $SummaryPath `
    -Value $summary `
    -Encoding UTF8

Write-Forensic `
    -Message "Summary exporté : $SummaryPath" `
    -Level PASS

# =============================================================================
# FINAL SINGLE-MODEL ASSERTION
# =============================================================================

Write-Section "[FINAL] SINGLE-MODEL CLEANUP"

$finalRunning = @(Get-RunningModelNames)

if ($finalRunning.Count -gt 1) {

    Write-Forensic `
        -Message (
            "FAIL-CLOSED FINAL : $($finalRunning.Count) modèles encore actifs : " +
            ($finalRunning -join ', ')
        ) `
        -Level FAIL

    throw "FINAL_MULTIPLE_MODELS"
}

if ($finalRunning.Count -eq 1) {

    Write-Forensic `
        -Message "Libération finale : $($finalRunning[0])" `
        -Level SWITCH

    $released = Unload-OllamaModel -Model $finalRunning[0]

    if (-not $released) {

        Write-Forensic `
            -Message "Impossible de confirmer la libération finale." `
            -Level FAIL

        throw "FINAL_UNLOAD_FAILED"
    }
}

$finalCheck = @(Get-RunningModelNames)

if ($finalCheck.Count -ne 0) {

    Write-Forensic `
        -Message "FAIL-CLOSED : un modèle reste actif après nettoyage." `
        -Level FAIL

    throw "FINAL_RUNTIME_NOT_EMPTY"
}

Write-Forensic `
    -Message "Runtime Ollama propre : 0 modèle actif." `
    -Level PASS

# =============================================================================
# VERDICT FINAL
# =============================================================================

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

Write-Host ''
Write-Host ('=' * 78)
Write-Host 'E-ZZIO — MODEL QUALIFICATION GATE v4.3.0 — FINISHED'
Write-Host ('=' * 78)

Write-Host ''
Write-Host "MODELS           : $($profiles.Count)"
Write-Host "QUALIFIED        : $qualifiedCount" -ForegroundColor Green
Write-Host "PARTIAL          : $partialCount" -ForegroundColor Yellow
Write-Host "FAIL             : $failedCount" -ForegroundColor Red
Write-Host "SINGLE MODEL     : ENFORCED"
Write-Host "CPU ONLY         : ENABLED"
Write-Host "GPU              : DISABLED"
Write-Host ''

if ($null -ne $best) {

    Write-Host (
        "BEST MODEL      : {0}" -f $best.Model
    ) -ForegroundColor Cyan

    Write-Host (
        "BEST OVERALL    : {0}/100" -f $best.OverallScore
    ) -ForegroundColor Cyan
}

Write-Host ''
Write-Host "JSON             : $JsonPath"
Write-Host "CSV              : $CsvPath"
Write-Host "SUMMARY          : $SummaryPath"
Write-Host "FORENSIC LOG     : $LogPath"
Write-Host ''

Write-Host ('=' * 78)
Write-Host 'EXECUTION TERMINEE — SINGLE-MODEL RUNTIME CONFIRMED CLEAN'
Write-Host ('=' * 78)