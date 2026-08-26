#Requires -Version 7.0

# ============================================================================
# E-ZZIO — STATIC RESOLVER LAB
# Version : 1.1.7.6
# Codename: THE ORACLE — ARRAY + FOREACH + FAIL-CLOSED
#
# MODE :
#   READ-ONLY
#   AST ONLY
#   NO TARGET EXECUTION
#   FAIL-CLOSED
#
# OBJECTIF :
#   Vérifier scientifiquement le moteur de résolution statique.
#
# IMPORTANT :
#   Le corpus est analysé syntaxiquement uniquement.
#   Aucun New-Item du corpus n'est exécuté.
# ============================================================================

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

# ============================================================================
# 0. CONFIGURATION
# ============================================================================

$TargetToMatch = 'G:\AI\E-zzio\EZZIO_Freeze_Certification_v1.1.1.ps1'

$LabPath = $PSCommandPath

# ============================================================================
# 1. CORPUS ADVERSARIAL
# ============================================================================

$TestCode = @'
# 01 — Littéral
$Destination1 = 'G:\AI\E-zzio\logs\x.log'
New-Item -Path $Destination1 -ItemType File

# 02 — Concaténation
$Root = 'G:\AI\E-zzio'
$Destination2 = $Root + '\logs\x.log'
New-Item -Path $Destination2 -ItemType File

# 03 — Join-Path Standard
$RootJoin = 'G:\AI\E-zzio'
$Destination3 = Join-Path $RootJoin 'logs\x.log'
New-Item -Path $Destination3 -ItemType File

# 04 — Dynamique
$Destination4 = Get-DynamicPath
New-Item -Path $Destination4 -ItemType File

# 05 — Argument Dynamique
New-Item -Path $args[0] -ItemType File

# 06 — Cible Exacte
$Destination6 = 'G:\AI\E-zzio\EZZIO_Freeze_Certification_v1.1.1.ps1'
New-Item -Path $Destination6 -ItemType File

# 07 — Piège de Portée
if ($false) {
    $Destination7 = 'C:\fake_malicious.txt'
}

$Destination7 = 'C:\real_safe.txt'
New-Item -Path $Destination7 -ItemType File

# 08 — Ambiguïté Statique
if ($true) {
    $Destination8 = 'C:\path_A.txt'
}
else {
    $Destination8 = 'C:\path_B.txt'
}

New-Item -Path $Destination8 -ItemType File

# 09 — Join-Path Pathologique
$Root9 = 'G:\AI\E-zzio\'
$Destination9 = Join-Path $Root9 '\logs\\x.log'
New-Item -Path $Destination9 -ItemType File

# 10 — Ambiguïté Dynamique
if ((Get-Random) -gt 5) {
    $Destination10 = 'C:\dyn_path_A.txt'
}
else {
    $Destination10 = 'C:\dyn_path_B.txt'
}

New-Item -Path $Destination10 -ItemType File

# 11 — Boucle avec Collection Statique
foreach ($File in @('a.txt', 'b.txt')) {
    $Destination11 = "C:\logs\$File"
    New-Item -Path $Destination11 -ItemType File
}

# 12 — Paramètre Positionnel
$Destination12 = 'G:\AI\E-zzio\positional.txt'
New-Item $Destination12 -ItemType File

# 13 — Chaîne Interpolée Résoluble
$SubDir = 'logs'
$Destination13 = "G:\AI\E-zzio\$SubDir\x.log"
New-Item -Path $Destination13 -ItemType File

# 14 — Chaîne Interpolée Non-Résoluble
$Destination14 = "G:\AI\E-zzio\$env:USERNAME\x.log"
New-Item -Path $Destination14 -ItemType File

# 15 — Index Array Déterministe
$Arr = @('C:\path_arr.txt', 'C:\other.txt')
$Destination15 = $Arr[0]
New-Item -Path $Destination15 -ItemType File
'@

# ============================================================================
# 2. ORACLE DE VÉRITÉ
# ============================================================================

$ExpectedOracle = @(
    'RESOLVED',              # 01
    'RESOLVED',              # 02
    'RESOLVED',              # 03
    'UNRESOLVED',            # 04
    'UNRESOLVED',            # 05
    'RESOLVED_TARGET',       # 06
    'RESOLVED',              # 07
    'UNRESOLVED_CANDIDATES', # 08
    'RESOLVED',              # 09
    'UNRESOLVED_CANDIDATES', # 10
    'UNRESOLVED_CANDIDATES', # 11
    'RESOLVED',              # 12
    'RESOLVED',              # 13
    'UNRESOLVED',            # 14
    'RESOLVED'               # 15
)

# ============================================================================
# 3. OUTILS FORENSIC
# ============================================================================

function New-ResolutionResult {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Status,

        $Value = $null,

        [string]$Confidence = 'NONE',

        [string]$Reason = '',

        [AllowEmptyCollection()]
        [object[]]$Candidates = @()
    )

    $SafeCandidates = @($Candidates)

    return [pscustomobject]@{
        Status     = $Status
        Value      = $Value
        Confidence = $Confidence
        Reason     = $Reason
        Candidates = $SafeCandidates
    }
}

function Test-IsConditionalRelativeTo {
    param(
        [Parameter(Mandatory = $true)]
        $AssignNode,

        [Parameter(Mandatory = $true)]
        $CommandNode
    )

    $Parent = $AssignNode.Parent

    while ($null -ne $Parent -and
           $Parent -isnot [System.Management.Automation.Language.ScriptBlockAst]) {

        if ($Parent -is [System.Management.Automation.Language.IfStatementAst] -or
            $Parent -is [System.Management.Automation.Language.ForEachStatementAst] -or
            $Parent -is [System.Management.Automation.Language.WhileStatementAst]) {

            $FoundCommand = $Parent.Find(
                {
                    param($Node)
                    $Node -eq $CommandNode
                },
                $true
            )

            if (-not $FoundCommand) {
                return $true
            }
        }

        $Parent = $Parent.Parent
    }

    return $false
}

# ============================================================================
# 4. MOTEUR DE RÉSOLUTION AST
# ============================================================================

function Invoke-StaticResolution {
    param(
        [Parameter(Mandatory = $true)]
        $ExpressionAst,

        [Parameter(Mandatory = $true)]
        $RootAst,

        [Parameter(Mandatory = $true)]
        $CommandAst,

        [int]$Depth = 0
    )

    if ($Depth -gt 15) {
        return New-ResolutionResult `
            -Status 'UNRESOLVED' `
            -Confidence 'NONE' `
            -Reason 'DEPTH_LIMIT_REACHED'
    }

    if ($null -eq $ExpressionAst) {
        return New-ResolutionResult `
            -Status 'UNRESOLVED' `
            -Confidence 'NONE' `
            -Reason 'NULL_EXPRESSION_AST'
    }

    # ========================================================================
    # UNWRAPPER
    # ========================================================================

    $Changed = $true

    while ($Changed) {

        $Changed = $false

        if ($ExpressionAst -is [System.Management.Automation.Language.PipelineAst] -and
            @($ExpressionAst.PipelineElements).Count -eq 1) {

            $ExpressionAst = $ExpressionAst.PipelineElements[0]
            $Changed = $true
        }
        elseif ($ExpressionAst -is [System.Management.Automation.Language.CommandExpressionAst]) {

            $ExpressionAst = $ExpressionAst.Expression
            $Changed = $true
        }
        elseif ($ExpressionAst -is [System.Management.Automation.Language.ParenExpressionAst]) {

            $ExpressionAst = $ExpressionAst.Pipeline
            $Changed = $true
        }
    }

    # ========================================================================
    # CAS A — LITTÉRAL
    # ========================================================================

    if ($ExpressionAst -is [System.Management.Automation.Language.StringConstantExpressionAst]) {

        return New-ResolutionResult `
            -Status 'RESOLVED' `
            -Value $ExpressionAst.Value `
            -Confidence 'STATIC_EXACT' `
            -Reason 'LITERAL_VALUE'
    }

    # ========================================================================
    # CAS B — INDEX ARRAY
    # ========================================================================

    if ($ExpressionAst -is [System.Management.Automation.Language.IndexExpressionAst]) {

        $TargetAst = $ExpressionAst.Target
        $IndexAst  = $ExpressionAst.Index

        if ($TargetAst -is [System.Management.Automation.Language.VariableExpressionAst] -and
            $IndexAst -is [System.Management.Automation.Language.ConstantExpressionAst]) {

            $VariableName = $TargetAst.VariablePath.UserPath

            try {
                $IndexValue = [int]$IndexAst.Value
            }
            catch {
                return New-ResolutionResult `
                    -Status 'UNRESOLVED' `
                    -Reason 'NON_INTEGER_ARRAY_INDEX'
            }

            $Assignments = @(
                $RootAst.FindAll(
                    {
                        param($Node)

                        $Node -is [System.Management.Automation.Language.AssignmentStatementAst] -and
                        $Node.Left -is [System.Management.Automation.Language.VariableExpressionAst] -and
                        $Node.Left.VariablePath.UserPath -eq $VariableName -and
                        $Node.Extent.StartOffset -lt $CommandAst.Extent.StartOffset
                    },
                    $true
                )
            )

            $Assignments = @(
                $Assignments |
                    Sort-Object { $_.Extent.StartOffset } -Descending
            )

            if (@($Assignments).Count -gt 0) {

                $LatestAssignment = $Assignments[0]

                $ArrayLiterals = @(
                    $LatestAssignment.Right.FindAll(
                        {
                            param($Node)
                            $Node -is [System.Management.Automation.Language.ArrayLiteralAst]
                        },
                        $true
                    )
                )

                if (@($ArrayLiterals).Count -gt 0) {

                    $Elements = @($ArrayLiterals[0].Elements)

                    if ($IndexValue -ge 0 -and
                        $IndexValue -lt $Elements.Count) {

                        $ElementResult = Invoke-StaticResolution `
                            -ExpressionAst $Elements[$IndexValue] `
                            -RootAst $RootAst `
                            -CommandAst $CommandAst `
                            -Depth ($Depth + 1)

                        if ($ElementResult.Status -eq 'RESOLVED') {

                            $ElementResult.Confidence =
                                'STATIC_ARRAY_INDEX'

                            return $ElementResult
                        }
                    }
                }
            }
        }

        return New-ResolutionResult `
            -Status 'UNRESOLVED' `
            -Reason 'DYNAMIC_INDEX_OR_UNSUPPORTED_ARRAY'
    }

    # ========================================================================
    # CAS C — VARIABLE
    # ========================================================================

    if ($ExpressionAst -is [System.Management.Automation.Language.VariableExpressionAst]) {

        $VariableName = $ExpressionAst.VariablePath.UserPath

        if ($VariableName -match '^(args|_|PSItem|env:.*)$') {

            return New-ResolutionResult `
                -Status 'UNRESOLVED' `
                -Reason 'DYNAMIC_VARIABLE'
        }

        # ====================================================================
        # FOREACH
        # ====================================================================

        $Loops = @(
            $RootAst.FindAll(
                {
                    param($Node)

                    $Node -is [System.Management.Automation.Language.ForEachStatementAst] -and
                    $Node.Variable.VariablePath.UserPath -eq $VariableName -and
                    $Node.Extent.StartOffset -lt $CommandAst.Extent.StartOffset
                },
                $true
            )
        )

        foreach ($Loop in $Loops) {

            $CommandInsideLoop = $Loop.Body.Find(
                {
                    param($Node)
                    $Node -eq $CommandAst
                },
                $true
            )

            if ($CommandInsideLoop) {

                $LoopElements = @(
                    $Loop.Condition.FindAll(
                        {
                            param($Node)

                            $Node -is [System.Management.Automation.Language.ArrayLiteralAst]
                        },
                        $true
                    )
                )

                if (@($LoopElements).Count -gt 0) {

                    $ArrayElements = @($LoopElements[0].Elements)

                    $Candidates = [System.Collections.Generic.List[string]]::new()

                    foreach ($Element in $ArrayElements) {

                        $ElementResult = Invoke-StaticResolution `
                            -ExpressionAst $Element `
                            -RootAst $RootAst `
                            -CommandAst $CommandAst `
                            -Depth ($Depth + 1)

                        if ($ElementResult.Status -eq 'RESOLVED') {
                            [void]$Candidates.Add([string]$ElementResult.Value)
                        }
                    }

                    if ($Candidates.Count -eq $ArrayElements.Count) {

                        return New-ResolutionResult `
                            -Status 'UNRESOLVED' `
                            -Confidence 'STATIC_LOOP_CANDIDATES' `
                            -Reason 'LOOP_VARIABLE' `
                            -Candidates $Candidates.ToArray()
                    }
                }
            }
        }

        # ====================================================================
        # ASSIGNATIONS
        # ====================================================================

        $Assignments = @(
            $RootAst.FindAll(
                {
                    param($Node)

                    $Node -is [System.Management.Automation.Language.AssignmentStatementAst] -and
                    $Node.Left -is [System.Management.Automation.Language.VariableExpressionAst] -and
                    $Node.Left.VariablePath.UserPath -eq $VariableName -and
                    $Node.Extent.StartOffset -lt $CommandAst.Extent.StartOffset
                },
                $true
            )
        )

        $Assignments = @(
            $Assignments |
                Sort-Object { $_.Extent.StartOffset } -Descending
        )

        if (@($Assignments).Count -eq 0) {

            return New-ResolutionResult `
                -Status 'UNRESOLVED' `
                -Reason 'NO_ASSIGNMENT_FOUND'
        }

        $LatestAssignment = $Assignments[0]

        # ====================================================================
        # CONTROL FLOW
        # ====================================================================

        if (Test-IsConditionalRelativeTo `
                -AssignNode $LatestAssignment `
                -CommandNode $CommandAst) {

            $Candidates = [System.Collections.Generic.List[string]]::new()

            foreach ($Assignment in $Assignments) {

                $SubResult = Invoke-StaticResolution `
                    -ExpressionAst $Assignment.Right `
                    -RootAst $RootAst `
                    -CommandAst $CommandAst `
                    -Depth ($Depth + 1)

                if ($SubResult.Status -eq 'RESOLVED' -and
                    -not $Candidates.Contains([string]$SubResult.Value)) {

                    [void]$Candidates.Add([string]$SubResult.Value)
                }
            }

            return New-ResolutionResult `
                -Status 'UNRESOLVED' `
                -Confidence 'NONE' `
                -Reason 'AMBIGUOUS_CONTROL_FLOW' `
                -Candidates $Candidates.ToArray()
        }

        # ====================================================================
        # TRACE
        # ====================================================================

        $Result = Invoke-StaticResolution `
            -ExpressionAst $LatestAssignment.Right `
            -RootAst $RootAst `
            -CommandAst $CommandAst `
            -Depth ($Depth + 1)

        if ($Result.Status -eq 'RESOLVED') {
            $Result.Confidence = 'STATIC_VARIABLE_TRACE'
        }

        return $Result
    }

    # ========================================================================
    # CAS D — EXPANDABLE STRING
    # ========================================================================

    if ($ExpressionAst -is [System.Management.Automation.Language.ExpandableStringExpressionAst]) {

        $BaseCandidates = @([string]$ExpressionAst.Value)
        $ProducedCandidates = $false

        $NestedExpressions = @($ExpressionAst.NestedExpressions)

        foreach ($NestedAst in $NestedExpressions) {

            $NestedResult = Invoke-StaticResolution `
                -ExpressionAst $NestedAst `
                -RootAst $RootAst `
                -CommandAst $CommandAst `
                -Depth ($Depth + 1)

            if ($NestedResult.Status -eq 'RESOLVED') {

                $NewCandidates = [System.Collections.Generic.List[string]]::new()

                foreach ($Candidate in $BaseCandidates) {

                    $Text = [string]$Candidate

                    [void]$NewCandidates.Add(
                        $Text.Replace(
                            $NestedAst.Extent.Text,
                            [string]$NestedResult.Value
                        )
                    )
                }

                $BaseCandidates = $NewCandidates.ToArray()
            }
            else {

                $NestedCandidates = @($NestedResult.Candidates)

                if ($NestedCandidates.Count -gt 0) {

                    $NewCandidates = [System.Collections.Generic.List[string]]::new()

                    foreach ($Candidate in $BaseCandidates) {

                        foreach ($SubCandidate in $NestedCandidates) {

                            [void]$NewCandidates.Add(
                                ([string]$Candidate).Replace(
                                    $NestedAst.Extent.Text,
                                    [string]$SubCandidate
                                )
                            )
                        }
                    }

                    $BaseCandidates = $NewCandidates.ToArray()
                    $ProducedCandidates = $true
                }
                else {

                    return New-ResolutionResult `
                        -Status 'UNRESOLVED' `
                        -Reason 'UNRESOLVED_NESTED_EXPRESSION'
                }
            }
        }

        if (-not $ProducedCandidates -and
            @($BaseCandidates).Count -eq 1) {

            return New-ResolutionResult `
                -Status 'RESOLVED' `
                -Value $BaseCandidates[0] `
                -Confidence 'STATIC_EXPANDABLE_STRING' `
                -Reason 'ALL_NESTED_RESOLVED'
        }

        return New-ResolutionResult `
            -Status 'UNRESOLVED' `
            -Confidence 'EXPANDABLE_STRING_CANDIDATES' `
            -Reason 'MULTIPLE_CANDIDATES_GENERATED' `
            -Candidates $BaseCandidates
    }

    # ========================================================================
    # CAS E — JOIN-PATH
    # ========================================================================

    if ($ExpressionAst -is [System.Management.Automation.Language.CommandAst]) {

        $CommandElements = @($ExpressionAst.CommandElements)

        if ($CommandElements.Count -gt 0) {

            $CommandName = [string]$CommandElements[0].Value

            if ($CommandName -eq 'Join-Path' -and
                $CommandElements.Count -ge 3) {

                $Path1 = Invoke-StaticResolution `
                    -ExpressionAst $CommandElements[1] `
                    -RootAst $RootAst `
                    -CommandAst $CommandAst `
                    -Depth ($Depth + 1)

                $Path2 = Invoke-StaticResolution `
                    -ExpressionAst $CommandElements[2] `
                    -RootAst $RootAst `
                    -CommandAst $CommandAst `
                    -Depth ($Depth + 1)

                if ($Path1.Status -eq 'RESOLVED' -and
                    $Path2.Status -eq 'RESOLVED') {

                    $P1 = ([string]$Path1.Value).TrimEnd('\', '/')
                    $P2 = ([string]$Path2.Value).TrimStart('\', '/')

                    $Combined = $P1 + '\' + $P2

                    $IsUNC = $Combined.StartsWith('\\')

                    $Combined = $Combined -replace '\\+', '\'

                    if ($IsUNC) {
                        $Combined = '\' + $Combined
                    }

                    return New-ResolutionResult `
                        -Status 'RESOLVED' `
                        -Value $Combined `
                        -Confidence 'STATIC_JOIN_PATH_NORMALIZED' `
                        -Reason 'JOIN_PATH_EVALUATED'
                }
            }

            return New-ResolutionResult `
                -Status 'UNRESOLVED' `
                -Reason "DYNAMIC_COMMAND_$CommandName"
        }
    }

    # ========================================================================
    # CAS F — CONCATÉNATION
    # ========================================================================

    if ($ExpressionAst -is [System.Management.Automation.Language.BinaryExpressionAst] -and
        $ExpressionAst.Operator -eq 'Plus') {

        $LeftResult = Invoke-StaticResolution `
            -ExpressionAst $ExpressionAst.Left `
            -RootAst $RootAst `
            -CommandAst $CommandAst `
            -Depth ($Depth + 1)

        $RightResult = Invoke-StaticResolution `
            -ExpressionAst $ExpressionAst.Right `
            -RootAst $RootAst `
            -CommandAst $CommandAst `
            -Depth ($Depth + 1)

        if ($LeftResult.Status -eq 'RESOLVED' -and
            $RightResult.Status -eq 'RESOLVED') {

            return New-ResolutionResult `
                -Status 'RESOLVED' `
                -Value (
                    [string]$LeftResult.Value +
                    [string]$RightResult.Value
                ) `
                -Confidence 'STATIC_CONCATENATION' `
                -Reason 'DETERMINISTIC_CONCAT'
        }

        return New-ResolutionResult `
            -Status 'UNRESOLVED' `
            -Reason 'PARTIAL_CONCATENATION'
    }

    # ========================================================================
    # FALLBACK
    # ========================================================================

    return New-ResolutionResult `
        -Status 'UNRESOLVED' `
        -Reason "UNSUPPORTED_AST_NODE_$($ExpressionAst.GetType().Name)"
}

# ============================================================================
# 5. AUTO-VALIDATION DU PROPRE LABORATOIRE
# ============================================================================

Write-Host ''
Write-Host '============================================================' -ForegroundColor Cyan
Write-Host ' E-ZZIO STATIC RESOLVER LAB v1.1.7.6' -ForegroundColor Cyan
Write-Host ' THE ORACLE — FAIL-CLOSED' -ForegroundColor Cyan
Write-Host '============================================================' -ForegroundColor Cyan
Write-Host ''

$Stats = [ordered]@{
    Total       = 0
    OraclePass  = 0
    OracleFail  = 0
    Exceptions  = 0
    AstErrors   = 0
}

# ============================================================================
# 6. VALIDATION AST DU CORPUS
# ============================================================================

$Tokens = $null
$Errors = $null

$Ast = [System.Management.Automation.Language.Parser]::ParseInput(
    $TestCode,
    [ref]$Tokens,
    [ref]$Errors
)

$AstErrors = @($Errors)

if ($AstErrors.Count -gt 0) {

    Write-Host 'CORPUS AST : FAIL' -ForegroundColor Red

    foreach ($AstError in $AstErrors) {
        Write-Host "  $($AstError.Message)" -ForegroundColor Red
    }

    $Stats.AstErrors = $AstErrors.Count

    Write-Host ''
    Write-Host 'FINAL : FORENSIC_FAIL_CLOSED' -ForegroundColor Red
    exit 1
}

Write-Host 'CORPUS AST : PASS' -ForegroundColor Green

# ============================================================================
# 7. EXTRACTION DES New-Item
# ============================================================================

$NewItems = @(
    $Ast.FindAll(
        {
            param($Node)

            $Node -is [System.Management.Automation.Language.CommandAst] -and
            @($Node.CommandElements).Count -gt 0 -and
            [string]$Node.CommandElements[0].Value -eq 'New-Item'
        },
        $true
    )
)

$Stats.Total = $NewItems.Count

Write-Host "CORPUS COMMANDS : $($Stats.Total)"

# ============================================================================
# 8. ORACLE EXECUTION
# ============================================================================

try {

    for ($i = 0; $i -lt $NewItems.Count; $i++) {

        $Command = $NewItems[$i]

        $PathArgAst = $null

        $CommandElements = @($Command.CommandElements)

        for ($j = 1; $j -lt $CommandElements.Count; $j++) {

            $Element = $CommandElements[$j]

            if ($Element -is [System.Management.Automation.Language.CommandParameterAst]) {

                if ($Element.ParameterName -match '^(Path|LiteralPath)$') {

                    if (($j + 1) -lt $CommandElements.Count) {
                        $PathArgAst = $CommandElements[$j + 1]
                    }

                    break
                }
            }
            elseif ($j -eq 1) {

                $PathArgAst = $Element
                break
            }
        }

        if ($null -eq $PathArgAst) {

            throw "CASE $($i + 1): impossible d'extraire l'argument Path."
        }

        $Resolution = Invoke-StaticResolution `
            -ExpressionAst $PathArgAst `
            -RootAst $Ast `
            -CommandAst $Command

        $Candidates = @($Resolution.Candidates)

        $ActualState = [string]$Resolution.Status

        if ($Resolution.Status -eq 'RESOLVED') {

            if ([string]$Resolution.Value -eq $TargetToMatch) {
                $ActualState = 'RESOLVED_TARGET'
            }
        }
        elseif ($Candidates.Count -gt 0) {

            $ActualState = 'UNRESOLVED_CANDIDATES'
        }

        $ExpectedState = [string]$ExpectedOracle[$i]

        $OracleMatch = ($ActualState -eq $ExpectedState)

        if ($OracleMatch) {
            $Stats.OraclePass++
        }
        else {
            $Stats.OracleFail++
        }

        $PassFailText = if ($OracleMatch) {
            'PASS'
        }
        else {
            'FAIL'
        }

        $Color = if ($OracleMatch) {
            'Green'
        }
        else {
            'Red'
        }

        Write-Host (
            "CASE {0:D2} | Expected: {1} | Actual: {2} | [{3}]" -f
            ($i + 1),
            $ExpectedState,
            $ActualState,
            $PassFailText
        ) -ForegroundColor $Color

        if (-not $OracleMatch) {

            $CandidateText = if ($Candidates.Count -gt 0) {
                ($Candidates -join ' | ')
            }
            else {
                '<none>'
            }

            Write-Host "  Value      : $($Resolution.Value)" -ForegroundColor Red
            Write-Host "  Confidence : $($Resolution.Confidence)" -ForegroundColor Red
            Write-Host "  Reason     : $($Resolution.Reason)" -ForegroundColor Red
            Write-Host "  Candidates : $CandidateText" -ForegroundColor Red
        }
    }
}
catch {

    $Stats.Exceptions++

    Write-Host ''
    Write-Host 'HARNESS EXCEPTION' -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
}

# ============================================================================
# 9. QUALITY GATES
# ============================================================================

Write-Host ''
Write-Host '============================================================' -ForegroundColor Cyan
Write-Host ' RÉSULTATS DU LAB & QUALITY GATES' -ForegroundColor Cyan
Write-Host '============================================================' -ForegroundColor Cyan
Write-Host ''

Write-Host "EXPECTED CASES : $($ExpectedOracle.Count)"
Write-Host "EXECUTED       : $($Stats.Total)"
Write-Host "CORRECT        : $($Stats.OraclePass)"
Write-Host "INCORRECT      : $($Stats.OracleFail)"
Write-Host "EXCEPTIONS     : $($Stats.Exceptions)"
Write-Host ''

$Verdict = 'FORENSIC_PASS'

# ============================================================================
# GATE 1 — INTÉGRITÉ RÉSOLVEUR
# ============================================================================

if ($Stats.Exceptions -eq 0) {

    Write-Host `
        '  SG_RESOLVER_INTEGRITY    : PASS' `
        -ForegroundColor Green
}
else {

    Write-Host `
        "  SG_RESOLVER_INTEGRITY    : FAIL ($($Stats.Exceptions) exception(s))" `
        -ForegroundColor Red

    $Verdict = 'FORENSIC_FAIL_CLOSED'
}

# ============================================================================
# GATE 2 — CORPUS COMPLET
# ============================================================================

if ($Stats.Total -eq $ExpectedOracle.Count) {

    Write-Host `
        '  SG_CORPUS_COMPLETENESS   : PASS' `
        -ForegroundColor Green
}
else {

    Write-Host `
        '  SG_CORPUS_COMPLETENESS   : FAIL' `
        -ForegroundColor Red

    if ($Verdict -eq 'FORENSIC_PASS') {
        $Verdict = 'FORENSIC_FAIL'
    }
}

# ============================================================================
# GATE 3 — ORACLE 100 %
# ============================================================================

if ($Stats.OracleFail -eq 0 -and
    $Stats.OraclePass -eq $ExpectedOracle.Count) {

    Write-Host `
        '  SG_CORPUS_ORACLE         : PASS' `
        -ForegroundColor Green
}
else {

    Write-Host `
        '  SG_CORPUS_ORACLE         : FAIL' `
        -ForegroundColor Red

    if ($Verdict -eq 'FORENSIC_PASS') {
        $Verdict = 'FORENSIC_FAIL'
    }
}

# ============================================================================
# GATE 4 — AUCUNE EXCEPTION
# ============================================================================

if ($Stats.Exceptions -eq 0) {

    Write-Host `
        '  SG_ZERO_EXCEPTION        : PASS' `
        -ForegroundColor Green
}
else {

    Write-Host `
        '  SG_ZERO_EXCEPTION        : FAIL' `
        -ForegroundColor Red

    $Verdict = 'FORENSIC_FAIL_CLOSED'
}

# ============================================================================
# 10. VERDICT FINAL
# ============================================================================

$FinalColor = if ($Verdict -eq 'FORENSIC_PASS') {
    'Green'
}
else {
    'Red'
}

Write-Host ''
Write-Host 'FINAL :' -ForegroundColor Cyan
Write-Host "  $Verdict" -ForegroundColor $FinalColor
Write-Host '============================================================' -ForegroundColor Cyan

# ============================================================================
# 11. EXIT CODE CERTIFIABLE
# ============================================================================

if ($Verdict -eq 'FORENSIC_PASS') {
    exit 0
}

exit 1