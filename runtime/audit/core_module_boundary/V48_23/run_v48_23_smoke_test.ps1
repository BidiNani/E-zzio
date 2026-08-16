# ==============================================================================
# E-ZZIO V48.23 — ADAPTER RUNTIME COMPATIBILITY CHECK
# READ ONLY / ZERO MUTATION
# ==============================================================================

$ErrorActionPreference="Stop"

Set-Location G:\AI\E-zzio


$AuditPath="runtime\audit\core_module_boundary\V48_23"


New-Item `
-ItemType Directory `
-Force `
-Path $AuditPath | Out-Null



Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " E-ZZIO V48.23 — ADAPTER RUNTIME COMPATIBILITY CHECK" -ForegroundColor Cyan
Write-Host " READ ONLY / ZERO MUTATION" -ForegroundColor Yellow
Write-Host "============================================================"



# ============================================================
# PYTHON IMPORT TEST
# ============================================================


$PythonCode=@"

results=@{}

try:
    import core.memory_core
    results['core.memory_core']='PASS'
except Exception as e:
    results['core.memory_core']='FAIL : '+str(e)


try:
    import runtime.core.ezzio_core
    results['runtime.core.ezzio_core']='PASS'
except Exception as e:
    results['runtime.core.ezzio_core']='FAIL : '+str(e)


for k,v in results.items():
    print(k+'='+v)

"@



$TempFile="$env:TEMP\ezzio_v48_23_test.py"


Set-Content `
$TempFile `
$PythonCode `
-Encoding UTF8



$ImportResult=python $TempFile


Remove-Item `
$TempFile `
-Force



$CoreImport="UNKNOWN"
$EzzioImport="UNKNOWN"



foreach($line in $ImportResult)
{

    if($line -match "core.memory_core=(.*)")
    {
        $CoreImport=$Matches[1]
    }


    if($line -match "runtime.core.ezzio_core=(.*)")
    {
        $EzzioImport=$Matches[1]
    }

}



# ============================================================
# ADAPTER SCAN
# ============================================================


$AdapterFiles=Get-ChildItem `
"runtime\adapters" `
-Recurse `
-Filter "*.py"



$AdapterReport=@()



foreach($file in $AdapterFiles)
{

    $content=Get-Content $file.FullName -Raw


    $stubs=([regex]::Matches(
        $content,
        "raise NotImplementedError"
    )).Count



    $AdapterReport += [PSCustomObject]@{

        File=$file.FullName

        StubCount=$stubs

    }

}



# ============================================================
# ADAPTER USAGE
# ============================================================


$Names=@(
"MemoryAdapter",
"IdentityAdapter",
"CognitionAdapter",
"TelemetryAdapter",
"RecoveryAdapter"
)



$Usage=@()



foreach($name in $Names)
{

    $hits=Get-ChildItem `
    "core","runtime\core" `
    -Recurse `
    -Filter "*.py" |
    Select-String `
    "$name\("



    $Usage += [PSCustomObject]@{

        Adapter=$name

        Calls=$hits.Count

    }

}



$StubTotal=(
$AdapterReport |
Measure-Object StubCount -Sum
).Sum



if($StubTotal -gt 0)
{
    $Risk="HIGH - STUB IMPLEMENTATIONS PRESENT"
}
elseif(
$CoreImport -eq "PASS" -and
$EzzioImport -eq "PASS"
)
{
    $Risk="LOW"
}
else
{
    $Risk="MEDIUM - IMPORT FAILURE"
}



$Report=[PSCustomObject]@{

    Version="V48.23"

    Timestamp=(Get-Date).ToString("o")

    ImportCoreMemory=$CoreImport

    ImportEzzioCore=$EzzioImport

    AdapterFiles=$AdapterFiles.Count

    StubMethods=$StubTotal

    AdapterDetails=$AdapterReport

    AdapterUsage=$Usage

    RuntimeRisk=$Risk

    Mutation="NONE"

}



$Report |
ConvertTo-Json -Depth 20 |
Set-Content `
(Join-Path $AuditPath "V48_23_RUNTIME_COMPATIBILITY_REPORT.json") `
-Encoding UTF8



Write-Host ""

Write-Host "============================================================" -ForegroundColor Cyan

Write-Host " IMPORT CORE MEMORY :" $CoreImport

Write-Host " IMPORT EZZIO CORE  :" $EzzioImport

Write-Host ""

Write-Host " ADAPTER FILES      :" $AdapterFiles.Count

Write-Host " STUB METHODS       :" $StubTotal

Write-Host ""

Write-Host " RUNTIME RISK       :" $Risk -ForegroundColor Yellow

Write-Host ""

Write-Host "AUDIT:"
Write-Host $AuditPath

Write-Host ""

Write-Host "READ ONLY"
Write-Host "NO DELETE"
Write-Host "NO MOVE"
Write-Host "NO MUTATION"

Write-Host "============================================================"

