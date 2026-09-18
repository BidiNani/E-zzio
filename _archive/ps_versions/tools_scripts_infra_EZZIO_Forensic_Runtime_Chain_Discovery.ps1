Set-StrictMode -Version Latest
$ErrorActionPreference = 'Continue'

Set-Location 'G:\AI\E-zzio'

Write-Host ''
Write-Host '================================================================================' -ForegroundColor Cyan
Write-Host 'E-ZZIO — FORENSIC RUNTIME CHAIN DISCOVERY' -ForegroundColor Cyan
Write-Host '================================================================================' -ForegroundColor Cyan

# ==============================================================================
# 1. PROCESSUS RÉEL
# ==============================================================================

Write-Host ''
Write-Host '[1] PROCESSUS API ACTUEL' -ForegroundColor Yellow

$apiConnections = @(Get-NetTCPConnection `
    -State Listen `
    -LocalPort 8001 `
    -ErrorAction SilentlyContinue)

if ($apiConnections.Count -eq 0) {
    Write-Host '[FAIL] Aucun listener sur 8001.' -ForegroundColor Red
}
else {
    foreach ($conn in $apiConnections) {
        Write-Host "Address : $($conn.LocalAddress)"
        Write-Host "Port    : $($conn.LocalPort)"
        Write-Host "PID     : $($conn.OwningProcess)"

        $proc = Get-CimInstance Win32_Process `
            -Filter "ProcessId=$($conn.OwningProcess)" `
            -ErrorAction SilentlyContinue

        if ($proc) {
            Write-Host "Name    : $($proc.Name)"
            Write-Host "Command : $($proc.CommandLine)"
        }
    }
}

# ==============================================================================
# 2. WEB_SERVER.PY
# ==============================================================================

Write-Host ''
Write-Host '[2] WEB_SERVER.PY — CHAÎNE D''IMPORT' -ForegroundColor Yellow

if (Test-Path '.\web_server.py') {
    $webServer = Get-Content '.\web_server.py' -Raw

    Write-Host ''
    Write-Host '--- imports / routers ---'

    $webServer |
        Select-String `
            -Pattern '^(from|import)|include_router|FastAPI|uvicorn' `
            -AllMatches |
        ForEach-Object {
            Write-Host $_.Line
        }
}
else {
    Write-Host '[FAIL] web_server.py introuvable.' -ForegroundColor Red
}

# ==============================================================================
# 3. MASTER ROUTER
# ==============================================================================

Write-Host ''
Write-Host '[3] LOCALISATION DE MASTER_ROUTER' -ForegroundColor Yellow

$masterCandidates = @(
    '.\routers\master.py',
    '.\routers\__init__.py'
)

foreach ($candidate in $masterCandidates) {

    if (Test-Path $candidate) {

        Write-Host ''
        Write-Host "--- $candidate ---" -ForegroundColor Green

        Get-Content $candidate |
            Select-String `
                -Pattern '^(from|import)|include_router|APIRouter|router|FastAPI' `
                -AllMatches |
            ForEach-Object {
                Write-Host $_.Line
            }
    }
    else {
        Write-Host "[ABSENT] $candidate" -ForegroundColor DarkGray
    }
}

# ==============================================================================
# 4. INCLUDE_ROUTER
# ==============================================================================

Write-Host ''
Write-Host '[4] TOUS LES INCLUDE_ROUTER DU CODE SOURCE' -ForegroundColor Yellow

Get-ChildItem . `
    -Recurse `
    -File `
    -Filter '*.py' `
    -ErrorAction SilentlyContinue |
    Where-Object {
        $_.FullName -notmatch '\\(\.venv|venv|__pycache__|site-packages|_EZZIO_TRUTH_REPORTS|runtime\\audit)\\'
    } |
    Select-String `
        -Pattern 'include_router\s*\(' `
        -AllMatches `
        -ErrorAction SilentlyContinue |
    Select-Object Path, LineNumber, Line |
    Format-Table -AutoSize

# ==============================================================================
# 5. ROUTES DIRECTES
# ==============================================================================

Write-Host ''
Write-Host '[5] ROUTES DÉCLARÉES DIRECTEMENT DANS LE CODE SOURCE' -ForegroundColor Yellow

Get-ChildItem . `
    -Recurse `
    -File `
    -Filter '*.py' `
    -ErrorAction SilentlyContinue |
    Where-Object {
        $_.FullName -notmatch '\\(\.venv|venv|__pycache__|site-packages|_EZZIO_TRUTH_REPORTS|runtime\\audit)\\'
    } |
    Select-String `
        -Pattern '@(app|router)\.(get|post|put|patch|delete|options|head|websocket)\s*\(' `
        -AllMatches `
        -ErrorAction SilentlyContinue |
    Select-Object Path, LineNumber, Line |
    Format-Table -AutoSize

# ==============================================================================
# 6. OPENAPI RÉEL
# ==============================================================================

Write-Host ''
Write-Host '[6] OPENAPI DU SERVEUR VIVANT' -ForegroundColor Yellow

try {

    $openapi = Invoke-RestMethod `
        -Uri 'http://127.0.0.1:8001/openapi.json' `
        -Method Get `
        -TimeoutSec 10 `
        -ErrorAction Stop

    $runtimeRoutes = @(
        $openapi.paths.PSObject.Properties |
        ForEach-Object {

            $path = $_.Name

            $methods = @(
                $_.Value.PSObject.Properties.Name |
                Where-Object {
                    $_ -match '^(get|post|put|patch|delete|options|head|trace)$'
                }
            )

            foreach ($method in $methods) {
                [PSCustomObject]@{
                    Method = $method.ToUpper()
                    Path   = $path
                }
            }
        }
    )

    Write-Host "ROUTES RUNTIME : $($runtimeRoutes.Count)" -ForegroundColor Green

    $runtimeRoutes |
        Sort-Object Path, Method |
        Format-Table -AutoSize
}
catch {
    Write-Host "[FAIL] /openapi.json : $($_.Exception.Message)" -ForegroundColor Red
}

# ==============================================================================
# 7. RECHERCHE DU BUG 8001.SPLIT
# ==============================================================================

Write-Host ''
Write-Host '[7] RECHERCHE DU BUG 8001.SPLIT' -ForegroundColor Yellow

$splitHits = @(
    Get-ChildItem . `
        -Recurse `
        -File `
        -Include '*.ps1','*.py' `
        -ErrorAction SilentlyContinue |
    Where-Object {
        $_.FullName -notmatch '\\(\.venv|venv|__pycache__|site-packages|_EZZIO_TRUTH_REPORTS)\\'
    } |
    Select-String `
        -Pattern '8001\.Split|Split.*8001|8001.*Split|\.Split\s*\(' `
        -AllMatches `
        -ErrorAction SilentlyContinue
)

if ($splitHits.Count -eq 0) {
    Write-Host '[INFO] Aucun motif direct trouvé.' -ForegroundColor DarkGray
}
else {
    $splitHits |
        Select-Object Path, LineNumber, Line |
        Format-Table -AutoSize
}

# ==============================================================================
# 8. LAUNCHERS
# ==============================================================================

Write-Host ''
Write-Host '[8] LAUNCHERS E-ZZIO' -ForegroundColor Yellow

Get-ChildItem . `
    -Recurse `
    -File `
    -Filter '*.ps1' `
    -ErrorAction SilentlyContinue |
    Where-Object {
        $_.Name -match 'start|launch|run|daemon|supervis'
    } |
    Where-Object {
        $_.FullName -notmatch '\\(\.venv|venv|site-packages|_EZZIO_TRUTH_REPORTS)\\'
    } |
    Select-Object FullName, Length, LastWriteTime |
    Sort-Object FullName |
    Format-Table -AutoSize

# ==============================================================================
# 9. FIN
# ==============================================================================

Write-Host ''
Write-Host '================================================================================' -ForegroundColor Cyan
Write-Host 'END FORENSIC RUNTIME CHAIN DISCOVERY' -ForegroundColor Cyan
Write-Host '================================================================================' -ForegroundColor Cyan
