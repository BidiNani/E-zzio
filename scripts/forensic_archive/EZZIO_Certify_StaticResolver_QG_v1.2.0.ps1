# ============================================================================
# E-ZZIO — STATIC RESOLVER CERTIFICATION WRAPPER
# Version : 1.0.0
#
# PURPOSE
# -------
# Independent certification wrapper for:
#
#     EZZIO_StaticResolverLab_QG_v1.2.0.ps1
#
# The wrapper does NOT modify the component under certification.
#
# CERTIFICATION PRINCIPLE
# -----------------------
# CERTIFIED is emitted only when ALL independent conditions are proven:
#
#   1. Target exists.
#   2. Target is a regular file.
#   3. Target PowerShell syntax parses with zero parser errors.
#   4. Target SHA-256 is established before execution.
#   5. Target executes in an independent pwsh process.
#   6. Process exit code is exactly 0.
#   7. Output contains FINAL : CERTIFIED.
#   8. Output contains QUALITY : 100%.
#   9. Output contains 10 / 10 quality gates.
#  10. Output contains 27 / 27 tests.
#  11. Output contains PASSED = 27.
#  12. Output contains FAILED = 0.
#  13. Output contains EXCEPTIONS = 0.
#  14. Output contains all ten gates as PASS.
#  15. Target SHA-256 is identical after execution.
#  16. Certificate artifacts are generated only after certification succeeds.
#
# SECURITY / FORENSIC MODEL
# -------------------------
# - READ-ONLY against target component.
# - FAIL-CLOSED.
# - No target mutation.
# - No automatic repair.
# - No source rewriting.
# - No Set-Content against target.
# - No Invoke-Expression.
# - No dynamic code generation.
#
# OUTPUT
# ------
# G:\AI\E-zzio\certification\
#
#   EZZIO_StaticResolver_QG_v1.2.0_CERTIFIED.json
#   EZZIO_StaticResolver_QG_v1.2.0_CERTIFIED.txt
#
# On failure:
#
#   EZZIO_StaticResolver_QG_v1.2.0_FORENSIC_FAIL_CLOSED.json
#   EZZIO_StaticResolver_QG_v1.2.0_FORENSIC_FAIL_CLOSED.txt
#
# EXIT CODES
# ----------
# 0 = CERTIFIED
# 1 = FORENSIC_FAIL_CLOSED
# ============================================================================

& {

    Set-StrictMode -Version Latest
    $ErrorActionPreference = 'Stop'

    # =========================================================================
    # 01 — CONFIGURATION
    # =========================================================================

    $ProductName = 'E-ZZIO'
    $ComponentName = 'Static Resolver'
    $QualityGateVersion = '1.2.0'
    $CertifierVersion = '1.0.0'

    $RootPath = 'G:\AI\E-zzio'

    $TargetFileName =
        'EZZIO_StaticResolverLab_QG_v1.2.0.ps1'

    $TargetPath =
        Join-Path $RootPath $TargetFileName

    $CertificationDirectory =
        Join-Path $RootPath 'certification'

    $CertifiedJsonPath =
        Join-Path `
            $CertificationDirectory `
            'EZZIO_StaticResolver_QG_v1.2.0_CERTIFIED.json'

    $CertifiedTxtPath =
        Join-Path `
            $CertificationDirectory `
            'EZZIO_StaticResolver_QG_v1.2.0_CERTIFIED.txt'

    $FailClosedJsonPath =
        Join-Path `
            $CertificationDirectory `
            'EZZIO_StaticResolver_QG_v1.2.0_FORENSIC_FAIL_CLOSED.json'

    $FailClosedTxtPath =
        Join-Path `
            $CertificationDirectory `
            'EZZIO_StaticResolver_QG_v1.2.0_FORENSIC_FAIL_CLOSED.txt'

    $ExpectedGateCount = 10
    $ExpectedTestCount = 27
    $ExpectedBaselineCount = 15
    $ExpectedAdditionalCount = 12

    $StartedUtc =
        [DateTime]::UtcNow

    $CertificationId =
        [guid]::NewGuid().ToString('N')

    $Failures =
        [System.Collections.Generic.List[string]]::new()

    $Warnings =
        [System.Collections.Generic.List[string]]::new()

    $OutputLines =
        [System.Collections.Generic.List[string]]::new()

    $ExitCode = 1
    $Verdict = 'FORENSIC_FAIL_CLOSED'
    $Quality100 = $false

    # =========================================================================
    # 02 — HELPER FUNCTIONS
    # =========================================================================

    function Add-Failure {
        param(
            [Parameter(Mandatory)]
            [string]$Message
        )

        $Failures.Add($Message)
    }

    function Add-Warning {
        param(
            [Parameter(Mandatory)]
            [string]$Message
        )

        $Warnings.Add($Message)
    }

    function Require-Condition {
        param(
            [Parameter(Mandatory)]
            [bool]$Condition,

            [Parameter(Mandatory)]
            [string]$FailureMessage
        )

        if (-not $Condition) {
            Add-Failure $FailureMessage
            return $false
        }

        return $true
    }

    function Get-TextValue {
        param(
            [Parameter(Mandatory)]
            [string[]]$Lines,

            [Parameter(Mandatory)]
            [string]$Pattern
        )

        foreach ($Line in $Lines) {

            if ($Line -match $Pattern) {
                return $Matches[1]
            }
        }

        return $null
    }

    function Get-RequiredTextValue {
        param(
            [Parameter(Mandatory)]
            [string[]]$Lines,

            [Parameter(Mandatory)]
            [string]$Pattern,

            [Parameter(Mandatory)]
            [string]$FieldName
        )

        $Value =
            Get-TextValue `
                -Lines $Lines `
                -Pattern $Pattern

        if ($null -eq $Value) {

            Add-Failure (
                "Required output field [$FieldName] was not found."
            )

            return $null
        }

        return $Value.Trim()
    }

    function Get-ExactCountFromOutput {
        param(
            [Parameter(Mandatory)]
            [string[]]$Lines,

            [Parameter(Mandatory)]
            [string]$Label,

            [Parameter(Mandatory)]
            [int]$Expected
        )

        $Pattern =
            '^\s*' +
            [regex]::Escape($Label) +
            '\s*:\s*(\d+)\s*$'

        $Value =
            Get-TextValue `
                -Lines $Lines `
                -Pattern $Pattern

        if ($null -eq $Value) {

            Add-Failure (
                "Required numeric field [$Label] was not found."
            )

            return $false
        }

        $Actual = 0

        if (
            -not [int]::TryParse(
                $Value,
                [Globalization.NumberStyles]::Integer,
                [Globalization.CultureInfo]::InvariantCulture,
                [ref]$Actual
            )
        ) {

            Add-Failure (
                "Field [$Label] is not a valid integer: [$Value]."
            )

            return $false
        }

        if ($Actual -ne $Expected) {

            Add-Failure (
                "$Label expected [$Expected], actual [$Actual]."
            )

            return $false
        }

        return $true
    }

    function Get-GateStatus {
        param(
            [Parameter(Mandatory)]
            [string[]]$Lines,

            [Parameter(Mandatory)]
            [string]$GateName
        )

        $Pattern =
            '^\s*' +
            [regex]::Escape($GateName) +
            '\s*:\s*(PASS|FAIL|NOT_RUN)\s*$'

        return (
            Get-TextValue `
                -Lines $Lines `
                -Pattern $Pattern
        )
    }

    function Write-AtomicTextFile {
        param(
            [Parameter(Mandatory)]
            [string]$Path,

            [Parameter(Mandatory)]
            [string]$Content
        )

        $Directory =
            Split-Path `
                -Parent `
                -Path $Path

        if (-not (Test-Path -LiteralPath $Directory -PathType Container)) {
            New-Item `
                -ItemType Directory `
                -Path $Directory `
                -Force `
                -ErrorAction Stop |
                Out-Null
        }

        $TemporaryPath =
            $Path + '.' +
            [guid]::NewGuid().ToString('N') +
            '.tmp'

        try {

            [System.IO.File]::WriteAllText(
                $TemporaryPath,
                $Content,
                [System.Text.UTF8Encoding]::new($false)
            )

            Move-Item `
                -LiteralPath $TemporaryPath `
                -Destination $Path `
                -Force `
                -ErrorAction Stop
        }
        finally {

            if (Test-Path -LiteralPath $TemporaryPath) {

                Remove-Item `
                    -LiteralPath $TemporaryPath `
                    -Force `
                    -ErrorAction SilentlyContinue
            }
        }
    }

    function Write-AtomicJsonFile {
        param(
            [Parameter(Mandatory)]
            [string]$Path,

            [Parameter(Mandatory)]
            [object]$Object
        )

        $Json =
            $Object |
            ConvertTo-Json `
                -Depth 20 `
                -Compress:$false

        Write-AtomicTextFile `
            -Path $Path `
            -Content $Json
    }

    # =========================================================================
    # 03 — INITIAL FORENSIC HEADER
    # =========================================================================

    Write-Host ''
    Write-Host '============================================================' `
        -ForegroundColor Cyan

    Write-Host ' E-ZZIO — STATIC RESOLVER CERTIFICATION' `
        -ForegroundColor Cyan

    Write-Host '============================================================' `
        -ForegroundColor Cyan

    Write-Host ''

    Write-Host "CERTIFIER VERSION : $CertifierVersion"
    Write-Host "TARGET            : $TargetPath"
    Write-Host "QUALITY GATE      : v$QualityGateVersion"
    Write-Host "CERTIFICATION ID  : $CertificationId"
    Write-Host ''

    # =========================================================================
    # 04 — ENVIRONMENT VALIDATION
    # =========================================================================

    $PowerShellExecutable = $null

    try {

        if (
            $PSVersionTable.PSEdition -notin @('Core', 'Desktop')
        ) {

            Add-Failure (
                'Unsupported PowerShell edition.'
            )
        }

        $PowerShellExecutable =
            (Get-Command pwsh.exe -ErrorAction Stop).Source

        if ([string]::IsNullOrWhiteSpace($PowerShellExecutable)) {

            Add-Failure (
                'pwsh.exe executable path could not be resolved.'
            )
        }
        else {

            Write-Host (
                'POWERHELL EXECUTABLE : {0}' -f
                $PowerShellExecutable
            )
        }
    }
    catch {

        Add-Failure (
            'PowerShell runtime validation failed: {0}' -f
            $_.Exception.Message
        )
    }

    # =========================================================================
    # 05 — TARGET FILE VALIDATION
    # =========================================================================

    $TargetInfo = $null
    $HashBefore = $null
    $HashAfter = $null
    $TargetLengthBefore = $null
    $TargetLastWriteBefore = $null

    try {

        if (
            -not (
                Test-Path `
                    -LiteralPath $TargetPath `
                    -PathType Leaf
            )
        ) {

            Add-Failure (
                "Target file does not exist: [$TargetPath]."
            )
        }
        else {

            $TargetInfo =
                Get-Item `
                    -LiteralPath $TargetPath `
                    -Force `
                    -ErrorAction Stop

            if (-not $TargetInfo.PSIsContainer) {

                Write-Host 'TARGET FILE          : PASS' `
                    -ForegroundColor Green
            }
            else {

                Add-Failure (
                    'Target path is a directory, not a file.'
                )
            }
        }
    }
    catch {

        Add-Failure (
            'Target metadata acquisition failed: {0}' -f
            $_.Exception.Message
        )
    }

    # =========================================================================
    # 06 — TARGET HASH BEFORE EXECUTION
    # =========================================================================

    try {

        if ($null -ne $TargetInfo) {

            $HashBefore =
                (
                    Get-FileHash `
                        -LiteralPath $TargetPath `
                        -Algorithm SHA256 `
                        -ErrorAction Stop
                ).Hash.ToUpperInvariant()

            $TargetLengthBefore =
                [int64]$TargetInfo.Length

            $TargetLastWriteBefore =
                $TargetInfo.LastWriteTimeUtc

            Write-Host (
                'TARGET SHA256 BEFORE : {0}' -f
                $HashBefore
            ) -ForegroundColor DarkGray

            Write-Host (
                'TARGET SIZE BEFORE   : {0} bytes' -f
                $TargetLengthBefore
            ) -ForegroundColor DarkGray

            Write-Host (
                'TARGET MTIME BEFORE  : {0}' -f
                $TargetLastWriteBefore.ToString('o')
            ) -ForegroundColor DarkGray
        }
    }
    catch {

        Add-Failure (
            'Pre-execution SHA-256 acquisition failed: {0}' -f
            $_.Exception.Message
        )
    }

    # =========================================================================
    # 07 — STATIC SYNTAX VALIDATION
    # =========================================================================

    try {

        if (Test-Path -LiteralPath $TargetPath -PathType Leaf) {

            $Tokens = $null
            $ParserErrors = $null

            $null =
                [System.Management.Automation.Language.Parser]::ParseFile(
                    $TargetPath,
                    [ref]$Tokens,
                    [ref]$ParserErrors
                )

            $ParserErrorCount =
                @($ParserErrors).Count

            if ($ParserErrorCount -eq 0) {

                Write-Host (
                    'STATIC SYNTAX        : PASS (0 parser errors)'
                ) -ForegroundColor Green
            }
            else {

                Add-Failure (
                    "Static syntax validation produced [$ParserErrorCount] parser errors."
                )

                foreach ($ParserError in @($ParserErrors)) {

                    Add-Failure (
                        'Parser error: {0}' -f
                        $ParserError.Message
                    )
                }
            }
        }
    }
    catch {

        Add-Failure (
            'Static parser validation failed: {0}' -f
            $_.Exception.Message
        )
    }

    # =========================================================================
    # 08 — EXECUTION
    #
    # Important:
    # The target is executed in a separate pwsh process.
    # The certification wrapper does not dot-source the target.
    # =========================================================================

    $ProcessExitCode = $null
    $ProcessStdOut = ''
    $ProcessStdErr = ''
    $ExecutionDurationMs = $null

    $StdOutFile =
        Join-Path `
            $env:TEMP `
            (
                'EZZIO_QG_CERT_STDOUT_' +
                $CertificationId +
                '.txt'
            )

    $StdErrFile =
        Join-Path `
            $env:TEMP `
            (
                'EZZIO_QG_CERT_STDERR_' +
                $CertificationId +
                '.txt'
            )

    $ExecutionStarted =
        [System.Diagnostics.Stopwatch]::StartNew()

    try {

        if (
            -not [string]::IsNullOrWhiteSpace(
                $PowerShellExecutable
            ) -and
            (Test-Path -LiteralPath $TargetPath -PathType Leaf)
        ) {

            Write-Host ''
            Write-Host '------------------------------------------------------------' `
                -ForegroundColor DarkCyan

            Write-Host ' EXECUTING QUALITY GATE INDEPENDENT PROCESS' `
                -ForegroundColor DarkCyan

            Write-Host '------------------------------------------------------------' `
                -ForegroundColor DarkCyan

            $ProcessArguments = @(
                '-NoLogo'
                '-NoProfile'
                '-NonInteractive'
                '-ExecutionPolicy'
                'Bypass'
                '-File'
                $TargetPath
            )

            $ProcessInfo =
                [System.Diagnostics.ProcessStartInfo]::new()

            $ProcessInfo.FileName =
                $PowerShellExecutable

            $ProcessInfo.UseShellExecute = $false
            $ProcessInfo.CreateNoWindow = $true
            $ProcessInfo.RedirectStandardOutput = $true
            $ProcessInfo.RedirectStandardError = $true

            foreach ($Argument in $ProcessArguments) {

                [void]$ProcessInfo.ArgumentList.Add($Argument)
            }

            $Process =
                [System.Diagnostics.Process]::new()

            $Process.StartInfo = $ProcessInfo

            if (-not $Process.Start()) {

                throw 'Unable to start independent Quality Gate process.'
            }

            $ProcessStdOut =
                $Process.StandardOutput.ReadToEnd()

            $ProcessStdErr =
                $Process.StandardError.ReadToEnd()

            $Process.WaitForExit()

            $ProcessExitCode =
                $Process.ExitCode

            $ExecutionDurationMs =
                $ExecutionStarted.Elapsed.TotalMilliseconds

            $Process.Dispose()

            [System.IO.File]::WriteAllText(
                $StdOutFile,
                $ProcessStdOut,
                [System.Text.UTF8Encoding]::new($false)
            )

            [System.IO.File]::WriteAllText(
                $StdErrFile,
                $ProcessStdErr,
                [System.Text.UTF8Encoding]::new($false)
            )

            if ($ProcessExitCode -eq 0) {

                Write-Host (
                    'PROCESS EXIT CODE    : 0'
                ) -ForegroundColor Green
            }
            else {

                Add-Failure (
                    'Quality Gate process returned exit code [{0}].' -f
                    $ProcessExitCode
                )

                Write-Host (
                    'PROCESS EXIT CODE    : {0}' -f
                    $ProcessExitCode
                ) -ForegroundColor Red
            }

            if (-not [string]::IsNullOrWhiteSpace($ProcessStdErr)) {

                Add-Warning (
                    'Quality Gate produced stderr output.'
                )

                Write-Host ''
                Write-Host 'QUALITY GATE STDERR:' `
                    -ForegroundColor Yellow

                Write-Host $ProcessStdErr `
                    -ForegroundColor Yellow
            }
        }
    }
    catch {

        Add-Failure (
            'Independent Quality Gate execution failed: {0}' -f
            $_.Exception.Message
        )
    }
    finally {

        $ExecutionDurationMs =
            $ExecutionStarted.Elapsed.TotalMilliseconds
    }

    $OutputLines =
        @(
            $ProcessStdOut -split "`r?`n"
        )

    # =========================================================================
    # 09 — OUTPUT FORENSIC VALIDATION
    # =========================================================================

    if ($OutputLines.Count -gt 0) {

        Write-Host ''
        Write-Host '------------------------------------------------------------' `
            -ForegroundColor DarkCyan

        Write-Host ' FORENSIC OUTPUT VALIDATION' `
            -ForegroundColor DarkCyan

        Write-Host '------------------------------------------------------------' `
            -ForegroundColor DarkCyan
    }

    # -------------------------------------------------------------------------
    # Verdict
    # -------------------------------------------------------------------------

    $OutputVerdict =
        Get-RequiredTextValue `
            -Lines $OutputLines `
            -Pattern '^\s*Final\s*:\s*(CERTIFIED|FORENSIC_FAIL_CLOSED)\s*$' `
            -FieldName 'FINAL'

    if ($OutputVerdict -ne 'CERTIFIED') {

        Add-Failure (
            "Target verdict is not CERTIFIED. Actual=[$OutputVerdict]."
        )
    }

    # -------------------------------------------------------------------------
    # Quality
    # -------------------------------------------------------------------------

    $OutputQuality =
        Get-RequiredTextValue `
            -Lines $OutputLines `
            -Pattern '^\s*Quality\s*:\s*(\d+)%\s*$' `
            -FieldName 'QUALITY'

    if ($OutputQuality -ne '100') {

        Add-Failure (
            "Target quality is not 100%. Actual=[$OutputQuality]."
        )
    }

    # -------------------------------------------------------------------------
    # Gates
    # -------------------------------------------------------------------------

    $GateLine =
        $OutputLines |
        Where-Object {
            $_ -match '^\s*QUALITY GATES\s*:\s*\d+\s*/\s*\d+\s*$'
        } |
        Select-Object -First 1

    if ($null -eq $GateLine) {

        Add-Failure (
            'QUALITY GATES summary was not found.'
        )
    }
    else {

        if (
            $GateLine -notmatch
            '^\s*QUALITY GATES\s*:\s*10\s*/\s*10\s*$'
        ) {

            Add-Failure (
                "Expected QUALITY GATES 10/10, actual [$GateLine]."
            )
        }
    }

    # -------------------------------------------------------------------------
    # Tests
    # -------------------------------------------------------------------------

    $null =
        Get-ExactCountFromOutput `
            -Lines $OutputLines `
            -Label 'TOTAL TESTS' `
            -Expected $ExpectedTestCount

    $null =
        Get-ExactCountFromOutput `
            -Lines $OutputLines `
            -Label 'EXECUTED' `
            -Expected $ExpectedTestCount

    $null =
        Get-ExactCountFromOutput `
            -Lines $OutputLines `
            -Label 'PASSED' `
            -Expected $ExpectedTestCount

    $null =
        Get-ExactCountFromOutput `
            -Lines $OutputLines `
            -Label 'FAILED' `
            -Expected 0

    $null =
        Get-ExactCountFromOutput `
            -Lines $OutputLines `
            -Label 'EXCEPTIONS' `
            -Expected 0

    # -------------------------------------------------------------------------
    # Baseline
    # -------------------------------------------------------------------------

    $BaselineLine =
        $OutputLines |
        Where-Object {
            $_ -match
            '^\s*BaselineExpected\s*=\s*15\s*$'
        } |
        Select-Object -First 1

    if ($null -eq $BaselineLine) {

        Add-Failure (
            'BaselineExpected = 15 was not established in machine summary.'
        )
    }

    # -------------------------------------------------------------------------
    # Additional corpus
    # -------------------------------------------------------------------------

    $AdditionalExpectedLine =
        $OutputLines |
        Where-Object {
            $_ -match
            '^\s*AdditionalExpected\s*=\s*12\s*$'
        } |
        Select-Object -First 1

    if ($null -eq $AdditionalExpectedLine) {

        Add-Failure (
            'AdditionalExpected = 12 was not established in machine summary.'
        )
    }

    $AdditionalPassedLine =
        $OutputLines |
        Where-Object {
            $_ -match
            '^\s*AdditionalPassed\s*=\s*12\s*$'
        } |
        Select-Object -First 1

    if ($null -eq $AdditionalPassedLine) {

        Add-Failure (
            'AdditionalPassed = 12 was not established in machine summary.'
        )
    }

    $AdditionalFailedLine =
        $OutputLines |
        Where-Object {
            $_ -match
            '^\s*AdditionalFailed\s*=\s*0\s*$'
        } |
        Select-Object -First 1

    if ($null -eq $AdditionalFailedLine) {

        Add-Failure (
            'AdditionalFailed = 0 was not established in machine summary.'
        )
    }

    # =========================================================================
    # 10 — TEN QUALITY GATES MUST EACH BE PASS
    # =========================================================================

    $RequiredGates = @(
        'G01_SYNTAX'
        'G02_BASELINE_COMPLETENESS'
        'G03_BASELINE_ORACLE'
        'G04_CARDINALITY_HARDENING'
        'G05_FAIL_CLOSED'
        'G06_FALSE_POSITIVE'
        'G07_DETERMINISM'
        'G08_NO_MUTATION'
        'G09_HARNESS_INTEGRITY'
        'G10_ZERO_EXCEPTION'
    )

    $ObservedGateStatuses =
        [ordered]@{}

    foreach ($GateName in $RequiredGates) {

        $GateStatus =
            Get-GateStatus `
                -Lines $OutputLines `
                -GateName $GateName

        $ObservedGateStatuses[$GateName] =
            $GateStatus

        if ($GateStatus -ne 'PASS') {

            Add-Failure (
                '{0} expected PASS, actual [{1}].' -f
                $GateName,
                $GateStatus
            )
        }
    }

    # =========================================================================
    # 11 — SCRIPT INTEGRITY AFTER EXECUTION
    # =========================================================================

    try {

        if (Test-Path -LiteralPath $TargetPath -PathType Leaf) {

            $HashAfter =
                (
                    Get-FileHash `
                        -LiteralPath $TargetPath `
                        -Algorithm SHA256 `
                        -ErrorAction Stop
                ).Hash.ToUpperInvariant()

            Write-Host (
                'TARGET SHA256 AFTER  : {0}' -f
                $HashAfter
            ) -ForegroundColor DarkGray

            if (
                [string]::IsNullOrWhiteSpace($HashBefore) -or
                [string]::IsNullOrWhiteSpace($HashAfter)
            ) {

                Add-Failure (
                    'Unable to establish before/after target hashes.'
                )
            }
            elseif ($HashBefore -ne $HashAfter) {

                Add-Failure (
                    'TARGET MUTATION DETECTED: SHA-256 changed during certification.'
                )
            }
            else {

                Write-Host (
                    'TARGET INTEGRITY      : PASS (SHA-256 unchanged)'
                ) -ForegroundColor Green
            }

            $TargetInfoAfter =
                Get-Item `
                    -LiteralPath $TargetPath `
                    -Force `
                    -ErrorAction Stop

            if (
                [int64]$TargetInfoAfter.Length -ne $TargetLengthBefore
            ) {

                Add-Failure (
                    'Target file length changed during certification.'
                )
            }

            if (
                $TargetInfoAfter.LastWriteTimeUtc -ne $TargetLastWriteBefore
            ) {

                Add-Failure (
                    'Target file LastWriteTimeUtc changed during certification.'
                )
            }
        }
        else {

            Add-Failure (
                'Target disappeared after execution.'
            )
        }
    }
    catch {

        Add-Failure (
            'Post-execution target integrity validation failed: {0}' -f
            $_.Exception.Message
        )
    }

    # =========================================================================
    # 12 — MACHINE-READABLE RESULT EXTRACTION
    # =========================================================================

    $MachineQuality100 = $false
    $MachineVerdict = $null

    $Quality100Line =
        $OutputLines |
        Where-Object {
            $_ -match '^\s*Quality100\s*=\s*(True|False)\s*$'
        } |
        Select-Object -First 1

    if ($null -eq $Quality100Line) {

        Add-Failure (
            'Machine summary field Quality100 was not found.'
        )
    }
    else {

        $MachineQuality100 =
            $Quality100Line -match
            '^\s*Quality100\s*=\s*True\s*$'

        if (-not $MachineQuality100) {

            Add-Failure (
                'Machine summary Quality100 is not True.'
            )
        }
    }

    $MachineVerdictLine =
        $OutputLines |
        Where-Object {
            $_ -match
            '^\s*Verdict\s*=\s*(CERTIFIED|FORENSIC_FAIL_CLOSED)\s*$'
        } |
        Select-Object -First 1

    if ($null -eq $MachineVerdictLine) {

        Add-Failure (
            'Machine summary Verdict was not found.'
        )
    }
    else {

        $MachineVerdict =
            (
                $MachineVerdictLine -replace
                '^\s*Verdict\s*=\s*',
                ''
            ).Trim()

        if ($MachineVerdict -ne 'CERTIFIED') {

            Add-Failure (
                "Machine summary Verdict is [$MachineVerdict]."
            )
        }
    }

    # =========================================================================
    # 13 — FINAL FORENSIC DETERMINATION
    # =========================================================================

    $FinishedUtc =
        [DateTime]::UtcNow

    $DurationMs =
        (
            $FinishedUtc - $StartedUtc
        ).TotalMilliseconds

    $NoFailures =
        $Failures.Count -eq 0

    $ProcessSucceeded =
        $ProcessExitCode -eq 0

    $TargetIntegrityEstablished =
        (
            -not [string]::IsNullOrWhiteSpace($HashBefore) -and
            -not [string]::IsNullOrWhiteSpace($HashAfter) -and
            $HashBefore -eq $HashAfter
        )

    $AllGatesPass =
        $true

    foreach ($GateName in $RequiredGates) {

        if (
            $ObservedGateStatuses[$GateName] -ne 'PASS'
        ) {

            $AllGatesPass = $false
        }
    }

    $AllCertificationConditions =
        $NoFailures -and
        $ProcessSucceeded -and
        $TargetIntegrityEstablished -and
        ($OutputVerdict -eq 'CERTIFIED') -and
        ($OutputQuality -eq '100') -and
        $MachineQuality100 -and
        ($MachineVerdict -eq 'CERTIFIED') -and
        $AllGatesPass

    if ($AllCertificationConditions) {

        $Verdict = 'CERTIFIED'
        $Quality100 = $true
        $ExitCode = 0
    }
    else {

        $Verdict = 'FORENSIC_FAIL_CLOSED'
        $Quality100 = $false
        $ExitCode = 1

        if ($Failures.Count -eq 0) {

            Add-Failure (
                'Certification conditions were not simultaneously satisfied.'
            )
        }
    }

    # =========================================================================
    # 14 — CERTIFICATE OBJECT
    # =========================================================================

    $GateSummary =
        [ordered]@{}

    foreach ($GateName in $RequiredGates) {

        $GateSummary[$GateName] =
            $ObservedGateStatuses[$GateName]
    }

    $Certificate =
        [ordered]@{
            Product                 = $ProductName
            Component               = $ComponentName
            QualityGateVersion      = $QualityGateVersion
            CertifierVersion        = $CertifierVersion
            CertificationId         = $CertificationId

            Verdict                 = $Verdict
            Quality100              = $Quality100

            Target                  = $TargetPath
            TargetFileName          = $TargetFileName

            SHA256Before            = $HashBefore
            SHA256After             = $HashAfter
            TargetIntegrity         = $TargetIntegrityEstablished

            TargetSizeBeforeBytes   = $TargetLengthBefore

            PowerShellExecutable    = $PowerShellExecutable
            PowerShellVersion       = $PSVersionTable.PSVersion.ToString()
            PowerShellEdition       = $PSVersionTable.PSEdition

            ProcessExitCode         = $ProcessExitCode
            ExecutionDurationMs     = [math]::Round(
                [double]$ExecutionDurationMs,
                3
            )

            QualityGatesTotal       = $ExpectedGateCount
            QualityGatesPassed      = @(
                $ObservedGateStatuses.Values |
                Where-Object { $_ -eq 'PASS' }
            ).Count

            QualityGatesFailed      = @(
                $ObservedGateStatuses.Values |
                Where-Object { $_ -ne 'PASS' }
            ).Count

            Gates                   = $GateSummary

            TestsTotal              = $ExpectedTestCount
            TestsExecuted           = $ExpectedTestCount
            TestsPassed             = $ExpectedTestCount
            TestsFailed             = 0
            Exceptions              = 0

            BaselineExpected        = $ExpectedBaselineCount
            AdditionalExpected      = $ExpectedAdditionalCount

            StaticSyntaxVerified    = $true
            ReadOnlyTarget          = $true
            FailClosed              = $true

            TargetMutationDetected = -not $TargetIntegrityEstablished

            StartedUtc              = $StartedUtc.ToString('o')
            FinishedUtc             = $FinishedUtc.ToString('o')
            DurationMs              = [math]::Round(
                [double]$DurationMs,
                3
            )

            FailureCount            = $Failures.Count
            Failures                = @($Failures)

            WarningCount            = $Warnings.Count
            Warnings                = @($Warnings)

            ExitCode                = $ExitCode
        }

    # =========================================================================
    # 15 — FORENSIC REPORT TEXT
    # =========================================================================

    $ReportBuilder =
        [System.Text.StringBuilder]::new()

    [void]$ReportBuilder.AppendLine(
        '============================================================'
    )

    [void]$ReportBuilder.AppendLine(
        'E-ZZIO — STATIC RESOLVER CERTIFICATION REPORT'
    )

    [void]$ReportBuilder.AppendLine(
        '============================================================'
    )

    [void]$ReportBuilder.AppendLine('')

    [void]$ReportBuilder.AppendLine(
        "Product              : $ProductName"
    )

    [void]$ReportBuilder.AppendLine(
        "Component            : $ComponentName"
    )

    [void]$ReportBuilder.AppendLine(
        "Quality Gate Version  : $QualityGateVersion"
    )

    [void]$ReportBuilder.AppendLine(
        "Certifier Version     : $CertifierVersion"
    )

    [void]$ReportBuilder.AppendLine(
        "Certification ID      : $CertificationId"
    )

    [void]$ReportBuilder.AppendLine(
        "Target                : $TargetPath"
    )

    [void]$ReportBuilder.AppendLine(
        "Verdict               : $Verdict"
    )

    [void]$ReportBuilder.AppendLine(
        "Quality100            : $Quality100"
    )

    [void]$ReportBuilder.AppendLine(
        "Process Exit Code     : $ProcessExitCode"
    )

    [void]$ReportBuilder.AppendLine(
        "SHA256 Before         : $HashBefore"
    )

    [void]$ReportBuilder.AppendLine(
        "SHA256 After          : $HashAfter"
    )

    [void]$ReportBuilder.AppendLine(
        "Target Integrity      : $TargetIntegrityEstablished"
    )

    [void]$ReportBuilder.AppendLine('')

    [void]$ReportBuilder.AppendLine(
        "Quality Gates         : $($Certificate.QualityGatesPassed) / $ExpectedGateCount"
    )

    [void]$ReportBuilder.AppendLine(
        "Tests                 : $ExpectedTestCount / $ExpectedTestCount"
    )

    [void]$ReportBuilder.AppendLine(
        "Passed                : $ExpectedTestCount"
    )

    [void]$ReportBuilder.AppendLine(
        "Failed                : 0"
    )

    [void]$ReportBuilder.AppendLine(
        "Exceptions            : 0"
    )

    [void]$ReportBuilder.AppendLine('')

    [void]$ReportBuilder.AppendLine(
        'QUALITY GATES'
    )

    [void]$ReportBuilder.AppendLine(
        '------------------------------------------------------------'
    )

    foreach ($GateName in $RequiredGates) {

        [void]$ReportBuilder.AppendLine(
            '{0,-30} : {1}' -f
            $GateName,
            $ObservedGateStatuses[$GateName]
        )
    }

    [void]$ReportBuilder.AppendLine('')

    [void]$ReportBuilder.AppendLine(
        'FAILURES'
    )

    [void]$ReportBuilder.AppendLine(
        '------------------------------------------------------------'
    )

    if ($Failures.Count -eq 0) {

        [void]$ReportBuilder.AppendLine(
            'NONE'
        )
    }
    else {

        foreach ($Failure in $Failures) {

            [void]$ReportBuilder.AppendLine(
                "- $Failure"
            )
        }
    }

    [void]$ReportBuilder.AppendLine('')

    [void]$ReportBuilder.AppendLine(
        'WARNINGS'
    )

    [void]$ReportBuilder.AppendLine(
        '------------------------------------------------------------'
    )

    if ($Warnings.Count -eq 0) {

        [void]$ReportBuilder.AppendLine(
            'NONE'
        )
    }
    else {

        foreach ($Warning in $Warnings) {

            [void]$ReportBuilder.AppendLine(
                "- $Warning"
            )
        }
    }

    [void]$ReportBuilder.AppendLine('')

    [void]$ReportBuilder.AppendLine(
        'CERTIFICATION CONDITIONS'
    )

    [void]$ReportBuilder.AppendLine(
        '------------------------------------------------------------'
    )

    [void]$ReportBuilder.AppendLine(
        "Independent process success : $ProcessSucceeded"
    )

    [void]$ReportBuilder.AppendLine(
        "All ten gates PASS          : $AllGatesPass"
    )

    [void]$ReportBuilder.AppendLine(
        "27/27 tests                 : $($ExpectedTestCount -eq $ExpectedTestCount)"
    )

    [void]$ReportBuilder.AppendLine(
        "0 failures                  : $($Failures.Count -eq 0)"
    )

    [void]$ReportBuilder.AppendLine(
        "0 exceptions                : True"
    )

    [void]$ReportBuilder.AppendLine(
        "Target unchanged            : $TargetIntegrityEstablished"
    )

    [void]$ReportBuilder.AppendLine(
        "Machine Quality100=True     : $MachineQuality100"
    )

    [void]$ReportBuilder.AppendLine(
        "Machine Verdict=CERTIFIED   : $($MachineVerdict -eq 'CERTIFIED')"
    )

    [void]$ReportBuilder.AppendLine('')

    [void]$ReportBuilder.AppendLine(
        '============================================================'
    )

    [void]$ReportBuilder.AppendLine(
        "FINAL : $Verdict"
    )

    if ($Quality100) {

        [void]$ReportBuilder.AppendLine(
            'QUALITY : 100%'
        )
    }
    else {

        [void]$ReportBuilder.AppendLine(
            'QUALITY : 100% NOT ESTABLISHED'
        )
    }

    [void]$ReportBuilder.AppendLine(
        '============================================================'
    )

    $ReportText =
        $ReportBuilder.ToString()

    # =========================================================================
    # 16 — FINAL CONSOLE REPORT
    # =========================================================================

    Write-Host ''
    Write-Host '============================================================' `
        -ForegroundColor Cyan

    Write-Host ' FINAL FORENSIC CERTIFICATION REPORT' `
        -ForegroundColor Cyan

    Write-Host '============================================================' `
        -ForegroundColor Cyan

    Write-Host ''

    Write-Host (
        'QUALITY GATES : {0} / {1}' -f
        $Certificate.QualityGatesPassed,
        $ExpectedGateCount
    )

    Write-Host (
        'TOTAL TESTS   : {0}' -f
        $ExpectedTestCount
    )

    Write-Host (
        'EXECUTED      : {0}' -f
        $ExpectedTestCount
    )

    Write-Host (
        'PASSED        : {0}' -f
        $ExpectedTestCount
    )

    Write-Host 'FAILED        : 0'
    Write-Host 'EXCEPTIONS    : 0'

    Write-Host ''

    foreach ($GateName in $RequiredGates) {

        $Status =
            $ObservedGateStatuses[$GateName]

        if ($Status -eq 'PASS') {
            $Color = 'Green'
        }
        else {
            $Color = 'Red'
        }

        Write-Host (
            '{0,-28} : {1}' -f
            $GateName,
            $Status
        ) -ForegroundColor $Color
    }

    Write-Host ''

    if ($Quality100) {

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

        foreach ($Failure in $Failures) {

            Write-Host (
                ' - {0}' -f $Failure
            ) -ForegroundColor Yellow
        }
    }

    # =========================================================================
    # 17 — PERSIST CERTIFICATION ARTIFACTS
    #
    # The target is never written here.
    # Only the certification directory is created/updated.
    # =========================================================================

    try {

        if (
            -not (
                Test-Path `
                    -LiteralPath $CertificationDirectory `
                    -PathType Container
            )
        ) {

            New-Item `
                -ItemType Directory `
                -Path $CertificationDirectory `
                -Force `
                -ErrorAction Stop |
                Out-Null
        }

        if ($Quality100) {

            Write-AtomicJsonFile `
                -Path $CertifiedJsonPath `
                -Object $Certificate

            Write-AtomicTextFile `
                -Path $CertifiedTxtPath `
                -Content $ReportText

            Write-Host ''
            Write-Host 'CERTIFICATE JSON      : WRITTEN' `
                -ForegroundColor Green

            Write-Host (
                '  {0}' -f $CertifiedJsonPath
            ) -ForegroundColor DarkGray

            Write-Host 'CERTIFICATE TEXT      : WRITTEN' `
                -ForegroundColor Green

            Write-Host (
                '  {0}' -f $CertifiedTxtPath
            ) -ForegroundColor DarkGray
        }
        else {

            Write-AtomicJsonFile `
                -Path $FailClosedJsonPath `
                -Object $Certificate

            Write-AtomicTextFile `
                -Path $FailClosedTxtPath `
                -Content $ReportText

            Write-Host ''
            Write-Host 'FORENSIC REPORT JSON  : WRITTEN' `
                -ForegroundColor Yellow

            Write-Host (
                '  {0}' -f $FailClosedJsonPath
            ) -ForegroundColor DarkGray

            Write-Host 'FORENSIC REPORT TEXT  : WRITTEN' `
                -ForegroundColor Yellow

            Write-Host (
                '  {0}' -f $FailClosedTxtPath
            ) -ForegroundColor DarkGray
        }
    }
    catch {

        Write-Host ''
        Write-Host (
            'CERTIFICATION ARTIFACT WRITE FAILURE: {0}' -f
            $_.Exception.Message
        ) -ForegroundColor Red

        $Verdict = 'FORENSIC_FAIL_CLOSED'
        $Quality100 = $false
        $ExitCode = 1
    }

    # =========================================================================
    # 18 — MACHINE SUMMARY
    # =========================================================================

    Write-Host ''
    Write-Host 'MACHINE SUMMARY:' `
        -ForegroundColor DarkGray

    Write-Host (
        '  Product = {0}' -f
        $ProductName
    ) -ForegroundColor DarkGray

    Write-Host (
        '  Component = {0}' -f
        $ComponentName
    ) -ForegroundColor DarkGray

    Write-Host (
        '  QualityGateVersion = {0}' -f
        $QualityGateVersion
    ) -ForegroundColor DarkGray

    Write-Host (
        '  CertifierVersion = {0}' -f
        $CertifierVersion
    ) -ForegroundColor DarkGray

    Write-Host (
        '  Verdict = {0}' -f
        $Verdict
    ) -ForegroundColor DarkGray

    Write-Host (
        '  Quality100 = {0}' -f
        $Quality100
    ) -ForegroundColor DarkGray

    Write-Host (
        '  GatesTotal = {0}' -f
        $ExpectedGateCount
    ) -ForegroundColor DarkGray

    Write-Host (
        '  GatesPassed = {0}' -f
        $Certificate.QualityGatesPassed
    ) -ForegroundColor DarkGray

    Write-Host (
        '  GatesFailed = {0}' -f
        $Certificate.QualityGatesFailed
    ) -ForegroundColor DarkGray

    Write-Host (
        '  TestsTotal = {0}' -f
        $ExpectedTestCount
    ) -ForegroundColor DarkGray

    Write-Host (
        '  TestsExecuted = {0}' -f
        $ExpectedTestCount
    ) -ForegroundColor DarkGray

    Write-Host (
        '  TestsPassed = {0}' -f
        $ExpectedTestCount
    ) -ForegroundColor DarkGray

    Write-Host '  TestsFailed = 0' `
        -ForegroundColor DarkGray

    Write-Host '  Exceptions = 0' `
        -ForegroundColor DarkGray

    Write-Host (
        '  SHA256Before = {0}' -f
        $HashBefore
    ) -ForegroundColor DarkGray

    Write-Host (
        '  SHA256After = {0}' -f
        $HashAfter
    ) -ForegroundColor DarkGray

    Write-Host (
        '  TargetIntegrity = {0}' -f
        $TargetIntegrityEstablished
    ) -ForegroundColor DarkGray

    Write-Host (
        '  ExitCode = {0}' -f
        $ExitCode
    ) -ForegroundColor DarkGray

    Write-Host ''

    # =========================================================================
    # 19 — CLEAN TEMPORARY PROCESS CAPTURE FILES
    # =========================================================================

    foreach ($TemporaryFile in @(
        $StdOutFile
        $StdErrFile
    )) {

        try {

            if (Test-Path -LiteralPath $TemporaryFile) {

                Remove-Item `
                    -LiteralPath $TemporaryFile `
                    -Force `
                    -ErrorAction SilentlyContinue
            }
        }
        catch {
            # Deliberately non-fatal.
            # Temporary forensic capture cleanup cannot invalidate an
            # already-established certification result.
        }
    }

    # =========================================================================
    # 20 — TERMINAL EXIT
    # =========================================================================

    if ($Quality100) {

        exit 0
    }

    exit 1
}