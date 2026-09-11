$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# ============================================================
# E-ZZIO ComfyUI CPU Installer
# Fonctionne avec Git si disponible, sinon archive ZIP GitHub.
# CPU/RAM only strict.
# ============================================================

$ExternalRoot = "G:\AI\external"
$ComfyRoot    = Join-Path $ExternalRoot "ComfyUI"
$TempRoot     = Join-Path $ExternalRoot "_tmp_comfyui_install"
$ZipPath      = Join-Path $TempRoot "ComfyUI.zip"

$env:CUDA_VISIBLE_DEVICES = ""
$env:CUDA_DEVICE_ORDER = "PCI_BUS_ID"
$env:OLLAMA_NUM_GPU = "0"
$env:GGML_CUDA = "0"
$env:EZZIO_GPU_POLICY = "cpu_ram_only"
$env:EZZIO_NUM_GPU = "0"
$env:PYTORCH_ENABLE_MPS_FALLBACK = "0"

function Ensure-Dir {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Force -Path $Path | Out-Null
    }
}

function Test-Cmd {
    param([string]$Name)
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Download-File {
    param([string]$Url, [string]$OutFile)

    Invoke-WebRequest `
        -Uri $Url `
        -OutFile $OutFile `
        -UseBasicParsing `
        -Headers @{ "User-Agent" = "E-ZZIO-local-installer" } `
        -TimeoutSec 300
}

Ensure-Dir $ExternalRoot
Ensure-Dir $TempRoot

Write-Host ""
Write-Host "=== INSTALL COMFYUI CPU-ONLY ===" -ForegroundColor Cyan
Write-Host "ComfyRoot : $ComfyRoot"
Write-Host ""

if (Test-Cmd "git") {
    Write-Host "[MODE] Git disponible." -ForegroundColor Green

    if (-not (Test-Path -LiteralPath $ComfyRoot)) {
        git clone https://github.com/Comfy-Org/ComfyUI.git $ComfyRoot
    }
    else {
        Set-Location -LiteralPath $ComfyRoot
        git pull
    }
}
else {
    Write-Host "[MODE] Git absent. Installation via ZIP GitHub." -ForegroundColor Yellow

    $RepoApi = "https://api.github.com/repos/Comfy-Org/ComfyUI"
    $Repo = Invoke-RestMethod `
        -Uri $RepoApi `
        -Headers @{ "User-Agent" = "E-ZZIO-local-installer" } `
        -TimeoutSec 60

    $DefaultBranch = $Repo.default_branch
    if ([string]::IsNullOrWhiteSpace($DefaultBranch)) {
        $DefaultBranch = "master"
    }

    $ZipUrl = "https://codeload.github.com/Comfy-Org/ComfyUI/zip/refs/heads/$DefaultBranch"

    if (Test-Path -LiteralPath $ZipPath) {
        Remove-Item -LiteralPath $ZipPath -Force
    }

    Download-File -Url $ZipUrl -OutFile $ZipPath

    if (Test-Path -LiteralPath $TempRoot) {
        Get-ChildItem -LiteralPath $TempRoot -Directory -Filter "ComfyUI-*" -ErrorAction SilentlyContinue |
            Remove-Item -Recurse -Force
    }

    Expand-Archive -LiteralPath $ZipPath -DestinationPath $TempRoot -Force

    $Expanded = Get-ChildItem -LiteralPath $TempRoot -Directory -Filter "ComfyUI-*" |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    if (-not $Expanded) {
        throw "Archive ComfyUI extraite introuvable."
    }

    if (Test-Path -LiteralPath $ComfyRoot) {
        $Backup = "$ComfyRoot.backup_$(Get-Date -Format yyyyMMdd_HHmmss)"
        Write-Host "[BACKUP] Ancien ComfyUI -> $Backup" -ForegroundColor Yellow
        Move-Item -LiteralPath $ComfyRoot -Destination $Backup -Force
    }

    Move-Item -LiteralPath $Expanded.FullName -Destination $ComfyRoot -Force
}

Set-Location -LiteralPath $ComfyRoot

if (-not (Test-Path -LiteralPath ".venv")) {
    Write-Host "[VENV] Création .venv..." -ForegroundColor Cyan

    if (Get-Command py -ErrorAction SilentlyContinue) {
        py -3.11 -m venv .venv
    }
    else {
        python -m venv .venv
    }
}

$Py = Join-Path $ComfyRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $Py)) {
    throw "Venv Python ComfyUI introuvable : $Py"
}

Write-Host "[PIP] Mise à jour pip..."
& $Py -m pip install --upgrade pip setuptools wheel

Write-Host "[TORCH] Installation PyTorch CPU-only..."
& $Py -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

Write-Host "[REQ] Installation requirements ComfyUI..."
& $Py -m pip install -r requirements.txt

$ModelsRoot = Join-Path $ComfyRoot "models"
$CheckpointsRoot = Join-Path $ModelsRoot "checkpoints"
$VaeRoot = Join-Path $ModelsRoot "vae"
$LorasRoot = Join-Path $ModelsRoot "loras"

Ensure-Dir $CheckpointsRoot
Ensure-Dir $VaeRoot
Ensure-Dir $LorasRoot

$Readme = Join-Path $ComfyRoot "EZZIO_CPU_ONLY_README.txt"
@"
E-ZZIO ComfyUI CPU/RAM only

ComfyUI est installé ici :
$ComfyRoot

Lancement :
G:\AI\E-zzio\scripts\start_comfyui_cpu_safe.ps1

Politique :
- CUDA_VISIBLE_DEVICES vide
- --cpu forcé
- Ollama reste num_gpu=0
- GPU non utilisé

Important :
ComfyUI est installé, mais les modèles image/checkpoints ne sont pas inclus automatiquement.
Place les checkpoints dans :
$CheckpointsRoot
"@ | Set-Content -LiteralPath $Readme -Encoding UTF8

Write-Host ""
Write-Host "✅ ComfyUI CPU installé/prêt." -ForegroundColor Green
Write-Host "Root        : $ComfyRoot"
Write-Host "Python      : $Py"
Write-Host "Checkpoints : $CheckpointsRoot"
Write-Host ""
