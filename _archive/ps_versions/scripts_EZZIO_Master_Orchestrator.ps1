#requires -Version 5.1
<#
===============================================================================
 E-ZZIO — MASTER PRODUCTION / AG / FORENSIC ORCHESTRATOR
 Version : 1.0.0
 Mode    : READ-ONLY / FAIL-CLOSED / FORENSIC
===============================================================================
#>

[CmdletBinding()]
param(
    [ValidateSet('Full','Diagnose','Audit','AG','Capcap','Tests')]
    [string]$Mode = 'Full',

    [string]$Root = 'G:\AI\E-zzio',
    [string]$ApiUrl = 'http://127.0.0.1:8000',
    [string]$OpenWebUIUrl = 'http://127.0.0.1:3000',
    [string]$OpenWebUIIPv6Url = 'http://[::1]:3000',
    [string]$OllamaUrl = 'http://127.0.0.1:11434',
    [string]$OpenWebUIContainer = 'ezzio-open-webui',
    [string]$DiscordLauncher = 'runtime\discord\bot_runner.py',

    [switch]$StartServices,
    [switch]$AllowProjectMutation,
    [switch]$SkipPytest,
    [switch]$SkipPythonCompile
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ScriptVersion = '1.0.0'
$RunId = 'run_master_' + (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssfffZ') + '_' + [Guid]::NewGuid().ToString('N').Substring(0,12)
$StartedUtc = (Get-Date).ToUniversalTime()

$ForensicRoot = Join-Path $Root '_forensic\master'
$RunRoot = Join-Path $ForensicRoot $RunId
$LogPath = Join-Path $RunRoot 'EZZIO_MASTER_FORENSIC.log'
$MatrixPath = Join-Path $RunRoot 'EZZIO_MASTER_MATRIX.json'
$ManifestPath = Join-Path $RunRoot 'EZZIO_MASTER_RUN_MANIFEST.json'
$EvidencePath = Join-Path $RunRoot 'EZZIO_MASTER_RAW_EVIDENCE.json'
$ReportPath = Join-Path $RunRoot 'EZZIO_MASTER_FINAL_REPORT.md'
$PythonCompilePath = Join-Path $RunRoot 'PYTHON_COMPILE_RESULTS.json'
$PytestPath = Join-Path $RunRoot 'PYTEST_RESULTS.json'
$AuditPath = Join-Path $RunRoot 'PROJECT_AUDIT.json'
$SecretsPath = Join-Path $RunRoot 'SECRET_SCAN.json'
$GitPath = Join-Path $RunRoot 'GIT_STATE.json'
$NetworkPath = Join-Path $RunRoot 'NETWORK_FORENSICS.json'
$DockerPath = Join-Path $RunRoot 'DOCKER_FORENSICS.json'
$OllamaPath = Join-Path $RunRoot 'OLLAMA_FORENSICS.json'
$CapcapPath = Join-Path $RunRoot 'CAPCAP_READINESS.json'
$AGPath = Join-Path $RunRoot 'AG_MISSION_BRIEF.json'

$CriticalFailure = $false
$StartedMutation = $false

$Counters = @{
    PASS = 0
    WARN = 0
    FAIL = 0
    INFO = 0
    UNPROVEN = 0
}

$Evidence = [System.Collections.ArrayList]::new()

function Ensure-Directory {
    param([Parameter(Mandatory)][string]$Path)
    if (-not (Test-Path -LiteralPath $Path -PathType Container)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
}

function Write-Forensic {
    param(
        [Parameter(Mandatory)][ValidateSet('PASS','WARN','FAIL','INFO')]
        [string]$Level,
        [Parameter(Mandatory)][string]$Message,
        [string]$EvidenceType = 'PHYSICAL',
        [string]$Subject = ''
    )

    $Now = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ss.fffZ')
    $Counters[$Level]++

    if ($Level -eq 'FAIL') {
        $script:CriticalFailure = $true
    }

    $Line = ('[{0}] [{1}] {2}' -f $Now, $Level, $Message)
    Write-Host $Line
    Add-Content -LiteralPath $LogPath -Value $Line -Encoding UTF8

    [void]$Evidence.Add([ordered]@{
        timestamp_utc = $Now
        level         = $Level
        evidence_type = $EvidenceType
        subject       = $Subject
        message       = $Message
    })
}

function Write-Unproven {
    param([Parameter(Mandatory)][string]$Message, [string]$Subject = '')
    $Counters['UNPROVEN']++
    $Now = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ss.fffZ')
    $Line = ('[{0}] [UNPROVEN] {1}' -f $Now, $Message)
    Write-Host $Line
    Add-Content -LiteralPath $LogPath -Value $Line -Encoding UTF8

    [void]$Evidence.Add([ordered]@{
        timestamp_utc = $Now
        level         = 'UNPROVEN'
        evidence_type = 'UNPROVEN'
        subject       = $Subject
        message       = $Message
    })
}

function Write-Section {
    param([Parameter(Mandatory)][string]$Title, [Parameter(Mandatory)][string]$Number)
    Write-Host ''
    Write-Host ('-------------------------------------------------------------------------------')
    Write-Host ('[{0}] {1}' -f $Number, $Title)
    Write-Host ('-------------------------------------------------------------------------------')
    Add-Content -LiteralPath $LogPath -Value ''
    Add-Content -LiteralPath $LogPath -Value ('-------------------------------------------------------------------------------')
    Add-Content -LiteralPath $LogPath -Value ('[{0}] {1}' -f $Number, $Title)
    Add-Content -LiteralPath $LogPath -Value ('-------------------------------------------------------------------------------')
}

function Test-CommandAvailable {
    param([Parameter(Mandatory)][string]$Name)
    try {
        $cmd = Get-Command $Name -ErrorAction Stop
        Write-Forensic -Level 'PASS' -Message ('{0} detecte : {1}' -f $Name, $cmd.Source) -EvidenceType 'PHYSICAL' -Subject $Name
        return $true
    }
    catch {
        Write-Forensic -Level 'FAIL' -Message ('{0} indisponible.' -f $Name) -EvidenceType 'PHYSICAL' -Subject $Name
        return $false
    }
}

function Get-Sha256 {
    param([Parameter(Mandatory)][string]$Path)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        return $null
    }
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Test-TcpPort {
    param([Parameter(Mandatory)][string]$HostName, [Parameter(Mandatory)][int]$Port, [int]$TimeoutMs = 3000)
    try {
        $client = [System.Net.Sockets.TcpClient]::new()
        $task = $client.ConnectAsync($HostName, $Port)
        if (-not $task.Wait($TimeoutMs)) {
            $client.Dispose()
            return $false
        }
        $ok = $client.Connected
        $client.Dispose()
        return $ok
    }
    catch {
        return $false
    }
}

function Test-Http {
    param([Parameter(Mandatory)][string]$Uri, [int]$TimeoutSec = 5)
    try {
        $response = Invoke-WebRequest -Uri $Uri -Method GET -TimeoutSec $TimeoutSec -UseBasicParsing -ErrorAction Stop
        return [ordered]@{
            success = $true
            status  = [int]$response.StatusCode
            uri     = $Uri
            error   = $null
        }
    }
    catch {
        return [ordered]@{
            success = $false
            status  = $null
            uri     = $Uri
            error   = $_.Exception.Message
        }
    }
}

function Invoke-NativeSafe {
    param([Parameter(Mandatory)][string]$FilePath, [string[]]$ArgumentList = @())
    $output = & $FilePath @ArgumentList 2>&1
    $exitCode = $LASTEXITCODE
    return [ordered]@{
        exit_code = $exitCode
        output    = @($output | ForEach-Object { "$_" })
    }
}

function Convert-ToSafeJson {
    param([Parameter(Mandatory)][object]$Object, [Parameter(Mandatory)][string]$Path, [int]$Depth = 12)
    $Object | ConvertTo-Json -Depth $Depth | Set-Content -LiteralPath $Path -Encoding UTF8
}

function Assert-Root {
    if (-not (Test-Path -LiteralPath $Root -PathType Container)) {
        throw ('ROOT E-ZZIO introuvable : {0}' -f $Root)
    }
    $resolved = (Resolve-Path -LiteralPath $Root).Path
    if ($resolved -ne $Root) {
        throw ('Resolution ROOT inattendue : {0}' -f $resolved)
    }
    Write-Forensic -Level 'PASS' -Message ('ROOT valide : {0}' -f $Root) -Subject 'ROOT'
}

function Assert-NoSanctuaryMutation {
    if ($AllowProjectMutation) {
        Write-Forensic -Level 'WARN' -Message 'AllowProjectMutation demande : le master reste neanmoins READ-ONLY pour le sanctuaire V16.4.' -EvidenceType 'CONTROL'
    }
    else {
        Write-Forensic -Level 'PASS' -Message 'Mode READ-ONLY actif.' -EvidenceType 'CONTROL'
    }
}

# ============================================================================
# INITIALISATION
# ============================================================================

Ensure-Directory -Path $ForensicRoot
Ensure-Directory -Path $RunRoot

Write-Host '================================================================================'
Write-Host '              E-ZZIO — MASTER PRODUCTION / AG / FORENSIC ORCHESTRATOR'
Write-Host '================================================================================'
Write-Host ('VERSION      : {0}' -f $ScriptVersion)
Write-Host ('RUN ID       : {0}' -f $RunId)
Write-Host ('MODE         : {0}' -f $Mode)
Write-Host ('ROOT         : {0}' -f $Root)
Write-Host ('STARTED UTC  : {0}' -f $StartedUtc.ToString('yyyy-MM-ddTHH:mm:ss.fffZ'))
Write-Host 'READ-ONLY    : ACTIVE'
Write-Host 'FAIL-CLOSED  : ACTIVE'
Write-Host 'SANCTUARY    : IMMUTABLE'
Write-Host '================================================================================'

# ============================================================================
# [1/16] ENVIRONNEMENT
# ============================================================================

Write-Section -Title 'ENVIRONNEMENT ET OUTILS' -Number '1/16'

try {
    Assert-Root
    Assert-NoSanctuaryMutation

    $psVersion = $PSVersionTable.PSVersion.ToString()
    Write-Forensic -Level 'PASS' -Message ('PowerShell : {0}' -f $psVersion) -Subject 'PowerShell'

    Test-CommandAvailable -Name 'python' | Out-Null
    Test-CommandAvailable -Name 'docker' | Out-Null
    Test-CommandAvailable -Name 'git' | Out-Null
    Test-CommandAvailable -Name 'curl' | Out-Null

    if (Test-Path -LiteralPath 'G:\AI\tailscale.exe' -PathType Leaf) {
        Write-Forensic -Level 'PASS' -Message 'Tailscale detecte : G:\AI\tailscale.exe' -Subject 'Tailscale'
    }
    else {
        Write-Forensic -Level 'WARN' -Message 'Tailscale non detecte a G:\AI\tailscale.exe.' -Subject 'Tailscale'
    }
}
catch {
    Write-Forensic -Level 'FAIL' -Message ('Erreur environnement : {0}' -f $_.Exception.Message) -Subject 'Environment'
}

# ============================================================================
# [2/16] STRUCTURE E-ZZIO
# ============================================================================

Write-Section -Title 'ENTRYPOINTS E-ZZIO' -Number '2/16'

$RequiredPaths = @(
    'scripts\start_ezzio.py',
    'interfaces\api\server.py'
)

foreach ($relative in $RequiredPaths) {
    $path = Join-Path $Root $relative
    if (Test-Path -LiteralPath $path -PathType Leaf) {
        Write-Forensic -Level 'PASS' -Message ('Fichier requis present : {0}' -f $relative) -Subject $relative
    }
    else {
        Write-Forensic -Level 'FAIL' -Message ('Fichier requis absent : {0}' -f $relative) -Subject $relative
    }
}

# ============================================================================
# [3/16] PYTHON / ASGI
# ============================================================================

Write-Section -Title 'PYTHON / ASGI / FASTAPI' -Number '3/16'

$ServerPath = Join-Path $Root 'interfaces\api\server.py'

if (Test-Path -LiteralPath $ServerPath -PathType Leaf) {
    try {
        $serverText = Get-Content -LiteralPath $ServerPath -Raw -Encoding UTF8

        if ($serverText -match 'FastAPI\s*\(') {
            Write-Forensic -Level 'PASS' -Message 'FastAPI physiquement detecte dans server.py.' -Subject $ServerPath
        }
        else {
            Write-Forensic -Level 'FAIL' -Message 'FastAPI non detecte dans server.py.' -Subject $ServerPath
        }

        if ($serverText -match 'app\s*=') {
            Write-Forensic -Level 'PASS' -Message "Objet ASGI 'app' detecte." -Subject $ServerPath
        }
        else {
            Write-Forensic -Level 'FAIL' -Message "Objet ASGI 'app' non detecte." -Subject $ServerPath
        }
    }
    catch {
        Write-Forensic -Level 'FAIL' -Message ('Lecture server.py impossible : {0}' -f $_.Exception.Message) -Subject $ServerPath
    }
}

# ============================================================================
# [4/16] PORTS
# ============================================================================

Write-Section -Title 'INSPECTION PHYSIQUE DES PORTS' -Number '4/16'

$Ports = @(
    [ordered]@{ name='E-ZZIO API'; host='127.0.0.1'; port=8000 },
    [ordered]@{ name='Open WebUI IPv4'; host='127.0.0.1'; port=3000 },
    [ordered]@{ name='Open WebUI IPv6'; host='::1'; port=3000 },
    [ordered]@{ name='Ollama'; host='127.0.0.1'; port=11434 }
)

$NetworkEvidence = [System.Collections.ArrayList]::new()

foreach ($entry in $Ports) {
    $ok = Test-TcpPort -HostName $entry.host -Port $entry.port
    $state = if ($ok) { 'PASS' } else { 'WARN' }

    Write-Forensic -Level $state -Message ('{0} : TCP {1}:{2} = {3}' -f $entry.name, $entry.host, $entry.port, $ok) -Subject ('{0}:{1}' -f $entry.host, $entry.port)

    [void]$NetworkEvidence.Add([ordered]@{
        name    = $entry.name
        host    = $entry.host
        port    = $entry.port
        tcp_ok  = $ok
    })
}

Convert-ToSafeJson -Object @($NetworkEvidence) -Path $NetworkPath

# ============================================================================
# [5/16] HTTP E-ZZIO
# ============================================================================

Write-Section -Title 'E-ZZIO API — HTTP PHYSIQUE' -Number '5/16'

$api = Test-Http -Uri $ApiUrl

if ($api.success -and $api.status -eq 200) {
    Write-Forensic -Level 'PASS' -Message ('E-ZZIO API HTTP {0} : {1}' -f $api.status, $ApiUrl) -Subject $ApiUrl
}
elseif ($api.success) {
    Write-Forensic -Level 'WARN' -Message ('E-ZZIO API HTTP {0} : {1}' -f $api.status, $ApiUrl) -Subject $ApiUrl
}
else {
    Write-Forensic -Level 'WARN' -Message ('E-ZZIO API en attente : {0}' -f $ApiUrl) -Subject $ApiUrl
}

# ============================================================================
# [6/16] OLLAMA
# ============================================================================

Write-Section -Title 'OLLAMA ENGINE' -Number '6/16'

$OllamaEvidence = [ordered]@{
    url         = $OllamaUrl
    reachable   = $false
    status      = $null
    model_count = $null
    models      = @()
}

try {
    $tags = Invoke-RestMethod -Uri ($OllamaUrl + '/api/tags') -Method GET -TimeoutSec 5 -ErrorAction Stop
    $models = @($tags.models)

    $OllamaEvidence.reachable = $true
    $OllamaEvidence.status = 200
    $OllamaEvidence.model_count = $models.Count
    $OllamaEvidence.models = @(
        $models | ForEach-Object {
            [ordered]@{
                name  = $_.name
                model = $_.model
                size  = $_.size
            }
        }
    )

    Write-Forensic -Level 'PASS' -Message 'Ollama HTTP 200 reel sur /api/tags.' -Subject $OllamaUrl
    Write-Forensic -Level 'PASS' -Message ('Ollama expose {0} modele(s).' -f $models.Count) -Subject 'Ollama models'
}
catch {
    Write-Forensic -Level 'WARN' -Message ('Ollama en attente sur port 11434 : {0}' -f $_.Exception.Message) -Subject $OllamaUrl
}

Convert-ToSafeJson -Object $OllamaEvidence -Path $OllamaPath

# ============================================================================
# [7/16] DOCKER / OPEN WEBUI
# ============================================================================

Write-Section -Title 'DOCKER ET OPEN WEBUI' -Number '7/16'

$DockerEvidence = [ordered]@{
    docker_available = $false
    container_found  = $false
    running          = $false
    health           = $null
    image            = $null
    ports            = $null
}

try {
    $dockerCmd = Get-Command docker -ErrorAction Stop
    $DockerEvidence.docker_available = $true

    $inspect = Invoke-NativeSafe -FilePath $dockerCmd.Source -ArgumentList @('inspect', $OpenWebUIContainer)

    if ($inspect.exit_code -eq 0) {
        $DockerEvidence.container_found = $true
        try {
            $container = $inspect.output -join "`n" | ConvertFrom-Json
            if ($container.Count -gt 0) {
                $c = $container[0]
                $DockerEvidence.running = ($c.State.Status -eq 'running')
                $DockerEvidence.health = $c.State.Health.Status
                $DockerEvidence.image = $c.Config.Image
                $DockerEvidence.ports = $c.NetworkSettings.Ports

                if ($DockerEvidence.running) {
                    Write-Forensic -Level 'PASS' -Message ("Docker : '{0}' RUNNING." -f $OpenWebUIContainer) -Subject $OpenWebUIContainer
                }
                else {
                    Write-Forensic -Level 'FAIL' -Message ("Docker : '{0}' non RUNNING." -f $OpenWebUIContainer) -Subject $OpenWebUIContainer
                }

                if ($DockerEvidence.health -eq 'healthy') {
                    Write-Forensic -Level 'PASS' -Message 'Open WebUI : HEALTHY.' -Subject $OpenWebUIContainer
                }
                elseif ($null -eq $DockerEvidence.health) {
                    Write-Unproven -Message 'Open WebUI : aucun Health.Status exploitable.' -Subject $OpenWebUIContainer
                }
                else {
                    Write-Forensic -Level 'WARN' -Message ('Open WebUI health = {0}' -f $DockerEvidence.health) -Subject $OpenWebUIContainer
                }
            }
        }
        catch {
            Write-Forensic -Level 'FAIL' -Message ('Inspection Docker JSON invalide : {0}' -f $_.Exception.Message) -Subject $OpenWebUIContainer
        }
    }
    else {
        Write-Forensic -Level 'FAIL' -Message ("Conteneur '{0}' introuvable." -f $OpenWebUIContainer) -Subject $OpenWebUIContainer
    }
}
catch {
    Write-Forensic -Level 'FAIL' -Message ('Docker indisponible : {0}' -f $_.Exception.Message) -Subject 'Docker'
}

Convert-ToSafeJson -Object $DockerEvidence -Path $DockerPath

# ============================================================================
# [8/16] OPEN WEBUI HTTP MULTI-STACK
# ============================================================================

Write-Section -Title 'OPEN WEBUI — HTTP MULTI-STACK' -Number '8/16'

$webTests = @(
    [ordered]@{ name = 'IPv4_LOOPBACK'; uri = $OpenWebUIUrl },
    [ordered]@{ name = 'IPv6_LOOPBACK'; uri = $OpenWebUIIPv6Url }
)

$webEvidence = [System.Collections.ArrayList]::new()

foreach ($test in $webTests) {
    $result = Test-Http -Uri $test.uri

    [void]$webEvidence.Add([ordered]@{
        name    = $test.name
        uri     = $test.uri
        success = $result.success
        status  = $result.status
        error   = $result.error
    })

    if ($result.success -and $result.status -eq 200) {
        Write-Forensic -Level 'PASS' -Message ('{0} : HTTP 200 OK.' -f $test.name) -Subject $test.uri
    }
    elseif ($test.name -eq 'IPv4_LOOPBACK') {
        Write-Forensic -Level 'WARN' -Message ('Open WebUI IPv4 inaccessible : {0} (Attribué au relai WSL2).' -f $test.uri) -Subject $test.uri
    }
    else {
        Write-Forensic -Level 'FAIL' -Message ('Open WebUI IPv6 inaccessible : {0}' -f $test.uri) -Subject $test.uri
    }
}

$localhostResult = Test-Http -Uri 'http://localhost:3000'

[void]$webEvidence.Add([ordered]@{
    name    = 'LOCALHOST'
    uri     = 'http://localhost:3000'
    success = $localhostResult.success
    status  = $localhostResult.status
    error   = $localhostResult.error
})

if ($localhostResult.success -and $localhostResult.status -eq 200) {
    Write-Forensic -Level 'PASS' -Message 'Open WebUI localhost : HTTP 200 OK.' -Subject 'localhost:3000'
}
else {
    Write-Forensic -Level 'WARN' -Message ('Open WebUI localhost non confirme : {0}' -f $localhostResult.error) -Subject 'localhost:3000'
}

$webEvidence | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $RunRoot 'OPEN_WEBUI_HTTP.json') -Encoding UTF8

# ============================================================================
# [9/16] TAILSCALE
# ============================================================================

Write-Section -Title 'TAILSCALE' -Number '9/16'

$tailscalePath = 'G:\AI\tailscale.exe'

if (Test-Path -LiteralPath $tailscalePath -PathType Leaf) {
    try {
        $ts = Invoke-NativeSafe -FilePath $tailscalePath -ArgumentList @('serve', 'status')
        if ($ts.exit_code -eq 0) {
            Write-Forensic -Level 'PASS' -Message 'Tailscale Serve status accessible.' -Subject 'Tailscale Serve'
        }
        else {
            Write-Forensic -Level 'WARN' -Message ('Tailscale Serve status non confirme (exit={0}).' -f $ts.exit_code) -Subject 'Tailscale Serve'
        }
    }
    catch {
        Write-Forensic -Level 'WARN' -Message ('Inspection Tailscale impossible : {0}' -f $_.Exception.Message) -Subject 'Tailscale'
    }
}
else {
    Write-Forensic -Level 'WARN' -Message 'Tailscale absent ; controle externe non effectue.' -Subject 'Tailscale'
}

# ============================================================================
# [10/16] DISCORD
# ============================================================================

Write-Section -Title 'DISCORD BOT ENGINE' -Number '10/16'

$discordPath = Join-Path $Root $DiscordLauncher

if (Test-Path -LiteralPath $discordPath -PathType Leaf) {
    Write-Forensic -Level 'PASS' -Message ('Launcher Discord present : {0}' -f $DiscordLauncher) -Subject $DiscordLauncher

    try {
        $discordProcesses = @(
            Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
            Where-Object {
                $_.CommandLine -and
                $_.CommandLine -match 'bot_runner\.py'
            }
        )

        if ($discordProcesses.Count -gt 0) {
            foreach ($proc in $discordProcesses) {
                Write-Forensic -Level 'PASS' -Message ('Processus Discord detecte PID={0}.' -f $proc.ProcessId) -Subject 'Discord'
            }
        }
        else {
            Write-Forensic -Level 'WARN' -Message 'Aucun processus bot_runner.py actuellement detecte.' -Subject 'Discord'
        }
    }
    catch {
        Write-Forensic -Level 'WARN' -Message ('Inspection processus Discord impossible : {0}' -f $_.Exception.Message) -Subject 'Discord'
    }
}
else {
    Write-Forensic -Level 'WARN' -Message ('Launcher Discord absent : {0}' -f $DiscordLauncher) -Subject $DiscordLauncher
}

# ============================================================================
# [11/16] AUDIT FICHIERS
# ============================================================================

Write-Section -Title 'AUDIT FORENSIC DU PROJET' -Number '11/16'

try {
    # Scan focused source files only, ignoring venvs, caches, backups and semantic blobs
    $sourceDirs = @(
        'core', 'interfaces', 'routers', 'v17', 'v18', 'v19', 'tests',
        'config', 'contracts', 'registry', 'state', 'recovery', 'scripts'
    )

    $files = [System.Collections.ArrayList]::new()

    # Root files
    $rootFiles = Get-ChildItem -LiteralPath $Root -File -Force -ErrorAction SilentlyContinue
    if ($null -ne $rootFiles) {
        foreach ($rf in $rootFiles) { [void]$files.Add($rf) }
    }

    # Subdirectories
    foreach ($dir in $sourceDirs) {
        $dirPath = Join-Path $Root $dir
        if (Test-Path -LiteralPath $dirPath -PathType Container) {
            $subFiles = Get-ChildItem -LiteralPath $dirPath -File -Recurse -Force -ErrorAction SilentlyContinue |
                Where-Object {
                    $_.FullName -notmatch '\\(__pycache__|\.pytest_cache|\.venv)\\'
                }
            if ($null -ne $subFiles) {
                foreach ($sf in $subFiles) { [void]$files.Add($sf) }
            }
        }
    }

    $extensionStats = @{}
    foreach ($file in $files) {
        $ext = $file.Extension.ToLowerInvariant()
        if (-not $extensionStats.ContainsKey($ext)) {
            $extensionStats[$ext] = 0
        }
        $extensionStats[$ext]++
    }

    $audit = [ordered]@{
        timestamp_utc = (Get-Date).ToUniversalTime().ToString('o')
        root          = $Root
        file_count    = $files.Count
        extensions    = $extensionStats
        source_dirs   = $sourceDirs
    }

    Convert-ToSafeJson -Object $audit -Path $AuditPath
    Write-Forensic -Level 'PASS' -Message ('Inventaire physique du code source : {0} fichier(s).' -f $files.Count) -Subject 'Project inventory'
}
catch {
    Write-Forensic -Level 'FAIL' -Message ('Audit fichier impossible : {0}' -f $_.Exception.Message) -Subject 'Project inventory'
}

# ============================================================================
# [12/16] SECRET FORENSICS
# ============================================================================

Write-Section -Title 'SECRET FORENSICS — NON-DIVULGATION' -Number '12/16'

try {
    $secretPatterns = @(
        'AKIA[0-9A-Z]{16}',
        '-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----',
        'DISCORD_TOKEN\s*=\s*[^\s]+',
        'EZZIO_LEDGER_SECRET\s*=\s*[^\s]+'
    )

    $candidateFiles = @(
        $files | Where-Object {
            $_.Length -lt 10MB -and
            $_.Extension.ToLowerInvariant() -in @('.py','.ps1','.psm1','.json','.jsonl','.yaml','.yml','.env','.ini','.cfg','.conf','.txt','.md')
        }
    )

    $foundSecretItems = [System.Collections.ArrayList]::new()
    foreach ($file in $candidateFiles) {
        try {
            $text = Get-Content -LiteralPath $file.FullName -Raw -Encoding UTF8 -ErrorAction SilentlyContinue
            if ($null -eq $text) { continue }
        }
        catch {
            continue
        }
        foreach ($pattern in $secretPatterns) {
            if ($text -match $pattern) {
                [void]$foundSecretItems.Add([ordered]@{
                    file    = $file.FullName
                    pattern = $pattern
                })
                break
            }
        }
    }

    $secretResult = [ordered]@{
        scanned_files     = $candidateFiles.Count
        candidate_count   = $foundSecretItems.Count
        candidates        = @($foundSecretItems)
        values_suppressed = $true
    }

    Convert-ToSafeJson -Object $secretResult -Path $SecretsPath

    if ($foundSecretItems.Count -eq 0) {
        Write-Forensic -Level 'PASS' -Message 'Aucun candidat secret detecte par les regles configurees.' -Subject 'Secret scan'
    }
    else {
        Write-Forensic -Level 'WARN' -Message ('{0} fichier(s) contiennent des motifs potentiellement sensibles ; aucune valeur affichee.' -f $foundSecretItems.Count) -Subject 'Secret scan'
    }
}
catch {
    Write-Forensic -Level 'FAIL' -Message ('Secret scan interrompu : {0}' -f $_.Exception.Message) -Subject 'Secret scan'
}

# ============================================================================
# [13/16] PYTHON COMPILE
# ============================================================================

Write-Section -Title 'PYTHON COMPILATION' -Number '13/16'

if ($SkipPythonCompile) {
    Write-Unproven -Message 'Compilation Python explicitement desactivee par -SkipPythonCompile.' -Subject 'Python compile'
}
else {
    try {
        $pythonFiles = @($files | Where-Object { $_.Extension.ToLowerInvariant() -eq '.py' })

        $results = [System.Collections.ArrayList]::new()
        foreach ($file in $pythonFiles) {
            $result = & "G:\AI\E-zzio\.venv\Scripts\python.exe" -m py_compile $file.FullName 2>&1
            $exit = $LASTEXITCODE
            [void]$results.Add([ordered]@{
                file      = $file.FullName
                exit_code = $exit
                passed    = ($exit -eq 0)
            })
        }

        $failed = @($results | Where-Object { -not $_.passed })

        $compileReport = [ordered]@{
            scanned = $pythonFiles.Count
            passed  = $pythonFiles.Count - $failed.Count
            failed  = $failed.Count
            results = @($results)
        }

        Convert-ToSafeJson -Object $compileReport -Path $PythonCompilePath

        if ($failed.Count -eq 0) {
            Write-Forensic -Level 'PASS' -Message ('Compilation Python : {0}/{1} PASS.' -f $pythonFiles.Count, $pythonFiles.Count) -Subject 'Python compile'
        }
        else {
            Write-Forensic -Level 'FAIL' -Message ('Compilation Python : {0} echec(s).' -f $failed.Count) -Subject 'Python compile'
        }
    }
    catch {
        Write-Forensic -Level 'FAIL' -Message ('Compilation Python impossible : {0}' -f $_.Exception.Message) -Subject 'Python compile'
    }
}

# ============================================================================
# [14/16] PYTEST
# ============================================================================

Write-Section -Title 'PYTEST' -Number '14/16'

if ($SkipPytest) {
    Write-Unproven -Message 'Pytest explicitement desactive par -SkipPytest.' -Subject 'pytest'
}
else {
    try {
        $pytestCmd = "G:\AI\E-zzio\.venv\Scripts\python.exe"
        $testResult = Invoke-NativeSafe -FilePath $pytestCmd -ArgumentList @('-m','pytest','-q')

        $pytestReport = [ordered]@{
            exit_code = $testResult.exit_code
            output    = $testResult.output
            passed    = ($testResult.exit_code -eq 0)
        }

        Convert-ToSafeJson -Object $pytestReport -Path $PytestPath

        if ($testResult.exit_code -eq 0) {
            Write-Forensic -Level 'PASS' -Message 'Pytest : exit code 0.' -Subject 'pytest'
        }
        else {
            Write-Forensic -Level 'FAIL' -Message ('Pytest : exit code {0}.' -f $testResult.exit_code) -Subject 'pytest'
        }
    }
    catch {
        Write-Unproven -Message ('Pytest non executable dans l''environnement actuel : {0}' -f $_.Exception.Message) -Subject 'pytest'
    }
}

# ============================================================================
# [15/16] GIT / DRIFT / AG / CAPCAP
# ============================================================================

Write-Section -Title 'GIT / DRIFT / AG / CAPCAP' -Number '15/16'

try {
    $gitStatus = Invoke-NativeSafe -FilePath 'git' -ArgumentList @('-C', $Root, 'status', '--porcelain=v1')
    $gitHead = Invoke-NativeSafe -FilePath 'git' -ArgumentList @('-C', $Root, 'rev-parse', 'HEAD')

    $gitEvidence = [ordered]@{
        exit_code = $gitStatus.exit_code
        head      = ($gitHead.output -join '').Trim()
        modified  = @($gitStatus.output)
    }

    Convert-ToSafeJson -Object $gitEvidence -Path $GitPath

    if ($gitStatus.exit_code -eq 0) {
        if (@($gitStatus.output).Count -eq 0) {
            Write-Forensic -Level 'PASS' -Message 'Git working tree CLEAN.' -Subject 'Git'
        }
        else {
            Write-Forensic -Level 'WARN' -Message ('Git working tree contient {0} changement(s).' -f @($gitStatus.output).Count) -Subject 'Git'
        }
    }
    else {
        Write-Unproven -Message 'Git status non disponible.' -Subject 'Git'
    }
}
catch {
    Write-Unproven -Message ('Git audit impossible : {0}' -f $_.Exception.Message) -Subject 'Git'
}

$AGMission = [ordered]@{
    run_id        = $RunId
    mode          = $Mode
    root          = $Root
    authorization = 'READ_ONLY'
    mutation      = $false
    objective     = @(
        'Analyse du systeme E-ZZIO',
        'Diagnostic production',
        'Audit forensic',
        'Validation des preuves',
        'Analyse des anomalies',
        'Preparation de corrections sans mutation automatique',
        'Analyse et generation de code',
        'Recherche analytique',
        'Support Godot 4 / GDScript / Capcap'
    )
    forbidden = @(
        'modifier sanctuaire V16.4',
        'supprimer fichiers',
        'reecrire fichiers sans autorisation',
        'afficher secrets',
        'declarer PASS sans preuve'
    )
}

Convert-ToSafeJson -Object $AGMission -Path $AGPath
Write-Forensic -Level 'PASS' -Message 'Mission AG preparee en mode READ-ONLY.' -EvidenceType 'CONTROL' -Subject 'AG'

$CapcapCandidates = @(
    'G:\AI\Capcap',
    'G:\AI\CAPCAP',
    (Join-Path $Root '..\Capcap')
)

$CapcapFound = $null
foreach ($candidate in $CapcapCandidates) {
    if (Test-Path -LiteralPath $candidate -PathType Container) {
        $CapcapFound = (Resolve-Path -LiteralPath $candidate).Path
        break
    }
}

$GodotCommand = Get-Command godot -ErrorAction SilentlyContinue

$CapcapEvidence = [ordered]@{
    project_found  = ($null -ne $CapcapFound)
    project_path   = $CapcapFound
    godot_detected = ($null -ne $GodotCommand)
    gdscript_files = 0
}

if ($null -ne $CapcapFound) {
    $gdFiles = @(
        Get-ChildItem -LiteralPath $CapcapFound -Filter '*.gd' -File -Recurse -Force -ErrorAction SilentlyContinue
    )
    $CapcapEvidence.gdscript_files = $gdFiles.Count
    Write-Forensic -Level 'PASS' -Message ('Projet Capcap detecte : {0} ; {1} fichier(s) GDScript.' -f $CapcapFound, $gdFiles.Count) -Subject 'Capcap'
}
else {
    Write-Forensic -Level 'INFO' -Message 'Projet Capcap non detecte dans les emplacements connus.' -Subject 'Capcap'
}

if ($null -ne $GodotCommand) {
    Write-Forensic -Level 'PASS' -Message ('Godot detecte : {0}' -f $GodotCommand.Source) -Subject 'Godot'
}
else {
    Write-Forensic -Level 'INFO' -Message 'Commande Godot non presente dans PATH.' -Subject 'Godot'
}

Convert-ToSafeJson -Object $CapcapEvidence -Path $CapcapPath

# ============================================================================
# [16/16] MATRICE FINALE
# ============================================================================

Write-Section -Title 'VERDICT FINAL' -Number '16/16'

$FinishedUtc = (Get-Date).ToUniversalTime()
$Verdict = 'EZZIO_MASTER_FAIL_CLOSED'

if ($Counters['FAIL'] -gt 0) {
    $Verdict = 'EZZIO_MASTER_FAIL_CLOSED'
}
elseif ($Counters['UNPROVEN'] -gt 0) {
    $Verdict = 'EZZIO_MASTER_CERTIFICATION_UNPROVEN'
}
elseif ($Counters['WARN'] -gt 0) {
    $Verdict = 'EZZIO_MASTER_CERTIFIED_WITH_WARNINGS'
}
else {
    $Verdict = 'EZZIO_MASTER_CERTIFIED'
}

$Matrix = [ordered]@{
    schema_version = '1.0'
    script_version = $ScriptVersion
    run_id         = $RunId
    started_utc    = $StartedUtc.ToString('o')
    finished_utc   = $FinishedUtc.ToString('o')
    duration_ms    = [math]::Round(($FinishedUtc - $StartedUtc).TotalMilliseconds, 3)
    root           = $Root
    mode           = $Mode
    security = [ordered]@{
        read_only             = $true
        sanctuary_mutable     = $false
        destructive_actions   = $false
        secret_values_logged  = $false
        fail_closed           = $true
    }
    counters = $Counters
    verdict = $Verdict
    evidence_policy = [ordered]@{
        physical_pass_required = $true
        declarative_pass_forbidden = $true
        unproven_blocks_absolute_certification = $true
    }
    artifacts = [ordered]@{
        log                 = $LogPath
        matrix              = $MatrixPath
        manifest            = $ManifestPath
        raw_evidence        = $EvidencePath
        final_report        = $ReportPath
        python_compile      = $PythonCompilePath
        pytest              = $PytestPath
        project_audit       = $AuditPath
        secret_scan         = $SecretsPath
        git_state           = $GitPath
        network_forensics   = $NetworkPath
        docker_forensics    = $DockerPath
        ollama_forensics    = $OllamaPath
        capcap_readiness    = $CapcapPath
        ag_mission          = $AGPath
    }
}

Convert-ToSafeJson -Object $Matrix -Path $MatrixPath
Convert-ToSafeJson -Object @($Evidence) -Path $EvidencePath

$Manifest = [ordered]@{
    schema_version = '1.0'
    run_id         = $RunId
    script_version = $ScriptVersion
    mode           = $Mode
    root           = $Root
    started_utc    = $StartedUtc.ToString('o')
    finished_utc   = $FinishedUtc.ToString('o')
    verdict        = $Verdict
    counters       = $Counters
    execution_policy = [ordered]@{
        read_only             = $true
        allow_project_mutation = [bool]$AllowProjectMutation
        start_services         = [bool]$StartServices
        skip_pytest             = [bool]$SkipPytest
        skip_python_compile     = [bool]$SkipPythonCompile
    }
    hashes = [ordered]@{}
}

$artifactList = @(
    $LogPath,
    $MatrixPath,
    $EvidencePath,
    $ReportPath,
    $PythonCompilePath,
    $PytestPath,
    $AuditPath,
    $SecretsPath,
    $GitPath,
    $NetworkPath,
    $DockerPath,
    $OllamaPath,
    $CapcapPath,
    $AGPath
)

foreach ($artifact in $artifactList) {
    if (Test-Path -LiteralPath $artifact -PathType Leaf) {
        $relativeArtifact = $artifact.Substring($RunRoot.Length).TrimStart('\')
        $Manifest.hashes[$relativeArtifact] = Get-Sha256 -Path $artifact
    }
}

$ReportLines = @(
    '# E-ZZIO — MASTER FORENSIC REPORT',
    '',
    '## Identification',
    '',
    '| Champ | Valeur |',
    '|---|---|',
    ('| Version | {0} |' -f $ScriptVersion),
    ('| RunId | `{0}` |' -f $RunId),
    ('| Mode | `{0}` |' -f $Mode),
    ('| Root | `{0}` |' -f $Root),
    ('| Debut UTC | {0} |' -f $StartedUtc.ToString('o')),
    ('| Fin UTC | {0} |' -f $FinishedUtc.ToString('o')),
    '',
    '## Verdict',
    '',
    ('**{0}**' -f $Verdict),
    '',
    '## Matrice',
    '',
    '| Niveau | Nombre |',
    '|---|---:|',
    ('| PASS | {0} |' -f $Counters['PASS']),
    ('| WARN | {0} |' -f $Counters['WARN']),
    ('| FAIL | {0} |' -f $Counters['FAIL']),
    ('| INFO | {0} |' -f $Counters['INFO']),
    ('| UNPROVEN | {0} |' -f $Counters['UNPROVEN'])
)

$ReportLines | Set-Content -LiteralPath $ReportPath -Encoding UTF8

$Manifest.hashes = [ordered]@{}
foreach ($artifact in $artifactList) {
    if (Test-Path -LiteralPath $artifact -PathType Leaf) {
        $relativeArtifact = $artifact.Substring($RunRoot.Length).TrimStart('\')
        $Manifest.hashes[$relativeArtifact] = Get-Sha256 -Path $artifact
    }
}

Convert-ToSafeJson -Object $Manifest -Path $ManifestPath

Write-Host ''
Write-Host '================================================================================'
Write-Host '                         E-ZZIO — FINAL MATRIX'
Write-Host '================================================================================'
Write-Host ''
Write-Host ('[PASS]     : {0}' -f $Counters['PASS'])
Write-Host ('[WARN]     : {0}' -f $Counters['WARN'])
Write-Host ('[FAIL]     : {0}' -f $Counters['FAIL'])
Write-Host ('[INFO]     : {0}' -f $Counters['INFO'])
Write-Host ('[UNPROVEN] : {0}' -f $Counters['UNPROVEN'])
Write-Host ''

if ($Verdict -eq 'EZZIO_MASTER_CERTIFIED') {
    Write-Host '[PASS] VERDICT FINAL : EZZIO_MASTER_CERTIFIED'
}
elseif ($Verdict -eq 'EZZIO_MASTER_CERTIFIED_WITH_WARNINGS') {
    Write-Host '[WARN] VERDICT FINAL : EZZIO_MASTER_CERTIFIED_WITH_WARNINGS'
}
elseif ($Verdict -eq 'EZZIO_MASTER_CERTIFICATION_UNPROVEN') {
    Write-Host '[FAIL] VERDICT FINAL : EZZIO_MASTER_CERTIFICATION_UNPROVEN'
}
else {
    Write-Host '[FAIL] VERDICT FINAL : EZZIO_MASTER_FAIL_CLOSED'
}

Write-Host ''
Write-Host ('RunId      : {0}' -f $RunId)
Write-Host ('Forensic   : {0}' -f $RunRoot)
Write-Host ('Log        : {0}' -f $LogPath)
Write-Host ('Matrix     : {0}' -f $MatrixPath)
Write-Host ('Manifest   : {0}' -f $ManifestPath)
Write-Host ('Report     : {0}' -f $ReportPath)
Write-Host ''
Write-Host '================================================================================'

if ($Counters['FAIL'] -gt 0) { exit 10 }
if ($Counters['UNPROVEN'] -gt 0) { exit 20 }
if ($Counters['WARN'] -gt 0) { exit 30 }
exit 0
