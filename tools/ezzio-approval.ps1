<#
.SYNOPSIS
    Wrapper PowerShell pour le CLI HITL Approval d'E-ZZIO.
.DESCRIPTION
    Transmet les commandes au script Python canonique tools/ezzio_approval.py
    en utilisant l'interpréteur .venv de production.
#>
param (
    [Parameter(Position=0, Mandatory=$true)]
    [ValidateSet("list", "approve", "reject")]
    [string]$Command,

    [Parameter(Position=1, Mandatory=$false)]
    [string]$ApprovalId,

    [Parameter(Mandatory=$false)]
    [string]$Reason,

    [Parameter(Mandatory=$false)]
    [string]$By = "powershell_operator"
)

$PythonExe = Join-Path $PSScriptRoot "..\.venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    $PythonExe = "python"
}

$CliPy = Join-Path $PSScriptRoot "ezzio_approval.py"

$ArgsList = @($CliPy, $Command)
if ($ApprovalId) {
    $ArgsList += $ApprovalId
}
if ($Reason) {
    $ArgsList += @("--reason", $Reason)
}
if ($By) {
    $ArgsList += @("--by", $By)
}

& $PythonExe @ArgsList
exit $LASTEXITCODE
