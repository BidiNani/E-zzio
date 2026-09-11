#requires -Version 7.4
<#
===============================================================================
 E-ZZIO — MASTER PRODUCTION / FORENSIC PRODUCER V3
 Version : 3.0.0
 Plane   : PLANE 1 (E-ZZIO PRODUCER)
 Role    : Collects primary evidence and produces verifiable forensic artifacts.
           Does NOT decide its own certification verdict (delegated to AG Arbiter).
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

$ScriptVersion = '3.0.0'
$RunId = 'run_master_v3_' + (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssfffZ') + '_' + [Guid]::NewGuid().ToString('N').Substring(0,12)
$StartedUtc = (Get-Date).ToUniversalTime()

$ForensicRoot = Join-Path $Root '_forensic\master'
$RunRoot = Join-Path $ForensicRoot $RunId
$RawDir = Join-Path $RunRoot 'raw'

# Create run directories
if (-not (Test-Path -LiteralPath $RawDir -PathType Container)) {
    New-Item -ItemType Directory -Path $RawDir -Force | Out-Null
}

$LogPath = Join-Path $RunRoot 'PRODUCER_EXECUTION.log'
$ManifestPath = Join-Path $RunRoot 'PRODUCER_RUN_MANIFEST.json'
$TelemetryPath = Join-Path $RawDir 'PRODUCER_TELEMETRY.json'
$SanctuaryPath = Join-Path $RawDir 'SANCTUARY_SNAPSHOT.json'
$PythonCompilePath = Join-Path $RawDir 'PYTHON_COMPILE_DATA.json'
$PytestPath = Join-Path $RawDir 'PYTEST_STRUCTURED_DATA.json'
$AuditPath = Join-Path $RawDir 'PROJECT_AUDIT_DATA.json'
$SecretsPath = Join-Path $RawDir 'SECRET_SCAN_DATA.json'
$GitPath = Join-Path $RawDir 'GIT_STATE_DATA.json'
$NetworkPath = Join-Path $RawDir 'NETWORK_MULTISTACK_DATA.json'
$DockerPath = Join-Path $RawDir 'DOCKER_INSPECT_DATA.json'
$OllamaPath = Join-Path $RawDir 'OLLAMA_TAGS_DATA.json'
$CapcapPath = Join-Path $RawDir 'CAPCAP_INVENTORY_DATA.json'
$PreSnapshotPath = Join-Path $RawDir 'PRE_RUN_FILE_SNAPSHOT.json'
$PostSnapshotPath = Join-Path $RawDir 'POST_RUN_FILE_SNAPSHOT.json'

function Write-ProducerLog {
    param([string]$Msg)
    $Now = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ss.fffZ')
    $Line = ('[{0}] [PRODUCER] {1}' -f $Now, $Msg)
    Write-Host $Line
    Add-Content -LiteralPath $LogPath -Value $Line -Encoding UTF8
}

function Get-FileSha256 {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $null }
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Save-SafeJson {
    param([object]$Obj, [string]$Path, [int]$Depth = 12)
    $Obj | ConvertTo-Json -Depth $Depth | Set-Content -LiteralPath $Path -Encoding UTF8
}

Write-ProducerLog ("Demarrage Producer V3 - RunId: {0}" -f $RunId)

# ----------------------------------------------------------------------------
# 1. Pre-Run Filesystem Snapshot (for Mutation Watchdog)
# ----------------------------------------------------------------------------
$sourceDirs = @('core', 'interfaces', 'routers', 'v17', 'v18', 'v19', 'tests', 'config', 'contracts', 'registry', 'state', 'recovery', 'scripts')
$preFiles = @{}
foreach ($dir in $sourceDirs) {
    $dp = Join-Path $Root $dir
    if (Test-Path -LiteralPath $dp -PathType Container) {
        $items = Get-ChildItem -LiteralPath $dp -File -Recurse -Force -ErrorAction SilentlyContinue |
            Where-Object { $_.FullName -notmatch '\\(__pycache__|\.pytest_cache|\.venv)\\' }
        foreach ($it in $items) {
            $rel = $it.FullName.Substring($Root.Length).TrimStart('\').Replace('\', '/')
            $preFiles[$rel] = @{
                length = $it.Length
                last_write = $it.LastWriteTimeUtc.ToString('o')
                sha256 = (Get-FileSha256 -Path $it.FullName)
            }
        }
    }
}
Save-SafeJson -Obj $preFiles -Path $PreSnapshotPath
Write-ProducerLog ("Snapshot Pre-Run realise : {0} fichiers inventories." -f $preFiles.Count)

# ----------------------------------------------------------------------------
# 2. Environment & PowerShell target check
# ----------------------------------------------------------------------------
$envData = [ordered]@{
    run_id             = $RunId
    ps_version         = $PSVersionTable.PSVersion.ToString()
    ps_edition         = $PSVersionTable.PSEdition
    os_version         = [System.Environment]::OSVersion.VersionString
    python_path        = (Get-Command python -ErrorAction SilentlyContinue).Source
    docker_path        = (Get-Command docker -ErrorAction SilentlyContinue).Source
    git_path           = (Get-Command git -ErrorAction SilentlyContinue).Source
    curl_path          = (Get-Command curl -ErrorAction SilentlyContinue).Source
    tailscale_path     = 'G:\AI\tailscale.exe'
    tailscale_exists   = (Test-Path -LiteralPath 'G:\AI\tailscale.exe' -PathType Leaf)
}

# ----------------------------------------------------------------------------
# 3. Sanctuary Anchors Physical Snapshot
# ----------------------------------------------------------------------------
$sanctuarySnapshot = [ordered]@{
    run_id       = $RunId
    anchors = [ordered]@{
        'MASTER_KNOWLEDGE.json' = [ordered]@{
            path   = '_forensic/knowledge/MASTER_KNOWLEDGE.json'
            sha256 = (Get-FileSha256 -Path (Join-Path $Root '_forensic\knowledge\MASTER_KNOWLEDGE.json'))
            length = (Get-Item -LiteralPath (Join-Path $Root '_forensic\knowledge\MASTER_KNOWLEDGE.json')).Length
        }
        'FILE_HASHES.json' = [ordered]@{
            path   = '_forensic/knowledge/FILE_HASHES.json'
            sha256 = (Get-FileSha256 -Path (Join-Path $Root '_forensic\knowledge\FILE_HASHES.json'))
            length = (Get-Item -LiteralPath (Join-Path $Root '_forensic\knowledge\FILE_HASHES.json')).Length
        }
        'drift_detector.py' = [ordered]@{
            path   = 'core/knowledge/drift_detector.py'
            sha256 = (Get-FileSha256 -Path (Join-Path $Root 'core\knowledge\drift_detector.py'))
            length = (Get-Item -LiteralPath (Join-Path $Root 'core\knowledge\drift_detector.py')).Length
        }
    }
}
Save-SafeJson -Obj $sanctuarySnapshot -Path $SanctuaryPath
Write-ProducerLog "Sanctuaire : Snapshot des ancres cryptographiques capture."

# ----------------------------------------------------------------------------
# 4. Multi-Layer Network Matrix
# ----------------------------------------------------------------------------
function Test-PortAsync {
    param([string]$H, [int]$P, [int]$Timeout = 2000)
    try {
        $c = [System.Net.Sockets.TcpClient]::new()
        $t = $c.ConnectAsync($H, $P)
        if (-not $t.Wait($Timeout)) { $c.Dispose(); return $false }
        $ok = $c.Connected
        $c.Dispose()
        return $ok
    } catch { return $false }
}

function Test-HttpAsync {
    param([string]$Uri, [int]$TimeoutSec = 4)
    try {
        $r = Invoke-WebRequest -Uri $Uri -Method GET -TimeoutSec $TimeoutSec -UseBasicParsing -ErrorAction Stop
        return @{ success = $true; status = [int]$r.StatusCode; err = $null }
    } catch {
        return @{ success = $false; status = $null; err = $_.Exception.Message }
    }
}

$netMatrix = [ordered]@{
    run_id       = $RunId
    timestamp    = (Get-Date).ToUniversalTime().ToString('o')
    tcp_layers = [ordered]@{
        'ezzio_api_ipv4_8000'   = (Test-PortAsync -H '127.0.0.1' -P 8000)
        'open_webui_ipv4_3000'  = (Test-PortAsync -H '127.0.0.1' -P 3000)
        'open_webui_ipv6_3000'  = (Test-PortAsync -H '::1' -P 3000)
        'ollama_ipv4_11434'     = (Test-PortAsync -H '127.0.0.1' -P 11434)
    }
    http_layers = [ordered]@{
        'ezzio_api'             = (Test-HttpAsync -Uri $ApiUrl)
        'open_webui_ipv4'       = (Test-HttpAsync -Uri $OpenWebUIUrl)
        'open_webui_ipv6'       = (Test-HttpAsync -Uri $OpenWebUIIPv6Url)
        'open_webui_localhost'  = (Test-HttpAsync -Uri 'http://localhost:3000')
        'ollama_tags'           = (Test-HttpAsync -Uri ($OllamaUrl + '/api/tags'))
    }
}
Save-SafeJson -Obj $netMatrix -Path $NetworkPath
Write-ProducerLog "Reseau : Matrice multi-couches physique enregistree."

# ----------------------------------------------------------------------------
# 5. Ollama Tags Physical Probe
# ----------------------------------------------------------------------------
$ollamaData = [ordered]@{
    run_id    = $RunId
    reachable = $false
    models    = @()
}
try {
    $tags = Invoke-RestMethod -Uri ($OllamaUrl + '/api/tags') -Method GET -TimeoutSec 5 -ErrorAction Stop
    $ollamaData.reachable = $true
    $ollamaData.models = @($tags.models | ForEach-Object { [ordered]@{ name = $_.name; model = $_.model; size = $_.size } })
} catch {
    $ollamaData.error = $_.Exception.Message
}
Save-SafeJson -Obj $ollamaData -Path $OllamaPath

# ----------------------------------------------------------------------------
# 6. Docker & Container Inspection Probe
# ----------------------------------------------------------------------------
$dockerData = [ordered]@{
    run_id           = $RunId
    docker_available = $false
    container_found  = $false
    running          = $false
    health           = $null
    ports            = $null
}
try {
    $dcmd = (Get-Command docker -ErrorAction Stop).Source
    $dockerData.docker_available = $true
    $dinspect = & $dcmd inspect $OpenWebUIContainer 2>&1
    if ($LASTEXITCODE -eq 0) {
        $dockerData.container_found = $true
        $cjson = $dinspect -join "`n" | ConvertFrom-Json
        if ($cjson.Count -gt 0) {
            $c = $cjson[0]
            $dockerData.running = ($c.State.Status -eq 'running')
            $dockerData.health = $c.State.Health.Status
            $dockerData.ports = $c.NetworkSettings.Ports
        }
    }
} catch {
    $dockerData.error = $_.Exception.Message
}
Save-SafeJson -Obj $dockerData -Path $DockerPath

# ----------------------------------------------------------------------------
# 7. Python Bytecode Compilation Probe
# ----------------------------------------------------------------------------
$pyCompileData = [ordered]@{
    run_id   = $RunId
    scanned  = 0
    passed   = 0
    failed   = 0
    failures = @()
}
$pyFiles = [System.Collections.ArrayList]::new()
foreach ($dir in $sourceDirs) {
    $dp = Join-Path $Root $dir
    if (Test-Path -LiteralPath $dp -PathType Container) {
        $pys = Get-ChildItem -LiteralPath $dp -Filter '*.py' -File -Recurse -Force -ErrorAction SilentlyContinue |
            Where-Object { $_.FullName -notmatch '\\(__pycache__|\.pytest_cache|\.venv)\\' }
        if ($null -ne $pys) { foreach ($p in $pys) { [void]$pyFiles.Add($p) } }
    }
}
$pyCompileData.scanned = $pyFiles.Count
foreach ($pf in $pyFiles) {
    $res = & "G:\AI\E-zzio\.venv\Scripts\python.exe" -m py_compile $pf.FullName 2>&1
    if ($LASTEXITCODE -eq 0) {
        $pyCompileData.passed++
    } else {
        $pyCompileData.failed++
        [void]$pyCompileData.failures.Add($pf.FullName.Substring($Root.Length).TrimStart('\'))
    }
}
Save-SafeJson -Obj $pyCompileData -Path $PythonCompilePath
Write-ProducerLog ("Compilation Python : {0}/{1} passes." -f $pyCompileData.passed, $pyCompileData.scanned)

# ----------------------------------------------------------------------------
# 8. Pytest Structured Metric Probe
# ----------------------------------------------------------------------------
$pytestScript = @"
import pytest, json
class StructuredCollector:
    def __init__(self):
        self.collected = 0
        self.executed = 0
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.xfailed = 0
        self.xpassed = 0
        self.errors = 0
    def pytest_collection_finish(self, session):
        self.collected = len(session.items)
    def pytest_runtest_logreport(self, report):
        if report.when == 'call':
            self.executed += 1
            if report.passed: self.passed += 1
            elif report.failed: self.failed += 1
            elif report.skipped: self.skipped += 1
        elif report.when in ('setup', 'teardown') and report.failed:
            self.errors += 1

collector = StructuredCollector()
exit_code = pytest.main(['-q'], plugins=[collector])
collector.invariant_verified = (collector.executed == collector.passed + collector.failed + collector.skipped + collector.xfailed)
collector.exit_code = int(exit_code)
print('PYTEST_JSON_START:' + json.dumps(collector.__dict__) + ':PYTEST_JSON_END')
"@
$pytestRaw = & "G:\AI\E-zzio\.venv\Scripts\python.exe" -c $pytestScript 2>&1
$pytestOut = $pytestRaw -join "`n"
if ($pytestOut -match 'PYTEST_JSON_START:(.*?):PYTEST_JSON_END') {
    $parsedPytest = $Matches[1] | ConvertFrom-Json
    Save-SafeJson -Obj $parsedPytest -Path $PytestPath
    Write-ProducerLog ("Pytest : COLLECTED={0}, EXECUTED={1}, PASSED={2}, FAILED={3}" -f $parsedPytest.collected, $parsedPytest.executed, $parsedPytest.passed, $parsedPytest.failed)
}

# ----------------------------------------------------------------------------
# 9. Secret Classification Probe (Zero Exposure)
# ----------------------------------------------------------------------------
$rules = @(
    @{ name='AWS_ACCESS_KEY'; pattern='AKIA[0-9A-Z]{16}'; category='CREDENTIAL_KEY' },
    @{ name='RSA_PRIVATE_KEY'; pattern='-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----'; category='PRIVATE_KEY' },
    @{ name='DISCORD_TOKEN_VAR'; pattern='DISCORD_TOKEN\s*=\s*[^\s]+'; category='ENV_DECLARATION' },
    @{ name='LEDGER_SECRET_VAR'; pattern='EZZIO_LEDGER_SECRET\s*=\s*[^\s]+'; category='ENV_DECLARATION' }
)
$classifiedSecrets = [System.Collections.ArrayList]::new()
foreach ($dir in $sourceDirs) {
    $dp = Join-Path $Root $dir
    if (Test-Path -LiteralPath $dp -PathType Container) {
        $cands = Get-ChildItem -LiteralPath $dp -File -Recurse -Force -ErrorAction SilentlyContinue |
            Where-Object {
                $_.Length -lt 10MB -and
                $_.Extension.ToLowerInvariant() -in @('.py','.ps1','.psm1','.json','.jsonl','.yaml','.yml','.env','.ini','.cfg','.conf','.txt','.md') -and
                $_.FullName -notmatch '\\(__pycache__|\.pytest_cache|\.venv)\\'
            }
        foreach ($f in $cands) {
            $lines = @(Get-Content -LiteralPath $f.FullName -Encoding UTF8 -ErrorAction SilentlyContinue)
            if ($null -eq $lines) { continue }
            for ($i = 0; $i -lt $lines.Count; $i++) {
                foreach ($r in $rules) {
                    if ($lines[$i] -match $r.pattern) {
                        $mval = $Matches[0]
                        $sha = [System.Security.Cryptography.SHA256]::Create()
                        $fp = -join ($sha.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($mval)) | ForEach-Object { '{0:x2}' -f $_ })
                        [void]$classifiedSecrets.Add([ordered]@{
                            file                 = $f.FullName.Substring($Root.Length).TrimStart('\').Replace('\', '/')
                            line                 = $i + 1
                            rule                 = $r.name
                            category             = $r.category
                            value_exposed        = $false
                            redacted_fingerprint = $fp
                        })
                        break
                    }
                }
            }
        }
    }
}
$secretData = [ordered]@{
    run_id           = $RunId
    classified_count = $classifiedSecrets.Count
    candidates       = @($classifiedSecrets)
    values_exposed   = $false
}
Save-SafeJson -Obj $secretData -Path $SecretsPath

# ----------------------------------------------------------------------------
# 10. Post-Run Filesystem Snapshot (for Mutation Watchdog)
# ----------------------------------------------------------------------------
$postFiles = @{}
foreach ($dir in $sourceDirs) {
    $dp = Join-Path $Root $dir
    if (Test-Path -LiteralPath $dp -PathType Container) {
        $items = Get-ChildItem -LiteralPath $dp -File -Recurse -Force -ErrorAction SilentlyContinue |
            Where-Object { $_.FullName -notmatch '\\(__pycache__|\.pytest_cache|\.venv)\\' }
        foreach ($it in $items) {
            $rel = $it.FullName.Substring($Root.Length).TrimStart('\').Replace('\', '/')
            $postFiles[$rel] = @{
                length = $it.Length
                last_write = $it.LastWriteTimeUtc.ToString('o')
                sha256 = (Get-FileSha256 -Path $it.FullName)
            }
        }
    }
}
Save-SafeJson -Obj $postFiles -Path $PostSnapshotPath

# ----------------------------------------------------------------------------
# 11. Git State Probe
# ----------------------------------------------------------------------------
$gitHead = & git -C $Root rev-parse HEAD 2>&1
$gitStatus = & git -C $Root status --porcelain=v1 2>&1
$gitData = [ordered]@{
    run_id   = $RunId
    head     = ($gitHead -join '').Trim()
    modified = @($gitStatus | ForEach-Object { "$_" })
}
Save-SafeJson -Obj $gitData -Path $GitPath

# ----------------------------------------------------------------------------
# 12. Capcap Inventory Probe
# ----------------------------------------------------------------------------
$capFound = Test-Path -LiteralPath 'G:\AI\Capcap' -PathType Container
$capData = [ordered]@{
    run_id        = $RunId
    capcap_found  = $capFound
    godot_present = ($null -ne (Get-Command godot -ErrorAction SilentlyContinue))
}
Save-SafeJson -Obj $capData -Path $CapcapPath

# ----------------------------------------------------------------------------
# 13. Telemetry & Producer Manifest
# ----------------------------------------------------------------------------
$FinishedUtc = (Get-Date).ToUniversalTime()
$telemetry = [ordered]@{
    producer_version = $ScriptVersion
    plane            = 'PLANE_1_PRODUCER'
    run_id           = $RunId
    started_utc      = $StartedUtc.ToString('o')
    finished_utc     = $FinishedUtc.ToString('o')
    duration_ms      = [math]::Round(($FinishedUtc - $StartedUtc).TotalMilliseconds, 3)
    root             = $Root
    mode             = $Mode
    environment      = $envData
}
Save-SafeJson -Obj $telemetry -Path $TelemetryPath

$manifest = [ordered]@{
    schema_version   = '3.0'
    plane            = 'PLANE_1_PRODUCER'
    producer         = 'EZZIO_Master_Orchestrator_V3.ps1'
    run_id           = $RunId
    started_utc      = $StartedUtc.ToString('o')
    finished_utc     = $FinishedUtc.ToString('o')
    primary_evidence = [ordered]@{}
}

$rawFiles = Get-ChildItem -LiteralPath $RawDir -File
foreach ($rf in $rawFiles) {
    $manifest.primary_evidence[$rf.Name] = [ordered]@{
        size_bytes = $rf.Length
        sha256     = (Get-FileSha256 -Path $rf.FullName)
        created    = $rf.CreationTimeUtc.ToString('o')
        modified   = $rf.LastWriteTimeUtc.ToString('o')
    }
}
Save-SafeJson -Obj $manifest -Path $ManifestPath

Write-ProducerLog "Primary Evidence scellee avec succes."
Write-ProducerLog ("RunId : {0}" -f $RunId)
Write-ProducerLog ("Manifeste Producer : {0}" -f $ManifestPath)
Write-Host ""
Write-Host "================================================================================"
Write-Host "             E-ZZIO PRODUCER V3 — PRIMARY EVIDENCE GENERATED"
Write-Host "================================================================================"
Write-Host ("RunId     : " + $RunId)
Write-Host ("Location  : " + $RunRoot)
Write-Host ("Manifest  : " + $ManifestPath)
Write-Host "STATUS    : PRIMARY EVIDENCE READY FOR INDEPENDENT ARBITRATION"
Write-Host "================================================================================"
exit 0
