# ============================================================================
# E-ZZIO — OFFICIAL SERVER LAUNCHER
# Runtime Python officiel E-ZZIO
# ============================================================================

& {

    Set-StrictMode -Version Latest
    $ErrorActionPreference = 'Stop'

    $ProjectRoot = 'G:\AI\E-zzio'

    $Python = Join-Path `
        $ProjectRoot `
        '.venv\Scripts\python.exe'

    $HostAddress = '127.0.0.1'
    $Port = 8001
    $Application = 'interfaces.api.server:app'

    Write-Host ''
    Write-Host '╔══════════════════════════════════════════════════════════════════════════════╗' -ForegroundColor Cyan
    Write-Host '║                    E-ZZIO — OFFICIAL SERVER                                ║' -ForegroundColor Cyan
    Write-Host '╚══════════════════════════════════════════════════════════════════════════════╝' -ForegroundColor Cyan
    Write-Host ''

    Write-Host 'PROJECT :' -ForegroundColor Gray
    Write-Host $ProjectRoot -ForegroundColor White

    Write-Host ''
    Write-Host 'PYTHON OFFICIEL :' -ForegroundColor Gray
    Write-Host $Python -ForegroundColor Green

    Write-Host ''
    Write-Host 'SERVER :' -ForegroundColor Gray
    Write-Host "http://$HostAddress`:$Port" -ForegroundColor Green

    Write-Host ''
    Write-Host 'APPLICATION :' -ForegroundColor Gray
    Write-Host $Application -ForegroundColor White

    Write-Host ''
    Write-Host 'CONTRAT :' -ForegroundColor Yellow
    Write-Host "$Python -m uvicorn $Application --host $HostAddress --port $Port" -ForegroundColor Green

    Write-Host ''
    Write-Host ('=' * 88) -ForegroundColor Cyan
    Write-Host ''

    if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {

        Write-Host '[FAIL] Python E-ZZIO introuvable.' -ForegroundColor Red
        Write-Host $Python -ForegroundColor Red

        Write-Host ''
        Write-Host 'Appuyez sur une touche pour terminer...' -ForegroundColor Yellow

        try {
            $null = $Host.UI.RawUI.ReadKey(
                'NoEcho,IncludeKeyDown'
            )
        }
        catch {
        }

        exit 1
    }

    $env:Path = (
        @(
            (Join-Path $ProjectRoot '.venv\Scripts')
            ($env:Path -split ';' | Where-Object {
                $_ -ne (Join-Path $ProjectRoot '.venv\Scripts')
            })
        ) -join ';'
    )

    Write-Host '[PASS] Python officiel trouvé.' -ForegroundColor Green
    Write-Host ''

    & $Python `
        -m uvicorn `
        $Application `
        --host $HostAddress `
        --port $Port

    $ExitCode = $LASTEXITCODE

    Write-Host ''
    Write-Host ('=' * 88) -ForegroundColor Cyan
    Write-Host "E-ZZIO — SERVEUR TERMINÉ — CODE $ExitCode" -ForegroundColor Cyan
    Write-Host ('=' * 88) -ForegroundColor Cyan
    Write-Host ''

    Write-Host 'Appuyez sur une touche pour terminer...' -ForegroundColor Yellow

    try {
        $null = $Host.UI.RawUI.ReadKey(
            'NoEcho,IncludeKeyDown'
        )
    }
    catch {
    }

    exit $ExitCode
}
