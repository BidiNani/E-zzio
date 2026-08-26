# ============================================================================
# E-ZZIO — TRUTH PROBLEM FORENSIC TRIAGE
# Version : 1.0.1
#
# PURPOSE
#   Analyse exclusivement le rapport EZZIO_PROJECT_PROBLEMS.json produit par
#   E-ZZIO PROJECT TRUTH ENGINE.
#
# MODE
#   READ-ONLY / FORENSIC / FAIL-CLOSED
#
# HARDENING 1.0.1
#   - Ne suppose aucune propriété facultative dans les problèmes.
#   - Absence de propriété = $null, jamais une assertion.
#   - Structure des problèmes inspectée dynamiquement.
#   - Comptage séparé des entrées de problèmes et des types.
#   - Détection des doublons sans dépendre de propriétés inexistantes.
#   - Aucun fichier source modifié.
#   - Aucun rapport source réécrit.
# ============================================================================

& {

    Set-StrictMode -Version Latest
    $ErrorActionPreference = 'Stop'

    # =========================================================================
    # CONFIGURATION
    # =========================================================================

    $Version = '1.0.1'

    $ProjectRoot = 'G:\AI\E-zzio'

    $RunId = '20260820_185842_063_bbacb75395cd'

    $ReportRoot = Join-Path `
        -Path $ProjectRoot `
        -ChildPath '_EZZIO_TRUTH_REPORTS'

    $RunRoot = Join-Path `
        -Path $ReportRoot `
        -ChildPath $RunId

    $ProblemsPath = Join-Path `
        -Path $RunRoot `
        -ChildPath 'EZZIO_PROJECT_PROBLEMS.json'

    $TriagePath = Join-Path `
        -Path $RunRoot `
        -ChildPath 'EZZIO_PROJECT_PROBLEMS_TRIAGE_v1.0.1.json'

    $SummaryPath = Join-Path `
        -Path $RunRoot `
        -ChildPath 'EZZIO_PROJECT_PROBLEMS_TRIAGE_v1.0.1.txt'

    # =========================================================================
    # SAFETY PRECONDITIONS
    # =========================================================================

    if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) {
        throw "PROJECT_ROOT_NOT_FOUND: $ProjectRoot"
    }

    if (-not (Test-Path -LiteralPath $RunRoot -PathType Container)) {
        throw "RUN_DIRECTORY_NOT_FOUND: $RunRoot"
    }

    if (-not (Test-Path -LiteralPath $ProblemsPath -PathType Leaf)) {
        throw "PROBLEMS_REPORT_NOT_FOUND: $ProblemsPath"
    }

    # =========================================================================
    # HELPERS
    # =========================================================================

    function Get-OptionalPropertyValue {

        param(
            [Parameter(Mandatory)]
            [AllowNull()]
            [object]$Object,

            [Parameter(Mandatory)]
            [string]$PropertyName
        )

        if ($null -eq $Object) {
            return $null
        }

        $Property = $Object.PSObject.Properties[$PropertyName]

        if ($null -eq $Property) {
            return $null
        }

        return $Property.Value
    }

    function Get-SafeString {

        param(
            [AllowNull()]
            [object]$Value
        )

        if ($null -eq $Value) {
            return ''
        }

        return [string]$Value
    }

    function Get-ProblemType {

        param(
            [Parameter(Mandatory)]
            [object]$Problem
        )

        $Value = Get-OptionalPropertyValue `
            -Object $Problem `
            -PropertyName 'Type'

        if ([string]::IsNullOrWhiteSpace(
            (Get-SafeString $Value)
        )) {
            return 'UNKNOWN_PROBLEM_TYPE'
        }

        return [string]$Value
    }

    function Get-ProblemPath {

        param(
            [Parameter(Mandatory)]
            [object]$Problem
        )

        return Get-SafeString (
            Get-OptionalPropertyValue `
                -Object $Problem `
                -PropertyName 'Path'
        )
    }

    function Get-ProblemErrorId {

        param(
            [Parameter(Mandatory)]
            [object]$Problem
        )

        return Get-SafeString (
            Get-OptionalPropertyValue `
                -Object $Problem `
                -PropertyName 'ErrorId'
        )
    }

    function Get-ProblemMessage {

        param(
            [Parameter(Mandatory)]
            [object]$Problem
        )

        return Get-SafeString (
            Get-OptionalPropertyValue `
                -Object $Problem `
                -PropertyName 'Message'
        )
    }

    function Get-ProblemExtent {

        param(
            [Parameter(Mandatory)]
            [object]$Problem
        )

        return Get-SafeString (
            Get-OptionalPropertyValue `
                -Object $Problem `
                -PropertyName 'Extent'
        )
    }

    # =========================================================================
    # HEADER
    # =========================================================================

    Write-Host ''
    Write-Host '============================================================' `
        -ForegroundColor Cyan

    Write-Host (
        ' E-ZZIO — TRUTH PROBLEM FORENSIC TRIAGE v{0}' -f $Version
    ) -ForegroundColor Cyan

    Write-Host ' READ-ONLY / FORENSIC / FAIL-CLOSED' `
        -ForegroundColor Cyan

    Write-Host '============================================================' `
        -ForegroundColor Cyan

    Write-Host ''

    Write-Host "PROJECT : $ProjectRoot"
    Write-Host "RUN ID  : $RunId"
    Write-Host ''

    # =========================================================================
    # READ SOURCE REPORT
    # =========================================================================

    Write-Host 'READING ORIGINAL PROBLEM REPORT...' `
        -ForegroundColor DarkCyan

    try {

        $RawJson = [System.IO.File]::ReadAllText(
            $ProblemsPath,
            [System.Text.UTF8Encoding]::new($false)
        )

    }
    catch {

        throw (
            'PROBLEMS_REPORT_READ_FAILURE: {0}' -f
            $_.Exception.Message
        )
    }

    if ([string]::IsNullOrWhiteSpace($RawJson)) {
        throw 'PROBLEMS_REPORT_EMPTY'
    }

    try {

        $Problems = @(
            $RawJson |
                ConvertFrom-Json `
                    -ErrorAction Stop
        )

    }
    catch {

        throw (
            'PROBLEMS_REPORT_INVALID_JSON: {0}' -f
            $_.Exception.Message
        )
    }

    Write-Host (
        'PROBLEMS LOADED : {0}' -f
        $Problems.Count
    ) -ForegroundColor Green

    Write-Host ''

    # =========================================================================
    # RAW STRUCTURE INSPECTION
    # =========================================================================

    $ObjectsWithType = 0
    $ObjectsWithoutType = 0
    $ObjectsWithPath = 0
    $ObjectsWithoutPath = 0

    $ObservedProperties = [ordered]@{}

    foreach ($Problem in $Problems) {

        if ($null -eq $Problem) {
            continue
        }

        foreach ($Property in $Problem.PSObject.Properties) {

            $PropertyName = [string]$Property.Name

            if (-not $ObservedProperties.Contains($PropertyName)) {
                $ObservedProperties[$PropertyName] = 0
            }

            $ObservedProperties[$PropertyName]++
        }

        $TypeValue = Get-ProblemType -Problem $Problem
        $PathValue = Get-ProblemPath -Problem $Problem

        if ($TypeValue -eq 'UNKNOWN_PROBLEM_TYPE') {
            $ObjectsWithoutType++
        }
        else {
            $ObjectsWithType++
        }

        if ([string]::IsNullOrWhiteSpace($PathValue)) {
            $ObjectsWithoutPath++
        }
        else {
            $ObjectsWithPath++
        }
    }

    # =========================================================================
    # TYPE COUNTS
    # =========================================================================

    $TypeCounts = [ordered]@{}

    foreach ($Problem in $Problems) {

        $Type = Get-ProblemType -Problem $Problem

        if (-not $TypeCounts.Contains($Type)) {
            $TypeCounts[$Type] = 0
        }

        $TypeCounts[$Type]++
    }

    # =========================================================================
    # NORMALIZED INVENTORY
    # =========================================================================

    $ProblemInventory = @(
        foreach ($Problem in $Problems) {

            [ordered]@{
                Type    = Get-ProblemType -Problem $Problem
                Path    = Get-ProblemPath -Problem $Problem
                ErrorId = Get-ProblemErrorId -Problem $Problem
                Message = Get-ProblemMessage -Problem $Problem
                Extent  = Get-ProblemExtent -Problem $Problem
            }
        }
    )

    # =========================================================================
    # EXTENSION COUNTS
    # =========================================================================

    $ExtensionCounts = [ordered]@{}

    foreach ($Problem in $ProblemInventory) {

        $Path = [string]$Problem.Path

        if ([string]::IsNullOrWhiteSpace($Path)) {

            $Extension = '<NO_PATH>'

        }
        else {

            try {

                $Extension = [System.IO.Path]::GetExtension($Path)

            }
            catch {

                $Extension = '<INVALID_PATH>'
            }

            if ([string]::IsNullOrWhiteSpace($Extension)) {
                $Extension = '<NO_EXTENSION>'
            }
            else {
                $Extension = $Extension.ToLowerInvariant()
            }
        }

        if (-not $ExtensionCounts.Contains($Extension)) {
            $ExtensionCounts[$Extension] = 0
        }

        $ExtensionCounts[$Extension]++
    }

    # =========================================================================
    # DUPLICATE DETECTION
    # =========================================================================

    $DuplicateGroups = @(
        $ProblemInventory |
            Group-Object `
                -Property {
                    '{0}|{1}|{2}|{3}|{4}' -f `
                        $_.Type,
                        $_.Path,
                        $_.ErrorId,
                        $_.Message,
                        $_.Extent
                } |
            Where-Object {
                $_.Count -gt 1
            } |
            Sort-Object Count -Descending |
            ForEach-Object {

                [ordered]@{
                    Count   = $_.Count
                    Type    = $_.Group[0].Type
                    Path    = $_.Group[0].Path
                    ErrorId = $_.Group[0].ErrorId
                    Message = $_.Group[0].Message
                    Extent  = $_.Group[0].Extent
                }
            }
    )

    # =========================================================================
    # CLASSIFICATION
    # =========================================================================

    $CriticalTypes = @(
        'HASH_FAILURE'
        'ANALYSIS_EXCEPTION'
        'UNREADABLE_FILE'
    )

    $HighTypes = @(
        'POWERSHELL_SYNTAX_ERROR'
        'JSON_SYNTAX_ERROR'
    )

    $MediumTypes = @(
        'EMPTY_FILE'
    )

    $CriticalProblems = @(
        $ProblemInventory |
            Where-Object {
                $CriticalTypes -contains $_.Type
            }
    )

    $HighProblems = @(
        $ProblemInventory |
            Where-Object {
                $HighTypes -contains $_.Type
            }
    )

    $MediumProblems = @(
        $ProblemInventory |
            Where-Object {
                $MediumTypes -contains $_.Type
            }
    )

    $UnknownProblems = @(
        $ProblemInventory |
            Where-Object {
                $_.Type -notin (
                    $CriticalTypes +
                    $HighTypes +
                    $MediumTypes
                )
            }
    )

    # =========================================================================
    # SPECIALIZED GROUPS
    # =========================================================================

    $PowerShellProblems = @(
        $ProblemInventory |
            Where-Object {
                $_.Type -eq 'POWERSHELL_SYNTAX_ERROR'
            }
    )

    $JsonProblems = @(
        $ProblemInventory |
            Where-Object {
                $_.Type -eq 'JSON_SYNTAX_ERROR'
            }
    )

    $EmptyProblems = @(
        $ProblemInventory |
            Where-Object {
                $_.Type -eq 'EMPTY_FILE'
            }
    )

    $UnreadableProblems = @(
        $ProblemInventory |
            Where-Object {
                $_.Type -eq 'UNREADABLE_FILE'
            }
    )

    $HashProblems = @(
        $ProblemInventory |
            Where-Object {
                $_.Type -eq 'HASH_FAILURE'
            }
    )

    $AnalysisExceptions = @(
        $ProblemInventory |
            Where-Object {
                $_.Type -eq 'ANALYSIS_EXCEPTION'
            }
    )

    # =========================================================================
    # VERDICT
    # =========================================================================

    if ($CriticalProblems.Count -gt 0) {

        $TriageVerdict = 'FORENSIC_FAIL_CLOSED'

    }
    elseif ($HighProblems.Count -gt 0) {

        $TriageVerdict = 'TRUTH_INVALID_HIGH_SEVERITY'

    }
    elseif ($UnknownProblems.Count -gt 0) {

        $TriageVerdict = 'TRUTH_UNCLASSIFIED_PROBLEMS'

    }
    elseif ($MediumProblems.Count -gt 0) {

        $TriageVerdict = 'TRUTH_PROBLEMS_DETECTED'

    }
    else {

        $TriageVerdict = 'TRUTH_NO_PROBLEMS'
    }

    # =========================================================================
    # MACHINE REPORT
    # =========================================================================

    $Triage = [ordered]@{

        Product   = 'E-ZZIO'
        Component = 'Truth Problem Forensic Triage'
        Version   = $Version

        Run = [ordered]@{
            RunId = $RunId
            SourceProblemsReport = $ProblemsPath
        }

        Safety = [ordered]@{
            Mode = 'READ_ONLY'
            SourceMutationAllowed = $false
            SourceDeletionAllowed = $false
            SourceRewriteAllowed = $false
            AutomaticCorrectionAllowed = $false
            FailClosed = $true
        }

        Input = [ordered]@{
            ProblemsLoaded = $Problems.Count
            ObjectsWithType = $ObjectsWithType
            ObjectsWithoutType = $ObjectsWithoutType
            ObjectsWithPath = $ObjectsWithPath
            ObjectsWithoutPath = $ObjectsWithoutPath
        }

        ObservedProperties = $ObservedProperties

        Verdict = $TriageVerdict

        Counts = [ordered]@{

            TotalProblemEntries = $Problems.Count

            Critical = $CriticalProblems.Count
            High = $HighProblems.Count
            Medium = $MediumProblems.Count
            Unknown = $UnknownProblems.Count

            PowerShellSyntaxErrors = $PowerShellProblems.Count
            JsonSyntaxErrors = $JsonProblems.Count

            EmptyFiles = $EmptyProblems.Count
            UnreadableFiles = $UnreadableProblems.Count
            HashFailures = $HashProblems.Count
            AnalysisExceptions = $AnalysisExceptions.Count

            DuplicateProblemGroups = $DuplicateGroups.Count
        }

        ProblemTypes = $TypeCounts

        Extensions = $ExtensionCounts

        CriticalProblems = $CriticalProblems

        HighProblems = $HighProblems

        MediumProblems = $MediumProblems

        UnknownProblems = $UnknownProblems

        DuplicateGroups = $DuplicateGroups

        AllProblems = $ProblemInventory
    }

    # =========================================================================
    # WRITE TRIAGE JSON
    # =========================================================================

    Write-Host 'WRITING FORENSIC TRIAGE REPORT...' `
        -ForegroundColor DarkCyan

    $Triage |
        ConvertTo-Json -Depth 30 |
        Set-Content `
            -LiteralPath $TriagePath `
            -Encoding utf8 `
            -ErrorAction Stop

    # =========================================================================
    # TEXT SUMMARY
    # =========================================================================

    $SummaryLines = @(
        'E-ZZIO — TRUTH PROBLEM FORENSIC TRIAGE'
        '======================================='
        ''
        "Version                = $Version"
        "RunId                  = $RunId"
        "SourceReport           = $ProblemsPath"
        "Verdict                = $TriageVerdict"
        ''
        "TotalProblemEntries    = $($Problems.Count)"
        "ObjectsWithType        = $ObjectsWithType"
        "ObjectsWithoutType    = $ObjectsWithoutType"
        "ObjectsWithPath        = $ObjectsWithPath"
        "ObjectsWithoutPath    = $ObjectsWithoutPath"
        ''
        "Critical               = $($CriticalProblems.Count)"
        "High                   = $($HighProblems.Count)"
        "Medium                 = $($MediumProblems.Count)"
        "Unknown                = $($UnknownProblems.Count)"
        ''
        "PowerShellSyntaxErrors = $($PowerShellProblems.Count)"
        "JsonSyntaxErrors       = $($JsonProblems.Count)"
        "EmptyFiles             = $($EmptyProblems.Count)"
        "UnreadableFiles        = $($UnreadableProblems.Count)"
        "HashFailures           = $($HashProblems.Count)"
        "AnalysisExceptions     = $($AnalysisExceptions.Count)"
        ''
        "DuplicateGroups        = $($DuplicateGroups.Count)"
        ''
        'OBSERVED PROPERTIES'
        '-------------------'
    )

    foreach ($Entry in $ObservedProperties.GetEnumerator()) {

        $SummaryLines += (
            '{0,-24} = {1}' -f
            $Entry.Key,
            $Entry.Value
        )
    }

    $SummaryLines += ''
    $SummaryLines += 'PROBLEM TYPES'
    $SummaryLines += '-------------'

    foreach ($Entry in $TypeCounts.GetEnumerator()) {

        $SummaryLines += (
            '{0,-36} = {1}' -f
            $Entry.Key,
            $Entry.Value
        )
    }

    $SummaryLines += ''
    $SummaryLines += 'POWERSHELL SYNTAX FAILURES'
    $SummaryLines += '-------------------------'

    if ($PowerShellProblems.Count -eq 0) {

        $SummaryLines += 'NONE'

    }
    else {

        foreach ($Problem in $PowerShellProblems) {

            $SummaryLines += (
                '[{0}] {1}' -f
                $Problem.ErrorId,
                $Problem.Path
            )

            $SummaryLines += (
                '  Message : {0}' -f
                $Problem.Message
            )

            $SummaryLines += (
                '  Extent  : {0}' -f
                $Problem.Extent
            )
        }
    }

    $SummaryLines += ''
    $SummaryLines += 'JSON SYNTAX FAILURES'
    $SummaryLines += '--------------------'

    if ($JsonProblems.Count -eq 0) {

        $SummaryLines += 'NONE'

    }
    else {

        foreach ($Problem in $JsonProblems) {

            $SummaryLines += (
                '{0}' -f
                $Problem.Path
            )

            $SummaryLines += (
                '  Message : {0}' -f
                $Problem.Message
            )
        }
    }

    $SummaryLines += ''
    $SummaryLines += 'CRITICAL FORENSIC FINDINGS'
    $SummaryLines += '--------------------------'

    if ($CriticalProblems.Count -eq 0) {

        $SummaryLines += 'NONE'

    }
    else {

        foreach ($Problem in $CriticalProblems) {

            $SummaryLines += (
                '{0} :: {1} :: {2}' -f
                $Problem.Type,
                $Problem.Path,
                $Problem.Message
            )
        }
    }

    $SummaryLines += ''
    $SummaryLines += 'REPORTS'
    $SummaryLines += '-------'
    $SummaryLines += "TriageJson = $TriagePath"
    $SummaryLines += "Summary    = $SummaryPath"
    $SummaryLines += ''
    $SummaryLines += 'NO SOURCE FILE WAS MODIFIED.'
    $SummaryLines += 'NO AUTOMATIC CORRECTION WAS PERFORMED.'
    $SummaryLines += 'ORIGINAL PROBLEM REPORT WAS NOT MODIFIED.'

    $SummaryLines |
        Set-Content `
            -LiteralPath $SummaryPath `
            -Encoding utf8 `
            -ErrorAction Stop

    # =========================================================================
    # CONSOLE
    # =========================================================================

    Write-Host ''
    Write-Host '============================================================' `
        -ForegroundColor Cyan

    Write-Host ' E-ZZIO — FORENSIC TRIAGE COMPLETE' `
        -ForegroundColor Cyan

    Write-Host '============================================================' `
        -ForegroundColor Cyan

    Write-Host ''

    Write-Host "TOTAL PROBLEM ENTRIES : $($Problems.Count)"
    Write-Host "CRITICAL              : $($CriticalProblems.Count)"
    Write-Host "HIGH                  : $($HighProblems.Count)"
    Write-Host "MEDIUM                : $($MediumProblems.Count)"
    Write-Host "UNKNOWN               : $($UnknownProblems.Count)"
    Write-Host ''

    Write-Host "POWERSHELL SYNTAX     : $($PowerShellProblems.Count)"
    Write-Host "JSON SYNTAX           : $($JsonProblems.Count)"
    Write-Host "EMPTY FILES           : $($EmptyProblems.Count)"
    Write-Host "UNREADABLE            : $($UnreadableProblems.Count)"
    Write-Host "HASH FAILURES         : $($HashProblems.Count)"
    Write-Host "ANALYSIS EXCEPTIONS   : $($AnalysisExceptions.Count)"
    Write-Host ''

    Write-Host "DUPLICATE GROUPS      : $($DuplicateGroups.Count)"
    Write-Host ''

    switch ($TriageVerdict) {

        'FORENSIC_FAIL_CLOSED' {

            Write-Host `
                "TRUTH STATUS          : $TriageVerdict" `
                -ForegroundColor Red
        }

        'TRUTH_INVALID_HIGH_SEVERITY' {

            Write-Host `
                "TRUTH STATUS          : $TriageVerdict" `
                -ForegroundColor Red
        }

        'TRUTH_UNCLASSIFIED_PROBLEMS' {

            Write-Host `
                "TRUTH STATUS          : $TriageVerdict" `
                -ForegroundColor Yellow
        }

        'TRUTH_PROBLEMS_DETECTED' {

            Write-Host `
                "TRUTH STATUS          : $TriageVerdict" `
                -ForegroundColor Yellow
        }

        default {

            Write-Host `
                "TRUTH STATUS          : $TriageVerdict" `
                -ForegroundColor Green
        }
    }

    Write-Host ''
    Write-Host 'REPORTS:' -ForegroundColor DarkCyan
    Write-Host "  $TriagePath"
    Write-Host "  $SummaryPath"
    Write-Host ''

    Write-Host 'IMPORTANT:' -ForegroundColor Yellow
    Write-Host 'No E-ZZIO source file was modified.'
    Write-Host 'No correction was performed.'
    Write-Host 'The original forensic problem report was not modified.'
    Write-Host ''
}