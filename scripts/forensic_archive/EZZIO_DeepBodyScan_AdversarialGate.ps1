#Requires -Version 7.0
<#
.SYNOPSIS
    E-ZZIO — AdversarialGate : porte de certification autonome pour
    EZZIO_DeepBodyScan_ContentTruth.ps1

.DESCRIPTION
    UNE SEULE COMMANDE. Aucune variable ne dépend d'une session PowerShell
    précédente : tout est déclaré et consommé dans ce fichier, dans cet ordre.

    IMPORTANT — comment lancer ce script :
        Ouvre un terminal PowerShell 7 FRAIS, puis exécute-le comme fichier :
            .\EZZIO_DeepBodyScan_AdversarialGate.ps1 -ScriptUnderTest ".\EZZIO_DeepBodyScan_ContentTruth.ps1"
        NE COLLE PAS son contenu ligne par ligne dans la console : un script
        collé en morceaux perd son état entre chaque bloc (variables non
        définies, blocs if/else séparés, etc.) — ce n'est PAS un bug du
        script, c'est un problème d'exécution.

    Chaque test (A à D) construit son propre corpus isolé sous un dossier
    temporaire dédié, pour qu'aucun test ne puisse être faussé par l'état
    laissé par un autre.

        TEST A — Correction de base
            T-01 hash exact (comparé indépendamment via Get-FileHash)
            T-02 comptage exact des records
            T-03 intégrité de la chaîne forensic (recalcul indépendant)
            T-07 confinement (RootPath strictement inchangé, exit code 0)

        TEST B — Gestion d'erreur
            T-04 un fichier verrouillé pendant le scan doit finir en
                 Status=ERROR, faire échouer la certification (exit != 0)
                 et NE PRODUIRE AUCUN dossier "run_<id>" final

        TEST C — Reprise après interruption
            T-05 records.jsonl tronqué + checkpoint honnête reconstruit
                 = interruption simulée ; la reprise doit terminer avec
                 exactement le bon nombre de records, sans doublon

        TEST D — Détection de falsification
            T-06 un ChainHash de checkpoint falsifié doit être REFUSÉ au
                 moment de la reprise (fail-closed, pas de reprise silencieuse)

    Le script produit un verdict unique à la fin, puis nettoie uniquement
    son propre dossier temporaire (jamais le script testé, jamais autre chose).

.PARAMETER ScriptUnderTest
    Chemin vers EZZIO_DeepBodyScan_ContentTruth.ps1
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ScriptUnderTest
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if (-not (Test-Path -LiteralPath $ScriptUnderTest)) {
    throw "Script à tester introuvable : $ScriptUnderTest"
}
$ScriptUnderTest = (Resolve-Path -LiteralPath $ScriptUnderTest).Path

$TestRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("ezzio_gate_" + (Get-Random))
New-Item -ItemType Directory -Path $TestRoot -Force | Out-Null
Write-Host "Environnement de test : $TestRoot"
Write-Host ""

$Results = [System.Collections.Generic.List[pscustomobject]]::new()

function Add-Result {
    param([string]$Id, [bool]$Pass, [string]$Detail)
    $script:Results.Add([pscustomobject]@{ Id = $Id; Pass = $Pass; Detail = $Detail })
    $status = if ($Pass) { 'PASS' } else { 'FAIL' }
    $color = if ($Pass) { 'Green' } else { 'Red' }
    Write-Host ("[{0}] {1} — {2}" -f $status, $Id, $Detail) -ForegroundColor $color
}

function Get-ChainFromRecordsFile {
    param([string]$RecordsPath)
    $chain = ''
    $sha = [System.Security.Cryptography.SHA256]::Create()
    foreach ($line in [System.IO.File]::ReadLines($RecordsPath)) {
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        $record = $line | ConvertFrom-Json
        $toHash = "$chain|$($record.RecordHash)"
        $bytes = $sha.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($toHash))
        $chain = [System.BitConverter]::ToString($bytes).Replace('-', '').ToLowerInvariant()
    }
    $sha.Dispose()
    return $chain
}

function Get-SingleTransactionDir {
    param([string]$OutputRoot)
    $dirs = @(Get-ChildItem -LiteralPath $OutputRoot -Directory -Filter '.transaction_*')
    if ($dirs.Count -ne 1) {
        throw "Attendu exactement 1 workspace transactionnel sous $OutputRoot, trouvé $($dirs.Count)."
    }
    return $dirs[0]
}

# ============================================================
# TEST A — Correction de base
# ============================================================
Write-Host "=== TEST A : correction de base ===" -ForegroundColor Cyan

$aCorpus = Join-Path $TestRoot 'A_corpus'
$aOutput = Join-Path $TestRoot 'A_output'
New-Item -ItemType Directory -Path $aCorpus, $aOutput -Force | Out-Null

Set-Content -LiteralPath (Join-Path $aCorpus 'normal.txt') -Value 'contenu normal E-ZZIO' -NoNewline -Encoding UTF8
New-Item -ItemType File -Path (Join-Path $aCorpus 'empty.txt') -Force | Out-Null
$bigContent = -join (1..20000 | ForEach-Object { '0123456789' })
Set-Content -LiteralPath (Join-Path $aCorpus 'big.txt') -Value $bigContent -NoNewline -Encoding UTF8
Set-Content -LiteralPath (Join-Path $aCorpus 'unicode_éàç_文件.txt') -Value 'texte accentué 你好' -NoNewline -Encoding UTF8
New-Item -ItemType Directory -Path (Join-Path $aCorpus 'sub') -Force | Out-Null
Set-Content -LiteralPath (Join-Path $aCorpus 'sub\nested.txt') -Value 'fichier imbriqué' -NoNewline -Encoding UTF8

$aFilesBefore = @(Get-ChildItem -LiteralPath $aCorpus -Recurse -File | Select-Object -ExpandProperty FullName | Sort-Object)
$aCount = $aFilesBefore.Count

& $ScriptUnderTest -RootPath $aCorpus -OutputRoot $aOutput -CheckpointEveryNFiles 2 *>&1 | Out-Null
$aExit = $LASTEXITCODE

$aTx = Get-SingleTransactionDir -OutputRoot $aOutput
$aRecordsPath = Join-Path $aTx.FullName 'staging\records.jsonl'
$aCheckpointPath = Join-Path $aTx.FullName 'staging\checkpoint.json'
$aRecords = @([System.IO.File]::ReadLines($aRecordsPath) | ForEach-Object { $_ | ConvertFrom-Json })

$aHashMismatches = @()
foreach ($record in $aRecords) {
    if ($record.Status -ne 'OBSERVED') { continue }
    $independentHash = (Get-FileHash -LiteralPath (Join-Path $aCorpus $record.RelativePath) -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($independentHash -ne $record.Hash) { $aHashMismatches += $record.RelativePath }
}
Add-Result -Id 'T-01_HashExact' -Pass ($aHashMismatches.Count -eq 0) -Detail "mismatches=$($aHashMismatches.Count)"
Add-Result -Id 'T-02_CountExact' -Pass ($aRecords.Count -eq $aCount) -Detail "records=$($aRecords.Count) corpus=$aCount"

$aChain = Get-ChainFromRecordsFile -RecordsPath $aRecordsPath
$aCheckpoint = Get-Content -LiteralPath $aCheckpointPath -Raw | ConvertFrom-Json
Add-Result -Id 'T-03_ChainIntegrity' -Pass ($aChain -eq $aCheckpoint.ChainHash) -Detail "recalc=$aChain checkpoint=$($aCheckpoint.ChainHash)"

$aFilesAfter = @(Get-ChildItem -LiteralPath $aCorpus -Recurse -File | Select-Object -ExpandProperty FullName | Sort-Object)
$aDiff = Compare-Object -ReferenceObject $aFilesBefore -DifferenceObject $aFilesAfter
Add-Result -Id 'T-07_RootUntouched' -Pass (($null -eq $aDiff) -and ($aExit -eq 0)) -Detail "diff=$(@($aDiff).Count) exit=$aExit"

Write-Host ""

# ============================================================
# TEST B — Gestion d'erreur (fichier verrouillé)
# ============================================================
Write-Host "=== TEST B : fichier verrouillé pendant le scan ===" -ForegroundColor Cyan

$bCorpus = Join-Path $TestRoot 'B_corpus'
$bOutput = Join-Path $TestRoot 'B_output'
New-Item -ItemType Directory -Path $bCorpus, $bOutput -Force | Out-Null

Set-Content -LiteralPath (Join-Path $bCorpus 'ok.txt') -Value 'lisible' -NoNewline -Encoding UTF8
$lockedPath = Join-Path $bCorpus 'locked.txt'
Set-Content -LiteralPath $lockedPath -Value 'sera verrouillé' -NoNewline -Encoding UTF8

$lockHandle = [System.IO.File]::Open($lockedPath, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::None)
try {
    & $ScriptUnderTest -RootPath $bCorpus -OutputRoot $bOutput -CheckpointEveryNFiles 1 *>&1 | Out-Null
    $bExit = $LASTEXITCODE
}
finally {
    $lockHandle.Dispose()
}

$bTx = Get-SingleTransactionDir -OutputRoot $bOutput
$bRecords = @([System.IO.File]::ReadLines((Join-Path $bTx.FullName 'staging\records.jsonl')) | ForEach-Object { $_ | ConvertFrom-Json })
$bLockedRecord = $bRecords | Where-Object { $_.RelativePath -eq 'locked.txt' }
$bRunIdCandidate = $bTx.Name -replace '^\.transaction_', ''
$bFinalDirExists = Test-Path -LiteralPath (Join-Path $bOutput ("run_" + $bRunIdCandidate))

Add-Result -Id 'T-04_LockedFileErrorNoFalseCertify' `
    -Pass (($bLockedRecord.Status -eq 'ERROR') -and ($bExit -ne 0) -and (-not $bFinalDirExists)) `
    -Detail "status=$($bLockedRecord.Status) exit=$bExit finalDirExists=$bFinalDirExists"

Write-Host ""

# ============================================================
# TEST C — Reprise après interruption simulée
# ============================================================
Write-Host "=== TEST C : reprise après interruption ===" -ForegroundColor Cyan

$cCorpus = Join-Path $TestRoot 'C_corpus'
$cOutput = Join-Path $TestRoot 'C_output'
New-Item -ItemType Directory -Path $cCorpus, $cOutput -Force | Out-Null
1..6 | ForEach-Object { Set-Content -LiteralPath (Join-Path $cCorpus "file_$_.txt") -Value "contenu numero $_" -NoNewline -Encoding UTF8 }
$cCount = 6

& $ScriptUnderTest -RootPath $cCorpus -OutputRoot $cOutput -CheckpointEveryNFiles 1 *>&1 | Out-Null

$cTx = Get-SingleTransactionDir -OutputRoot $cOutput
$cRecordsPath = Join-Path $cTx.FullName 'staging\records.jsonl'
$cCheckpointPath = Join-Path $cTx.FullName 'staging\checkpoint.json'
$cRunId = $cTx.Name -replace '^\.transaction_', ''

# Interruption simulée : on tronque records.jsonl à 3 lignes et on reconstruit
# un checkpoint honnête calculé UNIQUEMENT à partir des lignes conservées.
$allLines = @(Get-Content -LiteralPath $cRecordsPath)
$keptLines = $allLines | Select-Object -First 3
$keptLines | Set-Content -LiteralPath $cRecordsPath -Encoding UTF8

$tmpChainFile = Join-Path $TestRoot 'C_partial_for_chain.jsonl'
$keptLines | Set-Content -LiteralPath $tmpChainFile -Encoding UTF8
$partialChain = Get-ChainFromRecordsFile -RecordsPath $tmpChainFile

$honestCheckpoint = @{
    RunId = $cRunId; FilesProcessed = 3; TotalFiles = $cCount
    ChainHash = $partialChain; ErrorCount = 0
    LastUpdateUtc = (Get-Date).ToUniversalTime().ToString('o')
}
($honestCheckpoint | ConvertTo-Json) | Set-Content -LiteralPath $cCheckpointPath -Encoding UTF8

& $ScriptUnderTest -RootPath $cCorpus -OutputRoot $cOutput -ResumeRunId $cRunId -CheckpointEveryNFiles 1 *>&1 | Out-Null
$cResumeExit = $LASTEXITCODE

$cFinalRecords = @([System.IO.File]::ReadLines($cRecordsPath) | ForEach-Object { $_ | ConvertFrom-Json })
$cPaths = $cFinalRecords | Select-Object -ExpandProperty RelativePath
$cUniquePaths = @($cPaths | Select-Object -Unique)

Add-Result -Id 'T-05_ResumeCompletesCorrectly' `
    -Pass (($cFinalRecords.Count -eq $cCount) -and ($cUniquePaths.Count -eq $cCount) -and ($cResumeExit -eq 0)) `
    -Detail "records=$($cFinalRecords.Count) unique=$($cUniquePaths.Count) attendu=$cCount exit=$cResumeExit"

Write-Host ""

# ============================================================
# TEST D — Détection de falsification du checkpoint
# ============================================================
Write-Host "=== TEST D : checkpoint falsifié ===" -ForegroundColor Cyan

$dCorpus = Join-Path $TestRoot 'D_corpus'
$dOutput = Join-Path $TestRoot 'D_output'
New-Item -ItemType Directory -Path $dCorpus, $dOutput -Force | Out-Null
1..3 | ForEach-Object { Set-Content -LiteralPath (Join-Path $dCorpus "f_$_.txt") -Value "d$_" -NoNewline -Encoding UTF8 }

& $ScriptUnderTest -RootPath $dCorpus -OutputRoot $dOutput -CheckpointEveryNFiles 1 *>&1 | Out-Null

$dTx = Get-SingleTransactionDir -OutputRoot $dOutput
$dCheckpointPath = Join-Path $dTx.FullName 'staging\checkpoint.json'
$dRunId = $dTx.Name -replace '^\.transaction_', ''

$tamperedCheckpoint = Get-Content -LiteralPath $dCheckpointPath -Raw | ConvertFrom-Json
$tamperedCheckpoint.ChainHash = ('deadbeef' * 8)
($tamperedCheckpoint | ConvertTo-Json) | Set-Content -LiteralPath $dCheckpointPath -Encoding UTF8

$dRejected = $false
try {
    & $ScriptUnderTest -RootPath $dCorpus -OutputRoot $dOutput -ResumeRunId $dRunId -CheckpointEveryNFiles 1 2>&1 | Out-Null
}
catch {
    if ($_.Exception.Message -match 'FAIL-CLOSED') { $dRejected = $true }
}
Add-Result -Id 'T-06_TamperedChainRejected' -Pass $dRejected -Detail "rejected=$dRejected"

Write-Host ""

# ============================================================
# VERDICT
# ============================================================
Write-Host "=== VERDICT ===" -ForegroundColor Cyan
$passed = @($Results | Where-Object Pass).Count
$total = $Results.Count
foreach ($r in $Results) {
    $status = if ($r.Pass) { 'PASS' } else { 'FAIL' }
    Write-Host "  [$status] $($r.Id) — $($r.Detail)"
}
Write-Host ""
if ($passed -eq $total) {
    Write-Host "$passed / $total — le moteur respecte ses garanties fondamentales sur ce corpus adversarial." -ForegroundColor Green
}
else {
    Write-Host "$passed / $total — $($total - $passed) échec(s). Corriger EZZIO_DeepBodyScan_ContentTruth.ps1 avant de le lancer sur le corps réel." -ForegroundColor Red
}

Remove-Item -LiteralPath $TestRoot -Recurse -Force -ErrorAction SilentlyContinue
Write-Host ""
Write-Host "Environnement de test nettoyé ($TestRoot)."

if ($passed -ne $total) { exit 1 }
