$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ProjectRoot = "G:\AI\E-zzio"
$UiRoot = Join-Path $ProjectRoot "ezzio-ui"

if (-not (Test-Path -LiteralPath (Join-Path $UiRoot "package.json"))) {
    throw "package.json introuvable dans $UiRoot"
}

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw "npm introuvable. Installe Node.js LTS."
}

$env:CUDA_VISIBLE_DEVICES = ""
$env:OLLAMA_NUM_GPU = "0"
$env:GGML_CUDA = "0"
$env:EZZIO_GPU_POLICY = "cpu_ram_only"
$env:EZZIO_NUM_GPU = "0"

Set-Location -LiteralPath $UiRoot

npm install
npm install @capacitor/core @capacitor/cli @capacitor/android --save-dev

if (-not (Test-Path -LiteralPath "capacitor.config.ts")) {
    npx cap init E-ZZIO com.ezzio.local --web-dir build
}

Write-Host "✅ Capacitor prêt côté UI." -ForegroundColor Green
