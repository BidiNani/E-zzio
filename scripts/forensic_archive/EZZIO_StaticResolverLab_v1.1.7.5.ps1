#Requires -Version 7.0

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$TargetToMatch = 'G:\AI\E-zzio\EZZIO_Freeze_Certification_v1.1.1.ps1'

# ============================================================================
# 1. CORPUS DE TEST ADVERSARIAL
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
if ($false) { $Destination7 = 'C:\fake_malicious.txt' }
$Destination7 = 'C:\real_safe.txt'
New-Item -Path $Destination7 -ItemType File

# 08 — Ambiguïté Statique (If/Else)
if ($true) { $Destination8 = 'C:\path_A.txt' } 
else { $Destination8 = 'C:\path_B.txt' }
New-Item -Path $Destination8 -ItemType File

# 09 — Join-Path Pathologique
$Root9 = 'G:\AI\E-zzio\'
$Destination9 = Join-Path $Root9 '\logs\\x.log'
New-Item -Path $Destination9 -ItemType File

# 10 — Ambiguïté Dynamique
if ((Get-Random) -gt 5) { $Destination10 = 'C:\dyn_path_A.txt' } 
else { $Destination10 = 'C:\dyn_path_B.txt' }
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
# 2. MOTEUR DE RÉSOLUTION AST (v1.1.7.5)
# ============================================================================

function Test-IsConditionalRelativeTo {
    param($AssignNode, $CommandNode)
    $Parent = $AssignNode.Parent
    while ($Parent -and $Parent -isnot [System.Management.Automation.Language.ScriptBlockAst]) {
        if ($Parent -is [System.Management.Automation.Language.IfStatementAst] -or 
            $Parent -is [System.Management.Automation.Language.ForEachStatementAst] -or 
            $Parent -is [System.Management.Automation.Language.WhileStatementAst]) {
            if (-not $Parent.Find({ param($n) $n -eq $CommandNode }, $true)) { return $true }
        }
        $Parent = $Parent.Parent
    }
    return $false
}

function Invoke-StaticResolution {
    param(
        [Parameter(Mandatory=$true)] $ExpressionAst,
        [Parameter(Mandatory=$true)] $RootAst,
        [Parameter(Mandatory=$true)] $CommandAst,
        [int]$Depth = 0
    )

    function New-Res($Status, $Value, $Confidence, $Reason, $Cands=@()) {
        # Protection explicite si $Cands est nul pour éviter l'erreur .Count introuvable
        if (-not $Cands) { $Cands = @() }
        return [ordered]@{ Status=$Status; Value=$Value; Confidence=$Confidence; Reason=$Reason; Candidates=$Cands }
    }

    if ($Depth -gt 15) { return New-Res 'UNRESOLVED' $null 'NONE' 'DEPTH_LIMIT_REACHED' }

    $unwrapped = $true
    while ($unwrapped) {
        $unwrapped = $false
        if ($ExpressionAst -is [System.Management.Automation.Language.PipelineAst] -and $ExpressionAst.PipelineElements.Count -eq 1) {
            $ExpressionAst = $ExpressionAst.PipelineElements[0]; $unwrapped = $true
        } elseif ($ExpressionAst -is [System.Management.Automation.Language.CommandExpressionAst]) {
            $ExpressionAst = $ExpressionAst.Expression; $unwrapped = $true
        } elseif ($ExpressionAst -is [System.Management.Automation.Language.ParenExpressionAst]) {
            $ExpressionAst = $ExpressionAst.Pipeline; $unwrapped = $true
        }
    }

    # CAS A : Littéral
    if ($ExpressionAst -is [System.Management.Automation.Language.StringConstantExpressionAst]) {
        return New-Res 'RESOLVED' $ExpressionAst.Value 'STATIC_EXACT' 'LITERAL_VALUE'
    }

    # CAS B : Index Array
    if ($ExpressionAst -is [System.Management.Automation.Language.IndexExpressionAst]) {
        $Targ = $ExpressionAst.Target
        $Indx = $ExpressionAst.Index
        if ($Targ -is [System.Management.Automation.Language.VariableExpressionAst] -and $Indx -is [System.Management.Automation.Language.ConstantExpressionAst]) {
            $VName = $Targ.VariablePath.UserPath
            $IdxVal = [int]$Indx.Value
            
            $ArrAssigns = @($RootAst.FindAll({ 
                param($n) 
                $n -is [System.Management.Automation.Language.AssignmentStatementAst] -and 
                $n.Left -is [System.Management.Automation.Language.VariableExpressionAst] -and 
                $n.Left.VariablePath.UserPath -eq $VName -and 
                $n.Extent.StartLineNumber -lt $CommandAst.Extent.StartLineNumber 
            }, $true)) | Sort-Object { $_.Extent.StartLineNumber } -Descending
            
            if ($ArrAssigns.Count -gt 0) {
                $ArrLits = @($ArrAssigns[0].Right.FindAll({ param($n) $n -is [System.Management.Automation.Language.ArrayLiteralAst] }, $true))
                if ($ArrLits.Count -gt 0) {
                    $Elems = $ArrLits[0].Elements
                    if ($IdxVal -ge 0 -and $IdxVal -lt $Elems.Count) {
                        $ElRes = Invoke-StaticResolution -ExpressionAst $Elems[$IdxVal] -RootAst $RootAst -CommandAst $CommandAst -Depth ($Depth+1)
                        if ($ElRes.Status -eq 'RESOLVED') { 
                            return New-Res 'RESOLVED' $ElRes.Value 'STATIC_ARRAY_INDEX' 'STATIC_ARRAY_INDEX'
                        }
                    }
                }
            }
        }
        return New-Res 'UNRESOLVED' $null 'NONE' 'DYNAMIC_INDEX_OR_UNSUPPORTED_ARRAY'
    }

    # CAS C : Variable
    if ($ExpressionAst -is [System.Management.Automation.Language.VariableExpressionAst]) {
        $VarName = $ExpressionAst.VariablePath.UserPath
        if ($VarName -match '^(args|_|PSItem|env:.*)$') { return New-Res 'UNRESOLVED' $null 'NONE' 'DYNAMIC_VARIABLE' }

        $Loops = @($RootAst.FindAll({ 
            param($n) 
            $n -is [System.Management.Automation.Language.ForEachStatementAst] -and 
            $n.Variable.VariablePath.UserPath -eq $VarName -and 
            $n.Extent.StartLineNumber -lt $CommandAst.Extent.StartLineNumber 
        }, $true))
        
        foreach ($Loop in $Loops) {
            if ($Loop.Body.Find({param($n) $n -eq $CommandAst}, $true)) {
                $ArrLits = @($Loop.Condition.FindAll({param($n) $n -is [System.Management.Automation.Language.ArrayLiteralAst]}, $true))
                if ($ArrLits.Count -gt 0) {
                    $Cands = [System.Collections.Generic.List[string]]::new()
                    foreach ($El in $ArrLits[0].Elements) {
                        $ElRes = Invoke-StaticResolution -ExpressionAst $El -RootAst $RootAst -CommandAst $CommandAst -Depth ($Depth+1)
                        if ($ElRes.Status -eq 'RESOLVED') { $Cands.Add($ElRes.Value) }
                    }
                    if ($Cands.Count -eq $ArrLits[0].Elements.Count) {
                        return New-Res 'UNRESOLVED' $null 'STATIC_LOOP_CANDIDATES' 'LOOP_VARIABLE' $Cands.ToArray()
                    }
                }
            }
        }

        $Assignments = @($RootAst.FindAll({ 
            param($n) 
            $n -is [System.Management.Automation.Language.AssignmentStatementAst] -and 
            $n.Left -is [System.Management.Automation.Language.VariableExpressionAst] -and 
            $n.Left.VariablePath.UserPath -eq $VarName -and 
            $n.Extent.StartLineNumber -lt $CommandAst.Extent.StartLineNumber 
        }, $true))
        
        if ($Assignments.Count -eq 0) { return New-Res 'UNRESOLVED' $null 'NONE' 'NO_ASSIGNMENT_FOUND' }

        $Assignments = $Assignments | Sort-Object { $_.Extent.StartLineNumber } -Descending
        $LatestAssign = $Assignments[0]

        if (Test-IsConditionalRelativeTo -AssignNode $LatestAssign -CommandNode $CommandAst) {
            $Cands = [System.Collections.Generic.List[string]]::new()
            foreach ($Assign in $Assignments) {
                $SubRes = Invoke-StaticResolution -ExpressionAst $Assign.Right -RootAst $RootAst -CommandAst $CommandAst -Depth ($Depth+1)
                if ($SubRes.Status -eq 'RESOLVED' -and $SubRes.Value -notin $Cands) { $Cands.Add($SubRes.Value) }
            }
            return New-Res 'UNRESOLVED' $null 'NONE' 'AMBIGUOUS_CONTROL_FLOW' $Cands.ToArray()
        }

        $Res = Invoke-StaticResolution -ExpressionAst $LatestAssign.Right -RootAst $RootAst -CommandAst $CommandAst -Depth ($Depth+1)
        if ($Res.Status -eq 'RESOLVED') { $Res.Confidence = 'STATIC_VARIABLE_TRACE' }
        return $Res
    }

    # CAS D : ExpandableString
    if ($ExpressionAst -is [System.Management.Automation.Language.ExpandableStringExpressionAst]) {
        $BaseCandidates = @($ExpressionAst.Value)
        $ProducedCandidates = $false

        foreach ($NestedAst in $ExpressionAst.NestedExpressions) {
            $NestedRes = Invoke-StaticResolution -ExpressionAst $NestedAst -RootAst $RootAst -CommandAst $CommandAst -Depth ($Depth+1)
            
            if ($NestedRes.Status -eq 'RESOLVED') {
                $NewCands = @()
                foreach ($c in $BaseCandidates) { $NewCands += $c.Replace($NestedAst.Extent.Text, $NestedRes.Value) }
                $BaseCandidates = $NewCands
            } elseif ($NestedRes.Candidates.Count -gt 0) {
                $NewCands = @()
                foreach ($c in $BaseCandidates) {
                    foreach ($subC in $NestedRes.Candidates) { $NewCands += $c.Replace($NestedAst.Extent.Text, $subC) }
                }
                $BaseCandidates = $NewCands
                $ProducedCandidates = $true
            } else {
                return New-Res 'UNRESOLVED' $null 'NONE' 'UNRESOLVED_NESTED_EXPRESSION'
            }
        }

        if (-not $ProducedCandidates -and $BaseCandidates.Count -eq 1) {
            return New-Res 'RESOLVED' $BaseCandidates[0] 'STATIC_EXPANDABLE_STRING' 'ALL_NESTED_RESOLVED'
        } else {
            return New-Res 'UNRESOLVED' $null 'EXPANDABLE_STRING_CANDIDATES' 'MULTIPLE_CANDIDATES_GENERATED' $BaseCandidates
        }
    }

    # CAS E : Join-Path
    if ($ExpressionAst -is [System.Management.Automation.Language.CommandAst]) {
        $CmdName = $ExpressionAst.CommandElements[0].Value
        if ($CmdName -eq 'Join-Path' -and $ExpressionAst.CommandElements.Count -ge 3) {
            $Path1 = Invoke-StaticResolution -ExpressionAst $ExpressionAst.CommandElements[1] -RootAst $RootAst -CommandAst $CommandAst -Depth ($Depth+1)
            $Path2 = Invoke-StaticResolution -ExpressionAst $ExpressionAst.CommandElements[2] -RootAst $RootAst -CommandAst $CommandAst -Depth ($Depth+1)
            
            if ($Path1.Status -eq 'RESOLVED' -and $Path2.Status -eq 'RESOLVED') {
                $P1 = $Path1.Value.TrimEnd('\', '/')
                $P2 = $Path2.Value.TrimStart('\', '/')
                $Combined = $P1 + "\" + $P2
                $IsUNC = $Combined.StartsWith('\\')
                $Combined = $Combined -replace '\\+', '\'
                if ($IsUNC) { $Combined = '\' + $Combined }
                return New-Res 'RESOLVED' $Combined 'STATIC_JOIN_PATH_NORMALIZED' 'JOIN_PATH_EVALUATED'
            }
        }
        return New-Res 'UNRESOLVED' $null 'NONE' "DYNAMIC_COMMAND_$CmdName"
    }

    # CAS F : Concaténation
    if ($ExpressionAst -is [System.Management.Automation.Language.BinaryExpressionAst] -and $ExpressionAst.Operator -eq 'Plus') {
        $LeftRes = Invoke-StaticResolution -ExpressionAst $ExpressionAst.Left -RootAst $RootAst -CommandAst $CommandAst -Depth ($Depth+1)
        $RightRes = Invoke-StaticResolution -ExpressionAst $ExpressionAst.Right -RootAst $RootAst -CommandAst $CommandAst -Depth ($Depth+1)
        if ($LeftRes.Status -eq 'RESOLVED' -and $RightRes.Status -eq 'RESOLVED') { 
            return New-Res 'RESOLVED' ($LeftRes.Value + $RightRes.Value) 'STATIC_CONCATENATION' 'DETERMINISTIC_CONCAT' 
        }
        return New-Res 'UNRESOLVED' $null 'NONE' 'PARTIAL_CONCATENATION'
    }

    return New-Res 'UNRESOLVED' $null 'NONE' "UNSUPPORTED_AST_NODE_$(($ExpressionAst.GetType().Name))"
}

# ============================================================================
# 3. HARNESS D'EXÉCUTION ORACLE
# ============================================================================
Write-Host ''
Write-Host '============================================================' -ForegroundColor Cyan
Write-Host ' STATIC RESOLVER LAB (v1.1.7.5 THE ORACLE)' -ForegroundColor Cyan
Write-Host '============================================================' -ForegroundColor Cyan
Write-Host ''

$Stats = [ordered]@{ Total=0; OraclePass=0; OracleFail=0; Exception=$null }

try {
    $Tokens = $null; $Errors = $null
    $Ast = [System.Management.Automation.Language.Parser]::ParseInput($TestCode, [ref]$Tokens, [ref]$Errors)
    if ($Errors.Count -gt 0) { throw "Erreur AST Corpus" }

    $NewItems = @($Ast.FindAll({ param($Node) $Node -is [System.Management.Automation.Language.CommandAst] -and $Node.CommandElements[0].Value -eq 'New-Item' }, $true))
    $Stats.Total = $NewItems.Count

    for ($i = 0; $i -lt $NewItems.Count; $i++) {
        $Cmd = $NewItems[$i]
        
        $PathArgAst = $null
        for ($j = 1; $j -lt $Cmd.CommandElements.Count; $j++) {
            $El = $Cmd.CommandElements[$j]
            if ($El -is [System.Management.Automation.Language.CommandParameterAst]) {
                if ($El.ParameterName -match '^(Path|LiteralPath)$') { $PathArgAst = $Cmd.CommandElements[$j+1]; break }
            } elseif ($j -eq 1 -and $El -isnot [System.Management.Automation.Language.CommandParameterAst]) {
                $PathArgAst = $El; break
            }
        }

        # RÉSOLUTION
        $Resolution = Invoke-StaticResolution -ExpressionAst $PathArgAst -RootAst $Ast -CommandAst $Cmd

        # CLASSIFICATION ACTUAL vs EXPECTED
        $ActualState = $Resolution.Status
        if ($Resolution.Status -eq 'RESOLVED') {
            if ($Resolution.Value -eq $TargetToMatch) { $ActualState = 'RESOLVED_TARGET' }
        } else {
            if ($Resolution.Candidates -and $Resolution.Candidates.Count -gt 0) { $ActualState = 'UNRESOLVED_CANDIDATES' }
        }

        $ExpectedState = $ExpectedOracle[$i]
        $OracleMatch = ($ActualState -eq $ExpectedState)

        if ($OracleMatch) { $Stats.OraclePass++ } else { $Stats.OracleFail++ }

        $Color = if ($OracleMatch) { 'Green' } else { 'Red' }
        Write-Host "CASE $(('{0:D2}' -f ($i+1))) | Expected: $ExpectedState | Actual: $ActualState | " -NoNewline
        Write-Host "[$(if ($OracleMatch) {'PASS'} else {'FAIL'})]" -ForegroundColor $Color

        if (-not $OracleMatch) {
            Write-Host "  -> Value/Reason : $($Resolution.Value) $($Resolution.Reason)" -ForegroundColor Red
        }
    }
}
catch {
    $Stats.Exception = $_.Exception.Message
}

# ============================================================================
# 4. VERDICT FORENSIC
# ============================================================================
Write-Host ''
Write-Host '============================================================' -ForegroundColor Cyan
Write-Host ' RÉSULTATS DU LAB & QUALITY GATES' -ForegroundColor Cyan
Write-Host '============================================================' -ForegroundColor Cyan

Write-Host "EXPECTED CASES : $($Stats.Total)"
Write-Host "CORRECT        : $($Stats.OraclePass)"
Write-Host "INCORRECT      : $($Stats.OracleFail)"

$ExceptionCount = 0
if ($Stats.Exception) { $ExceptionCount = 1 }
Write-Host "EXCEPTIONS     : $ExceptionCount`n"

$Verdict = 'FORENSIC_PASS'

if (-not $Stats.Exception) { Write-Host "  SG_RESOLVER_INTEGRITY    : PASS" -ForegroundColor Green } 
else {
    Write-Host "  SG_RESOLVER_INTEGRITY    : FAIL ($($Stats.Exception))" -ForegroundColor Red
    $Verdict = 'FORENSIC_FAIL_CLOSED'
}

if ($Stats.OracleFail -eq 0 -and $Stats.Total -eq 15) {
    Write-Host "  SG_CORPUS_ORACLE         : PASS" -ForegroundColor Green
} else {
    Write-Host "  SG_CORPUS_ORACLE         : FAIL" -ForegroundColor Red
    if ($Verdict -ne 'FORENSIC_FAIL_CLOSED') { $Verdict = 'FORENSIC_FAIL' }
}

$FinalColor = if ($Verdict -eq 'FORENSIC_PASS') { 'Green' } else { 'Red' }

Write-Host "`nFINAL :"
Write-Host "  $Verdict" -ForegroundColor $FinalColor
Write-Host '============================================================' -ForegroundColor Cyan

if ($Host.Name -match 'Console') { Read-Host 'Appuyez sur Entrée pour fermer' }