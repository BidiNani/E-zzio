$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

param(
    [Parameter(Mandatory=$true)]
    [string]$FramesFolder,

    [int]$Fps = 8,

    [string]$OutputName = "ezzio_video_cpu.mp4"
)

$ProjectRoot = "G:\AI\E-zzio"
$OutputRoot = Join-Path $ProjectRoot "forge\outputs\video"
New-Item -ItemType Directory -Force -Path $OutputRoot | Out-Null

$env:CUDA_VISIBLE_DEVICES = ""
$env:OLLAMA_NUM_GPU = "0"
$env:GGML_CUDA = "0"
$env:EZZIO_GPU_POLICY = "cpu_ram_only"
$env:EZZIO_NUM_GPU = "0"

if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    throw "ffmpeg introuvable dans le PATH."
}

$OutputPath = Join-Path $OutputRoot $OutputName

ffmpeg -y `
    -framerate $Fps `
    -pattern_type glob `
    -i "$FramesFolder\*.png" `
    -c:v libx264 `
    -preset veryfast `
    -crf 23 `
    -pix_fmt yuv420p `
    $OutputPath

Write-Host "✅ Vidéo CPU créée : $OutputPath" -ForegroundColor Green
