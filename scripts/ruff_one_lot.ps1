# ruff_one_lot.ps1
param(
    [Parameter(Mandatory=$true)][string]$Select,
    [string]$Name = "",
    [switch]$UnsafeFix,
    [switch]$NoFix
)

$Py         = "G:\AI\E-zzio\.venv\Scripts\python.exe"
$Root       = "G:\AI\E-zzio"
$AstChecker = "G:\AI\E-zzio\scripts\_ast_check.py"
Set-Location $Root

if (-not $Name) { $Name = $Select }

$Stamp  = Get-Date -Format "yyyyMMdd_HHmmss"
$LogDir = "$Root\state\ruff_logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$Log = Join-Path $LogDir "$Stamp`_$Select.log"

function Log {
    param([string]$Msg, [string]$Color = "Gray")
    $line = "[$(Get-Date -Format 'HH:mm:ss')] $Msg"
    Add-Content -Path $Log -Value $line -Encoding UTF8
    Write-Host $line -ForegroundColor $Color
}

Log "=== LOT $Name (select=$Select) ===" "Cyan"

function Get-RuffCount {
    param([string]$Sel)
    $tmp = [System.IO.Path]::GetTempFileName()
    try {
        & $Py -m ruff check . --select $Sel --output-format=json --no-cache 2>$null |
            Set-Content -Path $tmp -Encoding UTF8
        $raw = Get-Content -Path $tmp -Raw -ErrorAction SilentlyContinue
        if (-not $raw -or $raw.Trim() -eq "[]" -or $raw.Trim() -eq "") { return 0 }
        $arr = $raw | ConvertFrom-Json
        return @($arr).Count
    } finally {
        Remove-Item $tmp -Force -ErrorAction SilentlyContinue
    }
}

$before = Get-RuffCount -Sel $Select
Log "Violations avant : $before"

if ($before -eq 0) {
    Log "Rien a faire." "DarkGray"
    exit 0
}

if ($NoFix) {
    Log "Detection seule." "Magenta"
    & $Py -m ruff check . --select $Select --output-format=concise --no-cache 2>&1 |
        Select-Object -First 30 |
        ForEach-Object { Add-Content -Path $Log -Value $_ -Encoding UTF8; Write-Host $_ }
    Log "Tronque a 30 lignes. Log : $Log"
    exit 0
}

$dirty = git status --porcelain
if ($dirty) {
    Log "Repo pas propre, commit securite..." "Yellow"
    git add -A
    git commit -m "wip: pre-ruff-$Select-$Stamp" 2>&1 | Out-Null
}

$fixArgs = @("-m","ruff","check",".","--select",$Select,"--fix","--no-cache","--quiet")
if ($UnsafeFix) { $fixArgs += "--unsafe-fixes" }
Log "ruff $($fixArgs -join ' ')"
& $Py @fixArgs 2>&1 | ForEach-Object { Add-Content -Path $Log -Value $_ -Encoding UTF8 }

Log "Verification AST..."
$astOut = & $Py $AstChecker 2>&1
$astOut | ForEach-Object { Add-Content -Path $Log -Value $_ -Encoding UTF8 }

if ($LASTEXITCODE -ne 0) {
    Log "AST CASSE - rollback" "Red"
    git checkout -- . 2>&1 | Out-Null
    exit 1
}
Log "AST OK" "Green"

$after = Get-RuffCount -Sel $Select
Log "Violations apres : $after (avant: $before)"

Log "pytest..."
$pytestOut = & $Py -m pytest tests/ -q --tb=line --no-header -x 2>&1
$pytestOut | Select-Object -Last 15 | ForEach-Object { Add-Content -Path $Log -Value $_ -Encoding UTF8; Write-Host $_ }

if ($LASTEXITCODE -ne 0) {
    Log "TESTS CASSES - rollback" "Red"
    git checkout -- . 2>&1 | Out-Null
    exit 1
}

git add -A
git commit -m "chore(ruff): $Name ($Select) [auto]" 2>&1 | Out-Null
Log "=== LOT TERMINE : $Name ===" "Green"
Log "Log : $Log" "DarkGray"
