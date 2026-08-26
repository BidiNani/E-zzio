#Requires -Version 7.0
<#
.SYNOPSIS
    E-ZZIO — Harnais de test adversarial pour EZZIO_DeepBodyScan_ContentTruth.ps1

.DESCRIPTION
    Ne teste PAS le corps réel d'E-zzio. Construit un corpus synthétique dans un
    dossier temporaire conçu pour piéger le moteur, puis vérifie mécaniquement
    (pas de confiance sur le "ça a tourné sans erreur") que chaque garantie
    annoncée est réellement respectée :

      T-01  Hash exact          : le hash de chaque record == Get-FileHash indépendant
      T-02  Comptage exact       : nb records == nb fichiers du corpus
      T-03  Chaîne intègre       : la chaîne recalculée == checkpoint final
      T-04  Erreur détectée      : un fichier verrouillé (illisible) produit Status=ERROR
                                    et fait échouer la gate G-04, PAS de faux PASS
      T-05  Reprise correcte     : interruption simulée puis -ResumeRunId termine le
                                    travail sans dupliquer ni sauter de fichier
      T-06  Tampering détecté    : un ChainHash de checkpoint falsifié doit être
                                    rejeté au moment de la reprise (fail-closed)
      T-07  Confinement          : le script ne doit écrire STRICTEMENT rien à
                                    l'intérieur du RootPath scanné

    Chaque test affiche PASS/FAIL explicitement. Le harnais s'arrête et affiche
    un résumé final — il ne "suppose" jamais qu'un test a réussi.

.PARAMETER ScriptUnderTest
    Chemin vers EZZIO_DeepBodyScan_ContentTruth.ps1

.EXAMPLE
    .\EZZIO_DeepBodyScan_TestHarness.ps1 -ScriptUnderTest ".\EZZIO_DeepBodyScan_ContentTruth.ps1"
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
$ScriptUnderTest = (Resolve-Path $ScriptUnderTest).Path

$TestResults = [System.Collections.Generic.List[object]]::new()
function Record-Test {
    param([string]$Id, [bool]$Pass, [string]$Detail)
    $script:TestResults.Add([pscustomobject]@{ Id = $Id; Pass = $Pass; Detail = $Detail })
    $status = if ($Pass) { 'PASS' } else { 'FAIL' }
    $color = if ($Pass) { 'Green' } else { 'Red' }
    Write-Host "[$status] $Id — $Detail" -ForegroundColor $color
}

# ============================================================
# CONSTRUCTION DU CORPUS SYNTHÉTIQUE
# ============================================================

$TestRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("ezzio_test_" + (Get-Random))
$CorpusDir = Join-Path $TestRoot 'corpus'
$OutputDir = Join-Path $TestRoot 'output'
New-Item -ItemType Directory -Path $CorpusDir -Force | Out-Null
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

Write-Host "Corpus de test : $CorpusDir"
Write-Host "Sortie forensic : $OutputDir"
Write-Host ""

# Fichier normal
Set-Content -LiteralPath (Join-Path $CorpusDir 'normal.txt') -Value 'Contenu normal E-ZZIO' -Encoding UTF8 -NoNewline

# Fichier vide
New-Item -ItemType File -Path (Join-Path $CorpusDir 'empty.txt') -Force | Out-Null

# Fichier "gros" pour forcer plusieurs itérations de streaming (> ChunkSize par défaut si on le réduit)
$bigContent = -join (1..50000 | ForEach-Object { 'ABCDEFGHIJ' })
Set-Content -LiteralPath (Join-Path $CorpusDir 'big.txt') -Value $bigContent -Encoding UTF8 -NoNewline

# Fichier unicode
Set-Content -LiteralPath (Join-Path $CorpusDir 'unicode_éàç_文件.txt') -Value 'Contenu accentué et unicode 你好' -Encoding UTF8 -NoNewline

# Sous-dossier avec fichier
New-Item -ItemType Directory -Path (Join-Path $CorpusDir 'sub') -Force | Out-Null
Set-Content -LiteralPath (Join-Path $CorpusDir 'sub\nested.txt') -Value 'Fichier imbriqué' -Encoding UTF8 -NoNewline

# Fichier qui sera verrouillé pendant le scan (pour T-04)
$lockedFilePath = Join-Path $CorpusDir 'locked.txt'
Set-Content -LiteralPath $lockedFilePath -Value 'Ce fichier sera verrouillé' -Encoding UTF8 -NoNewline

$corpusFileCount = (Get-ChildItem -LiteralPath $CorpusDir -Recurse -File).Count
Write-Host "Corpus construit : $corpusFileCount fichiers"
Write-Host ""

# ============================================================
# T-04 (préparation) : verrouiller un fichier en exclusif pendant le run
# ============================================================

Write-Host "=== T-01 à T-04 : premier run complet (avec fichier verrouillé) ===" -ForegroundColor Cyan

$lockStream = [System.IO.File]::Open($lockedFilePath, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::None)

try {
    & $ScriptUnderTest -RootPath $CorpusDir -OutputRoot $OutputDir -CheckpointEveryNFiles 2 2>&1 | Out-Null
    $firstRunExitCode = $LASTEXITCODE
}
finally {
    $lockStream.Dispose()
}

# Retrouver le run (non certifié à cause du fichier verrouillé)
$transactionDir = Get-ChildItem -LiteralPath $OutputDir -Directory -Filter '.transaction_*' | Select-Object -First 1
if (-not $transactionDir) {
    Record-Test -Id 'T-00_RunProduced' -Pass $false -Detail "Aucun workspace transactionnel trouvé — le script n'a pas tourné correctement."
    exit 1
}
$runId = $transactionDir.Name -replace '^\.transaction_', ''
$stagingRecords = Join-Path $transactionDir.FullName 'staging\records.jsonl'
$stagingCheckpoint = Join-Path $transactionDir.FullName 'staging\checkpoint.json'

# T-04 : le fichier verrouillé doit apparaître en ERROR, et la gate G-04 doit avoir échoué (pas de certification)
$lockedRecord = [System.IO.File]::ReadLines($stagingRecords) | ForEach-Object { $_ | ConvertFrom-Json } | Where-Object { $_.RelativePath -eq 'locked.txt' }
$t04Pass = ($lockedRecord.Status -eq 'ERROR') -and ($firstRunExitCode -eq 1)
Record-Test -Id 'T-04_LockedFileDetectedAsError' -Pass $t04Pass -Detail "Status=$($lockedRecord.Status), exit code=$firstRunExitCode (attendu: ERROR / 1, pas de certification silencieuse)"

# T-01 : le hash de chaque fichier lisible == hash indépendant calculé par Get-FileHash
$allRecords = [System.IO.File]::ReadLines($stagingRecords) | ForEach-Object { $_ | ConvertFrom-Json }
$hashMismatches = @()
foreach ($rec in $allRecords) {
    if ($rec.Status -ne 'OBSERVED') { continue }
    $fullPath = Join-Path $CorpusDir $rec.RelativePath
    $independentHash = (Get-FileHash -LiteralPath $fullPath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($independentHash -ne $rec.Hash) {
        $hashMismatches += $rec.RelativePath
    }
}
Record-Test -Id 'T-01_HashesExact' -Pass ($hashMismatches.Count -eq 0) -Detail "Fichiers avec hash divergent : $($hashMismatches.Count) $(if ($hashMismatches.Count -gt 0) { '(' + ($hashMismatches -join ', ') + ')' })"

# T-02 : comptage exact (locked.txt compte comme découvert même s'il finit en ERROR)
Record-Test -Id 'T-02_RecordCountExact' -Pass ($allRecords.Count -eq $corpusFileCount) -Detail "records=$($allRecords.Count), corpus=$corpusFileCount"

# T-03 : intégrité de la chaîne (recalcul indépendant depuis records.jsonl)
$checkpoint = Get-Content -LiteralPath $stagingCheckpoint -Raw | ConvertFrom-Json
$verifyChain = ''
$sha = [System.Security.Cryptography.SHA256]::Create()
foreach ($rec in $allRecords) {
    $toHash = "$verifyChain|$($rec.RecordHash)"
    $bytes = $sha.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($toHash))
    $verifyChain = [System.BitConverter]::ToString($bytes).Replace('-', '').ToLowerInvariant()
}
$sha.Dispose()
Record-Test -Id 'T-03_ChainIntegrity' -Pass ($verifyChain -eq $checkpoint.ChainHash) -Detail "recalculé=$verifyChain, checkpoint=$($checkpoint.ChainHash)"

# T-07 : confinement — aucune écriture dans CorpusDir
$corpusFilesAfter = Get-ChildItem -LiteralPath $CorpusDir -Recurse -File | Select-Object -ExpandProperty FullName | Sort-Object
$corpusFilesBefore = @(
    (Join-Path $CorpusDir 'normal.txt'), (Join-Path $CorpusDir 'empty.txt'), (Join-Path $CorpusDir 'big.txt'),
    (Join-Path $CorpusDir 'unicode_éàç_文件.txt'), (Join-Path $CorpusDir 'sub\nested.txt'), $lockedFilePath
) | Sort-Object
$diff = Compare-Object -ReferenceObject $corpusFilesBefore -DifferenceObject $corpusFilesAfter
Record-Test -Id 'T-07_RootPathUntouched' -Pass ($null -eq $diff) -Detail "Différences détectées dans le corpus : $($diff.Count)"

Write-Host ""
Write-Host "=== T-06 : tampering du checkpoint doit être rejeté à la reprise ===" -ForegroundColor Cyan

# On corrompt volontairement le ChainHash du checkpoint
$tamperedCheckpoint = Get-Content -LiteralPath $stagingCheckpoint -Raw | ConvertFrom-Json
$tamperedCheckpoint.ChainHash = 'deadbeef' * 8
($tamperedCheckpoint | ConvertTo-Json) | Set-Content -LiteralPath $stagingCheckpoint -Encoding UTF8

$tamperRejected = $false
try {
    & $ScriptUnderTest -RootPath $CorpusDir -OutputRoot $OutputDir -ResumeRunId $runId -CheckpointEveryNFiles 2 2>&1 | Out-Null
}
catch {
    if ($_.Exception.Message -match 'FAIL-CLOSED') { $tamperRejected = $true }
}
Record-Test -Id 'T-06_TamperedChainRejected' -Pass $tamperRejected -Detail "Le script a $(if ($tamperRejected) { 'refusé' } else { 'accepté' }) un checkpoint falsifié"

Write-Host ""
Write-Host "=== T-05 : reprise correcte après interruption simulée (checkpoint honnête) ===" -ForegroundColor Cyan

# Nouveau run propre, sans fichier verrouillé cette fois, interrompu manuellement à mi-chemin
$runId2 = $null
& $ScriptUnderTest -RootPath $CorpusDir -OutputRoot $OutputDir -CheckpointEveryNFiles 2 2>&1 | Out-Null
# Ce run échoue aussi tant que locked.txt existe : on le retire pour isoler T-05
Remove-Item -LiteralPath $lockedFilePath -Force

$transactionDir2 = Get-ChildItem -LiteralPath $OutputDir -Directory -Filter '.transaction_*' |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1
$runId2 = $transactionDir2.Name -replace '^\.transaction_', ''
$stagingRecords2 = Join-Path $transactionDir2.FullName 'staging\records.jsonl'

# Tronquer artificiellement records.jsonl et régénérer un checkpoint honnête pour ne garder
# que les 3 premiers records (simulation d'une interruption après 3 fichiers)
$lines = Get-Content -LiteralPath $stagingRecords2
$keepCount = [Math]::Min(3, $lines.Count - 1)  # -1 pour exclure potentiellement locked.txt s'il est resté
$truncatedLines = $lines | Select-Object -First $keepCount
$truncatedLines | Set-Content -LiteralPath $stagingRecords2 -Encoding UTF8

$verifyChain2 = ''
$sha2 = [System.Security.Cryptography.SHA256]::Create()
foreach ($line in $truncatedLines) {
    $rec = $line | ConvertFrom-Json
    $toHash = "$verifyChain2|$($rec.RecordHash)"
    $bytes = $sha2.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($toHash))
    $verifyChain2 = [System.BitConverter]::ToString($bytes).Replace('-', '').ToLowerInvariant()
}
$sha2.Dispose()

$honestCheckpoint = @{
    RunId = $runId2; FilesProcessed = $keepCount; TotalFiles = $corpusFileCount - 1
    ChainHash = $verifyChain2; ErrorCount = 0; LastUpdateUtc = (Get-Date).ToUniversalTime().ToString('o')
}
($honestCheckpoint | ConvertTo-Json) | Set-Content -LiteralPath (Join-Path $transactionDir2.FullName 'staging\checkpoint.json') -Encoding UTF8

& $ScriptUnderTest -RootPath $CorpusDir -OutputRoot $OutputDir -ResumeRunId $runId2 -CheckpointEveryNFiles 2 2>&1 | Out-Null
$resumeExitCode = $LASTEXITCODE

$finalRecords2 = [System.IO.File]::ReadLines($stagingRecords2) | ForEach-Object { $_ | ConvertFrom-Json }
$expectedAfterResume = $corpusFileCount - 1  # sans locked.txt, supprimé avant ce run
$t05Pass = ($finalRecords2.Count -eq $expectedAfterResume) -and ($resumeExitCode -eq 0)
Record-Test -Id 'T-05_ResumeCompletesCorrectly' -Pass $t05Pass -Detail "records après reprise=$($finalRecords2.Count), attendu=$expectedAfterResume, exit code=$resumeExitCode"

# ============================================================
# RÉSUMÉ FINAL
# ============================================================

Write-Host ""
Write-Host "=== RÉSUMÉ ===" -ForegroundColor Cyan
$passed = ($TestResults | Where-Object Pass).Count
$total = $TestResults.Count
foreach ($t in $TestResults) {
    $status = if ($t.Pass) { 'PASS' } else { 'FAIL' }
    Write-Host "  [$status] $($t.Id)"
}
Write-Host ""
if ($passed -eq $total) {
    Write-Host "$passed / $total tests PASSED — le moteur fait ce qu'il prétend sur ce corpus adversarial." -ForegroundColor Green
}
else {
    Write-Host "$passed / $total tests PASSED — $($total - $passed) échec(s) à corriger avant certification." -ForegroundColor Red
}

Write-Host ""
Write-Host "Corpus et sorties de test conservés pour inspection : $TestRoot"
