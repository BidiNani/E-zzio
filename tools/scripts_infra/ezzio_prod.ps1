#requires -Version 7.4

# ============================================================================
# SYNOPSIS
# E-ZZIO — PRODUCTION LAUNCHER HARDENED V19.3.2
#
# DESCRIPTION
# Lanceur production unifié E-ZZIO.
# Vérifie physiquement : Python, launcher officiel, ASGI entrypoint,
# ports 8000/3000/11434, Docker, Tailscale, Ollama, API E-ZZIO,
# et le moteur du bot Discord.
# ============================================================================

[CmdletBinding()]
param (
    [string]$RootPath      = "G:\AI\E-zzio",
    [string]$TailscaleBin  = "G:\AI\tailscale.exe",
    [string]$ApiUrl        = "http://127.0.0.1:8000",
    [string]$WebUiUrl      = "http://127.0.0.1:3000",
    [string]$OllamaUrl     = "http://127.0.0.1:11434",
    [int]$TimeoutSec       = 30,
    [switch]$NoBrowser
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ============================================================================
# CONFIGURATION
# ============================================================================

$Version = "19.3.2"

$LauncherRelativePath = "scripts\start_ezzio.py"
$DiscordLauncherPath  = "runtime\discord\bot_runner.py"
$AsgiEntrypoint       = "interfaces.api.server:app"
$ForbiddenEntrypoint  = "core.main:app"

$OpenWebUiContainer = "ezzio-open-webui"

$LauncherPath = Join-Path $RootPath $LauncherRelativePath
$DiscordPath  = Join-Path $RootPath $DiscordLauncherPath
$ServerPath   = Join-Path $RootPath "interfaces\api\server.py"

$ForensicRoot = Join-Path $RootPath "_forensic"
$ForensicDir  = Join-Path $ForensicRoot "v19"

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$LogPath   = Join-Path $ForensicDir "EZZIO_PROD_$Timestamp.log"

# ============================================================================
# COMPTEURS
# ============================================================================

$script:PassCount = 0
$script:WarnCount = 0
$script:FailCount = 0
$script:InfoCount = 0
$script:CriticalFailure = $false

# ============================================================================
# VALIDATION RACINE
# ============================================================================

if (-not (Test-Path -LiteralPath $RootPath -PathType Container)) {
    Write-Host ""
    Write-Host "[FAIL] Racine E-ZZIO introuvable : $RootPath" -ForegroundColor Red
    Write-Host ""
    exit 10
}

Set-Location -LiteralPath $RootPath

New-Item `
    -ItemType Directory `
    -Force `
    -Path $ForensicDir |
    Out-Null

# ============================================================================
# LOG
# ============================================================================

function Write-Log {
    param (
        [Parameter(Mandatory)]
        [string]$Message,

        [ValidateSet("PASS","WARN","FAIL","INFO")]
        [string]$Status = "INFO",

        [switch]$Critical
    )

    $Time = Get-Date -Format "HH:mm:ss.fff"

    switch ($Status) {
        "PASS" {
            $Color = "Green"
            $script:PassCount++
        }
        "WARN" {
            $Color = "Yellow"
            $script:WarnCount++
        }
        "FAIL" {
            $Color = "Red"
            $script:FailCount++
            if ($Critical) {
                $script:CriticalFailure = $true
            }
        }
        "INFO" {
            $Color = "Cyan"
            $script:InfoCount++
        }
    }

    $Line = "[$Time] [$Status] $Message"
    Write-Host $Line -ForegroundColor $Color
    Add-Content -LiteralPath $LogPath -Value $Line -Encoding UTF8
}

# ============================================================================
# SECTION
# ============================================================================

function Write-Section {
    param (
        [int]$Number,
        [int]$Total,
        [string]$Title
    )

    Write-Host ""
    Write-Host "-------------------------------------------------------------------------------" -ForegroundColor DarkGray
    Write-Host "[$Number/$Total] $Title" -ForegroundColor Cyan
    Write-Host "-------------------------------------------------------------------------------" -ForegroundColor DarkGray

    Add-Content -LiteralPath $LogPath -Value ""
    Add-Content -LiteralPath $LogPath -Value "[$Number/$Total] $Title"
}

# ============================================================================
# TCP PROBE
# ============================================================================

function Test-TcpPort {
    param (
        [Parameter(Mandatory)]
        [string]$ComputerName,

        [Parameter(Mandatory)]
        [int]$Port,

        [int]$TimeoutMs = 1500
    )

    $Client = $null
    try {
        $Client = [System.Net.Sockets.TcpClient]::new()
        $Task = $Client.ConnectAsync($ComputerName, $Port)
        if (-not $Task.Wait($TimeoutMs)) {
            return $false
        }
        return [bool]$Client.Connected
    }
    catch {
        return $false
    }
    finally {
        if ($null -ne $Client) {
            $Client.Dispose()
        }
    }
}

# ============================================================================
# HTTP PROBE
# ============================================================================

function Invoke-HttpProbe {
    param (
        [Parameter(Mandatory)]
        [string]$Uri,

        [int]$TimeoutSeconds = 5
    )

    try {
        $Response = Invoke-WebRequest `
            -Uri $Uri `
            -Method GET `
            -TimeoutSec $TimeoutSeconds `
            -UseBasicParsing `
            -ErrorAction Stop

        return [PSCustomObject]@{
            Success    = $true
            StatusCode = [int]$Response.StatusCode
            Content    = [string]$Response.Content
            Error      = $null
        }
    }
    catch {
        return [PSCustomObject]@{
            Success    = $false
            StatusCode = 0
            Content    = ""
            Error      = $_.Exception.Message
        }
    }
}

# ============================================================================
# EN-TÊTE
# ============================================================================

Clear-Host

Write-Host ""
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "              E-ZZIO — PRODUCTION LAUNCHER HARDENED V$Version" -ForegroundColor Cyan
Write-Host "              REAL BOOT / READINESS / OPEN WEBUI GATE" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "ROOT       : $RootPath"
Write-Host "LAUNCHER   : $LauncherRelativePath"
Write-Host "ASGI       : $AsgiEntrypoint"
Write-Host "API        : $ApiUrl"
Write-Host "OPEN WEBUI : $WebUiUrl"
Write-Host "OLLAMA     : $OllamaUrl"
Write-Host ""

Add-Content -LiteralPath $LogPath -Value "E-ZZIO PRODUCTION LAUNCHER V$Version" -Encoding UTF8
Add-Content -LiteralPath $LogPath -Value "Timestamp: $(Get-Date -Format o)" -Encoding UTF8

# ============================================================================
# [1/11] ENVIRONNEMENT
# ============================================================================

Write-Section 1 11 "ENVIRONNEMENT & OUTILS"

try {
    $PythonCommand = Get-Command python -ErrorAction Stop
    Write-Log -Message "Python détecté : $($PythonCommand.Source)" -Status PASS
}
catch {
    Write-Log -Message "Python introuvable dans le PATH." -Status FAIL -Critical
}

try {
    $PythonVersion = & python --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Log -Message "Version Python : $PythonVersion" -Status PASS
    }
    else {
        Write-Log -Message "Échec de python --version." -Status FAIL -Critical
    }
}
catch {
    Write-Log -Message "Impossible d'exécuter Python : $($_.Exception.Message)" -Status FAIL -Critical
}

# ============================================================================
# [2/11] SERVICE DISCOVERY
# ============================================================================

Write-Section 2 11 "SERVICE DISCOVERY & ENTRYPOINT BINDING"

if (Test-Path -LiteralPath $LauncherPath -PathType Leaf) {
    Write-Log -Message "Launcher officiel trouvé : $LauncherPath" -Status PASS
}
else {
    Write-Log -Message "Launcher officiel absent : $LauncherPath" -Status FAIL -Critical
}

if (Test-Path -LiteralPath $ServerPath -PathType Leaf) {
    Write-Log -Message "Module ASGI trouvé : $ServerPath" -Status PASS
}
else {
    Write-Log -Message "Module ASGI absent : $ServerPath" -Status FAIL -Critical
}

$ServerContent = ""
if (Test-Path -LiteralPath $ServerPath -PathType Leaf) {
    $ServerContent = Get-Content -LiteralPath $ServerPath -Raw -Encoding UTF8
    if ($ServerContent -match "FastAPI\s*\(") {
        Write-Log -Message "FastAPI physiquement détecté dans interfaces.api.server." -Status PASS
    }
    else {
        Write-Log -Message "FastAPI non détecté dans interfaces.api.server." -Status FAIL -Critical
    }

    if ($ServerContent -match "\bapp\s*=\s*FastAPI\s*\(") {
        Write-Log -Message "Objet ASGI 'app' physiquement détecté." -Status PASS
    }
    else {
        Write-Log -Message "Objet ASGI 'app' absent." -Status FAIL -Critical
    }
}

$ForbiddenReferences = @()
try {
    $PythonFiles = Get-ChildItem -LiteralPath $RootPath -Recurse -File -Filter "*.py" -ErrorAction SilentlyContinue |
        Where-Object {
            $_.FullName -notmatch "\\\.venv\\" -and
            $_.FullName -notmatch "\\_venv_" -and
            $_.FullName -notmatch "\\node_modules\\"
        }

    foreach ($File in $PythonFiles) {
        try {
            $Matches = Select-String -LiteralPath $File.FullName -Pattern "core\.main:app" -SimpleMatch -ErrorAction Stop
            if ($null -ne $Matches) {
                $ForbiddenReferences += $Matches
            }
        }
        catch { }
    }
}
catch {
    Write-Log -Message "Audit des références orphelines incomplet : $($_.Exception.Message)" -Status WARN
}

if ($ForbiddenReferences.Count -eq 0) {
    Write-Log -Message "Aucune référence à '$ForbiddenEntrypoint' détectée hors environnements exclus." -Status PASS
}
else {
    Write-Log -Message "$($ForbiddenReferences.Count) référence(s) à '$ForbiddenEntrypoint' détectée(s)." -Status FAIL -Critical
    foreach ($Reference in ($ForbiddenReferences | Select-Object -First 10)) {
        Write-Log -Message "$($Reference.Path):$($Reference.LineNumber) : $($Reference.Line.Trim())" -Status FAIL
    }
}

# ============================================================================
# [3/11] PORTS
# ============================================================================

Write-Section 3 11 "INSPECTION PHYSIQUE DES PORTS"

$Port8000 = Test-TcpPort -ComputerName "127.0.0.1" -Port 8000
if ($Port8000) { Write-Log -Message "Port 8000 : écoute TCP détectée." -Status PASS }
else { Write-Log -Message "Port 8000 : aucune écoute TCP détectée avant boot." -Status INFO }

$Port3000 = Test-TcpPort -ComputerName "127.0.0.1" -Port 3000
if ($Port3000) { Write-Log -Message "Port 3000 : écoute TCP détectée." -Status PASS }
else { Write-Log -Message "Port 3000 : aucune écoute TCP détectée." -Status WARN }

$Port11434 = Test-TcpPort -ComputerName "127.0.0.1" -Port 11434
if ($Port11434) { Write-Log -Message "Port 11434 : écoute TCP détectée." -Status PASS }
else { Write-Log -Message "Port 11434 : Ollama ne semble pas écouter." -Status FAIL -Critical }

# ============================================================================
# [4/11] DOCKER
# ============================================================================

Write-Section 4 11 "DOCKER & OPEN WEBUI"

$DockerAvailable = $false
$DockerRunning = $false

try {
    $DockerCommand = Get-Command docker -ErrorAction Stop
    $DockerAvailable = $true
    Write-Log -Message "Docker CLI détecté : $($DockerCommand.Source)" -Status PASS
}
catch {
    Write-Log -Message "Docker CLI introuvable." -Status FAIL -Critical
}

if ($DockerAvailable) {
    try {
        $DockerStatus = (& docker inspect -f '{{.State.Status}}' $OpenWebUiContainer 2>$null).Trim()
        if ($DockerStatus -eq "running") {
            $DockerRunning = $true
            Write-Log -Message "Docker : '$OpenWebUiContainer' est RUNNING." -Status PASS
        }
        elseif ([string]::IsNullOrWhiteSpace($DockerStatus)) {
            Write-Log -Message "Conteneur '$OpenWebUiContainer' introuvable." -Status FAIL -Critical
        }
        else {
            Write-Log -Message "Docker : état actuel '$DockerStatus'." -Status WARN
            if ($DockerStatus -eq "exited") {
                Write-Log -Message "Tentative de démarrage de '$OpenWebUiContainer'..." -Status INFO
                & docker start $OpenWebUiContainer | Out-Null
                Start-Sleep -Seconds 3
                $DockerStatusAfter = (& docker inspect -f '{{.State.Status}}' $OpenWebUiContainer 2>$null).Trim()
                if ($DockerStatusAfter -eq "running") {
                    $DockerRunning = $true
                    Write-Log -Message "Conteneur Open WebUI relancé avec succès." -Status PASS
                }
                else {
                    Write-Log -Message "Échec du redémarrage. État='$DockerStatusAfter'." -Status FAIL -Critical
                }
            }
        }
    }
    catch {
        Write-Log -Message "Erreur Docker : $($_.Exception.Message)" -Status FAIL -Critical
    }
}

# ============================================================================
# [5/11] TAILSCALE
# ============================================================================

Write-Section 5 11 "TAILSCALE SERVE"

if (Test-Path -LiteralPath $TailscaleBin -PathType Leaf) {
    Write-Log -Message "Binaire Tailscale trouvé : $TailscaleBin" -Status PASS
    try {
        $ServeStatus = (& $TailscaleBin serve status 2>&1) | Out-String
        Add-Content -LiteralPath $LogPath -Value "" -Encoding UTF8
        Add-Content -LiteralPath $LogPath -Value "TAILSCALE SERVE STATUS:" -Encoding UTF8
        Add-Content -LiteralPath $LogPath -Value $ServeStatus -Encoding UTF8

        if ($ServeStatus -match "https://") {
            Write-Log -Message "Tailscale Serve : endpoint HTTPS détecté." -Status PASS
        }
        elseif ($ServeStatus -match "3000") {
            Write-Log -Message "Tailscale Serve : routage vers port 3000 détecté." -Status PASS
        }
        else {
            Write-Log -Message "Aucun proxy Serve Open WebUI explicitement détecté." -Status WARN
        }
    }
    catch {
        Write-Log -Message "Échec de tailscale serve status : $($_.Exception.Message)" -Status WARN
    }
}
else {
    Write-Log -Message "Binaire Tailscale introuvable : $TailscaleBin" -Status WARN
}

# ============================================================================
# [6/11] OLLAMA
# ============================================================================

Write-Section 6 11 "OLLAMA ENGINE"

$OllamaProbe = Invoke-HttpProbe -Uri "$OllamaUrl/api/tags" -TimeoutSeconds 5
if ($OllamaProbe.Success -and $OllamaProbe.StatusCode -eq 200) {
    Write-Log -Message "Ollama : HTTP 200 réel sur /api/tags." -Status PASS
    try {
        $OllamaJson = $OllamaProbe.Content | ConvertFrom-Json
        if ($null -ne $OllamaJson.models) {
            $ModelCount = @($OllamaJson.models).Count
            Write-Log -Message "Ollama : $ModelCount modèle(s) exposé(s)." -Status PASS
        }
        else {
            Write-Log -Message "Ollama répond mais 'models' est absent." -Status WARN
        }
    }
    catch {
        Write-Log -Message "Réponse Ollama non interprétable comme JSON." -Status WARN
    }
}
else {
    Write-Log -Message "Ollama : probe HTTP échoué." -Status FAIL -Critical
}

# ============================================================================
# [7/11] BOOT E-ZZIO
# ============================================================================

Write-Section 7 11 "BOOT PHYSIQUE E-ZZIO"

$ReadinessUrl = "$ApiUrl/api/v1/health/readiness"
$Ready = $false
$ReadyPayload = $null

$InitialProbe = Invoke-HttpProbe -Uri $ReadinessUrl -TimeoutSeconds 3
if ($InitialProbe.Success -and $InitialProbe.StatusCode -eq 200) {
    try {
        $ReadyPayload = $InitialProbe.Content | ConvertFrom-Json
        if ($ReadyPayload.status -eq "READY") {
            $Ready = $true
            Write-Log -Message "E-ZZIO déjà actif : readiness READY." -Status PASS
        }
        else {
            Write-Log -Message "E-ZZIO répond mais status='$($ReadyPayload.status)'." -Status WARN
        }
    }
    catch {
        Write-Log -Message "Payload readiness invalide." -Status FAIL -Critical
    }
}
else {
    Write-Log -Message "Aucun readiness E-ZZIO initial détecté." -Status INFO
}

if (-not $Ready) {
    if (-not (Test-Path -LiteralPath $LauncherPath -PathType Leaf)) {
        Write-Log -Message "Impossible de démarrer : launcher officiel absent." -Status FAIL -Critical
    }
    else {
        Write-Log -Message "Démarrage via scripts/start_ezzio.py..." -Status INFO
        try {
            $LauncherProcess = Start-Process `
                -FilePath "python" `
                -ArgumentList @("`"$LauncherPath`"") `
                -WorkingDirectory $RootPath `
                -WindowStyle Minimized `
                -PassThru
            Write-Log -Message "Processus launcher créé : PID $($LauncherProcess.Id)." -Status PASS
        }
        catch {
            Write-Log -Message "Échec du lancement officiel : $($_.Exception.Message)" -Status FAIL -Critical
        }

        $Timer = [System.Diagnostics.Stopwatch]::StartNew()
        Write-Host ""
        Write-Host "Attente du readiness physique " -NoNewline -ForegroundColor Cyan
        
        while ($Timer.Elapsed.TotalSeconds -lt $TimeoutSec) {
            Start-Sleep -Milliseconds 750
            Write-Host "." -NoNewline -ForegroundColor DarkGray
            
            $Probe = Invoke-HttpProbe -Uri $ReadinessUrl -TimeoutSeconds 2
            if ($Probe.Success -and $Probe.StatusCode -eq 200) {
                try {
                    $Candidate = $Probe.Content | ConvertFrom-Json
                    if ($Candidate.status -eq "READY") {
                        $ReadyPayload = $Candidate
                        $Ready = $true
                        break
                    }
                }
                catch { }
            }
        }
        Write-Host ""
        $Timer.Stop()

        if ($Ready) {
            Write-Log -Message "E-ZZIO READY après $([math]::Round($Timer.Elapsed.TotalSeconds,2)) s." -Status PASS
        }
        else {
            Write-Log -Message "Timeout readiness après $TimeoutSec secondes." -Status FAIL -Critical
        }
    }
}

# ============================================================================
# [8/11] READINESS MATRIX
# ============================================================================

Write-Section 8 11 "READINESS MATRIX PHYSIQUE"

$RequiredChecks = @("process_alive", "database_ready", "memory_ready", "model_ready", "research_ready")

if ($null -eq $ReadyPayload) {
    Write-Log -Message "Aucun payload readiness exploitable." -Status FAIL -Critical
}
elseif ($null -eq $ReadyPayload.checks) {
    Write-Log -Message "Readiness : objet 'checks' ABSENT du payload." -Status FAIL -Critical
}
else {
    foreach ($CheckName in $RequiredChecks) {
        $Property = $ReadyPayload.checks.PSObject.Properties[$CheckName]
        
        if ($null -eq $Property) {
            Write-Log -Message "Readiness : check '$CheckName' ABSENT." -Status FAIL -Critical
            continue
        }
        
        $Value = [bool]$Property.Value
        if ($Value) {
            Write-Log -Message "Readiness : $CheckName = TRUE." -Status PASS
        }
        else {
            Write-Log -Message "Readiness : $CheckName = FALSE." -Status FAIL -Critical
        }
    }
}

# ============================================================================
# [9/11] OPEN WEBUI HTTP
# ============================================================================

Write-Section 9 11 "OPEN WEBUI — HTTP PHYSIQUE"

$WebUiProbe = Invoke-HttpProbe -Uri $WebUiUrl -TimeoutSeconds 5
if ($WebUiProbe.Success -and $WebUiProbe.StatusCode -ge 200 -and $WebUiProbe.StatusCode -lt 400) {
    Write-Log -Message "Open WebUI : HTTP $($WebUiProbe.StatusCode) réel." -Status PASS
}
else {
    Write-Log -Message "Open WebUI : HTTP inaccessible." -Status FAIL -Critical
}

# ============================================================================
# [10/11] DISCORD BOT INTEGRATION
# ============================================================================

Write-Section 10 11 "DISCORD BOT ENGINE"

if (Test-Path -LiteralPath $DiscordPath -PathType Leaf) {
    Write-Log -Message "Launcher Discord détecté : $DiscordLauncherPath" -Status PASS

    $DiscordPathEscaped = $DiscordLauncherPath.Replace('\', '\\')
    $BotRunning = Get-CimInstance Win32_Process -Filter "CommandLine LIKE '%$DiscordPathEscaped%'" | Select-Object -First 1

    if ($BotRunning) {
        Write-Log -Message "Processus Discord Bot déjà actif (PID: $($BotRunning.ProcessId))." -Status PASS
    }
    else {
        Write-Log -Message "Lancement du bot Discord en tâche de fond..." -Status INFO
        try {
            $BotProcess = Start-Process `
                -FilePath "python" `
                -ArgumentList @("`"$DiscordPath`"") `
                -WorkingDirectory $RootPath `
                -WindowStyle Minimized `
                -PassThru

            Start-Sleep -Seconds 4

            if ($BotProcess.HasExited) {
                Write-Log -Message "Le processus Discord s'est arrêté prématurément." -Status FAIL -Critical
            }
            else {
                Write-Log -Message "Bot Discord en ligne (PID: $($BotProcess.Id))." -Status PASS
            }
        }
        catch {
            Write-Log -Message "Échec du lancement Discord : $($_.Exception.Message)" -Status FAIL -Critical
        }
    }
}
else {
    Write-Log -Message "Script Discord introuvable : $DiscordLauncherPath (Ignoré)." -Status WARN
}

# ============================================================================
# [11/11] VERDICT FINAL & OUVERTURE
# ============================================================================

Write-Section 11 11 "VERDICT FINAL & OUVERTURE"

$Port3000Final = Test-TcpPort -ComputerName "127.0.0.1" -Port 3000
if ($Port3000Final) { Write-Log -Message "Port 3000 final : écoute TCP confirmée." -Status PASS }
else { Write-Log -Message "Port 3000 final : aucune écoute TCP." -Status FAIL -Critical }

$WebUiFinal = Invoke-HttpProbe -Uri $WebUiUrl -TimeoutSeconds 5
if ($WebUiFinal.Success -and $WebUiFinal.StatusCode -ge 200 -and $WebUiFinal.StatusCode -lt 400) {
    Write-Log -Message "Open WebUI final : HTTP $($WebUiFinal.StatusCode)." -Status PASS
}
else {
    Write-Log -Message "Open WebUI final : inaccessible." -Status FAIL -Critical
}

# ============================================================================
# RÉSUMÉ
# ============================================================================

Write-Host ""
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "                         E-ZZIO — FINAL MATRIX" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host ("[PASS] : {0}" -f $script:PassCount) -ForegroundColor Green
Write-Host ("[WARN] : {0}" -f $script:WarnCount) -ForegroundColor Yellow
Write-Host ("[FAIL] : {0}" -f $script:FailCount) -ForegroundColor Red
Write-Host ("[INFO] : {0}" -f $script:InfoCount) -ForegroundColor Cyan
Write-Host ""

if ($script:CriticalFailure) {
    Write-Log -Message "VERDICT FINAL : FAIL_CLOSED" -Status FAIL
    Write-Host ""
    Write-Host "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!" -ForegroundColor Red
    Write-Host "                         E-ZZIO — FAIL-CLOSED" -ForegroundColor Red
    Write-Host "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Une ou plusieurs preuves critiques sont absentes." -ForegroundColor Red
    Write-Host "Open WebUI n'est PAS déclaré certifié." -ForegroundColor Red
    Write-Host ""
    Write-Host "Journal forensic :" -ForegroundColor Cyan
    Write-Host $LogPath -ForegroundColor White
    Write-Host ""
    exit 20
}

Write-Log -Message "Toutes les conditions critiques sont physiquement satisfaites." -Status PASS

if (-not $NoBrowser) {
    Write-Log -Message "Ouverture d'Open WebUI : $WebUiUrl" -Status INFO
    try {
        Start-Process $WebUiUrl
        Write-Log -Message "Navigateur lancé vers Open WebUI." -Status PASS
    }
    catch {
        Write-Log -Message "Impossible d'ouvrir le navigateur : $($_.Exception.Message)" -Status WARN
    }
}

Write-Host ""
Write-Host "================================================================================" -ForegroundColor Green
Write-Host "                    E-ZZIO READY — OPEN WEBUI READY" -ForegroundColor Green
Write-Host "================================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "API        : $ApiUrl" -ForegroundColor Green
Write-Host "Readiness  : $ReadinessUrl" -ForegroundColor Green
Write-Host "Open WebUI : $WebUiUrl" -ForegroundColor Green
Write-Host "Ollama     : $OllamaUrl" -ForegroundColor Green
Write-Host ""
Write-Host "VERDICT : EZZIO_V19_3_2_PRODUCTION_BOOT_READY" -ForegroundColor Green
Write-Host ""
Write-Host "Journal forensic : $LogPath" -ForegroundColor DarkGray
Write-Host ""