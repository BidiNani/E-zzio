#Requires -Version 7.0

<#
.SYNOPSIS
    E-ZZIO — VALIDATION FORENSIC STATIQUE v1.1.6

.DESCRIPTION
    Validateur PowerShell READ-ONLY de niveau forensic.

    Séquence impérative :
      1. SELF PATH / SELF FILE / SELF SHA-256
      2. SELF AST — BLOQUANT
      3. TARGET EXISTENCE / TARGET SHA-256
      4. TARGET AST — BLOQUANT
      5. AST STRUCTURE FORENSIC
      6. MUTATION FORENSIC CONTEXTUALISÉE PAR AST
      7. STATIC PATTERN FORENSIC
      8. TARGET-MUTATION PROOF
      9. RAPPORT TXT + JSON
     10. VERDICT FAIL-CLOSED

    PRINCIPES :
      - La cible n'est jamais exécutée.
      - ParseFile() est utilisé uniquement pour l'analyse syntaxique.
      - SELF AST doit être valide avant toute analyse forensic de la cible.
      - Une primitive filesystem hors cible n'est plus automatiquement un WARN.
      - Une primitive qui référence explicitement la cible est FAIL.
      - Une primitive dont la destination est indéterminable est WARN.
      - Les écritures du validateur dans son propre répertoire de rapport
        ne constituent pas une mutation de la cible.
      - Aucun auto-correctif de la cible.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$TargetPath,

    [Parameter(Mandatory = $false)]
    [ValidateNotNullOrEmpty()]
    [string]$ProjectRoot = 'G:\AI\E-zzio',

    [Parameter(Mandatory = $false)]
    [string]$ReportDirectory = '',

    [Parameter(Mandatory = $false)]
    [switch]$PauseOnExit
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$script:EngineVersion = '1.1.6'
$script:Results = [System.Collections.Generic.List[object]]::new()

function Add-Result {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$Category,

        [Parameter(Mandatory = $true)]
        [string]$Name,

        [Parameter(Mandatory = $true)]
        [ValidateSet('PASS','WARN','FAIL','INFO')]
        [string]$Status,

        [Parameter(Mandatory = $true)]
        [int]$Count,

        [Parameter(Mandatory = $true)]
        [string]$Details
    )

    $script:Results.Add([pscustomobject][ordered]@{
        Category = $Category
        Name     = $Name
        Status   = $Status
        Count    = $Count
        Details  = $Details
    })
}

function Get-NormalizedFullPath {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    return [System.IO.Path]::GetFullPath(
        [Environment]::ExpandEnvironmentVariables($Path)
    )
}

function Test-PathEqual {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$Left,

        [Parameter(Mandatory = $true)]
        [string]$Right
    )

    try {
        $leftFull  = Get-NormalizedFullPath -Path $Left
        $rightFull = Get-NormalizedFullPath -Path $Right

        return [string]::Equals(
            $leftFull.TrimEnd('\'),
            $rightFull.TrimEnd('\'),
            [System.StringComparison]::OrdinalIgnoreCase
        )
    }
    catch {
        return $false
    }
}

function Get-CommandNameFromAst {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [System.Management.Automation.Language.CommandAst]$CommandAst
    )

    if ($CommandAst.CommandElements.Count -lt 1) {
        return ''
    }

    $first = $CommandAst.CommandElements[0]

    if ($first -is [System.Management.Automation.Language.StringConstantExpressionAst]) {
        return [string]$first.Value
    }

    if ($first -is [System.Management.Automation.Language.CommandParameterAst]) {
        return ''
    }

    return [string]$first.Extent.Text
}

function Get-AstCommandText {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [System.Management.Automation.Language.CommandAst]$CommandAst
    )

    return $CommandAst.Extent.Text.Trim()
}

function Test-CommandReferencesTarget {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [System.Management.Automation.Language.CommandAst]$CommandAst,

        [Parameter(Mandatory = $true)]
        [string]$TargetFullPath
    )

    $text = Get-AstCommandText -CommandAst $CommandAst

    # Direct variable reference: the analyzed target is explicitly supplied.
    if ($text -match '(?i)\$TargetPath\b') {
        return $true
    }

    # Exact normalized target path, including quoted/unquoted forms.
    $normalizedText = $text.Replace('/', '\')

    if (
        $normalizedText.IndexOf(
            $TargetFullPath.Replace('/', '\'),
            [System.StringComparison]::OrdinalIgnoreCase
        ) -ge 0
    ) {
        return $true
    }

    $targetLeaf = [System.IO.Path]::GetFileName($TargetFullPath)

    if (
        -not [string]::IsNullOrWhiteSpace($targetLeaf) -and
        $text -match [regex]::Escape($targetLeaf)
    ) {
        return $true
    }

    return $false
}

function Get-MutationClassification {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [System.Management.Automation.Language.CommandAst]$CommandAst,

        [Parameter(Mandatory = $true)]
        [string]$TargetFullPath
    )

    $commandName = Get-CommandNameFromAst -CommandAst $CommandAst
    $text = Get-AstCommandText -CommandAst $CommandAst

    if (Test-CommandReferencesTarget -CommandAst $CommandAst -TargetFullPath $TargetFullPath) {
        return [pscustomobject]@{
            Classification = 'TARGET_MUTATION'
            Status         = 'FAIL'
            Reason         = "La primitive $commandName référence explicitement la cible analysée."
            Command        = $text
        }
    }

    # Dynamic path expressions make destination proof impossible.
    if (
        $text -match '(?i)\$\{?[A-Za-z_][A-Za-z0-9_]*\}?'
    ) {
        return [pscustomobject]@{
            Classification = 'UNKNOWN_DESTINATION'
            Status         = 'WARN'
            Reason         = "Destination dynamique potentiellement inconnue pour $commandName."
            Command        = $text
        }
    }

    return [pscustomobject]@{
        Classification = 'EXTERNAL_MUTATION'
        Status         = 'INFO'
        Reason         = "Primitive $commandName détectée, sans référence identifiable à la cible."
        Command        = $text
    }
}

function Add-AstPatternResult {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,

        [Parameter(Mandatory = $true)]
        [string]$Category,

        [Parameter(Mandatory = $true)]
        [System.Management.Automation.Language.Ast]$RootAst,

        [Parameter(Mandatory = $true)]
        [scriptblock]$Predicate,

        [Parameter(Mandatory = $true)]
        [ValidateSet('PASS','WARN','FAIL','INFO')]
        [string]$FoundStatus,

        [Parameter(Mandatory = $true)]
        [string]$FoundDescription
    )

    $nodes = @($RootAst.FindAll($Predicate, $true))

    if ($nodes.Count -eq 0) {
        Add-Result -Category $Category -Name $Name -Status 'PASS' -Count 0 `
            -Details 'Aucune occurrence AST détectée.'
        return $nodes
    }

    $preview = foreach ($node in ($nodes | Select-Object -First 20)) {
        "L$($node.Extent.StartLineNumber): $($node.Extent.Text.Trim())"
    }

    Add-Result -Category $Category -Name $Name -Status $FoundStatus -Count $nodes.Count `
        -Details (($FoundDescription + ' ' + ($preview -join ' | ')).Trim())

    return $nodes
}

function Invoke-ForensicEngine {
    [CmdletBinding()]
    param()

    $startedAt = [DateTime]::UtcNow
    $exitCode = 99
    $verdict = 'ENGINE_CRASH'
    $verdictColor = 'Red'

    $validatorPath = $PSCommandPath

    if ([string]::IsNullOrWhiteSpace($validatorPath)) {
        Write-Host '[FAIL-CLOSED] PSCommandPath absent.' -ForegroundColor Red
        return 30
    }

    try {
        $validatorPath = Get-NormalizedFullPath -Path $validatorPath
        $targetFullPath = Get-NormalizedFullPath -Path $TargetPath
        $projectFullPath = Get-NormalizedFullPath -Path $ProjectRoot

        if ([string]::IsNullOrWhiteSpace($ReportDirectory)) {
            $reportDirectoryFull = Join-Path $projectFullPath '_forensic\Validation'
        }
        else {
            $reportDirectoryFull = Get-NormalizedFullPath -Path $ReportDirectory
        }

        Write-Host ''
        Write-Host '============================================================' -ForegroundColor Cyan
        Write-Host " E-ZZIO — VALIDATION FORENSIC STATIQUE v$script:EngineVersion" -ForegroundColor Cyan
        Write-Host '============================================================' -ForegroundColor Cyan
        Write-Host ''
        Write-Host 'MODE : READ-ONLY TARGET / NO EXECUTION / FAIL-CLOSED' -ForegroundColor Yellow
        Write-Host ''
        Write-Host "Projet  : $projectFullPath"
        Write-Host "Cible   : $targetFullPath"
        Write-Host "Self    : $validatorPath"
        Write-Host ''

        # =====================================================================
        # 1 — SELF FILE + SELF SHA
        # =====================================================================
        if (-not (Test-Path -LiteralPath $validatorPath -PathType Leaf)) {
            Write-Host '[FAIL-CLOSED] Validateur introuvable.' -ForegroundColor Red
            return 30
        }

        $validatorInfo = Get-Item -LiteralPath $validatorPath -Force -ErrorAction Stop

        if ($validatorInfo.Length -le 0) {
            Write-Host '[FAIL-CLOSED] Validateur vide.' -ForegroundColor Red
            return 30
        }

        $validatorSha256 = (
            Get-FileHash -LiteralPath $validatorPath -Algorithm SHA256 -ErrorAction Stop
        ).Hash

        Add-Result -Category 'SELF' -Name 'SELF_FILE' -Status 'PASS' -Count 1 `
            -Details "Validateur accessible : $validatorPath"

        Add-Result -Category 'SELF_INTEGRITY' -Name 'SELF_SHA256' -Status 'PASS' -Count 1 `
            -Details $validatorSha256

        # =====================================================================
        # 2 — SELF AST — BLOQUANT AVANT TOUT FORENSIC CIBLE
        # =====================================================================
        Write-Host '============================================================' -ForegroundColor Cyan
        Write-Host ' 1/2 — SELF AST VALIDATION — GATE BLOQUANTE' -ForegroundColor Cyan
        Write-Host '============================================================' -ForegroundColor Cyan

        $selfTokens = $null
        $selfErrors = $null

        $selfAst = [System.Management.Automation.Language.Parser]::ParseFile(
            $validatorPath,
            [ref]$selfTokens,
            [ref]$selfErrors
        )

        $selfErrorArray = @($selfErrors)

        Write-Host "AST Errors : $($selfErrorArray.Count)"

        if ($selfErrorArray.Count -gt 0) {
            foreach ($err in $selfErrorArray) {
                Write-Host (
                    "L$($err.Extent.StartLineNumber):C$($err.Extent.StartColumnNumber) : $($err.Message)"
                ) -ForegroundColor Red
            }

            Add-Result -Category 'SELF_AST' -Name 'SELF_SYNTAX' -Status 'FAIL' `
                -Count $selfErrorArray.Count `
                -Details 'Le validateur possède des erreurs AST. Aucun forensic cible autorisé.'

            Write-Host '[FAIL-CLOSED] SELF AST INVALID — FORENSIC CIBLE BLOQUÉ' -ForegroundColor Red
            return 30
        }

        Add-Result -Category 'SELF_AST' -Name 'SELF_SYNTAX' -Status 'PASS' -Count 0 `
            -Details 'AST du validateur = 0 erreur.'

        Write-Host '[PASS] SELF AST = 0 erreur' -ForegroundColor Green
        Write-Host ''

        # =====================================================================
        # 3 — PROJECT ROOT
        # =====================================================================
        if (-not (Test-Path -LiteralPath $projectFullPath -PathType Container)) {
            Add-Result -Category 'ENVIRONMENT' -Name 'PROJECT_ROOT' -Status 'FAIL' -Count 1 `
                -Details "Projet introuvable : $projectFullPath"
            Write-Host '[FAIL-CLOSED] PROJECT ROOT introuvable.' -ForegroundColor Red
            return 32
        }

        Add-Result -Category 'ENVIRONMENT' -Name 'PROJECT_ROOT' -Status 'PASS' -Count 1 `
            -Details "Projet accessible : $projectFullPath"

        # =====================================================================
        # 4 — TARGET EXISTENCE + SHA
        # =====================================================================
        if (-not (Test-Path -LiteralPath $targetFullPath -PathType Leaf)) {
            Add-Result -Category 'TARGET' -Name 'TARGET_EXISTS' -Status 'FAIL' -Count 1 `
                -Details "Cible introuvable : $targetFullPath"
            Write-Host '[FAIL-CLOSED] Cible introuvable.' -ForegroundColor Red
            return 31
        }

        $targetInfo = Get-Item -LiteralPath $targetFullPath -Force -ErrorAction Stop

        if ($targetInfo.Length -le 0) {
            Add-Result -Category 'TARGET' -Name 'TARGET_SIZE' -Status 'FAIL' -Count 1 `
                -Details 'La cible est vide.'
            Write-Host '[FAIL-CLOSED] Cible vide.' -ForegroundColor Red
            return 31
        }

        $targetSha256 = (
            Get-FileHash -LiteralPath $targetFullPath -Algorithm SHA256 -ErrorAction Stop
        ).Hash

        Add-Result -Category 'TARGET' -Name 'TARGET_EXISTS' -Status 'PASS' -Count 1 `
            -Details "Cible accessible : $targetFullPath"

        Add-Result -Category 'INTEGRITY' -Name 'TARGET_SHA256' -Status 'PASS' -Count 1 `
            -Details $targetSha256

        # =====================================================================
        # 5 — TARGET AST — BLOQUANT
        # =====================================================================
        Write-Host '============================================================' -ForegroundColor Cyan
        Write-Host ' 2/2 — TARGET AST VALIDATION — GATE BLOQUANTE' -ForegroundColor Cyan
        Write-Host '============================================================' -ForegroundColor Cyan

        $targetTokens = $null
        $targetErrors = $null

        $targetAst = [System.Management.Automation.Language.Parser]::ParseFile(
            $targetFullPath,
            [ref]$targetTokens,
            [ref]$targetErrors
        )

        $targetErrorArray = @($targetErrors)

        Write-Host "AST Errors : $($targetErrorArray.Count)"

        if ($targetErrorArray.Count -gt 0) {
            foreach ($err in $targetErrorArray) {
                Write-Host (
                    "L$($err.Extent.StartLineNumber):C$($err.Extent.StartColumnNumber) : $($err.Message)"
                ) -ForegroundColor Red
            }

            Add-Result -Category 'TARGET_AST' -Name 'TARGET_SYNTAX' -Status 'FAIL' `
                -Count $targetErrorArray.Count `
                -Details 'La cible possède des erreurs AST. Forensic bloqué.'

            Write-Host '[FAIL-CLOSED] TARGET AST INVALID — FORENSIC BLOQUÉ' -ForegroundColor Red
            return 31
        }

        Add-Result -Category 'TARGET_AST' -Name 'TARGET_SYNTAX' -Status 'PASS' -Count 0 `
            -Details 'AST de la cible = 0 erreur.'

        Write-Host '[PASS] TARGET AST = 0 erreur' -ForegroundColor Green
        Write-Host ''

        # =====================================================================
        # 6 — STRUCTURE AST
        # =====================================================================
        $commandNodes = @(
            $targetAst.FindAll({
                param($n)
                $n -is [System.Management.Automation.Language.CommandAst]
            }, $true)
        )

        $functionNodes = @(
            $targetAst.FindAll({
                param($n)
                $n -is [System.Management.Automation.Language.FunctionDefinitionAst]
            }, $true)
        )

        $throwNodes = @(
            $targetAst.FindAll({
                param($n)
                $n -is [System.Management.Automation.Language.ThrowStatementAst]
            }, $true)
        )

        $tryNodes = @(
            $targetAst.FindAll({
                param($n)
                $n -is [System.Management.Automation.Language.TryStatementAst]
            }, $true)
        )

        $ifNodes = @(
            $targetAst.FindAll({
                param($n)
                $n -is [System.Management.Automation.Language.IfStatementAst]
            }, $true)
        )

        $assignmentNodes = @(
            $targetAst.FindAll({
                param($n)
                $n -is [System.Management.Automation.Language.AssignmentStatementAst]
            }, $true)
        )

        Add-Result -Category 'STRUCTURE' -Name 'COMMANDS' -Status 'INFO' `
            -Count $commandNodes.Count -Details "Commandes AST : $($commandNodes.Count)"

        Add-Result -Category 'STRUCTURE' -Name 'FUNCTIONS' -Status 'INFO' `
            -Count $functionNodes.Count -Details "Fonctions AST : $($functionNodes.Count)"

        Add-Result -Category 'STRUCTURE' -Name 'THROW' -Status 'INFO' `
            -Count $throwNodes.Count -Details "Throws AST : $($throwNodes.Count)"

        Add-Result -Category 'STRUCTURE' -Name 'TRY' -Status 'INFO' `
            -Count $tryNodes.Count -Details "Try AST : $($tryNodes.Count)"

        Add-Result -Category 'STRUCTURE' -Name 'IF' -Status 'INFO' `
            -Count $ifNodes.Count -Details "If AST : $($ifNodes.Count)"

        Add-Result -Category 'STRUCTURE' -Name 'ASSIGNMENTS' -Status 'INFO' `
            -Count $assignmentNodes.Count -Details "Assignments AST : $($assignmentNodes.Count)"

        # =====================================================================
        # 7 — DYNAMIC EXECUTION / EXTERNAL EXECUTION
        # =====================================================================
        $invokeExpressionNodes = @(
            $targetAst.FindAll({
                param($n)
                $n -is [System.Management.Automation.Language.CommandAst] -and
                ((Get-CommandNameFromAst -CommandAst $n) -match '^(?i:Invoke-Expression|iex)$')
            }, $true)
        )

        if ($invokeExpressionNodes.Count -gt 0) {
            Add-Result -Category 'EXECUTION' -Name 'INVOKE_EXPRESSION' -Status 'FAIL' `
                -Count $invokeExpressionNodes.Count `
                -Details (($invokeExpressionNodes | Select-Object -First 20 | ForEach-Object {
                    "L$($_.Extent.StartLineNumber): $($_.Extent.Text.Trim())"
                }) -join ' | ')
        }
        else {
            Add-Result -Category 'EXECUTION' -Name 'INVOKE_EXPRESSION' -Status 'PASS' -Count 0 `
                -Details 'Aucune invocation dynamique Invoke-Expression/iex.'
        }

        $startProcessNodes = @(
            $targetAst.FindAll({
                param($n)
                $n -is [System.Management.Automation.Language.CommandAst] -and
                ((Get-CommandNameFromAst -CommandAst $n) -match '^(?i:Start-Process)$')
            }, $true)
        )

        if ($startProcessNodes.Count -gt 0) {
            Add-Result -Category 'EXECUTION' -Name 'START_PROCESS' -Status 'WARN' `
                -Count $startProcessNodes.Count `
                -Details (($startProcessNodes | Select-Object -First 20 | ForEach-Object {
                    "L$($_.Extent.StartLineNumber): $($_.Extent.Text.Trim())"
                }) -join ' | ')
        }
        else {
            Add-Result -Category 'EXECUTION' -Name 'START_PROCESS' -Status 'PASS' -Count 0 `
                -Details 'Aucun Start-Process.'
        }

        # =====================================================================
        # 8 — CONTEXTUALIZED FILESYSTEM MUTATION FORENSICS
        # =====================================================================
        $mutationCommandNames = @(
            'New-Item',
            'Remove-Item',
            'Move-Item',
            'Copy-Item',
            'Rename-Item',
            'Set-Content',
            'Add-Content',
            'Clear-Content',
            'Out-File'
        )

        $mutationNodes = @(
            $commandNodes | Where-Object {
                $name = Get-CommandNameFromAst -CommandAst $_
                $mutationCommandNames -contains $name
            }
        )

        $targetMutationNodes = [System.Collections.Generic.List[object]]::new()
        $unknownMutationNodes = [System.Collections.Generic.List[object]]::new()
        $externalMutationNodes = [System.Collections.Generic.List[object]]::new()

        foreach ($mutationNode in $mutationNodes) {
            $classification = Get-MutationClassification `
                -CommandAst $mutationNode `
                -TargetFullPath $targetFullPath

            switch ($classification.Classification) {
                'TARGET_MUTATION' {
                    $targetMutationNodes.Add($classification)
                }
                'UNKNOWN_DESTINATION' {
                    $unknownMutationNodes.Add($classification)
                }
                'EXTERNAL_MUTATION' {
                    $externalMutationNodes.Add($classification)
                }
            }
        }

        if ($targetMutationNodes.Count -gt 0) {
            $details = ($targetMutationNodes | Select-Object -First 20 | ForEach-Object {
                "L$($_.Command.Split([Environment]::NewLine)[0])"
            }) -join ' | '

            Add-Result -Category 'MUTATION' -Name 'TARGET_MUTATION' -Status 'FAIL' `
                -Count $targetMutationNodes.Count `
                -Details 'Une primitive de mutation référence explicitement la cible.'
        }
        else {
            Add-Result -Category 'MUTATION' -Name 'TARGET_MUTATION' -Status 'PASS' -Count 0 `
                -Details 'Aucune primitive de mutation AST ne référence explicitement la cible.'
        }

        if ($unknownMutationNodes.Count -gt 0) {
            $preview = ($unknownMutationNodes | Select-Object -First 20 | ForEach-Object {
                $_.Command
            }) -join ' | '

            Add-Result -Category 'MUTATION' -Name 'UNKNOWN_DESTINATION' -Status 'WARN' `
                -Count $unknownMutationNodes.Count `
                -Details "Destination dynamique non prouvable : $preview"
        }
        else {
            Add-Result -Category 'MUTATION' -Name 'UNKNOWN_DESTINATION' -Status 'PASS' -Count 0 `
                -Details 'Aucune destination dynamique indéterminable.'
        }

        if ($externalMutationNodes.Count -gt 0) {
            $preview = ($externalMutationNodes | Select-Object -First 20 | ForEach-Object {
                "L$($mutationNodes | Where-Object { $_.Extent.Text.Trim() -eq $_.Command } | Select-Object -First 1)"
                $_.Command
            }) -join ' | '

            Add-Result -Category 'MUTATION' -Name 'EXTERNAL_MUTATION' -Status 'INFO' `
                -Count $externalMutationNodes.Count `
                -Details 'Primitives filesystem détectées mais aucune référence explicite à la cible.'
        }
        else {
            Add-Result -Category 'MUTATION' -Name 'EXTERNAL_MUTATION' -Status 'INFO' -Count 0 `
                -Details 'Aucune primitive filesystem hors cible détectée.'
        }

        # =====================================================================
        # 9 — REDIRECTIONS DE FICHIER
        # =====================================================================
        $redirectionNodes = @(
            $targetAst.FindAll({
                param($n)
                $n -is [System.Management.Automation.Language.FileRedirectionAst]
            }, $true)
        )

        $targetRedirectionCount = 0
        $unknownRedirectionCount = 0

        foreach ($redir in $redirectionNodes) {
            $text = $redir.Extent.Text

            if (
                $text -match '(?i)\$TargetPath\b' -or
                $text.Replace('/','\').IndexOf(
                    $targetFullPath.Replace('/','\'),
                    [System.StringComparison]::OrdinalIgnoreCase
                ) -ge 0
            ) {
                $targetRedirectionCount++
            }
            elseif ($text -match '(?i)\$\{?[A-Za-z_][A-Za-z0-9_]*\}?') {
                $unknownRedirectionCount++
            }
        }

        if ($targetRedirectionCount -gt 0) {
            Add-Result -Category 'MUTATION' -Name 'TARGET_REDIRECTION' -Status 'FAIL' `
                -Count $targetRedirectionCount `
                -Details 'Redirection de fichier référant explicitement la cible.'
        }
        else {
            Add-Result -Category 'MUTATION' -Name 'TARGET_REDIRECTION' -Status 'PASS' -Count 0 `
                -Details 'Aucune redirection AST vers la cible.'
        }

        if ($unknownRedirectionCount -gt 0) {
            Add-Result -Category 'MUTATION' -Name 'UNKNOWN_REDIRECTION' -Status 'WARN' `
                -Count $unknownRedirectionCount `
                -Details 'Redirection vers une destination dynamique non déterminable.'
        }
        else {
            Add-Result -Category 'MUTATION' -Name 'UNKNOWN_REDIRECTION' -Status 'PASS' -Count 0 `
                -Details 'Aucune redirection dynamique indéterminable.'
        }

        # =====================================================================
        # 10 — NETWORK
        # =====================================================================
        $networkNames = @(
            'Invoke-WebRequest',
            'iwr',
            'Invoke-RestMethod',
            'irm'
        )

        $networkNodes = @(
            $commandNodes | Where-Object {
                $networkNames -contains (Get-CommandNameFromAst -CommandAst $_)
            }
        )

        if ($networkNodes.Count -gt 0) {
            Add-Result -Category 'NETWORK' -Name 'NETWORK_COMMANDS' -Status 'WARN' `
                -Count $networkNodes.Count `
                -Details 'Accès réseau PowerShell détecté.'
        }
        else {
            Add-Result -Category 'NETWORK' -Name 'NETWORK_COMMANDS' -Status 'PASS' -Count 0 `
                -Details 'Aucune primitive réseau ciblée détectée.'
        }

        # =====================================================================
        # 11 — CERTIFICATION / PLACEHOLDERS / SECRET REFERENCES
        # =====================================================================
        $text = [System.IO.File]::ReadAllText($targetFullPath)

        if ($text -match '(?im)\bFAKE.?PASS\b|\bFORCED.?PASS\b|\bALWAYS.?PASS\b|\bUNCONDITIONAL.?PASS\b') {
            Add-Result -Category 'CERTIFICATION' -Name 'FAKE_PASS' -Status 'FAIL' -Count 1 `
                -Details 'Motif de faux PASS détecté.'
        }
        else {
            Add-Result -Category 'CERTIFICATION' -Name 'FAKE_PASS' -Status 'PASS' -Count 0 `
                -Details 'Aucun motif de faux PASS détecté.'
        }

        if ($text -match '(?im)\bTODO\b|\bFIXME\b|\bPLACEHOLDER\b|\bTBD\b') {
            Add-Result -Category 'CERTIFICATION' -Name 'PLACEHOLDER' -Status 'WARN' -Count 1 `
                -Details 'Marqueur de travail détecté dans le contenu.'
        }
        else {
            Add-Result -Category 'CERTIFICATION' -Name 'PLACEHOLDER' -Status 'PASS' -Count 0 `
                -Details 'Aucun placeholder ciblé détecté.'
        }

        $secretPattern = '(?i)' + '\$' + 'env' + ':' +
            '[A-Za-z0-9_]*' +
            '(SECRET|KEY|TOKEN|PASSWORD)'

        if ($text -match $secretPattern) {
            Add-Result -Category 'SECRETS' -Name 'ENV_SECRET_REFERENCE' -Status 'WARN' -Count 1 `
                -Details 'Référence à une variable environnementale potentiellement secrète détectée.'
        }
        else {
            Add-Result -Category 'SECRETS' -Name 'ENV_SECRET_REFERENCE' -Status 'PASS' -Count 0 `
                -Details 'Aucune référence environnementale secrète ciblée.'
        }

        # =====================================================================
        # 12 — HARDENING / FAIL CLOSED
        # =====================================================================
        if ($text -match '(?i)FAIL.?CLOSED') {
            Add-Result -Category 'HARDENING' -Name 'FAIL_CLOSED' -Status 'PASS' -Count 1 `
                -Details 'Marqueur FAIL-CLOSED détecté.'
        }
        else {
            Add-Result -Category 'HARDENING' -Name 'FAIL_CLOSED' -Status 'WARN' -Count 0 `
                -Details 'Aucun marqueur FAIL-CLOSED détecté.'
        }

        if ($text -match '(?i)Set-StrictMode\s+-Version') {
            Add-Result -Category 'HARDENING' -Name 'STRICT_MODE' -Status 'PASS' -Count 1 `
                -Details 'Set-StrictMode détecté.'
        }
        else {
            Add-Result -Category 'HARDENING' -Name 'STRICT_MODE' -Status 'WARN' -Count 0 `
                -Details 'Set-StrictMode non détecté.'
        }

        if ($text -match '(?i)Get-FileHash\s+.*SHA256|SHA-256|SHA256') {
            Add-Result -Category 'INTEGRITY' -Name 'SHA256_MECHANISM' -Status 'PASS' -Count 1 `
                -Details 'Mécanisme SHA-256 détecté.'
        }
        else {
            Add-Result -Category 'INTEGRITY' -Name 'SHA256_MECHANISM' -Status 'FAIL' -Count 0 `
                -Details 'Mécanisme SHA-256 absent.'
        }

        # =====================================================================
        # 13 — SAFETY PROOFS
        # =====================================================================
        Add-Result -Category 'SAFETY' -Name 'TARGET_EXECUTION' -Status 'PASS' -Count 0 `
            -Details 'Le validateur utilise ParseFile et des scans statiques ; la cible n''est jamais invoquée.'

        Add-Result -Category 'SAFETY' -Name 'TARGET_AUTO_REPAIR' -Status 'PASS' -Count 0 `
            -Details 'Aucun mécanisme de correction automatique de la cible.'

        if ($targetMutationNodes.Count -eq 0 -and $targetRedirectionCount -eq 0) {
            Add-Result -Category 'SAFETY' -Name 'TARGET_MUTATION_PROOF' -Status 'PASS' -Count 0 `
                -Details 'Aucune primitive AST analysée ne démontre une mutation de la cible.'
        }
        else {
            Add-Result -Category 'SAFETY' -Name 'TARGET_MUTATION_PROOF' -Status 'FAIL' `
                -Count ($targetMutationNodes.Count + $targetRedirectionCount) `
                -Details 'Une mutation de la cible est démontrée par l''AST.'
        }

        # =====================================================================
        # 14 — VERDICT
        # =====================================================================
        $passCount = @($script:Results | Where-Object Status -eq 'PASS').Count
        $warnCount = @($script:Results | Where-Object Status -eq 'WARN').Count
        $failCount = @($script:Results | Where-Object Status -eq 'FAIL').Count
        $infoCount = @($script:Results | Where-Object Status -eq 'INFO').Count

        if ($failCount -gt 0) {
            $verdict = 'FORENSIC_FAIL'
            $verdictColor = 'Red'
            $exitCode = 10
        }
        elseif ($warnCount -gt 0) {
            $verdict = 'FORENSIC_REVIEW_REQUIRED'
            $verdictColor = 'Yellow'
            $exitCode = 20
        }
        else {
            $verdict = 'FORENSIC_PASS'
            $verdictColor = 'Green'
            $exitCode = 0
        }

        $endedAt = [DateTime]::UtcNow
        $durationSeconds = ($endedAt - $startedAt).TotalSeconds

        # =====================================================================
        # 15 — REPORT DIRECTORY / REPORTS
        # =====================================================================
        if (-not (Test-Path -LiteralPath $reportDirectoryFull -PathType Container)) {
            New-Item -ItemType Directory -LiteralPath $reportDirectoryFull -Force -ErrorAction Stop |
                Out-Null
        }

        $targetBase = [System.IO.Path]::GetFileNameWithoutExtension($targetFullPath)
        $timestamp = $startedAt.ToString('yyyyMMdd_HHmmss')
        $reportJson = Join-Path $reportDirectoryFull "${targetBase}_${timestamp}_Report.json"
        $reportTxt = Join-Path $reportDirectoryFull "${targetBase}_${timestamp}_Report.txt"

        $report = [ordered]@{
            Engine               = 'E-ZZIO'
            Validation           = 'FORENSIC_STATIC'
            Version              = $script:EngineVersion
            Mode                 = 'READ-ONLY_TARGET'
            ExecutionOfTarget    = $false
            AutoRepairOfTarget   = $false
            SelfAstErrors        = $selfErrorArray.Count
            TargetAstErrors      = $targetErrorArray.Count
            ProjectRoot          = $projectFullPath
            Validator            = $validatorPath
            ValidatorSHA256      = $validatorSha256
            Target              = $targetFullPath
            TargetLengthBytes    = $targetInfo.Length
            TargetLastWriteUTC   = $targetInfo.LastWriteTimeUtc.ToString('o')
            TargetSHA256         = $targetSha256
            StartedAtUTC         = $startedAt.ToString('o')
            EndedAtUTC           = $endedAt.ToString('o')
            DurationSeconds      = [math]::Round($durationSeconds, 3)
            CommandCount         = $commandNodes.Count
            FunctionCount        = $functionNodes.Count
            ThrowCount           = $throwNodes.Count
            TryCount             = $tryNodes.Count
            IfCount              = $ifNodes.Count
            AssignmentCount      = $assignmentNodes.Count
            MutationCommandCount = $mutationNodes.Count
            TargetMutationCount  = $targetMutationNodes.Count
            UnknownMutationCount = $unknownMutationNodes.Count
            TargetRedirectionCount = $targetRedirectionCount
            UnknownRedirectionCount = $unknownRedirectionCount
            PASS                 = $passCount
            WARN                 = $warnCount
            FAIL                 = $failCount
            INFO                 = $infoCount
            Verdict              = $verdict
            ExitCode             = $exitCode
            Results              = @($script:Results)
        }

        $report |
            ConvertTo-Json -Depth 12 |
            Set-Content -LiteralPath $reportJson -Encoding utf8 -ErrorAction Stop

        $txtLines = [System.Collections.Generic.List[string]]::new()

        $txtLines.Add('============================================================')
        $txtLines.Add(" E-ZZIO — VALIDATION FORENSIC STATIQUE v$script:EngineVersion")
        $txtLines.Add('============================================================')
        $txtLines.Add('')
        $txtLines.Add("Mode                : READ-ONLY TARGET")
        $txtLines.Add("Execution cible     : FALSE")
        $txtLines.Add("Auto-réparation     : FALSE")
        $txtLines.Add("Self AST Errors     : $($selfErrorArray.Count)")
        $txtLines.Add("Target AST Errors   : $($targetErrorArray.Count)")
        $txtLines.Add("Projet              : $projectFullPath")
        $txtLines.Add("Validateur          : $validatorPath")
        $txtLines.Add("Validator SHA-256   : $validatorSha256")
        $txtLines.Add("Cible               : $targetFullPath")
        $txtLines.Add("Taille              : $($targetInfo.Length) octets")
        $txtLines.Add("Target SHA-256      : $targetSha256")
        $txtLines.Add("Commandes AST       : $($commandNodes.Count)")
        $txtLines.Add("Fonctions AST       : $($functionNodes.Count)")
        $txtLines.Add("Throws AST          : $($throwNodes.Count)")
        $txtLines.Add("Try AST             : $($tryNodes.Count)")
        $txtLines.Add("If AST              : $($ifNodes.Count)")
        $txtLines.Add("Assignments AST     : $($assignmentNodes.Count)")
        $txtLines.Add("Mutation commands   : $($mutationNodes.Count)")
        $txtLines.Add("Target mutations    : $($targetMutationNodes.Count)")
        $txtLines.Add("Unknown mutations   : $($unknownMutationNodes.Count)")
        $txtLines.Add("Target redirections : $targetRedirectionCount")
        $txtLines.Add("Unknown redirects   : $unknownRedirectionCount")
        $txtLines.Add('')
        $txtLines.Add("PASS                : $passCount")
        $txtLines.Add("WARN                : $warnCount")
        $txtLines.Add("FAIL                : $failCount")
        $txtLines.Add("INFO                : $infoCount")
        $txtLines.Add('')
        $txtLines.Add("VERDICT             : $verdict")
        $txtLines.Add("EXIT CODE           : $exitCode")
        $txtLines.Add('')
        $txtLines.Add('------------------------------------------------------------')
        $txtLines.Add('DETAILS')
        $txtLines.Add('------------------------------------------------------------')

        foreach ($result in $script:Results) {
            $txtLines.Add(
                "[$($result.Status)] $($result.Category)/$($result.Name) " +
                "(Count=$($result.Count)) -> $($result.Details)"
            )
        }

        $txtLines.Add('')
        $txtLines.Add('============================================================')
        $txtLines.Add('FIN FORENSIC')
        $txtLines.Add('============================================================')

        $txtLines |
            Set-Content -LiteralPath $reportTxt -Encoding utf8 -ErrorAction Stop

        # =====================================================================
        # 16 — CONSOLE
        # =====================================================================
        Write-Host ''
        Write-Host '============================================================' -ForegroundColor Cyan
        Write-Host " RÉSULTAT FORENSIC STATIQUE v$script:EngineVersion" -ForegroundColor Cyan
        Write-Host '============================================================' -ForegroundColor Cyan
        Write-Host "Cible       : $targetFullPath"
        Write-Host "SHA-256     : $targetSha256"
        Write-Host ''
        Write-Host "SELF AST    : $($selfErrorArray.Count)"
        Write-Host "TARGET AST  : $($targetErrorArray.Count)"
        Write-Host ''
        Write-Host "MUTATIONS AST        : $($mutationNodes.Count)"
        Write-Host "MUTATIONS CIBLE      : $($targetMutationNodes.Count)"
        Write-Host "MUTATIONS INCONNUES  : $($unknownMutationNodes.Count)"
        Write-Host "REDIRECTIONS CIBLE   : $targetRedirectionCount"
        Write-Host ''
        Write-Host "PASS : $passCount | WARN : $warnCount | FAIL : $failCount | INFO : $infoCount"
        Write-Host ''
        Write-Host "VERDICT : $verdict" -ForegroundColor $verdictColor
        Write-Host ''
        Write-Host "Rapport TXT  : $reportTxt" -ForegroundColor DarkGray
        Write-Host "Rapport JSON : $reportJson" -ForegroundColor DarkGray
        Write-Host '============================================================' -ForegroundColor Cyan

        if ($failCount -gt 0) {
            Write-Host ''
            Write-Host '[FAIL-CLOSED] Anomalie(s) bloquante(s).' -ForegroundColor Red
            Write-Host '[FAIL-CLOSED] La cible n''a PAS été exécutée.' -ForegroundColor Red
        }
        elseif ($warnCount -gt 0) {
            Write-Host ''
            Write-Host '[REVIEW REQUIRED] Une ou plusieurs preuves restent indéterminées.' -ForegroundColor Yellow
            Write-Host '[REVIEW REQUIRED] La cible n''a PAS été exécutée.' -ForegroundColor Yellow
        }
        else {
            Write-Host ''
            Write-Host '[PASS] Aucun FAIL/WARN forensic.' -ForegroundColor Green
            Write-Host '[PASS] SELF AST valide.' -ForegroundColor Green
            Write-Host '[PASS] TARGET AST valide.' -ForegroundColor Green
            Write-Host '[PASS] Aucune mutation de la cible démontrée.' -ForegroundColor Green
            Write-Host '[PASS] La cible n''a PAS été exécutée.' -ForegroundColor Green
        }

        return $exitCode
    }
    catch {
        Write-Host ''
        Write-Host '!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!' -ForegroundColor Red
        Write-Host ' CRASH INATTENDU DU MOTEUR FORENSIC' -ForegroundColor Red
        Write-Host '!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!' -ForegroundColor Red
        Write-Host "Exception : $($_.Exception.Message)" -ForegroundColor Red
        Write-Host '[FAIL-CLOSED] La cible n''a pas été exécutée.' -ForegroundColor Red
        return 99
    }
    finally {
        if ($PauseOnExit) {
            Write-Host ''
            Read-Host 'Appuyez sur Entrée pour fermer'
        }
    }
}

$finalExitCode = Invoke-ForensicEngine
exit $finalExitCode
