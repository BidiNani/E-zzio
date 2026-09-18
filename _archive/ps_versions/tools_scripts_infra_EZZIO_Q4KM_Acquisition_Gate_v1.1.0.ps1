#requires -Version 7.4
# =============================================================================
# E-ZZIO — Q4_K_M MODEL ACQUISITION GATE
# Version : 1.1.0
# Mode    : SAFE / NON-DESTRUCTIVE / FORENSIC / FAIL-CLOSED
# =============================================================================
#
# OBJECTIFS
#   - Acquisition contrôlée de modèles Ollama
#   - Serveur Ollama ISOLÉ sur port dédié
#   - Aucun arrêt du serveur Ollama utilisateur
#   - Aucun rm / delete / purge
#   - Vérification présence + métadonnées
#   - Conservation d'une marge disque
#   - Rapport JSON forensic
#   - Verdict explicite
#
# IMPORTANT
#   Ce script doit être exécuté comme fichier .ps1.
#   Ne pas le coller ligne par ligne dans la console.
#
# =============================================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# =============================================================================
# CONFIGURATION
# =============================================================================

$Version = '1.1.0'

$OllamaExe  = 'G:\Ollama\ollama.exe'
$ModelsRoot = 'G:\Ollama\Models'
$Drive      = 'G:'

# Port privé pour CETTE instance.
# Cela évite le conflit avec Ollama Desktop / Ollama déjà actif.
$HostAddress = '127.0.0.1'
$Port        = 11435
$OllamaHost  = "$HostAddress`:$Port"

# Marge de sécurité.
$MinimumFreeGB = 10.0

# Timeout réseau / pull.
$ServerStartupTimeoutSec = 60
$PullTimeoutSec          = 1800
$ApiTimeoutSec           = 30

# Répertoire audit.
$AuditRoot = 'G:\AI\E-zzio\runtime\audit\forensic'

# =============================================================================
# CANDIDATS
# =============================================================================
#
# IMPORTANT :
# Le TAG Ollama doit être vérifié.
# Le script ne transforme PAS arbitrairement un modèle en Q4_K_M.
#
# Commence volontairement avec des modèles raisonnables pour ~60 GB libres.
#
# Tu peux modifier cette liste avant exécution.
#
# =============================================================================

$TargetModels = @(
    'qwen3:14b',
    'qwen3:8b',
    'qwen2.5-coder:14b',
    'granite4.1:8b'
)

# Modèles à exclure explicitement du banc génératif.
$ExcludedPatterns = @(
    'embed',
    'nomic',
    'bge'
)

# =============================================================================
# RUN ID
# =============================================================================

$RunId = Get-Date -Format 'yyyyMMdd_HHmmss'

$ReportPath = Join-Path `
    $AuditRoot `
    "EZZIO_Q4KM_ACQUISITION_$RunId.json"

$StdOutPath = Join-Path `
    $AuditRoot `
    "EZZIO_Q4KM_ACQUISITION_$RunId.server.stdout.log"

$StdErrPath = Join-Path `
    $AuditRoot `
    "EZZIO_Q4KM_ACQUISITION_$RunId.server.stderr.log"

# =============================================================================
# ÉTAT GLOBAL
# =============================================================================

$Results = [System.Collections.Generic.List[object]]::new()

$OverallPass = $true
$FatalErrors = 0

$ServerProcess = $null
$ServerStartedByUs = $false

# =============================================================================
# CONSOLE FORENSIC
# =============================================================================

function Write-Info {
    param([string]$Message)

    Write-Host "[INFO] $Message"
}

function Write-Pass {
    param([string]$Message)

    Write-Host "[PASS] $Message" -ForegroundColor Green
}

function Write-Warn {
    param([string]$Message)

    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Write-Fail {
    param([string]$Message)

    Write-Host "[FAIL] $Message" -ForegroundColor Red
}

function Write-Section {
    param([string]$Message)

    Write-Host ''
    Write-Host ('-' * 80)
    Write-Host $Message
    Write-Host ('-' * 80)
}

# =============================================================================
# DISQUE
# =============================================================================

function Get-FreeSpaceGB {

    $disk = Get-CimInstance `
        -ClassName Win32_LogicalDisk `
        -Filter "DeviceID='$Drive'" `
        -ErrorAction Stop

    if ($null -eq $disk) {
        throw "Lecteur introuvable : $Drive"
    }

    return [math]::Round(
        ([double]$disk.FreeSpace / 1GB),
        3
    )
}

# =============================================================================
# HTTP API
# =============================================================================

function Test-OllamaApi {

    try {

        $response = Invoke-RestMethod `
            -Uri "http://$OllamaHost/api/tags" `
            -Method Get `
            -TimeoutSec $ApiTimeoutSec `
            -ErrorAction Stop

        return $true
    }
    catch {

        return $false
    }
}

# =============================================================================
# ATTENTE SERVEUR
# =============================================================================

function Wait-OllamaServer {

    param(
        [int]$TimeoutSec
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSec)

    Write-Info "Attente du serveur Ollama sur http://$OllamaHost ..."

    while ((Get-Date) -lt $deadline) {

        if (Test-OllamaApi) {

            Write-Pass "API Ollama opérationnelle : http://$OllamaHost"

            return
        }

        Start-Sleep -Milliseconds 500
    }

    throw `
        "Timeout serveur Ollama après $TimeoutSec secondes."
}

# =============================================================================
# INVENTAIRE API
# =============================================================================

function Get-OllamaInventory {

    $response = Invoke-RestMethod `
        -Uri "http://$OllamaHost/api/tags" `
        -Method Get `
        -TimeoutSec $ApiTimeoutSec `
        -ErrorAction Stop

    if ($null -eq $response.models) {

        return @()
    }

    return @($response.models)
}

# =============================================================================
# TEST PRÉSENCE
# =============================================================================

function Test-ModelInstalled {

    param(
        [Parameter(Mandatory)]
        [string]$ModelName
    )

    $inventory = Get-OllamaInventory

    foreach ($model in $inventory) {

        if ([string]$model.name -eq $ModelName) {

            return $true
        }
    }

    return $false
}

# =============================================================================
# INVOCATION OLLAMA
# =============================================================================

function Invoke-Ollama {

    param(
        [Parameter(Mandatory)]
        [string[]]$Arguments,

        [int]$TimeoutSec = $PullTimeoutSec
    )

    $psi = [System.Diagnostics.ProcessStartInfo]::new()

    $psi.FileName = $OllamaExe

    $escaped = foreach ($argument in $Arguments) {

        if ($argument -match '[\s"]') {

            '"' + ($argument -replace '"', '\"') + '"'
        }
        else {

            $argument
        }
    }

    $psi.Arguments = ($escaped -join ' ')

    $psi.UseShellExecute = $false

    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError  = $true

    $psi.CreateNoWindow = $true

    $psi.Environment['OLLAMA_HOST']   = $OllamaHost
    $psi.Environment['OLLAMA_MODELS'] = $ModelsRoot

    $process = [System.Diagnostics.Process]::new()

    $process.StartInfo = $psi

    if (-not $process.Start()) {

        throw "Impossible de démarrer ollama.exe."
    }

    $stdoutTask = $process.StandardOutput.ReadToEndAsync()
    $stderrTask = $process.StandardError.ReadToEndAsync()

    if (-not $process.WaitForExit($TimeoutSec * 1000)) {

        try {
            $process.Kill($true)
        }
        catch {
        }

        throw `
            "Commande Ollama timeout après $TimeoutSec secondes : ollama $($Arguments -join ' ')"
    }

    $stdout = $stdoutTask.Result
    $stderr = $stderrTask.Result

    return [pscustomobject]@{
        ExitCode = $process.ExitCode
        StdOut   = $stdout
        StdErr   = $stderr
    }
}

# =============================================================================
# METADONNÉES
# =============================================================================

function Get-ModelMetadata {

    param(
        [Parameter(Mandatory)]
        [string]$ModelName
    )

    try {

        $result = Invoke-Ollama `
            -Arguments @(
                'show'
                $ModelName
            ) `
            -TimeoutSec 60

        return [pscustomobject]@{
            ExitCode = $result.ExitCode
            StdOut   = $result.StdOut
            StdErr   = $result.StdErr
        }
    }
    catch {

        return $null
    }
}

# =============================================================================
# EXTRACTION QUANTIFICATION
# =============================================================================

function Get-Quantization {

    param(
        [Parameter(Mandatory)]
        [string]$Text
    )

    if ($Text -match '(?im)^\s*quantization\s*[:=]\s*(.+?)\s*$') {

        return $Matches[1].Trim()
    }

    if ($Text -match '(?i)\bQ4_K_M\b') {

        return 'Q4_K_M'
    }

    return $null
}

# =============================================================================
# RÉSULTAT
# =============================================================================

function New-Result {

    param(
        [string]$Model
    )

    return [ordered]@{

        Model = $Model

        WasAlreadyInstalled = $false
        PullAttempted       = $false
        PullExitCode        = $null

        InstalledAfterPull  = $false

        Quantization        = $null
        ParameterSize       = $null
        Format              = $null
        Family              = $null

        ReportedAsQ4KM      = $false

        DiskBeforeGB        = $null
        DiskAfterGB         = $null
        DiskConsumedGB      = $null

        Status              = 'NOT_PROCESSED'

        Error               = $null
    }
}

# =============================================================================
# VALIDATION CANDIDATS
# =============================================================================

function Test-CandidateName {

    param(
        [string]$Model
    )

    foreach ($pattern in $ExcludedPatterns) {

        if ($Model -match [regex]::Escape($pattern)) {

            return $false
        }
    }

    return $true
}

# =============================================================================
# MAIN
# =============================================================================

try {

    Write-Host ''
    Write-Host ('=' * 80)
    Write-Host '       E-ZZIO — Q4_K_M MODEL ACQUISITION GATE'
    Write-Host '       v1.1.0 — ISOLATED OLLAMA SERVER'
    Write-Host '       SAFE / NON-DESTRUCTIVE / FORENSIC'
    Write-Host ('=' * 80)

    Write-Info "Version      : $Version"
    Write-Info "RunId        : $RunId"
    Write-Info "Ollama       : $OllamaExe"
    Write-Info "Models Root  : $ModelsRoot"
    Write-Info "OLLAMA_HOST  : $OllamaHost"
    Write-Info "Minimum free : $MinimumFreeGB GB"

    # =========================================================================
    # [1/7] ENVIRONNEMENT
    # =========================================================================

    Write-Section '[1/7] VALIDATION ENVIRONNEMENT'

    if (-not (Test-Path -LiteralPath $OllamaExe -PathType Leaf)) {

        throw "ollama.exe introuvable : $OllamaExe"
    }

    if (-not (Test-Path -LiteralPath $ModelsRoot -PathType Container)) {

        throw "Models Root introuvable : $ModelsRoot"
    }

    if (-not (Test-Path -LiteralPath $AuditRoot -PathType Container)) {

        New-Item `
            -Path $AuditRoot `
            -ItemType Directory `
            -Force |
            Out-Null
    }

    Write-Pass 'ollama.exe présent.'
    Write-Pass 'Models Root présent.'
    Write-Pass 'Audit Root présent.'

    # =========================================================================
    # [2/7] DISQUE
    # =========================================================================

    Write-Section '[2/7] VALIDATION ESPACE DISQUE'

    $freeBefore = Get-FreeSpaceGB

    Write-Info "Espace libre initial : $freeBefore GB"

    if ($freeBefore -lt $MinimumFreeGB) {

        throw `
            "Espace libre insuffisant : $freeBefore GB."
    }

    Write-Pass "Marge disque disponible : $freeBefore GB."

    # =========================================================================
    # [3/7] VALIDATION CANDIDATS
    # =========================================================================

    Write-Section '[3/7] VALIDATION MATRICE CANDIDATS'

    foreach ($model in $TargetModels) {

        if (-not (Test-CandidateName -Model $model)) {

            throw `
                "Modèle interdit dans la matrice générative : $model"
        }

        Write-Info "Candidat : $model"
    }

    Write-Pass "Matrice validée : $($TargetModels.Count) candidats."

    # =========================================================================
    # [4/7] SERVEUR OLLAMA ISOLÉ
    # =========================================================================

    Write-Section '[4/7] DÉMARRAGE SERVEUR OLLAMA ISOLÉ'

    #
    # On NE TOUCHE PAS au serveur Ollama utilisateur.
    #
    # Notre instance utilise :
    #
    #   127.0.0.1:11435
    #
    # L'instance standard peut continuer sur 11434.
    #

    $serverPsi = [System.Diagnostics.ProcessStartInfo]::new()

    $serverPsi.FileName = $OllamaExe
    $serverPsi.Arguments = 'serve'

    $serverPsi.UseShellExecute = $false

    $serverPsi.RedirectStandardOutput = $true
    $serverPsi.RedirectStandardError  = $true

    $serverPsi.CreateNoWindow = $true

    $serverPsi.Environment['OLLAMA_HOST']   = $OllamaHost
    $serverPsi.Environment['OLLAMA_MODELS'] = $ModelsRoot

    $ServerProcess = [System.Diagnostics.Process]::new()

    $ServerProcess.StartInfo = $serverPsi

    if (-not $ServerProcess.Start()) {

        throw 'Impossible de démarrer le serveur Ollama isolé.'
    }

    $ServerStartedByUs = $true

    Write-Info "PID serveur isolé : $($ServerProcess.Id)"

    Wait-OllamaServer `
        -TimeoutSec $ServerStartupTimeoutSec

    # =========================================================================
    # [5/7] INVENTAIRE
    # =========================================================================

    Write-Section '[5/7] INVENTAIRE INITIAL'

    $inventory = Get-OllamaInventory

    if ($inventory.Count -eq 0) {

        Write-Warn 'Aucun modèle visible sur cette instance.'
    }
    else {

        Write-Info "Modèles visibles : $($inventory.Count)"

        foreach ($item in $inventory) {

            Write-Host "  $($item.name)  $($item.size)"
        }
    }

    # =========================================================================
    # [6/7] ACQUISITION
    # =========================================================================

    Write-Section '[6/7] ACQUISITION DES MODÈLES'

    foreach ($model in $TargetModels) {

        Write-Host ''
        Write-Host ('=' * 80)
        Write-Host " CANDIDAT : $model"
        Write-Host ('=' * 80)

        $result = New-Result -Model $model

        try {

            $diskBefore = Get-FreeSpaceGB

            $result.DiskBeforeGB = $diskBefore

            Write-Info "Espace libre avant : $diskBefore GB"

            if ($diskBefore -lt $MinimumFreeGB) {

                throw `
                    "Marge disque minimale atteinte."
            }

            # -----------------------------------------------------------------
            # PRÉSENCE
            # -----------------------------------------------------------------

            if (Test-ModelInstalled -ModelName $model) {

                $result.WasAlreadyInstalled = $true

                Write-Pass "Déjà présent : $model"
            }
            else {

                Write-Info "Téléchargement : $model"

                $result.PullAttempted = $true

                $pull = Invoke-Ollama `
                    -Arguments @(
                        'pull'
                        $model
                    ) `
                    -TimeoutSec $PullTimeoutSec

                $result.PullExitCode = $pull.ExitCode

                if ($pull.StdOut) {

                    Write-Host $pull.StdOut
                }

                if ($pull.StdErr) {

                    Write-Warn $pull.StdErr
                }

                if ($pull.ExitCode -ne 0) {

                    throw `
                        "ollama pull échoué avec code $($pull.ExitCode)."
                }

                Write-Pass "Pull terminé : $model"
            }

            # -----------------------------------------------------------------
            # PRÉSENCE POST-PULL
            # -----------------------------------------------------------------

            if (-not (Test-ModelInstalled -ModelName $model)) {

                throw `
                    "Modèle absent de /api/tags après acquisition."
            }

            $result.InstalledAfterPull = $true

            Write-Pass 'Présence API confirmée.'

            # -----------------------------------------------------------------
            # SHOW
            # -----------------------------------------------------------------

            $metadata = Get-ModelMetadata `
                -ModelName $model

            if ($null -eq $metadata) {

                throw `
                    "Impossible de récupérer les métadonnées du modèle."
            }

            if ($metadata.ExitCode -ne 0) {

                throw `
                    "ollama show a échoué pour $model."
            }

            $quantization = Get-Quantization `
                -Text $metadata.StdOut

            $result.Quantization = $quantization

            Write-Info "Quantification détectée : $quantization"

            if ($quantization -eq 'Q4_K_M') {

                $result.ReportedAsQ4KM = $true

                Write-Pass 'Q4_K_M détecté dans les métadonnées.'
            }
            else {

                Write-Warn `
                    "Q4_K_M NON confirmé pour $model."

                Write-Warn `
                    'Le script refuse de qualifier arbitrairement ce modèle.'
            }

            # -----------------------------------------------------------------
            # DISQUE
            # -----------------------------------------------------------------

            $diskAfter = Get-FreeSpaceGB

            $result.DiskAfterGB = $diskAfter

            $result.DiskConsumedGB = [math]::Round(
                [math]::Max(
                    0.0,
                    $diskBefore - $diskAfter
                ),
                3
            )

            Write-Info "Espace libre après : $diskAfter GB"
            Write-Info "Consommation estimée : $($result.DiskConsumedGB) GB"

            if ($diskAfter -lt $MinimumFreeGB) {

                throw `
                    "Marge disque minimale dépassée."
            }

            if ($result.ReportedAsQ4KM) {

                $result.Status = 'ACQUIRED_Q4_K_M'
            }
            else {

                $result.Status = 'ACQUIRED_QUANTIFICATION_UNVERIFIED'
            }
        }
        catch {

            $result.Status = 'FAIL_CLOSED'
            $result.Error = $_.Exception.Message

            $OverallPass = $false

            Write-Fail `
                "$model : $($result.Error)"

            Write-Warn `
                'Aucune suppression automatique.'
        }

        $Results.Add(
            [pscustomobject]$result
        )
    }

    # =========================================================================
    # [7/7] RAPPORT FINAL
    # =========================================================================

    Write-Section '[7/7] RAPPORT FORENSIC'

    $freeFinal = Get-FreeSpaceGB

    $acquired = @(
        $Results |
            Where-Object {
                $_.Status -eq 'ACQUIRED_Q4_K_M'
            }
    ).Count

    $unverified = @(
        $Results |
            Where-Object {
                $_.Status -eq 'ACQUIRED_QUANTIFICATION_UNVERIFIED'
            }
    ).Count

    $failed = @(
        $Results |
            Where-Object {
                $_.Status -eq 'FAIL_CLOSED'
            }
    ).Count

    if ($freeFinal -lt $MinimumFreeGB) {

        $OverallPass = $false

        Write-Fail `
            "Espace libre final insuffisant : $freeFinal GB."
    }
    else {

        Write-Pass `
            "Marge disque finale conservée : $freeFinal GB."
    }

    $summary = [ordered]@{

        Engine = 'E-ZZIO Q4_K_M MODEL ACQUISITION GATE'

        Version = $Version

        RunId = $RunId

        Timestamp = (Get-Date).ToString('o')

        OllamaExe = $OllamaExe

        ModelsRoot = $ModelsRoot

        OllamaHost = $OllamaHost

        ServerPid = if ($null -ne $ServerProcess) {
            $ServerProcess.Id
        }
        else {
            $null
        }

        TargetModels = $TargetModels

        MinimumFreeGB = $MinimumFreeGB

        InitialFreeGB = $freeBefore

        FinalFreeGB = $freeFinal

        CandidatesProcessed = $Results.Count

        Q4KMConfirmed = $acquired

        QuantificationUnverified = $unverified

        Failed = $failed

        FatalErrors = $FatalErrors

        OverallPass = $OverallPass

        Results = @($Results)
    }

    $json = $summary |
        ConvertTo-Json `
            -Depth 100

    Set-Content `
        -LiteralPath $ReportPath `
        -Value $json `
        -Encoding utf8

    # -------------------------------------------------------------------------
    # RE-READ FORENSIC
    # -------------------------------------------------------------------------

    $reloaded = Get-Content `
        -LiteralPath $ReportPath `
        -Raw `
        -Encoding utf8

    $null = $reloaded |
        ConvertFrom-Json `
            -Depth 100 `
            -ErrorAction Stop

    Write-Pass 'Rapport JSON écrit et relu avec succès.'

    # =========================================================================
    # VERDICT
    # =========================================================================

    Write-Host ''
    Write-Host ('=' * 80)
    Write-Host '       E-ZZIO — Q4_K_M MODEL ACQUISITION GATE'
    Write-Host '                         FINAL VERDICT'
    Write-Host ('=' * 80)
    Write-Host ''

    Write-Info "Candidats traités           : $($Results.Count)"
    Write-Info "Q4_K_M confirmés            : $acquired"
    Write-Info "Quantification non vérifiée : $unverified"
    Write-Info "Échecs                       : $failed"
    Write-Info "Erreurs fatales              : $FatalErrors"
    Write-Info "Espace libre final           : $freeFinal GB"

    if ($OverallPass -and $acquired -eq $TargetModels.Count) {

        Write-Pass `
            'ACQUISITION GATE : PASS — TOUS LES CANDIDATS Q4_K_M CONFIRMÉS.'
    }
    elseif ($failed -gt 0) {

        Write-Fail `
            'ACQUISITION GATE : FAIL-CLOSED — AU MOINS UNE ACQUISITION A ÉCHOUÉ.'
    }
    else {

        Write-Warn `
            'ACQUISITION GATE : PARTIAL — MODÈLES ACQUIS MAIS Q4_K_M NON CONFIRMÉ POUR TOUS.'
    }

    Write-Info "Rapport : $ReportPath"

    Write-Host ''
    Write-Host ('=' * 80)
    Write-Host ' E-ZZIO — Q4_K_M MODEL ACQUISITION GATE — TERMINÉ'
    Write-Host ('=' * 80)
    Write-Host ''
}
catch {

    $FatalErrors++
    $OverallPass = $false

    Write-Fail `
        "EXCEPTION FATALE : $($_.Exception.Message)"
}
finally {

    # =========================================================================
    # ARRÊT UNIQUEMENT DE NOTRE SERVEUR
    # =========================================================================

    if (
        $ServerStartedByUs -and
        $null -ne $ServerProcess
    ) {

        Write-Info `
            "Arrêt du serveur Ollama isolé PID $($ServerProcess.Id) ..."

        try {

            if (-not $ServerProcess.HasExited) {

                $ServerProcess.Kill($true)
                $ServerProcess.WaitForExit(5000) | Out-Null
            }

            Write-Pass `
                'Serveur Ollama isolé arrêté.'
        }
        catch {

            Write-Warn `
                "Impossible de confirmer l'arrêt du serveur isolé : $($_.Exception.Message)"
        }
    }
}

# =============================================================================
# EXIT CODE
# =============================================================================

if ($OverallPass -and ($Results.Count -eq $TargetModels.Count)) {

    exit 0
}
else {

    exit 2
}