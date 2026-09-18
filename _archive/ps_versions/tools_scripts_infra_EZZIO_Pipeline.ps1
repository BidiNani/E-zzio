<#
.SYNOPSIS
    E-zzio Master Pipeline V3
    Enchaîne la génération locale (Ollama) et l'audit forensique de sécurité.
.PARAMETER Prompt
    La mission ou la requête technique à traiter.
.PARAMETER Model
    Le modèle local à solliciter (ex: qwen2.5-coder:7b ou qwen3-coder:30b).
.PARAMETER TargetDir
    Le répertoire cible où appliquer ou auditer les modifications.
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$Prompt,

    [Parameter(Mandatory=$false)]
    [string]$Model = "qwen2.5-coder:7b",

    [Parameter(Mandatory=$false)]
    [string]$TargetDir = "G:\AI\E-zzio\projects\default"
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "[E-ZZIO PIPELINE] Étape 1 : Production locale ($Model)" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

$OllamaUri = "http://127.0.0.1:11434/v1/chat/completions"
$headers = @{
    "Content-Type"  = "application/json"
    "Authorization" = "Bearer ollama-local"
}

$bodyDictionary = @{
    model       = $Model
    messages    = @(
        @{ role = "system"; content = "Tu es le sous-système de production d'E-zzio. Fournis du code propre, typé et sans fioriture." },
        @{ role = "user"; content = $Prompt }
    )
    temperature = 0.1
}

$jsonBody = $bodyDictionary | ConvertTo-Json -Depth 10

try {
    $response = Invoke-RestMethod -Uri $OllamaUri -Method Post -Headers $headers -Body $jsonBody -ErrorAction Stop
    $resultText = $response.choices[0].message.content

    # Stockage de l'artéfact brut
    $artifactPath = "G:\AI\E-zzio\artifacts\latest_output.txt"
    $outputDir = [System.IO.Path]::GetDirectoryName($artifactPath)
    if (!(Test-Path $outputDir)) { New-Item -ItemType Directory -Path $outputDir | Out-Null }
    
    $resultText | Out-File -FilePath $artifactPath -Encoding utf8
    Write-Host "[SUCCESS] Livrable généré et stocké dans : $artifactPath" -ForegroundColor Green
}
catch {
    Write-Error "[CRITICAL] Échec de la génération locale : $_"
    exit 1
}

Write-Host "`n==================================================" -ForegroundColor Cyan
Write-Host "[E-ZZIO PIPELINE] Étape 2 : Arbitrage & Audit Forensique V3" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

$orchestratorPath = "G:\AI\E-zzio\EZZIO_Master_Orchestrator_V3.ps1"

if (Test-Path $orchestratorPath) {
    # Appel de l'orchestrateur de sécurité existant
    pwsh -File $orchestratorPath -Target $TargetDir
} else {
    Write-Host "[WARNING] L'orchestrateur V3 n'a pas été trouvé à l'emplacement : $orchestratorPath" -ForegroundColor Yellow
    Write-Host "[INFO] Fin du pipeline avec succès (Génération seule validée)." -ForegroundColor Green
}