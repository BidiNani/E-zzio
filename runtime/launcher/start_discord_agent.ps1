$ErrorActionPreference = "Continue"
$Root = "G:\AI\E-zzio"
Set-Location $Root
$PythonExe = "G:\AI\E-zzio\.venv\Scripts\python.exe"

# Implémentation du Mutex Global (Boot Lock)
$MutexName = "Global\EZZIO_BOOT_V755"
$Mutex = New-Object System.Threading.Mutex($false, $MutexName, [ref]$false)
if (-not $Mutex.WaitOne(0, $false)) {
    Write-Warning "[!] Un orchestrateur de boot E-ZZIO est déjà en cours d'exécution. Arrêt immédiat."
    exit 0
}

try {
    $AuditLog = "G:\AI\E-zzio\runtime\audit\system\boot_chain.jsonl"
    function Write-Audit {
        param($Event, $Status, $Details = @{})
        $Record = @{
            time = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
            event = $Event
            status = $Status
            details = $Details
        }
        $Record | ConvertTo-Json -Compress -Depth 5 | Out-File -FilePath $AuditLog -Append -Encoding UTF8
    }

    Write-Audit -Event "BOOT_SEQUENCE" -Status "STARTING"
    Write-Host "[E-ZZIO BOOT] Lancement du Backend Supervisor..."
    Start-Process -FilePath $PythonExe -ArgumentList "core/runtime/backend_supervisor.py" -WindowStyle Hidden
    
    Write-Host "[E-ZZIO BOOT] Attente de la certification API /health..."
    $timeout = 60
    $elapsed = 0
    $api_ready = $false

    while ($elapsed -lt $timeout) {
        try {
            $response = Invoke-RestMethod -Uri "http://127.0.0.1:8001/health" -Method Get -TimeoutSec 2 -ErrorAction Stop
            if ($response.service -eq "E-ZZIO" -and $response.status -eq "ONLINE") {
                Write-Host "`n[OK] API E-ZZIO Validée."
                Write-Audit -Event "API_HEALTHCHECK" -Status "OK"
                $api_ready = $true
                break
            }
        } catch {}
        Start-Sleep -Seconds 2
        $elapsed += 2
    }

    if (-not $api_ready) {
        Write-Audit -Event "API_HEALTHCHECK" -Status "FAILED"
        Write-Error "[!] ÉCHEC CRITIQUE API."
        exit 1
    }

    Write-Host "[E-ZZIO BOOT] Lancement du Discord Supervisor..."
    Start-Process -FilePath $PythonExe -ArgumentList "core/runtime/discord_supervisor.py" -WindowStyle Hidden
    Write-Audit -Event "BOOT_SEQUENCE" -Status "COMPLETED"

} finally {
    $Mutex.ReleaseMutex()
    $Mutex.Dispose()
}

