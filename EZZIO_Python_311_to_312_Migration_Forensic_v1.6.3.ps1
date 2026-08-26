# =============================================================================
# E-ZZIO — PYTHON 3.11 -> 3.12 MIGRATION CERTIFICATION GATE
# Version : 1.6.3 (HARDENED FORENSIC CERTIFIER)
# Mode    : FORENSIC INVESTIGATION & RUNTIME CERTIFICATION / FAIL-CLOSED
# =============================================================================

param(
    [int]$ServerPort = 8001
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ErrorActionPreference = 'Stop'

# =============================================================================
# 0 — INITIALISATION ET CONFIGURATION
# =============================================================================

$ScriptVersion = '1.6.3'
$script:Checks = [System.Collections.Generic.List[object]]::new()
$script:CriticalFailure = $false

$UvicornProcess = $null
$SpawnedPid = $null

$ProjectRoot = 'G:\AI\E-zzio'

# Détection non-destructive des environnements
$CurrentVenv       = Join-Path $ProjectRoot '.venv'
$CurrentPython     = Join-Path $CurrentVenv 'Scripts\python.exe'

$Archive311Venv    = Join-Path $ProjectRoot '.venv_311_archive'
$Archive311Python  = Join-Path $Archive311Venv 'Scripts\python.exe'

$AuditRoot = Join-Path $ProjectRoot 'runtime\audit\python_migration'
$Timestamp = Get-Date -Format 'yyyyMMdd_HHmmss_fff'

$LogPath         = Join-Path $AuditRoot ("PYTHON_311_TO_312_{0}.log" -f $Timestamp)
$Requirements311 = Join-Path $AuditRoot ("REQUIREMENTS_311_{0}.txt" -f $Timestamp)
$Requirements312 = Join-Path $AuditRoot ("REQUIREMENTS_312_{0}.txt" -f $Timestamp)
$ReportPath      = Join-Path $AuditRoot ("MIGRATION_REPORT_{0}.json" -f $Timestamp)
$UvicornOutPath  = Join-Path $AuditRoot ("UVICORN_STDOUT_{0}.log" -f $Timestamp)
$UvicornErrPath  = Join-Path $AuditRoot ("UVICORN_STDERR_{0}.log" -f $Timestamp)

$ServerPythonModule = 'interfaces.api.server'
$ServerAppTarget    = 'interfaces.api.server:app'
$ServerHost         = '127.0.0.1'

if (-not (Test-Path -LiteralPath $AuditRoot -PathType Container)) {
    New-Item -ItemType Directory -Path $AuditRoot -Force | Out-Null
}

# Sauvegarde de l'environnement parent pour restauration stricte
$OriginalEnvUnbuffered = $env:PYTHONUNBUFFERED
$OriginalEnvEncoding   = $env:PYTHONIOENCODING

# Variables globales de mesure temporelle et processus
$TimingReport = [PSCustomObject]@{
    StaticServerImportSeconds = 0.0
    ProcessStartIso           = $null
    TcpReadyIso               = $null
    HttpReadyIso              = $null
    ShutdownIso               = $null
    StartupDurationSeconds    = 0.0
    TcpDurationSeconds        = 0.0
    HttpDurationSeconds       = 0.0
    ShutdownDurationSeconds   = 0.0
    ProcessId                 = $null
    ProcessExecutable         = $null
    ExitCode                  = $null
    TcpReady                  = $false
    HttpReady                 = $false
    HttpStatus                = 'N/A'
}

# =============================================================================
# FONCTIONS OUTILS FORENSIC ET CONFINEMENT PROCESSUS
# =============================================================================

function Write-Log {
    param([Parameter(Mandatory)][AllowEmptyString()][string]$Message)
    try { Add-Content -LiteralPath $LogPath -Value $Message -Encoding UTF8 -ErrorAction Stop } catch {}
}

function Write-Section {
    param([Parameter(Mandatory)][string]$Title)
    Write-Host ''
    Write-Host ('=' * 88) -ForegroundColor Cyan
    Write-Host $Title -ForegroundColor Cyan
    Write-Host ('=' * 88) -ForegroundColor Cyan
    Write-Log ''
    Write-Log ('=' * 88)
    Write-Log $Title
    Write-Log ('=' * 88)
}

function Write-Result {
    param(
        [Parameter(Mandatory)][ValidateSet('PASS','FAIL','WARN','INFO')][string]$Status,
        [Parameter(Mandatory)][AllowEmptyString()][string]$Message
    )
    $Color = switch ($Status) {
        'PASS' { 'Green' }
        'FAIL' { 'Red' }
        'WARN' { 'Yellow' }
        'INFO' { 'Gray' }
    }
    Write-Host ("[{0}] {1}" -f $Status, $Message) -ForegroundColor $Color
    Write-Log ("[{0}] {1}" -f $Status, $Message)
}

function Add-Check {
    param(
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)][ValidateSet('PASS','FAIL','WARN','INFO')][string]$Status,
        [Parameter(Mandatory)][AllowEmptyString()][string]$Detail
    )
    $script:Checks.Add([PSCustomObject]@{
        Name   = $Name
        Status = $Status
        Detail = $Detail
        Time   = (Get-Date).ToString('o')
    })
}

function Stop-SafeProcessTree {
    param([Parameter(Mandatory)][int]$ParentPid)
    try {
        # Vérification d'identité du parent
        $parentProc = Get-CimInstance Win32_Process -Filter ("ProcessId = {0}" -f $ParentPid) -ErrorAction SilentlyContinue
        if ($null -eq $parentProc) { return }

        # 1. Découverte et arrêt récursif des descendants (feuilles d'abord)
        $children = Get-CimInstance Win32_Process -Filter ("ParentProcessId = {0}" -f $ParentPid) -ErrorAction SilentlyContinue
        if ($null -ne $children) {
            foreach ($child in $children) {
                Stop-SafeProcessTree -ParentPid ([int]$child.ProcessId)
            }
        }

        # 2. Vérification d'identité avant terminaison
        $currentProc = Get-Process -Id $ParentPid -ErrorAction SilentlyContinue
        if ($null -ne $currentProc) {
            $currentProc.Kill()
            $currentProc.WaitForExit(2000)
        }
    } catch {}
}

function Test-TcpPortReady {
    param(
        [Parameter(Mandatory)][string]$HostName,
        [Parameter(Mandatory)][int]$Port,
        [int]$TimeoutMs = 150
    )
    try {
        $tcp = [System.Net.Sockets.TcpClient]::new()
        $connectTask = $tcp.ConnectAsync($HostName, $Port)
        $ready = $connectTask.Wait($TimeoutMs) -and $tcp.Connected
        $tcp.Close()
        $tcp.Dispose()
        return $ready
    } catch {
        return $false
    }
}

function Invoke-Python {
    param([Parameter(Mandatory)][string]$PythonPath, [Parameter(Mandatory)][string[]]$Arguments)
    if (-not (Test-Path -LiteralPath $PythonPath -PathType Leaf)) { throw ("Python introuvable : {0}" -f $PythonPath) }
    $output = @()
    try {
        $output = & $PythonPath @Arguments 2>&1
        $exitCode = $LASTEXITCODE
    } catch { throw ("Échec d'exécution Python : {0}" -f $_.Exception.Message) }
    return [PSCustomObject]@{ ExitCode = $exitCode; Output = @($output) }
}

function Show-PythonOutput {
    param([Parameter(Mandatory)][object]$Result)
    foreach ($line in @($Result.Output)) {
        if ($null -ne $line) {
            $text = [string]$line
            if ($text.Length -gt 0) {
                Write-Host ("  {0}" -f $text) -ForegroundColor Gray
                Write-Log ("  {0}" -f $text)
            }
        }
    }
}

function Get-PythonVersion {
    param([Parameter(Mandatory)][string]$PythonPath)
    $result = Invoke-Python -PythonPath $PythonPath -Arguments @('-c', 'import sys; print(sys.version_info.major); print(sys.version_info.minor); print(sys.version); print(sys.executable)')
    if ($result.ExitCode -ne 0) { Show-PythonOutput $result; throw ("Impossible de déterminer l'identité Python : {0}" -f $PythonPath) }
    $lines = @($result.Output | ForEach-Object { "$_".Trim() } | Where-Object { $_ -ne '' })
    if ($lines.Count -lt 4) { throw ("Réponse Python incomplète pour : {0}" -f $PythonPath) }
    return [PSCustomObject]@{
        Major      = [int]$lines[0]
        Minor      = [int]$lines[1]
        Version    = $lines[2]
        Executable = $lines[3]
    }
}

function Get-PipVersion {
    param([Parameter(Mandatory)][string]$PythonPath)
    $result = Invoke-Python -PythonPath $PythonPath -Arguments @('-m', 'pip', '--version')
    if ($result.ExitCode -ne 0) { throw ("pip indisponible via : {0} -m pip" -f $PythonPath) }
    $text = (@($result.Output) -join "`n").Trim()
    if ([string]::IsNullOrWhiteSpace($text)) { throw "pip n'a retourné aucune information." }
    return $text
}

function Export-PipFreeze {
    param([Parameter(Mandatory)][string]$PythonPath, [Parameter(Mandatory)][string]$Destination)
    $result = Invoke-Python -PythonPath $PythonPath -Arguments @('-m', 'pip', 'freeze')
    if ($result.ExitCode -ne 0) { Show-PythonOutput $result; throw "pip freeze a échoué." }
    $lines = @($result.Output | ForEach-Object { "$_" })
    Set-Content -LiteralPath $Destination -Value $lines -Encoding UTF8 -Force -ErrorAction Stop
    return $lines
}

function Test-PythonImport {
    param([Parameter(Mandatory)][string]$PythonPath, [Parameter(Mandatory)][string]$ModuleName)
    $code = ("import importlib, sys; module = importlib.import_module('{0}'); print('MODULE={0}'); print('VERSION=' + str(getattr(module, '__version__', 'unknown')))" -f $ModuleName)
    $result = Invoke-Python -PythonPath $PythonPath -Arguments @('-c', $code)
    return $result
}

function Test-ServerModuleWithTiming {
    param([Parameter(Mandatory)][string]$PythonPath, [Parameter(Mandatory)][string]$ModuleName)
    $code = ("import importlib, time, sys; t0 = time.perf_counter(); module = importlib.import_module('{0}'); t1 = time.perf_counter(); print('SERVER_MODULE={0}'); print(f'IMPORT_TIME_SECONDS={{t1 - t0:.4f}}'); assert hasattr(module, 'app'), 'App manquante'; print('HAS_APP=True')" -f $ModuleName)
    $result = Invoke-Python -PythonPath $PythonPath -Arguments @('-c', $code)
    return $result
}

function Parse-Requirements {
    param([Parameter(Mandatory)][string]$FilePath)
    $map = @{}
    if (Test-Path -LiteralPath $FilePath) {
        $lines = Get-Content -LiteralPath $FilePath
        foreach ($line in $lines) {
            $line = $line.Trim()
            if ($line -match '^([^=<>@]+)(==|@)(.*)$') {
                $pkg = $matches[1].Trim().ToLowerInvariant()
                $ver = $matches[3].Trim()
                $map[$pkg] = $ver
            }
        }
    }
    return $map
}

# =============================================================================
# BANNIÈRE D'EXÉCUTION
# =============================================================================

Write-Host ''
Write-Host ('╔' + ('═' * 86) + '╗') -ForegroundColor Cyan
Write-Host '║        E-ZZIO — PYTHON 3.11 -> 3.12 MIGRATION CERTIFICATION GATE (1.6.3)    ║' -ForegroundColor Cyan
Write-Host '║                 STRICT ISOLATION, PID CONFINEMENT & SMOKE TEST              ║' -ForegroundColor Cyan
Write-Host ('╚' + ('═' * 86) + '╝') -ForegroundColor Cyan
Write-Host ''

Write-Host 'MODE       : FORENSIC INVESTIGATION & CERTIFICATION / FAIL-CLOSED'
Write-Host ("PROJECT    : {0}" -f $ProjectRoot)
Write-Host ("LOG        : {0}" -f $LogPath)
Write-Host ''

Write-Log ("E-ZZIO PYTHON 3.11 TO 3.12 MIGRATION CERTIFICATION GATE v{0}" -f $ScriptVersion)

# =============================================================================
# PIPELINE D'EXÉCUTION ET VALIDATION STRICTEMENT FORENSIQUE
# =============================================================================

$DiffAdded   = @()
$DiffRemoved = @()
$DiffChanged = @()
$IdenticalCount = 0

try {
    # -------------------------------------------------------------------------
    # [1/14] à [5/14] - VÉRIFICATIONS SYSTÈME & IDENTIFICATION DU RUNTIME
    # -------------------------------------------------------------------------
    Write-Section '[1/14 à 5/14] VÉRIFICATIONS SYSTÈME'
    
    if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) {
        throw ("Projet E-ZZIO introuvable : {0}" -f $ProjectRoot)
    }
    Add-Check -Name 'Project Root Verification' -Status 'PASS' -Detail $ProjectRoot

    # Runtime principal 3.12
    if (-not (Test-Path -LiteralPath $CurrentPython -PathType Leaf)) {
        throw ("Runtime Python (.venv) introuvable : {0}" -f $CurrentPython)
    }
    $currentIdentity = Get-PythonVersion -PythonPath $CurrentPython
    if ($currentIdentity.Major -ne 3 -or $currentIdentity.Minor -ne 12) {
        Add-Check -Name 'Python 3.12 Runtime Identity' -Status 'FAIL' -Detail ("Détecté: {0}" -f $currentIdentity.Version)
        throw ("Le runtime .venv n'est pas en Python 3.12 (Détecté: {0})" -f $currentIdentity.Version)
    }
    Write-Result -Status 'PASS' -Message ("Runtime principal (.venv) certifié en Python 3.12 ({0})." -f $currentIdentity.Version)
    Add-Check -Name 'Python 3.12 Runtime Identity' -Status 'PASS' -Detail $currentIdentity.Version

    # Archive de référence 3.11 (FAIL-CLOSED strict, aucun fallback)
    if (-not (Test-Path -LiteralPath $Archive311Python -PathType Leaf)) {
        Add-Check -Name 'Python 3.11 Archive Presence' -Status 'FAIL' -Detail ("Archive introuvable: {0}" -f $Archive311Python)
        throw "Archive de référence Python 3.11 (.venv_311_archive) introuvable (FAIL-CLOSED)."
    }
    $archiveIdentity = Get-PythonVersion -PythonPath $Archive311Python
    if ($archiveIdentity.Major -ne 3 -or $archiveIdentity.Minor -ne 11) {
        Add-Check -Name 'Python 3.11 Archive Identity' -Status 'FAIL' -Detail ("Détecté: {0}" -f $archiveIdentity.Version)
        throw ("L'archive .venv_311_archive n'est pas un Python 3.11 valide (Détecté: {0})" -f $archiveIdentity.Version)
    }
    Write-Result -Status 'PASS' -Message ("Archive de référence Python 3.11 certifiée ({0})." -f $archiveIdentity.Version)
    Add-Check -Name 'Python 3.11 Archive Identity' -Status 'PASS' -Detail $archiveIdentity.Version

    # Snapshot de référence 3.11
    $snapshot311 = Export-PipFreeze -PythonPath $Archive311Python -Destination $Requirements311
    Write-Result -Status 'PASS' -Message ("Snapshot de référence Python 3.11 extrait ({0} packages)." -f $snapshot311.Count)
    Add-Check -Name 'Python 3.11 Snapshot Extraction' -Status 'PASS' -Detail ("{0} packages" -f $snapshot311.Count)

    # -------------------------------------------------------------------------
    # [6/14] CONTRÔLE PIP ET INTÉGRITÉ DU RUNTIME 3.12
    # -------------------------------------------------------------------------
    Write-Section '[6/14] VÉRIFICATION DE L''ENVIRONNEMENT PYTHON 3.12'
    $pipVersion = Get-PipVersion -PythonPath $CurrentPython
    Write-Result -Status 'PASS' -Message ("pip Python 3.12 certifié ({0})." -f $pipVersion)
    Add-Check -Name 'Pip 3.12 Integrity' -Status 'PASS' -Detail $pipVersion

    # -------------------------------------------------------------------------
    # [7/14] à [11/14] - IMPORTS ET IDENTITÉ RUNTIME
    # -------------------------------------------------------------------------
    Write-Section '[7/14 à 11/14] IMPORTS ET IDENTITÉ RUNTIME'
    $criticalModules = @('fastapi', 'uvicorn', 'aiosqlite')
    foreach ($module in $criticalModules) {
        $moduleResult = Test-PythonImport -PythonPath $CurrentPython -ModuleName $module
        if ($moduleResult.ExitCode -ne 0) {
            Add-Check -Name ("Module Import: {0}" -f $module) -Status 'FAIL' -Detail ("ExitCode {0}" -f $moduleResult.ExitCode)
            throw ("Module critique invalide : {0}" -f $module)
        }
        Add-Check -Name ("Module Import: {0}" -f $module) -Status 'PASS' -Detail 'ExitCode 0'
        Write-Result -Status 'PASS' -Message ("Module critique validé : {0}" -f $module)
    }

    # Import statique du serveur et mesure du coût d'initialisation
    Write-Host ("  Test d'importation statique du serveur ({0}) et mesure du temps..." -f $ServerPythonModule) -ForegroundColor Yellow
    $serverResult = Test-ServerModuleWithTiming -PythonPath $CurrentPython -ModuleName $ServerPythonModule
    if ($serverResult.ExitCode -ne 0) {
        Add-Check -Name 'Server Module Static Import' -Status 'FAIL' -Detail ("ExitCode {0}" -f $serverResult.ExitCode)
        throw ("Échec d'importation statique du module serveur : {0}" -f $ServerPythonModule)
    }

    $staticImportTime = 0.0
    $hasApp = $false
    foreach ($line in @($serverResult.Output)) {
        if ($null -ne $line) {
            $str = [string]$line
            if ($str -match '^IMPORT_TIME_SECONDS=([\d\.]+)') {
                $staticImportTime = [double]$matches[1]
            }
            if ($str -match '^HAS_APP=True') {
                $hasApp = $true
            }
        }
    }

    $TimingReport.StaticServerImportSeconds = $staticImportTime

    if (-not $hasApp) {
        Add-Check -Name 'Server App Object Verification' -Status 'FAIL' -Detail ("Objet app manquant dans {0}" -f $ServerPythonModule)
        throw "Le module serveur ne contient pas l'objet app."
    }

    Add-Check -Name 'Server Module Static Import' -Status 'PASS' -Detail ("{0} importé en {1}s" -f $ServerPythonModule, $staticImportTime)
    Add-Check -Name 'Server App Object Verification' -Status 'PASS' -Detail "Objet app présent"
    Write-Result -Status 'PASS' -Message ("Module serveur interfaces.api.server validé avec app (Temps d'import statique : {0}s)." -f $staticImportTime)

    # -------------------------------------------------------------------------
    # [12/14] GATE 13 : RUNTIME SMOKE TEST (FORENSIC TIMED SMOKE TEST v1.6.3)
    # -------------------------------------------------------------------------
    Write-Section '[12/14] GATE 13 : RUNTIME SMOKE TEST (HARDENED v1.6.3)'
    Write-Host ("  Démarrage Uvicorn sur {0}:{1} (PID contrôlé)..." -f $ServerHost, $ServerPort) -ForegroundColor Yellow
    Write-Host ("  Flux STDOUT capturé dans : {0}" -f $UvicornOutPath) -ForegroundColor DarkGray
    Write-Host ("  Flux STDERR capturé dans : {0}" -f $UvicornErrPath) -ForegroundColor DarkGray

    # 0. Vérification pré-vol : Le port de test DOIT être strictement libre avant le lancement
    if (Test-TcpPortReady -HostName $ServerHost -Port $ServerPort -TimeoutMs 150) {
        Add-Check -Name 'Gate 13 Smoke Test Pre-flight' -Status 'FAIL' -Detail ("Le port de test {0} est déjà occupé avant le lancement du serveur (Collision détectée)" -f $ServerPort)
        throw ("Le port de test {0} est déjà occupé avant le lancement du serveur. Veuillez libérer ce port ou spécifier un -ServerPort libre." -f $ServerPort)
    }

    # 1. Variables d'environnement pour flush immédiat
    $env:PYTHONUNBUFFERED = '1'
    $env:PYTHONIOENCODING = 'utf-8'

    # 2. Lancement avec WorkingDirectory explicite, -u et --no-use-colors
    $UvicornArgs = @('-u', '-m', 'uvicorn', $ServerAppTarget, '--host', $ServerHost, '--port', [string]$ServerPort, '--no-use-colors')
    
    $TimingReport.ProcessStartIso = (Get-Date).ToString('o')
    $Stopwatch = [System.Diagnostics.Stopwatch]::StartNew()

    $UvicornProcess = Start-Process -FilePath $CurrentPython `
                                   -ArgumentList $UvicornArgs `
                                   -WorkingDirectory $ProjectRoot `
                                   -RedirectStandardOutput $UvicornOutPath `
                                   -RedirectStandardError $UvicornErrPath `
                                   -PassThru `
                                   -WindowStyle Hidden

    $SpawnedPid = [int]$UvicornProcess.Id
    $TimingReport.ProcessId = $SpawnedPid
    $TimingReport.ProcessExecutable = $CurrentPython

    Write-Host ("  Processus Uvicorn instancié (PID: {0}). Attente active du socket..." -f $SpawnedPid) -ForegroundColor DarkGray

    # 3. Timeout calibré à 90 secondes avec détection de crash immédiate à chaque tour
    $MaxWaitSeconds = 90
    $PollIntervalMs = 200
    $MaxAttempts = [int](($MaxWaitSeconds * 1000) / $PollIntervalMs)
    $IsUp = $false
    $CrashedPrematurely = $false
    $CapturedExitCode = $null

    for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
        # Détection immédiate d'un arrêt prématuré
        if ($UvicornProcess.HasExited) {
            $CrashedPrematurely = $true
            $CapturedExitCode = $UvicornProcess.ExitCode
            $TimingReport.ExitCode = $CapturedExitCode
            break
        }

        # Sonde TCP non-bloquante ultra-rapide via TcpClient (120ms)
        if (Test-TcpPortReady -HostName $ServerHost -Port $ServerPort -TimeoutMs 120) {
            $IsUp = $true
            $TimingReport.TcpReadyIso = (Get-Date).ToString('o')
            $TimingReport.TcpDurationSeconds = [math]::Round($Stopwatch.ElapsedMilliseconds / 1000, 3)
            $TimingReport.TcpReady = $true
            break
        }

        Start-Sleep -Milliseconds $PollIntervalMs
    }

    $TimingReport.StartupDurationSeconds = [math]::Round($Stopwatch.ElapsedMilliseconds / 1000, 3)

    # 4. Traitement en cas d'échec
    if (-not $IsUp) {
        $exitCode = if ($CrashedPrematurely) { $CapturedExitCode } elseif ($UvicornProcess.HasExited) { $UvicornProcess.ExitCode } else { 'TIMEOUT_ALIVE' }
        $TimingReport.ExitCode = $exitCode

        $errContent = if (Test-Path -LiteralPath $UvicornErrPath) { Get-Content -LiteralPath $UvicornErrPath -Raw -ErrorAction SilentlyContinue } else { '' }
        $outContent = if (Test-Path -LiteralPath $UvicornOutPath) { Get-Content -LiteralPath $UvicornOutPath -Raw -ErrorAction SilentlyContinue } else { '' }

        Write-Host ''
        Write-Host ("[CRASH] ÉCHEC SMOKE TEST ! (PID: {0} | Statut: {1} | Durée: {2}s)" -f $SpawnedPid, $exitCode, $TimingReport.StartupDurationSeconds) -ForegroundColor Red
        if (-not [string]::IsNullOrWhiteSpace($errContent)) {
            Write-Host '--- STDERR CAPTURÉ ---' -ForegroundColor Yellow
            Write-Host $errContent -ForegroundColor Yellow
            Write-Host '----------------------' -ForegroundColor Yellow
        }
        if (-not [string]::IsNullOrWhiteSpace($outContent)) {
            Write-Host '--- STDOUT CAPTURÉ ---' -ForegroundColor DarkGray
            Write-Host $outContent -ForegroundColor Gray
            Write-Host '----------------------' -ForegroundColor DarkGray
        }

        # Nettoyage récursif confiné au PID parent
        if ($null -ne $SpawnedPid) {
            Stop-SafeProcessTree -ParentPid $SpawnedPid
        }

        Add-Check -Name 'Gate 13 Smoke Test' -Status 'FAIL' -Detail ("Port non ouvert après {0}s (Statut: {1})" -f $TimingReport.StartupDurationSeconds, $exitCode)
        throw ("Smoke Test échoué : Le serveur n'a pas ouvert le port {0} dans le délai imparti ({1}s / {2}s)." -f $ServerPort, $TimingReport.StartupDurationSeconds, $MaxWaitSeconds)
    }

    Write-Host ("  Port TCP {0} ouvert avec succès en {1}s." -f $ServerPort, $TimingReport.TcpDurationSeconds) -ForegroundColor Green

    # 5. Validation fonctionnelle HTTP GET
    $httpWatch = [System.Diagnostics.Stopwatch]::StartNew()
    $HttpTestResult = 'NONE'
    $StatusCode = 0
    Write-Host ("  Test HTTP GET strict sur http://{0}:{1}/api/v1/self/status..." -f $ServerHost, $ServerPort) -ForegroundColor Yellow
    try {
        $TestUri = ("http://{0}:{1}/api/v1/self/status" -f $ServerHost, $ServerPort)
        $Response = Invoke-WebRequest -Uri $TestUri -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
        $StatusCode = [int]$Response.StatusCode
        $HttpTestResult = ("HTTP {0}" -f $StatusCode)
        $TimingReport.HttpReady = ($StatusCode -ge 200 -and $StatusCode -lt 300)
    } catch {
        if ($null -ne $_.Exception.Response) {
            $StatusCode = [int]$_.Exception.Response.StatusCode
            $HttpTestResult = ("HTTP {0}" -f $StatusCode)
        } else {
            $StatusCode = 0
            $HttpTestResult = ("HTTP ERROR: {0}" -f $_.Exception.Message)
        }
        $TimingReport.HttpReady = $false
    }

    $TimingReport.HttpReadyIso = (Get-Date).ToString('o')
    $TimingReport.HttpDurationSeconds = [math]::Round($httpWatch.ElapsedMilliseconds / 1000, 3)
    $TimingReport.HttpStatus = $HttpTestResult

    # 6. Fermeture propre et chirurgicale du processus testé
    Write-Host ("  Fermeture propre de l'arborescence Uvicorn (PID: {0})..." -f $SpawnedPid) -ForegroundColor DarkGray
    $shutdownWatch = [System.Diagnostics.Stopwatch]::StartNew()
    if ($null -ne $SpawnedPid) {
        Stop-SafeProcessTree -ParentPid $SpawnedPid
    }
    $TimingReport.ShutdownIso = (Get-Date).ToString('o')
    $TimingReport.ShutdownDurationSeconds = [math]::Round($shutdownWatch.ElapsedMilliseconds / 1000, 3)

    # Restauration de l'environnement parent
    if ($null -ne $OriginalEnvUnbuffered) { $env:PYTHONUNBUFFERED = $OriginalEnvUnbuffered } else { Remove-Item Env:\PYTHONUNBUFFERED -ErrorAction SilentlyContinue }
    if ($null -ne $OriginalEnvEncoding) { $env:PYTHONIOENCODING = $OriginalEnvEncoding } else { Remove-Item Env:\PYTHONIOENCODING -ErrorAction SilentlyContinue }

    # Validation stricte du statut HTTP (Uniquement 2xx accepté)
    if ($StatusCode -lt 200 -or $StatusCode -ge 300) {
        Add-Check -Name 'Gate 13 HTTP Verification' -Status 'FAIL' -Detail ("Statut rejeté: {0}" -f $HttpTestResult)
        throw ("Réponse HTTP inacceptable (Non 2xx) : {0}" -f $HttpTestResult)
    }

    Add-Check -Name 'Gate 13 Smoke Test' -Status 'PASS' -Detail ("TCP OK ({0}s) | HTTP {1} ({2}s)" -f $TimingReport.TcpDurationSeconds, $HttpTestResult, $TimingReport.HttpDurationSeconds)
    Write-Result -Status 'PASS' -Message ("Smoke Test validé : Port TCP ouvert en {0}s, Réponse ASGI {1}." -f $TimingReport.TcpDurationSeconds, $HttpTestResult)

    # -------------------------------------------------------------------------
    # [13/14] SNAPSHOT FINAL ET PARITÉ DES DÉPENDANCES STRICTE
    # -------------------------------------------------------------------------
    Write-Section '[13/14] DEPENDENCY PARITY GATE (STRICT POLICY)'
    $snapshot312 = Export-PipFreeze -PythonPath $CurrentPython -Destination $Requirements312
    Write-Result -Status 'PASS' -Message ("Snapshot final Python 3.12 généré ({0} packages)." -f $snapshot312.Count)
    Add-Check -Name 'Python 3.12 Snapshot Extraction' -Status 'PASS' -Detail ("{0} packages" -f $snapshot312.Count)

    $map311 = Parse-Requirements -FilePath $Requirements311
    $map312 = Parse-Requirements -FilePath $Requirements312

    foreach ($pkg in $map312.Keys) {
        if (-not $map311.ContainsKey($pkg)) {
            $DiffAdded += $pkg
        }
        elseif ($map311[$pkg] -ne $map312[$pkg]) {
            $DiffChanged += ("{0} ({1} -> {2})" -f $pkg, $map311[$pkg], $map312[$pkg])
        }
        else {
            $IdenticalCount++
        }
    }
    foreach ($pkg in $map311.Keys) {
        if (-not $map312.ContainsKey($pkg)) {
            $DiffRemoved += $pkg
        }
    }

    Write-Host '  Comparaison des Snapshots (3.11 vs 3.12) :' -ForegroundColor DarkGray
    Write-Host ("  IDENTICAL : {0}" -f $IdenticalCount) -ForegroundColor Gray
    Write-Host ("  ADDED     : {0}" -f $DiffAdded.Count) -ForegroundColor $(if ($DiffAdded.Count -gt 0) { 'Red' } else { 'Gray' })
    Write-Host ("  REMOVED   : {0}" -f $DiffRemoved.Count) -ForegroundColor $(if ($DiffRemoved.Count -gt 0) { 'Red' } else { 'Gray' })
    Write-Host ("  CHANGED   : {0}" -f $DiffChanged.Count) -ForegroundColor $(if ($DiffChanged.Count -gt 0) { 'Red' } else { 'Gray' })

    # RÈGLE FORENSIQUE STRICTE : Tout écart de parité sans validation explicite est un FAIL
    $parityDetail = ("Identical: {0} | Added: {1} | Removed: {2} | Changed: {3}" -f $IdenticalCount, $DiffAdded.Count, $DiffRemoved.Count, $DiffChanged.Count)
    if ($DiffAdded.Count -gt 0 -or $DiffRemoved.Count -gt 0 -or $DiffChanged.Count -gt 0) {
        Write-Result -Status 'FAIL' -Message ("Parité des dépendances non respectée : {0}" -f $parityDetail)
        Add-Check -Name 'Dependency Parity' -Status 'FAIL' -Detail $parityDetail
        throw "Parité des dépendances compromise."
    } else {
        Write-Result -Status 'PASS' -Message ("Parité des dépendances 100% conforme ({0}/{0} packages identiques)." -f $IdenticalCount)
        Add-Check -Name 'Dependency Parity' -Status 'PASS' -Detail ("Exact Match ({0}/{0})" -f $IdenticalCount)
    }

    # -------------------------------------------------------------------------
    # [14/14] SYNTHÈSE FORENSIC ET RAPPORT JSON COMPLET
    # -------------------------------------------------------------------------
    Write-Section '[14/14] VERDICT ET RAPPORT JSON'

    $PassCount = @($script:Checks | Where-Object { $_.Status -eq 'PASS' }).Count
    $FailCount = @($script:Checks | Where-Object { $_.Status -eq 'FAIL' }).Count
    $WarnCount = @($script:Checks | Where-Object { $_.Status -eq 'WARN' }).Count

    # Condition de certification absolue : 0 FAIL, 0 WARN, CriticalFailure = False
    $CalculatedVerdict = if ($FailCount -eq 0 -and $WarnCount -eq 0 -and -not $script:CriticalFailure) {
        'CERTIFIED_PYTHON_312_CANDIDATE'
    } else {
        'MIGRATION_REJECTED'
    }

    $ReportData = [PSCustomObject]@{
        Timestamp                 = $Timestamp
        ScriptVersion             = $ScriptVersion
        ProjectRoot               = $ProjectRoot
        CurrentPython             = $CurrentPython
        CurrentPythonVersion      = $currentIdentity.Version
        ArchivePython             = $Archive311Python
        ArchivePythonVersion      = $archiveIdentity.Version
        
        # Processus et mesures de temps
        ProcessId                 = $TimingReport.ProcessId
        ProcessExecutable         = $TimingReport.ProcessExecutable
        ProcessStartTime          = $TimingReport.ProcessStartIso
        TcpReadyTime              = $TimingReport.TcpReadyIso
        HttpReadyTime             = $TimingReport.HttpReadyIso
        ShutdownTime              = $TimingReport.ShutdownIso
        
        StaticServerImportSeconds = $TimingReport.StaticServerImportSeconds
        StartupDurationSeconds    = $TimingReport.StartupDurationSeconds
        TcpDurationSeconds        = $TimingReport.TcpDurationSeconds
        HttpDurationSeconds       = $TimingReport.HttpDurationSeconds
        ShutdownDurationSeconds   = $TimingReport.ShutdownDurationSeconds
        
        ExitCode                  = $TimingReport.ExitCode
        TcpReady                  = $TimingReport.TcpReady
        HttpReady                 = $TimingReport.HttpReady
        HttpStatus                = $TimingReport.HttpStatus
        
        # Parité des dépendances
        DependencyParity = [PSCustomObject]@{
            IdenticalCount = $IdenticalCount
            Added          = $DiffAdded
            Removed        = $DiffRemoved
            Changed        = $DiffChanged
        }

        # Décompte et liste des vérifications
        PassCount                 = $PassCount
        FailCount                 = $FailCount
        WarnCount                 = $WarnCount
        Verdict                   = $CalculatedVerdict
        Checks                    = $script:Checks
    }

    $ReportData | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $ReportPath -Encoding UTF8 -Force
    Write-Result -Status 'PASS' -Message ("Rapport forensic JSON écrit dans : {0}" -f $ReportPath)

    Write-Host ''
    if ($CalculatedVerdict -eq 'CERTIFIED_PYTHON_312_CANDIDATE') {
        Write-Host ('╔' + ('═' * 86) + '╗') -ForegroundColor Green
        Write-Host '║            VERDICT FINAL : CERTIFIED_PYTHON_312_CANDIDATE (100% PASS)         ║' -ForegroundColor Green
        Write-Host ('╚' + ('═' * 86) + '╝') -ForegroundColor Green
        exit 0
    }
    else {
        Write-Host ('╔' + ('═' * 86) + '╗') -ForegroundColor Red
        Write-Host '║            VERDICT FINAL : MIGRATION_REJECTED (FAIL-CLOSED)                   ║' -ForegroundColor Red
        Write-Host ('╚' + ('═' * 86) + '╝') -ForegroundColor Red
        exit 1
    }
}
catch {
    $script:CriticalFailure = $true
    
    # Restauration de l'environnement parent en cas d'erreur
    if ($null -ne $OriginalEnvUnbuffered) { $env:PYTHONUNBUFFERED = $OriginalEnvUnbuffered } else { Remove-Item Env:\PYTHONUNBUFFERED -ErrorAction SilentlyContinue }
    if ($null -ne $OriginalEnvEncoding) { $env:PYTHONIOENCODING = $OriginalEnvEncoding } else { Remove-Item Env:\PYTHONIOENCODING -ErrorAction SilentlyContinue }

    Write-Host ''
    Write-Host ('!' * 88) -ForegroundColor Red
    Write-Host ("ARRÊT FORENSIC (FAIL-CLOSED) : {0}" -f $_.Exception.Message) -ForegroundColor Red
    Write-Host ('!' * 88) -ForegroundColor Red

    # Nettoyage d'urgence strictement limité au PID instancié
    if ($null -ne $SpawnedPid) {
        Stop-SafeProcessTree -ParentPid $SpawnedPid
    }
    exit 1
}
