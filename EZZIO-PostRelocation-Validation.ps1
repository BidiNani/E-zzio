# ==============================================================================
# E-ZZIO JSON VALIDATION PATCH v1.0
# READ ONLY
#
# Objectif :
#   - Valider correctement les JSON classiques
#   - Détecter et valider les JSONL / NDJSON
#   - Accepter les clés JSON vides via -AsHashtable
#   - Ne modifier aucun fichier
# ==============================================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ProjectRoot = 'G:\AI\E-zzio'

$Files = @(
    (Join-Path $ProjectRoot 'data\index_engine_v5.json'),
    (Join-Path $ProjectRoot 'ezzio-ui\package-lock.json')
)

Write-Host ''
Write-Host '============================================================' -ForegroundColor Cyan
Write-Host ' E-ZZIO JSON VALIDATION PATCH v1.0' -ForegroundColor Cyan
Write-Host '============================================================' -ForegroundColor Cyan
Write-Host '[INFO] MODE : READ ONLY' -ForegroundColor Gray
Write-Host '[INFO] Aucun fichier ne sera modifié.' -ForegroundColor Gray
Write-Host ''

function Test-JsonDocument {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    $result = [ordered]@{
        Path           = $Path
        Exists         = $false
        Type           = 'UNKNOWN'
        Valid          = $false
        Records        = 0
        Errors         = 0
        FirstError     = $null
    }

    Write-Host '------------------------------------------------------------' -ForegroundColor DarkGray
    Write-Host "FILE : $Path" -ForegroundColor Yellow

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        Write-Host '[FAIL] FICHIER ABSENT' -ForegroundColor Red
        return [pscustomobject]$result
    }

    $result.Exists = $true

    $item = Get-Item -LiteralPath $Path

    Write-Host ("SIZE : {0:N0} bytes" -f $item.Length) -ForegroundColor Gray

    $raw = Get-Content -LiteralPath $Path -Raw -Encoding UTF8

    if ([string]::IsNullOrWhiteSpace($raw)) {
        $result.Type = 'EMPTY'
        $result.FirstError = 'Fichier vide.'
        Write-Host '[FAIL] FICHIER JSON VIDE' -ForegroundColor Red
        return [pscustomobject]$result
    }

    $trimmed = $raw.Trim()

    # --------------------------------------------------------------------------
    # TEST 1 : JSON DOCUMENT CLASSIQUE
    # --------------------------------------------------------------------------

    try {
        $null = $trimmed | ConvertFrom-Json -AsHashtable -ErrorAction Stop

        $result.Type = 'JSON'
        $result.Valid = $true
        $result.Records = 1

        Write-Host '[OK]   TYPE : JSON DOCUMENT' -ForegroundColor Green
        Write-Host '[OK]   VALIDATION : PASS (-AsHashtable)' -ForegroundColor Green

        return [pscustomobject]$result
    }
    catch {
        $jsonDocumentError = $_.Exception.Message
    }

    # --------------------------------------------------------------------------
    # TEST 2 : JSONL / NDJSON
    # --------------------------------------------------------------------------

    $lines = Get-Content -LiteralPath $Path -Encoding UTF8

    $lineNumber = 0
    $validLines = 0
    $invalidLines = 0
    $firstLineError = $null

    foreach ($line in $lines) {

        $lineNumber++

        if ([string]::IsNullOrWhiteSpace($line)) {
            continue
        }

        try {
            $null = $line | ConvertFrom-Json -AsHashtable -ErrorAction Stop
            $validLines++
        }
        catch {
            $invalidLines++

            if ($null -eq $firstLineError) {
                $firstLineError = $_.Exception.Message
            }
        }
    }

    if ($validLines -gt 0 -and $invalidLines -eq 0) {

        $result.Type = 'JSONL/NDJSON'
        $result.Valid = $true
        $result.Records = $validLines

        Write-Host '[OK]   TYPE : JSONL / NDJSON' -ForegroundColor Green
        Write-Host ("[OK]   RECORDS : {0:N0}" -f $validLines) -ForegroundColor Green
        Write-Host '[OK]   VALIDATION : PASS' -ForegroundColor Green

        return [pscustomobject]$result
    }

    # --------------------------------------------------------------------------
    # ECHEC
    # --------------------------------------------------------------------------

    $result.Type = 'INVALID'
    $result.Valid = $false
    $result.Records = $validLines
    $result.Errors = $invalidLines

    if ($null -ne $firstLineError) {
        $result.FirstError = $firstLineError
    }
    else {
        $result.FirstError = $jsonDocumentError
    }

    Write-Host '[FAIL] VALIDATION : FAIL' -ForegroundColor Red

    if ($validLines -gt 0) {
        Write-Host ("[INFO] LIGNES JSON VALIDES : {0:N0}" -f $validLines) -ForegroundColor Yellow
        Write-Host ("[INFO] LIGNES JSON INVALIDES : {0:N0}" -f $invalidLines) -ForegroundColor Yellow
    }

    Write-Host "[INFO] ERREUR : $($result.FirstError)" -ForegroundColor Red

    return [pscustomobject]$result
}

# ==============================================================================
# EXECUTION
# ==============================================================================

$Results = foreach ($file in $Files) {
    Test-JsonDocument -Path $file
}

# ==============================================================================
# SYNTHESE
# ==============================================================================

$Passed = @($Results | Where-Object { $_.Valid }).Count
$Failed = @($Results | Where-Object { -not $_.Valid }).Count

Write-Host ''
Write-Host '============================================================' -ForegroundColor Cyan
Write-Host ' RESULTAT JSON' -ForegroundColor Cyan
Write-Host '============================================================' -ForegroundColor Cyan

foreach ($result in $Results) {

    if ($result.Valid) {
        Write-Host "[OK]   $($result.Type) | $($result.Path)" -ForegroundColor Green

        if ($result.Records -gt 1) {
            Write-Host ("       RECORDS : {0:N0}" -f $result.Records) -ForegroundColor Gray
        }
    }
    else {
        Write-Host "[FAIL] $($result.Path)" -ForegroundColor Red
        Write-Host "       $($result.FirstError)" -ForegroundColor Red
    }
}

Write-Host ''
Write-Host ("FILES VALIDES : {0}" -f $Passed) -ForegroundColor Green
Write-Host ("FILES FAIL    : {0}" -f $Failed) -ForegroundColor $(if ($Failed -eq 0) { 'Green' } else { 'Red' })

if ($Failed -eq 0) {
    Write-Host ''
    Write-Host '============================================================' -ForegroundColor Green
    Write-Host ' JSON VALIDATION : CLEAN' -ForegroundColor Green
    Write-Host '============================================================' -ForegroundColor Green
}
else {
    Write-Host ''
    Write-Host '============================================================' -ForegroundColor Red
    Write-Host ' JSON VALIDATION : FAILURES PRESENT' -ForegroundColor Red
    Write-Host '============================================================' -ForegroundColor Red
}

Write-Host ''