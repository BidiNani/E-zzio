# ============================================================================
# E-ZZIO — CRITICAL ROOT-CAUSE TRIAGE v1.0.0
# ============================================================================
# READ-ONLY / NO EXECUTION / NO MUTATION
#
# Objectif :
#   Transformer les 70 CRITICAL en cartographie de causes probables.
#
# Aucun fichier E-ZZIO n'est modifié.
# ============================================================================

[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$RunRoot = 'G:\AI\E-zzio\_EZZIO_TRUTH_REPORTS\20260820_193008_236_132bbbbb5486'

$FindingsPath = Join-Path `
    $RunRoot `
    'FINDINGS\EZZIO_TRUTH_FORENSIC_FINDINGS.json'

if (-not (Test-Path -LiteralPath $FindingsPath -PathType Leaf)) {
    throw "Findings introuvable : $FindingsPath"
}

$Findings = @(
    Get-Content `
        -LiteralPath $FindingsPath `
        -Raw `
        -ErrorAction Stop |
    ConvertFrom-Json `
        -ErrorAction Stop
)

$Critical = @(
    $Findings |
    Where-Object {
        [string]$_.Severity -eq 'CRITICAL'
    }
)

$TriageRoot = Join-Path $RunRoot 'CRITICAL_TRIAGE'

New-Item `
    -ItemType Directory `
    -Path $TriageRoot `
    -Force |
    Out-Null

# ============================================================================
# 1 — GROUP BY FILE
# ============================================================================

$ByFile = @(
    $Critical |
    Group-Object Path |
    Sort-Object Count -Descending |
    ForEach-Object {

        [PSCustomObject]@{
            Findings = $_.Count
            Path     = $_.Name
        }
    }
)

$ByFile |
    ConvertTo-Json -Depth 20 |
    Set-Content `
        -LiteralPath (Join-Path $TriageRoot 'CRITICAL_BY_FILE.json') `
        -Encoding UTF8

$ByFile |
    Export-Csv `
        -LiteralPath (Join-Path $TriageRoot 'CRITICAL_BY_FILE.csv') `
        -NoTypeInformation `
        -Encoding UTF8

# ============================================================================
# 2 — GROUP BY ERROR ID
# ============================================================================

$ByErrorId = @(
    $Critical |
    ForEach-Object {

        $Evidence = $_.Evidence

        if ($null -ne $Evidence) {

            if ($Evidence -is [System.Array]) {

                foreach ($Item in $Evidence) {

                    [PSCustomObject]@{
                        ErrorId = [string]$Item.ErrorId
                        Code    = [string]$_.Code
                        Path    = [string]$_.Path
                        Message = [string]$Item.Message
                    }
                }
            }
            else {

                [PSCustomObject]@{
                    ErrorId = [string]$Evidence.ErrorId
                    Code    = [string]$_.Code
                    Path    = [string]$_.Path
                    Message = [string]$Evidence.Message
                }
            }
        }
        else {

            [PSCustomObject]@{
                ErrorId = ''
                Code    = [string]$_.Code
                Path    = [string]$_.Path
                Message = [string]$_.Message
            }
        }
    }
)

$ByErrorIdSummary = @(
    $ByErrorId |
    Group-Object ErrorId |
    Sort-Object Count -Descending |
    ForEach-Object {

        [PSCustomObject]@{
            Count   = $_.Count
            ErrorId = $_.Name
        }
    }
)

$ByErrorId |
    ConvertTo-Json -Depth 20 |
    Set-Content `
        -LiteralPath (Join-Path $TriageRoot 'CRITICAL_ERROR_DETAILS.json') `
        -Encoding UTF8

$ByErrorIdSummary |
    ConvertTo-Json -Depth 20 |
    Set-Content `
        -LiteralPath (Join-Path $TriageRoot 'CRITICAL_BY_ERROR_ID.json') `
        -Encoding UTF8

# ============================================================================
# 3 — GROUP BY FILE + ERROR ID
# ============================================================================

$ByFileAndError = @(
    $ByErrorId |
    Group-Object Path,ErrorId |
    Sort-Object Count -Descending |
    ForEach-Object {

        $Parts = $_.Name -split ', ', 2

        [PSCustomObject]@{
            Count   = $_.Count
            Path    = $Parts[0]
            ErrorId = if ($Parts.Count -gt 1) {
                $Parts[1]
            }
            else {
                ''
            }
        }
    }
)

$ByFileAndError |
    ConvertTo-Json -Depth 20 |
    Set-Content `
        -LiteralPath (Join-Path $TriageRoot 'CRITICAL_BY_FILE_AND_ERROR.json') `
        -Encoding UTF8

# ============================================================================
# 4 — IDENTIFICATION DES FAMILLES DE CAUSES
# ============================================================================

$Families = [System.Collections.Generic.List[object]]::new()

$Patterns = @(
    [PSCustomObject]@{
        Family = 'PARENTHESIS_STRUCTURE'
        Regex  = 'MissingEndParenthesis|MissingEndParenthesisInMethodCall|UnexpectedToken.*\)'
    }

    [PSCustomObject]@{
        Family = 'BRACE_STRUCTURE'
        Regex  = 'MissingEndCurlyBrace|UnexpectedToken.*\}'
    }

    [PSCustomObject]@{
        Family = 'TRY_CATCH_STRUCTURE'
        Regex  = 'MissingCatchOrFinally'
    }

    [PSCustomObject]@{
        Family = 'USING_DIRECTIVE'
        Regex  = 'MissingUsingStatementDirective|UsingMustBeAtStartOfScript'
    }

    [PSCustomObject]@{
        Family = 'VARIABLE_REFERENCE'
        Regex  = 'InvalidVariableReference|InvalidVariableReferenceWithDrive'
    }

    [PSCustomObject]@{
        Family = 'BRACKET_STRUCTURE'
        Regex  = 'EndSquareBracketExpectedAtEndOfAttribute'
    }

    [PSCustomObject]@{
        Family = 'STRING_STRUCTURE'
        Regex  = 'TerminatorExpectedAtEndOfString'
    }

    [PSCustomObject]@{
        Family = 'OPERATOR_EXPRESSION'
        Regex  = 'ExpectedValueExpression|UnexpectedToken.*ne'
    }

    [PSCustomObject]@{
        Family = 'JSON_STRUCTURE'
        Regex  = 'JSON_SYNTAX_ERROR'
    }
)

foreach ($Pattern in $Patterns) {

    $Matches = @(
        $Critical |
        Where-Object {

            $Text = (
                [string]$_.Code + ' ' +
                [string]$_.Message + ' ' +
                [string]$_.Path
            )

            $Text -match $Pattern.Regex
        }
    )

    if ($Matches.Count -gt 0) {

        [void]$Families.Add(
            [PSCustomObject]@{
                Family      = $Pattern.Family
                FindingCount = $Matches.Count
                Files       = @(
                    $Matches |
                    Select-Object -ExpandProperty Path -Unique
                )
            }
        )
    }
}

$Families |
    ConvertTo-Json -Depth 30 |
    Set-Content `
        -LiteralPath (Join-Path $TriageRoot 'CRITICAL_CAUSE_FAMILIES.json') `
        -Encoding UTF8

# ============================================================================
# 5 — HUMAN REPORT
# ============================================================================

$Report = [System.Collections.Generic.List[string]]::new()

[void]$Report.Add('============================================================================')
[void]$Report.Add('E-ZZIO — CRITICAL ROOT-CAUSE TRIAGE v1.0.0')
[void]$Report.Add('============================================================================')
[void]$Report.Add('')
[void]$Report.Add("RUN ROOT       : $RunRoot")
[void]$Report.Add("TOTAL FINDINGS : $($Critical.Count)")
[void]$Report.Add("FILES AFFECTED : $(@($Critical | Select-Object -ExpandProperty Path -Unique).Count)")
[void]$Report.Add('')
[void]$Report.Add('-------------------- BY FILE ----------------------------------------------')

foreach ($Item in $ByFile) {
    [void]$Report.Add(
        ('{0,4}  {1}' -f $Item.Findings, $Item.Path)
    )
}

[void]$Report.Add('')
[void]$Report.Add('-------------------- ERROR IDS -------------------------------------------')

foreach ($Item in $ByErrorIdSummary) {
    [void]$Report.Add(
        ('{0,4}  {1}' -f $Item.Count, $Item.ErrorId)
    )
}

[void]$Report.Add('')
[void]$Report.Add('-------------------- CAUSE FAMILIES -------------------------------------')

foreach ($Item in $Families) {
    [void]$Report.Add(
        "$($Item.Family) : $($Item.FindingCount)"
    )

    foreach ($Path in $Item.Files) {
        [void]$Report.Add(
            "    - $Path"
        )
    }
}

[void]$Report.Add('')
[void]$Report.Add('-------------------- INTERPRETATION -------------------------------------')
[void]$Report.Add(
    'Ces résultats sont une classification forensic et ne constituent PAS'
)
[void]$Report.Add(
    'une preuve qu''un finding individuel est une cause racine.'
)
[void]$Report.Add(
    'Aucune correction automatique n''a été effectuée.'
)
[void]$Report.Add('')
[void]$Report.Add(
    'NEXT STEP : examiner les fichiers par défaut structurel primaire avant'
)
[void]$Report.Add(
    'toute modification.'
)

$Report |
    Set-Content `
        -LiteralPath (Join-Path $TriageRoot 'CRITICAL_ROOT_CAUSE_TRIAGE.txt') `
        -Encoding UTF8

# ============================================================================
# CONSOLE
# ============================================================================

Write-Host ''
Write-Host '============================================================================' -ForegroundColor Cyan
Write-Host ' E-ZZIO — CRITICAL ROOT-CAUSE TRIAGE COMPLETE' -ForegroundColor Cyan
Write-Host '============================================================================' -ForegroundColor Cyan
Write-Host ''
Write-Host "CRITICAL       : $($Critical.Count)"
Write-Host "FILES AFFECTED : $(@($Critical | Select-Object -ExpandProperty Path -Unique).Count)"
Write-Host ''
Write-Host 'BY FILE :' -ForegroundColor Yellow
Write-Host ''

$ByFile |
    Format-Table -AutoSize

Write-Host ''
Write-Host 'CAUSE FAMILIES :' -ForegroundColor Yellow
Write-Host ''

$Families |
    Select-Object Family,FindingCount |
    Format-Table -AutoSize

Write-Host ''
Write-Host "TRIAGE ROOT : $TriageRoot"
Write-Host ''

exit 0
