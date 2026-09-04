param (
    [switch]$SkipTests
)
$RootDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$argsList = @(Join-Path $RootDir "tools\verify_golden_release_v9_2.py")
if ($SkipTests) { $argsList += "--skip-tests" }
& (Join-Path $RootDir ".venv\Scripts\python.exe") $argsList
if ($LASTEXITCODE -ne 0) { exit 1 }