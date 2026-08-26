# ============================================================================
# E-ZZIO — PYTHON RUNTIME OPERATIONAL NORMALIZATION
# VERSION : 2.0.0
#
# MODE :
#   CONTROLLED MUTATION / FORENSIC
#
# PROJECT :
#   G:\AI\E-zzio
#
# OBJECTIF :
#   1. Stabiliser définitivement le runtime Python E-ZZIO.
#   2. Réparer pip dans le .venv si nécessaire.
#   3. Vérifier FastAPI / Uvicorn / aiosqlite.
#   4. Créer un lanceur officiel E-ZZIO utilisant UNIQUEMENT :
#
#      G:\AI\E-zzio\.venv\Scripts\python.exe
#
# GARANTIES :
#   - Aucun Python 3.12 supprimé.
#   - Aucun Python UV supprimé.
#   - Aucun environnement Hermes touché.
#   - Aucun fichier Python E-ZZIO modifié.
#   - Aucun package existant désinstallé.
#   - Le lanceur utilise explicitement le Python E-ZZIO.
#
# ============================================================================


& {

    Set-StrictMode -Version Latest
    $ErrorActionPreference = "Stop"


    # =========================================================================
    # CONFIGURATION
    # =========================================================================

    $ProjectRoot = "G:\AI\E-zzio"

    $VenvRoot = Join-Path `
        $ProjectRoot `
        ".venv"

    $EzzioPython = Join-Path `
        $VenvRoot `
        "Scripts\python.exe"

    $EzzioPip = Join-Path `
        $VenvRoot `
        "Scripts\pip.exe"

    $LauncherPath = Join-Path `
        $ProjectRoot `
        "EZZIO_Run_API.ps1"

    $ServerModule = "interfaces.api.server:app"

    $ServerHost = "127.0.0.1"

    $ServerPort = 8001


    # =========================================================================
    # STOCKAGE DES CONTRÔLES
    # =========================================================================

    $Checks = New-Object System.Collections.ArrayList


    # =========================================================================
    # FONCTIONS
    # =========================================================================

    function Add-Check {

        param(
            [Parameter(Mandatory = $true)]
            [string]$Name,

            [Parameter(Mandatory = $true)]
            [ValidateSet(
                "PASS",
                "FAIL",
                "WARN",
                "INFO"
            )]
            [string]$Status,

            [Parameter(Mandatory = $true)]
            [string]$Detail
        )


        [void]$Checks.Add(
            [PSCustomObject]@{
                Name   = $Name
                Status = $Status
                Detail = $Detail
            }
        )
    }


    function Write-Result {

        param(
            [Parameter(Mandatory = $true)]
            [ValidateSet(
                "PASS",
                "FAIL",
                "WARN",
                "INFO"
            )]
            [string]$Status,

            [Parameter(Mandatory = $true)]
            [string]$Message
        )


        $Color = switch ($Status) {

            "PASS" { "Green" }

            "FAIL" { "Red" }

            "WARN" { "Yellow" }

            "INFO" { "Gray" }
        }


        Write-Host `
            ("[{0}] {1}" -f $Status, $Message) `
            -ForegroundColor $Color
    }


    function Write-Section {

        param(
            [Parameter(Mandatory = $true)]
            [string]$Title
        )


        Write-Host ""

        Write-Host `
            ("=" * 88) `
            -ForegroundColor Cyan

        Write-Host `
            $Title `
            -ForegroundColor Cyan

        Write-Host `
            ("=" * 88) `
            -ForegroundColor Cyan
    }


    # =========================================================================
    # BANDEAU
    # =========================================================================

    Write-Host ""

    Write-Host `
        "╔══════════════════════════════════════════════════════════════════════════════╗" `
        -ForegroundColor Cyan

    Write-Host `
        "║        E-ZZIO — PYTHON RUNTIME OPERATIONAL NORMALIZATION                  ║" `
        -ForegroundColor Cyan

    Write-Host `
        "║                              VERSION 2.0.0                                ║" `
        -ForegroundColor Cyan

    Write-Host `
        "╚══════════════════════════════════════════════════════════════════════════════╝" `
        -ForegroundColor Cyan

    Write-Host ""

    Write-Host "MODE       : " -NoNewline -ForegroundColor Gray
    Write-Host "CONTROLLED MUTATION / FORENSIC" -ForegroundColor Yellow

    Write-Host "PROJECT    : " -NoNewline -ForegroundColor Gray
    Write-Host $ProjectRoot -ForegroundColor White

    Write-Host "PYTHON     : " -NoNewline -ForegroundColor Gray
    Write-Host $EzzioPython -ForegroundColor Green

    Write-Host "SERVER     : " -NoNewline -ForegroundColor Gray
    Write-Host "http://$ServerHost`:$ServerPort" -ForegroundColor White

    Write-Host ""

    Write-Host `
        "OBJECTIF   : stabiliser le runtime E-ZZIO et créer son lanceur officiel." `
        -ForegroundColor White

    Write-Host ""


    # =========================================================================
    # [1/10] VÉRIFICATION DU PROJET
    # =========================================================================

    Write-Section "[1/10] VÉRIFICATION DU PROJET"


    if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) {

        Write-Result `
            -Status "FAIL" `
            -Message "Projet E-ZZIO introuvable : $ProjectRoot"

        Add-Check `
            -Name "Projet" `
            -Status "FAIL" `
            -Detail "Racine du projet absente."

        throw "Projet E-ZZIO introuvable."
    }


    Write-Result `
        -Status "PASS" `
        -Message "Projet E-ZZIO détecté : $ProjectRoot"


    Add-Check `
        -Name "Projet" `
        -Status "PASS" `
        -Detail "Racine E-ZZIO présente."


    # =========================================================================
    # [2/10] VÉRIFICATION DU .VEN V
    # =========================================================================

    Write-Section "[2/10] VÉRIFICATION — ENVIRONNEMENT .VEN V"


    if (-not (Test-Path -LiteralPath $VenvRoot -PathType Container)) {

        Write-Result `
            -Status "FAIL" `
            -Message "Environnement .venv absent."

        Add-Check `
            -Name ".venv" `
            -Status "FAIL" `
            -Detail $VenvRoot

        throw "Le .venv E-ZZIO est absent."
    }


    Write-Result `
        -Status "PASS" `
        -Message "Environnement .venv présent."


    Add-Check `
        -Name ".venv" `
        -Status "PASS" `
        -Detail $VenvRoot


    # =========================================================================
    # [3/10] IDENTITÉ PYTHON
    # =========================================================================

    Write-Section "[3/10] IDENTITÉ — PYTHON E-ZZIO"


    if (-not (Test-Path -LiteralPath $EzzioPython -PathType Leaf)) {

        Write-Result `
            -Status "FAIL" `
            -Message "python.exe E-ZZIO absent."

        Add-Check `
            -Name "Python E-ZZIO" `
            -Status "FAIL" `
            -Detail $EzzioPython

        throw "Python E-ZZIO absent."
    }


    $PythonIdentity = @(
        & $EzzioPython `
            -c "import sys; print(sys.executable); print(sys.version)"
    )


    if ($LASTEXITCODE -ne 0) {

        Write-Result `
            -Status "FAIL" `
            -Message "Le Python E-ZZIO ne peut pas être exécuté."

        Add-Check `
            -Name "Python E-ZZIO" `
            -Status "FAIL" `
            -Detail "Exécution impossible."

        throw "Python E-ZZIO non fonctionnel."
    }


    foreach ($Line in $PythonIdentity) {

        Write-Host `
            "  $Line" `
            -ForegroundColor White
    }


    Write-Result `
        -Status "PASS" `
        -Message "Python E-ZZIO opérationnel."


    Add-Check `
        -Name "Python E-ZZIO" `
        -Status "PASS" `
        -Detail (($PythonIdentity -join " | "))


    # =========================================================================
    # [4/10] VALIDATION DE LA VERSION
    # =========================================================================

    Write-Section "[4/10] VALIDATION — VERSION PYTHON"


    $PythonVersion = @(
        & $EzzioPython `
            -c "import sys; print('%d.%d.%d' % sys.version_info[:3])"
    )


    $PythonVersionString = ($PythonVersion -join "").Trim()


    Write-Host `
        "Version détectée : $PythonVersionString" `
        -ForegroundColor White


    if ($PythonVersionString -like "3.11.*") {

        Write-Result `
            -Status "PASS" `
            -Message "Python 3.11 détecté dans le runtime E-ZZIO."

        Add-Check `
            -Name "Python Version" `
            -Status "PASS" `
            -Detail $PythonVersionString
    }
    else {

        Write-Result `
            -Status "WARN" `
            -Message "Version différente de Python 3.11 détectée : $PythonVersionString"

        Add-Check `
            -Name "Python Version" `
            -Status "WARN" `
            -Detail $PythonVersionString
    }


    # =========================================================================
    # [5/10] PIP
    # =========================================================================

    Write-Section "[5/10] RÉPARATION CONTRÔLÉE — PIP"


    if (Test-Path -LiteralPath $EzzioPip -PathType Leaf) {

        Write-Result `
            -Status "PASS" `
            -Message "pip.exe déjà présent."


        Add-Check `
            -Name "pip" `
            -Status "PASS" `
            -Detail $EzzioPip
    }
    else {

        Write-Result `
            -Status "WARN" `
            -Message "pip.exe absent — tentative de restauration via ensurepip."

        Write-Host ""

        Write-Host `
            "ACTION AUTORISÉE :" `
            -ForegroundColor Yellow

        Write-Host `
            "  Python E-ZZIO uniquement" `
            -ForegroundColor White

        Write-Host `
            "  Aucune installation de package E-ZZIO" `
            -ForegroundColor White

        Write-Host ""


        try {

            & $EzzioPython `
                -m ensurepip `
                --upgrade `
                2>&1 |
                ForEach-Object {
                    Write-Host `
                        "  $_" `
                        -ForegroundColor Gray
                }


            if ($LASTEXITCODE -ne 0) {

                throw "ensurepip a retourné le code $LASTEXITCODE."
            }


            if (Test-Path -LiteralPath $EzzioPip -PathType Leaf) {

                Write-Result `
                    -Status "PASS" `
                    -Message "pip restauré dans le .venv E-ZZIO."

                Add-Check `
                    -Name "pip" `
                    -Status "PASS" `
                    -Detail "pip restauré via ensurepip."
            }
            else {

                Write-Result `
                    -Status "FAIL" `
                    -Message "ensurepip exécuté mais pip.exe reste absent."

                Add-Check `
                    -Name "pip" `
                    -Status "FAIL" `
                    -Detail "pip.exe toujours absent."

                throw "pip non restauré."
            }
        }
        catch {

            Write-Result `
                -Status "FAIL" `
                -Message "Échec de restauration de pip : $($_.Exception.Message)"

            Add-Check `
                -Name "pip" `
                -Status "FAIL" `
                -Detail $_.Exception.Message

            throw
        }
    }


    # =========================================================================
    # [6/10] DÉPENDANCES CRITIQUES
    # =========================================================================

    Write-Section "[6/10] VALIDATION — DÉPENDANCES CRITIQUES"


    $CriticalModules = @(
        "fastapi",
        "uvicorn",
        "aiosqlite"
    )


    foreach ($Module in $CriticalModules) {

        try {

            $ModuleVersion = @(
                & $EzzioPython `
                    -c "import importlib.metadata as m; print(m.version('$Module'))"
            )


            if ($LASTEXITCODE -ne 0) {

                throw "module absent"
            }


            $VersionText = ($ModuleVersion -join "").Trim()


            Write-Result `
                -Status "PASS" `
                -Message "$Module $VersionText"

            Add-Check `
                -Name $Module `
                -Status "PASS" `
                -Detail $VersionText
        }
        catch {

            Write-Result `
                -Status "FAIL" `
                -Message "$Module absent du runtime E-ZZIO."

            Add-Check `
                -Name $Module `
                -Status "FAIL" `
                -Detail "Dépendance critique absente."
        }
    }


    # =========================================================================
    # [7/10] UVICORN
    # =========================================================================

    Write-Section "[7/10] RÉSOLUTION — UVICORN E-ZZIO"


    $UvicornModuleTest = @(
        & $EzzioPython `
            -c "import uvicorn,sys; print(uvicorn.__file__); print(sys.executable)"
    )


    if ($LASTEXITCODE -eq 0) {

        foreach ($Line in $UvicornModuleTest) {

            Write-Host `
                "  $Line" `
                -ForegroundColor White
        }


        Write-Result `
            -Status "PASS" `
            -Message "Uvicorn est résolu par le Python E-ZZIO."

        Add-Check `
            -Name "Uvicorn Resolution" `
            -Status "PASS" `
            -Detail (($UvicornModuleTest -join " | "))
    }
    else {

        Write-Result `
            -Status "FAIL" `
            -Message "Uvicorn ne peut pas être importé."

        Add-Check `
            -Name "Uvicorn Resolution" `
            -Status "FAIL" `
            -Detail "Import Uvicorn impossible."
    }


    # =========================================================================
    # [8/10] CRÉATION DU LANCEUR OFFICIEL
    # =========================================================================

    Write-Section "[8/10] CRÉATION — LANCEUR OFFICIEL E-ZZIO"


    Write-Host ""
    Write-Host "FICHIER CIBLE :" -ForegroundColor Yellow
    Write-Host $LauncherPath -ForegroundColor White
    Write-Host ""


    $LauncherContent = @"
# ============================================================================
# E-ZZIO — OFFICIAL API LAUNCHER
# VERSION : 1.0.0
#
# IMPORTANT :
#   Ce lanceur utilise exclusivement le Python du .venv E-ZZIO.
# ============================================================================

`$ErrorActionPreference = "Stop"

`$ProjectRoot = "G:\AI\E-zzio"

`$Python = Join-Path `
    `$ProjectRoot `
    ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath `$Python -PathType Leaf)) {

    Write-Host ""
    Write-Host "[FAIL] Python E-ZZIO introuvable :" -ForegroundColor Red
    Write-Host `$Python -ForegroundColor Red
    Write-Host ""
    Read-Host "Appuyez sur Entrée pour terminer"
    exit 1
}

Set-Location -LiteralPath `$ProjectRoot

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "E-ZZIO — API SERVER" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "PROJECT :" -ForegroundColor Gray
Write-Host `$ProjectRoot -ForegroundColor White
Write-Host ""
Write-Host "PYTHON :" -ForegroundColor Gray
Write-Host `$Python -ForegroundColor Green
Write-Host ""
Write-Host "SERVER :" -ForegroundColor Gray
Write-Host "http://127.0.0.1:8001" -ForegroundColor White
Write-Host ""
Write-Host "MODULE :" -ForegroundColor Gray
Write-Host "interfaces.api.server:app" -ForegroundColor White
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

& `$Python -m uvicorn `
    "interfaces.api.server:app" `
    --host 127.0.0.1 `
    --port 8001

`$ExitCode = `$LASTEXITCODE

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "E-ZZIO — API SERVER TERMINÉ" -ForegroundColor Cyan
Write-Host "CODE : `$ExitCode" -ForegroundColor White
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

Read-Host "Appuyez sur Entrée pour fermer"
exit `$ExitCode
"@


try {

    Set-Content `
        -LiteralPath $LauncherPath `
        -Value $LauncherContent `
        -Encoding UTF8 `
        -Force


    if (-not (Test-Path -LiteralPath $LauncherPath -PathType Leaf)) {

        throw "Le lanceur n'a pas pu être créé."
    }


    Write-Result `
        -Status "PASS" `
        -Message "Lanceur officiel E-ZZIO créé."


    Add-Check `
        -Name "Official Launcher" `
        -Status "PASS" `
        -Detail $LauncherPath
}
catch {

    Write-Result `
        -Status "FAIL" `
        -Message "Création du lanceur impossible : $($_.Exception.Message)"

    Add-Check `
        -Name "Official Launcher" `
        -Status "FAIL" `
        -Detail $_.Exception.Message
}


# ============================================================================
# [9/10] VALIDATION DU LANCEUR
# ============================================================================

Write-Section "[9/10] VALIDATION — LANCEUR E-ZZIO"


if (Test-Path -LiteralPath $LauncherPath -PathType Leaf) {

    $LauncherText = Get-Content `
        -LiteralPath $LauncherPath `
        -Raw


    $PythonReferenceValid =
        $LauncherText.Contains(
            '.venv\Scripts\python.exe'
        )


    $UvicornReferenceValid =
        $LauncherText.Contains(
            'interfaces.api.server:app'
        )


    if ($PythonReferenceValid -and $UvicornReferenceValid) {

        Write-Result `
            -Status "PASS" `
            -Message "Le lanceur référence explicitement le Python E-ZZIO et Uvicorn."

        Add-Check `
            -Name "Launcher Validation" `
            -Status "PASS" `
            -Detail "Python E-ZZIO + interfaces.api.server:app détectés."
    }
    else {

        Write-Result `
            -Status "FAIL" `
            -Message "Le contenu du lanceur ne correspond pas au contrat attendu."

        Add-Check `
            -Name "Launcher Validation" `
            -Status "FAIL" `
            -Detail "Références runtime incomplètes."
    }
}
else {

    Write-Result `
        -Status "FAIL" `
        -Message "Lanceur introuvable après création."

    Add-Check `
        -Name "Launcher Validation" `
        -Status "FAIL" `
        -Detail "Fichier absent."
}


# ============================================================================
# [10/10] SYNTHÈSE FORENSIC
# ============================================================================

Write-Section "[10/10] SYNTHÈSE FORENSIC"


foreach ($Item in $Checks) {

    $ItemColor = switch ($Item.Status) {

        "PASS" { "Green" }

        "FAIL" { "Red" }

        "WARN" { "Yellow" }

        default { "Gray" }
    }


    $SummaryLine = "[{0}] {1} — {2}" -f `
        $Item.Status,
        $Item.Name,
        $Item.Detail


    Write-Host `
        $SummaryLine `
        -ForegroundColor $ItemColor
}


$PassCount = @(
    $Checks |
    Where-Object {
        $_.Status -eq "PASS"
    }
).Count


$FailCount = @(
    $Checks |
    Where-Object {
        $_.Status -eq "FAIL"
    }
).Count


$WarnCount = @(
    $Checks |
    Where-Object {
        $_.Status -eq "WARN"
    }
).Count


$InfoCount = @(
    $Checks |
    Where-Object {
        $_.Status -eq "INFO"
    }
).Count


Write-Host ""

Write-Host "COMPTEURS :" -ForegroundColor White

Write-Host `
    "  PASS : $PassCount" `
    -ForegroundColor Green

Write-Host `
    "  FAIL : $FailCount" `
    -ForegroundColor Red

Write-Host `
    "  WARN : $WarnCount" `
    -ForegroundColor Yellow

Write-Host `
    "  INFO : $InfoCount" `
    -ForegroundColor Gray


Write-Host ""
Write-Host ("=" * 88) -ForegroundColor Cyan


if ($FailCount -eq 0) {

    Write-Host `
        "VERDICT : RUNTIME E-ZZIO NORMALISÉ" `
        -ForegroundColor Green

    Write-Host ""

    Write-Host `
        "PYTHON OFFICIEL :" `
        -ForegroundColor White

    Write-Host `
        $EzzioPython `
        -ForegroundColor Green

    Write-Host ""

    Write-Host `
        "LANCEUR OFFICIEL :" `
        -ForegroundColor White

    Write-Host `
        $LauncherPath `
        -ForegroundColor Green

    Write-Host ""

    Write-Host `
        "E-ZZIO doit désormais être lancé avec ce runtime explicite." `
        -ForegroundColor White

}
else {

    Write-Host `
        "VERDICT : NORMALISATION INCOMPLÈTE — NE PAS CONTINUER" `
        -ForegroundColor Red

    Write-Host ""

    Write-Host `
        "Un ou plusieurs contrôles critiques ont échoué." `
        -ForegroundColor Red
}


Write-Host ""
Write-Host ("=" * 88) -ForegroundColor Cyan
Write-Host ""
Write-Host "E-ZZIO — FIN DU PYTHON RUNTIME OPERATIONAL NORMALIZATION" -ForegroundColor Cyan
Write-Host ""
Write-Host "La fenêtre reste ouverte volontairement." -ForegroundColor Gray
Write-Host "Appuyez sur une touche pour terminer..." -ForegroundColor Gray


$null = $Host.UI.RawUI.ReadKey(
    "NoEcho,IncludeKeyDown"
)

}