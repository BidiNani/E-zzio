# ==============================================================================
# E-ZZIO V48.23 — ADAPTER RUNTIME COMPATIBILITY CERTIFICATION
# HARDENED 10/10
# READ ONLY / ZERO MUTATION
# ==============================================================================

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

Set-Location "G:\AI\E-zzio"

$Version="V48.23"

$AuditPath="runtime\audit\core_module_boundary\V48_23"

New-Item -ItemType Directory -Force -Path $AuditPath | Out-Null


Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " E-ZZIO $Version — ADAPTER RUNTIME CERTIFICATION"
Write-Host " HARDENED 10/10"
Write-Host " READ ONLY / ZERO MUTATION" -ForegroundColor Yellow
Write-Host "============================================================"


# ------------------------------------------------------------------
# PYTHON IMPORT TEST
# ------------------------------------------------------------------

$Python=@"
import sys
import traceback

sys.path.insert(0,r"G:\AI\E-zzio")

results={}

tests=[
("IMPORT_CORE_MEMORY","core.memory_core"),
("IMPORT_EZZIO_CORE","runtime.core.ezzio_core")
]

for name,module in tests:
    try:
        __import__(module)
        results[name]="PASS"
    except Exception as e:
        results[name]="FAIL:"+str(e)

for k,v in results.items():
    print(k+"="+v)

"@

$tmp="$env:TEMP\ezzio_import_test.py"

Set-Content $tmp $Python -Encoding UTF8

$out=python $tmp 2>&1

Remove-Item $tmp -Force -ErrorAction SilentlyContinue


$CoreImport="UNKNOWN"
$EzzioImport="UNKNOWN"

foreach($line in $out)
{
    if($line -match "IMPORT_CORE_MEMORY=(.*)")
    {
        $CoreImport=$Matches[1]
    }

    if($line -match "IMPORT_EZZIO_CORE=(.*)")
    {
        $EzzioImport=$Matches[1]
    }
}



# ------------------------------------------------------------------
# ADAPTER SCAN
# ------------------------------------------------------------------

$Adapters=Get-ChildItem `
"runtime\adapters" `
-Recurse `
-Filter "*.py" `
-ErrorAction SilentlyContinue


$StubDetails=@()
$StubCount=0


foreach($file in $Adapters)
{

    $hits=Select-String `
    -Path $file.FullName `
    -Pattern "raise NotImplementedError" `
    -ErrorAction SilentlyContinue


    foreach($hit in $hits)
    {
        $StubCount++

        $StubDetails += [PSCustomObject]@{
            File=$file.FullName
            Line=$hit.LineNumber
            Code=$hit.Line.Trim()
        }
    }
}



# ------------------------------------------------------------------
# RISK ENGINE
# ------------------------------------------------------------------

if($StubCount -gt 0)
{
    $Risk="HIGH - STUB IMPLEMENTATIONS PRESENT"
}
elseif(
($CoreImport -eq "PASS") -and
($EzzioImport -eq "PASS")
)
{
    $Risk="LOW"
}
else
{
    $Risk="MEDIUM - IMPORT FAILURE"
}



# ------------------------------------------------------------------
# REPORT
# ------------------------------------------------------------------

$Report=[PSCustomObject]@{

    Version=$Version

    Timestamp=(Get-Date).ToString("o")

    Mode="READ_ONLY_CERTIFICATION"

    ImportCoreMemory=$CoreImport

    ImportEzzioCore=$EzzioImport

    AdapterFiles=$Adapters.Count

    StubMethods=$StubCount

    StubDetails=$StubDetails

    RuntimeRisk=$Risk

    Delete="FORBIDDEN"

    Move="FORBIDDEN"

    Mutation="NONE"
}


$Json=$Report | ConvertTo-Json -Depth 50


$ReportFile=Join-Path `
$AuditPath `
"V48_23_RUNTIME_COMPATIBILITY_REPORT.json"


Set-Content `
$ReportFile `
$Json `
-Encoding UTF8


$Hash=(Get-FileHash $ReportFile -Algorithm SHA256).Hash


Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan

Write-Host "CORE MEMORY :" $CoreImport
Write-Host "EZZIO CORE  :" $EzzioImport
Write-Host "ADAPTERS    :" $Adapters.Count
Write-Host "STUBS       :" $StubCount
Write-Host "RISK        :" $Risk

Write-Host ""
Write-Host "REPORT:"
Write-Host $ReportFile

Write-Host ""
Write-Host "SHA256:"
Write-Host $Hash

Write-Host ""
Write-Host "READ ONLY"
Write-Host "NO DELETE"
Write-Host "NO MOVE"
Write-Host "NO MUTATION"

Write-Host "============================================================"


if($Risk -eq "LOW")
{
    exit 0
}
else
{
    exit 1
}

