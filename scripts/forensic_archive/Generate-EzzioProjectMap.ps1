#requires -Version 5.1

[CmdletBinding()]
param(
    [string]$ProjectRoot = "G:\AI\E-zzio",
    [string]$OutputFile = "",
    [int]$MaxFileSizeMB = 10,
    [switch]$RunTests
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"

$ExcludedDirectories = @(
    ".git", ".hg", ".svn", "node_modules", "__pycache__",
    ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox",
    ".venv", "venv", "env", "dist", "build", "coverage",
    ".idea", ".vscode", "target", "bin", "obj"
)

$AllowedExtensions = @(
    ".py", ".pyi", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs",
    ".java", ".cs", ".ps1", ".sh", ".yaml", ".yml", ".json",
    ".toml", ".ini", ".cfg", ".md", ".txt"
)

$ProviderTerms = @(
    "ollama", "gemini", "openai", "anthropic", "mistral",
    "provider", "modelrouter", "model_router"
)

$KernelTerms = @(
    "kernel", "context", "policy", "budget", "execution",
    "executor", "capability", "permission", "sandbox", "guardian"
)

$MemoryTerms = @(
    "memory", "retrieval", "embedding", "vector", "decision"
)

$LedgerTerms = @(
    "ledger", "audit", "hmac", "sha256", "sha-256", "integrity",
    "sequence", "atomic", "recovery", "fail_closed", "fail-closed"
)

$RealtimeTerms = @(
    "pipecat", "livekit", "stt", "tts", "realtime", "websocket", "voice"
)

function Get-RelativePath {
    param(
        [string]$BasePath,
        [string]$TargetPath
    )

    $BaseFull = [System.IO.Path]::GetFullPath($BasePath)
    $TargetFull = [System.IO.Path]::GetFullPath($TargetPath)

    if (-not $BaseFull.EndsWith("\")) {
        $BaseFull = $BaseFull + "\"
    }

    $BaseUri = New-Object System.Uri($BaseFull)
    $TargetUri = New-Object System.Uri($TargetFull)
    $RelativeUri = $BaseUri.MakeRelativeUri($TargetUri)

    return [System.Uri]::UnescapeDataString(
        $RelativeUri.ToString()
    ).Replace("/", "\")
}

function Test-Term {
    param(
        [string]$Text,
        [string[]]$Terms
    )

    if ($null -eq $Text) {
        return $false
    }

    $LowerText = $Text.ToLowerInvariant()

    foreach ($Term in $Terms) {
        if ($LowerText.Contains($Term.ToLowerInvariant())) {
            return $true
        }
    }

    return $false
}

function Get-Category {
    param(
        [string]$Path,
        [string]$Content
    )

    $Relative = Get-RelativePath $ProjectRoot $Path
    $Combined = $Relative + "`n" + $Content

    if (Test-Term $Combined $ProviderTerms) {
        return "MODEL ROUTER / PROVIDERS"
    }

    if (Test-Term $Combined $RealtimeTerms) {
        return "REALTIME"
    }

    if (Test-Term $Combined $LedgerTerms) {
        return "LEDGER / AUDIT / FORENSICS"
    }

    if (Test-Term $Combined $MemoryTerms) {
        return "MEMORY / CONTEXT"
    }

    if (Test-Term $Combined $KernelTerms) {
        return "CORE / KERNEL / EXECUTION"
    }

    if ($Relative -match "test|spec|chaos|adversarial|certif|quality") {
        return "TESTING / CERTIFICATION"
    }

    if ($Relative -match "tool|filesystem|executor|sandbox|plugin") {
        return "TOOLS / EXECUTION"
    }

    if ($Relative -match "audit|forensic|inventory|inspect") {
        return "AUDIT / FORENSICS"
    }

    return "OTHER"
}

function Get-Status {
    param(
        [string]$Path,
        [string]$Content,
        [bool]$IsTest
    )

    $Name = [System.IO.Path]::GetFileName($Path)
    $Lower = $Content.ToLowerInvariant()

    if ($Name -match "legacy|deprecated|archive|old") {
        return "LEGACY"
    }

    if ($Lower -match "experimental|prototype|proof.of.concept|poc") {
        return "EXPERIMENTAL"
    }

    if ($Lower -match "planned|not implemented|todo|fixme|future work") {
        return "PARTIAL"
    }

    return "REAL"
}

function Get-Matches {
    param(
        [string]$Content,
        [string[]]$Patterns
    )

    $Results = New-Object System.Collections.Generic.List[string]
    $Lines = $Content -split "`r?`n"

    for ($Index = 0; $Index -lt $Lines.Count; $Index++) {
        $Line = $Lines[$Index]

        foreach ($Pattern in $Patterns) {
            if ($Line -match $Pattern) {
                $Preview = $Line.Trim()

                if ($Preview.Length -gt 180) {
                    $Preview = $Preview.Substring(0, 180) + "..."
                }

                $Results.Add(
                    ("line " + ($Index + 1) + ": " + $Preview)
                )

                break
            }
        }
    }

    return @($Results)
}

function Get-Symbols {
    param(
        [string]$Content,
        [string]$Extension
    )

    $Results = New-Object System.Collections.Generic.List[string]
    $Lines = $Content -split "`r?`n"

    for ($Index = 0; $Index -lt $Lines.Count; $Index++) {
        $Line = $Lines[$Index]

        if ($Extension -eq ".py" -or $Extension -eq ".pyi") {
            if ($Line -match "^\s*(class|def|async\s+def)\s+([A-Za-z_][A-Za-z0-9_]*)") {
                $Results.Add(
                    (($Index + 1).ToString() + ":" + $Matches[2])
                )
            }
        }
        elseif ($Extension -eq ".ts" -or $Extension -eq ".tsx" -or $Extension -eq ".js" -or $Extension -eq ".jsx") {
            if ($Line -match "^\s*(export\s+)?(default\s+)?(class|function|async\s+function)\s+([A-Za-z_][A-Za-z0-9_]*)") {
                $Results.Add(
                    (($Index + 1).ToString() + ":" + $Matches[4])
                )
            }
        }
        elseif ($Extension -eq ".go") {
            if ($Line -match "^\s*func\s+([A-Za-z_][A-Za-z0-9_]*)") {
                $Results.Add(
                    (($Index + 1).ToString() + ":" + $Matches[1])
                )
            }
        }
        elseif ($Extension -eq ".rs") {
            if ($Line -match "^\s*(pub\s+)?(async\s+)?fn\s+([A-Za-z_][A-Za-z0-9_]*)") {
                $Results.Add(
                    (($Index + 1).ToString() + ":" + $Matches[3])
                )
            }
        }
        elseif ($Extension -eq ".ps1") {
            if ($Line -match "^\s*function\s+([A-Za-z_][A-Za-z0-9_-]*)") {
                $Results.Add(
                    (($Index + 1).ToString() + ":" + $Matches[1])
                )
            }
        }
    }

    return @($Results)
}

function Add-Row {
    param(
        [System.Collections.Generic.List[string]]$List,
        [string[]]$Values
    )

    $CleanValues = New-Object System.Collections.Generic.List[string]

    foreach ($Value in $Values) {
        $Text = ""

        if ($null -ne $Value) {
            $Text = [string]$Value
        }

        $Text = $Text.Replace("|", "\|")
        $Text = $Text.Replace("`r", " ")
        $Text = $Text.Replace("`n", " ")

        $CleanValues.Add($Text)
    }

    $List.Add("| " + ($CleanValues -join " | ") + " |")
}

# ============================================================
# VALIDATION
# ============================================================

if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) {
    Write-Host "Projet introuvable : $ProjectRoot" -ForegroundColor Red
    Read-Host "Appuie sur Entree pour fermer"
    exit 1
}

$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)

if ([string]::IsNullOrWhiteSpace($OutputFile)) {
    $OutputFile = Join-Path $ProjectRoot "E-ZZIO_PROJECT_MAP.md"
}

$OutputFile = [System.IO.Path]::GetFullPath($OutputFile)

Write-Host "Analyse de E-ZZIO..." -ForegroundColor Cyan
Write-Host ("Racine : " + $ProjectRoot) -ForegroundColor Gray
Write-Host ""

# ============================================================
# COLLECTE
# ============================================================