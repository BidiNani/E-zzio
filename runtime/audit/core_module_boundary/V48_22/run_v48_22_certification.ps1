# ==============================================================================
# E-ZZIO V48.22 — FINAL CORE BOUNDARY CERTIFICATION
# SCRIPT MODE
# READ ONLY / ZERO MUTATION
# ==============================================================================

$ErrorActionPreference="Stop"

Set-Location G:\AI\E-zzio


$AuditPath="runtime\audit\core_module_boundary\V48_22"


New-Item `
-ItemType Directory `
-Force `
-Path $AuditPath | Out-Null


Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " E-ZZIO V48.22 — FINAL CORE BOUNDARY CERTIFICATION" -ForegroundColor Cyan
Write-Host " SCRIPT MODE / READ ONLY / ZERO MUTATION" -ForegroundColor Yellow
Write-Host "============================================================"


$CoreFiles = Get-ChildItem `
"core","runtime\core" `
-Recurse `
-Filter "*.py"



$Violations=@()



foreach($file in $CoreFiles)
{

    $Lines=Get-Content $file.FullName


    foreach($line in $Lines)
    {


        if(($line -match "from runtime\.(memory|identity|cognition|telemetry|recovery)") -and ($line -notmatch "runtime\.adapters"))
        {

            $Violations += [PSCustomObject]@{

                File=$file.FullName
                ForbiddenImport=$line.Trim()
                Severity="CRITICAL"
                Rule="CORE_DIRECT_RUNTIME_DEPENDENCY"

            }

        }



        if(($line -match "import runtime\.(memory|identity|cognition|telemetry|recovery)") -and ($line -notmatch "runtime\.adapters"))
        {

            $Violations += [PSCustomObject]@{

                File=$file.FullName
                ForbiddenImport=$line.Trim()
                Severity="CRITICAL"
                Rule="CORE_DIRECT_RUNTIME_IMPORT"

            }

        }


    }

}



$Score=100


if($Violations.Count -gt 0)
{
    $Score=0
}



if($Violations.Count -eq 0)
{
    $Status="BOUNDARY_SECURE"
}
else
{
    $Status="BOUNDARY_BREACH"
}



$Report=[PSCustomObject]@{

    Version="V48.22"

    Timestamp=(Get-Date).ToString("o")

    ExecutionMode="SCRIPT"

    CoreFilesScanned=$CoreFiles.Count

    Violations=$Violations.Count

    BoundaryScore="$Score/100"

    Status=$Status

    Mutation="NONE"

}



$Violations |
ConvertTo-Json -Depth 10 |
Set-Content `
(Join-Path $AuditPath "BOUNDARY_VIOLATIONS.json") `
-Encoding UTF8



$Report |
ConvertTo-Json -Depth 10 |
Set-Content `
(Join-Path $AuditPath "BOUNDARY_CERTIFICATION.json") `
-Encoding UTF8




Write-Host ""

Write-Host "============================================================" -ForegroundColor Cyan

Write-Host " CORE FILES SCANNED :" $CoreFiles.Count

Write-Host " VIOLATIONS         :" $Violations.Count



if($Violations.Count -eq 0)
{

    Write-Host " STATUS : BOUNDARY SECURE" -ForegroundColor Green

    Write-Host " SCORE  : 10/10" -ForegroundColor Green

}
else
{

    Write-Host " STATUS : BOUNDARY BREACH" -ForegroundColor Red

    $Violations | Format-Table -AutoSize

}



Write-Host "============================================================"

Write-Host ""

Write-Host "AUDIT:"
Write-Host $AuditPath

Write-Host ""

Write-Host "READ ONLY"
Write-Host "NO DELETE"
Write-Host "NO MOVE"
Write-Host "NO MUTATION"

