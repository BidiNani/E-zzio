#requires -Version 7.4
<#
===============================================================================
 E-ZZIO — MODEL QUALIFICATION GATE
 Version : 4.3.4
 Mode    : CPU-ONLY / FORENSIC / FAIL-CLOSED / SINGLE-ACTIVE-MODEL
 Target  : Windows + PowerShell 7.4+
 Ollama  : http://127.0.0.1:11434
 Hardware profile: Ryzen 9 5900X / 12C / 24T / no GPU dependency

 PRINCIPLES
   - Exactly one Ollama model may remain resident during qualification.
   - Every model is unloaded before the next model is loaded.
   - The gate never assumes optional properties exist.
   - Empty/null model responses are recorded as FAIL, never as exceptions.
   - JSON parsing is strict for JSON-01.
   - No destructive project mutation: only report files are written.
   - A model can fail tests without crashing the entire qualification run.
===============================================================================
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

# -----------------------------------------------------------------------------
# 0. CONFIGURATION
# -----------------------------------------------------------------------------
$Version = '4.3.4'
$OllamaHost = 'http://127.0.0.1:11434'
$OllamaExe = 'G:\Ollama\ollama.exe'

$RequestedThreads = 12
$SwitchAttempts = 8
$SwitchWaitMs = 350
$LoadTimeoutSec = 180
$RequestTimeoutSec = 180
$KeepAlive = '5m'
$WarmupPredict = 24

$MinScore = 70
$RequireAllHardPass = $true
$SingleActiveRequired = $true

$RunId = Get-Date -Format 'yyyyMMdd_HHmmss'
$RunStarted = Get-Date

$ReportRoot = Join-Path $PSScriptRoot 'audit\model_qualification'
New-Item -ItemType Directory -Path $ReportRoot -Force | Out-Null
$JsonReport = Join-Path $ReportRoot "EZZIO_Model_Qualification_Gate_${RunId}.json"
$CsvReport  = Join-Path $ReportRoot "EZZIO_Model_Qualification_Gate_${RunId}.csv"
$LogReport  = Join-Path $ReportRoot "EZZIO_Model_Qualification_Gate_${RunId}.log"

$script:LogLines = [System.Collections.Generic.List[string]]::new()
$script:Results = [System.Collections.Generic.List[object]]::new()
$script:CurrentModel = $null
$script:FailureCount = 0
$script:PassCount = 0
$script:WarnCount = 0

# -----------------------------------------------------------------------------
# LOGGING
# -----------------------------------------------------------------------------
function Write-Log {
    param(
        [ValidateSet('INFO','PASS','WARN','FAIL','TEST','METRIC','SWITCH')]
        [string]$Level,
        [AllowEmptyString()]
        [string]$Message
    )

    $stamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss.fff'
    $line = "[${stamp}] [$Level] $Message"
    Write-Host $line
    [void]$script:LogLines.Add($line)

    switch ($Level) {
        'PASS' { $script:PassCount++ }
        'WARN' { $script:WarnCount++ }
        'FAIL' { $script:FailureCount++ }
    }
}

function Write-Section {
    param(
        [int]$Number,
        [string]$Title
    )
    Write-Host ''
    Write-Host ('=' * 82)
    Write-Host ("[{0}/18] {1}" -f $Number, $Title)
    Write-Host ('=' * 82)
}

function Write-ModelHeader {
    param([string]$Model)
    Write-Host ''
    Write-Host ('=' * 82)
    Write-Host ("[MODEL] {0}" -f $Model)
    Write-Host ('=' * 82)
}

function Convert-ToSafeString {
    param([AllowNull()][object]$Value)
    if ($null -eq $Value) { return '' }
    return [string]$Value
}

function Get-Number {
    param(
        [AllowNull()][object]$Value,
        [double]$Default = 0
    )
    if ($null -eq $Value) { return $Default }
    $n = 0.0
    if ([double]::TryParse(([string]$Value), [Globalization.NumberStyles]::Float, [Globalization.CultureInfo]::InvariantCulture, [ref]$n)) {
        return $n
    }
    return $Default
}

# -----------------------------------------------------------------------------
# HTTP / OLLAMA HELPERS
# -----------------------------------------------------------------------------
function Invoke-Ollama {
    param(
        [Parameter(Mandatory)][ValidateSet('GET','POST','DELETE')]
        [string]$Method,

        [Parameter(Mandatory)]
        [string]$Path,

        [AllowNull()]
        [object]$Body,

        [int]$TimeoutSec = 60
    )

    $uri = "$OllamaHost$Path"
    try {
        $params = @{
            Uri = $uri
            Method = $Method
            TimeoutSec = $TimeoutSec
            ErrorAction = 'Stop'
        }

        if ($null -ne $Body) {
            $params.ContentType = 'application/json; charset=utf-8'
            $params.Body = ($Body | ConvertTo-Json -Depth 20 -Compress)
        }

        $response = Invoke-RestMethod @params
        return $response
    }
    catch {
        throw "Ollama $Method $Path failed: $($_.Exception.Message)"
    }
}

function Test-OllamaApi {
    try {
        $null = Invoke-Ollama -Method GET -Path '/api/version' -TimeoutSec 10
        return $true
    }
    catch {
        return $false
    }
}

function Get-OllamaModels {
    $r = Invoke-Ollama -Method GET -Path '/api/tags' -TimeoutSec 30
    if ($null -eq $r) { return @() }
    if ($null -eq $r.models) { return @() }
    return @($r.models)
}

function Get-OllamaRunningModels {
    try {
        $r = Invoke-Ollama -Method GET -Path '/api/ps' -TimeoutSec 15
        if ($null -eq $r) { return @() }
        if ($null -eq $r.models) { return @() }
        return @($r.models)
    }
    catch {
        Write-Log WARN ("Impossible de lire /api/ps : {0}" -f $_.Exception.Message)
        return @()
    }
}

function Get-RunningModelNames {
    $running = @(Get-OllamaRunningModels)
    $names = [System.Collections.Generic.List[string]]::new()

    foreach ($entry in $running) {
        if ($null -eq $entry) { continue }
        $name = ''
        if ($entry.PSObject.Properties.Name -contains 'name') {
            $name = Convert-ToSafeString $entry.name
        }
        elseif ($entry.PSObject.Properties.Name -contains 'model') {
            $name = Convert-ToSafeString $entry.model
        }
        if (-not [string]::IsNullOrWhiteSpace($name)) {
            [void]$names.Add($name)
        }
    }
    return @($names)
}

function Get-RunningCount {
    return @((Get-OllamaRunningModels)).Count
}

function Get-PropertyValue {
    param(
        [AllowNull()][object]$Object,
        [Parameter(Mandatory)][string]$Name
    )
    if ($null -eq $Object) { return $null }
    if ($Object.PSObject.Properties.Name -contains $Name) {
        return $Object.$Name
    }
    return $null
}

function Invoke-OllamaUnload {
    param([Parameter(Mandatory)][string]$Model)

    $body = @{
        model = $Model
        keep_alive = 0
        prompt = ''
        stream = $false
        options = @{
            num_thread = $RequestedThreads
            num_predict = 1
        }
    }

    try {
        $null = Invoke-Ollama -Method POST -Path '/api/generate' -Body $body -TimeoutSec 45
        return $true
    }
    catch {
        Write-Log WARN ("API unload échoué pour {0} : {1}" -f $Model, $_.Exception.Message)
    }

    if (Test-Path -LiteralPath $OllamaExe) {
        try {
            $p = Start-Process -FilePath $OllamaExe -ArgumentList @('stop', $Model) -NoNewWindow -Wait -PassThru
            if ($p.ExitCode -eq 0) {
                return $true
            }
        }
        catch {
            Write-Log WARN ("CLI stop indisponible pour {0} : {1}" -f $Model, $_.Exception.Message)
        }
    }
    return $false
}

function Wait-OllamaEmpty {
    param([int]$Attempts = $SwitchAttempts)

    for ($i = 1; $i -le $Attempts; $i++) {
        $running = @(Get-OllamaRunningModels)
        if ($running.Count -eq 0) {
            Write-Log PASS ("Runtime EMPTY confirmé à la tentative {0}/{1}." -f $i, $Attempts)
            return $true
        }

        foreach ($entry in $running) {
            $name = Convert-ToSafeString (Get-PropertyValue $entry 'name')
            if ([string]::IsNullOrWhiteSpace($name)) {
                $name = Convert-ToSafeString (Get-PropertyValue $entry 'model')
            }
            if (-not [string]::IsNullOrWhiteSpace($name)) {
                Write-Log SWITCH ("LIBERATION -> {0}" -f $name)
                [void](Invoke-OllamaUnload -Model $name)
            }
        }

        Start-Sleep -Milliseconds $SwitchWaitMs
    }

    $remaining = @(Get-RunningModelNames)
    Write-Log FAIL ("Runtime non vide après {0} tentatives : {1}" -f $Attempts, (($remaining -join ', ')))
    return $false
}

function Confirm-SingleActiveModel {
    param([Parameter(Mandatory)][string]$ExpectedModel)

    $running = @(Get-OllamaRunningModels)
    if ($running.Count -ne 1) {
        Write-Log FAIL ("Single-active violation : attendu=1, observé={0}." -f $running.Count)
        return $false
    }

    $name = Convert-ToSafeString (Get-PropertyValue $running[0] 'name')
    if ([string]::IsNullOrWhiteSpace($name)) {
        $name = Convert-ToSafeString (Get-PropertyValue $running[0] 'model')
    }

    if ($name -ne $ExpectedModel) {
        Write-Log FAIL ("Modèle actif inattendu : attendu={0} observé={1}" -f $ExpectedModel, $name)
        return $false
    }

    Write-Log INFO ("Modèle actif confirmé : {0}" -f $name)
    return $true
}

function Invoke-OllamaGenerate {
    param(
        [Parameter(Mandatory)][string]$Model,
        [Parameter(Mandatory)][AllowEmptyString()][string]$Prompt,
        [int]$NumPredict = 180,
        [double]$Temperature = 0.2,
        [int]$TimeoutSec = $RequestTimeoutSec
    )

    $body = @{
        model = $Model
        prompt = $Prompt
        stream = $false
        keep_alive = $KeepAlive
        options = @{
            num_thread = $RequestedThreads
            num_predict = $NumPredict
            temperature = $Temperature
        }
    }

    $started = Get-Date
    try {
        $raw = Invoke-Ollama -Method POST -Path '/api/generate' -Body $body -TimeoutSec $TimeoutSec
        $elapsed = ((Get-Date) - $started).TotalMilliseconds

        $responseText = ''
        $thinkingText = ''

        if ($null -ne $raw) {
            $responseText = Convert-ToSafeString (Get-PropertyValue $raw 'response')
            $thinkingText = Convert-ToSafeString (Get-PropertyValue $raw 'thinking')
        }

        return [pscustomobject]@{
            Ok          = $true
            Raw         = $raw
            Response    = $responseText
            Thinking    = $thinkingText
            WallMs      = [math]::Round($elapsed, 3)
            EvalMs      = [math]::Round($elapsed, 3)
            Tokens      = [int](Get-Number (Get-PropertyValue $raw 'eval_count') 0)
            PromptEval  = [int](Get-Number (Get-PropertyValue $raw 'prompt_eval_count') 0)
            Error       = ''
        }
    }
    catch {
        $elapsed = ((Get-Date) - $started).TotalMilliseconds
        return [pscustomobject]@{
            Ok          = $false
            Raw         = $null
            Response    = ''
            Thinking    = ''
            WallMs      = [math]::Round($elapsed, 3)
            EvalMs      = 0
            Tokens      = 0
            PromptEval  = 0
            Error       = $_.Exception.Message
        }
    }
}

# -----------------------------------------------------------------------------
# HARDWARE
# -----------------------------------------------------------------------------
function Get-HardwareInfo {
    $cpu = $null
    $os = $null

    try { $cpu = Get-CimInstance Win32_Processor | Select-Object -First 1 } catch {}
    try { $os = Get-CimInstance Win32_OperatingSystem } catch {}

    $cpuName = 'UNKNOWN'
    $cores = 0
    $threads = 0
    $totalRamGb = 0
    $freeRamGb = 0

    if ($null -ne $cpu) {
        if ($cpu.PSObject.Properties.Name -contains 'Name') { $cpuName = Convert-ToSafeString $cpu.Name }
        if ($cpu.PSObject.Properties.Name -contains 'NumberOfCores') { $cores = [int]$cpu.NumberOfCores }
        if ($cpu.PSObject.Properties.Name -contains 'NumberOfLogicalProcessors') { $threads = [int]$cpu.NumberOfLogicalProcessors }
    }
    if ($null -ne $os) {
        if ($os.PSObject.Properties.Name -contains 'TotalVisibleMemorySize') {
            $totalRamGb = [math]::Round(([double]$os.TotalVisibleMemorySize / 1MB), 2)
        }
        if ($os.PSObject.Properties.Name -contains 'FreePhysicalMemory') {
            $freeRamGb = [math]::Round(([double]$os.FreePhysicalMemory / 1MB), 2)
        }
    }

    if ($threads -le 0) { $threads = [Environment]::ProcessorCount }
    if ($cores -le 0) { $cores = [math]::Max(1, [math]::Floor($threads / 2)) }

    return [pscustomobject]@{
        CpuName = $cpuName
        Cores = $cores
        Threads = $threads
        TotalRamGb = $totalRamGb
        FreeRamGb = $freeRamGb
        RequestedThreads = [math]::Min($RequestedThreads, $threads)
    }
}

$Hardware = Get-HardwareInfo
$RequestedThreads = $Hardware.RequestedThreads

# -----------------------------------------------------------------------------
# MODEL INVENTORY
# -----------------------------------------------------------------------------
function Get-ModelInventory {
    $models = @(Get-OllamaModels)
    $out = [System.Collections.Generic.List[object]]::new()

    foreach ($m in $models) {
        $name = Convert-ToSafeString (Get-PropertyValue $m 'name')
        if ([string]::IsNullOrWhiteSpace($name)) { continue }

        $sizeBytes = [double](Get-Number (Get-PropertyValue $m 'size') 0)
        $details = Get-PropertyValue $m 'details'

        $param = ''
        $quant = ''
        $family = ''
        if ($null -ne $details) {
            $param = Convert-ToSafeString (Get-PropertyValue $details 'parameter_size')
            $quant = Convert-ToSafeString (Get-PropertyValue $details 'quantization_level')
            $family = Convert-ToSafeString (Get-PropertyValue $details 'family')
        }

        [void]$out.Add([pscustomobject]@{
            Name = $name
            SizeGb = [math]::Round($sizeBytes / 1GB, 2)
            ParameterSize = $param
            Quantization = $quant
            Family = $family
        })
    }
    return @($out)
}

# -----------------------------------------------------------------------------
# QUALIFICATION TESTS
# -----------------------------------------------------------------------------
$Tests = @(
    [pscustomobject]@{
        Id='GEN-01'; Category='General'; NumPredict=300; Temperature=0.2
        Prompt='Réponds en français en 3 phrases maximum. Explique simplement ce qu''est une base de données relationnelle et donne un exemple concret.'
    },
    [pscustomobject]@{
        Id='INS-01'; Category='Instruction'; NumPredict=80; Temperature=0.1
        Prompt='Effectue exactement ces deux actions dans cet ordre : 1) écris le mot ALPHA ; 2) écris le mot BETA. Ne produis aucun autre mot.'
    },
    [pscustomobject]@{
        Id='REASON-01'; Category='Reasoning'; NumPredict=180; Temperature=0.1
        Prompt='Résous ce problème : Alice a 3 pommes. Elle en donne 1 à Bob puis achète 4 pommes. Combien lui en reste-t-il ? Donne le calcul puis la réponse.'
    },
    [pscustomobject]@{
        Id='REASON-02'; Category='Reasoning'; NumPredict=220; Temperature=0.1
        Prompt='Un fichier contient 120 lignes. Une première opération en supprime 15 %, puis une seconde supprime 10 lignes. Combien reste-t-il de lignes ? Montre les étapes de calcul et termine par une réponse numérique.'
    },
    [pscustomobject]@{
        Id='CODE-01'; Category='Code'; NumPredict=180; Temperature=0.1
        Prompt='Écris uniquement une fonction Python nommée add(a, b) qui retourne la somme de a et b. Utilise un bloc de code Python.'
    },
    [pscustomobject]@{
        Id='CODE-02'; Category='Code'; NumPredict=220; Temperature=0.1
        Prompt='Écris un petit script PowerShell qui affiche Bonjour puis le nombre 42. Utilise un bloc de code PowerShell.'
    },
    [pscustomobject]@{
        Id='JSON-01'; Category='Structured'; NumPredict=120; Temperature=0.0
        Prompt='Retourne uniquement un objet JSON valide, sans markdown ni commentaire, avec exactement ces champs : {"name":"EZZIO","ok":true,"count":42}.'
    },
    [pscustomobject]@{
        Id='FR-01'; Category='French'; NumPredict=250; Temperature=0.2
        Prompt='Réponds uniquement en français. Explique en 4 phrases maximum la différence entre un processus et un thread.'
    },
    [pscustomobject]@{
        Id='ROB-01'; Category='Robustness'; NumPredict=180; Temperature=0.1
        Prompt='Réponds brièvement et honnêtement. Si une information est inconnue, dis que tu ne sais pas. Question : quelle est la capitale de la France ?'
    }
)

function Get-CombinedResponseText {
    param([Parameter(Mandatory)][object]$Result)

    $response = Convert-ToSafeString (Get-PropertyValue $Result 'Response')
    $thinking = Convert-ToSafeString (Get-PropertyValue $Result 'Thinking')

    if (-not [string]::IsNullOrWhiteSpace($response)) {
        return $response.Trim()
    }
    if (-not [string]::IsNullOrWhiteSpace($thinking)) {
        return $thinking.Trim()
    }
    return ''
}

function Test-General {
    param([AllowEmptyString()][string]$Text)
    if ([string]::IsNullOrWhiteSpace($Text)) { return $false }
    return ($Text.Length -ge 20)
}

function Test-Instruction {
    param([AllowEmptyString()][string]$Text)
    if ([string]::IsNullOrWhiteSpace($Text)) { return $false }
    $u = $Text.ToUpperInvariant()
    return ($u -match 'ALPHA' -and $u -match 'BETA')
}

function Test-Reasoning01 {
    param([AllowEmptyString()][string]$Text)
    if ([string]::IsNullOrWhiteSpace($Text)) { return $false }
    $n = [regex]::Match($Text, '(?<!\d)(6)(?!\d)')
    return ($null -ne $n -and $n.Success)
}

function Test-Reasoning02 {
    param([AllowEmptyString()][string]$Text)
    if ([string]::IsNullOrWhiteSpace($Text)) { return $false }
    $n = [regex]::Match($Text, '(?<!\d)(92)(?!\d)')
    $hasStep = $Text -match '(?i)(donc|car|puisque|étape|calcul|d''abord|ensuite|première|seconde)'
    return ($n.Success -and $hasStep)
}

function Test-CodePython {
    param([AllowEmptyString()][string]$Text)
    if ([string]::IsNullOrWhiteSpace($Text)) { return $false }
    return ($Text -match '(?i)def\s+add\s*\(' -and $Text -match '(?i)return\s+a\s*\+\s*b')
}

function Test-CodePowerShell {
    param([AllowEmptyString()][string]$Text)
    if ([string]::IsNullOrWhiteSpace($Text)) { return $false }
    return ($Text -match '(?i)Write-Host' -and $Text -match '42')
}

function Test-JsonStrict {
    param([AllowEmptyString()][string]$Text)
    if ([string]::IsNullOrWhiteSpace($Text)) { return $false }

    $candidate = $Text.Trim()
    if ($candidate.StartsWith('```')) {
        $candidate = [regex]::Replace($candidate, '^```(?:json)?\s*', '', [Text.RegularExpressions.RegexOptions]::IgnoreCase)
        $candidate = [regex]::Replace($candidate, '\s*```$', '')
        $candidate = $candidate.Trim()
    }

    try {
        $obj = $candidate | ConvertFrom-Json -ErrorAction Stop
        $props = @($obj.PSObject.Properties.Name)
        if ($props.Count -ne 3) { return $false }
        if ($props -notcontains 'name') { return $false }
        if ($props -notcontains 'ok') { return $false }
        if ($props -notcontains 'count') { return $false }
        if ([string]$obj.name -ne 'EZZIO') { return $false }
        if ([bool]$obj.ok -ne $true) { return $false }
        if ([int]$obj.count -ne 42) { return $false }
        return $true
    }
    catch {
        return $false
    }
}

function Test-French {
    param([AllowEmptyString()][string]$Text)
    if ([string]::IsNullOrWhiteSpace($Text)) { return $false }
    $latin = ([regex]::Matches($Text, '[A-Za-zÀ-ÿ]').Count)
    if ($latin -lt 20) { return $false }
    $frWords = @(' le ',' la ',' les ',' un ',' une ',' des ',' et ',' est ',' pour ',' entre ','processus','thread')
    $hits = 0
    $lower = ' ' + $Text.ToLowerInvariant() + ' '
    foreach ($w in $frWords) {
        if ($lower.Contains($w)) { $hits++ }
    }
    return ($hits -ge 2)
}

function Test-Robustness {
    param([AllowEmptyString()][string]$Text)
    if ([string]::IsNullOrWhiteSpace($Text)) { return $false }
    return ($Text -match '(?i)Paris')
}

function Get-TestScore {
    param([bool]$HardPass)
    if ($HardPass) { return 100 }
    return 0
}

function Get-TestEvaluator {
    param([string]$Id)
    switch ($Id) {
        'GEN-01'    { return { param($t) Test-General $t } }
        'INS-01'    { return { param($t) Test-Instruction $t } }
        'REASON-01' { return { param($t) Test-Reasoning01 $t } }
        'REASON-02' { return { param($t) Test-Reasoning02 $t } }
        'CODE-01'   { return { param($t) Test-CodePython $t } }
        'CODE-02'   { return { param($t) Test-CodePowerShell $t } }
        'JSON-01'   { return { param($t) Test-JsonStrict $t } }
        'FR-01'     { return { param($t) Test-French $t } }
        'ROB-01'    { return { param($t) Test-Robustness $t } }
        default     { return { param($t) $false } }
    }
}

function Invoke-QualificationTest {
    param(
        [Parameter(Mandatory)][string]$Model,
        [Parameter(Mandatory)][object]$Test
    )

    Write-Log TEST ("TEST {0} | {1}" -f $Test.Id, $Test.Category)

    $activeOk = Confirm-SingleActiveModel -ExpectedModel $Model
    if (-not $activeOk) {
        return [pscustomobject]@{
            Model=$Model; TestId=$Test.Id; Category=$Test.Category
            Score=0; HardPass=$false; Response=''; Thinking=''
            WallMs=0; EvalMs=0; Tokens=0; PromptEval=0
            Error='ACTIVE_MODEL_CONTRACT_FAILED'; EmptyResponse=$true
        }
    }

    $r = Invoke-OllamaGenerate -Model $Model -Prompt $Test.Prompt `
        -NumPredict $Test.NumPredict -Temperature $Test.Temperature

    $text = Get-CombinedResponseText -Result $r
    $empty = [string]::IsNullOrWhiteSpace($text)

    if (-not $r.Ok) {
        Write-Log FAIL ("TEST {0} FAIL : {1}" -f $Test.Id, $r.Error)
        $hardPass = $false
    }
    elseif ($empty) {
        Write-Log WARN ("TEST {0} : réponse vide. Echec enregistré sans crash du Gate." -f $Test.Id)
        $hardPass = $false
    }
    else {
        $evaluator = Get-TestEvaluator -Id $Test.Id
        try {
            $hardPass = [bool](& $evaluator $text)
        }
        catch {
            $hardPass = $false
            Write-Log FAIL ("TEST {0} evaluator error : {1}" -f $Test.Id, $_.Exception.Message)
        }

        if ($hardPass) {
            Write-Log PASS ("TEST {0} PASS | longueur réponse={1}" -f $Test.Id, $text.Length)
        }
        else {
            Write-Log WARN ("TEST {0} FAIL | réponse présente mais critère non satisfait." -f $Test.Id)
        }
    }

    $score = Get-TestScore -HardPass $hardPass
    $tps = 0.0
    if ($r.EvalMs -gt 0 -and $r.Tokens -gt 0) {
        $tps = [math]::Round(($r.Tokens / $r.EvalMs) * 1000, 3)
    }

    Write-Log METRIC ("RESULT {0} | Score={1} | HardPass={2} | Wall={3}ms | Eval={4}ms | Tokens={5} | TPS={6}" -f `
        $Test.Id, $score, $hardPass, $r.WallMs, $r.EvalMs, $r.Tokens, $tps)

    return [pscustomobject]@{
        Model=$Model
        TestId=$Test.Id
        Category=$Test.Category
        Score=$score
        HardPass=$hardPass
        Response=$text
        Thinking=(Convert-ToSafeString $r.Thinking)
        WallMs=$r.WallMs
        EvalMs=$r.EvalMs
        Tokens=$r.Tokens
        PromptEval=$r.PromptEval
        Error=(Convert-ToSafeString $r.Error)
        EmptyResponse=$empty
    }
}

# -----------------------------------------------------------------------------
# SWITCH ENGINE
# -----------------------------------------------------------------------------
function Switch-ToModel {
    param([Parameter(Mandatory)][string]$Model)

    Write-Log SWITCH ("========== SWITCH -> {0} ==========" -f $Model)
    Write-Log SWITCH 'NETTOYAGE GLOBAL DU RUNTIME OLLAMA'

    if (-not (Wait-OllamaEmpty)) {
        return $false
    }

    $started = Get-Date
    $body = @{
        model = $Model
        prompt = 'Réponds uniquement par READY.'
        stream = $false
        keep_alive = $KeepAlive
        options = @{
            num_thread = $RequestedThreads
            num_predict = $WarmupPredict
            temperature = 0.0
        }
    }

    try {
        $r = Invoke-Ollama -Method POST -Path '/api/generate' -Body $body -TimeoutSec $LoadTimeoutSec
        $loadMs = ((Get-Date) - $started).TotalMilliseconds

        Start-Sleep -Milliseconds $SwitchWaitMs

        $running = @(Get-OllamaRunningModels)
        if ($running.Count -ne 1) {
            Write-Log FAIL ("SWITCH FAIL | Active={0}, attendu=1." -f $running.Count)
            return $false
        }

        $activeName = Convert-ToSafeString (Get-PropertyValue $running[0] 'name')
        if ([string]::IsNullOrWhiteSpace($activeName)) {
            $activeName = Convert-ToSafeString (Get-PropertyValue $running[0] 'model')
        }

        if ($activeName -ne $Model) {
            Write-Log FAIL ("SWITCH FAIL | attendu={0} observé={1}" -f $Model, $activeName)
            return $false
        }

        Write-Log PASS ("SWITCH OK | Model={0} | Load={1} ms | Wall={2} ms | Active={3}" -f `
            $Model, [math]::Round($loadMs,3), [math]::Round($loadMs,3), $running.Count)
        return $true
    }
    catch {
        Write-Log FAIL ("SWITCH FAIL | Model={0} | {1}" -f $Model, $_.Exception.Message)
        return $false
    }
}

function Release-Model {
    param([Parameter(Mandatory)][string]$Model)

    Write-Log SWITCH ("LIBERATION -> {0}" -f $Model)
    [void](Invoke-OllamaUnload -Model $Model)
    [void](Wait-OllamaEmpty)

    $remaining = @(Get-RunningModelNames)
    if ($remaining.Count -eq 0) {
        Write-Log PASS ("Modèle {0} complètement sorti du runtime." -f $Model)
        $script:CurrentModel = $null
        return $true
    }

    Write-Log FAIL ("Modèle encore résident après libération : {0}" -f ($remaining -join ', '))
    return $false
}

# -----------------------------------------------------------------------------
# MAIN
# -----------------------------------------------------------------------------
try {
    Write-Section 0 "E-ZZIO MODEL QUALIFICATION GATE v$Version"

    Write-Host ''
    Write-Host ("CPU NAME              : {0}" -f $Hardware.CpuName)
    Write-Host ("CPU CORES             : {0}" -f $Hardware.Cores)
    Write-Host ("CPU THREADS DETECTED  : {0}" -f $Hardware.Threads)
    Write-Host ("CPU THREADS REQUESTED : {0}" -f $RequestedThreads)
    Write-Host ("TOTAL RAM             : {0} GB" -f $Hardware.TotalRamGb)
    Write-Host ("AVAILABLE RAM         : {0} GB" -f $Hardware.FreeRamGb)
    Write-Host ("OLLAMA HOST           : {0}" -f $OllamaHost)
    Write-Host ("RUN ID                : {0}" -f $RunId)

    Write-Log INFO ("Version={0} | RunId={1}" -f $Version, $RunId)
    Write-Log INFO ("CPU={0} | Cores={1} | Threads={2} | RAM={3}GB" -f `
        $Hardware.CpuName, $Hardware.Cores, $Hardware.Threads, $Hardware.TotalRamGb)
    Write-Log INFO ("Benchmark threads requested={0}" -f $RequestedThreads)

    Write-Section 1 'OLLAMA AVAILABILITY'

    if (-not (Test-Path -LiteralPath $OllamaExe)) {
        Write-Log WARN ("Ollama executable introuvable à {0}; poursuite via API." -f $OllamaExe)
    }
    else {
        Write-Log PASS ("Ollama executable : {0}" -f $OllamaExe)
    }

    if (-not (Test-OllamaApi)) {
        throw 'Ollama API indisponible.'
    }
    Write-Log PASS 'Ollama API disponible.'

    Write-Section 2 'MODEL INVENTORY'
    $inventory = @(Get-ModelInventory)

    if ($inventory.Count -eq 0) {
        throw 'Aucun modèle Ollama détecté.'
    }

    Write-Log PASS ("{0} modèle(s) à qualifier." -f $inventory.Count)
    foreach ($m in $inventory) {
        Write-Host ("  - {0} | {1} GB | params={2} | quant={3} | family={4}" -f `
            $m.Name, $m.SizeGb, $m.ParameterSize, $m.Quantization, $m.Family)
    }

    Write-Section 3 'INITIAL RUNTIME CLEANUP'
    $initialRunning = @(Get-OllamaRunningModels)
    Write-Log INFO ("Etat initial : {0} modèle(s) actif(s)." -f $initialRunning.Count)

    if ($initialRunning.Count -gt 0) {
        Write-Host ''
        Write-Host 'Modèle(s) actuellement actif(s) :'
        foreach ($n in @(Get-RunningModelNames)) {
            Write-Host ("  * {0}" -f $n)
        }
    }

    if (-not (Wait-OllamaEmpty)) {
        throw 'Impossible d''obtenir un runtime Ollama vide avant qualification.'
    }
    Write-Log PASS 'PRECHECK OK : 0 modèle actif.'

    Write-Section 4 'QUALIFICATION BATTERY'

    $modelIndex = 0
    foreach ($model in $inventory) {
        $modelIndex++
        $modelName = $model.Name

        Write-Host ''
        Write-Host (">>> MODELE {0}/{1} : {2}" -f $modelIndex, $inventory.Count, $modelName)
        Write-ModelHeader $modelName
        Write-Log INFO ("Début qualification : {0}" -f $modelName)

        $modelResults = [System.Collections.Generic.List[object]]::new()
        $switchOk = $false

        try {
            $switchOk = Switch-ToModel -Model $modelName
            if (-not $switchOk) {
                Write-Log FAIL ("Qualification interrompue pour {0} : SWITCH contract failure." -f $modelName)
            }
            else {
                $script:CurrentModel = $modelName

                Write-Log INFO ("Warmup 1/1 : {0}" -f $modelName)

                foreach ($test in $Tests) {
                    try {
                        $tr = Invoke-QualificationTest -Model $modelName -Test $test
                        [void]$modelResults.Add($tr)
                        [void]$script:Results.Add($tr)
                    }
                    catch {
                        Write-Log FAIL ("TEST {0} exception isolée : {1}" -f $test.Id, $_.Exception.Message)
                        $tr = [pscustomobject]@{
                            Model=$modelName; TestId=$test.Id; Category=$test.Category
                            Score=0; HardPass=$false; Response=''; Thinking=''
                            WallMs=0; EvalMs=0; Tokens=0; PromptEval=0
                            Error=$_.Exception.Message; EmptyResponse=$true
                        }
                        [void]$modelResults.Add($tr)
                        [void]$script:Results.Add($tr)
                    }
                }
            }
        }
        catch {
            Write-Log FAIL ("Qualification interrompue pour {0} : {1}" -f $modelName, $_.Exception.Message)
        }
        finally {
            if ($switchOk) {
                [void](Release-Model -Model $modelName)
            }
            else {
                # Defensive cleanup even when load failed halfway.
                [void](Wait-OllamaEmpty)
            }
        }

        $count = $modelResults.Count
        $passed = @($modelResults | Where-Object { $_.HardPass -eq $true }).Count
        $score = if ($count -gt 0) {
            [math]::Round((($modelResults | Measure-Object -Property Score -Average).Average), 2)
        } else { 0 }

        $hardPassAll = ($count -eq $Tests.Count -and $passed -eq $Tests.Count)
        $qualified = ($switchOk -and $score -ge $MinScore -and ((-not $RequireAllHardPass) -or $hardPassAll))

        $summary = [pscustomobject]@{
            Model=$modelName
            SizeGb=$model.SizeGb
            ParameterSize=$model.ParameterSize
            Quantization=$model.Quantization
            Family=$model.Family
            SwitchOk=$switchOk
            Tests=$count
            Passed=$passed
            Failed=($count - $passed)
            Score=$score
            HardPassAll=$hardPassAll
            Qualified=$qualified
            RunId=$RunId
        }

        Write-Host ''
        Write-Host ('-' * 82)
        Write-Host ("MODEL SUMMARY : {0}" -f $modelName)
        Write-Host ("  Switch       : {0}" -f $switchOk)
        Write-Host ("  Tests        : {0}/{1}" -f $passed, $Tests.Count)
        Write-Host ("  Score        : {0}/100" -f $score)
        Write-Host ("  HardPassAll  : {0}" -f $hardPassAll)
        Write-Host ("  QUALIFIED    : {0}" -f $qualified)
        Write-Host ('-' * 82)

        $script:Results.Add($summary) | Out-Null
    }

    Write-Section 5 'PER-MODEL SCOREBOARD'

    $summaries = @($script:Results | Where-Object { $_.PSObject.Properties.Name -contains 'Qualified' })
    foreach ($s in $summaries) {
        $verdict = if ($s.Qualified) { 'QUALIFIED' } else { 'REJECTED' }
        Write-Host ("{0,-48} | Score={1,6} | Tests={2,2}/{3,2} | {4}" -f `
            $s.Model, $s.Score, $s.Passed, $s.Tests, $verdict)
    }

    Write-Section 6 'GLOBAL CONTRACT CHECKS'
    $finalRunning = @(Get-OllamaRunningModels)
    if ($finalRunning.Count -eq 0) {
        Write-Log PASS 'Runtime final EMPTY.'
    }
    else {
        Write-Log FAIL ("Runtime final non vide : {0}" -f (($finalRunning | ForEach-Object {
            $n = Convert-ToSafeString (Get-PropertyValue $_ 'name')
            if ([string]::IsNullOrWhiteSpace($n)) { $n = Convert-ToSafeString (Get-PropertyValue $_ 'model') }
            $n
        }) -join ', '))
    }

    Write-Section 7 'RESULT EXPORT'
    $finished = Get-Date
    $durationSec = [math]::Round(($finished - $RunStarted).TotalSeconds, 3)

    $qualifiedModels = @($summaries | Where-Object { $_.Qualified })
    $rejectedModels = @($summaries | Where-Object { -not $_.Qualified })

    $payload = [pscustomobject]@{
        Schema='EZZIO.ModelQualificationGate'
        Version=$Version
        RunId=$RunId
        StartedAt=$RunStarted.ToString('o')
        FinishedAt=$finished.ToString('o')
        DurationSec=$durationSec
        Host=$OllamaHost
        Cpu=$Hardware
        RequestedThreads=$RequestedThreads
        SingleActiveRequired=$SingleActiveRequired
        MinimumScore=$MinScore
        RequireAllHardPass=$RequireAllHardPass
        Inventory=$inventory
        Tests=$Tests
        Results=@($script:Results)
        QualifiedModels=@($qualifiedModels)
        RejectedModels=@($rejectedModels)
        FinalRuntimeCount=$finalRunning.Count
    }

    $payload | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $JsonReport -Encoding UTF8

    $flat = @($script:Results | ForEach-Object {
        [pscustomobject]@{
            RunId=$RunId
            Model=Convert-ToSafeString (Get-PropertyValue $_ 'Model')
            TestId=Convert-ToSafeString (Get-PropertyValue $_ 'TestId')
            Category=Convert-ToSafeString (Get-PropertyValue $_ 'Category')
            Score=Convert-ToSafeString (Get-PropertyValue $_ 'Score')
            HardPass=Convert-ToSafeString (Get-PropertyValue $_ 'HardPass')
            WallMs=Convert-ToSafeString (Get-PropertyValue $_ 'WallMs')
            EvalMs=Convert-ToSafeString (Get-PropertyValue $_ 'EvalMs')
            Tokens=Convert-ToSafeString (Get-PropertyValue $_ 'Tokens')
            Error=Convert-ToSafeString (Get-PropertyValue $_ 'Error')
            Qualified=Convert-ToSafeString (Get-PropertyValue $_ 'Qualified')
        }
    })

    if ($flat.Count -gt 0) {
        $flat | Export-Csv -LiteralPath $CsvReport -NoTypeInformation -Encoding UTF8
    }
    else {
        'RunId,Model,TestId,Category,Score,HardPass,WallMs,EvalMs,Tokens,Error,Qualified' |
            Set-Content -LiteralPath $CsvReport -Encoding UTF8
    }

    $script:LogLines | Set-Content -LiteralPath $LogReport -Encoding UTF8

    Write-Log PASS ("JSON report : {0}" -f $JsonReport)
    Write-Log PASS ("CSV report  : {0}" -f $CsvReport)
    Write-Log PASS ("LOG report  : {0}" -f $LogReport)

    Write-Section 8 'FINAL VERDICT'

    $globalOk = ($summaries.Count -eq $inventory.Count -and $finalRunning.Count -eq 0)
    if ($qualifiedModels.Count -gt 0) {
        Write-Host ("QUALIFIED MODELS : {0}" -f $qualifiedModels.Count)
        foreach ($q in $qualifiedModels) {
            Write-Host ("  [QUALIFIED] {0} | Score={1}" -f $q.Model, $q.Score)
        }
    }
    else {
        Write-Host 'QUALIFIED MODELS : 0'
    }

    Write-Host ("REJECTED MODELS  : {0}" -f $rejectedModels.Count)
    Write-Host ("GLOBAL RUNTIME   : {0} active at end" -f $finalRunning.Count)
    Write-Host ("DURATION         : {0} sec" -f $durationSec)

    if ($globalOk) {
        Write-Log PASS 'GLOBAL FORENSIC CONTRACT : PASS'
    }
    else {
        Write-Log FAIL 'GLOBAL FORENSIC CONTRACT : FAIL'
    }

    Write-Section 9 'EXECUTION SUMMARY'
    Write-Host ("Version       : {0}" -f $Version)
    Write-Host ("RunId         : {0}" -f $RunId)
    Write-Host ("Models        : {0}" -f $inventory.Count)
    Write-Host ("Qualified     : {0}" -f $qualifiedModels.Count)
    Write-Host ("Rejected      : {0}" -f $rejectedModels.Count)
    Write-Host ("PASS logs     : {0}" -f $script:PassCount)
    Write-Host ("WARN logs     : {0}" -f $script:WarnCount)
    Write-Host ("FAIL logs     : {0}" -f $script:FailureCount)

    Write-Host ''
    Write-Host ('=' * 82)
    if ($globalOk -and $qualifiedModels.Count -gt 0) {
        Write-Host 'VERDICT : QUALIFICATION COMPLETE — AU MOINS UN MODELE QUALIFIE'
    }
    elseif ($globalOk) {
        Write-Host 'VERDICT : QUALIFICATION COMPLETE — AUCUN MODELE QUALIFIE'
    }
    else {
        Write-Host 'VERDICT : FAIL-CLOSED — CONTRAT GLOBAL NON SATISFAIT'
    }
    Write-Host ('=' * 82)
    Write-Host 'EXECUTION TERMINEE.'
}
catch {
    Write-Log FAIL ("FATAL : {0}" -f $_.Exception.Message)

    try {
        [void](Wait-OllamaEmpty)
        $script:LogLines | Set-Content -LiteralPath $LogReport -Encoding UTF8
    }
    catch {}

    Write-Host ''
    Write-Host ('=' * 82)
    Write-Host 'VERDICT : FAIL-CLOSED — EXECUTION ABORTED'
    Write-Host ('=' * 82)
    exit 2
}

exit 0
