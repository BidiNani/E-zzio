#requires -Version 7.0

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$EzzioHome = 'G:\AI\E-zzio'
$SecretsFile = Join-Path $EzzioHome 'secrets\.env'
$RegistryDir = Join-Path $EzzioHome 'state\audit\current\capability_registry'
$RegistryPath = Join-Path $RegistryDir 'llm_capability_registry.json'

function Fail([string]$Message) {
    throw $Message
}

function Get-SafeProperty {
    param(
        [Parameter(Mandatory)]
        [object]$Object,

        [Parameter(Mandatory)]
        [string]$Name
    )

    $property = $Object.PSObject.Properties[$Name]

    if ($null -eq $property) {
        return $null
    }

    return $property.Value
}

# ------------------------------------------------------------
# DIRECTORIES
# ------------------------------------------------------------

New-Item -ItemType Directory -Path $RegistryDir -Force | Out-Null

# ------------------------------------------------------------
# GEMINI KEYS
# ------------------------------------------------------------

$keys = @()

foreach ($line in Get-Content -LiteralPath $SecretsFile) {

    if ($line -match '^\s*([^#=]+)\s*=(.*)$') {

        $name = $Matches[1].Trim()
        $value = $Matches[2].Trim()

        $isGemini = (
            ($name -match '^GEMINI_API_KEY_\d+$') -or
            ($name -eq 'GEMINI_API6')
        )

        if ($isGemini -and -not [string]::IsNullOrWhiteSpace($value)) {

            $keys += [PSCustomObject]@{
                Name  = $name
                Value = $value
            }
        }
    }
}

$keys = @(
    $keys |
    Sort-Object Name -Unique
)

if ($keys.Count -ne 6) {
    Fail "Gemini pool invalide : $($keys.Count)/6"
}

# ------------------------------------------------------------
# DISCOVERY
# ------------------------------------------------------------

$health = @()
$catalogs = @{}
$detailModels = $null

foreach ($key in $keys) {

    try {

        $response = Invoke-RestMethod `
            -Uri 'https://generativelanguage.googleapis.com/v1beta/models?pageSize=1000' `
            -Headers @{ 'x-goog-api-key' = $key.Value } `
            -Method Get `
            -TimeoutSec 30

        $models = @($response.models)

        if ($models.Count -eq 0) {
            throw 'models.list = 0'
        }

        $names = @(
            $models |
            ForEach-Object {
                ([string]$_.name -replace '^models/', '')
            } |
            Where-Object {
                -not [string]::IsNullOrWhiteSpace($_)
            } |
            Sort-Object -Unique
        )

        $generative = @(
            $models |
            Where-Object {
                @($_.supportedGenerationMethods) -contains 'generateContent'
            }
        )

        $catalogs[$key.Name] = $names

        if ($null -eq $detailModels) {
            $detailModels = @($models)
        }

        $health += [PSCustomObject]@{
            Name       = $key.Name
            Status     = 'OK'
            Models     = $models.Count
            Generative = $generative.Count
        }
    }
    catch {

        $health += [PSCustomObject]@{
            Name       = $key.Name
            Status     = 'FAILED'
            Models     = 0
            Generative = 0
        }
    }
}

$healthy = @(
    $health |
    Where-Object Status -eq 'OK'
)

if ($healthy.Count -ne 6) {
    Fail "Gemini pool unhealthy : $($healthy.Count)/6"
}

# ------------------------------------------------------------
# COMMON CATALOG
# ------------------------------------------------------------

$common = @(
    $catalogs[$healthy[0].Name]
)

foreach ($healthyKey in ($healthy | Select-Object -Skip 1)) {

    $currentSet = @(
        $catalogs[$healthyKey.Name]
    )

    $common = @(
        $common |
        Where-Object {
            $_ -in $currentSet
        }
    )
}

$common = @(
    $common |
    Sort-Object -Unique
)

if ($common.Count -eq 0) {
    Fail 'Aucun modèle commun aux 6 clés.'
}

# ------------------------------------------------------------
# MODEL SELECTION
# ------------------------------------------------------------

function Pick {
    param(
        [Parameter(Mandatory)]
        [string[]]$Candidates,

        [Parameter(Mandatory)]
        [string]$Role
    )

    foreach ($candidate in $Candidates) {
        if ($candidate -in $common) {
            return $candidate
        }
    }

    Fail "Aucun modèle commun pour $Role"
}

$primary = Pick @(
    'gemini-3.7-flash',
    'gemini-3.6-flash',
    'gemini-3.5-flash',
    'gemini-flash-latest'
) 'primary'

$fast = Pick @(
    'gemini-3.5-flash-lite',
    'gemini-3.1-flash-lite',
    'gemini-flash-lite-latest',
    'gemini-3.5-flash'
) 'fast'

$ultra = Pick @(
    'gemini-3.1-flash-lite',
    'gemini-3.5-flash-lite',
    'gemini-flash-lite-latest'
) 'ultra'

$pro = Pick @(
    'gemini-3.1-pro-preview',
    'gemini-3-pro-preview',
    'gemini-2.5-pro'
) 'escalation'

# ------------------------------------------------------------
# OLLAMA
# ------------------------------------------------------------

$ollamaRaw = @(
    ollama list 2>&1
)

if ($LASTEXITCODE -ne 0) {
    Fail 'ollama list a échoué.'
}

$ollamaInventory = @(
    $ollamaRaw |
    Select-Object -Skip 1 |
    ForEach-Object {
        $line = ([string]$_).Trim()

        if ($line) {
            $line
        }
    }
)

# ------------------------------------------------------------
# GEMINI RECORDS
# ------------------------------------------------------------

$geminiRecords = @(
    foreach ($model in $detailModels) {

        $name = ([string]$model.name -replace '^models/', '')
        $capabilities = [System.Collections.Generic.List[string]]::new()
        $lower = $name.ToLowerInvariant()

        $methods = @()
$methodsProperty = $model.PSObject.Properties['supportedGenerationMethods']
if ($null -ne $methodsProperty -and $null -ne $methodsProperty.Value) {
    $methods = @($methodsProperty.Value)
}

foreach ($method in $methods) {

            switch ([string]$method) {

                'generateContent' {
                    $capabilities.Add('chat')
                }

                'embedContent' {
                    $capabilities.Add('embedding')
                }

                'countTokens' {
                    $capabilities.Add('token_count')
                }
            }
        }

        $hasThinking = (
            $null -ne $model.PSObject.Properties['thinking'] -and
            $model.thinking -eq $true
        )

        if ($hasThinking) {
            $capabilities.Add('reasoning')
        }

        if ($lower -match 'flash|lite') {
            $capabilities.Add('fast')
        }

        if ($lower -match 'pro') {
            $capabilities.Add('deep_reasoning')
        }

        [ordered]@{
            name = $name
            display_name = Get-SafeProperty $model 'displayName'
            version = Get-SafeProperty $model 'version'
            input_token_limit = Get-SafeProperty $model 'inputTokenLimit'
            output_token_limit = Get-SafeProperty $model 'outputTokenLimit'
            thinking = Get-SafeProperty $model 'thinking'
            supported_generation_methods = @(
                $model.supportedGenerationMethods
            )
            common_to_all_six_keys = ($name -in $common)
            capabilities = @(
                $capabilities |
                Select-Object -Unique
            )
        }
    }
)

# ------------------------------------------------------------
# REGISTRY
# ------------------------------------------------------------

$registry = [ordered]@{
    schema_version = '5.2'

    generated_at = (
        Get-Date
    ).ToUniversalTime().ToString('o')

    secret_source = $SecretsFile

    gemini_pool = @(
        foreach ($item in $health) {

            [ordered]@{
                name = $item.Name
                status = $item.Status
                models = $item.Models
                generative_models = $item.Generative
            }
        }
    )

    availability = [ordered]@{
        healthy_keys = $healthy.Count
        total_keys = $keys.Count
        common_models = $common.Count
    }

    selected = [ordered]@{
        primary = @{
            provider = 'gemini'
            model = $primary
        }

        escalation = @{
            provider = 'gemini'
            model = $pro
        }

        fast_cloud = @{
            provider = 'gemini'
            model = $fast
        }

        ultra_fast_cloud = @{
            provider = 'gemini'
            model = $ultra
        }
    }

    common_gemini_models = $common

    ollama_inventory = $ollamaInventory

    gemini_models = $geminiRecords
}

# ------------------------------------------------------------
# ATOMIC WRITE
# ------------------------------------------------------------

$json = (
    $registry |
    ConvertTo-Json -Depth 20
)

$tempPath = "$RegistryPath.tmp"

Set-Content `
    -LiteralPath $tempPath `
    -Value $json `
    -Encoding UTF8

if (-not (Test-Path -LiteralPath $tempPath)) {
    Fail 'Fichier temporaire registre absent.'
}

Move-Item `
    -LiteralPath $tempPath `
    -Destination $RegistryPath `
    -Force

# ------------------------------------------------------------
# SELF-VALIDATION
# ------------------------------------------------------------

$loaded = (
    Get-Content `
        -LiteralPath $RegistryPath `
        -Raw |
    ConvertFrom-Json
)

if ($loaded.schema_version -ne '5.2') {
    Fail "Schema invalide : $($loaded.schema_version)"
}

if ($loaded.availability.healthy_keys -ne 6) {
    Fail 'Pool Gemini invalide après écriture.'
}

if ($loaded.availability.total_keys -ne 6) {
    Fail 'Nombre total de clés invalide.'
}

if ($loaded.selected.primary.model -ne $primary) {
    Fail 'Primary invalide après écriture.'
}

if ($loaded.selected.fast_cloud.model -ne $fast) {
    Fail 'Fast invalide après écriture.'
}

if ($loaded.selected.ultra_fast_cloud.model -ne $ultra) {
    Fail 'Ultra invalide après écriture.'
}

if ($loaded.selected.escalation.model -ne $pro) {
    Fail 'Escalation invalide après écriture.'
}

Write-Host ''
Write-Host '[OK] LLM registry refreshed.' -ForegroundColor Green
Write-Host "Healthy Gemini keys : $($healthy.Count)/6"
Write-Host "Common Gemini models: $($common.Count)"
Write-Host "Primary             : $primary"
Write-Host "Fast                : $fast"
Write-Host "Ultra               : $ultra"
Write-Host "Escalation          : $pro"
Write-Host "Schema              : $($loaded.schema_version)"
Write-Host "Registry            : $RegistryPath"




