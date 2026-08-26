#requires -Version 7.4
# =============================================================================
# E-ZZIO — LITELLM / CREDENTIAL ARCHITECTURE INSPECTION
# Version : 1.0.1
# Mode    : READ-ONLY / SECRET-SAFE / FORENSIC
# =============================================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# =============================================================================
# 0. CONFIGURATION
# =============================================================================

$Version = '1.0.1'
$ProjectRoot = 'G:\AI\E-zzio'

$ReportRoot = Join-Path `
    $ProjectRoot `
    '_forensic\reports'

$RunId = Get-Date -Format 'yyyyMMdd_HHmmss'

$ReportFile = Join-Path `
    $ReportRoot `
    "EZZIO_LiteLLM_Credential_Inspection_$RunId.txt"

$JsonReportFile = Join-Path `
    $ReportRoot `
    "EZZIO_LiteLLM_Credential_Inspection_$RunId.json"

# =============================================================================
# 1. BANNIÈRE
# =============================================================================

Clear-Host

Write-Host ''
Write-Host '============================================================================='
Write-Host ' E-ZZIO - LITELLM / CREDENTIAL ARCHITECTURE INSPECTION'
Write-Host " Version : $Version"
Write-Host ' Mode    : READ-ONLY / SECRET-SAFE / FORENSIC'
Write-Host '============================================================================='
Write-Host ''

# =============================================================================
# 2. VALIDATION DU PROJET
# =============================================================================

Write-Host '[1/9] Validation du projet'
Write-Host '-----------------------------------------------------------------------------'

if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) {
    Write-Host "[FAIL] Projet introuvable : $ProjectRoot"
    exit 10
}

Write-Host "[PASS] Projet trouve : $ProjectRoot"

# =============================================================================
# 3. DOSSIER DE RAPPORT
# =============================================================================

Write-Host ''
Write-Host '[2/9] Preparation du rapport'
Write-Host '-----------------------------------------------------------------------------'

New-Item `
    -ItemType Directory `
    -Force `
    -Path $ReportRoot |
    Out-Null

Write-Host "[PASS] Dossier rapport : $ReportRoot"

# =============================================================================
# 4. STRUCTURES DE SECURITE / CONFIGURATION
# =============================================================================

Write-Host ''
Write-Host '[3/9] Recherche des structures de securite et configuration'
Write-Host '-----------------------------------------------------------------------------'

$TargetPaths = @(
    'runtime\security',
    'runtime\secrets',
    'core\security',
    'core\secrets',
    'secrets',
    'config',
    '.archcore',
    '.traerules',
    '.agents',
    '.opencode'
)

$ExistingTargets = @()
$MissingTargets = @()

foreach ($RelativePath in $TargetPaths) {

    $FullPath = Join-Path `
        $ProjectRoot `
        $RelativePath

    if (Test-Path -LiteralPath $FullPath) {

        $ExistingTargets += [PSCustomObject]@{
            Path   = $RelativePath
            Status = 'EXISTS'
        }

        Write-Host "[PASS] $RelativePath"
    }
    else {

        $MissingTargets += [PSCustomObject]@{
            Path   = $RelativePath
            Status = 'MISSING'
        }

        Write-Host "[INFO] Absent : $RelativePath"
    }
}

# =============================================================================
# 5. INVENTAIRE DES FICHIERS
# =============================================================================

Write-Host ''
Write-Host '[4/9] Inventaire des fichiers pertinents'
Write-Host '-----------------------------------------------------------------------------'

$ExcludeDirectories = @(
    '.git',
    '.venv',
    '.venv_311_archive',
    '.venv_forensic_17Aug',
    'node_modules',
    '__pycache__',
    'site-packages',
    '_forensic\quarantine',
    '_forensic_backups'
)

$AllFiles = @()

try {

    $AllFiles = @(
        Get-ChildItem `
            -LiteralPath $ProjectRoot `
            -File `
            -Recurse `
            -ErrorAction SilentlyContinue |
        Where-Object {

            $FullName = $_.FullName
            $Excluded = $false

            foreach ($ExcludedDirectory in $ExcludeDirectories) {

                $ExcludedPath = Join-Path `
                    $ProjectRoot `
                    $ExcludedDirectory

                if (
                    $FullName.StartsWith(
                        $ExcludedPath,
                        [System.StringComparison]::OrdinalIgnoreCase
                    )
                ) {
                    $Excluded = $true
                    break
                }
            }

            -not $Excluded
        }
    )
}
catch {
    Write-Host "[WARN] Inventaire partiel : $($_.Exception.Message)"
}

Write-Host "[INFO] Fichiers disponibles pour inspection : $($AllFiles.Count)"

# =============================================================================
# 6. FILTRAGE DES FICHIERS INTERESSANTS
# =============================================================================

Write-Host ''
Write-Host '[5/9] Identification des fichiers securite / credentials / providers'
Write-Host '-----------------------------------------------------------------------------'

$InterestingNameRegex = '(?i)(secret|credential|credentials|vault|crypto|encrypt|decrypt|rotate|rotation|key|token|auth|litellm|openrouter|gemini|groq|config|settings|provider)'

$InterestingExtensions = @(
    '.py',
    '.toml',
    '.yaml',
    '.yml',
    '.json',
    '.md',
    '.ps1',
    '.psm1',
    '.ini',
    '.cfg',
    '.conf'
)

$SensitiveFileRegex = '(?i)(^|\\)(\.env|\.env\..*|.*\.secret|.*\.secrets|.*credentials.*|.*credential.*|.*private.*key.*)$'

$InterestingFiles = @(
    $AllFiles |
    Where-Object {

        $ExtensionAllowed =
            $InterestingExtensions -contains (
                $_.Extension.ToLowerInvariant()
            )

        $NameInteresting =
            $_.Name -match $InterestingNameRegex

        $ExtensionAllowed -and $NameInteresting
    } |
    Sort-Object FullName
)

Write-Host "[INFO] Fichiers candidats : $($InterestingFiles.Count)"

# =============================================================================
# 7. PATTERNS DE DETECTION
# =============================================================================

Write-Host ''
Write-Host '[6/9] Analyse des references'
Write-Host '-----------------------------------------------------------------------------'

$Patterns = [ordered]@{

    'LiteLLM' = @(
        'litellm',
        'LiteLLM',
        'litellm_proxy',
        'proxy_server',
        'proxy_server_config'
    )

    'OpenRouter' = @(
        'OPENROUTER_API_KEY',
        'openrouter',
        'OpenRouter'
    )

    'Gemini' = @(
        'GEMINI_API_KEY',
        'GOOGLE_API_KEY',
        'gemini',
        'Gemini'
    )

    'Groq' = @(
        'GROQ_API_KEY',
        'groq',
        'Groq'
    )

    'CredentialManagement' = @(
        'credential',
        'credentials',
        'secret',
        'secrets',
        'vault',
        'decrypt',
        'encrypt',
        'rotation',
        'rotate',
        'keyring',
        'CredentialManager'
    )

    'EnvironmentLoading' = @(
        'load_dotenv',
        'os.getenv',
        'os.environ',
        'dotenv',
        'Environment'
    )
}

$Findings = @()
$SourceFilesRead = 0
$SkippedSensitiveFiles = 0
$ReadErrors = 0

foreach ($File in $InterestingFiles) {

    # -------------------------------------------------------------------------
    # PROTECTION ABSOLUE DES FICHIERS DE SECRETS
    # -------------------------------------------------------------------------

    if (
        $File.Name -match '^\..*env' -or
        $File.Name -match '(?i)^\.env($|\.)' -or
        $File.Name -match '(?i)(secret|secrets|credentials|credential)'
    ) {

        $SkippedSensitiveFiles++

        continue
    }

    try {

        $Content = Get-Content `
            -LiteralPath $File.FullName `
            -Raw `
            -ErrorAction Stop

        $SourceFilesRead++

        foreach ($Category in $Patterns.Keys) {

            $CategoryMatched = $false

            foreach ($Pattern in $Patterns[$Category]) {

                if ($Content -match [regex]::Escape($Pattern)) {

                    $RelativePath = $File.FullName.Substring(
                        $ProjectRoot.Length
                    ).TrimStart('\')

                    $Findings += [PSCustomObject]@{
                        Category = $Category
                        File     = $RelativePath
                        Pattern  = $Pattern
                    }

                    $CategoryMatched = $true

                    break
                }
            }

            if ($CategoryMatched) {
                continue
            }
        }
    }
    catch {

        $ReadErrors++
    }
}

Write-Host "[INFO] Fichiers analyses       : $SourceFilesRead"
Write-Host "[INFO] Fichiers sensibles ignores : $SkippedSensitiveFiles"
Write-Host "[INFO] Erreurs de lecture     : $ReadErrors"
Write-Host "[INFO] Signaux detectes       : $($Findings.Count)"

# =============================================================================
# 8. SYNTHESE DES CATEGORIES
# =============================================================================

Write-Host ''
Write-Host '[7/9] Synthese des composants'
Write-Host '-----------------------------------------------------------------------------'

$Categories = @(
    'CredentialManagement',
    'EnvironmentLoading',
    'LiteLLM',
    'OpenRouter',
    'Gemini',
    'Groq'
)

$CategorySummary = @()

foreach ($Category in $Categories) {

    $Count = @(
        $Findings |
        Where-Object {
            $_.Category -eq $Category
        }
    ).Count

    $CategorySummary += [PSCustomObject]@{
        Category = $Category
        Findings = $Count
    }

    if ($Count -gt 0) {
        Write-Host "[PASS] $Category : $Count signal(s)"
    }
    else {
        Write-Host "[WARN] $Category : aucun signal detecte"
    }
}

# =============================================================================
# 9. VERDICT D'INTEGRATION
# =============================================================================

Write-Host ''
Write-Host '[8/9] Determination du point d integration LiteLLM'
Write-Host '-----------------------------------------------------------------------------'

$SecurityFindings = @(
    $Findings |
    Where-Object {
        $_.Category -eq 'CredentialManagement'
    }
)

$LiteLLMFindings = @(
    $Findings |
    Where-Object {
        $_.Category -eq 'LiteLLM'
    }
)

$ProviderFindings = @(
    $Findings |
    Where-Object {
        $_.Category -in @(
            'OpenRouter',
            'Gemini',
            'Groq'
        )
    }
)

$EnvironmentFindings = @(
    $Findings |
    Where-Object {
        $_.Category -eq 'EnvironmentLoading'
    }
)

$IntegrationVerdict = 'UNKNOWN'

if (
    $SecurityFindings.Count -gt 0 -and
    $ProviderFindings.Count -gt 0 -and
    $LiteLLMFindings.Count -eq 0
) {
    $IntegrationVerdict =
        'CREDENTIAL_LAYER_EXISTS_LITELLM_NOT_YET_BOUND'
}
elseif (
    $SecurityFindings.Count -gt 0 -and
    $ProviderFindings.Count -gt 0 -and
    $LiteLLMFindings.Count -gt 0
) {
    $IntegrationVerdict =
        'LITELLM_REFERENCES_EXIST_WITH_CREDENTIAL_LAYER'
}
elseif (
    $LiteLLMFindings.Count -gt 0
) {
    $IntegrationVerdict =
        'LITELLM_FOUND_CHECK_CREDENTIAL_BOUNDARY'
}
elseif (
    $ProviderFindings.Count -gt 0
) {
    $IntegrationVerdict =
        'PROVIDERS_FOUND_CREDENTIAL_ARCHITECTURE_UNCLEAR'
}

Write-Host "[INFO] Verdict : $IntegrationVerdict"

# =============================================================================
# 10. CONSTRUCTION DU RAPPORT TXT
# =============================================================================

Write-Host ''
Write-Host '[9/9] Generation du rapport forensic'
Write-Host '-----------------------------------------------------------------------------'

$Report = New-Object System.Collections.Generic.List[string]

$Report.Add('===============================================================================')
$Report.Add('E-ZZIO - LITELLM / CREDENTIAL ARCHITECTURE INSPECTION')
$Report.Add("Version : $Version")
$Report.Add("RunId   : $RunId")
$Report.Add('Mode    : READ-ONLY / SECRET-SAFE / NO NETWORK')
$Report.Add('===============================================================================')
$Report.Add('')

$Report.Add('PROJECT')
$Report.Add('-------')
$Report.Add("Root : $ProjectRoot")
$Report.Add('')

$Report.Add('SECURITY GUARANTEES')
$Report.Add('-------------------')
$Report.Add('No .env values read')
$Report.Add('No secret values displayed')
$Report.Add('No secrets decrypted')
$Report.Add('No API calls performed')
$Report.Add('No LiteLLM process launched')
$Report.Add('No project source files modified')
$Report.Add('')

$Report.Add('TARGET DIRECTORIES')
$Report.Add('------------------')

foreach ($Item in $ExistingTargets) {
    $Report.Add("[EXISTS] $($Item.Path)")
}

foreach ($Item in $MissingTargets) {
    $Report.Add("[MISSING] $($Item.Path)")
}

$Report.Add('')

$Report.Add('CATEGORY SUMMARY')
$Report.Add('----------------')

foreach ($Item in $CategorySummary) {

    $Report.Add(
        "{0,-28} : {1}" -f
        $Item.Category,
        $Item.Findings
    )
}

$Report.Add('')

$Report.Add('READ STATISTICS')
$Report.Add('---------------')
$Report.Add("Files discovered          : $($AllFiles.Count)")
$Report.Add("Interesting files         : $($InterestingFiles.Count)")
$Report.Add("Source files read         : $SourceFilesRead")
$Report.Add("Sensitive files skipped  : $SkippedSensitiveFiles")
$Report.Add("Read errors               : $ReadErrors")
$Report.Add('')

$Report.Add('INTEGRATION VERDICT')
$Report.Add('-------------------')
$Report.Add($IntegrationVerdict)
$Report.Add('')

$Report.Add('DETAILED FINDINGS')
$Report.Add('-----------------')

foreach (
    $Finding in (
        $Findings |
        Sort-Object Category, File
    )
) {

    $Report.Add(
        "[{0}] {1} -> {2}" -f
        $Finding.Category,
        $Finding.File,
        $Finding.Pattern
    )
}

$Report.Add('')

$Report.Add('RECOMMENDED TARGET ARCHITECTURE')
$Report.Add('-------------------------------')
$Report.Add('E-ZZIO Core')
$Report.Add('    -> Credential Resolver')
$Report.Add('    -> Provider Policy / Rotation')
$Report.Add('    -> LiteLLM Proxy')
$Report.Add('    -> OpenRouter / Gemini / Groq')
$Report.Add('')
$Report.Add('LiteLLM must NOT become the owner of the E-ZZIO credential vault.')
$Report.Add('E-ZZIO remains the authority for credential selection and policy.')
$Report.Add('LiteLLM acts as the model/provider routing layer.')
$Report.Add('')

$Report.Add('END OF REPORT')
$Report.Add('===============================================================================')

$ReportText = $Report -join [Environment]::NewLine

Set-Content `
    -LiteralPath $ReportFile `
    -Value $ReportText `
    -Encoding UTF8

# =============================================================================
# 11. RAPPORT JSON
# =============================================================================

$JsonObject = [PSCustomObject]@{
    Version            = $Version
    RunId              = $RunId
    ProjectRoot        = $ProjectRoot
    Mode               = 'READ_ONLY_SECRET_SAFE'
    SourceFilesRead    = $SourceFilesRead
    InterestingFiles   = $InterestingFiles.Count
    Findings           = $Findings.Count
    IntegrationVerdict = $IntegrationVerdict
    ExistingTargets    = $ExistingTargets
    MissingTargets     = $MissingTargets
    CategorySummary    = $CategorySummary
    DetailedFindings   = $Findings
}

$JsonObject |
    ConvertTo-Json -Depth 8 |
    Set-Content `
        -LiteralPath $JsonReportFile `
        -Encoding UTF8

# =============================================================================
# 12. VERIFICATION DES RAPPORTS
# =============================================================================

Write-Host ''
Write-Host '============================================================================='
Write-Host ' VERIFICATION FINALE'
Write-Host '============================================================================='

if (Test-Path -LiteralPath $ReportFile -PathType Leaf) {
    Write-Host "[PASS] Rapport TXT cree"
}
else {
    Write-Host "[FAIL] Rapport TXT absent"
}

if (Test-Path -LiteralPath $JsonReportFile -PathType Leaf) {
    Write-Host "[PASS] Rapport JSON cree"
}
else {
    Write-Host "[FAIL] Rapport JSON absent"
}

Write-Host ''
Write-Host "[INFO] Fichiers analyses      : $SourceFilesRead"
Write-Host "[INFO] Secrets ignores        : $SkippedSensitiveFiles"
Write-Host "[INFO] Signaux detectes      : $($Findings.Count)"
Write-Host "[INFO] Verdict                : $IntegrationVerdict"
Write-Host ''

Write-Host '[INFO] Rapport TXT :'
Write-Host "       $ReportFile"

Write-Host ''
Write-Host '[INFO] Rapport JSON :'
Write-Host "       $JsonReportFile"

Write-Host ''
Write-Host '============================================================================='
Write-Host ' INSPECTION TERMINEE - AUCUNE MODIFICATION DU PROJET'
Write-Host '============================================================================='
Write-Host ''
