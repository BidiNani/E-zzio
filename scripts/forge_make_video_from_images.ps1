param(
    [Parameter(Mandatory=$true)]
    [string]$InputFolder,

    [string]$OutputPath = "",

    [int]$Fps = 24,

    [int]$Crf = 18,

    [int]$Threads = 8,

    [switch]$Overwrite
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ProjectRoot = "G:\AI\E-zzio"
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$LogRoot = Join-Path $ProjectRoot "logs\video_from_images_$Stamp"
$OutRoot = Join-Path $ProjectRoot "forge\outputs\video"

New-Item -ItemType Directory -Force -Path $LogRoot, $OutRoot | Out-Null

$env:OLLAMA_NUM_GPU = "0"
$env:CUDA_VISIBLE_DEVICES = ""
$env:GGML_CUDA = "0"
$env:EZZIO_GPU_POLICY = "cpu_ram_only"
$env:EZZIO_NO_ADS = "true"
$env:EZZIO_NO_TRACKING = "true"
$env:EZZIO_NO_SPONSORS = "true"

if (-not (Test-Path -LiteralPath $InputFolder)) {
    throw "Dossier introuvable : $InputFolder"
}

$ffmpeg = Get-Command ffmpeg -ErrorAction SilentlyContinue
if (-not $ffmpeg) {
    throw "ffmpeg introuvable dans le PATH."
}

if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    $OutputPath = Join-Path $OutRoot "ezzio_video_$Stamp.mp4"
}

if ((Test-Path -LiteralPath $OutputPath) -and -not $Overwrite) {
    throw "Le fichier existe déjà : $OutputPath. Utilise -Overwrite."
}

$images = Get-ChildItem -LiteralPath $InputFolder -File |
    Where-Object { $_.Extension.ToLowerInvariant() -in @(".png", ".jpg", ".jpeg", ".webp") } |
    Sort-Object Name

if ($images.Count -lt 1) {
    throw "Aucune image trouvée dans : $InputFolder"
}

$listPath = Join-Path $LogRoot "ffmpeg_images.txt"
$listLines = foreach ($img in $images) {
    "file '$($img.FullName.Replace("'", "''"))'"
}

$listLines | Set-Content -LiteralPath $listPath -Encoding UTF8

$stdout = Join-Path $LogRoot "ffmpeg.stdout.log"
$stderr = Join-Path $LogRoot "ffmpeg.stderr.log"

$args = @(
    "-y",
    "-r", "$Fps",
    "-f", "concat",
    "-safe", "0",
    "-i", $listPath,
    "-c:v", "libx264",
    "-preset", "medium",
    "-crf", "$Crf",
    "-pix_fmt", "yuv420p",
    "-threads", "$Threads",
    $OutputPath
)

$process = Start-Process `
    -FilePath $ffmpeg.Source `
    -ArgumentList $args `
    -NoNewWindow `
    -PassThru `
    -Wait `
    -RedirectStandardOutput $stdout `
    -RedirectStandardError $stderr

if ($process.ExitCode -ne 0) {
    Get-Content -LiteralPath $stderr -Tail 80 -ErrorAction SilentlyContinue
    throw "ffmpeg a échoué avec ExitCode=$($process.ExitCode)"
}

$report = [ordered]@{
    ok = $true
    created_at = (Get-Date).ToString("s")
    input_folder = $InputFolder
    output_path = $OutputPath
    image_count = $images.Count
    fps = $Fps
    crf = $Crf
    threads = $Threads
    logs = $LogRoot
    gpu_policy = "cpu_ram_only"
    no_ads = $true
}

$reportPath = Join-Path $LogRoot "video_report.json"
$report | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $reportPath -Encoding UTF8

[pscustomobject]$report
