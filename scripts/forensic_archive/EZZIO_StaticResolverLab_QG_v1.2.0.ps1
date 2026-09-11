#Requires -Version 7.0

<#
===============================================================================
E-ZZIO — STATIC RESOLVER QUALITY GATE
Version : 1.2.0
Mode    : FORENSIC / FAIL-CLOSED / READ-ONLY

OBJECTIF
--------
Établir mathématiquement si le Static Resolver satisfait 100 % du
Quality Gate.

CERTIFIED est impossible si :
    - un gate échoue
    - un test échoue
    - une exception survient
    - un test n'est pas exécuté
    - la cardinalité n'est pas correctement normalisée
    - la déterminisme n'est pas démontrée
    - une mutation filesystem est détectée

IMPORTANT
---------
Ce laboratoire analyse uniquement de l'AST.
Il n'exécute aucun New-Item contenu dans les corpus.
===============================================================================
#>

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

# ============================================================================
# 0. CONFIGURATION
# ============================================================================

$Version = '1.2.0'
$ExpectedCaseCount = 15

$PassedTests = 0
$FailedTests = 0
$ExecutedTests = 0
$TotalTests = 0
$ExceptionCount = 0

$Gates = [ordered]@{
    G01_SYNTAX                = 'NOT_RUN'
    G02_BASELINE_COMPLETENESS = 'NOT_RUN'
    G03_BASELINE_ORACLE       = 'NOT_RUN'
    G04_CARDINALITY_HARDENING = 'NOT_RUN'
    G05_FAIL_CLOSED            = 'NOT_RUN'
    G06_FALSE_POSITIVE         = 'NOT_RUN'
    G07_DETERMINISM             = 'NOT_RUN'
    G08_NO_MUTATION             = 'NOT_RUN'
    G09_HARNESS_INTEGRITY       = 'NOT_RUN'
    G10_ZERO_EXCEPTION         = 'NOT_RUN'
}

$GateReasons = [ordered]@{}

# ============================================================================
# 1. OUTILS DE TEST
# ============================================================================

function Get-SafeCount {
    [CmdletBinding()]
    param(
        [Parameter(Position = 0)]
        [AllowNull()]
        [object]$Value
    )

    # CRITIQUE :
    # Un argument $null peut être absorbé par PowerShell lors de l'appel.
    # La fonction doit néanmoins retourner physiquement 0.
    if ($null -eq $Value) {
        return 0
    }

    return @($Value).Count
}

function Assert-Equal {
    [CmdletBinding()]
    param(
        [AllowNull()]
        [object]$Actual,

        [AllowNull()]
        [object]$Expected,

        [Parameter(Mandatory)]
        [string]$Name
    )

    if ($Actual -ne $Expected) {
        throw (
            '{0} : expected [{1}], actual [{2}]' -f
            $Name,
            $Expected,
            $Actual
        )
    }
}

function Assert-True {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [bool]$Condition,

        [Parameter(Mandatory)]
        [string]$Name
    )

    if (-not $Condition) {
        throw "$Name : expected TRUE."
    }
}

function New-Resolution {
    param(
        [Parameter(Mandatory)]
        [string]$Status,

        [AllowNull()]
        [string]$Value,

        [Parameter(Mandatory)]
        [string]$Confidence,

        [Parameter(Mandatory)]
        [string]$Reason,

        [AllowNull()]
        [object[]]$Candidates = @()
    )

    $SafeCandidates = @()

    if ($null -ne $Candidates) {
        $SafeCandidates = @($Candidates)
    }

    return [pscustomobject]@{
        Status     = $Status
        Value      = $Value
        Confidence = $Confidence
        Reason     = $Reason
        Candidates = $SafeCandidates
    }
}

# ============================================================================
# 2. CONDITIONAL-FLOW ANALYSIS
# ============================================================================

function Test-IsConditionalRelativeTo {
    param(
        [Parameter(Mandatory)]
        $AssignNode,

        [Parameter(Mandatory)]
        $CommandNode
    )

    $Parent = $AssignNode.Parent

    while (
        $null -ne $Parent -and
        $Parent -isnot [System.Management.Automation.Language.ScriptBlockAst]
    ) {
        if (
            $Parent -is [System.Management.Automation.Language.IfStatementAst] -or
            $Parent -is [System.Management.Automation.Language.ForEachStatementAst] -or
            $Parent -is [System.Management.Automation.Language.WhileStatementAst]
        ) {
            $ContainsCommand = $Parent.Find(
                {
                    param($Node)
                    $Node -eq $CommandNode
                },
                $true
            )

            if (-not $ContainsCommand) {
                return $true
            }
        }

        $Parent = $Parent.Parent
    }

    return $false
}

# ============================================================================
# 3. STATIC RESOLVER
# ============================================================================

function Invoke-StaticResolution {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        $ExpressionAst,

        [Parameter(Mandatory)]
        $RootAst,

        [Parameter(Mandatory)]
        $CommandAst,

        [int]$Depth = 0
    )

    if ($Depth -gt 20) {
        return New-Resolution `
            -Status 'UNRESOLVED' `
            -Value $null `
            -Confidence 'NONE' `
            -Reason 'DEPTH_LIMIT_REACHED'
    }

    # ------------------------------------------------------------------------
    # AST UNWRAPPING
    # ------------------------------------------------------------------------

    $Unwrapped = $true

    while ($Unwrapped) {

        $Unwrapped = $false

        if (
            $ExpressionAst -is
            [System.Management.Automation.Language.PipelineAst] -and
            @($ExpressionAst.PipelineElements).Count -eq 1
        ) {
            $ExpressionAst = $ExpressionAst.PipelineElements[0]
            $Unwrapped = $true
            continue
        }

        if (
            $ExpressionAst -is
            [System.Management.Automation.Language.CommandExpressionAst]
        ) {
            $ExpressionAst = $ExpressionAst.Expression
            $Unwrapped = $true
            continue
        }

        if (
            $ExpressionAst -is
            [System.Management.Automation.Language.ParenExpressionAst]
        ) {
            $ExpressionAst = $ExpressionAst.Pipeline
            $Unwrapped = $true
        }
    }

    # ------------------------------------------------------------------------
    # CAS A — STRING LITERAL
    # ------------------------------------------------------------------------

    if (
        $ExpressionAst -is
        [System.Management.Automation.Language.StringConstantExpressionAst]
    ) {
        return New-Resolution `
            -Status 'RESOLVED' `
            -Value $ExpressionAst.Value `
            -Confidence 'STATIC_EXACT' `
            -Reason 'LITERAL_VALUE'
    }

    # ------------------------------------------------------------------------
    # CAS B — ARRAY INDEX
    # ------------------------------------------------------------------------

    if (
        $ExpressionAst -is
        [System.Management.Automation.Language.IndexExpressionAst]
    ) {

        $Target = $ExpressionAst.Target
        $Index = $ExpressionAst.Index

        if (
            $Target -is
            [System.Management.Automation.Language.VariableExpressionAst] -and
            $Index -is
            [System.Management.Automation.Language.ConstantExpressionAst]
        ) {

            $VariableName = $Target.VariablePath.UserPath

            try {
                $IndexValue = [int]$Index.Value
            }
            catch {
                return New-Resolution `
                    -Status 'UNRESOLVED' `
                    -Value $null `
                    -Confidence 'NONE' `
                    -Reason 'NON_INTEGER_ARRAY_INDEX'
            }

            $Assignments = @(
                $RootAst.FindAll(
                    {
                        param($Node)

                        $Node -is
                        [System.Management.Automation.Language.AssignmentStatementAst] -and

                        $Node.Left -is
                        [System.Management.Automation.Language.VariableExpressionAst] -and

                        $Node.Left.VariablePath.UserPath -eq $VariableName -and

                        $Node.Extent.StartLineNumber -lt
                        $CommandAst.Extent.StartLineNumber
                    },
                    $true
                )
            )

            $Assignments =
                @(
                    $Assignments |
                    Sort-Object {
                        $_.Extent.StartLineNumber
                    } -Descending
                )

            if (@($Assignments).Count -gt 0) {

                $ArrayLiterals = @(
                    $Assignments[0].Right.FindAll(
                        {
                            param($Node)

                            $Node -is
                            [System.Management.Automation.Language.ArrayLiteralAst]
                        },
                        $true
                    )
                )

                if (@($ArrayLiterals).Count -gt 0) {

                    $Elements = @($ArrayLiterals[0].Elements)

                    if (
                        $IndexValue -ge 0 -and
                        $IndexValue -lt @($Elements).Count
                    ) {

                        $ElementResolution =
                            Invoke-StaticResolution `
                                -ExpressionAst $Elements[$IndexValue] `
                                -RootAst $RootAst `
                                -CommandAst $CommandAst `
                                -Depth ($Depth + 1)

                        if ($ElementResolution.Status -eq 'RESOLVED') {

                            $ElementResolution.Confidence =
                                'STATIC_ARRAY_INDEX'

                            return $ElementResolution
                        }
                    }
                }
            }
        }

        return New-Resolution `
            -Status 'UNRESOLVED' `
            -Value $null `
            -Confidence 'NONE' `
            -Reason 'DYNAMIC_INDEX_OR_UNSUPPORTED_ARRAY'
    }

    # ------------------------------------------------------------------------
    # CAS C — VARIABLE
    # ------------------------------------------------------------------------

    if (
        $ExpressionAst -is
        [System.Management.Automation.Language.VariableExpressionAst]
    ) {

        $VariableName =
            $ExpressionAst.VariablePath.UserPath

        if (
            $VariableName -match
            '^(args|_|PSItem|env:.*)$'
        ) {
            return New-Resolution `
                -Status 'UNRESOLVED' `
                -Value $null `
                -Confidence 'NONE' `
                -Reason 'DYNAMIC_VARIABLE'
        }

        # FOREACH STATIC COLLECTION
        $Loops = @(
            $RootAst.FindAll(
                {
                    param($Node)

                    $Node -is
                    [System.Management.Automation.Language.ForEachStatementAst] -and

                    $Node.Variable.VariablePath.UserPath -eq
                    $VariableName -and

                    $Node.Extent.StartLineNumber -lt
                    $CommandAst.Extent.StartLineNumber
                },
                $true
            )
        )

        foreach ($Loop in $Loops) {

            $ContainsCommand =
                $Loop.Body.Find(
                    {
                        param($Node)
                        $Node -eq $CommandAst
                    },
                    $true
                )

            if ($ContainsCommand) {

                $ArrayLiterals = @(
                    $Loop.Condition.FindAll(
                        {
                            param($Node)

                            $Node -is
                            [System.Management.Automation.Language.ArrayLiteralAst]
                        },
                        $true
                    )
                )

                if (@($ArrayLiterals).Count -gt 0) {

                    $Candidates =
                        [System.Collections.Generic.List[string]]::new()

                    $Elements = @($ArrayLiterals[0].Elements)

                    foreach ($Element in $Elements) {

                        $ElementResolution =
                            Invoke-StaticResolution `
                                -ExpressionAst $Element `
                                -RootAst $RootAst `
                                -CommandAst $CommandAst `
                                -Depth ($Depth + 1)

                        if ($ElementResolution.Status -eq 'RESOLVED') {
                            $Candidates.Add(
                                [string]$ElementResolution.Value
                            )
                        }
                    }

                    if (
                        $Candidates.Count -eq
                        @($Elements).Count
                    ) {

                        return New-Resolution `
                            -Status 'UNRESOLVED' `
                            -Value $null `
                            -Confidence 'STATIC_LOOP_CANDIDATES' `
                            -Reason 'LOOP_VARIABLE' `
                            -Candidates $Candidates.ToArray()
                    }
                }
            }
        }

        # CLASSIC ASSIGNMENT
        $Assignments = @(
            $RootAst.FindAll(
                {
                    param($Node)

                    $Node -is
                    [System.Management.Automation.Language.AssignmentStatementAst] -and

                    $Node.Left -is
                    [System.Management.Automation.Language.VariableExpressionAst] -and

                    $Node.Left.VariablePath.UserPath -eq
                    $VariableName -and

                    $Node.Extent.StartLineNumber -lt
                    $CommandAst.Extent.StartLineNumber
                },
                $true
            )
        )

        if (@($Assignments).Count -eq 0) {

            return New-Resolution `
                -Status 'UNRESOLVED' `
                -Value $null `
                -Confidence 'NONE' `
                -Reason 'NO_ASSIGNMENT_FOUND'
        }

        $Assignments =
            @(
                $Assignments |
                Sort-Object {
                    $_.Extent.StartLineNumber
                } -Descending
            )

        $LatestAssignment = $Assignments[0]

        # CONTROL-FLOW AMBIGUITY
        if (
            Test-IsConditionalRelativeTo `
                -AssignNode $LatestAssignment `
                -CommandNode $CommandAst
        ) {

            $Candidates =
                [System.Collections.Generic.List[string]]::new()

            foreach ($Assignment in $Assignments) {

                $SubResolution =
                    Invoke-StaticResolution `
                        -ExpressionAst $Assignment.Right `
                        -RootAst $RootAst `
                        -CommandAst $CommandAst `
                        -Depth ($Depth + 1)

                if (
                    $SubResolution.Status -eq 'RESOLVED' -and
                    $SubResolution.Value -notin $Candidates
                ) {
                    $Candidates.Add(
                        [string]$SubResolution.Value
                    )
                }
            }

            return New-Resolution `
                -Status 'UNRESOLVED' `
                -Value $null `
                -Confidence 'NONE' `
                -Reason 'AMBIGUOUS_CONTROL_FLOW' `
                -Candidates $Candidates.ToArray()
        }

        $Resolution =
            Invoke-StaticResolution `
                -ExpressionAst $LatestAssignment.Right `
                -RootAst $RootAst `
                -CommandAst $CommandAst `
                -Depth ($Depth + 1)

        if ($Resolution.Status -eq 'RESOLVED') {
            $Resolution.Confidence =
                'STATIC_VARIABLE_TRACE'
        }

        return $Resolution
    }

    # ------------------------------------------------------------------------
    # CAS D — EXPANDABLE STRING
    # ------------------------------------------------------------------------

    if (
        $ExpressionAst -is
        [System.Management.Automation.Language.ExpandableStringExpressionAst]
    ) {

        $BaseCandidates = @(
            [string]$ExpressionAst.Value
        )

        $ProducedCandidates = $false

        foreach ($NestedAst in @($ExpressionAst.NestedExpressions)) {

            $NestedResolution =
                Invoke-StaticResolution `
                    -ExpressionAst $NestedAst `
                    -RootAst $RootAst `
                    -CommandAst $CommandAst `
                    -Depth ($Depth + 1)

            if ($NestedResolution.Status -eq 'RESOLVED') {

                $NewCandidates = @()

                foreach ($Candidate in $BaseCandidates) {

                    $NewCandidates +=
                        $Candidate.Replace(
                            $NestedAst.Extent.Text,
                            [string]$NestedResolution.Value
                        )
                }

                $BaseCandidates = @($NewCandidates)
            }
            elseif (
                @($NestedResolution.Candidates).Count -gt 0
            ) {

                $NewCandidates = @()

                foreach ($Candidate in $BaseCandidates) {

                    foreach (
                        $SubCandidate in
                        @($NestedResolution.Candidates)
                    ) {

                        $NewCandidates +=
                            $Candidate.Replace(
                                $NestedAst.Extent.Text,
                                [string]$SubCandidate
                            )
                    }
                }

                $BaseCandidates = @($NewCandidates)
                $ProducedCandidates = $true
            }
            else {

                return New-Resolution `
                    -Status 'UNRESOLVED' `
                    -Value $null `
                    -Confidence 'NONE' `
                    -Reason 'UNRESOLVED_NESTED_EXPRESSION'
            }
        }

        if (
            -not $ProducedCandidates -and
            @($BaseCandidates).Count -eq 1
        ) {

            return New-Resolution `
                -Status 'RESOLVED' `
                -Value $BaseCandidates[0] `
                -Confidence 'STATIC_EXPANDABLE_STRING' `
                -Reason 'ALL_NESTED_RESOLVED'
        }

        return New-Resolution `
            -Status 'UNRESOLVED' `
            -Value $null `
            -Confidence 'EXPANDABLE_STRING_CANDIDATES' `
            -Reason 'MULTIPLE_CANDIDATES_GENERATED' `
            -Candidates $BaseCandidates
    }

    # ------------------------------------------------------------------------
    # CAS E — JOIN-PATH
    # ------------------------------------------------------------------------

    if (
        $ExpressionAst -is
        [System.Management.Automation.Language.CommandAst]
    ) {

        $CommandElements =
            @($ExpressionAst.CommandElements)

        if (@($CommandElements).Count -eq 0) {

            return New-Resolution `
                -Status 'UNRESOLVED' `
                -Value $null `
                -Confidence 'NONE' `
                -Reason 'EMPTY_COMMAND'
        }

        $CommandName =
            [string]$CommandElements[0].Value

        if (
            $CommandName -eq 'Join-Path' -and
            @($CommandElements).Count -ge 3
        ) {

            $Path1 =
                Invoke-StaticResolution `
                    -ExpressionAst $CommandElements[1] `
                    -RootAst $RootAst `
                    -CommandAst $CommandAst `
                    -Depth ($Depth + 1)

            $Path2 =
                Invoke-StaticResolution `
                    -ExpressionAst $CommandElements[2] `
                    -RootAst $RootAst `
                    -CommandAst $CommandAst `
                    -Depth ($Depth + 1)

            if (
                $Path1.Status -eq 'RESOLVED' -and
                $Path2.Status -eq 'RESOLVED'
            ) {

                $P1 =
                    ([string]$Path1.Value).TrimEnd('\','/')

                $P2 =
                    ([string]$Path2.Value).TrimStart('\','/')

                $Combined =
                    $P1 + '\' + $P2

                $IsUNC =
                    $Combined.StartsWith('\\')

                $Combined =
                    $Combined -replace '\\+', '\'

                if ($IsUNC) {
                    $Combined = '\' + $Combined
                }

                return New-Resolution `
                    -Status 'RESOLVED' `
                    -Value $Combined `
                    -Confidence 'STATIC_JOIN_PATH_NORMALIZED' `
                    -Reason 'JOIN_PATH_EVALUATED'
            }
        }

        return New-Resolution `
            -Status 'UNRESOLVED' `
            -Value $null `
            -Confidence 'NONE' `
            -Reason "DYNAMIC_COMMAND_$CommandName"
    }

    # ------------------------------------------------------------------------
    # CAS F — CONCATENATION
    # ------------------------------------------------------------------------

    if (
        $ExpressionAst -is
        [System.Management.Automation.Language.BinaryExpressionAst] -and
        $ExpressionAst.Operator -eq 'Plus'
    ) {

        $LeftResolution =
            Invoke-StaticResolution `
                -ExpressionAst $ExpressionAst.Left `
                -RootAst $RootAst `
                -CommandAst $CommandAst `
                -Depth ($Depth + 1)

        $RightResolution =
            Invoke-StaticResolution `
                -ExpressionAst $ExpressionAst.Right `
                -RootAst $RootAst `
                -CommandAst $CommandAst `
                -Depth ($Depth + 1)

        if (
            $LeftResolution.Status -eq 'RESOLVED' -and
            $RightResolution.Status -eq 'RESOLVED'
        ) {

            return New-Resolution `
                -Status 'RESOLVED' `
                -Value (
                    [string]$LeftResolution.Value +
                    [string]$RightResolution.Value
                ) `
                -Confidence 'STATIC_CONCATENATION' `
                -Reason 'DETERMINISTIC_CONCAT'
        }

        return New-Resolution `
            -Status 'UNRESOLVED' `
            -Value $null `
            -Confidence 'NONE' `
            -Reason 'PARTIAL_CONCATENATION'
    }

    # ------------------------------------------------------------------------
    # FAIL CLOSED
    # ------------------------------------------------------------------------

    $TypeName =
        if ($null -eq $ExpressionAst) {
            'NULL_AST'
        }
        else {
            $ExpressionAst.GetType().Name
        }

    return New-Resolution `
        -Status 'UNRESOLVED' `
        -Value $null `
        -Confidence 'NONE' `
        -Reason "UNSUPPORTED_AST_NODE_$TypeName"
}

# ============================================================================
# 4. BASELINE CORPUS
# ============================================================================

$BaselineCode = @'
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

# 07 — Piège de portée
if ($false) {
    $Destination7 = 'C:\fake_malicious.txt'
}
$Destination7 = 'C:\real_safe.txt'
New-Item -Path $Destination7 -ItemType File

# 08 — If/Else ambigu
if ($true) {
    $Destination8 = 'C:\path_A.txt'
}
else {
    $Destination8 = 'C:\path_B.txt'
}
New-Item -Path $Destination8 -ItemType File

# 09 — Join-Path pathologique
$Root9 = 'G:\AI\E-zzio\'
$Destination9 = Join-Path $Root9 '\logs\\x.log'
New-Item -Path $Destination9 -ItemType File

# 10 — Ambiguïté dynamique
if ((Get-Random) -gt 5) {
    $Destination10 = 'C:\dyn_path_A.txt'
}
else {
    $Destination10 = 'C:\dyn_path_B.txt'
}
New-Item -Path $Destination10 -ItemType File

# 11 — Foreach statique
foreach ($File in @('a.txt', 'b.txt')) {
    $Destination11 = "C:\logs\$File"
    New-Item -Path $Destination11 -ItemType File
}

# 12 — Positionnel
$Destination12 = 'G:\AI\E-zzio\positional.txt'
New-Item $Destination12 -ItemType File

# 13 — Interpolation résoluble
$SubDir = 'logs'
$Destination13 = "G:\AI\E-zzio\$SubDir\x.log"
New-Item -Path $Destination13 -ItemType File

# 14 — Interpolation non résoluble
$Destination14 = "G:\AI\E-zzio\$env:USERNAME\x.log"
New-Item -Path $Destination14 -ItemType File

# 15 — Index array déterministe
$Arr = @('C:\path_arr.txt', 'C:\other.txt')
$Destination15 = $Arr[0]
New-Item -Path $Destination15 -ItemType File
'@

$ExpectedOracle = @(
    'RESOLVED',
    'RESOLVED',
    'RESOLVED',
    'UNRESOLVED',
    'UNRESOLVED',
    'RESOLVED_TARGET',
    'RESOLVED',
    'UNRESOLVED_CANDIDATES',
    'RESOLVED',
    'UNRESOLVED_CANDIDATES',
    'UNRESOLVED_CANDIDATES',
    'RESOLVED',
    'RESOLVED',
    'UNRESOLVED',
    'RESOLVED'
)

$TargetToMatch =
    'G:\AI\E-zzio\EZZIO_Freeze_Certification_v1.1.1.ps1'

# ============================================================================
# 5. ADDITIONAL ADVERSARIAL CORPUS
# ============================================================================

$AdditionalCorpus = @(
    [pscustomobject]@{
        Name = 'NULL_COLLECTION_CARDINALITY'
        Code = '$x = $null'
        Expected = 'PASS'
    }

    [pscustomobject]@{
        Name = 'SCALAR_COLLECTION_CARDINALITY'
        Code = '$x = "x"'
        Expected = 'PASS'
    }

    [pscustomobject]@{
        Name = 'SINGLETON_COLLECTION_CARDINALITY'
        Code = '$x = @("x")'
        Expected = 'PASS'
    }

    [pscustomobject]@{
        Name = 'EMPTY_COLLECTION_CARDINALITY'
        Code = '$x = @()'
        Expected = 'PASS'
    }

    [pscustomobject]@{
        Name = 'UNKNOWN_COMMAND_FAIL_CLOSED'
        Code = @'
$Destination = Get-DynamicPath
New-Item -Path $Destination -ItemType File
'@
        Expected = 'UNRESOLVED'
    }

    [pscustomobject]@{
        Name = 'ENVIRONMENT_FAIL_CLOSED'
        Code = @'
$Destination = "C:\$env:USERNAME\x.txt"
New-Item -Path $Destination -ItemType File
'@
        Expected = 'UNRESOLVED'
    }

    [pscustomobject]@{
        Name = 'ARGS_FAIL_CLOSED'
        Code = @'
New-Item -Path $args[0] -ItemType File
'@
        Expected = 'UNRESOLVED'
    }

    [pscustomobject]@{
        Name = 'DETERMINISTIC_LITERAL'
        Code = @'
$Destination = 'C:\deterministic.txt'
New-Item -Path $Destination -ItemType File
'@
        Expected = 'RESOLVED'
    }

    [pscustomobject]@{
        Name = 'AMBIGUOUS_BRANCH'
        Code = @'
if (Get-Random) {
    $Destination = 'C:\A.txt'
}
else {
    $Destination = 'C:\B.txt'
}
New-Item -Path $Destination -ItemType File
'@
        Expected = 'UNRESOLVED_CANDIDATES'
    }

    [pscustomobject]@{
        Name = 'ARRAY_INDEX_ZERO'
        Code = @'
$Arr = @('C:\A.txt','C:\B.txt')
$Destination = $Arr[0]
New-Item -Path $Destination -ItemType File
'@
        Expected = 'RESOLVED'
    }

    [pscustomobject]@{
        Name = 'ARRAY_INDEX_OUT_OF_RANGE'
        Code = @'
$Arr = @('C:\A.txt')
$Destination = $Arr[9]
New-Item -Path $Destination -ItemType File
'@
        Expected = 'UNRESOLVED'
    }

    [pscustomobject]@{
        Name = 'UNSUPPORTED_EXPRESSION'
        Code = @'
$Destination = [System.IO.Path]::GetTempFileName()
New-Item -Path $Destination -ItemType File
'@
        Expected = 'UNRESOLVED'
    }
)

# ============================================================================
# 6. GATE 01 — SYNTAX
# ============================================================================

try {

    $Tokens = $null
    $Errors = $null

    $BaselineAst =
        [System.Management.Automation.Language.Parser]::ParseInput(
            $BaselineCode,
            [ref]$Tokens,
            [ref]$Errors
        )

    Assert-Equal `
        @($Errors).Count `
        0 `
        'BASELINE_SYNTAX_ERRORS'

    $Gates.G01_SYNTAX = 'PASS'
    $GateReasons.G01_SYNTAX =
        'Baseline parsed without parser errors.'

    Write-Host 'G01_SYNTAX                : PASS' `
        -ForegroundColor Green
}
catch {

    $Gates.G01_SYNTAX = 'FAIL'
    $GateReasons.G01_SYNTAX =
        $_.Exception.Message

    $ExceptionCount++

    Write-Host (
        'G01_SYNTAX                : FAIL ({0})' -f
        $_.Exception.Message
    ) -ForegroundColor Red
}

# ============================================================================
# 7. GATE 02 + G03 — BASELINE
# ============================================================================

$BaselineResults =
    [System.Collections.Generic.List[object]]::new()

try {

    $NewItems = @(
        $BaselineAst.FindAll(
            {
                param($Node)

                $Node -is
                [System.Management.Automation.Language.CommandAst] -and

                @($Node.CommandElements).Count -gt 0 -and

                [string]$Node.CommandElements[0].Value -eq
                'New-Item'
            },
            $true
        )
    )

    Assert-Equal `
        @($NewItems).Count `
        $ExpectedCaseCount `
        'BASELINE_COMMAND_COUNT'

    $Gates.G02_BASELINE_COMPLETENESS = 'PASS'
    $GateReasons.G02_BASELINE_COMPLETENESS =
        "$($NewItems.Count)/$ExpectedCaseCount baseline commands detected."

    Write-Host (
        'G02_BASELINE_COMPLETENESS : PASS ({0}/{1})' -f
        $NewItems.Count,
        $ExpectedCaseCount
    ) -ForegroundColor Green

    for (
        $i = 0;
        $i -lt @($NewItems).Count;
        $i++
    ) {

        $Command = $NewItems[$i]

        $PathAst = $null
        $Elements = @($Command.CommandElements)

        for (
            $j = 1;
            $j -lt $Elements.Count;
            $j++
        ) {

            $Element = $Elements[$j]

            if (
                $Element -is
                [System.Management.Automation.Language.CommandParameterAst]
            ) {

                if (
                    $Element.ParameterName -match
                    '^(Path|LiteralPath)$'
                ) {

                    if (($j + 1) -lt $Elements.Count) {
                        $PathAst = $Elements[$j + 1]
                    }

                    break
                }
            }
            elseif (
                $j -eq 1 -and
                $Element -isnot
                [System.Management.Automation.Language.CommandParameterAst]
            ) {

                $PathAst = $Element
                break
            }
        }

        if ($null -eq $PathAst) {
            throw "Baseline case $($i + 1) has no path AST."
        }

        $Resolution =
            Invoke-StaticResolution `
                -ExpressionAst $PathAst `
                -RootAst $BaselineAst `
                -CommandAst $Command

        $ActualState =
            [string]$Resolution.Status

        if (
            $Resolution.Status -eq 'RESOLVED' -and
            [string]$Resolution.Value -eq $TargetToMatch
        ) {
            $ActualState = 'RESOLVED_TARGET'
        }
        elseif (
            $Resolution.Status -ne 'RESOLVED' -and
            @($Resolution.Candidates).Count -gt 0
        ) {
            $ActualState = 'UNRESOLVED_CANDIDATES'
        }

        $ExpectedState =
            [string]$ExpectedOracle[$i]

        $Match =
            $ActualState -eq $ExpectedState

        $ExecutedTests++
        $TotalTests++

        if ($Match) {
            $PassedTests++
        }
        else {
            $FailedTests++
        }

        $Result = [pscustomobject]@{
            Case       = $i + 1
            Expected   = $ExpectedState
            Actual     = $ActualState
            Pass       = $Match
            Value      = $Resolution.Value
            Reason     = $Resolution.Reason
            Candidates = @($Resolution.Candidates)
        }

        $BaselineResults.Add($Result)

        $Text =
            if ($Match) {
                'PASS'
            }
            else {
                'FAIL'
            }

        $Color =
            if ($Match) {
                'Green'
            }
            else {
                'Red'
            }

        Write-Host (
            'CASE {0:D2} | Expected: {1} | Actual: {2} | [{3}]' -f
            ($i + 1),
            $ExpectedState,
            $ActualState,
            $Text
        ) -ForegroundColor $Color
    }

    Assert-Equal `
        @($BaselineResults).Count `
        $ExpectedCaseCount `
        'BASELINE_RESULT_COUNT'

    Assert-Equal `
        @($BaselineResults | Where-Object Pass).Count `
        $ExpectedCaseCount `
        'BASELINE_ORACLE_PASS_COUNT'

    $Gates.G03_BASELINE_ORACLE = 'PASS'
    $GateReasons.G03_BASELINE_ORACLE =
        "$($ExpectedCaseCount)/$ExpectedCaseCount oracle cases passed."

    Write-Host 'G03_BASELINE_ORACLE      : PASS' `
        -ForegroundColor Green
}
catch {

    $Gates.G02_BASELINE_COMPLETENESS = 'FAIL'
    $Gates.G03_BASELINE_ORACLE = 'FAIL'

    $GateReasons.G02_BASELINE_COMPLETENESS =
        $_.Exception.Message

    $GateReasons.G03_BASELINE_ORACLE =
        $_.Exception.Message

    $ExceptionCount++

    Write-Host 'G02_BASELINE_COMPLETENESS : FAIL' `
        -ForegroundColor Red

    Write-Host 'G03_BASELINE_ORACLE      : FAIL' `
        -ForegroundColor Red
}

# ============================================================================
# 8. GATE 04 — CARDINALITY
# ============================================================================

try {

    $NullCount =
        Get-SafeCount $null

    $ScalarCount =
        Get-SafeCount 'x'

    $SingletonCount =
        Get-SafeCount @('x')

    $EmptyCount =
        Get-SafeCount @()

    Assert-Equal `
        $NullCount `
        0 `
        'NULL_COUNT'

    Assert-Equal `
        $ScalarCount `
        1 `
        'SCALAR_COUNT'

    Assert-Equal `
        $SingletonCount `
        1 `
        'SINGLETON_COUNT'

    Assert-Equal `
        $EmptyCount `
        0 `
        'EMPTY_COLLECTION_COUNT'

    $Gates.G04_CARDINALITY_HARDENING = 'PASS'

    $GateReasons.G04_CARDINALITY_HARDENING =
        'Null/scalar/singleton/empty cardinality normalized.'

    Write-Host 'G04_CARDINALITY_HARDENING : PASS' `
        -ForegroundColor Green
}
catch {

    $Gates.G04_CARDINALITY_HARDENING = 'FAIL'

    $GateReasons.G04_CARDINALITY_HARDENING =
        $_.Exception.Message

    $ExceptionCount++

    Write-Host (
        'G04_CARDINALITY_HARDENING : FAIL ({0})' -f
        $_.Exception.Message
    ) -ForegroundColor Red
}

# ============================================================================
# 9. GATE 05 — FAIL CLOSED
# ============================================================================

try {

    $DynamicCode = @'
$Destination = Get-DynamicPath
New-Item -Path $Destination -ItemType File
'@

    $Tokens = $null
    $Errors = $null

    $DynamicAst =
        [System.Management.Automation.Language.Parser]::ParseInput(
            $DynamicCode,
            [ref]$Tokens,
            [ref]$Errors
        )

    Assert-Equal `
        @($Errors).Count `
        0 `
        'DYNAMIC_SYNTAX'

    $DynamicCommand = @(
        $DynamicAst.FindAll(
            {
                param($Node)

                $Node -is
                [System.Management.Automation.Language.CommandAst] -and

                @($Node.CommandElements).Count -gt 0 -and

                [string]$Node.CommandElements[0].Value -eq
                'New-Item'
            },
            $true
        )
    )

    Assert-Equal `
        @($DynamicCommand).Count `
        1 `
        'DYNAMIC_COMMAND_COUNT'

    $DynamicPath =
        $DynamicCommand[0].CommandElements[2]

    $DynamicResult =
        Invoke-StaticResolution `
            -ExpressionAst $DynamicPath `
            -RootAst $DynamicAst `
            -CommandAst $DynamicCommand[0]

    Assert-Equal `
        $DynamicResult.Status `
        'UNRESOLVED' `
        'DYNAMIC_FAIL_CLOSED'

    $Gates.G05_FAIL_CLOSED = 'PASS'

    $GateReasons.G05_FAIL_CLOSED =
        'Unknown runtime value remained unresolved.'

    Write-Host 'G05_FAIL_CLOSED           : PASS' `
        -ForegroundColor Green
}
catch {

    $Gates.G05_FAIL_CLOSED = 'FAIL'

    $GateReasons.G05_FAIL_CLOSED =
        $_.Exception.Message

    $ExceptionCount++

    Write-Host (
        'G05_FAIL_CLOSED           : FAIL ({0})' -f
        $_.Exception.Message
    ) -ForegroundColor Red
}

# ============================================================================
# 10. GATE 06 — FALSE POSITIVE RESISTANCE
# ============================================================================

try {

    $AmbiguousCode = @'
if (Get-Random) {
    $Destination = 'C:\A.txt'
}
else {
    $Destination = 'C:\B.txt'
}
New-Item -Path $Destination -ItemType File
'@

    $Tokens = $null
    $Errors = $null

    $AmbiguousAst =
        [System.Management.Automation.Language.Parser]::ParseInput(
            $AmbiguousCode,
            [ref]$Tokens,
            [ref]$Errors
        )

    Assert-Equal `
        @($Errors).Count `
        0 `
        'AMBIGUOUS_SYNTAX'

    $AmbiguousCommand = @(
        $AmbiguousAst.FindAll(
            {
                param($Node)

                $Node -is
                [System.Management.Automation.Language.CommandAst] -and

                @($Node.CommandElements).Count -gt 0 -and

                [string]$Node.CommandElements[0].Value -eq
                'New-Item'
            },
            $true
        )
    )

    Assert-Equal `
        @($AmbiguousCommand).Count `
        1 `
        'AMBIGUOUS_COMMAND_COUNT'

    $AmbiguousPath =
        $AmbiguousCommand[0].CommandElements[2]

    $AmbiguousResult =
        Invoke-StaticResolution `
            -ExpressionAst $AmbiguousPath `
            -RootAst $AmbiguousAst `
            -CommandAst $AmbiguousCommand[0]

    Assert-Equal `
        $AmbiguousResult.Status `
        'UNRESOLVED' `
        'AMBIGUOUS_STATUS'

    Assert-True `
        (@($AmbiguousResult.Candidates).Count -eq 2) `
        'AMBIGUOUS_CANDIDATE_COUNT'

    Assert-True `
        ('C:\A.txt' -in @($AmbiguousResult.Candidates)) `
        'CANDIDATE_A_PRESENT'

    Assert-True `
        ('C:\B.txt' -in @($AmbiguousResult.Candidates)) `
        'CANDIDATE_B_PRESENT'

    $Gates.G06_FALSE_POSITIVE = 'PASS'

    $GateReasons.G06_FALSE_POSITIVE =
        'Ambiguous control flow never collapsed into false certainty.'

    Write-Host 'G06_FALSE_POSITIVE        : PASS' `
        -ForegroundColor Green
}
catch {

    $Gates.G06_FALSE_POSITIVE = 'FAIL'

    $GateReasons.G06_FALSE_POSITIVE =
        $_.Exception.Message

    $ExceptionCount++

    Write-Host (
        'G06_FALSE_POSITIVE        : FAIL ({0})' -f
        $_.Exception.Message
    ) -ForegroundColor Red
}

# ============================================================================
# 11. GATE 07 — DETERMINISM
# ============================================================================

try {

    $DeterministicResults =
        [System.Collections.Generic.List[string]]::new()

    for (
        $Run = 1;
        $Run -le 10;
        $Run++
    ) {

        $Tokens = $null
        $Errors = $null

        $DetAst =
            [System.Management.Automation.Language.Parser]::ParseInput(
                $BaselineCode,
                [ref]$Tokens,
                [ref]$Errors
            )

        if (@($Errors).Count -ne 0) {
            throw (
                'Determinism run {0}: parser errors.' -f
                $Run
            )
        }

        $Commands = @(
            $DetAst.FindAll(
                {
                    param($Node)

                    $Node -is
                    [System.Management.Automation.Language.CommandAst] -and

                    @($Node.CommandElements).Count -gt 0 -and

                    [string]$Node.CommandElements[0].Value -eq
                    'New-Item'
                },
                $true
            )
        )

        Assert-Equal `
            @($Commands).Count `
            $ExpectedCaseCount `
            (
                'DETERMINISM_COMMAND_COUNT_RUN_{0}' -f
                $Run
            )

        $RunSignature =
            [System.Collections.Generic.List[string]]::new()

        foreach ($Command in $Commands) {

            $Elements = @($Command.CommandElements)

            $PathAst = $null

            for (
                $j = 1;
                $j -lt $Elements.Count;
                $j++
            ) {

                $Element = $Elements[$j]

                if (
                    $Element -is
                    [System.Management.Automation.Language.CommandParameterAst]
                ) {

                    if (
                        $Element.ParameterName -match
                        '^(Path|LiteralPath)$'
                    ) {

                        if (($j + 1) -lt $Elements.Count) {
                            $PathAst = $Elements[$j + 1]
                        }

                        break
                    }
                }
                elseif (
                    $j -eq 1 -and
                    $Element -isnot
                    [System.Management.Automation.Language.CommandParameterAst]
                ) {

                    $PathAst = $Element
                    break
                }
            }

            if ($null -eq $PathAst) {
                throw (
                    'Determinism run {0}: missing path.' -f
                    $Run
                )
            }

            $Resolution =
                Invoke-StaticResolution `
                    -ExpressionAst $PathAst `
                    -RootAst $DetAst `
                    -CommandAst $Command

            $CandidateSignature =
                @($Resolution.Candidates) -join '||'

            $RunSignature.Add(
                (
                    '{0}|{1}|{2}|{3}' -f
                    $Resolution.Status,
                    $Resolution.Value,
                    $Resolution.Reason,
                    $CandidateSignature
                )
            )
        }

        $DeterministicResults.Add(
            ($RunSignature -join '###')
        )
    }

    $DistinctSignatures =
        @(
            $DeterministicResults |
            Select-Object -Unique
        )

    Assert-Equal `
        @($DistinctSignatures).Count `
        1 `
        'DETERMINISTIC_SIGNATURE_COUNT'

    $Gates.G07_DETERMINISM = 'PASS'

    $GateReasons.G07_DETERMINISM =
        '10 identical executions produced one unique signature.'

    Write-Host 'G07_DETERMINISM           : PASS' `
        -ForegroundColor Green
}
catch {

    $Gates.G07_DETERMINISM = 'FAIL'

    $GateReasons.G07_DETERMINISM =
        $_.Exception.Message

    $ExceptionCount++

    Write-Host (
        'G07_DETERMINISM           : FAIL ({0})' -f
        $_.Exception.Message
    ) -ForegroundColor Red
}

# ============================================================================
# 12. GATE 08 — NO MUTATION
# ============================================================================

$MutationSentinel = $null

try {

    $MutationSentinel =
        Join-Path `
            $env:TEMP `
            (
                'EZZIO_QG_1_2_0_' +
                [guid]::NewGuid().ToString('N') +
                '.txt'
            )

    if (
        Test-Path `
            -LiteralPath $MutationSentinel
    ) {
        Remove-Item `
            -LiteralPath $MutationSentinel `
            -Force
    }

    $BeforeExists =
        Test-Path `
            -LiteralPath $MutationSentinel

    $ReadOnlyCode = @"
`$Destination = '$MutationSentinel'
New-Item -Path `$Destination -ItemType File
"@

    $Tokens = $null
    $Errors = $null

    $ReadOnlyAst =
        [System.Management.Automation.Language.Parser]::ParseInput(
            $ReadOnlyCode,
            [ref]$Tokens,
            [ref]$Errors
        )

    Assert-Equal `
        @($Errors).Count `
        0 `
        'READONLY_SYNTAX'

    $Command = @(
        $ReadOnlyAst.FindAll(
            {
                param($Node)

                $Node -is
                [System.Management.Automation.Language.CommandAst] -and

                @($Node.CommandElements).Count -gt 0 -and

                [string]$Node.CommandElements[0].Value -eq
                'New-Item'
            },
            $true
        )
    )

    Assert-Equal `
        @($Command).Count `
        1 `
        'READONLY_COMMAND_COUNT'

    $PathAst =
        $Command[0].CommandElements[2]

    $null =
        Invoke-StaticResolution `
            -ExpressionAst $PathAst `
            -RootAst $ReadOnlyAst `
            -CommandAst $Command[0]

    $AfterExists =
        Test-Path `
            -LiteralPath $MutationSentinel

    Assert-Equal `
        $AfterExists `
        $BeforeExists `
        'NO_MUTATION_SENTINEL'

    $Gates.G08_NO_MUTATION = 'PASS'

    $GateReasons.G08_NO_MUTATION =
        'AST analysis did not create the filesystem sentinel.'

    Write-Host 'G08_NO_MUTATION           : PASS' `
        -ForegroundColor Green
}
catch {

    $Gates.G08_NO_MUTATION = 'FAIL'

    $GateReasons.G08_NO_MUTATION =
        $_.Exception.Message

    $ExceptionCount++

    Write-Host (
        'G08_NO_MUTATION           : FAIL ({0})' -f
        $_.Exception.Message
    ) -ForegroundColor Red
}
finally {

    if ($null -ne $MutationSentinel) {

        if (
            Test-Path `
                -LiteralPath $MutationSentinel
        ) {
            Remove-Item `
                -LiteralPath $MutationSentinel `
                -Force `
                -ErrorAction SilentlyContinue
        }
    }
}

# ============================================================================
# 13. ADDITIONAL ADVERSARIAL CORPUS
# ============================================================================

$AdditionalPass = 0
$AdditionalFail = 0

Write-Host ''
Write-Host '------------------------------------------------------------' `
    -ForegroundColor DarkCyan

Write-Host ' ADDITIONAL ADVERSARIAL CORPUS' `
    -ForegroundColor DarkCyan

Write-Host '------------------------------------------------------------' `
    -ForegroundColor DarkCyan

foreach ($Test in @($AdditionalCorpus)) {

    $TotalTests++
    $ExecutedTests++

    try {

        # CARDINALITY TESTS
        if (
            $Test.Name -match
            '^(NULL|SCALAR|SINGLETON|EMPTY)_COLLECTION_CARDINALITY$'
        ) {

            switch ($Test.Name) {

                'NULL_COLLECTION_CARDINALITY' {
                    Assert-Equal `
                        (Get-SafeCount $null) `
                        0 `
                        'ADDITIONAL_NULL_COUNT'
                }

                'SCALAR_COLLECTION_CARDINALITY' {
                    Assert-Equal `
                        (Get-SafeCount 'x') `
                        1 `
                        'ADDITIONAL_SCALAR_COUNT'
                }

                'SINGLETON_COLLECTION_CARDINALITY' {
                    Assert-Equal `
                        (Get-SafeCount @('x')) `
                        1 `
                        'ADDITIONAL_SINGLETON_COUNT'
                }

                'EMPTY_COLLECTION_CARDINALITY' {
                    Assert-Equal `
                        (Get-SafeCount @()) `
                        0 `
                        'ADDITIONAL_EMPTY_COUNT'
                }
            }

            $Actual = 'PASS'
        }
        else {

            $Tokens = $null
            $Errors = $null

            $TestAst =
                [System.Management.Automation.Language.Parser]::ParseInput(
                    $Test.Code,
                    [ref]$Tokens,
                    [ref]$Errors
                )

            Assert-Equal `
                @($Errors).Count `
                0 `
                "$($Test.Name)_SYNTAX"

            $Commands = @(
                $TestAst.FindAll(
                    {
                        param($Node)

                        $Node -is
                        [System.Management.Automation.Language.CommandAst] -and

                        @($Node.CommandElements).Count -gt 0 -and

                        [string]$Node.CommandElements[0].Value -eq
                        'New-Item'
                    },
                    $true
                )
            )

            Assert-True `
                (@($Commands).Count -gt 0) `
                "$($Test.Name)_COMMAND_PRESENT"

            $Command = $Commands[0]

            $Elements = @($Command.CommandElements)

            $PathAst = $null

            for (
                $j = 1;
                $j -lt $Elements.Count;
                $j++
            ) {

                $Element = $Elements[$j]

                if (
                    $Element -is
                    [System.Management.Automation.Language.CommandParameterAst]
                ) {

                    if (
                        $Element.ParameterName -match
                        '^(Path|LiteralPath)$'
                    ) {

                        if (($j + 1) -lt $Elements.Count) {
                            $PathAst = $Elements[$j + 1]
                        }

                        break
                    }
                }
                elseif (
                    $j -eq 1 -and
                    $Element -isnot
                    [System.Management.Automation.Language.CommandParameterAst]
                ) {

                    $PathAst = $Element
                    break
                }
            }

            Assert-True `
                ($null -ne $PathAst) `
                "$($Test.Name)_PATH_AST"

            $Resolution =
                Invoke-StaticResolution `
                    -ExpressionAst $PathAst `
                    -RootAst $TestAst `
                    -CommandAst $Command

            $Actual =
                [string]$Resolution.Status

            if (
                $Actual -ne 'RESOLVED' -and
                @($Resolution.Candidates).Count -gt 0
            ) {
                $Actual = 'UNRESOLVED_CANDIDATES'
            }
        }

        if ($Actual -eq [string]$Test.Expected) {

            $AdditionalPass++
            $PassedTests++

            Write-Host (
                '{0,-35} PASS' -f
                $Test.Name
            ) -ForegroundColor Green
        }
        else {

            $AdditionalFail++
            $FailedTests++

            Write-Host (
                '{0,-35} FAIL | Expected={1} Actual={2}' -f
                $Test.Name,
                $Test.Expected,
                $Actual
            ) -ForegroundColor Red
        }
    }
    catch {

        $AdditionalFail++
        $FailedTests++
        $ExceptionCount++

        Write-Host (
            '{0,-35} EXCEPTION | {1}' -f
            $Test.Name,
            $_.Exception.Message
        ) -ForegroundColor Red
    }
}

if (
    $AdditionalFail -eq 0 -and
    $AdditionalPass -eq @($AdditionalCorpus).Count
) {

    Write-Host ''
    Write-Host 'ADVERSARIAL CORPUS          : PASS' `
        -ForegroundColor Green
}
else {

    Write-Host ''
    Write-Host 'ADVERSARIAL CORPUS          : FAIL' `
        -ForegroundColor Red
}

# ============================================================================
# 14. GATE 09 — HARNESS INTEGRITY
# ============================================================================

try {

    Assert-Equal `
        $ExecutedTests `
        $TotalTests `
        'ALL_TESTS_ACCOUNTED'

    Assert-Equal `
        ($PassedTests + $FailedTests) `
        $ExecutedTests `
        'PASS_FAIL_ACCOUNTING'

    Assert-Equal `
        $FailedTests `
        0 `
        'FAILED_TEST_COUNT'

    # IMPORTANT :
    # G09 est évalué avant G10, mais les exceptions précédentes doivent
    # être connues. Une exception signifie que le harness n'est pas intégral.
    Assert-Equal `
        $ExceptionCount `
        0 `
        'EXCEPTION_ACCOUNTING'

    Assert-Equal `
        $AdditionalPass `
        @($AdditionalCorpus).Count `
        'ADDITIONAL_CORPUS_ACCOUNTING'

    Assert-Equal `
        $AdditionalFail `
        0 `
        'ADDITIONAL_CORPUS_FAILURES'

    $Gates.G09_HARNESS_INTEGRITY = 'PASS'

    $GateReasons.G09_HARNESS_INTEGRITY =
        'All tests accounted exactly once; zero failures and zero exceptions.'

    Write-Host 'G09_HARNESS_INTEGRITY     : PASS' `
        -ForegroundColor Green
}
catch {

    $Gates.G09_HARNESS_INTEGRITY = 'FAIL'

    $GateReasons.G09_HARNESS_INTEGRITY =
        $_.Exception.Message

    $ExceptionCount++

    Write-Host (
        'G09_HARNESS_INTEGRITY     : FAIL ({0})' -f
        $_.Exception.Message
    ) -ForegroundColor Red
}

# ============================================================================
# 15. GATE 10 — ZERO EXCEPTION
# ============================================================================

if ($ExceptionCount -eq 0) {

    $Gates.G10_ZERO_EXCEPTION = 'PASS'

    $GateReasons.G10_ZERO_EXCEPTION =
        'Zero exceptions.'

    Write-Host 'G10_ZERO_EXCEPTION        : PASS' `
        -ForegroundColor Green
}
else {

    $Gates.G10_ZERO_EXCEPTION = 'FAIL'

    $GateReasons.G10_ZERO_EXCEPTION =
        "ExceptionCount=$ExceptionCount."

    Write-Host (
        'G10_ZERO_EXCEPTION        : FAIL ({0})' -f
        $ExceptionCount
    ) -ForegroundColor Red
}

# ============================================================================
# 16. FINAL ACCOUNTING
# ============================================================================

$AllGates =
    @($Gates.GetEnumerator())

$GatePassCount =
    @(
        $AllGates |
        Where-Object {
            $_.Value -eq 'PASS'
        }
    ).Count

$GateFailCount =
    @(
        $AllGates |
        Where-Object {
            $_.Value -ne 'PASS'
        }
    ).Count

$AllGatesPass =
    $GateFailCount -eq 0

$AllTestsAccounted =
    $ExecutedTests -eq $TotalTests

$NoFailures =
    $FailedTests -eq 0

$NoExceptions =
    $ExceptionCount -eq 0

$Quality100 =
    $AllGatesPass -and
    $AllTestsAccounted -and
    $NoFailures -and
    $NoExceptions

# ============================================================================
# 17. FORENSIC REPORT
# ============================================================================

Write-Host ''
Write-Host '============================================================' `
    -ForegroundColor Cyan

Write-Host ' FINAL FORENSIC QUALITY REPORT' `
    -ForegroundColor Cyan

Write-Host '============================================================' `
    -ForegroundColor Cyan

Write-Host ''

Write-Host (
    'QUALITY GATES : {0} / {1}' -f
    $GatePassCount,
    @($AllGates).Count
)

Write-Host "TOTAL TESTS   : $TotalTests"
Write-Host "EXECUTED      : $ExecutedTests"
Write-Host "PASSED        : $PassedTests"
Write-Host "FAILED        : $FailedTests"
Write-Host "EXCEPTIONS    : $ExceptionCount"

Write-Host ''

foreach ($Gate in $AllGates) {

    $GateColor =
        if ($Gate.Value -eq 'PASS') {
            'Green'
        }
        else {
            'Red'
        }

    Write-Host (
        '{0,-28} : {1}' -f
        $Gate.Key,
        $Gate.Value
    ) -ForegroundColor $GateColor
}

# ============================================================================
# 18. CERTIFICATION VERDICT
# ============================================================================

$Verdict = 'FORENSIC_FAIL_CLOSED'
$ExitCode = 1

if ($Quality100) {

    $Verdict = 'CERTIFIED'
    $ExitCode = 0

    Write-Host ''
    Write-Host '============================================================' `
        -ForegroundColor Green

    Write-Host ' FINAL : CERTIFIED' `
        -ForegroundColor Green

    Write-Host ' QUALITY : 100%' `
        -ForegroundColor Green

    Write-Host '============================================================' `
        -ForegroundColor Green
}
else {

    Write-Host ''
    Write-Host '============================================================' `
        -ForegroundColor Red

    Write-Host ' FINAL : FORENSIC_FAIL_CLOSED' `
        -ForegroundColor Red

    Write-Host ' QUALITY : 100% NOT ESTABLISHED' `
        -ForegroundColor Red

    Write-Host '============================================================' `
        -ForegroundColor Red

    Write-Host ''
    Write-Host 'FAILURE REASONS:' `
        -ForegroundColor Yellow

    foreach ($Gate in $AllGates) {

        if ($Gate.Value -ne 'PASS') {

            $Reason =
                if ($GateReasons.Contains($Gate.Key)) {
                    $GateReasons[$Gate.Key]
                }
                else {
                    'No reason recorded.'
                }

            Write-Host (
                ' - {0}: {1}' -f
                $Gate.Key,
                $Reason
            ) -ForegroundColor Yellow
        }
    }
}

# ============================================================================
# 19. MACHINE-READABLE SUMMARY
# ============================================================================

$Summary = [ordered]@{
    Product            = 'E-ZZIO'
    Component          = 'Static Resolver'
    QualityGateVersion = $Version
    Verdict             = $Verdict
    Quality100          = $Quality100
    GatesTotal          = @($AllGates).Count
    GatesPassed         = $GatePassCount
    GatesFailed         = $GateFailCount
    TestsTotal          = $TotalTests
    TestsExecuted       = $ExecutedTests
    TestsPassed         = $PassedTests
    TestsFailed         = $FailedTests
    Exceptions          = $ExceptionCount
    BaselineExpected    = $ExpectedCaseCount
    BaselineExecuted    = @($BaselineResults).Count
    AdditionalExpected  = @($AdditionalCorpus).Count
    AdditionalPassed    = $AdditionalPass
    AdditionalFailed    = $AdditionalFail
    ExitCode            = $ExitCode
}

Write-Host ''
Write-Host 'MACHINE SUMMARY:' `
    -ForegroundColor DarkGray

foreach ($Entry in $Summary.GetEnumerator()) {

    Write-Host (
        '  {0} = {1}' -f
        $Entry.Key,
        $Entry.Value
    ) -ForegroundColor DarkGray
}

Write-Host ''

# ============================================================================
# 20. HARD FAIL-CLOSED EXIT
# ============================================================================

if (-not $Quality100) {
    exit 1
}

exit 0