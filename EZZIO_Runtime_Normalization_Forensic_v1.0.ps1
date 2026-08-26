# ============================================================================
# E-ZZIO — PYTHON RUNTIME NORMALIZATION FORENSIC
# VERSION : 1.0.0
#
# MODE :
#   READ-ONLY / FAIL-CLOSED / FORENSIC
#
# OBJECTIF :
#   Normaliser l'identité Python utilisée par E-ZZIO.
#
# GARANTIES :
#   - Aucune suppression
#   - Aucune migration Python 3.12
#   - Aucune modification du projet
#   - Aucun pip install automatique
#   - Diagnostic uniquement
#
# CIBLE :
#   G:\AI\E-zzio\.venv\Scripts\python.exe
#
# ============================================================================


& {

    Set-StrictMode -Version Latest
    $ErrorActionPreference = "Stop"


    # =========================================================================
    # CONFIGURATION
    # =========================================================================

    $ProjectRoot = "G:\AI\E-zzio"

    $EzzioVenv = Join-Path `
        $ProjectRoot `
        ".venv"

    $PythonExe = Join-Path `
        $EzzioVenv `
        "Scripts\python.exe"

    $PipExe = Join-Path `
        $EzzioVenv `
        "Scripts\pip.exe"


    $script:Checks = @()


    # =========================================================================
    # FONCTIONS
    # =========================================================================

    function Add-Check {

        param(
            [string]$Name,
            [string]$Status,
            [string]$Detail
        )

        $script:Checks += [PSCustomObject]@{
            Name   = $Name
            Status = $Status
            Detail = $Detail
        }
    }


    function Write-Result {

        param(
            [string]$Status,
            [string]$Message
        )

        $Color = switch ($Status) {

            "PASS" { "Green" }
            "FAIL" { "Red" }
            "WARN" { "Yellow" }
            default { "Gray" }
        }

        Write-Host `
            "[$Status] $Message" `
            -ForegroundColor $Color
    }


    function Section {

        param(
            [string]$Title
        )

        Write-Host ""
        Write-Host ("=" * 88) -ForegroundColor Cyan
        Write-Host $Title -ForegroundColor Cyan
        Write-Host ("=" * 88) -ForegroundColor Cyan
    }


    # =========================================================================
    # BANDEAU
    # =========================================================================

    Write-Host ""

    Write-Host `
    "╔══════════════════════════════════════════════════════════════════════════════╗" `
    -ForegroundColor Cyan

    Write-Host `
    "║          E-ZZIO — PYTHON RUNTIME NORMALIZATION FORENSIC                   ║" `
    -ForegroundColor Cyan

    Write-Host `
    "║                              VERSION 1.0.0                                ║" `
    -ForegroundColor Cyan

    Write-Host `
    "╚══════════════════════════════════════════════════════════════════════════════╝" `
    -ForegroundColor Cyan


    Write-Host ""

    Write-Host "MODE    : " -NoNewline -ForegroundColor Gray
    Write-Host "READ-ONLY / FORENSIC" -ForegroundColor Yellow

    Write-Host "PROJECT : " -NoNewline -ForegroundColor Gray
    Write-Host $ProjectRoot -ForegroundColor White

    Write-Host "PYTHON  : " -NoNewline -ForegroundColor Gray
    Write-Host $PythonExe -ForegroundColor White



    # =========================================================================
    # [1/10]
    # =========================================================================

    Section "[1/10] VÉRIFICATION PROJET"

    if(Test-Path $ProjectRoot){

        Write-Result PASS "Projet E-ZZIO détecté."

        Add-Check `
            "Project" `
            "PASS" `
            "Racine présente."

    }
    else {

        Write-Result FAIL "Projet introuvable."

        Add-Check `
            "Project" `
            "FAIL" `
            "Racine absente."

        throw "Projet absent."
    }



    # =========================================================================
    # [2/10]
    # =========================================================================

    Section "[2/10] IDENTITÉ PYTHON E-ZZIO"


    if(Test-Path $PythonExe){

        Write-Result PASS "Python E-ZZIO trouvé."

        Add-Check `
            "Python Path" `
            "PASS" `
            $PythonExe

    }
    else {

        Write-Result FAIL "Python E-ZZIO absent."

        Add-Check `
            "Python Path" `
            "FAIL" `
            $PythonExe
    }



    # =========================================================================
    # [3/10]
    # =========================================================================

    Section "[3/10] VERSION PYTHON"


    $PythonInfo = & $PythonExe `
        -c "import sys; print(sys.executable); print(sys.version)" `
        2>&1


    if($LASTEXITCODE -eq 0){

        Write-Result PASS "Python opérationnel."

        foreach($line in $PythonInfo){

            Write-Host "  $line" `
                -ForegroundColor White
        }


        Add-Check `
            "Python Runtime" `
            "PASS" `
            "Python exécutable."

    }
    else {

        Write-Result FAIL "Python non exécutable."

        Add-Check `
            "Python Runtime" `
            "FAIL" `
            ($PythonInfo -join " ")
    }



    # =========================================================================
    # [4/10]
    # =========================================================================

    Section "[4/10] PIP"


    if(Test-Path $PipExe){

        Write-Result PASS "pip E-ZZIO présent."

        Add-Check `
            "pip" `
            "PASS" `
            $PipExe

    }
    else {

        Write-Result WARN "pip absent."

        Add-Check `
            "pip" `
            "WARN" `
            "pip.exe introuvable."
    }



    # =========================================================================
    # [5/10]
    # =========================================================================

    Section "[5/10] PACKAGE FASTAPI"


    $FastApi = & $PythonExe `
        -c "import fastapi; print(fastapi.__version__)" `
        2>&1


    if($LASTEXITCODE -eq 0){

        Write-Result PASS "FastAPI disponible : $FastApi"

        Add-Check `
            "FastAPI" `
            "PASS" `
            $FastApi

    }
    else {

        Write-Result WARN "FastAPI absent."

        Add-Check `
            "FastAPI" `
            "WARN" `
            ($FastApi -join " ")
    }



    # =========================================================================
    # [6/10]
    # =========================================================================

    Section "[6/10] PACKAGE UVICORN"


    $Uvicorn = & $PythonExe `
        -c "import uvicorn; print(uvicorn.__version__)" `
        2>&1


    if($LASTEXITCODE -eq 0){

        Write-Result PASS "Uvicorn disponible : $Uvicorn"

        Add-Check `
            "Uvicorn" `
            "PASS" `
            $Uvicorn

    }
    else {

        Write-Result WARN "Uvicorn absent."

        Add-Check `
            "Uvicorn" `
            "WARN" `
            ($Uvicorn -join " ")
    }



    # =========================================================================
    # [7/10]
    # =========================================================================

    Section "[7/10] DEPENDANCE SQLITE ASYNCHRONE"


    $AsyncSql = & $PythonExe `
        -c "import aiosqlite; print(aiosqlite.__version__)" `
        2>&1


    if($LASTEXITCODE -eq 0){

        Write-Result PASS "aiosqlite disponible : $AsyncSql"

        Add-Check `
            "aiosqlite" `
            "PASS" `
            $AsyncSql

    }
    else {

        Write-Result WARN "aiosqlite absent."

        Write-Host ""
        Write-Host "ACTION PROPOSÉE (NON EXÉCUTÉE) :" `
            -ForegroundColor Yellow

        Write-Host `
        "$PipExe install aiosqlite" `
        -ForegroundColor White


        Add-Check `
            "aiosqlite" `
            "WARN" `
            "Installation manuelle nécessaire."
    }



    # =========================================================================
    # [8/10]
    # =========================================================================

    Section "[8/10] RÉSOLUTION PYTHON GLOBAL"


    $GlobalPython = (Get-Command python).Source


    Write-Host `
        "python actuel : $GlobalPython" `
        -ForegroundColor White


    Add-Check `
        "Global Python" `
        "INFO" `
        $GlobalPython



    # =========================================================================
    # [9/10]
    # =========================================================================

    Section "[9/10] RÉSUMÉ"


    foreach($Check in $Checks){

        $color = switch($Check.Status){

            "PASS" {"Green"}
            "FAIL" {"Red"}
            "WARN" {"Yellow"}
            default {"Gray"}
        }


        Write-Host `
        "[{0}] {1} — {2}" -f `
        $Check.Status,
        $Check.Name,
        $Check.Detail `
        -ForegroundColor $color
    }



    # =========================================================================
    # [10/10]
    # =========================================================================

    Section "[10/10] VERDICT"


    $Fail = @(
        $Checks |
        Where-Object {$_.Status -eq "FAIL"}
    ).Count


    $Warn = @(
        $Checks |
        Where-Object {$_.Status -eq "WARN"}
    ).Count



    Write-Host ""

    if($Fail -eq 0){

        Write-Host `
        "VERDICT : RUNTIME PYTHON E-ZZIO STABLE POUR ANALYSE" `
        -ForegroundColor Green

    }
    else {

        Write-Host `
        "VERDICT : PROBLÈMES CRITIQUES DÉTECTÉS" `
        -ForegroundColor Red
    }


    Write-Host ""

    Write-Host "COMPTEURS :" -ForegroundColor White
    Write-Host "  FAIL : $Fail" -ForegroundColor Red
    Write-Host "  WARN : $Warn" -ForegroundColor Yellow


    Write-Host ""
    Write-Host ("=" * 88) -ForegroundColor Cyan

    Write-Host `
    "E-ZZIO — FIN DU PYTHON RUNTIME NORMALIZATION FORENSIC" `
    -ForegroundColor Cyan


    Write-Host ""
    Write-Host "Fenêtre maintenue ouverte." -ForegroundColor Gray
    Write-Host "Appuyez sur une touche pour terminer..." -ForegroundColor Gray


    $null = $Host.UI.RawUI.ReadKey(
        "NoEcho,IncludeKeyDown"
    )

}