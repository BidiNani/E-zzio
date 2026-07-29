$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ExternalRoot = "G:\AI\external"
$ComfyRoot = Join-Path $ExternalRoot "ComfyUI"

$env:CUDA_VISIBLE_DEVICES = ""
$env:CUDA_DEVICE_ORDER = "PCI_BUS_ID"
$env:OLLAMA_NUM_GPU = "0"
$env:GGML_CUDA = "0"
$env:EZZIO_GPU_POLICY = "cpu_ram_only"
$env:EZZIO_NUM_GPU = "0"
$env:PYTORCH_ENABLE_MPS_FALLBACK = "0"

New-Item -ItemType Directory -Force -Path $ExternalRoot | Out-Null

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "git introuvable. Installe Git for Windows, ferme/réouvre PowerShell, puis relance."
}

if (-not (Test-Path -LiteralPath $ComfyRoot)) {
    git clone https://github.com/Comfy-Org/ComfyUI.git $ComfyRoot
}
else {
    Set-Location -LiteralPath $ComfyRoot
    git pull
}

Set-Location -LiteralPath $ComfyRoot

if (-not (Test-Path -LiteralPath ".venv")) {
    py -3.11 -m venv .venv
}

$Py = Join-Path $ComfyRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $Py)) {
    throw "Venv Python ComfyUI introuvable : $Py"
}

& $Py -m pip install --upgrade pip setuptools wheel
& $Py -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
& $Py -m pip install -r requirements.txt

Write-Host ""
Write-Host "✅ ComfyUI CPU prêt : $ComfyRoot" -ForegroundColor Green
