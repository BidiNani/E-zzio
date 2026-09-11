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

function Fail([string]$Message) {
    throw $Message
}

Write-Host ''
Write-Host '============================================================' -ForegroundColor Cyan
Write-Host ' E-ZZIO / HERMES — FINAL LLM ROUTER' -ForegroundColor Cyan
Write-Host '============================================================' -ForegroundColor Cyan

# ------------------------------------------------------------
# 0. PRECHECK
# ------------------------------------------------------------

foreach ($p in @(
    $EzzioHome,
    $SecretsFile,
    $HermesHome,
    $HermesConfig,
    $HermesExe
)) {
    if (-not (Test-Path -LiteralPath $p)) {
        Fail "Ressource absente : $p"
    }
}

if (Get-Process -Name hermes -ErrorAction SilentlyContinue) {
    Fail 'Hermes est encore lancé.'
}

# ------------------------------------------------------------
# 1. GEMINI KEYS
# ------------------------------------------------------------

Write-Host ''
Write-Host '[1/8] Lecture du pool Gemini' -ForegroundColor Yellow

$keyPairs = @()

foreach ($line in Get-Content -LiteralPath $SecretsFile) {
    if ($line -match '^\s*([^#=]+)\s*=(.*)$') {
        $name  = $Matches[1].Trim()
        $value = $Matches[2].Trim()

        $isGemini = (
            $name -match '^GEMINI_API_KEY_\d+$' -or
            $name -eq 'GEMINI_API6'
        )

        if ($isGemini -and -not [string]::IsNullOrWhiteSpace($value)) {
            $keyPairs += [PSCustomObject]@{
                Name  = $name
                Value = $value
            }
        }
    }
}

$keyPairs = @($keyPairs | Sort-Object Name -Unique)

if ($keyPairs.Count -ne 6) {
    Fail "Pool Gemini attendu : 6 ; détecté : $($keyPairs.Count)"
}

Write-Host "  Clés détectées : 6" -ForegroundColor Green

# ------------------------------------------------------------
# 2. DISCOVERY PAR CLE
# ------------------------------------------------------------

Write-Host ''
Write-Host '[2/8] Discovery Gemini' -ForegroundColor Yellow

$keyResults = @()
$keyCatalogs = @{}

foreach ($key in $keyPairs) {
    Write-Host "  [$($key.Name)] ..." -ForegroundColor Yellow

    try {
        $resp = Invoke-RestMethod `
            -Uri 'https://generativelanguage.googleapis.com/v1beta/models?pageSize=1000' `
            -Headers @{ 'x-goog-api-key' = $key.Value } `
            -Method Get `
            -TimeoutSec 30

        $models = @($resp.models)

        if ($models.Count -eq 0) {
            throw 'models.list retourne 0 modèle.'
        }

        $names = @(
            $models |
            ForEach-Object {
                ([string]$_.name -replace '^models/','')
            } |
            Sort-Object -Unique
        )

        $generative = @(
            $models |
            Where-Object {
                @($_.supportedGenerationMethods) -contains 'generateContent'
            }
        )

        $keyCatalogs[$key.Name] = $names

        $keyResults += [PSCustomObject]@{
            Name       = $key.Name
            Status     = 'OK'
            Models     = $models.Count
            Generative = $generative.Count
        }

        Write-Host "      OK : $($models.Count) modèles / $($generative.Count) génératifs" `
            -ForegroundColor Green
    }
    catch {
        $keyResults += [PSCustomObject]@{
            Name       = $key.Name
            Status     = 'FAILED'
            Models     = 0
            Generative = 0
        }

        Write-Host "      FAILED : $($_.Exception.Message)" -ForegroundColor Red
    }
}

$healthy = @(
    $keyResults |
    Where-Object Status -eq 'OK'
)

if ($healthy.Count -ne 6) {
    Fail "Pool Gemini non sain : $($healthy.Count)/6"
}

# ------------------------------------------------------------
# 3. CATALOGUE COMMUN
# ------------------------------------------------------------

Write-Host ''
Write-Host '[3/8] Catalogue commun' -ForegroundColor Yellow

$commonModels = @(
    $keyCatalogs[$healthy[0].Name]
)

foreach ($h in ($healthy | Select-Object -Skip 1)) {
    $set = @($keyCatalogs[$h.Name])

    $commonModels = @(
        $commonModels |
        Where-Object { $_ -in $set }
    )
}

$commonModels = @(
    $commonModels |
    Sort-Object -Unique
)

if ($commonModels.Count -eq 0) {
    Fail 'Aucun modèle commun aux 6 clés.'
}

Write-Host "  Modèles communs : $($commonModels.Count)" -ForegroundColor Green

function Pick-Gemini {
    param(
        [string[]]$Candidates,
        [string]$Role
    )

    foreach ($candidate in $Candidates) {
        if ($candidate -in $commonModels) {
            return $candidate
        }
    }

    Fail "Aucun modèle disponible pour $Role"
}

$primary = Pick-Gemini @(
    'gemini-3.7-flash',
    'gemini-3.6-flash',
    'gemini-3.5-flash',
    'gemini-flash-latest'
) 'primary'

$fast = Pick-Gemini @(
    'gemini-3.5-flash-lite',
    'gemini-3.1-flash-lite',
    'gemini-flash-lite-latest',
    'gemini-3.5-flash'
) 'fast'

$ultra = Pick-Gemini @(
    'gemini-3.1-flash-lite',
    'gemini-3.5-flash-lite',
    'gemini-flash-lite-latest'
) 'ultra'

$escalation = Pick-Gemini @(
    'gemini-3.1-pro-preview',
    'gemini-3-pro-preview',
    'gemini-2.5-pro'
) 'escalation'

Write-Host "  PRIMARY    : $primary" -ForegroundColor Green
Write-Host "  FAST       : $fast" -ForegroundColor Green
Write-Host "  ULTRA      : $ultra" -ForegroundColor Green
Write-Host "  ESCALATION : $escalation" -ForegroundColor Green

# ------------------------------------------------------------
# 4. OLLAMA
# ------------------------------------------------------------

Write-Host ''
Write-Host '[4/8] Inventaire Ollama' -ForegroundColor Yellow

$ollamaRaw = @(ollama list 2>&1)

if ($LASTEXITCODE -ne 0) {
    Fail 'ollama list a échoué.'
}

$ollamaNames = @(
    $ollamaRaw |
    Select-Object -Skip 1 |
    ForEach-Object {
        $parts = ([string]$_) -split '\s{2,}'
        if ($parts.Count -ge 1) {
            $parts[0].Trim()
        }
    } |
    Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
)

function Pick-Ollama {
    param(
        [string[]]$Candidates,
        [string]$Role
    )

    foreach ($candidate in $Candidates) {
        if ($candidate -in $ollamaNames) {
            return $candidate
        }
    }

    Fail "Aucun modèle Ollama disponible pour $Role"
}

$localGeneral = Pick-Ollama @(
    'qwen3.5:9b'
) 'local_general'

$localAgent = Pick-Ollama @(
    'hermes3:8b',
    'nemotron-3-nano:4b'
) 'local_agent'

$localFast = Pick-Ollama @(
    'nemotron-3-nano:4b',
    'phi4-mini:latest'
) 'local_fast'

$localReason = Pick-Ollama @(
    'phi4-mini:latest',
    'nemotron-3-nano:4b'
) 'local_reasoning'

$embedPrimary = Pick-Ollama @(
    'bge-m3:latest',
    'nomic-embed-text:latest'
) 'embedding_primary'

$embedSecondary = Pick-Ollama @(
    'nomic-embed-text:latest',
    'bge-m3:latest'
) 'embedding_secondary'

Write-Host "  GENERAL    : $localGeneral"
Write-Host "  AGENT      : $localAgent"
Write-Host "  FAST       : $localFast"
Write-Host "  REASONING  : $localReason"
Write-Host "  EMBED      : $embedPrimary"
Write-Host "  EMBED 2    : $embedSecondary"

# ------------------------------------------------------------
# 5. BACKUP
# ------------------------------------------------------------

Write-Host ''
Write-Host '[5/8] Backup Hermes' -ForegroundColor Yellow

$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$backup = "$HermesConfig.pre-final-router-$stamp.bak"

Copy-Item `
    -LiteralPath $HermesConfig `
    -Destination $backup `
    -Force

Write-Host "  Backup : $backup" -ForegroundColor Green

# ------------------------------------------------------------
# 6. PATCH + VALIDATION HERMES
# ------------------------------------------------------------

Write-Host ''
Write-Host '[6/8] Routage Hermes' -ForegroundColor Yellow

$lines = [System.Collections.Generic.List[string]]::new()

foreach ($line in [System.IO.File]::ReadAllLines(
    $HermesConfig,
    [System.Text.Encoding]::UTF8
)) {
    $lines.Add($line)
}

function Find-Block {
    param([string]$Task)

    $aux = -1

    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -match '^auxiliary:\s*$') {
            $aux = $i
            break
        }
    }

    if ($aux -lt 0) {
        Fail 'Bloc auxiliary introuvable.'
    }

    $start = -1

    for ($i = $aux + 1; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -match '^[^\s#][^:]*:\s*$') {
            break
        }

        if ($lines[$i] -match "^  $([regex]::Escape($Task)):\s*$") {
            $start = $i
            break
        }
    }

    if ($start -lt 0) {
        Fail "Bloc auxiliary.$Task introuvable."
    }

    $end = $lines.Count

    for ($i = $start + 1; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -match '^  [A-Za-z0-9_]+:\s*$') {
            $end = $i
            break
        }
        if ($lines[$i] -match '^[^\s#][^:]*:\s*$') {
            $end = $i
            break
        }
    }

    return @($start,$end)
}

function Replace-Field {
    param(
        [int]$Start,
        [int]$End,
        [string]$Field,
        [string]$Value
    )

    for ($i = $Start + 1; $i -lt $End; $i++) {
        if ($lines[$i] -match "^    $([regex]::Escape($Field)):\s*") {
            $lines[$i] = "    $Field`: $Value"
            return
        }
    }

    Fail "Champ absent : $Field"
}

# main model
$modelStart = -1

for ($i = 0; $i -lt $lines.Count; $i++) {
    if ($lines[$i] -match '^model:\s*$') {
        $modelStart = $i
        break
    }
}

if ($modelStart -lt 0) {
    Fail 'Bloc model introuvable.'
}

$modelEnd = $lines.Count

for ($i = $modelStart + 1; $i -lt $lines.Count; $i++) {
    if ($lines[$i] -match '^[^\s#][^:]*:\s*$') {
        $modelEnd = $i
        break
    }
}

Replace-Field $modelStart $modelEnd 'default'  $primary
Replace-Field $modelStart $modelEnd 'provider' 'gemini'
Replace-Field $modelStart $modelEnd 'base_url' 'https://generativelanguage.googleapis.com/v1beta'

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
    tts_audio_tags       = $ultra
    vision               = $primary
    review               = $primary
    triage_specifier     = $primary
    kanban_decomposer    = $primary
    delegation           = $primary
    background_review    = $primary
}

foreach ($route in $routes.GetEnumerator()) {
    $range = Find-Block $route.Key
    Replace-Field $range[0] $range[1] 'provider' 'gemini'
    Replace-Field $range[0] $range[1] 'model' $route.Value
    Replace-Field $range[0] $range[1] 'base_url' 'https://generativelanguage.googleapis.com/v1beta'
}

[System.IO.File]::WriteAllLines(
    $HermesConfig,
    $lines.ToArray(),
    [System.Text.UTF8Encoding]::new($false)
)

try {
    $validatedModel = & $HermesExe config get model --json 2>&1 |
        ConvertFrom-Json

    $validatedAux = & $HermesExe config get auxiliary --json 2>&1 |
        ConvertFrom-Json

    if ($validatedModel.default -ne $primary) {
        throw "Main model incorrect : $($validatedModel.default)"
    }

    if ($validatedModel.provider -ne 'gemini') {
        throw "Main provider incorrect : $($validatedModel.provider)"
    }

    foreach ($route in $routes.GetEnumerator()) {
        $block = $validatedAux.($route.Key)

        if ($block.provider -ne 'gemini') {
            throw "auxiliary.$($route.Key).provider incorrect"
        }

        if ($block.model -ne $route.Value) {
            throw "auxiliary.$($route.Key).model incorrect : $($block.model)"
        }
    }

    $acp = & $HermesExe acp --check 2>&1

    if ($LASTEXITCODE -ne 0 -or ([string]$acp -notmatch 'ACP check OK')) {
        throw "ACP incorrect : $acp"
    }
}
catch {
    Copy-Item `
        -LiteralPath $backup `
        -Destination $HermesConfig `
        -Force

    Fail "Validation Hermes échouée. Configuration restaurée. $($_.Exception.Message)"
}

Write-Host '  MAIN + AUXILIAIRES = OK' -ForegroundColor Green
Write-Host '  ACP                = OK' -ForegroundColor Green

# ------------------------------------------------------------
# 7. REGISTRY
# ------------------------------------------------------------

Write-Host ''
Write-Host '[7/8] Génération registre' -ForegroundColor Yellow

New-Item -ItemType Directory -Path $RegistryDir -Force | Out-Null
New-Item -ItemType Directory -Path $ToolsDir -Force | Out-Null

$detailKey = (
    $keyPairs |
    Where-Object Name -eq $healthy[0].Name |
    Select-Object -ExpandProperty Value
)

$detailed = Invoke-RestMethod `
    -Uri 'https://generativelanguage.googleapis.com/v1beta/models?pageSize=1000' `
    -Headers @{ 'x-goog-api-key' = $detailKey } `
    -Method Get `
    -TimeoutSec 30

$geminiRecords = @(
    foreach ($m in @($detailed.models)) {
        $cleanName = ([string]$m.name -replace '^models/','')

        $caps = [System.Collections.Generic.List[string]]::new()

        foreach ($method in @($m.supportedGenerationMethods)) {
            switch ([string]$method) {
                'generateContent' { $caps.Add('chat') }
                'embedContent'    { $caps.Add('embedding') }
                'countTokens'     { $caps.Add('token_count') }
            }
        }

        $n = $cleanName.ToLowerInvariant()

        if ($m.thinking -eq $true) { $caps.Add('reasoning') }
        if ($n -match 'flash|lite') { $caps.Add('fast') }
        if ($n -match 'pro') { $caps.Add('deep_reasoning') }

        [ordered]@{
            name = $cleanName
            display_name = $m.displayName
            version = $m.version
            input_token_limit = $m.inputTokenLimit
            output_token_limit = $m.outputTokenLimit
            thinking = $m.thinking
            supported_generation_methods = @($m.supportedGenerationMethods)
            common_to_all_six_keys = ($cleanName -in $commonModels)
            capabilities = @($caps | Select-Object -Unique)
        }
    }
)

$registry = [ordered]@{
    schema_version = '5.0'
    generated_at = (Get-Date).ToUniversalTime().ToString('o')
    secret_source = $SecretsFile

    gemini_pool = @(
        foreach ($r in $keyResults) {
            [ordered]@{
                name = $r.Name
                status = $r.Status
                models = $r.Models
                generative_models = $r.Generative
            }
        }
    )

    availability = [ordered]@{
        healthy_keys = $healthy.Count
        total_keys = $keyPairs.Count
        common_models = $commonModels.Count
    }

    selected = [ordered]@{
        primary = @{ provider='gemini'; model=$primary }
        escalation = @{ provider='gemini'; model=$escalation }
        fast_cloud = @{ provider='gemini'; model=$fast }
        ultra_fast_cloud = @{ provider='gemini'; model=$ultra }

        local_general = @{ provider='ollama'; model=$localGeneral }
        local_agent = @{ provider='ollama'; model=$localAgent }
        local_fast_agent = @{ provider='ollama'; model=$localFast }
        local_reasoning = @{ provider='ollama'; model=$localReason }

        embedding_primary = @{ provider='ollama'; model=$embedPrimary }
        embedding_secondary = @{ provider='ollama'; model=$embedSecondary }
    }

    functions = [ordered]@{
        main_agent = @($primary,$localGeneral,$localAgent)
        coding = @($primary,$localGeneral,$localAgent)
        complex_reasoning = @($escalation,$primary,$localReason)
        fast_tasks = @($fast,$ultra,$localFast)
        vision = @($primary,$localGeneral)
        tool_use = @($primary,$localGeneral,$localAgent,$localFast)
        compression = @($fast,$ultra,$localFast)
        memory_rewrite = @($ultra,$localFast,$localReason)
        embeddings = @($embedPrimary,$embedSecondary)
    }

    gemini_models = $geminiRecords
}

$registry |
    ConvertTo-Json -Depth 20 |
    Set-Content -LiteralPath $RegistryPath -Encoding UTF8

if (-not (Test-Path -LiteralPath $RegistryPath)) {
    Fail "Registre non créé : $RegistryPath"
}

# ------------------------------------------------------------
# 8. REFRESH ENGINE
# ------------------------------------------------------------

$refreshLines = @(
'#requires -Version 7.0',
'Set-StrictMode -Version Latest',
'$ErrorActionPreference = ''Stop''',
'$EzzioHome = ''G:\AI\E-zzio''',
'$SecretsFile = Join-Path $EzzioHome ''secrets\.env''',
'$RegistryDir = Join-Path $EzzioHome ''state\audit\current\capability_registry''',
'$RegistryPath = Join-Path $RegistryDir ''llm_capability_registry.json''',
'New-Item -ItemType Directory -Path $RegistryDir -Force | Out-Null',
'$keys = @()',
'foreach ($line in Get-Content -LiteralPath $SecretsFile) {',
'    if ($line -match ''^\s*([^#=]+)\s*=(.*)$'') {',
'        $name = $Matches[1].Trim()',
'        $value = $Matches[2].Trim()',
'        if ((($name -match ''^GEMINI_API_KEY_\d+$'') -or ($name -eq ''GEMINI_API6'')) -and -not [string]::IsNullOrWhiteSpace($value)) {',
'            $keys += [PSCustomObject]@{Name=$name;Value=$value}',
'        }',
'    }',
'}',
'if ($keys.Count -ne 6) { throw "Gemini pool invalide : $($keys.Count)/6" }',
'$health = @()',
'$catalogs = @{}',
'foreach ($key in $keys) {',
'    try {',
'        $resp = Invoke-RestMethod -Uri ''https://generativelanguage.googleapis.com/v1beta/models?pageSize=1000'' -Headers @{''x-goog-api-key''=$key.Value} -Method Get -TimeoutSec 30',
'        $models = @($resp.models)',
'        $names = @($models | ForEach-Object { ([string]$_.name -replace ''^models/'','''') } | Sort-Object -Unique)',
'        $catalogs[$key.Name] = $names',
'        $health += [PSCustomObject]@{Name=$key.Name;Status=''OK'';Models=$models.Count}',
'    } catch {',
'        $health += [PSCustomObject]@{Name=$key.Name;Status=''FAILED'';Models=0}',
'    }',
'}',
'$healthy = @($health | Where-Object Status -eq ''OK'')',
'if ($healthy.Count -ne 6) { throw "Gemini pool unhealthy : $($healthy.Count)/6" }',
'$common = @($catalogs[$healthy[0].Name])',
'foreach ($h in ($healthy | Select-Object -Skip 1)) {',
'    $set = @($catalogs[$h.Name])',
'    $common = @($common | Where-Object { $_ -in $set })',
'}',
'$common = @($common | Sort-Object -Unique)',
'function Pick([string[]]$Candidates,[string]$Role) { foreach ($c in $Candidates) { if ($c -in $common) { return $c } } throw "Aucun modèle commun pour $Role" }',
'$primary = Pick @(',
'''gemini-3.7-flash'',''gemini-3.6-flash'',''gemini-3.5-flash'',''gemini-flash-latest''',
') ''primary''',
'$fast = Pick @(',
'''gemini-3.5-flash-lite'',''gemini-3.1-flash-lite'',''gemini-flash-lite-latest'',''gemini-3.5-flash''',
') ''fast''',
'$ultra = Pick @(',
'''gemini-3.1-flash-lite'',''gemini-3.5-flash-lite'',''gemini-flash-lite-latest''',
') ''ultra''',
'$pro = Pick @(',
'''gemini-3.1-pro-preview'',''gemini-3-pro-preview'',''gemini-2.5-pro''',
') ''escalation''',
'$registry = [ordered]@{',
'    schema_version=''5.0''',
'    generated_at=(Get-Date).ToUniversalTime().ToString(''o'')',
'    gemini_pool=$health',
'    availability=@{healthy_keys=$healthy.Count;total_keys=6;common_models=$common.Count}',
'    selected=@{',
'        primary=@{provider=''gemini'';model=$primary}',
'        escalation=@{provider=''gemini'';model=$pro}',
'        fast_cloud=@{provider=''gemini'';model=$fast}',
'        ultra_fast_cloud=@{provider=''gemini'';model=$ultra}',
'    }',
'    common_gemini_models=$common',
'}',
'$registry | ConvertTo-Json -Depth 16 | Set-Content -LiteralPath $RegistryPath -Encoding UTF8',
'if (-not (Test-Path -LiteralPath $RegistryPath)) { throw ''Registry non créé'' }',
'Write-Host ''[OK] LLM registry refreshed.'' -ForegroundColor Green',
'Write-Host "Healthy Gemini keys : $($healthy.Count)/6"',
'Write-Host "Common Gemini models: $($common.Count)"',
'Write-Host "Primary             : $primary"',
'Write-Host "Fast                : $fast"',
'Write-Host "Ultra               : $ultra"',
'Write-Host "Escalation          : $pro"'
)

Set-Content `
    -LiteralPath $RefreshPath `
    -Value ($refreshLines -join [Environment]::NewLine) `
    -Encoding UTF8

if (-not (Test-Path -LiteralPath $RefreshPath)) {
    Fail "Refresh absent : $RefreshPath"
}

$loaded = Get-Content -LiteralPath $RegistryPath -Raw | ConvertFrom-Json

if ($loaded.schema_version -ne '5.0') {
    Fail 'Schema registre invalide.'
}

if ($loaded.availability.healthy_keys -ne 6) {
    Fail 'Registre : pool Gemini non sain.'
}

if ($loaded.selected.primary.model -ne $primary) {
    Fail 'Registre : primary incorrect.'
}

if ($loaded.selected.fast_cloud.model -ne $fast) {
    Fail 'Registre : fast incorrect.'
}

if ($loaded.selected.ultra_fast_cloud.model -ne $ultra) {
    Fail 'Registre : ultra incorrect.'
}

if ($loaded.selected.escalation.model -ne $escalation) {
    Fail 'Registre : escalation incorrect.'
}

Write-Host ''
Write-Host '============================================================' -ForegroundColor Green
Write-Host ' FINAL LLM ROUTER — VALIDATION REELLEMENT REUSSIE' -ForegroundColor Green
Write-Host '============================================================' -ForegroundColor Green
Write-Host ''
Write-Host "Gemini pool : 6/6"
Write-Host "Common      : $($commonModels.Count)"
Write-Host "PRIMARY     : $primary"
Write-Host "FAST        : $fast"
Write-Host "ULTRA       : $ultra"
Write-Host "ESCALATION  : $escalation"
Write-Host "Registry    : $RegistryPath"
Write-Host "Refresh     : $RefreshPath"
Write-Host "Backup      : $backup"
Write-Host 'ACP         : OK'
Write-Host ''

