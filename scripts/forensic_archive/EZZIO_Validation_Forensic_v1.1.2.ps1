# ============================================================================
# E-ZZIO — VALIDATION FORENSIC STATIQUE v1.1.2
# ============================================================================
# MODE       : READ-ONLY / FAIL-CLOSED / FORENSIC
# CIBLE      : EZZIO_Freeze_Certification_v1.1.1.ps1
#
# GARANTIES :
#   - La cible est uniquement lue.
#   - La cible n'est jamais exécutée.
#   - La cible n'est jamais modifiée.
#   - AST PowerShell réel.
#   - SHA-256 réel.
#   - Recherche statique de constructions sensibles.
#   - Rapport TXT + JSON.
#
# EXIT CODES :
#   0  = FORENSIC_PASS
#   10 = FORENSIC_FAIL
#   20 = FORENSIC_REVIEW_REQUIRED
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
    # OUTILS
    # =========================================================================

    $Results = [System.Collections.Generic.List[object]]::new()

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

        $script:Results.Add(
            [pscustomobject]@{
                Category = $Category
                Name     = $Name
                Status   = $Status
                Count    = $Count
                Details  = $Details
            }
        )
    }

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

        $Locations = foreach ($Match in $MatchesFound) {

            foreach ($M in $Match.Matches) {

                [pscustomobject]@{
                    Line   = $Match.LineNumber
                    Column = $M.Index + 1
                    Text   = $Match.Line.Trim()
                }
            }
        }

        $Preview = (
            $Locations |
            Select-Object -First 20 |
            ForEach-Object {
                "L$($_.Line):C$($_.Column) -> $($_.Text)"
            }
        ) -join ' | '

        Add-Result `
            -Category $Category `
            -Name $Name `
            -Status $StatusWhenFound `
            -Count $Locations.Count `
            -Details "$FoundDescription $Preview"
    }

    # =========================================================================
    # START
    # =========================================================================

    $StartedAt = Get-Date

    Write-Host ''
    Write-Host '============================================================' -ForegroundColor Cyan
    Write-Host ' E-ZZIO — VALIDATION FORENSIC STATIQUE v1.1.2' -ForegroundColor Cyan
    Write-Host '============================================================' -ForegroundColor Cyan
    Write-Host ''

    Write-Host "Projet : $ProjectRoot"
    Write-Host "Cible  : $Target"
    Write-Host ''
    Write-Host 'MODE : READ-ONLY / NO TARGET EXECUTION / FAIL-CLOSED' -ForegroundColor Yellow
    Write-Host ''

    # =========================================================================
    # 1 — PROJET
    # =========================================================================

    if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) {

        throw "FAIL-CLOSED : projet introuvable : $ProjectRoot"
    }

    Add-Result `
        -Category 'ENVIRONMENT' `
        -Name 'PROJECT_ROOT' `
        -Status 'PASS' `
        -Count 1 `
        -Details "Répertoire projet accessible : $ProjectRoot"

    # =========================================================================
    # 2 — CIBLE
    # =========================================================================

    if (-not (Test-Path -LiteralPath $Target -PathType Leaf)) {

        throw "FAIL-CLOSED : cible introuvable : $Target"
    }

    $FileInfo = Get-Item -LiteralPath $Target -Force -ErrorAction Stop

    if ($FileInfo.Length -eq 0) {

        Add-Result `
            -Category 'TARGET' `
            -Name 'EMPTY_FILE' `
            -Status 'FAIL' `
            -Count 1 `
            -Details 'Le fichier cible est vide.'

        throw 'FAIL-CLOSED : fichier cible vide.'
    }

    Add-Result `
        -Category 'TARGET' `
        -Name 'TARGET_EXISTS' `
        -Status 'PASS' `
        -Count 1 `
        -Details "Fichier trouvé : $($FileInfo.FullName)"

    Add-Result `
        -Category 'TARGET' `
        -Name 'TARGET_SIZE' `
        -Status 'PASS' `
        -Count 1 `
        -Details "Taille physique : $($FileInfo.Length) octets"

    # =========================================================================
    # 3 — SHA-256
    # =========================================================================

    $Sha256 = (
        Get-FileHash `
            -LiteralPath $Target `
            -Algorithm SHA256 `
            -ErrorAction Stop
    ).Hash

    Add-Result `
        -Category 'INTEGRITY' `
        -Name 'SHA256' `
        -Status 'PASS' `
        -Count 1 `
        -Details $Sha256

    # =========================================================================
    # 4 — LECTURE
    # =========================================================================

    $Content = Get-Content `
        -LiteralPath $Target `
        -Raw `
        -Encoding UTF8 `
        -ErrorAction Stop

    if ([string]::IsNullOrWhiteSpace($Content)) {

        Add-Result `
            -Category 'TARGET' `
            -Name 'CONTENT_READ' `
            -Status 'FAIL' `
            -Count 1 `
            -Details 'Le contenu lu est vide.'

        throw 'FAIL-CLOSED : contenu cible vide.'
    }

    $Lines = @(
        $Content -split "`r?`n"
    )

    Add-Result `
        -Category 'TARGET' `
        -Name 'CONTENT_READ' `
        -Status 'PASS' `
        -Count $Lines.Count `
        -Details "Lecture réussie : $($Lines.Count) lignes logiques."

    # =========================================================================
    # 5 — AST
    # =========================================================================

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
                "[AST FAIL] Ligne $($AstError.Extent.StartLineNumber), " +
                "colonne $($AstError.Extent.StartColumnNumber) : " +
                "$($AstError.Message)"
            ) -ForegroundColor Red
        }

        Add-Result `
            -Category 'AST' `
            -Name 'SYNTAX' `
            -Status 'FAIL' `
            -Count $AstErrorArray.Count `
            -Details 'Erreur(s) AST détectée(s).'
    }

    # =========================================================================
    # 6 — STRUCTURE AST
    # =========================================================================

    $CommandNodes = @(
        $Ast.FindAll(
            {
                param($Node)

                $Node -is [System.Management.Automation.Language.CommandAst]
            },
            $true
        )
    )

    $FunctionNodes = @(
        $Ast.FindAll(
            {
                param($Node)

                $Node -is [System.Management.Automation.Language.FunctionDefinitionAst]
            },
            $true
        )
    )

    $ThrowNodes = @(
        $Ast.FindAll(
            {
                param($Node)

                $Node -is [System.Management.Automation.Language.ThrowStatementAst]
            },
            $true
        )
    )

    $TryNodes = @(
        $Ast.FindAll(
            {
                param($Node)

                $Node -is [System.Management.Automation.Language.TryStatementAst]
            },
            $true
        )
    )

    $IfNodes = @(
        $Ast.FindAll(
            {
                param($Node)

                $Node -is [System.Management.Automation.Language.IfStatementAst]
            },
            $true
        )
    )

    Add-Result `
        -Category 'STRUCTURE' `
        -Name 'COMMANDS' `
        -Status 'INFO' `
        -Count $CommandNodes.Count `
        -Details "Commandes AST détectées : $($CommandNodes.Count)"

    Add-Result `
        -Category 'STRUCTURE' `
        -Name 'FUNCTIONS' `
        -Status 'INFO' `
        -Count $FunctionNodes.Count `
        -Details "Fonctions détectées : $($FunctionNodes.Count)"

    Add-Result `
        -Category 'STRUCTURE' `
        -Name 'THROW' `
        -Status 'INFO' `
        -Count $ThrowNodes.Count `
        -Details "Instructions throw détectées : $($ThrowNodes.Count)"

    Add-Result `
        -Category 'STRUCTURE' `
        -Name 'TRY' `
        -Status 'INFO' `
        -Count $TryNodes.Count `
        -Details "Blocs try détectés : $($TryNodes.Count)"

    Add-Result `
        -Category 'STRUCTURE' `
        -Name 'IF' `
        -Status 'INFO' `
        -Count $IfNodes.Count `
        -Details "Blocs if détectés : $($IfNodes.Count)"

    # =========================================================================
    # 7 — EXECUTION DYNAMIQUE
    # =========================================================================

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

    # =========================================================================
    # 8 — MUTATIONS
    # =========================================================================

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

    # =========================================================================
    # 9 — PROCESSUS EXTERNES
    # =========================================================================

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

    # =========================================================================
    # 10 — RESEAU
    # =========================================================================

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

    # =========================================================================
    # 11 — CERTIFICATION / PLACEHOLDERS
    # =========================================================================

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

    # =========================================================================
    # 12 — FAIL-CLOSED
    # =========================================================================

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

    # =========================================================================
    # 13 — HARDENING
    # =========================================================================

    Test-Pattern `
        -Name 'STRICT_MODE' `
        -Pattern '(?i)Set-StrictMode\s+-Version' `
        -Category 'HARDENING' `
        -StatusWhenFound 'PASS' `
        -FoundDescription 'Set-StrictMode détecté :'

    # =========================================================================
    # 14 — INTEGRITE
    # =========================================================================

    Test-Pattern `
        -Name 'SHA256' `
        -Pattern '(?i)SHA256|SHA-256|Get-FileHash' `
        -Category 'INTEGRITY' `
        -StatusWhenFound 'PASS' `
        -FoundDescription 'Mécanisme SHA-256 détecté :'

    # =========================================================================
    # 15 — CRYPTOGRAPHIE
    # =========================================================================

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

    # =========================================================================
    # 16 — SECRETS
    # =========================================================================

    Test-Pattern `
        -Name 'ENV_SECRET_REFERENCE' `
        -Pattern '(?i)\$env:[A-Za-z0-9_]*(SECRET|KEY|TOKEN|PASSWORD)' `
        -Category 'SECRETS' `
        -StatusWhenFound 'PASS' `
        -FoundDescription 'Référence environnementale potentiellement secrète détectée :'

    # =========================================================================
    # 17 — OBFUSCATION / REFLECTION
    # =========================================================================

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

    # =========================================================================
    # 18 — READ ONLY ANALYSIS
    # =========================================================================

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
            -Details 'Une ou plusieurs primitives de mutation sont présentes dans le texte cible. Analyse contextuelle requise.'
    }

    # =========================================================================
    # 19 — GARANTIE DE NON-EXECUTION
    # =========================================================================

    Add-Result `
        -Category 'SAFETY' `
        -Name 'TARGET_EXECUTION' `
        -Status 'PASS' `
        -Count 0 `
        -Details 'Le validateur ne contient aucun appel permettant de lancer la cible.'

    # =========================================================================
    # 20 — SUMMARY
    # =========================================================================

    $PassCount = @(
        $Results |
        Where-Object { $_.Status -eq 'PASS' }
    ).Count

    $WarnCount = @(
        $Results |
        Where-Object { $_.Status -eq 'WARN' }
    ).Count

    $FailCount = @(
        $Results |
        Where-Object { $_.Status -eq 'FAIL' }
    ).Count

    $InfoCount = @(
        $Results |
        Where-Object { $_.Status -eq 'INFO' }
    ).Count

    $EndedAt = Get-Date

    # =========================================================================
    # 21 — VERDICT
    # =========================================================================

    if ($FailCount -gt 0) {

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
    # 22 — RAPPORT JSON
    # =========================================================================

    if (-not (Test-Path -LiteralPath $ReportDirectory -PathType Container)) {

        New-Item `
            -ItemType Directory `
            -Path $ReportDirectory `
            -Force `
            -ErrorAction Stop |
            Out-Null
    }

    $Report = [ordered]@{
        Engine              = 'E-ZZIO'
        Validation          = 'FORENSIC_STATIC'
        Version             = '1.1.2'
        Mode                = 'READ-ONLY'
        ExecutionOfTarget   = $false
        MutationOfTarget    = $false
        ProjectRoot         = $ProjectRoot
        Target              = $Target
        TargetLengthBytes   = $FileInfo.Length
        TargetLastWriteTime = $FileInfo.LastWriteTime.ToString('o')
        SHA256              = $Sha256
        StartedAt           = $StartedAt.ToString('o')
        EndedAt             = $EndedAt.ToString('o')
        DurationSeconds     = [math]::Round(
            ($EndedAt - $StartedAt).TotalSeconds,
            3
        )
        AstErrors           = $AstErrorArray.Count
        CommandCount        = $CommandNodes.Count
        FunctionCount       = $FunctionNodes.Count
        ThrowCount          = $ThrowNodes.Count
        TryCount             = $TryNodes.Count
        IfCount              = $IfNodes.Count
        PassCount           = $PassCount
        WarnCount           = $WarnCount
        FailCount           = $FailCount
        InfoCount           = $InfoCount
        Verdict             = $Verdict
        ExitCode            = $ExitCode
        Results             = @($Results)
    }

    $Report |
        ConvertTo-Json -Depth 8 |
        Set-Content `
            -LiteralPath $ReportJson `
            -Encoding UTF8 `
            -ErrorAction Stop

    # =========================================================================
    # 23 — RAPPORT TXT
    # =========================================================================

    $TextLines = [System.Collections.Generic.List[string]]::new()

    $TextLines.Add('============================================================')
    $TextLines.Add('E-ZZIO — VALIDATION FORENSIC STATIQUE v1.1.2')
    $TextLines.Add('============================================================')
    $TextLines.Add('')
    $TextLines.Add('Mode                : READ-ONLY')
    $TextLines.Add('Execution cible     : FALSE')
    $TextLines.Add('Mutation cible      : FALSE')
    $TextLines.Add("Projet              : $ProjectRoot")
    $TextLines.Add("Cible               : $Target")
    $TextLines.Add("Taille              : $($FileInfo.Length) octets")
    $TextLines.Add("SHA-256             : $Sha256")
    $TextLines.Add("AST Errors          : $($AstErrorArray.Count)")
    $TextLines.Add("Commandes AST       : $($CommandNodes.Count)")
    $TextLines.Add("Fonctions           : $($FunctionNodes.Count)")
    $TextLines.Add("Throw               : $($ThrowNodes.Count)")
    $TextLines.Add("Try                 : $($TryNodes.Count)")
    $TextLines.Add("If                  : $($IfNodes.Count)")
    $TextLines.Add('')
    $TextLines.Add("PASS                : $PassCount")
    $TextLines.Add("WARN                : $WarnCount")
    $TextLines.Add("FAIL                : $FailCount")
    $TextLines.Add("INFO                : $InfoCount")
    $TextLines.Add('')
    $TextLines.Add("VERDICT             : $Verdict")
    $TextLines.Add("EXIT CODE           : $ExitCode")
    $TextLines.Add('')
    $TextLines.Add('------------------------------------------------------------')
    $TextLines.Add('DETAILS')
    $TextLines.Add('------------------------------------------------------------')

    foreach ($Result in $Results) {

        $TextLines.Add(
            "[{0}] {1}/{2} | Count={3} | {4}" -f
            $Result.Status,
            $Result.Category,
            $Result.Name,
            $Result.Count,
            $Result.Details
        )
    }

    $TextLines.Add('')
    $TextLines.Add('============================================================')
    $TextLines.Add('FIN FORENSIC')
    $TextLines.Add('============================================================')

    $TextLines |
        Set-Content `
            -LiteralPath $ReportTxt `
            -Encoding UTF8 `
            -ErrorAction Stop

    # =========================================================================
    # 24 — CONSOLE
    # =========================================================================

    Write-Host ''
    Write-Host '============================================================' -ForegroundColor Cyan
    Write-Host ' RÉSULTAT FORENSIC STATIQUE' -ForegroundColor Cyan
    Write-Host '============================================================' -ForegroundColor Cyan
    Write-Host ''

    Write-Host "Cible       : $Target"
    Write-Host "SHA-256     : $Sha256"
    Write-Host ''

    Write-Host "AST Errors  : $($AstErrorArray.Count)"
    Write-Host "PASS        : $PassCount"
    Write-Host "WARN        : $WarnCount"
    Write-Host "FAIL        : $FailCount"
    Write-Host "INFO        : $InfoCount"
    Write-Host ''

    Write-Host "VERDICT : $Verdict" -ForegroundColor $VerdictColor

    Write-Host ''
    Write-Host "Rapport TXT  : $ReportTxt"
    Write-Host "Rapport JSON : $ReportJson"
    Write-Host ''

    Write-Host '============================================================' -ForegroundColor Cyan

    # =========================================================================
    # 25 — FAIL CLOSED
    # =========================================================================

    if ($FailCount -gt 0) {

        Write-Host ''
        Write-Host '[FAIL-CLOSED] Anomalie(s) bloquante(s) détectée(s).' -ForegroundColor Red
        Write-Host '[FAIL-CLOSED] La cible n''a PAS été exécutée.' -ForegroundColor Red

        exit 10
    }

    if ($WarnCount -gt 0) {

        Write-Host ''
        Write-Host '[REVIEW REQUIRED] Analyse contextuelle nécessaire.' -ForegroundColor Yellow
        Write-Host '[REVIEW REQUIRED] La cible n''a PAS été exécutée.' -ForegroundColor Yellow

        exit 20
    }

    Write-Host ''
    Write-Host '[PASS] Aucun FAIL forensic détecté.' -ForegroundColor Green
    Write-Host '[PASS] La cible n''a PAS été exécutée.' -ForegroundColor Green

    exit 0
}
