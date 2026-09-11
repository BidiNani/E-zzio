# ============================================================================
# E-ZZIO — VALIDATION FORENSIC STATIQUE v1.1.4
# ============================================================================
# MODE       : READ-ONLY / FAIL-CLOSED / FORENSIC
# CIBLE      : EZZIO_Freeze_Certification_v1.1.1.ps1
#
# OBJECTIFS :
#   - La cible n'est jamais exécutée.
#   - La cible n'est jamais modifiée.
#   - La cible est verrouillée en lecture pendant l'analyse.
#   - AST PowerShell réel.
#   - SHA-256 réel.
#   - Lecture UTF-8 stricte.
#   - Analyse statique des constructions sensibles.
#   - Vérification d'intégrité AVANT / APRÈS analyse.
#   - Rapport TXT + JSON.
#   - Gestion FAIL-CLOSED des erreurs internes du validateur.
#   - Aucun formatage "-f" fragile pour les rapports.
#
# EXIT CODES :
#   0  = FORENSIC_PASS
#   10 = FORENSIC_FAIL
#   20 = FORENSIC_REVIEW_REQUIRED
#
# IMPORTANT :
#   Une exception interne du validateur n'est PAS considérée comme un
#   "code inconnu". Elle devient explicitement FORENSIC_FAIL.
# ============================================================================

& {

    Set-StrictMode -Version Latest
    $ErrorActionPreference = 'Stop'

    # =========================================================================
    # CONFIGURATION
    # =========================================================================

    $ProjectRoot = 'G:\AI\E-zzio'

    $Target = Join-Path `
        $ProjectRoot `
        'EZZIO_Freeze_Certification_v1.1.1.ps1'

    $ReportDirectory = Join-Path `
        $ProjectRoot `
        'forensic_validation'

    $Timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'

    $ReportTxt = Join-Path `
        $ReportDirectory `
        "EZZIO_Freeze_Certification_v1.1.1_FORENSIC_$Timestamp.txt"

    $ReportJson = Join-Path `
        $ReportDirectory `
        "EZZIO_Freeze_Certification_v1.1.1_FORENSIC_$Timestamp.json"

    # =========================================================================
    # STATE
    # =========================================================================

    $Results = [System.Collections.Generic.List[object]]::new()

    $StartedAt = Get-Date
    $EndedAt = $null

    $FileInfo = $null
    $Sha256Before = $null
    $Sha256After = $null
    $TargetLengthBefore = $null
    $TargetLengthAfter = $null

    $Content = $null
    $Lines = @()

    $Tokens = $null
    $AstErrors = $null
    $Ast = $null

    $CommandNodes = @()
    $FunctionNodes = @()
    $ThrowNodes = @()
    $TryNodes = @()
    $IfNodes = @()

    $AstErrorArray = @()

    $PassCount = 0
    $WarnCount = 0
    $FailCount = 0
    $InfoCount = 0

    $Verdict = 'FORENSIC_FAIL'
    $ExitCode = 10
    $VerdictColor = 'Red'

    $InternalFailure = $false
    $InternalFailureMessage = $null
    $InternalFailureType = $null
    $InternalFailureLine = $null

    $TargetReadHandle = $null

    # =========================================================================
    # RESULT FUNCTION
    # =========================================================================

    function Add-Result {

        param(
            [Parameter(Mandatory)]
            [string]$Category,

            [Parameter(Mandatory)]
            [string]$Name,

            [Parameter(Mandatory)]
            [ValidateSet('PASS','WARN','FAIL','INFO')]
            [string]$Status,

            [Parameter(Mandatory)]
            [string]$Details,

            [int]$Count = 0
        )

        $Results.Add(
            [pscustomobject]@{
                Category = $Category
                Name     = $Name
                Status   = $Status
                Count    = $Count
                Details  = $Details
            }
        )
    }

    # =========================================================================
    # SAFE PATTERN SCANNER
    # =========================================================================

    function Test-Pattern {

        param(
            [Parameter(Mandatory)]
            [string]$Name,

            [Parameter(Mandatory)]
            [string]$Pattern,

            [Parameter(Mandatory)]
            [string]$Category,

            [Parameter(Mandatory)]
            [ValidateSet('PASS','WARN','FAIL')]
            [string]$StatusWhenFound,

            [Parameter(Mandatory)]
            [string]$FoundDescription
        )

        $MatchesFound = @(
            Select-String `
                -LiteralPath $Target `
                -Pattern $Pattern `
                -CaseSensitive:$false `
                -AllMatches `
                -ErrorAction Stop
        )

        if ($MatchesFound.Count -eq 0) {

            Add-Result `
                -Category $Category `
                -Name $Name `
                -Status 'PASS' `
                -Count 0 `
                -Details 'Aucune occurrence détectée.'

            return
        }

        $Locations = [System.Collections.Generic.List[object]]::new()

        foreach ($Match in $MatchesFound) {

            foreach ($M in $Match.Matches) {

                $Locations.Add(
                    [pscustomobject]@{
                        Line   = $Match.LineNumber
                        Column = $M.Index + 1
                        Text   = $Match.Line.Trim()
                    }
                )
            }
        }

        $PreviewItems = @(
            $Locations |
            Select-Object -First 20 |
            ForEach-Object {
                'L' + $_.Line +
                ':C' + $_.Column +
                ' -> ' +
                $_.Text
            }
        )

        $Preview = $PreviewItems -join ' | '

        if ($Locations.Count -gt 20) {
            $Preview += ' | ...'
        }

        Add-Result `
            -Category $Category `
            -Name $Name `
            -Status $StatusWhenFound `
            -Count $Locations.Count `
            -Details ($FoundDescription + ' ' + $Preview)
    }

    # =========================================================================
    # SAFE TARGET HASH
    # =========================================================================

    function Get-TargetSha256 {

        return (
            Get-FileHash `
                -LiteralPath $Target `
                -Algorithm SHA256 `
                -ErrorAction Stop
        ).Hash
    }

    # =========================================================================
    # TARGET READ HANDLE
    #
    # FileShare.Read :
    #   - autorise les lectures concurrentes ;
    #   - interdit les ouvertures concurrentes demandant Write/Delete ;
    #   - protège donc la cible contre une mutation concurrente pendant
    #     l'analyse.
    # =========================================================================

    function Open-TargetReadLock {

        $Stream = [System.IO.FileStream]::new(
            $Target,
            [System.IO.FileMode]::Open,
            [System.IO.FileAccess]::Read,
            [System.IO.FileShare]::Read
        )

        return $Stream
    }

    # =========================================================================
    # STRICT UTF-8 READ
    # =========================================================================

    function Read-TargetUtf8 {

        $Encoding = [System.Text.UTF8Encoding]::new(
            $false,
            $true
        )

        $Bytes = [System.IO.File]::ReadAllBytes($Target)

        return $Encoding.GetString($Bytes)
    }

    # =========================================================================
    # START
    # =========================================================================

    Write-Host ''
    Write-Host '============================================================' -ForegroundColor Cyan
    Write-Host ' E-ZZIO — VALIDATION FORENSIC STATIQUE v1.1.4' -ForegroundColor Cyan
    Write-Host '============================================================' -ForegroundColor Cyan
    Write-Host ''

    Write-Host ('Projet : ' + $ProjectRoot)
    Write-Host ('Cible  : ' + $Target)
    Write-Host ''

    Write-Host `
        'MODE : READ-ONLY / NO TARGET EXECUTION / FAIL-CLOSED' `
        -ForegroundColor Yellow

    Write-Host ''
    Write-Host '[INFO] Démarrage du forensic.' -ForegroundColor Cyan
    Write-Host '[INFO] La cible sera verrouillée en lecture pendant l'analyse.' -ForegroundColor Cyan
    Write-Host ''

    try {

        # =====================================================================
        # 1 — PROJECT
        # =====================================================================

        if (-not (
            Test-Path `
                -LiteralPath $ProjectRoot `
                -PathType Container
        )) {

            throw `
                "FAIL-CLOSED : projet introuvable : $ProjectRoot"
        }

        Add-Result `
            -Category 'ENVIRONMENT' `
            -Name 'PROJECT_ROOT' `
            -Status 'PASS' `
            -Count 1 `
            -Details ('Répertoire projet accessible : ' + $ProjectRoot)

        # =====================================================================
        # 2 — TARGET
        # =====================================================================

        if (-not (
            Test-Path `
                -LiteralPath $Target `
                -PathType Leaf
        )) {

            throw `
                "FAIL-CLOSED : cible introuvable : $Target"
        }

        $FileInfo = Get-Item `
            -LiteralPath $Target `
            -Force `
            -ErrorAction Stop

        if ($FileInfo.Length -eq 0) {

            Add-Result `
                -Category 'TARGET' `
                -Name 'EMPTY_FILE' `
                -Status 'FAIL' `
                -Count 1 `
                -Details 'Le fichier cible est vide.'

            throw `
                'FAIL-CLOSED : fichier cible vide.'
        }

        $TargetLengthBefore = $FileInfo.Length

        Add-Result `
            -Category 'TARGET' `
            -Name 'TARGET_EXISTS' `
            -Status 'PASS' `
            -Count 1 `
            -Details ('Fichier trouvé : ' + $FileInfo.FullName)

        Add-Result `
            -Category 'TARGET' `
            -Name 'TARGET_SIZE' `
            -Status 'PASS' `
            -Count 1 `
            -Details ('Taille physique : ' + $FileInfo.Length + ' octets')

        # =====================================================================
        # 3 — TARGET READ LOCK
        # =====================================================================

        $TargetReadHandle = Open-TargetReadLock

        if ($null -eq $TargetReadHandle) {

            throw `
                'FAIL-CLOSED : impossible d''obtenir le handle de lecture cible.'
        }

        Add-Result `
            -Category 'SAFETY' `
            -Name 'TARGET_READ_LOCK' `
            -Status 'PASS' `
            -Count 1 `
            -Details 'Handle FileStream ouvert en FileAccess.Read / FileShare.Read.'

        # =====================================================================
        # 4 — SHA-256 BEFORE
        # =====================================================================

        $Sha256Before = Get-TargetSha256

        if ([string]::IsNullOrWhiteSpace($Sha256Before)) {

            throw `
                'FAIL-CLOSED : SHA-256 cible vide ou invalide.'
        }

        Add-Result `
            -Category 'INTEGRITY' `
            -Name 'SHA256_BEFORE' `
            -Status 'PASS' `
            -Count 1 `
            -Details $Sha256Before

        # =====================================================================
        # 5 — CONTENT READ
        # =====================================================================

        $Content = Read-TargetUtf8

        if ([string]::IsNullOrWhiteSpace($Content)) {

            Add-Result `
                -Category 'TARGET' `
                -Name 'CONTENT_READ' `
                -Status 'FAIL' `
                -Count 1 `
                -Details 'Le contenu UTF-8 lu est vide.'

            throw `
                'FAIL-CLOSED : contenu cible vide.'
        }

        $Lines = @(
            $Content -split "`r?`n"
        )

        Add-Result `
            -Category 'TARGET' `
            -Name 'CONTENT_READ' `
            -Status 'PASS' `
            -Count $Lines.Count `
            -Details ('Lecture UTF-8 stricte réussie : ' + $Lines.Count + ' lignes logiques.')

        # =====================================================================
        # 6 — AST PARSER
        # =====================================================================

        $Tokens = $null
        $AstErrors = $null

        $Ast = [System.Management.Automation.Language.Parser]::ParseFile(
            $Target,
            [ref]$Tokens,
            [ref]$AstErrors
        )

        $AstErrorArray = @($AstErrors)

        if ($AstErrorArray.Count -eq 0) {

            Add-Result `
                -Category 'AST' `
                -Name 'SYNTAX' `
                -Status 'PASS' `
                -Count 0 `
                -Details 'AST PowerShell : 0 erreur.'
        }
        else {

            foreach ($AstError in $AstErrorArray) {

                Write-Host (
                    '[AST FAIL] Ligne ' +
                    $AstError.Extent.StartLineNumber +
                    ', colonne ' +
                    $AstError.Extent.StartColumnNumber +
                    ' : ' +
                    $AstError.Message
                ) -ForegroundColor Red
            }

            Add-Result `
                -Category 'AST' `
                -Name 'SYNTAX' `
                -Status 'FAIL' `
                -Count $AstErrorArray.Count `
                -Details 'Erreur(s) AST détectée(s).'
        }

        # =====================================================================
        # 7 — AST STRUCTURE
        # =====================================================================

        $CommandNodes = @(
            $Ast.FindAll(
                {
                    param($Node)

                    $Node -is `
                        [System.Management.Automation.Language.CommandAst]
                },
                $true
            )
        )

        $FunctionNodes = @(
            $Ast.FindAll(
                {
                    param($Node)

                    $Node -is `
                        [System.Management.Automation.Language.FunctionDefinitionAst]
                },
                $true
            )
        )

        $ThrowNodes = @(
            $Ast.FindAll(
                {
                    param($Node)

                    $Node -is `
                        [System.Management.Automation.Language.ThrowStatementAst]
                },
                $true
            )
        )

        $TryNodes = @(
            $Ast.FindAll(
                {
                    param($Node)

                    $Node -is `
                        [System.Management.Automation.Language.TryStatementAst]
                },
                $true
            )
        )

        $IfNodes = @(
            $Ast.FindAll(
                {
                    param($Node)

                    $Node -is `
                        [System.Management.Automation.Language.IfStatementAst]
                },
                $true
            )
        )

        Add-Result `
            -Category 'STRUCTURE' `
            -Name 'COMMANDS' `
            -Status 'INFO' `
            -Count $CommandNodes.Count `
            -Details ('Commandes AST détectées : ' + $CommandNodes.Count)

        Add-Result `
            -Category 'STRUCTURE' `
            -Name 'FUNCTIONS' `
            -Status 'INFO' `
            -Count $FunctionNodes.Count `
            -Details ('Fonctions détectées : ' + $FunctionNodes.Count)

        Add-Result `
            -Category 'STRUCTURE' `
            -Name 'THROW' `
            -Status 'INFO' `
            -Count $ThrowNodes.Count `
            -Details ('Instructions throw détectées : ' + $ThrowNodes.Count)

        Add-Result `
            -Category 'STRUCTURE' `
            -Name 'TRY' `
            -Status 'INFO' `
            -Count $TryNodes.Count `
            -Details ('Blocs try détectés : ' + $TryNodes.Count)

        Add-Result `
            -Category 'STRUCTURE' `
            -Name 'IF' `
            -Status 'INFO' `
            -Count $IfNodes.Count `
            -Details ('Blocs if détectés : ' + $IfNodes.Count)

        # =====================================================================
        # 8 — DYNAMIC EXECUTION
        # =====================================================================

        Test-Pattern `
            -Name 'INVOKE_EXPRESSION' `
            -Pattern '\bInvoke-Expression\b|\biex\b' `
            -Category 'EXECUTION' `
            -StatusWhenFound 'FAIL' `
            -FoundDescription 'Exécution dynamique détectée :'

        Test-Pattern `
            -Name 'START_PROCESS' `
            -Pattern '\bStart-Process\b' `
            -Category 'EXECUTION' `
            -StatusWhenFound 'WARN' `
            -FoundDescription 'Lancement de processus détecté :'

        Test-Pattern `
            -Name 'ADD_TYPE' `
            -Pattern '\bAdd-Type\b' `
            -Category 'EXECUTION' `
            -StatusWhenFound 'WARN' `
            -FoundDescription 'Chargement ou compilation de type détecté :'

        # =====================================================================
        # 9 — MUTATIONS
        # =====================================================================

        Test-Pattern `
            -Name 'SET_CONTENT' `
            -Pattern '\bSet-Content\b|\bAdd-Content\b' `
            -Category 'MUTATION' `
            -StatusWhenFound 'WARN' `
            -FoundDescription 'Écriture de contenu détectée :'

        Test-Pattern `
            -Name 'OUT_FILE' `
            -Pattern '\bOut-File\b' `
            -Category 'MUTATION' `
            -StatusWhenFound 'WARN' `
            -FoundDescription 'Écriture via Out-File détectée :'

        Test-Pattern `
            -Name 'NEW_ITEM' `
            -Pattern '\bNew-Item\b' `
            -Category 'MUTATION' `
            -StatusWhenFound 'WARN' `
            -FoundDescription 'Création filesystem détectée :'

        Test-Pattern `
            -Name 'COPY_ITEM' `
            -Pattern '\bCopy-Item\b' `
            -Category 'MUTATION' `
            -StatusWhenFound 'WARN' `
            -FoundDescription 'Copie filesystem détectée :'

        Test-Pattern `
            -Name 'MOVE_ITEM' `
            -Pattern '\bMove-Item\b' `
            -Category 'MUTATION' `
            -StatusWhenFound 'WARN' `
            -FoundDescription 'Déplacement filesystem détecté :'

        Test-Pattern `
            -Name 'REMOVE_ITEM' `
            -Pattern '\bRemove-Item\b' `
            -Category 'MUTATION' `
            -StatusWhenFound 'WARN' `
            -FoundDescription 'Suppression filesystem détectée :'

        # =====================================================================
        # 10 — EXTERNAL PROCESSES
        # =====================================================================

        Test-Pattern `
            -Name 'CMD_EXE' `
            -Pattern '(?i)(^|\s)cmd(?:\.exe)?(\s|$)' `
            -Category 'EXTERNAL_EXECUTION' `
            -StatusWhenFound 'WARN' `
            -FoundDescription 'Invocation CMD détectée :'

        Test-Pattern `
            -Name 'POWERSHELL_EXE' `
            -Pattern '(?i)\bpowershell(?:\.exe)?\b|\bpwsh(?:\.exe)?\b' `
            -Category 'EXTERNAL_EXECUTION' `
            -StatusWhenFound 'WARN' `
            -FoundDescription 'Invocation PowerShell externe détectée :'

        Test-Pattern `
            -Name 'GIT_COMMAND' `
            -Pattern '(?i)\bgit(?:\.exe)?\b' `
            -Category 'EXTERNAL_EXECUTION' `
            -StatusWhenFound 'WARN' `
            -FoundDescription 'Commande Git détectée :'

        # =====================================================================
        # 11 — NETWORK
        # =====================================================================

        Test-Pattern `
            -Name 'INVOKE_WEBREQUEST' `
            -Pattern '\bInvoke-WebRequest\b|\biwr\b' `
            -Category 'NETWORK' `
            -StatusWhenFound 'WARN' `
            -FoundDescription 'Accès HTTP détecté :'

        Test-Pattern `
            -Name 'INVOKE_RESTMETHOD' `
            -Pattern '\bInvoke-RestMethod\b|\birm\b' `
            -Category 'NETWORK' `
            -StatusWhenFound 'WARN' `
            -FoundDescription 'Accès REST détecté :'

        Test-Pattern `
            -Name 'WEBCLIENT' `
            -Pattern '\bSystem\.Net\.WebClient\b' `
            -Category 'NETWORK' `
            -StatusWhenFound 'WARN' `
            -FoundDescription 'WebClient détecté :'

        # =====================================================================
        # 12 — CERTIFICATION / PLACEHOLDERS
        # =====================================================================

        Test-Pattern `
            -Name 'ASSERT_TRUE' `
            -Pattern '(?i)\$true\s*$|\breturn\s+\$true\b|\breturn\s+true\b' `
            -Category 'CERTIFICATION' `
            -StatusWhenFound 'WARN' `
            -FoundDescription 'Construction pouvant constituer une assertion de succès :'

        Test-Pattern `
            -Name 'PLACEHOLDER' `
            -Pattern '(?i)\bTODO\b|\bFIXME\b|\bPLACEHOLDER\b|\bTBD\b|À\s*COMPL[EÈ]TER|A\s*COMPLETER' `
            -Category 'CERTIFICATION' `
            -StatusWhenFound 'WARN' `
            -FoundDescription 'Placeholder ou marqueur détecté :'

        Test-Pattern `
            -Name 'FAKE_PASS' `
            -Pattern '(?i)FAKE.?PASS|FORCED.?PASS|ALWAYS.?PASS|UNCONDITIONAL.?PASS' `
            -Category 'CERTIFICATION' `
            -StatusWhenFound 'FAIL' `
            -FoundDescription 'Motif de faux PASS détecté :'

        # =====================================================================
        # 13 — FAIL CLOSED
        # =====================================================================

        Test-Pattern `
            -Name 'FAIL_CLOSED' `
            -Pattern '(?i)FAIL.?CLOSED|FAIL_CLOSED|Fail.?Closed' `
            -Category 'FAIL_CLOSED' `
            -StatusWhenFound 'PASS' `
            -FoundDescription 'Marqueur FAIL-CLOSED détecté :'

        Test-Pattern `
            -Name 'ERROR_ACTION_STOP' `
            -Pattern '(?i)-ErrorAction\s+Stop' `
            -Category 'FAIL_CLOSED' `
            -StatusWhenFound 'PASS' `
            -FoundDescription 'Gestion ErrorAction Stop détectée :'

        Test-Pattern `
            -Name 'THROW' `
            -Pattern '(?i)\bthrow\b' `
            -Category 'FAIL_CLOSED' `
            -StatusWhenFound 'PASS' `
            -FoundDescription 'Mécanisme throw détecté :'

        # =====================================================================
        # 14 — HARDENING
        # =====================================================================

        Test-Pattern `
            -Name 'STRICT_MODE' `
            -Pattern '(?i)Set-StrictMode\s+-Version' `
            -Category 'HARDENING' `
            -StatusWhenFound 'PASS' `
            -FoundDescription 'Set-StrictMode détecté :'

        # =====================================================================
        # 15 — INTEGRITY
        # =====================================================================

        Test-Pattern `
            -Name 'SHA256' `
            -Pattern '(?i)SHA256|SHA-256|Get-FileHash' `
            -Category 'INTEGRITY' `
            -StatusWhenFound 'PASS' `
            -FoundDescription 'Mécanisme SHA-256 détecté :'

        # =====================================================================
        # 16 — CRYPTOGRAPHY
        # =====================================================================

        Test-Pattern `
            -Name 'HMAC' `
            -Pattern '(?i)\bHMAC\b|HMACSHA256|HMACSHA512' `
            -Category 'CRYPTOGRAPHY' `
            -StatusWhenFound 'PASS' `
            -FoundDescription 'Mécanisme HMAC détecté :'

        Test-Pattern `
            -Name 'SIGNATURE' `
            -Pattern '(?i)\bSignature\b|\bSigned\b|\bVerifySignature\b' `
            -Category 'CRYPTOGRAPHY' `
            -StatusWhenFound 'PASS' `
            -FoundDescription 'Mécanisme signature ou vérification détecté :'

        # =====================================================================
        # 17 — SECRETS
        # =====================================================================

        Test-Pattern `
            -Name 'ENV_SECRET_REFERENCE' `
            -Pattern ('(?i)\' + [char]36 + 'env:[A-Za-z0-9_]*(SECRET|KEY|TOKEN|PASSWORD)') `
            -Category 'SECRETS' `
            -StatusWhenFound 'PASS' `
            -FoundDescription 'Référence environnementale potentiellement secrète détectée :'

        # =====================================================================
        # 18 — OBFUSCATION / REFLECTION
        # =====================================================================

        Test-Pattern `
            -Name 'BASE64_LIKE' `
            -Pattern '(?i)(FromBase64String|ToBase64String)' `
            -Category 'OBFUSCATION' `
            -StatusWhenFound 'WARN' `
            -FoundDescription 'Conversion Base64 détectée :'

        Test-Pattern `
            -Name 'REFLECTION' `
            -Pattern '(?i)\.Reflection\b|System\.Reflection' `
            -Category 'OBFUSCATION' `
            -StatusWhenFound 'WARN' `
            -FoundDescription 'API Reflection détectée :'

        # =====================================================================
        # 19 — READ-ONLY ANALYSIS
        # =====================================================================

        $MutationResults = @(
            $Results |
            Where-Object {
                $_.Category -eq 'MUTATION' -and
                $_.Count -gt 0
            }
        )

        if ($MutationResults.Count -eq 0) {

            Add-Result `
                -Category 'READ_ONLY_ANALYSIS' `
                -Name 'MUTATION_SCAN' `
                -Status 'PASS' `
                -Count 0 `
                -Details 'Aucune primitive de mutation filesystem ciblée détectée.'
        }
        else {

            Add-Result `
                -Category 'READ_ONLY_ANALYSIS' `
                -Name 'MUTATION_SCAN' `
                -Status 'WARN' `
                -Count $MutationResults.Count `
                -Details 'Une ou plusieurs primitives de mutation sont présentes. Analyse contextuelle requise.'
        }

        # =====================================================================
        # 20 — TARGET EXECUTION GUARANTEE
        # =====================================================================

        Add-Result `
            -Category 'SAFETY' `
            -Name 'TARGET_EXECUTION' `
            -Status 'PASS' `
            -Count 0 `
            -Details 'Le validateur n''a exécuté aucune commande provenant de la cible.'

        # =====================================================================
        # 21 — TARGET MUTATION GUARANTEE
        # =====================================================================

        Add-Result `
            -Category 'SAFETY' `
            -Name 'TARGET_MUTATION' `
            -Status 'PASS' `
            -Count 0 `
            -Details 'Le validateur ne contient aucune opération d''écriture dirigée vers la cible.'

        # =====================================================================
        # 22 — SHA-256 AFTER
        # =====================================================================

        $Sha256After = Get-TargetSha256

        $FileInfoAfter = Get-Item `
            -LiteralPath $Target `
            -Force `
            -ErrorAction Stop

        $TargetLengthAfter = $FileInfoAfter.Length

        if ($Sha256Before -ne $Sha256After) {

            Add-Result `
                -Category 'INTEGRITY' `
                -Name 'SHA256_STABILITY' `
                -Status 'FAIL' `
                -Count 1 `
                -Details (
                    'SHA-256 modifié pendant le forensic. BEFORE=' +
                    $Sha256Before +
                    ' AFTER=' +
                    $Sha256After
                )
        }
        else {

            Add-Result `
                -Category 'INTEGRITY' `
                -Name 'SHA256_STABILITY' `
                -Status 'PASS' `
                -Count 1 `
                -Details 'SHA-256 identique avant et après le forensic.'
        }

        # =====================================================================
        # 23 — LENGTH STABILITY
        # =====================================================================

        if ($TargetLengthBefore -ne $TargetLengthAfter) {

            Add-Result `
                -Category 'INTEGRITY' `
                -Name 'SIZE_STABILITY' `
                -Status 'FAIL' `
                -Count 1 `
                -Details (
                    'Taille modifiée pendant le forensic. BEFORE=' +
                    $TargetLengthBefore +
                    ' AFTER=' +
                    $TargetLengthAfter
                )
        }
        else {

            Add-Result `
                -Category 'INTEGRITY' `
                -Name 'SIZE_STABILITY' `
                -Status 'PASS' `
                -Count 1 `
                -Details 'Taille physique identique avant et après le forensic.'
        }

        # =====================================================================
        # 24 — HANDLE STATUS
        # =====================================================================

        if ($null -ne $TargetReadHandle) {

            Add-Result `
                -Category 'SAFETY' `
                -Name 'READ_LOCK' `
                -Status 'PASS' `
                -Count 1 `
                -Details 'Le handle de lecture est resté actif durant l''analyse.'
        }

    }
    catch {

        $InternalFailure = $true
        $InternalFailureMessage = $_.Exception.Message
        $InternalFailureType = $_.Exception.GetType().FullName

        if ($null -ne $_.InvocationInfo) {
            $InternalFailureLine = $_.InvocationInfo.ScriptLineNumber
        }

        Add-Result `
            -Category 'VALIDATOR' `
            -Name 'INTERNAL_EXCEPTION' `
            -Status 'FAIL' `
            -Count 1 `
            -Details (
                'Exception interne du validateur : ' +
                $InternalFailureType +
                ' | Ligne=' +
                $InternalFailureLine +
                ' | Message=' +
                $InternalFailureMessage
            )

        Write-Host ''
        Write-Host '[FAIL-CLOSED] Exception interne du validateur.' -ForegroundColor Red
        Write-Host (
            'Type    : ' +
            $InternalFailureType
        ) -ForegroundColor Red
        Write-Host (
            'Ligne   : ' +
            $InternalFailureLine
        ) -ForegroundColor Red
        Write-Host (
            'Message : ' +
            $InternalFailureMessage
        ) -ForegroundColor Red
        Write-Host ''
    }
    finally {

        # =====================================================================
        # HANDLE RELEASE
        # =====================================================================

        if ($null -ne $TargetReadHandle) {

            try {
                $TargetReadHandle.Dispose()
            }
            catch {
                # Une erreur de libération sera traitée explicitement ci-dessous.
                Add-Result `
                    -Category 'SAFETY' `
                    -Name 'READ_LOCK_RELEASE' `
                    -Status 'FAIL' `
                    -Count 1 `
                    -Details (
                        'Impossible de libérer proprement le handle de lecture : ' +
                        $_.Exception.Message
                    )
            }

            $TargetReadHandle = $null
        }
    }

    # =========================================================================
    # 25 — FINAL COUNTS
    # =========================================================================

    $PassCount = @(
        $Results |
        Where-Object {
            $_.Status -eq 'PASS'
        }
    ).Count

    $WarnCount = @(
        $Results |
        Where-Object {
            $_.Status -eq 'WARN'
        }
    ).Count

    $FailCount = @(
        $Results |
        Where-Object {
            $_.Status -eq 'FAIL'
        }
    ).Count

    $InfoCount = @(
        $Results |
        Where-Object {
            $_.Status -eq 'INFO'
        }
    ).Count

    $EndedAt = Get-Date

    # =========================================================================
    # 26 — VERDICT
    # =========================================================================

    if ($InternalFailure) {

        $Verdict = 'FORENSIC_FAIL'
        $VerdictColor = 'Red'
        $ExitCode = 10
    }
    elseif ($FailCount -gt 0) {

        $Verdict = 'FORENSIC_FAIL'
        $VerdictColor = 'Red'
        $ExitCode = 10
    }
    elseif ($WarnCount -gt 0) {

        $Verdict = 'FORENSIC_REVIEW_REQUIRED'
        $VerdictColor = 'Yellow'
        $ExitCode = 20
    }
    else {

        $Verdict = 'FORENSIC_PASS'
        $VerdictColor = 'Green'
        $ExitCode = 0
    }

    # =========================================================================
    # 27 — REPORT DIRECTORY
    # =========================================================================

    try {

        if (-not (
            Test-Path `
                -LiteralPath $ReportDirectory `
                -PathType Container
        )) {

            New-Item `
                -ItemType Directory `
                -Path $ReportDirectory `
                -Force `
                -ErrorAction Stop |
                Out-Null
        }
    }
    catch {

        Write-Host ''
        Write-Host '[FAIL-CLOSED] Impossible de créer le répertoire de rapports.' -ForegroundColor Red
        Write-Host $_.Exception.Message -ForegroundColor Red
        exit 10
    }

    # =========================================================================
    # 28 — REPORT OBJECT
    # =========================================================================

    $Report = [ordered]@{

        Engine = 'E-ZZIO'

        Validation = 'FORENSIC_STATIC'

        Version = '1.1.4'

        Mode = 'READ-ONLY'

        ExecutionOfTarget = $false

        MutationOfTarget = $false

        TargetReadLock = $true

        ProjectRoot = $ProjectRoot

        Target = $Target

        TargetLengthBytesBefore = $TargetLengthBefore

        TargetLengthBytesAfter = $TargetLengthAfter

        TargetLastWriteTime = if ($null -ne $FileInfo) {
            $FileInfo.LastWriteTime.ToString('o')
        }
        else {
            $null
        }

        SHA256Before = $Sha256Before

        SHA256After = $Sha256After

        SHA256Stable = if (
            $null -ne $Sha256Before -and
            $null -ne $Sha256After
        ) {
            $Sha256Before -eq $Sha256After
        }
        else {
            $false
        }

        StartedAt = $StartedAt.ToString('o')

        EndedAt = $EndedAt.ToString('o')

        DurationSeconds = [math]::Round(
            ($EndedAt - $StartedAt).TotalSeconds,
            3
        )

        AstErrors = $AstErrorArray.Count

        CommandCount = $CommandNodes.Count

        FunctionCount = $FunctionNodes.Count

        ThrowCount = $ThrowNodes.Count

        TryCount = $TryNodes.Count

        IfCount = $IfNodes.Count

        PassCount = $PassCount

        WarnCount = $WarnCount

        FailCount = $FailCount

        InfoCount = $InfoCount

        InternalFailure = $InternalFailure

        InternalFailureType = $InternalFailureType

        InternalFailureLine = $InternalFailureLine

        InternalFailureMessage = $InternalFailureMessage

        Verdict = $Verdict

        ExitCode = $ExitCode

        Results = @(
            $Results
        )
    }

    # =========================================================================
    # 29 — JSON REPORT
    #
    # IMPORTANT :
    #   Aucun "-f".
    # =========================================================================

    try {

        $JsonText = $Report |
            ConvertTo-Json `
                -Depth 10 `
                -ErrorAction Stop

        Set-Content `
            -LiteralPath $ReportJson `
            -Value $JsonText `
            -Encoding UTF8 `
            -ErrorAction Stop
    }
    catch {

        Write-Host ''
        Write-Host '[FAIL-CLOSED] Échec génération JSON.' -ForegroundColor Red
        Write-Host $_.Exception.Message -ForegroundColor Red

        $Verdict = 'FORENSIC_FAIL'
        $ExitCode = 10

        exit 10
    }

    # =========================================================================
    # 30 — TXT REPORT
    #
    # IMPORTANT :
    #   Construction par concaténation.
    #   Aucun opérateur "-f".
    #   Cela élimine la classe d'erreur rencontrée en v1.1.3.
    # =========================================================================

    try {

        $TextLines = [System.Collections.Generic.List[string]]::new()

        $TextLines.Add(
            '============================================================'
        )

        $TextLines.Add(
            'E-ZZIO — VALIDATION FORENSIC STATIQUE v1.1.4'
        )

        $TextLines.Add(
            '============================================================'
        )

        $TextLines.Add('')

        $TextLines.Add(
            'Mode                : READ-ONLY'
        )

        $TextLines.Add(
            'Execution cible     : FALSE'
        )

        $TextLines.Add(
            'Mutation cible      : FALSE'
        )

        $TextLines.Add(
            'Target read lock    : TRUE'
        )

        $TextLines.Add(
            'Projet              : ' + $ProjectRoot
        )

        $TextLines.Add(
            'Cible               : ' + $Target
        )

        $TextLines.Add(
            'Taille BEFORE       : ' + $TargetLengthBefore
        )

        $TextLines.Add(
            'Taille AFTER        : ' + $TargetLengthAfter
        )

        $TextLines.Add(
            'SHA-256 BEFORE      : ' + $Sha256Before
        )

        $TextLines.Add(
            'SHA-256 AFTER       : ' + $Sha256After
        )

        $TextLines.Add(
            'SHA-256 STABLE      : ' +
            [string](
                $null -ne $Sha256Before -and
                $null -ne $Sha256After -and
                $Sha256Before -eq $Sha256After
            )
        )

        $TextLines.Add(
            'AST Errors          : ' + $AstErrorArray.Count
        )

        $TextLines.Add(
            'Commandes AST       : ' + $CommandNodes.Count
        )

        $TextLines.Add(
            'Fonctions           : ' + $FunctionNodes.Count
        )

        $TextLines.Add(
            'Throw               : ' + $ThrowNodes.Count
        )

        $TextLines.Add(
            'Try                 : ' + $TryNodes.Count
        )

        $TextLines.Add(
            'If                  : ' + $IfNodes.Count
        )

        $TextLines.Add('')

        $TextLines.Add(
            'PASS                : ' + $PassCount
        )

        $TextLines.Add(
            'WARN                : ' + $WarnCount
        )

        $TextLines.Add(
            'FAIL                : ' + $FailCount
        )

        $TextLines.Add(
            'INFO                : ' + $InfoCount
        )

        $TextLines.Add('')

        $TextLines.Add(
            'Internal Failure    : ' + $InternalFailure
        )

        if ($InternalFailure) {

            $TextLines.Add(
                'Failure Type        : ' + $InternalFailureType
            )

            $TextLines.Add(
                'Failure Line        : ' + $InternalFailureLine
            )

            $TextLines.Add(
                'Failure Message     : ' + $InternalFailureMessage
            )
        }

        $TextLines.Add('')

        $TextLines.Add(
            'VERDICT             : ' + $Verdict
        )

        $TextLines.Add(
            'EXIT CODE           : ' + $ExitCode
        )

        $TextLines.Add('')

        $TextLines.Add(
            '------------------------------------------------------------'
        )

        $TextLines.Add(
            'DETAILS'
        )

        $TextLines.Add(
            '------------------------------------------------------------'
        )

        foreach ($Result in $Results) {

            $TextLines.Add(
                '[' +
                $Result.Status +
                '] ' +
                $Result.Category +
                '/' +
                $Result.Name +
                ' | Count=' +
                $Result.Count +
                ' | ' +
                $Result.Details
            )
        }

        $TextLines.Add('')

        $TextLines.Add(
            '============================================================'
        )

        $TextLines.Add(
            'FIN FORENSIC'
        )

        $TextLines.Add(
            '============================================================'
        )

        Set-Content `
            -LiteralPath $ReportTxt `
            -Value $TextLines `
            -Encoding UTF8 `
            -ErrorAction Stop
    }
    catch {

        Write-Host ''
        Write-Host '[FAIL-CLOSED] Échec génération TXT.' -ForegroundColor Red
        Write-Host $_.Exception.Message -ForegroundColor Red
        exit 10
    }

    # =========================================================================
    # 31 — CONSOLE
    # =========================================================================

    Write-Host ''
    Write-Host '============================================================' -ForegroundColor Cyan
    Write-Host ' RÉSULTAT FORENSIC STATIQUE v1.1.4' -ForegroundColor Cyan
    Write-Host '============================================================' -ForegroundColor Cyan
    Write-Host ''

    Write-Host (
        'Cible       : ' +
        $Target
    )

    Write-Host (
        'SHA-256     : ' +
        $Sha256Before
    )

    Write-Host (
        'SHA stable  : ' +
        (
            $null -ne $Sha256Before -and
            $null -ne $Sha256After -and
            $Sha256Before -eq $Sha256After
        )
    )

    Write-Host ''

    Write-Host (
        'AST Errors  : ' +
        $AstErrorArray.Count
    )

    Write-Host (
        'PASS        : ' +
        $PassCount
    )

    Write-Host (
        'WARN        : ' +
        $WarnCount
    )

    Write-Host (
        'FAIL        : ' +
        $FailCount
    )

    Write-Host (
        'INFO        : ' +
        $InfoCount
    )

    Write-Host ''

    Write-Host (
        'VERDICT : ' +
        $Verdict
    ) -ForegroundColor $VerdictColor

    Write-Host ''

    Write-Host (
        'Rapport TXT  : ' +
        $ReportTxt
    )

    Write-Host (
        'Rapport JSON : ' +
        $ReportJson
    )

    Write-Host ''

    Write-Host '============================================================' -ForegroundColor Cyan

    # =========================================================================
    # 32 — FINAL FAIL CLOSED
    # =========================================================================

    if ($FailCount -gt 0) {

        Write-Host ''
        Write-Host `
            '[FAIL-CLOSED] Anomalie(s) bloquante(s) détectée(s).' `
            -ForegroundColor Red

        Write-Host `
            '[FAIL-CLOSED] La cible n''a PAS été exécutée.' `
            -ForegroundColor Red

        Write-Host `
            '[FAIL-CLOSED] La cible n''a PAS été modifiée.' `
            -ForegroundColor Red

        exit 10
    }

    if ($WarnCount -gt 0) {

        Write-Host ''
        Write-Host `
            '[REVIEW REQUIRED] Analyse contextuelle nécessaire.' `
            -ForegroundColor Yellow

        Write-Host `
            '[REVIEW REQUIRED] La cible n''a PAS été exécutée.' `
            -ForegroundColor Yellow

        Write-Host `
            '[REVIEW REQUIRED] La cible n''a PAS été modifiée.' `
            -ForegroundColor Yellow

        exit 20
    }

    Write-Host ''
    Write-Host `
        '[PASS] Aucun FAIL forensic détecté.' `
        -ForegroundColor Green

    Write-Host `
        '[PASS] La cible n''a PAS été exécutée.' `
        -ForegroundColor Green

    Write-Host `
        '[PASS] La cible n''a PAS été modifiée.' `
        -ForegroundColor Green

    exit 0
}
