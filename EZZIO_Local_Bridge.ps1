<#
.SYNOPSIS
    E-zzio PowerShell Local AI Bridge
    Interroge directement Ollama en local via l'API OpenAI-compatible.
.PARAMETER Prompt
    La mission ou la question à envoyer au modèle.
.PARAMETER Model
    Le tag du modèle local à utiliser (ex: qwen2.5-coder:7b ou qwen3-coder:30b).
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$Prompt = "Génère un snippet d'initialisation pour le microkernel E-zzio.",

    [Parameter(Mandatory=$false)]
    [string]$Model = "qwen2.5-coder:7b",

    [string]$OllamaUri = "http://127.0.0.1:11434/v1/chat/completions"
)

# Configuration de l'encodage pour éviter les problèmes de caractères spéciaux
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$headers = @{
    "Content-Type"  = "application/json"
    "Authorization" = "Bearer ollama-local"
}

$bodyDictionary = @{
    model       = $Model
    messages    = @(
        @{ role = "system"; content = "Tu es le sous-système d'inférence local d'E-zzio. Réponds de manière technique et directe." },
        @{ role = "user"; content = $Prompt }
    )
    temperature = 0.1
}

$jsonBody = $bodyDictionary | ConvertTo-Json -Depth 10

Write-Host "[E-ZZIO] Transmission de la mission au modèle local [$Model]..." -ForegroundColor Cyan

try {
    $response = Invoke-RestMethod -Uri $OllamaUri -Method Post -Headers $headers -Body $jsonBody -ErrorAction Stop
    $resultText = $response.choices[0].message.content

    Write-Host "[E-ZZIO] Réponse validée." -ForegroundColor Green
    Write-Host "--------------------------------------------------"
    Write-Output $resultText
    Write-Host "--------------------------------------------------"

    # Sauvegarde automatique du livrable pour audit par le vérificateur V3
    $outputPath = "G:\AI\E-zzio\artifacts\latest_output.txt"
    $outputDir = [System.IO.Path]::GetDirectoryName($outputPath)
    if (!(Test-Path $outputDir)) { New-Item -ItemType Directory -Path $outputDir | Out-Null }
    
    $resultText | Out-File -FilePath $outputPath -Encoding utf8
    Write-Host "[E-ZZIO] Livrable stocké dans : $outputPath" -ForegroundColor Yellow

}
catch {
    Write-Error "[E-ZZIO] Échec de la communication avec le serveur local : $_"
    exit 1
}