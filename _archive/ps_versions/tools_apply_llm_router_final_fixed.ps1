#requires -Version 7.0

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$EzzioHome    = 'G:\AI\E-zzio'
$SecretsFile  = Join-Path $EzzioHome 'secrets\.env'
$HermesHome   = 'G:\Hermes'
$HermesConfig = Join-Path $HermesHome 'config.yaml'
$HermesExe    = Join-Path $HermesHome 'bin\hermes.exe'
$RegistryDir  = Join-Path $EzzioHome 'state\audit\current\capability_registry'
$ToolsDir     = Join-Path $EzzioHome 'tools'
$RegistryPath = Join-Path $RegistryDir 'llm_capability_registry.json'
$RefreshPath  = Join-Path $ToolsDir 'refresh_llm_capability_registry.ps1'
$Stamp        = Get-Date -Format 'yyyyMMdd-HHmmss'
$HermesBackup = "$HermesConfig.pre-final-router-$Stamp.bak"

function Fail([string]$Message) {
    throw $Message
}

function Assert-Path([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) {
        Fail "Ressource absente : $Path"
    }
}

function Get-GeminiKeys([string]$Path) {
    $items = @()
    foreach ($line in Get-Content -LiteralPath $Path) {
        if ($line -match '^\s*([^#=]+)\s*=(.*)$') {
            $name  = $Matches[1].Trim()
            $value = $Matches[2].Trim()
            $isGemini = (($name -match '^GEMINI_API_KEY_\d+$') -or ($name -eq 'GEMINI_API6'))
            if ($isGemini -and -not [string]::IsNullOrWhiteSpace($value)) {
                $items += [PSCustomObject]@{ Name = $name; Value = $value }
            }
        }
    }
    @($items | Sort-Object Name -Unique)
}

function Discover-Gemini([string]$KeyName, [string]$KeyValue) {
    $resp = Invoke-RestMethod `
        -Uri 'https://generativelanguage.googleapis.com/v1beta/models?pageSize=1000' `
        -Headers @{ 'x-goog-api-key' = $KeyValue } `
        -Method Get `
        -TimeoutSec 30

    $models = @($resp.models)
    if ($models.Count -eq 0) { Fail "models.list=0 pour $KeyName" }

    $names = @(
        $models |
        ForEach-Object { ([string]$_.name -replace '^models/','') } |
        Where-Object { $_ } |
        Sort-Object -Unique
    )

    $generative = @(
        $models | Where-Object { @($_.supportedGenerationMethods) -contains 'generateContent' }
    )

    [PSCustomObject]@{
        Models = $models
        Names = $names
        Count = $models.Count
        Generative = $generative.Count
    }
}

function Pick-CommonModel([string[]]$Candidates, [string[]]$CommonModels, [string]$Role) {
    foreach ($candidate in $Candidates) {
        if ($candidate -in $CommonModels) { return $candidate }
    }
    Fail "Aucun modèle commun disponible pour $Role"
}

function Find-TopLevel([System.Collections.Generic.List[string]]$Lines, [string]$Name) {
    for ($i = 0; $i -lt $Lines.Count; $i++) {
        if ($Lines[$i] -match ('^' + [regex]::Escape($Name) + ':\s*$')) { return $i }
    }
    return -1
}

function Find-Child([System.Collections.Generic.List[string]]$Lines, [int]$Parent, [string]$Name) {
    for ($i = $Parent + 1; $i -lt $Lines.Count; $i++) {
        if ($Lines[$i] -match '^[^\s#][^:]*:\s*$') { break }
        if ($Lines[$i] -match ('^  ' + [regex]::Escape($Name) + ':\s*$')) { return $i }
    }
    return -1
}

function Get-BlockEnd([System.Collections.Generic.List[string]]$Lines, [int]$Start) {
    for ($i = $Start + 1; $i -lt $Lines.Count; $i++) {
        if ($Lines[$i] -match '^  [A-Za-z0-9_-]+:\s*$') { return $i }
        if ($Lines[$i] -match '^[^\s#][^:]*:\s*$') { return $i }
    }
    return $Lines.Count
}

function Replace-RequiredField(
    [System.Collections.Generic.List[string]]$Lines,
    [int]$Start,
    [int]$End,
    [string]$Field,
    [string]$Value,
    [string]$Indent
) {
    for ($i = $Start + 1; $i -lt $End; $i++) {
        if ($Lines[$i] -match ('^' + [regex]::Escape($Indent) + [regex]::Escape($Field) + ':\s*')) {
            $Lines[$i] = "$Indent$Field`: $Value"
            return
        }
    }
    Fail "Champ requis absent : $Field"
}

function Test-HermesConfig([string]$ExpectedPrimary, [System.Collections.IDictionary]$Routes) {
    $model = & $HermesExe config get model --json 2>&1 | ConvertFrom-Json
    if ($model.default -ne $ExpectedPrimary) { Fail "Hermes main model incorrect : $($model.default)" }
    if ($model.provider -ne 'gemini') { Fail "Hermes main provider incorrect : $($model.provider)" }

    $aux = & $HermesExe config get auxiliary --json 2>&1 | ConvertFrom-Json
    foreach ($route in $Routes.GetEnumerator()) {
        $block = $aux.($route.Key)
        if ($block.provider -ne 'gemini') { Fail "auxiliary.$($route.Key).provider incorrect" }
        if ($block.model -ne $route.Value) { Fail "auxiliary.$($route.Key).model incorrect : $($block.model)" }
    }

    $acp = & $HermesExe acp --check 2>&1
    if ($LASTEXITCODE -ne 0 -or ([string]$acp -notmatch 'ACP check OK')) {
        Fail "ACP check échoué : $acp"
    }
}

Write-Host ''
Write-Host '============================================================' -ForegroundColor Cyan
Write-Host ' E-ZZIO / HERMES — FINAL LLM ROUTER' -ForegroundColor Cyan
Write-Host ' STRICT / FAIL-CLOSED / ROLLBACK' -ForegroundColor Cyan
Write-Host '============================================================' -ForegroundColor Cyan

# 0. PRECHECK
foreach ($p in @($EzzioHome,$SecretsFile,$HermesHome,$HermesConfig,$HermesExe)) {
    Assert-Path $p
}
if (Get-Process -Name hermes -ErrorAction SilentlyContinue) {
    Fail 'Hermes est encore lancé. Ferme Hermes avant cette opération.'
}

# 1. DISCOVER GEMINI
Write-Host ''
Write-Host '[1/8] Discovery Gemini sur 6 clés' -ForegroundColor Yellow
$keyPairs = @(Get-GeminiKeys $SecretsFile)
if ($keyPairs.Count -ne 6) { Fail "Pool Gemini attendu : 6 ; détecté : $($keyPairs.Count)" }

$keyResults = @()
$keyCatalogs = @{}
$referenceModels = $null

foreach ($key in $keyPairs) {
    Write-Host "  [$($key.Name)] interrogation..." -ForegroundColor Yellow
    try {
        $d = Discover-Gemini $key.Name $key.Value
        $keyCatalogs[$key.Name] = @($d.Names)
        $keyResults += [PSCustomObject]@{ Name=$key.Name; Status='OK'; Models=$d.Count; Generative=$d.Generative }
        if ($null -eq $referenceModels) { $referenceModels = @($d.Models) }
        Write-Host "      OK : $($d.Count) modèles / $($d.Generative) génératifs" -ForegroundColor Green
    } catch {
        $keyResults += [PSCustomObject]@{ Name=$key.Name; Status='FAILED'; Models=0; Generative=0 }
        Write-Host "      FAILED : $($_.Exception.Message)" -ForegroundColor Red
    }
}

$healthy = @($keyResults | Where-Object Status -eq 'OK')
if ($healthy.Count -ne 6) { Fail "Pool Gemini non sain : $($healthy.Count)/6" }

# 2. COMMON CATALOG + SELECTION
Write-Host ''
Write-Host '[2/8] Catalogue commun et sélection' -ForegroundColor Yellow
$commonModels = @($keyCatalogs[$healthy[0].Name])
foreach ($h in ($healthy | Select-Object -Skip 1)) {
    $set = @($keyCatalogs[$h.Name])
    $commonModels = @($commonModels | Where-Object { $_ -in $set })
}
$commonModels = @($commonModels | Sort-Object -Unique)
if ($commonModels.Count -eq 0) { Fail 'Aucun modèle commun aux 6 clés Gemini.' }

$primary = Pick-CommonModel @('gemini-3.7-flash','gemini-3.6-flash','gemini-3.5-flash','gemini-flash-latest') $commonModels 'primary'
$fast = Pick-CommonModel @('gemini-3.5-flash-lite','gemini-3.1-flash-lite','gemini-flash-lite-latest','gemini-3.5-flash') $commonModels 'fast'
$ultra = Pick-CommonModel @('gemini-3.1-flash-lite','gemini-3.5-flash-lite','gemini-flash-lite-latest') $commonModels 'ultra'
$escalation = Pick-CommonModel @('gemini-3.1-pro-preview','gemini-3-pro-preview','gemini-2.5-pro') $commonModels 'escalation'

Write-Host "  COMMON     : $($commonModels.Count)" -ForegroundColor Green
Write-Host "  PRIMARY    : $primary" -ForegroundColor Green
Write-Host "  FAST       : $fast" -ForegroundColor Green
Write-Host "  ULTRA      : $ultra" -ForegroundColor Green
Write-Host "  ESCALATION : $escalation" -ForegroundColor Green

# 3. OLLAMA
Write-Host ''
Write-Host '[3/8] Inventaire Ollama' -ForegroundColor Yellow
$ollamaRaw = @(ollama list 2>&1)
if ($LASTEXITCODE -ne 0) { Fail 'ollama list a échoué.' }
$ollamaModels = @()
foreach ($line in ($ollamaRaw | Select-Object -Skip 1)) {
    $parts = ([string]$line) -split '\s{2,}'
    if ($parts.Count -ge 4) {
        $ollamaModels += [PSCustomObject]@{ Name=$parts[0].Trim(); ID=$parts[1].Trim(); Size=$parts[2].Trim(); Modified=$parts[3].Trim() }
    }
}
$ollamaNames = @($ollamaModels | ForEach-Object Name)

function Pick-Ollama([string[]]$Candidates,[string]$Role) {
    foreach ($candidate in $Candidates) { if ($candidate -in $ollamaNames) { return $candidate } }
    Fail "Aucun modèle Ollama disponible pour $Role"
}

$localGeneral = Pick-Ollama @('qwen3.5:9b') 'local_general'
$localAgent = Pick-Ollama @('hermes3:8b','nemotron-3-nano:4b') 'local_agent'
$localFast = Pick-Ollama @('nemotron-3-nano:4b','phi4-mini:latest') 'local_fast_agent'
$localReason = Pick-Ollama @('phi4-mini:latest','nemotron-3-nano:4b') 'local_reasoning'
$embedPrimary = Pick-Ollama @('bge-m3:latest','nomic-embed-text:latest') 'embedding_primary'
$embedSecondary = Pick-Ollama @('nomic-embed-text:latest','bge-m3:latest') 'embedding_secondary'

Write-Host "  GENERAL    : $localGeneral"
Write-Host "  AGENT      : $localAgent"
Write-Host "  FAST       : $localFast"
Write-Host "  REASONING  : $localReason"
Write-Host "  EMBED 1    : $embedPrimary"
Write-Host "  EMBED 2    : $embedSecondary"

# 4. BUILD ROUTES + REGISTRY IN MEMORY
Write-Host ''
Write-Host '[4/8] Construction en mémoire' -ForegroundColor Yellow
$routes = [ordered]@{
    title_generation     = $fast
    compression          = $fast
    approval             = $fast
    mcp                  = $fast
    skills_hub           = $fast
    profile_describer    = $fast
    goal_judge           = $fast
    curator              = $fast
    monitor              = $fast
    memory_query_rewrite = $ultra
    tts_audio_tags        = $ultra
    vision               = $primary
    review               = $primary
    triage_specifier     = $primary
    kanban_decomposer    = $primary
    delegation           = $primary
    background_review    = $primary
}

$geminiRecords = @(
    foreach ($m in $referenceModels) {
        $name = ([string]$m.name -replace '^models/','')
        $caps = [System.Collections.Generic.List[string]]::new()
        foreach ($method in @($m.supportedGenerationMethods)) {
            switch ([string]$method) {
                'generateContent' { $caps.Add('chat') }
                'embedContent' { $caps.Add('embedding') }
                'countTokens' { $caps.Add('token_count') }
            }
        }
        $lower = $name.ToLowerInvariant()
        if ($m.thinking -eq $true) { $caps.Add('reasoning') }
        if ($lower -match 'flash|lite') { $caps.Add('fast') }
        if ($lower -match 'pro') { $caps.Add('deep_reasoning') }
        [ordered]@{
            name=$name
            display_name=$m.displayName
            version=$m.version
            input_token_limit=$m.inputTokenLimit
            output_token_limit=$m.outputTokenLimit
            thinking=$m.thinking
            supported_generation_methods=@($m.supportedGenerationMethods)
            common_to_all_six_keys=($name -in $commonModels)
            capabilities=@($caps | Select-Object -Unique)
        }
    }
)

$ollamaRecords = @(
    foreach ($m in $ollamaModels) {
        $caps = [System.Collections.Generic.List[string]]::new()
        $lower = $m.Name.ToLowerInvariant()
        if ($lower -match 'bge|nomic|embed') {
            $caps.Add('embedding')
        } else {
            $caps.Add('chat')
            if ($lower -match 'qwen3\.5|hermes3|nemotron') { $caps.Add('agentic'); $caps.Add('tools') }
            if ($lower -match 'qwen3\.5') { $caps.Add('vision_candidate') }
            if ($lower -match 'nemotron|phi4') { $caps.Add('fast'); $caps.Add('reasoning_candidate') }
        }
        [ordered]@{ name=$m.Name; id=$m.ID; size=$m.Size; modified=$m.Modified; capabilities=@($caps | Select-Object -Unique) }
    }
)

$registry = [ordered]@{
    schema_version='5.1'
    generated_at=(Get-Date).ToUniversalTime().ToString('o')
    secret_source=$SecretsFile
    gemini_pool=@($keyResults | ForEach-Object { [ordered]@{name=$_.Name;status=$_.Status;models=$_.Models;generative_models=$_.Generative} })
    availability=[ordered]@{healthy_keys=$healthy.Count;total_keys=$keyPairs.Count;common_models=$commonModels.Count}
    selected=[ordered]@{
        primary=[ordered]@{provider='gemini';model=$primary}
        escalation=[ordered]@{provider='gemini';model=$escalation}
        fast_cloud=[ordered]@{provider='gemini';model=$fast}
        ultra_fast_cloud=[ordered]@{provider='gemini';model=$ultra}
        local_general=[ordered]@{provider='ollama';model=$localGeneral}
        local_agent=[ordered]@{provider='ollama';model=$localAgent}
        local_fast_agent=[ordered]@{provider='ollama';model=$localFast}
        local_reasoning=[ordered]@{provider='ollama';model=$localReason}
        embedding_primary=[ordered]@{provider='ollama';model=$embedPrimary}
        embedding_secondary=[ordered]@{provider='ollama';model=$embedSecondary}
    }
    functions=[ordered]@{
        main_agent=@($primary,$localGeneral,$localAgent)
        coding=@($primary,$localGeneral,$localAgent)
        complex_reasoning=@($escalation,$primary,$localReason)
        fast_tasks=@($fast,$ultra,$localFast)
        vision=@($primary,$localGeneral)
        tool_use=@($primary,$localGeneral,$localAgent,$localFast)
        compression=@($fast,$ultra,$localFast)
        memory_rewrite=@($ultra,$localFast,$localReason)
        embeddings=@($embedPrimary,$embedSecondary)
    }
    gemini_models=$geminiRecords
    ollama_models=$ollamaRecords
}

$registryJson = $registry | ConvertTo-Json -Depth 20
$null = $registryJson | ConvertFrom-Json

# 5. PREPARE HERMES IN MEMORY
Write-Host ''
Write-Host '[5/8] Préparation Hermes en mémoire' -ForegroundColor Yellow
$lines = [System.Collections.Generic.List[string]]::new()
foreach ($line in [System.IO.File]::ReadAllLines($HermesConfig,[System.Text.Encoding]::UTF8)) { $lines.Add($line) }

$auxIndex = Find-TopLevel $lines 'auxiliary'
if ($auxIndex -lt 0) { Fail 'Bloc auxiliary introuvable.' }

$modelStart = Find-TopLevel $lines 'model'
if ($modelStart -lt 0) { Fail 'Bloc model introuvable.' }
$modelEnd = Get-BlockEnd $lines $modelStart
Replace-RequiredField $lines $modelStart $modelEnd 'default' $primary '  '
Replace-RequiredField $lines $modelStart $modelEnd 'provider' 'gemini' '  '
Replace-RequiredField $lines $modelStart $modelEnd 'base_url' 'https://generativelanguage.googleapis.com/v1beta' '  '

foreach ($route in $routes.GetEnumerator()) {
    $start = Find-Child $lines $auxIndex $route.Key
    if ($start -lt 0) { Fail "Bloc auxiliary.$($route.Key) introuvable." }
    $end = Get-BlockEnd $lines $start
    Replace-RequiredField $lines $start $end 'provider' 'gemini' '    '
    Replace-RequiredField $lines $start $end 'model' $route.Value '    '
    Replace-RequiredField $lines $start $end 'base_url' 'https://generativelanguage.googleapis.com/v1beta' '    '
}

$configText = $lines -join [Environment]::NewLine

# 6. COMMIT HERMES WITH ROLLBACK
Write-Host ''
Write-Host '[6/8] Commit Hermes + validation' -ForegroundColor Yellow
Copy-Item -LiteralPath $HermesConfig -Destination $HermesBackup -Force

$committedHermes = $false
try {
    [System.IO.File]::WriteAllText($HermesConfig,$configText,[System.Text.UTF8Encoding]::new($false))
    Test-HermesConfig -ExpectedPrimary $primary -Routes $routes
    $committedHermes = $true
    Write-Host '  MAIN + AUXILIAIRES = OK' -ForegroundColor Green
    Write-Host '  ACP                = OK' -ForegroundColor Green
}
catch {
    Copy-Item -LiteralPath $HermesBackup -Destination $HermesConfig -Force
    Fail "Hermes rollback effectué : $($_.Exception.Message)"
}
if (-not $committedHermes) { Fail 'Commit Hermes non confirmé.' }

# 7. WRITE REGISTRY + REFRESH
Write-Host ''
Write-Host '[7/8] Ecriture registre + refresh' -ForegroundColor Yellow
New-Item -ItemType Directory -Path $RegistryDir -Force | Out-Null
New-Item -ItemType Directory -Path $ToolsDir -Force | Out-Null

$registryTemp = "$RegistryPath.tmp-$PID"
Set-Content -LiteralPath $registryTemp -Value $registryJson -Encoding UTF8
if (-not (Test-Path -LiteralPath $registryTemp)) { Fail 'Registre temporaire absent.' }
Move-Item -LiteralPath $registryTemp -Destination $RegistryPath -Force

$refreshText = @'
#requires -Version 7.0
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$EzzioHome = 'G:\AI\E-zzio'
$SecretsFile = Join-Path $EzzioHome 'secrets\.env'
$RegistryDir = Join-Path $EzzioHome 'state\audit\current\capability_registry'
$RegistryPath = Join-Path $RegistryDir 'llm_capability_registry.json'

function Fail([string]$Message) { throw $Message }

$keys = @()
foreach ($line in Get-Content -LiteralPath $SecretsFile) {
    if ($line -match '^\s*([^#=]+)\s*=(.*)$') {
        $name = $Matches[1].Trim()
        $value = $Matches[2].Trim()
        if ((($name -match '^GEMINI_API_KEY_\d+$') -or ($name -eq 'GEMINI_API6')) -and -not [string]::IsNullOrWhiteSpace($value)) {
            $keys += [PSCustomObject]@{Name=$name;Value=$value}
        }
    }
}
$keys = @($keys | Sort-Object Name -Unique)
if ($keys.Count -ne 6) { Fail "Pool Gemini invalide : $($keys.Count)/6" }

$health = @()
$catalogs = @{}
foreach ($key in $keys) {
    try {
        $resp = Invoke-RestMethod -Uri 'https://generativelanguage.googleapis.com/v1beta/models?pageSize=1000' -Headers @{ 'x-goog-api-key'=$key.Value } -Method Get -TimeoutSec 30
        $models = @($resp.models)
        if ($models.Count -eq 0) { throw 'models.list=0' }
        $names = @($models | ForEach-Object { ([string]$_.name -replace '^models/','') } | Where-Object { $_ } | Sort-Object -Unique)
        $catalogs[$key.Name] = $names
        $health += [PSCustomObject]@{Name=$key.Name;Status='OK';Models=$models.Count}
    } catch {
        $health += [PSCustomObject]@{Name=$key.Name;Status='FAILED';Models=0}
    }
}

$healthy = @($health | Where-Object Status -eq 'OK')
if ($healthy.Count -ne 6) { Fail "Gemini pool unhealthy : $($healthy.Count)/6" }

$common = @($catalogs[$healthy[0].Name])
foreach ($h in ($healthy | Select-Object -Skip 1)) {
    $set = @($catalogs[$h.Name])
    $common = @($common | Where-Object { $_ -in $set })
}
$common = @($common | Sort-Object -Unique)
if ($common.Count -eq 0) { Fail 'Aucun modèle commun.' }

function Pick([string[]]$Candidates,[string]$Role) {
    foreach ($c in $Candidates) { if ($c -in $common) { return $c } }
    Fail "Aucun modèle commun pour $Role"
}

$primary = Pick @('gemini-3.7-flash','gemini-3.6-flash','gemini-3.5-flash','gemini-flash-latest') 'primary'
$fast = Pick @('gemini-3.5-flash-lite','gemini-3.1-flash-lite','gemini-flash-lite-latest','gemini-3.5-flash') 'fast'
$ultra = Pick @('gemini-3.1-flash-lite','gemini-3.5-flash-lite','gemini-flash-lite-latest') 'ultra'
$pro = Pick @('gemini-3.1-pro-preview','gemini-3-pro-preview','gemini-2.5-pro') 'escalation'

New-Item -ItemType Directory -Path $RegistryDir -Force | Out-Null
$registry = [ordered]@{
    schema_version='5.1'
    generated_at=(Get-Date).ToUniversalTime().ToString('o')
    gemini_pool=$health
    availability=[ordered]@{healthy_keys=$healthy.Count;total_keys=$keys.Count;common_models=$common.Count}
    selected=[ordered]@{
        primary=[ordered]@{provider='gemini';model=$primary}
        escalation=[ordered]@{provider='gemini';model=$pro}
        fast_cloud=[ordered]@{provider='gemini';model=$fast}
        ultra_fast_cloud=[ordered]@{provider='gemini';model=$ultra}
    }
    common_gemini_models=$common
}

$temp = "$RegistryPath.tmp-$PID"
$registry | ConvertTo-Json -Depth 16 | Set-Content -LiteralPath $temp -Encoding UTF8
Move-Item -LiteralPath $temp -Destination $RegistryPath -Force
$check = Get-Content -LiteralPath $RegistryPath -Raw | ConvertFrom-Json
if ($check.schema_version -ne '5.1') { Fail 'Schema refresh invalide.' }
if ($check.availability.healthy_keys -ne 6) { Fail 'Pool refresh invalide.' }

Write-Host ''
Write-Host '[OK] LLM registry refreshed.' -ForegroundColor Green
Write-Host "Healthy Gemini keys : $($healthy.Count)/6"
Write-Host "Common Gemini models: $($common.Count)"
Write-Host "Primary             : $primary"
Write-Host "Fast                : $fast"
Write-Host "Ultra               : $ultra"
Write-Host "Escalation          : $pro"
Write-Host "Registry            : $RegistryPath"
'@

Set-Content -LiteralPath $RefreshPath -Value $refreshText -Encoding UTF8
if (-not (Test-Path -LiteralPath $RefreshPath)) { Fail 'Refresh script absent.' }

# 8. FINAL PHYSICAL VALIDATION + REFRESH DRY TEST
Write-Host ''
Write-Host '[8/8] Validation physique + test refresh' -ForegroundColor Yellow
Assert-Path $RegistryPath
Assert-Path $RefreshPath

$loaded = Get-Content -LiteralPath $RegistryPath -Raw | ConvertFrom-Json
if ($loaded.schema_version -ne '5.1') { Fail 'Schema registre final invalide.' }
if ($loaded.availability.healthy_keys -ne 6) { Fail 'Registre final : pool != 6/6.' }
if ($loaded.selected.primary.model -ne $primary) { Fail 'Registre final : primary incorrect.' }
if ($loaded.selected.fast_cloud.model -ne $fast) { Fail 'Registre final : fast incorrect.' }
if ($loaded.selected.ultra_fast_cloud.model -ne $ultra) { Fail 'Registre final : ultra incorrect.' }
if ($loaded.selected.escalation.model -ne $escalation) { Fail 'Registre final : escalation incorrect.' }

$refreshTokens = $null
$refreshErrors = $null
[System.Management.Automation.Language.Parser]::ParseFile(
    $RefreshPath,
    [ref]$refreshTokens,
    [ref]$refreshErrors
) | Out-Null

if ($refreshErrors.Count -gt 0) {
    $messages = @($refreshErrors | ForEach-Object { $_.Message }) -join ' | '
    Fail "Syntaxe du refresh invalide : $messages"
}

$finalAcp = & $HermesExe acp --check 2>&1
if ($LASTEXITCODE -ne 0 -or ([string]$finalAcp -notmatch 'ACP check OK')) { Fail "ACP final échoué : $finalAcp" }

Write-Host ''
Write-Host '============================================================' -ForegroundColor Green
Write-Host ' FINAL LLM ROUTER — VALIDATION REELLE REUSSIE' -ForegroundColor Green
Write-Host '============================================================' -ForegroundColor Green
Write-Host ''
Write-Host "Gemini pool : $($healthy.Count)/6"
Write-Host "Common      : $($commonModels.Count)"
Write-Host "PRIMARY     : $primary"
Write-Host "FAST        : $fast"
Write-Host "ULTRA       : $ultra"
Write-Host "ESCALATION  : $escalation"
Write-Host ''
Write-Host "Registry    : $RegistryPath"
Write-Host "Refresh     : $RefreshPath"
Write-Host "Backup      : $HermesBackup"
Write-Host 'ACP         : OK'
Write-Host 'Ollama      : aucun modèle supprimé'
Write-Host 'Python 3.12 : non modifie'
Write-Host ''
Write-Host 'SUCCESS — validation physique et syntaxique OK.' -ForegroundColor Green
