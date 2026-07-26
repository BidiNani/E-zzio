$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ComfyRoot = "G:\AI\external\ComfyUI"
$CheckpointRoot = Join-Path $ComfyRoot "models\checkpoints"
$ModelFile = "DreamShaper_8_pruned.safetensors"
$ModelUrl = "https://huggingface.co/Lykon/DreamShaper/resolve/main/DreamShaper_8_pruned.safetensors"
$ModelPath = Join-Path $CheckpointRoot $ModelFile

New-Item -ItemType Directory -Force -Path $CheckpointRoot | Out-Null

if (Test-Path -LiteralPath $ModelPath) {
    $size = (Get-Item -LiteralPath $ModelPath).Length
    if ($size -gt 100MB) {
        Write-Host "[OK] Modèle déjà présent : $ModelPath" -ForegroundColor Green
        Get-Item -LiteralPath $ModelPath | Select-Object FullName, @{Name="GB";Expression={[math]::Round($_.Length / 1GB, 2)}}, LastWriteTime
        return
    }
    Remove-Item -LiteralPath $ModelPath -Force
}

$Partial = "$ModelPath.partial"
if (Test-Path -LiteralPath $Partial) {
    Remove-Item -LiteralPath $Partial -Force
}

Write-Host "[DOWNLOAD] DreamShaper 8 SD1.5 CPU-friendly" -ForegroundColor Cyan

try {
    Start-BitsTransfer -Source $ModelUrl -Destination $Partial -Description "E-ZZIO DreamShaper8" -ErrorAction Stop
}
catch {
    Write-Warning "BITS échoué, fallback Invoke-WebRequest : $($_.Exception.Message)"
    Invoke-WebRequest `
        -Uri $ModelUrl `
        -OutFile $Partial `
        -UseBasicParsing `
        -Headers @{ "User-Agent" = "E-ZZIO-model-vault" } `
        -TimeoutSec 7200
}

$size = (Get-Item -LiteralPath $Partial).Length
if ($size -lt 100MB) {
    throw "Fichier trop petit. Hugging Face a probablement renvoyé une page d'erreur."
}

Move-Item -LiteralPath $Partial -Destination $ModelPath -Force

Get-Item -LiteralPath $ModelPath |
    Select-Object FullName, @{Name="GB";Expression={[math]::Round($_.Length / 1GB, 2)}}, LastWriteTime
