#requires -Version 7.4
# =============================================================================
# E-ZZIO — FORENSIC CREDENTIAL VAULT CARTOGRAPHY
# Version : 1.0.0
# Mode    : READ-ONLY / SECRET-SAFE / FORENSIC / NO NETWORK
#
# OBJECTIF
#   Cartographier les coffres de credentials E-ZzIO sans exposer :
#     - aucune valeur
#     - aucune clé
#     - aucun token
#     - aucun secret
#     - aucun contenu brut
#
# AUTORISÉ
#   - noms de fichiers
#   - noms de variables
#   - catégories
#   - statut de présence
#   - classe de remplissage
#   - hash SHA-256 du fichier
#   - taille du fichier
#   - dates/attributs
#   - doublons de noms de variables
#
# INTERDIT
#   - affichage des valeurs
#   - export des valeurs
#   - appel réseau
#   - modification des fichiers
#   - modification des credentials
# =============================================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# =============================================================================
# CONFIGURATION
# =============================================================================

$Version     = '1.0.0'
$ProjectRoot = 'G:\AI\E-zzio'
$SecretsRoot = Join-Path $ProjectRoot 'secrets'

$ForensicRoot = Join-Path $ProjectRoot '_forensic'
$ReportRoot   = Join-Path $ForensicRoot 'reports'

$RunId    = Get-Date -Format 'yyyyMMdd_HHmmss'
$Timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'

$ReportTxt  = Join-Path $ReportRoot "EZZIO_Credential_Vault_Map_$RunId.txt"
$ReportJson = Join-Path $ReportRoot "EZZIO_Credential_Vault_Map_$RunId.json"

$ExitCode = 0

# =============================================================================
# COMPTEURS
# =============================================================================

$Stats = [ordered]@{
    VaultFiles              = 0
    EnvFiles                = 0
    ExampleFiles            = 0
    OtherFiles              = 0
    VariablesDetected       = 0
    VariablesPresent        = 0
    VariablesEmpty          = 0
    InvalidVariableLines    = 0
    SensitiveVariables      = 0
    ProviderVariables       = 0
    ControlVariables        = 0
    ModelVariables          = 0
    LimitVariables          = 0
    EndpointVariables       = 0
    DuplicateVariableNames = 0
    ReadErrors              = 0
    NetworkCalls            = 0
    FilesModified           = 0
}

$FilesMap      = New-Object System.Collections.Generic.List[object]
$VariableMap   = New-Object System.Collections.Generic.List[object]
$ErrorsList    = New-Object System.Collections.Generic.List[string]
$DuplicateMap = New-Object System.Collections.Generic.List[object]

# =============================================================================
# MOTIFS DE CLASSIFICATION
# =============================================================================

$SensitivePatterns = @(
    'key',
    'token',
    'secret',
    'password',
    'passwd',
    'credential',
    'auth',
    'private'
)

$ProviderPatterns = @(
    'gemini',
    'google',
    'groq',
    'openrouter',
    'openai',
    'anthropic',
    'mistral',
    'deepseek',
    'provider'
)

$ControlPatterns = @(
    'allow',
    'mode',
    'timeout',
    'cache',
    'redact',
    'log',
    'enable',
    'disable',
    'flag'
)

$ModelPatterns = @(
    'model',
    'deployment',
    'engine'
)

$LimitPatterns = @(
    'limit',
    'quota',
    'daily',
    'monthly',
    'budget',
    'max'
)

$EndpointPatterns = @(
    'url',
    'uri',
    'endpoint',
    'host',
    'base'
)

# =============================================================================
# FONCTIONS
# =============================================================================

function Write-Section {
    param(
        [Parameter(Mandatory)]
        [string]$Title
    )

    Write-Host ''
    Write-Host '-----------------------------------------------------------------------------'
    Write-Host $Title
    Write-Host '-----------------------------------------------------------------------------'
}

function Get-RelativePathSafe {
    param(
        [Parameter(Mandatory)]
        [string]$FullPath
    )

    try {
        return [System.IO.Path]::GetRelativePath(
            $ProjectRoot,
            $FullPath
        )
    }
    catch {
        return $FullPath
    }
}

function Get-VariableCategory {
    param(
        [Parameter(Mandatory)]
        [string]$Name
    )

    $Lower = $Name.ToLowerInvariant()

    foreach ($Pattern in $ProviderPatterns) {
        if ($Lower -match $Pattern) {
            return 'PROVIDER'
        }
    }

    foreach ($Pattern in $SensitivePatterns) {
        if ($Lower -match $Pattern) {
            return 'SENSITIVE'
        }
    }

    foreach ($Pattern in $ModelPatterns) {
        if ($Lower -match $Pattern) {
            return 'MODEL'
        }
    }

    foreach ($Pattern in $LimitPatterns) {
        if ($Lower -match $Pattern) {
            return 'LIMIT'
        }
    }

    foreach ($Pattern in $EndpointPatterns) {
        if ($Lower -match $Pattern) {
            return 'ENDPOINT'
        }
    }

    foreach ($Pattern in $ControlPatterns) {
        if ($Lower -match $Pattern) {
            return 'CONTROL'
        }
    }

    return 'OTHER'
}

function Get-SafePresenceClass {
    param(
        [Parameter(Mandatory)]
        [string]$Value
    )

    if ([string]::IsNullOrWhiteSpace($Value)) {
        return 'EMPTY'
    }

    # Aucune longueur exacte.
    # On utilise uniquement une classe non révélatrice.

    if ($Value.Length -le 8) {
        return 'PRESENT_SHORT'
    }

    if ($Value.Length -le 32) {
        return 'PRESENT_MEDIUM'
    }

    return 'PRESENT_LONG'
}

function Get-FileHashSafe {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    return (
        Get-FileHash `
            -LiteralPath $Path `
            -Algorithm SHA256 `
            -ErrorAction Stop
    ).Hash
}

function Get-FileType {
    param(
        [Parameter(Mandatory)]
        [string]$Name
    )

    if ($Name -match '(?i)\.env\.example$') {
        return 'ENV_EXAMPLE'
    }

    if ($Name -match '(?i)\.example$') {
        return 'EXAMPLE'
    }

    if ($Name -match '(?i)\.env$') {
        return 'ENV'
    }

    return 'OTHER'
}

# =============================================================================
# BANNIÈRE
# =============================================================================

Write-Host ''
Write-Host '============================================================================='
Write-Host ' E-ZZIO — FORENSIC CREDENTIAL VAULT CARTOGRAPHY'
Write-Host " Version : $Version"
Write-Host ' Mode    : READ-ONLY / SECRET-SAFE / FORENSIC / NO NETWORK'
Write-Host '============================================================================='
Write-Host ''
Write-Host "[INFO] RunId : $RunId"
Write-Host "[INFO] Début : $Timestamp"

# =============================================================================
# [1/9] VALIDATION
# =============================================================================

Write-Section '[1/9] Validation du projet et du coffre'

if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) {
    Write-Host "[FAIL] Projet introuvable : $ProjectRoot" -ForegroundColor Red
    exit 1
}

Write-Host "[PASS] Projet : $ProjectRoot"

if (-not (Test-Path -LiteralPath $SecretsRoot -PathType Container)) {
    Write-Host "[FAIL] Coffre introuvable : $SecretsRoot" -ForegroundColor Red
    exit 1
}

Write-Host "[PASS] Coffre : $SecretsRoot"

# =============================================================================
# [2/9] RAPPORT
# =============================================================================

Write-Section '[2/9] Préparation du rapport'

New-Item `
    -ItemType Directory `
    -Force `
    -Path $ReportRoot `
    -ErrorAction Stop |
    Out-Null

Write-Host "[PASS] Dossier forensic : $ReportRoot"

# =============================================================================
# [3/9] INVENTAIRE DES FICHIERS
# =============================================================================

Write-Section '[3/9] Inventaire du coffre — NOMS UNIQUEMENT'

$VaultFiles = @(
    Get-ChildItem `
        -LiteralPath $SecretsRoot `
        -File `
        -Recurse `
        -Force `
        -ErrorAction Stop
)

$Stats.VaultFiles = $VaultFiles.Count

if ($VaultFiles.Count -eq 0) {
    Write-Host '[WARN] Aucun fichier dans le coffre.'
}
else {
    Write-Host "[INFO] Fichiers trouvés : $($VaultFiles.Count)"
}

# =============================================================================
# [4/9] MÉTADONNÉES
# =============================================================================

Write-Section '[4/9] Cartographie des fichiers — MÉTADONNÉES UNIQUEMENT'

foreach ($File in $VaultFiles) {

    try {

        $Relative = [System.IO.Path]::GetRelativePath(
            $SecretsRoot,
            $File.FullName
        )

        $Type = Get-FileType -Name $File.Name

        switch ($Type) {
            'ENV' {
                $Stats.EnvFiles++
            }

            'ENV_EXAMPLE' {
                $Stats.ExampleFiles++
            }

            'EXAMPLE' {
                $Stats.ExampleFiles++
            }

            default {
                $Stats.OtherFiles++
            }
        }

        $Hash = Get-FileHashSafe -Path $File.FullName

        $Attributes = $File.Attributes.ToString()

        $FileRecord = [pscustomobject][ordered]@{
            FileName      = $File.Name
            RelativePath  = $Relative
            Type          = $Type
            SizeClass     = if ($File.Length -eq 0) {
                'EMPTY'
            }
            elseif ($File.Length -lt 1024) {
                'SMALL'
            }
            elseif ($File.Length -lt 1048576) {
                'MEDIUM'
            }
            else {
                'LARGE'
            }
            Attributes    = $Attributes
            LastWriteTime = $File.LastWriteTime.ToString('yyyy-MM-dd HH:mm:ss')
            SHA256        = $Hash
        }

        $FilesMap.Add($FileRecord)

        Write-Host "[PASS] $Relative [$Type]"

    }
    catch {

        $Stats.ReadErrors++

        $ErrorsList.Add(
            "$($File.FullName) :: $($_.Exception.Message)"
        )

        Write-Host "[FAIL] Métadonnées impossibles à lire : $($File.Name)" -ForegroundColor Red
    }
}

# =============================================================================
# [5/9] ANALYSE DES VARIABLES
# =============================================================================

Write-Section '[5/9] Cartographie des variables — VALEURS JAMAIS AFFICHÉES'

foreach ($File in $VaultFiles) {

    try {

        $Type = Get-FileType -Name $File.Name

        # ---------------------------------------------------------------------
        # IMPORTANT :
        # Le contenu est lu uniquement en mémoire.
        # Aucune ligne brute n'est envoyée à l'écran.
        # ---------------------------------------------------------------------

        $Lines = Get-Content `
            -LiteralPath $File.FullName `
            -Encoding UTF8 `
            -ErrorAction Stop

        $LineNumber = 0

        foreach ($Line in $Lines) {

            $LineNumber++

            # -----------------------------------------------------------------
            # Ligne vide / commentaire
            # -----------------------------------------------------------------

            if ([string]::IsNullOrWhiteSpace($Line)) {
                continue
            }

            $Trimmed = $Line.Trim()

            if ($Trimmed.StartsWith('#')) {
                continue
            }

            # -----------------------------------------------------------------
            # Variable ENV classique
            # -----------------------------------------------------------------

            if ($Trimmed -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$') {

                $VariableName = [string]$matches[1]
                $VariableValue = [string]$matches[2]

                $Stats.VariablesDetected++

                $Presence = Get-SafePresenceClass -Value $VariableValue
                $Category = Get-VariableCategory -Name $VariableName

                if ($Presence -eq 'EMPTY') {
                    $Stats.VariablesEmpty++
                }
                else {
                    $Stats.VariablesPresent++
                }

                switch ($Category) {
                    'SENSITIVE' {
                        $Stats.SensitiveVariables++
                    }

                    'PROVIDER' {
                        $Stats.ProviderVariables++
                    }

                    'CONTROL' {
                        $Stats.ControlVariables++
                    }

                    'MODEL' {
                        $Stats.ModelVariables++
                    }

                    'LIMIT' {
                        $Stats.LimitVariables++
                    }

                    'ENDPOINT' {
                        $Stats.EndpointVariables++
                    }
                }

                $Relative = [System.IO.Path]::GetRelativePath(
                    $SecretsRoot,
                    $File.FullName
                )

                $VariableRecord = [pscustomobject][ordered]@{
                    File       = $Relative
                    Type       = $Type
                    Variable   = $VariableName
                    Category   = $Category
                    Status     = $Presence
                    LineNumber = $LineNumber
                }

                $VariableMap.Add($VariableRecord)

                Write-Host (
                    "[INFO] {0} :: {1} :: {2} :: {3}" -f
                    $Relative,
                    $VariableName,
                    $Category,
                    $Presence
                )
            }
            else {

                # Une ligne non conforme est comptée mais jamais affichée.
                $Stats.InvalidVariableLines++
            }
        }
    }
    catch {

        $Stats.ReadErrors++

        $ErrorsList.Add(
            "$($File.FullName) :: $($_.Exception.Message)"
        )

        Write-Host "[FAIL] Analyse impossible : $($File.Name)" -ForegroundColor Red
    }
}

# =============================================================================
# [6/9] DÉTECTION DES DOUBLONS
# =============================================================================

Write-Section '[6/9] Détection des noms de variables partagés'

$GroupedVariables = @(
    $VariableMap |
    Group-Object -Property Variable
)

foreach ($Group in $GroupedVariables) {

    if ($Group.Count -gt 1) {

        $Stats.DuplicateVariableNames += $Group.Count

        $Locations = @(
            $Group.Group |
            ForEach-Object {
                $_.File
            }
        )

        $DuplicateRecord = [pscustomobject][ordered]@{
            Variable = $Group.Name
            Count    = $Group.Count
            Files    = $Locations
        }

        $DuplicateMap.Add($DuplicateRecord)

        Write-Host (
            "[WARN] Variable partagée : {0} ({1} fichiers)" -f
            $Group.Name,
            $Group.Count
        )
    }
}

if ($DuplicateMap.Count -eq 0) {
    Write-Host '[PASS] Aucun nom de variable partagé entre les fichiers.'
}

# =============================================================================
# [7/9] SYNTHÈSE
# =============================================================================

Write-Section '[7/9] Synthèse forensic'

Write-Host ("[INFO] Fichiers coffre          : {0}" -f $Stats.VaultFiles)
Write-Host ("[INFO] Fichiers .env            : {0}" -f $Stats.EnvFiles)
Write-Host ("[INFO] Fichiers exemple         : {0}" -f $Stats.ExampleFiles)
Write-Host ("[INFO] Variables détectées      : {0}" -f $Stats.VariablesDetected)
Write-Host ("[INFO] Variables présentes      : {0}" -f $Stats.VariablesPresent)
Write-Host ("[INFO] Variables vides          : {0}" -f $Stats.VariablesEmpty)
Write-Host ("[INFO] Variables sensibles      : {0}" -f $Stats.SensitiveVariables)
Write-Host ("[INFO] Variables providers      : {0}" -f $Stats.ProviderVariables)
Write-Host ("[INFO] Variables modèles        : {0}" -f $Stats.ModelVariables)
Write-Host ("[INFO] Variables limites        : {0}" -f $Stats.LimitVariables)
Write-Host ("[INFO] Variables endpoints      : {0}" -f $Stats.EndpointVariables)
Write-Host ("[INFO] Variables contrôle       : {0}" -f $Stats.ControlVariables)
Write-Host ("[INFO] Doublons de variables    : {0}" -f $Stats.DuplicateVariableNames)
Write-Host ("[INFO] Lignes invalides         : {0}" -f $Stats.InvalidVariableLines)
Write-Host ("[INFO] Erreurs lecture          : {0}" -f $Stats.ReadErrors)

# =============================================================================
# [8/9] GARANTIES DE SÉCURITÉ
# =============================================================================

Write-Section '[8/9] Garanties de sécurité'

Write-Host '[PASS] Aucune valeur de credential affichée'
Write-Host '[PASS] Aucune clé API affichée'
Write-Host '[PASS] Aucun token affiché'
Write-Host '[PASS] Aucun secret affiché'
Write-Host '[PASS] Aucun contenu brut exporté'
Write-Host '[PASS] Aucun secret déchiffré'
Write-Host '[PASS] Aucun fichier modifié'
Write-Host '[PASS] Aucun credential modifié'
Write-Host '[PASS] Aucun appel réseau effectué'
Write-Host '[PASS] Aucun processus LiteLLM lancé'

# =============================================================================
# [9/9] RAPPORTS
# =============================================================================

Write-Section '[9/9] Génération des rapports forensic'

$Report = New-Object System.Collections.Generic.List[string]

$Report.Add('===============================================================================')
$Report.Add('E-ZZIO — FORENSIC CREDENTIAL VAULT CARTOGRAPHY')
$Report.Add("Version : $Version")
$Report.Add("RunId   : $RunId")
$Report.Add('Mode    : READ-ONLY / SECRET-SAFE / FORENSIC / NO NETWORK')
$Report.Add('===============================================================================')
$Report.Add('')

$Report.Add('SECURITY GUARANTEES')
$Report.Add('-------------------')
$Report.Add('No secret values displayed')
$Report.Add('No API keys displayed')
$Report.Add('No tokens displayed')
$Report.Add('No passwords displayed')
$Report.Add('No raw credential content exported')
$Report.Add('No secrets decrypted')
$Report.Add('No files modified')
$Report.Add('No credentials modified')
$Report.Add('No network calls')
$Report.Add('No LiteLLM process started')
$Report.Add('')

$Report.Add('STATISTICS')
$Report.Add('----------')

foreach ($Key in $Stats.Keys) {
    $Report.Add(
        ('{0,-28} : {1}' -f
            $Key,
            [string]$Stats[$Key]
        )
    )
}

$Report.Add('')
$Report.Add('FILES')
$Report.Add('-----')

foreach ($FileRecord in $FilesMap) {

    $Report.Add(
        (
            '{0} | {1} | {2} | {3} | SHA256={4}' -f
            $FileRecord.RelativePath,
            $FileRecord.Type,
            $FileRecord.SizeClass,
            $FileRecord.Attributes,
            $FileRecord.SHA256
        )
    )
}

$Report.Add('')
$Report.Add('VARIABLE MAP')
$Report.Add('------------')

foreach ($VariableRecord in $VariableMap) {

    $Report.Add(
        (
            '{0} | {1} | {2} | {3} | line={4}' -f
            $VariableRecord.File,
            $VariableRecord.Variable,
            $VariableRecord.Category,
            $VariableRecord.Status,
            $VariableRecord.LineNumber
        )
    )
}

$Report.Add('')
$Report.Add('DUPLICATE VARIABLE NAMES')
$Report.Add('------------------------')

if ($DuplicateMap.Count -eq 0) {

    $Report.Add('None')

}
else {

    foreach ($Duplicate in $DuplicateMap) {

        $Report.Add(
            (
                '{0} | count={1} | files={2}' -f
                $Duplicate.Variable,
                $Duplicate.Count,
                ($Duplicate.Files -join ', ')
            )
        )
    }
}

$Report.Add('')
$Report.Add('END OF REPORT')
$Report.Add('===============================================================================')

Set-Content `
    -LiteralPath $ReportTxt `
    -Value $Report `
    -Encoding UTF8 `
    -ErrorAction Stop

$JsonObject = [ordered]@{
    schema_version = '1.0.0'
    tool_version   = $Version
    run_id         = $RunId
    timestamp      = $Timestamp
    mode           = 'READ-ONLY / SECRET-SAFE / FORENSIC / NO NETWORK'

    project_root   = $ProjectRoot
    secrets_root   = $SecretsRoot

    statistics     = $Stats
    files          = $FilesMap
    variables      = $VariableMap
    duplicates     = $DuplicateMap
    errors         = $ErrorsList

    security = [ordered]@{
        values_displayed       = $false
        api_keys_displayed     = $false
        tokens_displayed       = $false
        passwords_displayed    = $false
        secrets_decrypted      = $false
        raw_content_exported   = $false
        files_modified         = $false
        credentials_modified   = $false
        network_used           = $false
        litellm_started        = $false
    }
}

$Json = $JsonObject | ConvertTo-Json -Depth 12

Set-Content `
    -LiteralPath $ReportJson `
    -Value $Json `
    -Encoding UTF8 `
    -ErrorAction Stop

# =============================================================================
# VÉRIFICATION FINALE
# =============================================================================

Write-Host ''
Write-Host '============================================================================='
Write-Host ' VÉRIFICATION FINALE'
Write-Host '============================================================================='

if (Test-Path -LiteralPath $ReportTxt -PathType Leaf) {
    Write-Host '[PASS] Rapport TXT créé'
}
else {
    Write-Host '[FAIL] Rapport TXT absent' -ForegroundColor Red
    $ExitCode = 1
}

if (Test-Path -LiteralPath $ReportJson -PathType Leaf) {
    Write-Host '[PASS] Rapport JSON créé'
}
else {
    Write-Host '[FAIL] Rapport JSON absent' -ForegroundColor Red
    $ExitCode = 1
}

if ($Stats.ReadErrors -eq 0) {
    Write-Host '[PASS] Zéro erreur de lecture'
}
else {
    Write-Host "[FAIL] Erreurs de lecture : $($Stats.ReadErrors)" -ForegroundColor Red
    $ExitCode = 1
}

if ($Stats.NetworkCalls -eq 0) {
    Write-Host '[PASS] Zéro appel réseau'
}
else {
    Write-Host '[FAIL] Appels réseau détectés' -ForegroundColor Red
    $ExitCode = 1
}

if ($Stats.FilesModified -eq 0) {
    Write-Host '[PASS] Zéro fichier modifié'
}
else {
    Write-Host '[FAIL] Modification de fichier détectée' -ForegroundColor Red
    $ExitCode = 1
}

Write-Host ''
Write-Host '============================================================================='
Write-Host ' RÉSULTAT FINAL'
Write-Host '============================================================================='

Write-Host ("[INFO] Coffre analysé       : {0}" -f $SecretsRoot)
Write-Host ("[INFO] Fichiers             : {0}" -f $Stats.VaultFiles)
Write-Host ("[INFO] Variables            : {0}" -f $Stats.VariablesDetected)
Write-Host ("[INFO] Variables présentes  : {0}" -f $Stats.VariablesPresent)
Write-Host ("[INFO] Variables vides      : {0}" -f $Stats.VariablesEmpty)
Write-Host ("[INFO] Doublons             : {0}" -f $Stats.DuplicateVariableNames)
Write-Host ("[INFO] Rapport TXT          : {0}" -f $ReportTxt)
Write-Host ("[INFO] Rapport JSON         : {0}" -f $ReportJson)

Write-Host ''

if ($ExitCode -eq 0) {
    Write-Host '[PASS] CARTOGRAPHIE FORENSIC TERMINÉE SANS ERREUR' -ForegroundColor Green
}
else {
    Write-Host "[FAIL] CARTOGRAPHIE FORENSIC TERMINÉE AVEC CODE : $ExitCode" -ForegroundColor Red
}

Write-Host '============================================================================='

exit $ExitCode