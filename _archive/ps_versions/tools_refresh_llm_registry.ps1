#requires -Version 7.0
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$EzzioHome = 'G:\AI\E-zzio'
$EnvFile = Join-Path $EzzioHome '.env'
$RegistryDir = Join-Path $EzzioHome 'state\audit\current\capability_registry'
$RegistryPath = Join-Path $RegistryDir 'llm_capability_registry.json'
$Stamp = Get-Date -Format 'yyyyMMdd-HHmmss'

New-Item -ItemType Directory -Path $RegistryDir -Force | Out-Null

$line = Get-Content $EnvFile |
    Where-Object { $_ -match '^GEMINI_API_KEY=' } |
    Select-Object -First 1

if (-not $line) {
    throw 'GEMINI_API_KEY absent.'
}

$key = ($line -split '=', 2)[1].Trim()

$headers = @{
    'x-goog-api-key' = $key
}

$gemini = Invoke-RestMethod `
    -Uri 'https://generativelanguage.googleapis.com/v1beta/models?pageSize=1000' `
    -Headers $headers `
    -Method Get `
    -TimeoutSec 30

$ollamaRaw = @(ollama list 2>&1)

if ($LASTEXITCODE -ne 0) {
    throw 'ollama list a échoué.'
}

$ollama = @()

foreach ($line in ($ollamaRaw | Select-Object -Skip 1)) {
    $parts = ([string]$line) -split '\s{2,}'
    if ($parts.Count -ge 4) {
        $ollama += [ordered]@{
            name = $parts[0].Trim()
            id = $parts[1].Trim()
            size = $parts[2].Trim()
            modified = $parts[3].Trim()
        }
    }
}

$geminiNames = @(
    $gemini.models |
        ForEach-Object { ([string]$_.name -replace '^models/', '') }
)

function Pick([string[]]$candidates, [string]$role) {
    foreach ($c in $candidates) {
        if ($geminiNames -contains $c) {
            return $c
        }
    }
    throw "Aucun Gemini pour $role."
}

function PickO([string[]]$candidates, [string]$role) {
    $names = @($ollama | ForEach-Object { $_.name })
    foreach ($c in $candidates) {
        if ($names -contains $c) {
            return $c
        }
    }
    throw "Aucun Ollama pour $role."
}

$primary = Pick @('gemini-3.7-flash') 'primary'
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

$localGeneral = PickO @('qwen3.5:9b') 'local_general'
$localAgent = PickO @('hermes3:8b','nemotron-3-nano:4b') 'local_agent'
$localFast = PickO @('nemotron-3-nano:4b','phi4-mini:latest') 'local_fast'
$localReason = PickO @('phi4-mini:latest','nemotron-3-nano:4b') 'local_reasoning'
$emb1 = PickO @('bge-m3:latest','nomic-embed-text:latest') 'embedding_primary'
$emb2 = PickO @('nomic-embed-text:latest','bge-m3:latest') 'embedding_secondary'

$record = [ordered]@{
    schema_version = '2.0'
    generated_at = (Get-Date).ToUniversalTime().ToString('o')

    selected = [ordered]@{
        primary = @{ provider='gemini'; model=$primary }
        escalation = @{ provider='gemini'; model=$pro }
        fast_cloud = @{ provider='gemini'; model=$fast }
        ultra_fast_cloud = @{ provider='gemini'; model=$ultra }

        local_general = @{ provider='ollama'; model=$localGeneral }
        local_agent = @{ provider='ollama'; model=$localAgent }
        local_fast_agent = @{ provider='ollama'; model=$localFast }
        local_reasoning = @{ provider='ollama'; model=$localReason }

        embedding_primary = @{ provider='ollama'; model=$emb1 }
        embedding_secondary = @{ provider='ollama'; model=$emb2 }
    }

    available_gemini = $geminiNames
    available_ollama = @($ollama | ForEach-Object { $_.name })

    functions = [ordered]@{
        main_agent = @($primary,$localGeneral,$localAgent)
        coding = @($primary,$localGeneral,$localAgent)
        complex_reasoning = @($pro,$primary,$localReason)
        fast_tasks = @($fast,$ultra,$localFast)
        vision = @($primary,$localGeneral)
        tool_use = @($primary,$localGeneral,$localAgent,$localFast)
        compression = @($fast,$ultra,$localFast)
        memory_rewrite = @($ultra,$localFast,$localReason)
        embeddings = @($emb1,$emb2)
    }
}

$record |
    ConvertTo-Json -Depth 16 |
    Set-Content -Path $RegistryPath -Encoding UTF8

Write-Host "[OK] Registry refreshed: $RegistryPath"
Write-Host "[OK] Gemini models: $($geminiNames.Count)"
Write-Host "[OK] Ollama models: $($ollama.Count)"
