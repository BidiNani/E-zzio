#Requires -Version 7.0
<#
===============================================================================
 E-ZZIO — ADVERSARIAL GATE
 DEEP BODY SCAN — CONTENT TRUTH
 CERTIFICATION HARNESS v3.1
===============================================================================

MODE
----
FAST + FORENSIC
READ-ONLY vis-à-vis du ScriptUnderTest
FAIL-CLOSED
PROCESS-ISOLATED
NO FALSE PASS
NO DEFAULT PASS

OBJECTIF
--------
Certifier mécaniquement les propriétés réellement testées de :

    EZZIO_DeepBodyScan_ContentTruth.ps1

Le moteur sous test est TOUJOURS exécuté dans un processus pwsh enfant.

Aucun "exit" du moteur ne peut tuer le harness.

REGLES ABSOLUES
---------------
1. Une donnée absente ne peut jamais produire PASS.
2. Un test non exécutable produit FAIL.
3. Aucun PASS n'est fondé uniquement sur stdout/stderr.
4. Les hashes sont recalculés indépendamment.
5. La chaîne est recalculée indépendamment.
6. Les commits finaux sont vérifiés physiquement.
7. Le RootPath est vérifié avant/après.
8. Les artefacts sont conservés en cas de FAIL.
9. Le PASS final exige :
       total > 0
       failed = 0
       passed = total
10. Le harness ne modifie jamais le ScriptUnderTest.
11. Le SUT est toujours lancé dans un processus enfant.
12. Aucun exit du SUT ne peut terminer le harness.
===============================================================================
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$ScriptUnderTest
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ============================================================================
# 0. RESULT ENGINE
# ============================================================================

$Results = [System.Collections.Generic.List[object]]::new()

function Add-TestResult {
    param(
        [Parameter(Mandatory)]
        [string]$Id,

        [Parameter(Mandatory)]
        [bool]$Pass,

        [Parameter(Mandatory)]
        [string]$Detail
    )

    $status = if ($Pass) { 'PASS' } else { 'FAIL' }
    $color  = if ($Pass) { 'Green' } else { 'Red' }

    [void]$script:Results.Add(
        [pscustomobject]@{
            Id     = $Id
            Pass   = $Pass
            Status = $status
            Detail = $Detail
        }
    )

    Write-Host (
        '[{0}] {1} — {2}' -f
        $status,
        $Id,
        $Detail
    ) -ForegroundColor $color
}

function Add-TestFailure {
    param(
        [Parameter(Mandatory)]
        [string]$Id,

        [Parameter(Mandatory)]
        [System.Exception]$Exception
    )

    Add-TestResult `
        -Id $Id `
        -Pass $false `
        -Detail ("Test non démontré : " + $Exception.Message)
}

function Assert-Exists {
    param(
        [Parameter(Mandatory)]
        [string]$Path,

        [Parameter(Mandatory)]
        [ValidateSet('Leaf','Container')]
        [string]$Type
    )

    if (-not (Test-Path -LiteralPath $Path -PathType $Type)) {
        throw "Précondition absente : $Path"
    }
}

# ============================================================================
# 1. VALIDATION DU SCRIPT SOUS TEST
# ============================================================================

try {
    Assert-Exists -Path $ScriptUnderTest -Type Leaf

    $ScriptUnderTest = (
        Resolve-Path -LiteralPath $ScriptUnderTest -ErrorAction Stop
    ).Path

    $extension = (
        [IO.Path]::GetExtension($ScriptUnderTest)
    ).ToLowerInvariant()

    if ($extension -ne '.ps1') {
        throw "Le script sous test n'est pas un .ps1 : $ScriptUnderTest"
    }
}
catch {
    Write-Host ''
    Write-Host 'HARNESS FAILURE' -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 2
}

# ============================================================================
# 2. TEST ROOT
# ============================================================================

$timestamp = Get-Date -Format 'yyyyMMdd_HHmmss_fff'
$guid      = [Guid]::NewGuid().ToString('N').Substring(0,12)

$TestRoot = Join-Path `
    ([IO.Path]::GetTempPath()) `
    "ezzio_adversarial_${timestamp}_$guid"

New-Item `
    -ItemType Directory `
    -Path $TestRoot `
    -Force |
    Out-Null

Write-Host ''
Write-Host '===============================================================================' -ForegroundColor Cyan
Write-Host ' E-ZZIO — ADVERSARIAL CERTIFICATION GATE v3.1' -ForegroundColor Cyan
Write-Host '===============================================================================' -ForegroundColor Cyan
Write-Host ''
Write-Host "SUT     : $ScriptUnderTest"
Write-Host "TESTROOT: $TestRoot"
Write-Host ''

# ============================================================================
# 3. PROCESS-ISOLATED EXECUTION
# ============================================================================

function Invoke-Sut {
    param(
        [Parameter(Mandatory)]
        [string[]]$Arguments
    )

    $stdoutPath = Join-Path `
        $TestRoot `
        ("stdout_" + [Guid]::NewGuid().ToString('N') + '.txt')

    $stderrPath = Join-Path `
        $TestRoot `
        ("stderr_" + [Guid]::NewGuid().ToString('N') + '.txt')

    $pwshCommand = Get-Command `
        pwsh `
        -CommandType Application `
        -ErrorAction Stop

    $psi = [System.Diagnostics.ProcessStartInfo]::new()

    $psi.FileName = $pwshCommand.Source
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true

    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError  = $true

    [void]$psi.ArgumentList.Add('-NoProfile')
    [void]$psi.ArgumentList.Add('-NonInteractive')
    [void]$psi.ArgumentList.Add('-ExecutionPolicy')
    [void]$psi.ArgumentList.Add('Bypass')
    [void]$psi.ArgumentList.Add('-File')
    [void]$psi.ArgumentList.Add($ScriptUnderTest)

    foreach ($arg in $Arguments) {
        [void]$psi.ArgumentList.Add([string]$arg)
    }

    $process = [System.Diagnostics.Process]::new()
    $process.StartInfo = $psi

    try {
        $started = $process.Start()

        if (-not $started) {
            throw 'Impossible de démarrer le processus SUT.'
        }

        $stdoutTask = $process.StandardOutput.ReadToEndAsync()
        $stderrTask = $process.StandardError.ReadToEndAsync()

        $process.WaitForExit()

        $stdout = $stdoutTask.GetAwaiter().GetResult()
        $stderr = $stderrTask.GetAwaiter().GetResult()

        Set-Content `
            -LiteralPath $stdoutPath `
            -Value $stdout `
            -Encoding UTF8

        Set-Content `
            -LiteralPath $stderrPath `
            -Value $stderr `
            -Encoding UTF8

        return [pscustomobject]@{
            ExitCode   = [int]$process.ExitCode
            Output     = [string]$stdout
            Error      = [string]$stderr
            StdoutPath = $stdoutPath
            StderrPath = $stderrPath
            Started    = $true
            Threw      = $false
        }
    }
    catch {
        return [pscustomobject]@{
            ExitCode   = -1
            Output     = ''
            Error      = $_.Exception.Message
            StdoutPath = $stdoutPath
            StderrPath = $stderrPath
            Started    = $false
            Threw      = $true
        }
    }
    finally {
        $process.Dispose()
    }
}

# ============================================================================
# 4. PHYSICAL SNAPSHOT
# ============================================================================

function Get-PhysicalSnapshot {
    param(
        [Parameter(Mandatory)]
        [string]$Root
    )

    Assert-Exists -Path $Root -Type Container

    $items = @(
        Get-ChildItem `
            -LiteralPath $Root `
            -Recurse `
            -File `
            -Force `
            -ErrorAction Stop
    )

    $snapshot = [System.Collections.Generic.List[object]]::new()

    foreach ($item in $items) {

        $hashResult = Get-FileHash `
            -LiteralPath $item.FullName `
            -Algorithm SHA256 `
            -ErrorAction Stop

        $relative = [IO.Path]::GetRelativePath(
            $Root,
            $item.FullName
        )

        [void]$snapshot.Add(
            [pscustomobject]@{
                RelativePath     = $relative
                Length           = [int64]$item.Length
                LastWriteTimeUtc = $item.LastWriteTimeUtc.ToString('o')
                Hash             = $hashResult.Hash.ToLowerInvariant()
            }
        )
    }

    return @(
        $snapshot |
        Sort-Object RelativePath
    )
}

function Compare-PhysicalSnapshot {
    param(
        [Parameter(Mandatory)]
        [object[]]$Before,

        [Parameter(Mandatory)]
        [object[]]$After
    )

    $beforeJson = (
        @($Before) |
        ConvertTo-Json -Depth 10 -Compress
    )

    $afterJson = (
        @($After) |
        ConvertTo-Json -Depth 10 -Compress
    )

    return ($beforeJson -eq $afterJson)
}

# ============================================================================
# 5. TRANSACTION DISCOVERY
# ============================================================================

function Get-SingleTransactionDir {
    param(
        [Parameter(Mandatory)]
        [string]$OutputRoot
    )

    Assert-Exists -Path $OutputRoot -Type Container

    $dirs = @(
        Get-ChildItem `
            -LiteralPath $OutputRoot `
            -Directory `
            -Filter '.transaction_*' `
            -ErrorAction Stop
    )

    if ($dirs.Count -ne 1) {
        throw (
            "Workspace transactionnel attendu=1, trouvé=$($dirs.Count)"
        )
    }

    return $dirs[0]
}

# ============================================================================
# 6. ARTIFACT LOADING
# ============================================================================

function Get-TransactionArtifacts {
    param(
        [Parameter(Mandatory)]
        [string]$TransactionDirectory
    )

    Assert-Exists `
        -Path $TransactionDirectory `
        -Type Container

    $recordsCandidates = @(
        Get-ChildItem `
            -LiteralPath $TransactionDirectory `
            -Recurse `
            -File `
            -Filter 'records.jsonl' `
            -ErrorAction Stop
    )

    $checkpointCandidates = @(
        Get-ChildItem `
            -LiteralPath $TransactionDirectory `
            -Recurse `
            -File `
            -Filter 'checkpoint.json' `
            -ErrorAction Stop
    )

    if ($recordsCandidates.Count -ne 1) {
        throw (
            "records.jsonl attendu=1, trouvé=$($recordsCandidates.Count)"
        )
    }

    if ($checkpointCandidates.Count -ne 1) {
        throw (
            "checkpoint.json attendu=1, trouvé=$($checkpointCandidates.Count)"
        )
    }

    $recordsPath = $recordsCandidates[0].FullName
    $checkpointPath = $checkpointCandidates[0].FullName

    $records = @(
        [IO.File]::ReadLines($recordsPath) |
        ForEach-Object {

            if ([string]::IsNullOrWhiteSpace($_)) {
                throw 'records.jsonl contient une ligne vide.'
            }

            $_ |
                ConvertFrom-Json `
                    -ErrorAction Stop
        }
    )

    if ($records.Count -lt 1) {
        throw 'records.jsonl vide : aucune donnée certifiable.'
    }

    $checkpoint = (
        [IO.File]::ReadAllText($checkpointPath) |
        ConvertFrom-Json `
            -ErrorAction Stop
    )

    return [pscustomobject]@{
        RecordsPath    = $recordsPath
        CheckpointPath = $checkpointPath
        Records        = $records
        Checkpoint     = $checkpoint
    }
}

# ============================================================================
# 7. INDEPENDENT CHAIN
# ============================================================================

function Get-IndependentChainHash {
    param(
        [Parameter(Mandatory)]
        [object[]]$Records
    )

    if ($Records.Count -lt 1) {
        throw 'Impossible de calculer une chaîne sur zéro record.'
    }

    $chain = ''
    $sha = [System.Security.Cryptography.SHA256]::Create()

    try {

        foreach ($record in $Records) {

            if (
                -not (
                    $record.PSObject.Properties.Name -contains
                    'RecordHash'
                )
            ) {
                throw 'Record sans propriété RecordHash.'
            }

            $recordHash = [string]$record.RecordHash

            if ([string]::IsNullOrWhiteSpace($recordHash)) {
                throw 'RecordHash vide.'
            }

            $payload = "$chain|$recordHash"

            $bytes = [Text.Encoding]::UTF8.GetBytes($payload)

            $digest = $sha.ComputeHash($bytes)

            $chain = (
                [BitConverter]::ToString($digest)
            ).Replace(
                '-',
                ''
            ).ToLowerInvariant()
        }
    }
    finally {
        $sha.Dispose()
    }

    if ([string]::IsNullOrWhiteSpace($chain)) {
        throw 'Chaîne finale vide.'
    }

    return $chain
}

# ============================================================================
# 8. FINAL COMMIT DISCOVERY
# ============================================================================

function Get-FinalRunDirs {
    param(
        [Parameter(Mandatory)]
        [string]$OutputRoot
    )

    return @(
        Get-ChildItem `
            -LiteralPath $OutputRoot `
            -Directory `
            -Filter 'run_*' `
            -ErrorAction SilentlyContinue
    )
}

# ============================================================================
# TEST A — BASE TRUTH
# ============================================================================

Write-Host ''
Write-Host '===============================================================================' -ForegroundColor Cyan
Write-Host ' TEST A — BASE TRUTH' -ForegroundColor Cyan
Write-Host '===============================================================================' -ForegroundColor Cyan

$aCorpus = Join-Path $TestRoot 'A_corpus'
$aOutput = Join-Path $TestRoot 'A_output'

New-Item `
    -ItemType Directory `
    -Path $aCorpus,$aOutput `
    -Force |
    Out-Null

Set-Content `
    -LiteralPath (Join-Path $aCorpus 'normal.txt') `
    -Value 'contenu normal E-ZZIO' `
    -NoNewline `
    -Encoding UTF8

New-Item `
    -ItemType File `
    -Path (Join-Path $aCorpus 'empty.txt') `
    -Force |
    Out-Null

$bigContent = -join (
    1..20000 |
    ForEach-Object {
        '0123456789'
    }
)

Set-Content `
    -LiteralPath (Join-Path $aCorpus 'big.txt') `
    -Value $bigContent `
    -NoNewline `
    -Encoding UTF8

Set-Content `
    -LiteralPath (Join-Path $aCorpus 'unicode_éàç_文件.txt') `
    -Value 'texte accentué 你好' `
    -NoNewline `
    -Encoding UTF8

New-Item `
    -ItemType Directory `
    -Path (Join-Path $aCorpus 'sub') `
    -Force |
    Out-Null

Set-Content `
    -LiteralPath (Join-Path $aCorpus 'sub\nested.txt') `
    -Value 'fichier imbriqué' `
    -NoNewline `
    -Encoding UTF8

$aBefore = @()
$aExpectedCount = 0
$aRun = $null
$aTx = $null
$aArtifacts = $null
$aRecords = @()

try {

    $aBefore = @(
        Get-PhysicalSnapshot -Root $aCorpus
    )

    if ($aBefore.Count -lt 1) {
        throw 'Corpus A vide.'
    }

    $aExpectedCount = $aBefore.Count

    $aRun = Invoke-Sut -Arguments @(
        '-RootPath', $aCorpus,
        '-OutputRoot', $aOutput,
        '-CheckpointEveryNFiles', '2'
    )

    $aTx = Get-SingleTransactionDir `
        -OutputRoot $aOutput

    $aArtifacts = Get-TransactionArtifacts `
        -TransactionDirectory $aTx.FullName

    $aRecords = @($aArtifacts.Records)

    # ------------------------------------------------------------------------
    # T-01
    # ------------------------------------------------------------------------

    $hashFailures =
        [System.Collections.Generic.List[string]]::new()

    $observedCount = 0

    foreach ($record in $aRecords) {

        if ([string]$record.Status -ne 'OBSERVED') {
            continue
        }

        $observedCount++

        $relative = [string]$record.RelativePath

        if ([string]::IsNullOrWhiteSpace($relative)) {
            [void]$hashFailures.Add('<EMPTY_RELATIVE_PATH>')
            continue
        }

        $full = Join-Path $aCorpus $relative

        if (-not (
            Test-Path `
                -LiteralPath $full `
                -PathType Leaf
        )) {
            [void]$hashFailures.Add($relative)
            continue
        }

        $physicalHash = (
            Get-FileHash `
                -LiteralPath $full `
                -Algorithm SHA256 `
                -ErrorAction Stop
        ).Hash.ToLowerInvariant()

        $recordHash = [string]$record.Hash

        if (
            [string]::IsNullOrWhiteSpace($recordHash) -or
            $physicalHash -ne $recordHash.ToLowerInvariant()
        ) {
            [void]$hashFailures.Add($relative)
        }
    }

    $t01Pass = (
        ($observedCount -gt 0) -and
        ($hashFailures.Count -eq 0)
    )

    Add-TestResult `
        -Id 'T-01_HashExact' `
        -Pass $t01Pass `
        -Detail (
            "observed=$observedCount, " +
            "hashFailures=$($hashFailures.Count)"
        )

    # ------------------------------------------------------------------------
    # T-02
    # ------------------------------------------------------------------------

    $t02Pass = (
        ($aRecords.Count -eq $aExpectedCount) -and
        ($aRecords.Count -gt 0)
    )

    Add-TestResult `
        -Id 'T-02_RecordCountExact' `
        -Pass $t02Pass `
        -Detail (
            "records=$($aRecords.Count), " +
            "expected=$aExpectedCount"
        )

    # ------------------------------------------------------------------------
    # T-03
    # ------------------------------------------------------------------------

    $independentChain = Get-IndependentChainHash `
        -Records $aRecords

    $checkpointChain = [string]$aArtifacts.Checkpoint.ChainHash

    $t03Pass = (
        (-not [string]::IsNullOrWhiteSpace($checkpointChain)) -and
        ($independentChain -eq $checkpointChain)
    )

    Add-TestResult `
        -Id 'T-03_IndependentChainIntegrity' `
        -Pass $t03Pass `
        -Detail (
            "independent=$independentChain, " +
            "checkpoint=$checkpointChain"
        )

    # ------------------------------------------------------------------------
    # T-07
    # ------------------------------------------------------------------------

    $aAfter = @(
        Get-PhysicalSnapshot -Root $aCorpus
    )

    $t07Snapshot = Compare-PhysicalSnapshot `
        -Before $aBefore `
        -After $aAfter

    $t07Pass = (
        $t07Snapshot -and
        ($aRun.ExitCode -eq 0)
    )

    Add-TestResult `
        -Id 'T-07_RootUntouched' `
        -Pass $t07Pass `
        -Detail (
            "snapshot=$t07Snapshot, " +
            "exit=$($aRun.ExitCode)"
        )
}
catch {
    Add-TestResult `
        -Id 'T-01_HashExact' `
        -Pass $false `
        -Detail ("Test A non exécutable : " + $_.Exception.Message)

    Add-TestResult `
        -Id 'T-02_RecordCountExact' `
        -Pass $false `
        -Detail 'Test A non exécutable.'

    Add-TestResult `
        -Id 'T-03_IndependentChainIntegrity' `
        -Pass $false `
        -Detail 'Test A non exécutable.'

    Add-TestResult `
        -Id 'T-07_RootUntouched' `
        -Pass $false `
        -Detail 'Test A non exécutable.'
}

# ============================================================================
# TEST B — PHYSICAL ERROR
# ============================================================================

Write-Host ''
Write-Host '===============================================================================' -ForegroundColor Cyan
Write-Host ' TEST B — PHYSICAL ERROR / FAIL-CLOSED' -ForegroundColor Cyan
Write-Host '===============================================================================' -ForegroundColor Cyan

$bCorpus = Join-Path $TestRoot 'B_corpus'
$bOutput = Join-Path $TestRoot 'B_output'

New-Item `
    -ItemType Directory `
    -Path $bCorpus,$bOutput `
    -Force |
    Out-Null

Set-Content `
    -LiteralPath (Join-Path $bCorpus 'ok.txt') `
    -Value 'lisible' `
    -NoNewline `
    -Encoding UTF8

$bLockedPath = Join-Path $bCorpus 'locked.txt'

Set-Content `
    -LiteralPath $bLockedPath `
    -Value 'sera verrouillé' `
    -NoNewline `
    -Encoding UTF8

$lockHandle = $null
$bRun = $null

try {

    $lockHandle = [IO.File]::Open(
        $bLockedPath,
        [IO.FileMode]::Open,
        [IO.FileAccess]::Read,
        [IO.FileShare]::None
    )

    $bRun = Invoke-Sut -Arguments @(
        '-RootPath', $bCorpus,
        '-OutputRoot', $bOutput,
        '-CheckpointEveryNFiles', '1'
    )
}
catch {

    $bRun = [pscustomobject]@{
        ExitCode = -1
        Output   = ''
        Error    = $_.Exception.Message
        Started  = $false
        Threw    = $true
    }
}
finally {

    if ($null -ne $lockHandle) {
        $lockHandle.Dispose()
        $lockHandle = $null
    }
}

try {

    $bTx = Get-SingleTransactionDir `
        -OutputRoot $bOutput

    $bArtifacts = Get-TransactionArtifacts `
        -TransactionDirectory $bTx.FullName

    $bLockedRecords = @(
        $bArtifacts.Records |
        Where-Object {
            [string]$_.RelativePath -eq 'locked.txt'
        }
    )

    $bFinalDirs = @(
        Get-FinalRunDirs -OutputRoot $bOutput
    )

    $bStatus = 'ABSENT'

    if ($bLockedRecords.Count -eq 1) {
        $bStatus = [string]$bLockedRecords[0].Status
    }

    $t04Pass = (
        ($bLockedRecords.Count -eq 1) -and
        ($bStatus -eq 'ERROR') -and
        ($bRun.ExitCode -ne 0) -and
        ($bFinalDirs.Count -eq 0)
    )

    Add-TestResult `
        -Id 'T-04_LockedFileFailClosed' `
        -Pass $t04Pass `
        -Detail (
            "lockedRecords=$($bLockedRecords.Count), " +
            "status=$bStatus, " +
            "exit=$($bRun.ExitCode), " +
            "finalDirs=$($bFinalDirs.Count)"
        )
}
catch {

    Add-TestResult `
        -Id 'T-04_LockedFileFailClosed' `
        -Pass $false `
        -Detail (
            "Impossible de vérifier le résultat physique : " +
            $_.Exception.Message
        )
}

# ============================================================================
# TEST C — RESUME
# ============================================================================

Write-Host ''
Write-Host '===============================================================================' -ForegroundColor Cyan
Write-Host ' TEST C — FORENSIC RESUME' -ForegroundColor Cyan
Write-Host '===============================================================================' -ForegroundColor Cyan

$cCorpus = Join-Path $TestRoot 'C_corpus'
$cOutput = Join-Path $TestRoot 'C_output'

New-Item `
    -ItemType Directory `
    -Path $cCorpus,$cOutput `
    -Force |
    Out-Null

1..6 |
    ForEach-Object {

        $filePath = Join-Path `
            $cCorpus `
            "file_$_.txt"

        Set-Content `
            -LiteralPath $filePath `
            -Value "contenu numero $_" `
            -NoNewline `
            -Encoding UTF8
    }

$cExpected = @(
    Get-PhysicalSnapshot -Root $cCorpus
).Count

$cFinalRecords = @()
$cTx = $null

try {

    $cInitial = Invoke-Sut -Arguments @(
        '-RootPath', $cCorpus,
        '-OutputRoot', $cOutput,
        '-CheckpointEveryNFiles', '1'
    )

    if ($cInitial.ExitCode -ne 0) {
        throw (
            "Exécution initiale échouée, exit=$($cInitial.ExitCode)"
        )
    }

    $cTx = Get-SingleTransactionDir `
        -OutputRoot $cOutput

    $cArtifacts = Get-TransactionArtifacts `
        -TransactionDirectory $cTx.FullName

    $cRunId = $cTx.Name -replace '^\.transaction_', ''

    $cRecords = @($cArtifacts.Records)

    if ($cRecords.Count -lt 3) {
        throw 'Corpus insuffisant pour simuler une interruption.'
    }

    # ------------------------------------------------------------------------
    # INTERRUPTION ARTIFICIELLE
    # ------------------------------------------------------------------------

    $kept = @(
        $cRecords |
        Select-Object -First 3
    )

    $partialLines = @(
        foreach ($record in $kept) {

            $record |
                ConvertTo-Json `
                    -Compress `
                    -Depth 30
        }
    )

    Set-Content `
        -LiteralPath $cArtifacts.RecordsPath `
        -Value $partialLines `
        -Encoding UTF8

    $partialChain = Get-IndependentChainHash `
        -Records $kept

    $checkpoint = (
        Get-Content `
            -LiteralPath $cArtifacts.CheckpointPath `
            -Raw |
        ConvertFrom-Json
    )

    if (
        -not (
            $checkpoint.PSObject.Properties.Name -contains
            'ChainHash'
        )
    ) {
        throw 'Checkpoint sans ChainHash.'
    }

    $checkpoint.ChainHash = $partialChain

    if (
        $checkpoint.PSObject.Properties.Name -contains
        'FilesProcessed'
    ) {
        $checkpoint.FilesProcessed = $kept.Count
    }

    $checkpoint |
        ConvertTo-Json `
            -Depth 30 |
        Set-Content `
            -LiteralPath $cArtifacts.CheckpointPath `
            -Encoding UTF8

    # ------------------------------------------------------------------------
    # REPRISE
    # ------------------------------------------------------------------------

    $cResume = Invoke-Sut -Arguments @(
        '-RootPath', $cCorpus,
        '-OutputRoot', $cOutput,
        '-ResumeRunId', $cRunId,
        '-CheckpointEveryNFiles', '1'
    )

    $cFinal = Get-TransactionArtifacts `
        -TransactionDirectory $cTx.FullName

    $cFinalRecords = @($cFinal.Records)

    $paths = @(
        $cFinalRecords |
        ForEach-Object {
            [string]$_.RelativePath
        }
    )

    $uniquePaths = @(
        $paths |
        Sort-Object -Unique
    )

    if ($cFinalRecords.Count -lt 1) {
        throw 'Aucun record après reprise.'
    }

    $finalIndependentChain = Get-IndependentChainHash `
        -Records $cFinalRecords

    $finalCheckpointChain = [string]$cFinal.Checkpoint.ChainHash

    $finalChainValid = (
        (-not [string]::IsNullOrWhiteSpace($finalCheckpointChain)) -and
        ($finalIndependentChain -eq $finalCheckpointChain)
    )

    $t05Pass = (
        ($cFinalRecords.Count -eq $cExpected) -and
        ($uniquePaths.Count -eq $cExpected) -and
        $finalChainValid -and
        ($cResume.ExitCode -eq 0)
    )

    Add-TestResult `
        -Id 'T-05_ResumeCompletesCorrectly' `
        -Pass $t05Pass `
        -Detail (
            "records=$($cFinalRecords.Count)/$cExpected, " +
            "unique=$($uniquePaths.Count), " +
            "chainValid=$finalChainValid, " +
            "exit=$($cResume.ExitCode)"
        )
}
catch {

    Add-TestResult `
        -Id 'T-05_ResumeCompletesCorrectly' `
        -Pass $false `
        -Detail (
            "Reprise non démontrée : " +
            $_.Exception.Message
        )
}

# ============================================================================
# TEST D — TAMPERING
# ============================================================================

Write-Host ''
Write-Host '===============================================================================' -ForegroundColor Cyan
Write-Host ' TEST D — CHECKPOINT TAMPERING' -ForegroundColor Cyan
Write-Host '===============================================================================' -ForegroundColor Cyan

$dCorpus = Join-Path $TestRoot 'D_corpus'
$dOutput = Join-Path $TestRoot 'D_output'

New-Item `
    -ItemType Directory `
    -Path $dCorpus,$dOutput `
    -Force |
    Out-Null

1..3 |
    ForEach-Object {

        $filePath = Join-Path `
            $dCorpus `
            "f_$_.txt"

        Set-Content `
            -LiteralPath $filePath `
            -Value "d$_" `
            -NoNewline `
            -Encoding UTF8
    }

try {

    $dInitial = Invoke-Sut -Arguments @(
        '-RootPath', $dCorpus,
        '-OutputRoot', $dOutput,
        '-CheckpointEveryNFiles', '1'
    )

    if ($dInitial.ExitCode -ne 0) {
        throw (
            "Exécution initiale échouée, exit=$($dInitial.ExitCode)"
        )
    }

    $dTx = Get-SingleTransactionDir `
        -OutputRoot $dOutput

    $dArtifacts = Get-TransactionArtifacts `
        -TransactionDirectory $dTx.FullName

    $dRunId = $dTx.Name -replace '^\.transaction_', ''

    $tampered = (
        Get-Content `
            -LiteralPath $dArtifacts.CheckpointPath `
            -Raw |
        ConvertFrom-Json
    )

    if (
        -not (
            $tampered.PSObject.Properties.Name -contains
            'ChainHash'
        )
    ) {
        throw 'Checkpoint sans ChainHash.'
    }

    $originalChain = [string]$tampered.ChainHash

    if ([string]::IsNullOrWhiteSpace($originalChain)) {
        throw 'ChainHash original vide.'
    }

    $tampered.ChainHash = ('deadbeef' * 8)

    $tampered |
        ConvertTo-Json `
            -Depth 30 |
        Set-Content `
            -LiteralPath $dArtifacts.CheckpointPath `
            -Encoding UTF8

    $dBeforeFinal = @(
        Get-FinalRunDirs -OutputRoot $dOutput
    ).Count

    $dResume = Invoke-Sut -Arguments @(
        '-RootPath', $dCorpus,
        '-OutputRoot', $dOutput,
        '-ResumeRunId', $dRunId,
        '-CheckpointEveryNFiles', '1'
    )

    $dAfterFinal = @(
        Get-FinalRunDirs -OutputRoot $dOutput
    ).Count

    $dRejected = (
        ($dResume.ExitCode -ne 0) -or
        $dResume.Threw
    )

    $dNoCommit = (
        $dAfterFinal -eq $dBeforeFinal
    )

    $dCheckpointAfter = (
        Get-Content `
            -LiteralPath $dArtifacts.CheckpointPath `
            -Raw |
        ConvertFrom-Json
    )

    $dChainActuallyTampered = (
        [string]$dCheckpointAfter.ChainHash -eq
        ('deadbeef' * 8)
    )

    $t06Pass = (
        $dRejected -and
        $dNoCommit -and
        $dChainActuallyTampered
    )

    Add-TestResult `
        -Id 'T-06_TamperedCheckpointRejected' `
        -Pass $t06Pass `
        -Detail (
            "rejected=$dRejected, " +
            "noCommit=$dNoCommit, " +
            "tamperingPhysicallyPresent=$dChainActuallyTampered, " +
            "exit=$($dResume.ExitCode)"
        )
}
catch {

    Add-TestResult `
        -Id 'T-06_TamperedCheckpointRejected' `
        -Pass $false `
        -Detail (
            "Test tampering non démontré : " +
            $_.Exception.Message
        )
}

# ============================================================================
# TEST E — FINAL COMMIT / MANIFEST
# ============================================================================

Write-Host ''
Write-Host '===============================================================================' -ForegroundColor Cyan
Write-Host ' TEST E — FINAL COMMIT / MANIFEST' -ForegroundColor Cyan
Write-Host '===============================================================================' -ForegroundColor Cyan

$finalDirs = @()
$finalDir = $null
$cFinalAvailable = $false

try {

    if ($null -eq $cTx) {
        throw 'Transaction C indisponible.'
    }

    if ($cFinalRecords.Count -lt 1) {
        throw 'Aucun record final C disponible.'
    }

    $finalDirs = @(
        Get-FinalRunDirs -OutputRoot $cOutput
    )

    if ($finalDirs.Count -ne 1) {
        throw (
            "Nombre de commits finaux attendu=1, trouvé=$($finalDirs.Count)"
        )
    }

    $finalDir = $finalDirs[0]
    $cFinalAvailable = $true

    $expectedArtifacts = @(
        'records.jsonl'
        'checkpoint.json'
        'quality_gates.json'
        'run_manifest.json'
    )

    $missing =
        [System.Collections.Generic.List[string]]::new()

    foreach ($name in $expectedArtifacts) {

        $path = Join-Path `
            $finalDir.FullName `
            $name

        if (-not (
            Test-Path `
                -LiteralPath $path `
                -PathType Leaf
        )) {
            [void]$missing.Add($name)
        }
    }

    $t09Pass = (
        $missing.Count -eq 0
    )

    $t09Detail = ''

    if ($t09Pass) {
        $t09Detail =
            'Les quatre artefacts finaux sont physiquement présents.'
    }
    else {
        $t09Detail =
            "Manquants=$($missing -join ', ')"
    }

    Add-TestResult `
        -Id 'T-09_FinalArtifactsComplete' `
        -Pass $t09Pass `
        -Detail $t09Detail

    # ------------------------------------------------------------------------
    # T-10
    # ------------------------------------------------------------------------

    if (-not $t09Pass) {
        throw 'Impossible de vérifier le manifeste : artefacts manquants.'
    }

    $manifestPath = Join-Path `
        $finalDir.FullName `
        'run_manifest.json'

    $manifest = (
        Get-Content `
            -LiteralPath $manifestPath `
            -Raw |
        ConvertFrom-Json
    )

    if (
        -not (
            $manifest.PSObject.Properties.Name -contains
            'Certified'
        )
    ) {
        throw 'Manifeste sans propriété Certified.'
    }

    if (
        -not (
            $manifest.PSObject.Properties.Name -contains
            'ChainHash'
        )
    ) {
        throw 'Manifeste sans propriété ChainHash.'
    }

    $manifestCertified = [bool]$manifest.Certified
    $manifestChain = [string]$manifest.ChainHash

    $independentFinalChain = Get-IndependentChainHash `
        -Records $cFinalRecords

    $t10Pass = (
        $manifestCertified -and
        (-not [string]::IsNullOrWhiteSpace($manifestChain)) -and
        ($manifestChain -eq $independentFinalChain)
    )

    Add-TestResult `
        -Id 'T-10_ManifestCryptographicTruth' `
        -Pass $t10Pass `
        -Detail (
            "Certified=$manifestCertified, " +
            "manifestChain=$manifestChain, " +
            "independentChain=$independentFinalChain"
        )
}
catch {

    if (-not $cFinalAvailable) {

        Add-TestResult `
            -Id 'T-09_FinalArtifactsComplete' `
            -Pass $false `
            -Detail (
                "Impossible de démontrer la complétude : " +
                $_.Exception.Message
            )
    }

    Add-TestResult `
        -Id 'T-10_ManifestCryptographicTruth' `
        -Pass $false `
        -Detail (
            "Impossible de démontrer la vérité cryptographique : " +
            $_.Exception.Message
        )
}

# ============================================================================
# TEST F — POST-TEST ROOT CONFINEMENT
# ============================================================================

Write-Host ''
Write-Host '===============================================================================' -ForegroundColor Cyan
Write-Host ' TEST F — FINAL ROOT CONFINEMENT' -ForegroundColor Cyan
Write-Host '===============================================================================' -ForegroundColor Cyan

try {

    if ($aBefore.Count -lt 1) {
        throw 'Snapshot A initial indisponible.'
    }

    $aAfterFinal = @(
        Get-PhysicalSnapshot -Root $aCorpus
    )

    $t07Final = Compare-PhysicalSnapshot `
        -Before $aBefore `
        -After $aAfterFinal

    $t07Detail = ''

    if ($t07Final) {
        $t07Detail =
            'Snapshot physique A avant/après strictement identique.'
    }
    else {
        $t07Detail =
            'Mutation physique détectée dans RootPath A.'
    }

    Add-TestResult `
        -Id 'T-07_PostTestRootIntegrity' `
        -Pass $t07Final `
        -Detail $t07Detail
}
catch {

    Add-TestResult `
        -Id 'T-07_PostTestRootIntegrity' `
        -Pass $false `
        -Detail (
            "Snapshot final impossible : " +
            $_.Exception.Message
        )
}

# ============================================================================
# VERDICT
# ============================================================================

Write-Host ''
Write-Host '===============================================================================' -ForegroundColor Cyan
Write-Host ' ADVERSARIAL CERTIFICATION VERDICT' -ForegroundColor Cyan
Write-Host '===============================================================================' -ForegroundColor Cyan
Write-Host ''

$total = $Results.Count

$passed = @(
    $Results |
    Where-Object {
        $_.Pass -eq $true
    }
).Count

$failed = $total - $passed

foreach ($result in $Results) {

    $color = if ($result.Pass) {
        'Green'
    }
    else {
        'Red'
    }

    Write-Host (
        '[{0}] {1} — {2}' -f
        $result.Status,
        $result.Id,
        $result.Detail
    ) -ForegroundColor $color
}

Write-Host ''
Write-Host "TOTAL : $total"
Write-Host "PASS  : $passed"
Write-Host "FAIL  : $failed"
Write-Host ''

# ============================================================================
# ABSOLUTE GATE
# ============================================================================

$certified = (
    ($total -gt 0) -and
    ($failed -eq 0) -and
    ($passed -eq $total)
)

if ($certified) {

    Write-Host '===============================================================================' -ForegroundColor Green
    Write-Host ' ADVERSARIAL GATE : CERTIFIED' -ForegroundColor Green
    Write-Host '===============================================================================' -ForegroundColor Green
    Write-Host ''
    Write-Host '100 % des propriétés testées ont été démontrées mécaniquement.'
    Write-Host ''
    Write-Host 'Le harness ne prétend certifier que les propriétés effectivement testées.'
    Write-Host ''

    Remove-Item `
        -LiteralPath $TestRoot `
        -Recurse `
        -Force `
        -ErrorAction SilentlyContinue

    exit 0
}

Write-Host '===============================================================================' -ForegroundColor Red
Write-Host ' ADVERSARIAL GATE : FAIL' -ForegroundColor Red
Write-Host '===============================================================================' -ForegroundColor Red
Write-Host ''
Write-Host 'CERTIFICATION INTERDITE.'
Write-Host ''
Write-Host 'Les artefacts sont CONSERVÉS pour analyse forensic.'
Write-Host ''
Write-Host "FORENSIC ROOT : $TestRoot"
Write-Host ''

exit 1