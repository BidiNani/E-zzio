# ==============================================================================
# E-ZZIO PROGRESS ENGINE
# ==============================================================================

Set-StrictMode -Version Latest

$script:ProgressStart = Get-Date

function Start-EzzioProgress {

    param(
        [string]$Activity,
        [int]$Total
    )

    $script:EZZ_Total = [Math]::Max($Total,1)
    $script:EZZ_Start = Get-Date

    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host " $Activity" -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host ""
}

function Update-EzzioProgress {

    param(
        [int]$Current,
        [string]$Status = ""
    )

    $percent = [Math]::Round(($Current / $script:EZZ_Total) * 100,2)

    $elapsed = (Get-Date) - $script:EZZ_Start

    if($Current -gt 0){
        $speed = $Current / [Math]::Max($elapsed.TotalSeconds,1)
    }
    else{
        $speed = 0
    }

    if($speed -gt 0){
        $remaining = ($script:EZZ_Total-$Current)/$speed
    }
    else{
        $remaining = 0
    }

    $eta = (Get-Date).AddSeconds($remaining)

    $mem = [Math]::Round(
        (Get-Process -Id $PID).WorkingSet64/1MB,
        0
    )

    Write-Progress `
        -Activity "E-ZZIO" `
        -Status "$Status" `
        -PercentComplete $percent `
        -CurrentOperation "$Current / $($script:EZZ_Total) | $([Math]::Round($speed,1)) obj/s | ETA $($eta.ToString('HH:mm:ss')) | RAM ${mem}MB"

}

function Stop-EzzioProgress{

    Write-Progress -Activity "E-ZZIO" -Completed

    $elapsed = (Get-Date)-$script:EZZ_Start

    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host " OPÉRATION TERMINÉE" -ForegroundColor Green
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host ("Durée : {0:hh\:mm\:ss}" -f $elapsed)
    Write-Host ""
}