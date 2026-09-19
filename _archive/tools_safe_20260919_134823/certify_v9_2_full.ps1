$RootDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
& (Join-Path $RootDir ".venv\Scripts\python.exe") (Join-Path $RootDir "tools\certify_v9_2_full.py")
if ($LASTEXITCODE -ne 0) { exit 1 }