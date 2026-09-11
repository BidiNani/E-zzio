param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("architect","lua","powershell","review","debug")]
    [string]$Agent,

    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Task
)

$ErrorActionPreference = "Stop"

$root = "G:\AI\E-zZIO"
$profileMap = @{
    architect  = "ezzio-architect.md"
    lua        = "lua-godot-coder.md"
    powershell = "powershell-automation.md"
    review     = "code-reviewer.md"
    debug      = "ezzio-debugger.md"
}

$profilePath = Join-Path $root "hermes-profiles\$($profileMap[$Agent])"

if (-not (Test-Path $profilePath)) {
    throw "Profil introuvable : $profilePath"
}

$taskText = ($Task -join " ").Trim()
if ([string]::IsNullOrWhiteSpace($taskText)) {
    $taskText = "Analyse le projet courant et demande-moi quelle tâche précise je veux effectuer."
}

$profileText = Get-Content -Path $profilePath -Raw
$prompt = @"
$profileText

Contexte de travail :
- Projet courant : G:\AI\E-zZIO
- N'affiche jamais les valeurs des fichiers .env, secrets ou tokens.
- Utilise des réponses concises.
- Avant toute modification, explique brièvement les fichiers qui seront touchés.

Tâche utilisateur :
$taskText
"@

Set-Location $root
hermes -z $prompt

