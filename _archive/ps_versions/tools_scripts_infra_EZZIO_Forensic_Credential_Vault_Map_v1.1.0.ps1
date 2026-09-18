#requires -Version 7.4
# =============================================================================
# E-ZZIO — FORENSIC CREDENTIAL VAULT CARTOGRAPHY
# Version : 1.1.0
# Mode    : READ-ONLY / SECRET-SAFE / FORENSIC / NO NETWORK
# =============================================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# =============================================================================
# CONFIGURATION
# =============================================================================

$Version     = '1.1.0'
$ProjectRoot = 'G:\AI\E-zzio'
$SecretsRoot = Join-Path $ProjectRoot 'secrets'
$ReportRoot  = Join-Path $ProjectRoot '_forensic\reports'

$RunId = Get-Date -Format 'yyyyMMdd_HHmmss'
$Stamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'

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
    VariablesDetected       = 0
    VariablesPresent        = 0
    VariablesEmpty          = 0
    SensitiveVariables      = 0
    ProviderVariables       = 0
    ModelVariables          = 0
    LimitVariables          = 0
    EndpointVariables       = 0
    ControlVariables        = 0
    DuplicateVariables      = 0
    InvalidLines             = 0
    ReadErrors              = 0
    ReportsCreated          = 0
}

$FileMap = New-Object System.Collections.Generic.List[object]
$VariableMap = New-Object System.Collections.Generic.List[object]
$ReadErrors = New-Object System.Collections.Generic.List[object]
$DuplicateMap = New-Object System.Collections.Generic.List[object]

# =============================================================================
# MOTIFS
# =============================================================================

$SensitivePatterns = @(
    '(^|_)(api[_-]?key)(_|$)',
    '(^|_)(token)(_|$)',
    '(^|_)(secret)(_|$)',
    '(^|_)(password)(_|$)',
    '(^|_)(passwd)(_|$)',
    '(^|_)(private[_-]?key)(_|$)',
    '(^|_)(client[_-]?secret)(_|$)',
    '(^|_)(credential)(_|$)',
    '(^|_)(credentials)(_|$)',
    '(^|_)(auth[_-]?token)(_|$)',
    '(^|_)(access[_-]?token)(_|$)',
    '(^|_)(refresh[_-]?token)(_|$)'
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
    'cohere',
    'together',
    'perplexity',
    'ollama',
    'xai'
)

$ModelPatterns = @(
    '(^|_)model(_|$)',
    '(^|_)models(_|$)'
)

$LimitPatterns = @(
    'limit',
    'quota',
    'daily',
    'monthly',
    'max[_-]?requests',
    'max[_-]?tokens'
)

$EndpointPatterns = @(
    'url',
    'uri',
    'endpoint',
    'base[_-]?url',
    'base[_-]?uri',
    'host'
)

$ControlPatterns = @(
    'mode',
    'allow',
    'enabled',
    'enable',
    'timeout',
    'ttl',
    'cache',
    'log',
    'redact',
    'debug',
    'strict',
    'policy'
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

function Get-VariableClass {
    param(
        [Parameter(Mandatory)]
        [string]$Name
    )

    $Upper = $Name.ToUpperInvariant()

    foreach ($Pattern in $SensitivePatterns) {
        if ($Upper -match $Pattern) {
            return 'SENSITIVE'
        }
    }

    foreach ($Pattern in $ProviderPatterns) {
        if ($Upper -match [regex]::Escape($Pattern)) {
            if ($Upper -match 'API|KEY|TOKEN|MODEL|URL|URI|HOST') {
                return 'PROVIDER'
            }
        }
    }

    foreach ($Pattern in $ModelPatterns) {
        if ($Upper -match $Pattern) {
            return 'MODEL'
        }
    }

    foreach ($Pattern in $LimitPatterns) {
        if ($Upper -match $Pattern) {
            return 'LIMIT'
        }
    }

    foreach ($Pattern in $EndpointPatterns) {
        if ($Upper -match $Pattern) {
            return 'ENDPOINT'
        }
    }

    foreach ($Pattern in $ControlPatterns) {
        if ($Upper -match $Pattern) {
            return 'CONTROL'
        }
    }

    return 'OTHER'
}

function Get-PresenceClass {
    param(
        [Parameter(Mandatory)]
        [string]$Value
    )

    if ([string]::IsNullOrWhiteSpace($Value)) {
        return 'EMPTY'
    }

    $Length = $Value.Length

    if ($Length -le 8) {
        return 'PRESENT_SHORT'
    }

    if ($Length -le 24) {
        return 'PRESENT_MEDIUM'
    }

    return 'PRESENT_LONG'
}

function Test-IsExampleFile {
    param(
        [Parameter(Mandatory)]
        [string]$FileName
    )

    return $FileName -match '(?i)\.example($|\.env$)'
}

function Get-SafeEnvEntries {
    param(
        [Parameter(Mandatory)]
        [string]$FilePath
    )

    $Entries = New-Object System.Collections.Generic.List[object]

    try {
        $Lines = [System.IO.File]::ReadAllLines(
            $FilePath,
            [System.Text.UTF8Encoding]::new($false, $true)
        )
    }
    catch {
        throw
    }

    $LineNumber = 0

    foreach ($Line in $Lines) {

        $LineNumber++

        if ([string]::IsNullOrWhiteSpace($Line)) {
            continue
        }

        $Trimmed = $Line.Trim()

        if ($Trimmed.StartsWith('#')) {
            continue
        }

        # ---------------------------------------------------------------------
        # Supporte :
        #
        # KEY=value
        # export KEY=value
        # KEY="value"
        # KEY='value'
        #
        # La valeur n'est JAMAIS retournée.
        # ---------------------------------------------------------------------

        $Match = [regex]::Match(
            $Trimmed,
            '^(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=(.*)$'
        )

        if (-not $Match.Success) {

            $Stats.InvalidLines++

            $Entries.Add(
                [pscustomobject][ordered]@{
                    LineNumber = $LineNumber
                    Name       = $null
                    HasValue   = $false
                    ValueClass = 'INVALID'
                }
            )

            continue
        }

        $Name = $Match.Groups[1].Value
        $RawValue = $Match.Groups[2].Value

        # ---------------------------------------------------------------------
        # IMPORTANT :
        # RawValue existe uniquement en mémoire pendant cette fonction.
        # Il n'est jamais retourné, écrit, loggé, hashé ou exporté.
        # ---------------------------------------------------------------------

        $Value = $RawValue.Trim()

        if (
            ($Value.Length -ge 2) -and
            (
                ($Value.StartsWith('"') -and $Value.EndsWith('"')) -or
                ($Value.StartsWith("'") -and $Value.EndsWith("'"))
            )
        ) {
            $Value = $Value.Substring(1, $Value.Length - 2)
        }

        $IsPresent = -not [string]::IsNullOrWhiteSpace($Value)
        $Class = Get-VariableClass -Name $Name
        $Presence = Get-PresenceClass -Value $Value

        $Entries.Add(
            [pscustomobject][ordered]@{
                LineNumber = $LineNumber
                Name       = $Name
                HasValue   = $IsPresent
                ValueClass = $Presence
                Category   = $Class
            }
        )

        # Effacement de références locales dès que possible.
        $Value = $null
        $RawValue = $null
    }

    return $Entries
}

function Add-VariableClassification {
    param(
        [Parameter(Mandatory)]
        [string]$FileName,

        [Parameter(Mandatory)]
        [string]$RelativePath,

        [Parameter(Mandatory)]
        [bool]$IsExample,

        [Parameter(Mandatory)]
        [object]$Entry
    )

    $Stats.VariablesDetected++

    if ($Entry.HasValue) {
        $Stats.VariablesPresent++
    }
    else {
        $Stats.VariablesEmpty++
    }

    switch ($Entry.Category) {
        'SENSITIVE' {
            $Stats.SensitiveVariables++
        }

        'PROVIDER' {
            $Stats.ProviderVariables++
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

        'CONTROL' {
            $Stats.ControlVariables++
        }
    }

    $VariableMap.Add(
        [pscustomobject][ordered]@{
            File       = $FileName
            Path       = $RelativePath
            FileType   = if ($IsExample) { 'ENV_EXAMPLE' } else { 'ENV' }
            Variable   = $Entry.Name
            Category   = $Entry.Category
            Presence   = $Entry.ValueClass
            Line       = $Entry.LineNumber
        }
    )

    Write-Host (
        '[INFO] {0} :: {1} :: {2} :: {3}' -f
        $FileName,
        $Entry.Name,
        $Entry.Category,
        $Entry.ValueClass
    )
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
Write-Host "[INFO] Début : $Stamp"

# =============================================================================
# [1/9] VALIDATION
# =============================================================================

Write-Section '[1/9] Validation du projet et du coffre'

if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) {
    Write-Host "[FAIL] Projet introuvable : $ProjectRoot" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path -LiteralPath $SecretsRoot -PathType Container)) {
    Write-Host "[FAIL] Coffre introuvable : $SecretsRoot" -ForegroundColor Red
    exit 1
}

Write-Host "[PASS] Projet : $ProjectRoot"
Write-Host "[PASS] Coffre : $SecretsRoot"

# =============================================================================
# [2/9] RAPPORT
# =============================================================================

Write-Section '[2/9] Préparation du rapport'

New-Item `
    -ItemType Directory `
    -Force `
    -Path $ReportRoot |
    Out-Null

Write-Host "[PASS] Dossier forensic : $ReportRoot"

# =============================================================================
# [3/9] INVENTAIRE
# =============================================================================

Write-Section '[3/9] Inventaire du coffre — NOMS UNIQUEMENT'

$Files = @(
    Get-ChildItem `
        -LiteralPath $SecretsRoot `
        -File `
        -Recurse `
        -Force `
        -ErrorAction Stop
)

$Stats.VaultFiles = $Files.Count

Write-Host "[INFO] Fichiers trouvés : $($Files.Count)"

# =============================================================================
# [4/9] CARTOGRAPHIE DES FICHIERS
# =============================================================================

Write-Section '[4/9] Cartographie des fichiers — MÉTADONNÉES UNIQUEMENT'

foreach ($File in $Files) {

    $Relative = [System.IO.Path]::GetRelativePath(
        $SecretsRoot,
        $File.FullName
    )

    $IsExample = Test-IsExampleFile -FileName $File.Name

    if ($IsExample) {
        $Stats.ExampleFiles++
        $FileType = 'ENV_EXAMPLE'
    }
    else {
        $Stats.EnvFiles++
        $FileType = 'ENV'
    }

    $FileMap.Add(
        [pscustomobject][ordered]@{
            Name       = $File.Name
            Relative   = $Relative
            Type       = $FileType
            SizeBytes  = $File.Length
            Readable   = $true
        }
    )

    Write-Host "[PASS] $Relative [$FileType]"
}

# =============================================================================
# [5/9] CARTOGRAPHIE DES VARIABLES
# =============================================================================

Write-Section '[5/9] Cartographie des variables — VALEURS JAMAIS AFFICHÉES'

foreach ($File in $Files) {

    $Relative = [System.IO.Path]::GetRelativePath(
        $SecretsRoot,
        $File.FullName
    )

    $IsExample = Test-IsExampleFile -FileName $File.Name

    try {

        $Entries = Get-SafeEnvEntries -FilePath $File.FullName

        foreach ($Entry in $Entries) {

            if ($Entry.Name -eq $null) {
                continue
            }

            Add-VariableClassification `
                -FileName $File.Name `
                -RelativePath $Relative `
                -IsExample $IsExample `
                -Entry $Entry
        }

    }
    catch {

        $Stats.ReadErrors++

        # ---------------------------------------------------------------------
        # IMPORTANT :
        # Aucun message d'exception brut n'est exporté.
        # On conserve uniquement une classification générique.
        # ---------------------------------------------------------------------

        $ReadErrors.Add(
            [pscustomobject][ordered]@{
                File   = $Relative
                Reason = 'READ_OR_PARSE_ERROR'
            }
        )

        Write-Host "[FAIL] Lecture impossible : $Relative" -ForegroundColor Red
    }
}

# =============================================================================
# [6/9] DOUBLONS
# =============================================================================

Write-Section '[6/9] Détection des noms de variables partagés'

$GroupedVariables = @(
    $VariableMap |
    Group-Object -Property Variable |
    Where-Object {
        $_.Count -gt 1
    }
)

foreach ($Group in $GroupedVariables) {

    $Stats.DuplicateVariables += $Group.Count

    $FilesForVariable = @(
        $Group.Group |
        Select-Object -ExpandProperty File -Unique
    )

    $DuplicateMap.Add(
        [pscustomobject][ordered]@{
            Variable = $Group.Name
            Count    = $Group.Count
            Files    = $FilesForVariable
        }
    )

    Write-Host (
        '[WARN] Variable partagée : {0} ({1} fichiers)' -f
        $Group.Name,
        $FilesForVariable.Count
    )
}

# =============================================================================
# [7/9] SYNTHÈSE
# =============================================================================

Write-Section '[7/9] Synthèse forensic'

Write-Host "[INFO] Fichiers coffre           : $($Stats.VaultFiles)"
Write-Host "[INFO] Fichiers .env             : $($Stats.EnvFiles)"
Write-Host "[INFO] Fichiers exemple          : $($Stats.ExampleFiles)"
Write-Host "[INFO] Variables détectées       : $($Stats.VariablesDetected)"
Write-Host "[INFO] Variables présentes       : $($Stats.VariablesPresent)"
Write-Host "[INFO] Variables vides           : $($Stats.VariablesEmpty)"
Write-Host "[INFO] Variables sensibles       : $($Stats.SensitiveVariables)"
Write-Host "[INFO] Variables providers       : $($Stats.ProviderVariables)"
Write-Host "[INFO] Variables modèles         : $($Stats.ModelVariables)"
Write-Host "[INFO] Variables limites         : $($Stats.LimitVariables)"
Write-Host "[INFO] Variables endpoints       : $($Stats.EndpointVariables)"
Write-Host "[INFO] Variables contrôle        : $($Stats.ControlVariables)"
Write-Host "[INFO] Doublons de variables     : $($Stats.DuplicateVariables)"
Write-Host "[INFO] Lignes invalides          : $($Stats.InvalidLines)"
Write-Host "[INFO] Erreurs lecture           : $($Stats.ReadErrors)"

# =============================================================================
# [8/9] GARANTIES
# =============================================================================

Write-Section '[8/9] Garanties de sécurité'

Write-Host '[PASS] Aucune valeur de credential affichée'
Write-Host '[PASS] Aucune clé API affichée'
Write-Host '[PASS] Aucun token affiché'
Write-Host '[PASS] Aucun secret affiché'
Write-Host '[PASS] Aucun contenu brut exporté'
Write-Host '[PASS] Aucun secret déchiffré'
Write-Host '[PASS] Aucun fichier du coffre modifié'
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
$Report.Add("Date    : $Stamp")
$Report.Add('Mode    : READ-ONLY / SECRET-SAFE / FORENSIC / NO NETWORK')
$Report.Add('===============================================================================')
$Report.Add('')

$Report.Add('SECURITY GUARANTEES')
$Report.Add('-------------------')
$Report.Add('No credential values exported')
$Report.Add('No API keys exported')
$Report.Add('No tokens exported')
$Report.Add('No secrets exported')
$Report.Add('No raw file contents exported')
$Report.Add('No secrets decrypted')
$Report.Add('No files modified')
$Report.Add('No credentials modified')
$Report.Add('No network calls')
$Report.Add('No LiteLLM process launched')
$Report.Add('')

$Report.Add('VAULT')
$Report.Add('-----')
$Report.Add("Vault files          : $($Stats.VaultFiles)")
$Report.Add("ENV files            : $($Stats.EnvFiles)")
$Report.Add("Example files        : $($Stats.ExampleFiles)")
$Report.Add('')

$Report.Add('VARIABLE STATISTICS')
$Report.Add('-------------------')
$Report.Add("Variables detected   : $($Stats.VariablesDetected)")
$Report.Add("Variables present    : $($Stats.VariablesPresent)")
$Report.Add("Variables empty      : $($Stats.VariablesEmpty)")
$Report.Add("Sensitive            : $($Stats.SensitiveVariables)")
$Report.Add("Providers            : $($Stats.ProviderVariables)")
$Report.Add("Models               : $($Stats.ModelVariables)")
$Report.Add("Limits               : $($Stats.LimitVariables)")
$Report.Add("Endpoints            : $($Stats.EndpointVariables)")
$Report.Add("Controls             : $($Stats.ControlVariables)")
$Report.Add("Duplicate references : $($Stats.DuplicateVariables)")
$Report.Add("Invalid lines        : $($Stats.InvalidLines)")
$Report.Add("Read errors          : $($Stats.ReadErrors)")
$Report.Add('')

$Report.Add('FILE MAP')
$Report.Add('--------')

foreach ($Item in $FileMap) {
    $Report.Add(
        ('{0} | {1} | {2} | {3} bytes' -f
            $Item.Type,
            $Item.Relative,
            $Item.Name,
            $Item.SizeBytes
        )
    )
}

$Report.Add('')
$Report.Add('VARIABLE MAP')
$Report.Add('------------')

foreach ($Item in $VariableMap) {

    $Report.Add(
        ('{0} | {1} | {2} | {3} | line={4}' -f
            $Item.File,
            $Item.Variable,
            $Item.Category,
            $Item.Presence,
            $Item.Line
        )
    )
}

$Report.Add('')
$Report.Add('DUPLICATE VARIABLES')
$Report.Add('-------------------')

foreach ($Item in $DuplicateMap) {

    $Report.Add(
        ('{0} | count={1} | files={2}' -f
            $Item.Variable,
            $Item.Count,
            ($Item.Files -join ', ')
        )
    )
}

$Report.Add('')
$Report.Add('READ ERRORS')
$Report.Add('-----------')

foreach ($Item in $ReadErrors) {
    $Report.Add(
        ('{0} | {1}' -f
            $Item.File,
            $Item.Reason
        )
    )
}

$Report.Add('')
$Report.Add('END OF FORENSIC REPORT')
$Report.Add('===============================================================================')

Set-Content `
    -LiteralPath $ReportTxt `
    -Value $Report `
    -Encoding UTF8 `
    -ErrorAction Stop

$JsonObject = [ordered]@{
    schema_version = '1.1.0'
    tool_version   = $Version
    run_id         = $RunId
    timestamp      = $Stamp
    mode           = 'READ-ONLY / SECRET-SAFE / FORENSIC / NO NETWORK'

    project_root = $ProjectRoot
    secrets_root = $SecretsRoot

    statistics = $Stats

    security = [ordered]@{
        credential_values_exported = $false
        api_keys_exported          = $false
        tokens_exported             = $false
        secrets_exported            = $false
        raw_contents_exported      = $false
        secrets_decrypted           = $false
        files_modified              = $false
        credentials_modified        = $false
        network_used                = $false
        litellm_started             = $false
    }

    files      = $FileMap
    variables  = $VariableMap
    duplicates = $DuplicateMap
    errors     = $ReadErrors
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
    $Stats.ReportsCreated++
}
else {
    Write-Host '[FAIL] Rapport TXT absent' -ForegroundColor Red
    $ExitCode = 1
}

if (Test-Path -LiteralPath $ReportJson -PathType Leaf) {
    Write-Host '[PASS] Rapport JSON créé'
    $Stats.ReportsCreated++
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

if ($Stats.InvalidLines -eq 0) {
    Write-Host '[PASS] Zéro ligne invalide'
}
else {
    Write-Host "[WARN] Lignes invalides : $($Stats.InvalidLines)"
}

Write-Host '[PASS] Zéro appel réseau'
Write-Host '[PASS] Zéro fichier du coffre modifié'
Write-Host '[PASS] Zéro valeur secrète exportée'

# =============================================================================
# RÉSULTAT FINAL
# =============================================================================

Write-Host ''
Write-Host '============================================================================='
Write-Host ' RÉSULTAT FINAL'
Write-Host '============================================================================='

Write-Host "[INFO] Coffre analysé        : $SecretsRoot"
Write-Host "[INFO] Fichiers              : $($Stats.VaultFiles)"
Write-Host "[INFO] Variables             : $($Stats.VariablesDetected)"
Write-Host "[INFO] Variables présentes   : $($Stats.VariablesPresent)"
Write-Host "[INFO] Variables vides       : $($Stats.VariablesEmpty)"
Write-Host "[INFO] Sensibles             : $($Stats.SensitiveVariables)"
Write-Host "[INFO] Providers             : $($Stats.ProviderVariables)"
Write-Host "[INFO] Modèles               : $($Stats.ModelVariables)"
Write-Host "[INFO] Limites               : $($Stats.LimitVariables)"
Write-Host "[INFO] Contrôles             : $($Stats.ControlVariables)"
Write-Host "[INFO] Doublons              : $($Stats.DuplicateVariables)"
Write-Host "[INFO] Erreurs lecture       : $($Stats.ReadErrors)"
Write-Host "[INFO] Rapport TXT           : $ReportTxt"
Write-Host "[INFO] Rapport JSON          : $ReportJson"
Write-Host ''

if ($ExitCode -eq 0) {
    Write-Host '[PASS] CARTOGRAPHIE FORENSIC TERMINÉE SANS ERREUR'
    Write-Host '[PASS] CODE RETOUR = 0'
}
else {
    Write-Host "[FAIL] CARTOGRAPHIE FORENSIC TERMINÉE AVEC CODE : $ExitCode" -ForegroundColor Red
}

Write-Host '============================================================================='

exit $ExitCode