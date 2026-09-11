& {

    Set-StrictMode -Version Latest
    $ErrorActionPreference = 'Stop'

    $ProjectRoot = 'G:\AI\E-zzio'

    $Target = Join-Path `
        -Path $ProjectRoot `
        -ChildPath 'EZZIO_Freeze_Certification_v1.1.1.ps1'

    $ReportDirectory = Join-Path `
        -Path $ProjectRoot `
        -ChildPath 'forensic_validation'

    $Timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'

    $ReportTxt = Join-Path `
        -Path $ReportDirectory `
        -ChildPath "EZZIO_Freeze_Certification_v1.1.1_FORENSIC_$Timestamp.txt"

    $ReportJson = Join-Path `
        -Path $ReportDirectory `
        -ChildPath "EZZIO_Freeze_Certification_v1.1.1_FORENSIC_$Timestamp.json"

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

        $Matches = @(
            Select-String `
                -LiteralPath $Target `
                -Pattern $Pattern `
                -CaseSensitive:$false `
                -AllMatches `
                -ErrorAction Stop
        )

        if ($Matches.Count -eq 0) {

            Add-Result `
                -Category $Category `
                -Name $Name `
                -Status 'PASS' `
                -Count 0 `
                -Details 'Aucune occurrence détectée.'

            return
        }

        $Locations = @(
            foreach ($Match in $Matches) {

                foreach ($M in $Match.Matches) {

                    [pscustomobject]@{
                        Line   = $Match.LineNumber
                        Column = $M.Index + 1
                        Text   = $Match.Line.Trim()
                    }
                }
            }
        )

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

    $StartedAt = Get-Date

    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host ' E-ZZIO — VALIDATION FORENSIC STATIQUE v1.1.1' -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Projet : $ProjectRoot"
    Write-Host "Cible  : $Target"
    Write-Host ""
    Write-Host 'MODE : READ-ONLY / NO EXECUTION / FAIL-CLOSED' -ForegroundColor Yellow
    Write-Host ""

    # ========================================================================
    # 1 — PROJET
    # ========================================================================

    if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) {
        throw "FAIL-CLOSED : projet introuvable : $ProjectRoot"
    }

    Add-Result `
        -Category 'ENVIRONMENT' `
        -Name 'PROJECT_ROOT' `
        -Status 'PASS' `
        -Count 1 `
        -Details "Projet accessible : $ProjectRoot"

    # ========================================================================
    # 2 — CIBLE
    # ========================================================================

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

        throw 'FAIL-CLOSED : cible vide.'
    }

    Add-Result `
        -Category 'TARGET' `
        -Name 'TARGET_EXISTS' `
        -Status 'PASS' `
        -Count 1 `
        -Details "Cible trouvée : $($FileInfo.FullName)"

    Add-Result `
        -Category 'TARGET' `
        -Name 'TARGET_SIZE' `
        -Status 'PASS' `
        -Count 1 `
        -Details "Taille : $($FileInfo.Length) octets"

    # ========================================================================
    # 3 — SHA-256
    # ========================================================================

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

    # ========================================================================
    # 4 — LECTURE
    # ========================================================================

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
            -Details 'Contenu vide après lecture.'

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
        -Details "Lecture réussie : $($Lines.Count) lignes."

    # ========================================================================
    # 5 — AST
    # ========================================================================

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

    # ========================================================================
    # 6 — STRUCTURE AST
    # ========================================================================

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

    $ThrowNodes = @(
        $Ast.FindAll(
            {
                param($Node)

                $Node -is [System.Management.Automation.Language.ThrowStatementAst]
            },
            $true
        )
    )

    Add-Result `
        -Category 'STRUCTURE' `
        -Name 'COMMANDS' `
        -Status 'INFO' `
        -Count $CommandNodes.Count `
        -Details "Commandes AST : $($CommandNodes.Count)"

    Add-Result `
        -Category 'STRUCTURE' `
        -Name 'FUNCTIONS' `
        -Status 'INFO' `
        -Count $FunctionNodes.Count `
        -Details "Fonctions AST : $($FunctionNodes.Count)"

    Add-Result `
        -Category 'STRUCTURE' `
        -Name 'TRY' `
        -Status 'INFO' `
        -Count $TryNodes.Count `
        -Details "Try AST : $($TryNodes.Count)"

    Add-Result `
        -Category 'STRUCTURE' `
        -Name 'IF' `
        -Status 'INFO' `
        -Count $IfNodes.Count `
        -Details "If AST : $($IfNodes.Count)"

    Add-Result `
        -Category 'STRUCTURE' `
        -Name 'THROW' `
        -Status 'INFO' `
        -Count $ThrowNodes.Count `
        -Details "Throw AST : $($ThrowNodes.Count)"

    # ========================================================================
    # 7 — EXECUTION DYNAMIQUE
    # ========================================================================

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
        -FoundDescription 'Add-Type détecté :'

    # ========================================================================
    # 8 — MUTATIONS
    # ========================================================================

    Test-Pattern `
        -Name 'SET_CONTENT' `
        -Pattern '\bSet-Content\b|\bAdd-Content\b' `
        -Category 'MUTATION' `
        -StatusWhenFound 'WARN' `
        -FoundDescription 'Écriture détectée :'

    Test-Pattern `
        -Name 'OUT_FILE' `
        -Pattern '\bOut-File\b' `
        -Category 'MUTATION' `
        -StatusWhenFound 'WARN' `
        -FoundDescription 'Out-File détecté :'

    Test-Pattern `
        -Name 'NEW_ITEM' `
        -Pattern '\bNew-Item\b' `
        -Category 'MUTATION' `
        -StatusWhenFound 'WARN' `
        -FoundDescription 'New-Item détecté :'

    Test-Pattern `
        -Name 'COPY_ITEM' `
        -Pattern '\bCopy-Item\b' `
        -Category 'MUTATION' `
        -StatusWhenFound 'WARN' `
        -FoundDescription 'Copy-Item détecté :'

    Test-Pattern `
        -Name 'MOVE_ITEM' `
        -Pattern '\bMove-Item\b' `
        -Category 'MUTATION' `
        -StatusWhenFound 'WARN' `
        -FoundDescription 'Move-Item détecté :'

    Test-Pattern `
        -Name 'REMOVE_ITEM' `
        -Pattern '\bRemove-Item\b' `
        -Category 'MUTATION' `
        -StatusWhenFound 'WARN' `
        -FoundDescription 'Remove-Item détecté :'

    # ========================================================================
    # 9 — RÉSEAU
    # ========================================================================

    Test-Pattern `
        -Name 'INVOKE_WEBREQUEST' `
        -Pattern '\bInvoke-WebRequest\b|\biwr\b' `
        -Category 'NETWORK' `
        -StatusWhenFound 'WARN' `
        -FoundDescription 'Invoke-WebRequest détecté :'

    Test-Pattern `
        -Name 'INVOKE_RESTMETHOD' `
        -Pattern '\bInvoke-RestMethod\b|\birm\b' `
        -Category 'NETWORK' `
        -StatusWhenFound 'WARN' `
        -FoundDescription 'Invoke-RestMethod détecté :'

    # ========================================================================
    # 10 — ASSERTIONS / PLACEHOLDERS
    # ========================================================================

    Test-Pattern `
        -Name 'ASSERT_TRUE' `
        -Pattern '(?i)\$true\s*$|\breturn\s+\$true\b|\breturn\s+true\b' `
        -Category 'CERTIFICATION' `
        -StatusWhenFound 'WARN' `
        -FoundDescription 'Assertion de succès potentielle :'

    Test-Pattern `
        -Name 'PLACEHOLDER' `
        -Pattern '(?i)\bTODO\b|\bFIXME\b|\bPLACEHOLDER\b|\bTBD\b' `
        -Category 'CERTIFICATION' `
        -StatusWhenFound 'WARN' `
        -FoundDescription 'Placeholder détecté :'

    Test-Pattern `
        -Name 'FAKE_PASS' `
        -Pattern '(?i)FAKE.?PASS|FORCED.?PASS|ALWAYS.?PASS|UNCONDITIONAL.?PASS' `
        -Category 'CERTIFICATION' `
        -StatusWhenFound 'FAIL' `
        -FoundDescription 'Motif de faux PASS détecté :'

    # ========================================================================
    # 11 — FAIL-CLOSED / HARDENING
    # ========================================================================

    Test-Pattern `
        -Name 'FAIL_CLOSED' `
        -Pattern '(?i)FAIL.?CLOSED|FAIL_CLOSED' `
        -Category 'FAIL_CLOSED' `
        -StatusWhenFound 'PASS' `
        -FoundDescription 'FAIL-CLOSED détecté :'

    Test-Pattern `
        -Name 'ERROR_ACTION_STOP' `
        -Pattern '(?i)-ErrorAction\s+Stop' `
        -Category 'FAIL_CLOSED' `
        -StatusWhenFound 'PASS' `
        -FoundDescription 'ErrorAction Stop détecté :'

    Test-Pattern `
        -Name 'STRICT_MODE' `
        -Pattern '(?i)Set-StrictMode\s+-Version' `
        -Category 'HARDENING' `
        -StatusWhenFound 'PASS' `
        -FoundDescription 'StrictMode détecté :'

    Test-Pattern `
        -Name 'THROW' `
        -Pattern '(?i)\bthrow\b' `
        -Category 'FAIL_CLOSED' `
        -StatusWhenFound 'PASS' `
        -FoundDescription 'Throw détecté :'

    # ========================================================================
    # 12 — INTÉGRITÉ / CRYPTO
    # ========================================================================

    Test-Pattern `
        -Name 'SHA256' `
        -Pattern '(?i)SHA256|SHA-256|Get-FileHash' `
        -Category 'INTEGRITY' `
        -StatusWhenFound 'PASS' `
        -FoundDescription 'SHA-256 détecté :'

    Test-Pattern `
        -Name 'HMAC' `
        -Pattern '(?i)\bHMAC\b|HMACSHA256|HMACSHA512' `
        -Category 'CRYPTOGRAPHY' `
        -StatusWhenFound 'PASS' `
        -FoundDescription 'HMAC détecté :'

    Test-Pattern `
        -Name 'SIGNATURE' `
        -Pattern '(?i)VerifySignature|\bSignature\b|\bSigned\b' `
        -Category 'CRYPTOGRAPHY' `
        -StatusWhenFound 'PASS' `
        -FoundDescription 'Signature/vérification détectée :'

    # ========================================================================
    # 13 — SECRETS
    # ========================================================================

    Test-Pattern `
        -Name 'ENV_SECRET_REFERENCE' `
        -Pattern '(?i)\$env:[A-Za-z0-9_]*(SECRET|KEY|TOKEN|PASSWORD)' `
        -Category 'SECRETS' `
        -StatusWhenFound 'INFO' `
            -FoundDescription "Référence à un secret d'environnement :"

    # ========================================================================
    # 14 — OBFUSCATION
    # ========================================================================

    Test-Pattern `
        -Name 'BASE64' `
        -Pattern '(?i)FromBase64String|ToBase64String' `
        -Category 'OBFUSCATION' `
        -StatusWhenFound 'WARN' `
        -FoundDescription 'Base64 détecté :'

    Test-Pattern `
        -Name 'REFLECTION' `
        -Pattern '(?i)System\.Reflection|\.Reflection\b' `
        -Category 'OBFUSCATION' `
        -StatusWhenFound 'WARN' `
        -FoundDescription 'Reflection détectée :'

    # ========================================================================
    # 15 — SYNTHÈSE
    # ========================================================================

    $PassCount = @(
        $Results | Where-Object { $_.Status -eq 'PASS' }
    ).Count

    $WarnCount = @(
        $Results | Where-Object { $_.Status -eq 'WARN' }
    ).Count

    $FailCount = @(
        $Results | Where-Object { $_.Status -eq 'FAIL' }
    ).Count

    $InfoCount = @(
        $Results | Where-Object { $_.Status -eq 'INFO' }
    ).Count

    if ($FailCount -gt 0) {

        $Verdict = 'FORENSIC_FAIL'
        $VerdictColor = 'Red'

    }
    elseif ($WarnCount -gt 0) {

        $Verdict = 'FORENSIC_REVIEW_REQUIRED'
        $VerdictColor = 'Yellow'

    }
    else {

        $Verdict = 'FORENSIC_PASS'
        $VerdictColor = 'Green'
    }

    $EndedAt = Get-Date

    # ========================================================================
    # 16 — RAPPORT JSON
    # ========================================================================

    if (-not (Test-Path -LiteralPath $ReportDirectory -PathType Container)) {

        New-Item `
            -ItemType Directory `
            -Path $ReportDirectory `
            -Force `
            -ErrorAction Stop |
            Out-Null
    }

    $Report = [ordered]@{
        Engine            = 'E-ZZIO'
        Validation        = 'FORENSIC_STATIC'
        Version           = '1.1.1'
        Mode              = 'READ_ONLY'
        ExecutionOfTarget = $false
        MutationOfTarget  = $false
        Target            = $Target
        SHA256            = $Sha256
        TargetSizeBytes   = $FileInfo.Length
        StartedAt         = $StartedAt.ToString('o')
        EndedAt           = $EndedAt.ToString('o')
        ASTErrors         = $AstErrorArray.Count
        CommandCount      = $CommandNodes.Count
        FunctionCount     = $FunctionNodes.Count
        TryCount          = $TryNodes.Count
        IfCount           = $IfNodes.Count
        ThrowCount        = $ThrowNodes.Count
        PassCount         = $PassCount
        WarnCount         = $WarnCount
        FailCount         = $FailCount
        InfoCount         = $InfoCount
        Verdict           = $Verdict
        Results           = @($Results)
    }

    $Report |
        ConvertTo-Json -Depth 8 |
        Set-Content `
            -LiteralPath $ReportJson `
            -Encoding UTF8 `
            -ErrorAction Stop

    # ========================================================================
    # 17 — RAPPORT TXT
    # ========================================================================

    $Text = [System.Collections.Generic.List[string]]::new()

    `$Text.Add("============================================================")
    `$Text.Add("E-ZZIO — VALIDATION FORENSIC STATIQUE v1.1.1")
    `$Text.Add("============================================================")
    `$Text.Add("")
    `$Text.Add("MODE                : READ-ONLY")
    `$Text.Add("EXECUTION CIBLE     : FALSE")
    `$Text.Add("MUTATION CIBLE      : FALSE")
    $Text.Add("CIBLE               : $Target")
    $Text.Add("TAILLE              : $($FileInfo.Length) octets")
    $Text.Add("SHA-256             : $Sha256")
    $Text.Add("AST ERRORS          : $($AstErrorArray.Count)")
    $Text.Add("COMMANDES AST       : $($CommandNodes.Count)")
    $Text.Add("FONCTIONS AST       : $($FunctionNodes.Count)")
    $Text.Add("TRY AST             : $($TryNodes.Count)")
    $Text.Add("IF AST              : $($IfNodes.Count)")
    $Text.Add("THROW AST           : $($ThrowNodes.Count)")
    `$Text.Add("")
    $Text.Add("PASS                : $PassCount")
    $Text.Add("WARN                : $WarnCount")
    $Text.Add("FAIL                : $FailCount")
    $Text.Add("INFO                : $InfoCount")
    `$Text.Add("")
    $Text.Add("VERDICT             : $Verdict")
    `$Text.Add("")
    `$Text.Add("------------------------------------------------------------")
    `$Text.Add("DETAILS")
    `$Text.Add("------------------------------------------------------------")

    foreach ($Result in $Results) {

        $Text.Add(
            "[{0}] {1}/{2} | Count={3} | {4}" -f
            $Result.Status,
            $Result.Category,
            $Result.Name,
            $Result.Count,
            $Result.Details
        )
    }

    `$Text.Add("")
    `$Text.Add("============================================================")
    `$Text.Add("FIN FORENSIC")
    `$Text.Add("============================================================")

    $Text |
        Set-Content `
            -LiteralPath $ReportTxt `
            -Encoding UTF8 `
            -ErrorAction Stop

    # ========================================================================
    # 18 — SORTIE
    # ========================================================================

    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host " RÉSULTAT FORENSIC STATIQUE" -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Cible       : $Target"
    Write-Host "SHA-256     : $Sha256"
    Write-Host ""
    Write-Host "AST Errors  : $($AstErrorArray.Count)"
    Write-Host "PASS        : $PassCount"
    Write-Host "WARN        : $WarnCount"
    Write-Host "FAIL        : $FailCount"
    Write-Host "INFO        : $InfoCount"
    Write-Host ""

    Write-Host "VERDICT : $Verdict" -ForegroundColor $VerdictColor

    Write-Host ""
    Write-Host "Rapport TXT  : $ReportTxt"
    Write-Host "Rapport JSON : $ReportJson"
    Write-Host ""

    Write-Host "============================================================" -ForegroundColor Cyan
    if ($FailCount -gt 0) {
        Write-Host ""
        Write-Host "[FAIL-CLOSED] Analyse bloquante." -ForegroundColor Red
        Write-Host "[FAIL-CLOSED] NE PAS executer la cible." -ForegroundColor Red
        exit 10
    }

    if ($WarnCount -gt 0) {
        Write-Host ""
        Write-Host "[REVIEW REQUIRED] Analyse contextuelle necessaire." -ForegroundColor Yellow
        Write-Host "[PASS] La cible n a PAS ete executee." -ForegroundColor Green
        exit 20
    }

    Write-Host ""
    Write-Host "[PASS] Aucun FAIL forensic." -ForegroundColor Green
    Write-Host "[PASS] La cible n a PAS ete executee." -ForegroundColor Green
    exit 0
}
