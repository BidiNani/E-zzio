$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ComfyRoot = "G:\AI\external\ComfyUI"
$CheckpointRoot = Join-Path $ComfyRoot "models\checkpoints"
$VaeRoot = Join-Path $ComfyRoot "models\vae"
$LoraRoot = Join-Path $ComfyRoot "models\loras"
$OutputRoot = Join-Path $ComfyRoot "output"

New-Item -ItemType Directory -Force -Path $CheckpointRoot, $VaeRoot, $LoraRoot, $OutputRoot | Out-Null

function Get-Files {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) { return @() }

    Get-ChildItem -LiteralPath $Path -File -ErrorAction SilentlyContinue |
        Where-Object { $_.Extension -in ".safetensors", ".ckpt", ".pt", ".pth" } |
        Select-Object Name, @{Name="GB";Expression={[math]::Round($_.Length / 1GB, 2)}}, LastWriteTime, FullName
}

[pscustomobject]@{
    ComfyRoot = $ComfyRoot
    Output = $OutputRoot
    CheckpointsPath = $CheckpointRoot
    VaePath = $VaeRoot
    LoraPath = $LoraRoot
    Checkpoints = @(Get-Files $CheckpointRoot)
    Vae = @(Get-Files $VaeRoot)
    Loras = @(Get-Files $LoraRoot)
    Policy = "CPU/RAM only"
}
