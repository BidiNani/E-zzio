#Requires -Version 7.0

<#
.SYNOPSIS
    E-ZZIO — VALIDATION FORENSIC STATIQUE v1.1.5
.DESCRIPTION
    Moteur de validation de code READ-ONLY.
    Séquence stricte :
    1. SELF AST VALIDATION (Arrêt 30 si échec)
    2. TARGET AST VALIDATION (Arrêt 31 si échec)
    3. STATIC FORENSIC & STRUCTURE SCAN
    4. VERDICT (0=PASS, 10=FAIL, 20=WARN)
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$TargetPath,

    [Parameter(Mandatory = $false)]
    [string]$ProjectRoot = 'G:\AI\E-zzio',

    [Parameter(Mandatory = $false)]
    [switch]$PauseOnExit
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# =========================================================================
# CLASSE DE RÉSULTAT
# =========================================================================
$script:Results = [System.Collections.Generic.List[object]]::new()

function Add-Result {
    param([string]$Category, [string]$Name, [string]$Status, [int]$Count, [string]$Details)
    $script:Results.Add([ordered]@{
        Category = $Category
        Name     = $Name
        Status   = $Status
        Count    = $Count
        Details  = $Details
    })
}

# =========================================================================
# MOTEUR PRINCIPAL (Isolé)
# =========================================================================
function Invoke-ForensicEngine {

    $StartedAt = [DateTime]::UtcNow
    $EngineVersion = '1.1.5'

    Write-Host ''
    Write-Host '============================================================' -ForegroundColor Cyan
    Write-Host " E-ZZIO — VALIDATION FORENSIC STATIQUE v$EngineVersion" -ForegroundColor Cyan
    Write-Host '============================================================' -ForegroundColor Cyan
    Write-Host ''
    Write-Host 'MODE : READ-ONLY TARGET / NO EXECUTION / FAIL-CLOSED' -ForegroundColor Yellow
    Write-Host ''

    # -------------------------------------------------------------------------
    # 1. SELF VALIDATION
    # -------------------------------------------------------------------------
    $ValidatorPath = $PSCommandPath
    if (-not (Test-Path -LiteralPath $ValidatorPath -PathType Leaf)) {
        Write-Host '[FAIL-CLOSED] Validateur introuvable.' -ForegroundColor Red
        return 30
    }

    $ValidatorSha256 = (Get-FileHash -LiteralPath $ValidatorPath -Algorithm SHA256).Hash

    Write-Host '--- 1/2 SELF AST VALIDATION ---' -ForegroundColor Cyan
    $SelfTokens = $null
    $SelfErrors = $null
    $SelfAst = [System.Management.Automation.Language.Parser]::ParseFile($ValidatorPath, [ref]$SelfTokens, [ref]$SelfErrors)
    $SelfErrorArray = @($SelfErrors)

    if ($SelfErrorArray.Count -gt 0) {
        Write-Host "AST Errors : $($SelfErrorArray.Count)" -ForegroundColor Red
        foreach ($err in $SelfErrorArray) {
            Write-Host "Ligne $($err.Extent.StartLineNumber) : $($err.Message)" -ForegroundColor Red
        }
        Write-Host '[FAIL-CLOSED] SELF AST INVALID — FORENSIC BLOQUÉ' -ForegroundColor Red
        return 30
    }
    Write-Host '[PASS] SELF AST = 0 erreur' -ForegroundColor Green
    Write-Host ''

    # -------------------------------------------------------------------------
    # 2. TARGET VALIDATION
    # -------------------------------------------------------------------------
    if (-not (Test-Path -LiteralPath $TargetPath -PathType Leaf)) {
        Write-Host "[FAIL-CLOSED] Cible introuvable : $TargetPath" -ForegroundColor Red
        return 31
    }

    $TargetInfo = Get-Item -LiteralPath $TargetPath -Force
    $TargetSha256 = (Get-FileHash -LiteralPath $TargetPath -Algorithm SHA256).Hash

    Write-Host '--- 2/2 TARGET AST VALIDATION ---' -ForegroundColor Cyan
    $TargetTokens = $null
    $TargetErrors = $null
    $TargetAst = [System.Management.Automation.Language.Parser]::ParseFile($TargetPath, [ref]$TargetTokens, [ref]$TargetErrors)
    $TargetErrorArray = @($TargetErrors)

    if ($TargetErrorArray.Count -gt 0) {
        Write-Host "Cible : $TargetPath" -ForegroundColor Yellow
        Write-Host "AST Errors : $($TargetErrorArray.Count)" -ForegroundColor Red
        foreach ($err in $TargetErrorArray) {
            Write-Host "Ligne $($err.Extent.StartLineNumber) : $($err.Message)" -ForegroundColor Red
        }
        Write-Host '[FAIL-CLOSED] TARGET AST INVALID — FORENSIC BLOQUÉ' -ForegroundColor Red
        return 31
    }
    Write-Host '[PASS] TARGET AST = 0 erreur' -ForegroundColor Green
    Write-Host ''

    # -------------------------------------------------------------------------
    # 3. STRUCTURE AST SCAN
    # -------------------------------------------------------------------------
    $CommandNodes = @($TargetAst.FindAll({ param($n) $n -is [System.Management.Automation.Language.CommandAst] }, $true))
    $FunctionNodes = @($TargetAst.FindAll({ param($n) $n -is [System.Management.Automation.Language.FunctionDefinitionAst] }, $true))
    $ThrowNodes = @($TargetAst.FindAll({ param($n) $n -is [System.Management.Automation.Language.ThrowStatementAst] }, $true))
    $TryNodes = @($TargetAst.FindAll({ param($n) $n -is [System.Management.Automation.Language.TryStatementAst] }, $true))
    $IfNodes = @($TargetAst.FindAll({ param($n) $n -is [System.Management.Automation.Language.IfStatementAst] }, $true))

    Add-Result 'STRUCTURE' 'COMMANDS' 'INFO' $CommandNodes.Count "Commandes : $($CommandNodes.Count)"
    Add-Result 'STRUCTURE' 'FUNCTIONS' 'INFO' $FunctionNodes.Count "Fonctions : $($FunctionNodes.Count)"
    Add-Result 'STRUCTURE' 'THROW' 'INFO' $ThrowNodes.Count "Throws : $($ThrowNodes.Count)"

    # -------------------------------------------------------------------------
    # 4. PATTERN SCAN (FORENSIC)
    # -------------------------------------------------------------------------
    function Test-Pattern {
        param([string]$Name, [string]$Pattern, [string]$Category, [string]$StatusWhenFound)
        $Matches = @(Select-String -LiteralPath $TargetPath -Pattern $Pattern -CaseSensitive:$false -AllMatches -ErrorAction Stop)
        if ($Matches.Count -eq 0) {
            Add-Result $Category $Name 'PASS' 0 'Aucune occurrence.'
        } else {
            $Preview = ($Matches | Select-Object -First 3 | ForEach-Object { "L$($_.LineNumber): $($_.Line.Trim())" }) -join ' | '
            Add-Result $Category $Name $StatusWhenFound $Matches.Count "Détecté : $Preview"
        }
    }

    Test-Pattern 'INVOKE_EXPRESSION' '\bInvoke-Expression\b|\biex\b' 'EXECUTION' 'FAIL'
    Test-Pattern 'START_PROCESS' '\bStart-Process\b' 'EXECUTION' 'WARN'
    Test-Pattern 'SET_CONTENT' '\bSet-Content\b|\bAdd-Content\b|\bOut-File\b' 'MUTATION' 'WARN'
    Test-Pattern 'FILESYSTEM' '\bNew-Item\b|\bRemove-Item\b|\bMove-Item\b' 'MUTATION' 'WARN'
    Test-Pattern 'NETWORK' '\bInvoke-WebRequest\b|\biwr\b|\bInvoke-RestMethod\b' 'NETWORK' 'WARN'
    Test-Pattern 'FAKE_PASS' '(?i)FAKE.?PASS|FORCED.?PASS|ALWAYS.?PASS' 'CERTIFICATION' 'FAIL'
    Test-Pattern 'PLACEHOLDER' '(?i)\bTODO\b|\bFIXME\b|\bPLACEHOLDER\b' 'CERTIFICATION' 'WARN'
    Test-Pattern 'FAIL_CLOSED' '(?i)FAIL.?CLOSED' 'HARDENING' 'PASS'
    Test-Pattern 'STRICT_MODE' '(?i)Set-StrictMode' 'HARDENING' 'PASS'

    $SecretEnvPattern = '(?i)' + '\$' + 'env' + ':' + '[A-Za-z0-9_]*' + '(SECRET|KEY|TOKEN|PASSWORD)'
    Test-Pattern 'ENV_SECRET_REFERENCE' $SecretEnvPattern 'SECRETS' 'WARN'

    # -------------------------------------------------------------------------
    # 5. DÉCOMPTE ET VERDICT
    # -------------------------------------------------------------------------
    $PassCount = @($script:Results | Where-Object { $_.Status -eq 'PASS' }).Count
    $WarnCount = @($script:Results | Where-Object { $_.Status -eq 'WARN' }).Count
    $FailCount = @($script:Results | Where-Object { $_.Status -eq 'FAIL' }).Count
    $InfoCount = @($script:Results | Where-Object { $_.Status -eq 'INFO' }).Count

    $ExitCode = 0
    $Verdict = 'FORENSIC_PASS'
    $VerdictColor = 'Green'

    if ($FailCount -gt 0) {
        $Verdict = 'FORENSIC_FAIL'
        $VerdictColor = 'Red'
        $ExitCode = 10
    } elseif ($WarnCount -gt 0) {
        $Verdict = 'FORENSIC_REVIEW_REQUIRED'
        $VerdictColor = 'Yellow'
        $ExitCode = 20
    }

    # -------------------------------------------------------------------------
    # 6. RAPPORTS JSON ET TXT
    # -------------------------------------------------------------------------
    $EndedAt = [DateTime]::UtcNow
    $ReportDir = Join-Path $ProjectRoot '_forensic\Validation'
    if (-not (Test-Path -LiteralPath $ReportDir -PathType Container)) {
        New-Item -ItemType Directory -Path $ReportDir -Force | Out-Null
    }

    $TargetBase = [System.IO.Path]::GetFileNameWithoutExtension($TargetPath)
    $Timestamp = $StartedAt.ToString('yyyyMMdd_HHmmss')
    $ReportJson = Join-Path $ReportDir "${TargetBase}_${Timestamp}_Report.json"
    $ReportTxt  = Join-Path $ReportDir "${TargetBase}_${Timestamp}_Report.txt"

    $ReportData = [ordered]@{
        Engine = 'E-ZZIO'
        Validation = 'FORENSIC_STATIC'
        Version = $EngineVersion
        Verdict = $Verdict
        Target = $TargetPath
        TargetSHA256 = $TargetSha256
        ValidatorSHA256 = $ValidatorSha256
        StartedAtUTC = $StartedAt.ToString('o')
        EndedAtUTC = $EndedAt.ToString('o')
        Stats = [ordered]@{ PASS=$PassCount; WARN=$WarnCount; FAIL=$FailCount; INFO=$InfoCount }
        Results = @($script:Results)
    }

    $ReportData | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $ReportJson -Encoding UTF8

    $TxtLines = [System.Collections.Generic.List[string]]::new()
    $TxtLines.Add('============================================================')
    $TxtLines.Add(" RÉSULTAT FORENSIC : $Verdict")
    $TxtLines.Add(" Cible : $TargetPath")
    $TxtLines.Add(" SHA-256 : $TargetSha256")
    $TxtLines.Add('============================================================')
    foreach ($Res in $script:Results) {
        $TxtLines.Add("[" + $Res.Status + "] " + $Res.Category + "/" + $Res.Name + " (" + $Res.Count + ") -> " + $Res.Details)
    }
    $TxtLines | Set-Content -LiteralPath $ReportTxt -Encoding UTF8

    # -------------------------------------------------------------------------
    # 7. AFFICHAGE FINAL
    # -------------------------------------------------------------------------
    Write-Host '============================================================' -ForegroundColor Cyan
    Write-Host " RÉSULTAT FORENSIC STATIQUE v$EngineVersion" -ForegroundColor Cyan
    Write-Host '============================================================'
    Write-Host "Cible       : $TargetPath"
    Write-Host "SHA-256     : $TargetSha256"
    Write-Host ''
    Write-Host "PASS : $PassCount | WARN : $WarnCount | FAIL : $FailCount | INFO : $InfoCount"
    Write-Host ''
    Write-Host "VERDICT     : $Verdict" -ForegroundColor $VerdictColor
    Write-Host ''
    Write-Host "Rapport TXT  : $ReportTxt" -ForegroundColor DarkGray
    Write-Host "Rapport JSON : $ReportJson" -ForegroundColor DarkGray
    Write-Host '============================================================' -ForegroundColor Cyan

    return $ExitCode
}

# =========================================================================
# EXÉCUTION
# =========================================================================
$FinalExitCode = 99

try {
    $FinalExitCode = Invoke-ForensicEngine
} catch {
    Write-Host ''
    Write-Host '!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!' -ForegroundColor Red
    Write-Host ' CRASH INATTENDU DU MOTEUR FORENSIC' -ForegroundColor Red
    Write-Host '!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!' -ForegroundColor Red
    Write-Host "Exception : $($_.Exception.Message)" -ForegroundColor Red
    $FinalExitCode = 99
} finally {
    if ($PauseOnExit) {
        Write-Host ''
        Read-Host 'Appuyez sur Entrée pour fermer'
    }
    exit $FinalExitCode
}