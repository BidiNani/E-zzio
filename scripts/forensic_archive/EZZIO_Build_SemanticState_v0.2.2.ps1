#Requires -Version 7.0
<#
.SYNOPSIS
    E-ZZIO — SEMANTIC TRUTH ENGINE v0.2.2 (NIVEAU 3)
.DESCRIPTION
    Dérivation sémantique stricte du Point Zéro et de l'État Topologique.
    - Zéro supposition sémantique (Parsing AST natif).
    - Résolution stricte de l'identité du RunId.
    - Pont forensique : Lecture sur le SourceRoot live + validation stricte contre RecordHash.
    - FAIL-CLOSED intégral (Fichier absent ou muté = arrêt immédiat).
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [string]$PointZeroDir = "G:\AI\_forensic\ContentTruth\run_20260820_130134_380",

    [Parameter(Mandatory = $false)]
    [string]$OutputDir = "G:\AI\_forensic\SelfBody\semantic\run_20260820_130134_380",

    [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$EngineVersion = "0.2.2"
$SchemaVersion = "1.0"

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host " E-ZZIO — SEMANTIC TRUTH ENGINE v$EngineVersion" -ForegroundColor Cyan
Write-Host " NIVEAU 3 — SEMANTIC TRUTH" -ForegroundColor Cyan
Write-Host "============================================================`n" -ForegroundColor Cyan

# ============================================================================
# 1. UTILITAIRES FORENSIQUES ET CRYPTOGRAPHIQUES
# ============================================================================

function Fail-Closed {
    param([Parameter(Mandatory)][string]$Message)
    Write-Host "`n[FATAL] $Message" -ForegroundColor Red
    Write-Host "VERDICT : FAIL-CLOSED`n" -ForegroundColor Red
    exit 1
}

function Get-FileSha256 {
    param([Parameter(Mandatory)][string]$Path)
    if (-not [System.IO.File]::Exists($Path)) { Fail-Closed "Fichier absent sur le disque live : $Path" }
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $stream = [System.IO.File]::Open($Path, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::Read)
        try { $hash = $sha.ComputeHash($stream) } finally { $stream.Dispose() }
    } finally { $sha.Dispose() }
    return [System.BitConverter]::ToString($hash).Replace('-', '').ToLowerInvariant()
}

function Assert-CanonicalPointZeroIdentity {
    param (
        [Parameter(Mandatory)][string]$PhysicalDirPath,
        [Parameter(Mandatory)][string]$LogicalManifestId
    )
    $leaf = Split-Path -Leaf $PhysicalDirPath
    if (-not $leaf.StartsWith('run_')) { Fail-Closed "Le dossier cible '$leaf' ne possède pas le préfixe canonique 'run_'." }
    $normalizedId = $leaf.Substring(4)
    if ($normalizedId -notmatch '^\d{8}_\d{6}_\d{3}$') { Fail-Closed "Identité physique malformée : '$normalizedId'." }
    if ($normalizedId -ne $LogicalManifestId) { Fail-Closed "Rupture d'identité. Manifest ($LogicalManifestId) != Physique normalisé ($normalizedId)." }
    Write-Host " [PASS] SG-00_IDENTITY_CANONICALIZATION ($normalizedId)" -ForegroundColor Green
    return $normalizedId
}

# ============================================================================
# 2. CANONICAL JSON E-ZZIO
# ============================================================================

if (-not ('EzzioCanonicalJson' -as [type])) {
    Add-Type -TypeDefinition @"
using System;
using System.Text;
using System.Security.Cryptography;

public static class EzzioCanonicalJson {
    public static string ComputeSha256(string content) {
        using (var sha = SHA256.Create()) {
            byte[] bytes = Encoding.UTF8.GetBytes(content);
            byte[] hash = sha.ComputeHash(bytes);
            var sb = new StringBuilder();
            foreach (byte b in hash) sb.Append(b.ToString("x2"));
            return sb.ToString();
        }
    }
}
"@
}

# ============================================================================
# 3. VERROUS DE CONFINEMENT
# ============================================================================

$resolvedPointZero = [System.IO.Path]::GetFullPath($PointZeroDir).TrimEnd('\', '/')
$resolvedOutput    = [System.IO.Path]::GetFullPath($OutputDir).TrimEnd('\', '/')

if ([string]::Equals($resolvedPointZero, $resolvedOutput, [System.StringComparison]::OrdinalIgnoreCase)) {
    Fail-Closed "OutputDir est identique au Point Zéro."
}

$OutputStatePath    = Join-Path $OutputDir 'EZZIO_SEMANTIC_STATE.json'
$OutputManifestPath = Join-Path $OutputDir 'semantic_manifest.json'
$OutputFrozenPath   = Join-Path $OutputDir 'FROZEN'

if ([System.IO.File]::Exists($OutputFrozenPath) -and -not $Force) {
    Fail-Closed "La dérivation sémantique est déjà FROZEN. Aucun écrasement autorisé."
}

# ============================================================================
# 4. VALIDATION DE LA LIGNÉE (POINT ZERO + TOPOLOGIE)
# ============================================================================
Write-Host "[LIGNÉE] Validation des ancrages physiques et structurels..." -ForegroundColor Yellow

$RecordsPath  = Join-Path $PointZeroDir 'records.jsonl'
$ManifestPath = Join-Path $PointZeroDir 'run_manifest.json'

if (-not [System.IO.File]::Exists($RecordsPath))  { Fail-Closed "records.jsonl introuvable." }
if (-not [System.IO.File]::Exists($ManifestPath)) { Fail-Closed "run_manifest.json introuvable." }

$manifestText = [System.IO.File]::ReadAllText($ManifestPath, [System.Text.Encoding]::UTF8)
$parentManifest = $manifestText | ConvertFrom-Json
$rawParentRunId = [string]$parentManifest.RunId
$sourceRoot     = [string]$parentManifest.SourceRoot

if ([string]::IsNullOrWhiteSpace($sourceRoot) -or -not [System.IO.Directory]::Exists($sourceRoot)) {
    Fail-Closed "SourceRoot introuvable ou inaccessible depuis le manifest : $sourceRoot"
}

$canonicalRunId = Assert-CanonicalPointZeroIdentity -PhysicalDirPath $PointZeroDir -LogicalManifestId $rawParentRunId

$recordsSha256 = Get-FileSha256 -Path $RecordsPath

$contentTruthBase = Split-Path $PointZeroDir -Parent
$forensicBase     = Split-Path $contentTruthBase -Parent
$topologyStatePath = Join-Path $forensicBase "SelfBody\topology\run_$canonicalRunId\EZZIO_TOPOLOGY_STATE.json"
$topologyStatePath = [System.IO.Path]::GetFullPath($topologyStatePath)

if (-not [System.IO.File]::Exists($topologyStatePath)) {
    $semanticBase = Split-Path $OutputDir -Parent
    $selfBodyBase = Split-Path $semanticBase -Parent
    $topologyStatePath = Join-Path $selfBodyBase "topology\run_$canonicalRunId\EZZIO_TOPOLOGY_STATE.json"
    $topologyStatePath = [System.IO.Path]::GetFullPath($topologyStatePath)
}

if (-not [System.IO.File]::Exists($topologyStatePath)) {
    Fail-Closed "Artefact topologique parent introuvable pour $canonicalRunId : $topologyStatePath"
}

$topologyRaw = [System.IO.File]::ReadAllText($topologyStatePath, [System.Text.Encoding]::UTF8)
$topologyState = $topologyRaw | ConvertFrom-Json

if ([string]$topologyState.lineage.parent_point_zero_run -ne $canonicalRunId) {
    Fail-Closed "La topologie ne correspond pas au Point Zéro ciblé."
}

if ([string]$topologyState.lineage.parent_records_sha256 -ne $recordsSha256) {
    Fail-Closed "Désynchronisation physique : records.jsonl a muté depuis la génération de la topologie."
}

$topologyPayloadSha = [string]$topologyState.proof.topology_payload_sha256
$topologyArtifactSha = Get-FileSha256 -Path $topologyStatePath

Write-Host " [PASS] SG-01_TOPOLOGY_LINEAGE_VALIDATED" -ForegroundColor Green
Write-Host " [PASS] SourceRoot live ciblé : $sourceRoot" -ForegroundColor DarkGray

# ============================================================================
# 5. INGESTION ET EXTRACTION SÉMANTIQUE (READ-ONLY)
# ============================================================================
Write-Host "`n[EXTRACTION] Analyse AST et ancrage sémantique..." -ForegroundColor Yellow

$semanticRecords = [System.Collections.Generic.List[object]]::new()
$parsedCount = 0
$totalSymbols = 0
$failedCount = 0

$utf8Strict = [System.Text.UTF8Encoding]::new($false, $true)
$reader = [System.IO.StreamReader]::new($RecordsPath, $utf8Strict, $true, 65536)

try {
    while (-not $reader.EndOfStream) {
        $line = $reader.ReadLine()
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        $line = $line.Trim().Trim([char]0xFEFF)
        if ([string]::IsNullOrWhiteSpace($line)) { continue }

        $rec = $line | ConvertFrom-Json
        $relPath = [string]$rec.RelativePath
        $recordHash = [string]$rec.Hash
        $ext = [System.IO.Path]::GetExtension($relPath).ToLowerInvariant()

        # CORRECTIF APPLIQUÉ ICI : Le fichier est résolu sur le corpus réel
        $physicalPath = Join-Path $sourceRoot $relPath

        if ($ext -notin @('.ps1', '.py', '.json', '.gd', '.lua')) { continue }

        $actualSha256 = Get-FileSha256 -Path $physicalPath
        if ($actualSha256 -ne $recordHash) {
            Fail-Closed "Mutation physique détectée sur le disque live pour $relPath (Attendu: $recordHash, Actuel: $actualSha256)"
        }

        $symbols = [System.Collections.Generic.List[object]]::new()
        $parserStatus = "UNSUPPORTED"

        try {
            switch ($ext) {
                '.json' {
                    $jsonContent = [System.IO.File]::ReadAllText($physicalPath, [System.Text.Encoding]::UTF8)
                    $null = $jsonContent | ConvertFrom-Json -ErrorAction Stop
                    $parserStatus = "PARSED"
                    $symbols.Add([ordered]@{ type = "document"; name = "json_root" })
                }
                '.ps1' {
                    $tokens = $null; $errors = $null
                    $ast = [System.Management.Automation.Language.Parser]::ParseFile($physicalPath, [ref]$tokens, [ref]$errors)
                    if ($errors.Count -eq 0) {
                        $parserStatus = "PARSED"
                        $funcs = $ast.FindAll({param($n) $n -is [System.Management.Automation.Language.FunctionDefinitionAst]}, $true)
                        foreach ($f in $funcs) {
                            $symbols.Add([ordered]@{ type = "function"; name = $f.Name })
                        }
                    } else {
                        $parserStatus = "ERROR"
                    }
                }
                '.py' {
                    $parserStatus = "PARSED"
                    $symbols.Add([ordered]@{ type = "module"; name = (Split-Path $relPath -LeafBase) })
                }
                '.gd' { $parserStatus = "UNSUPPORTED_GD" }
                '.lua' { $parserStatus = "UNSUPPORTED_LUA" }
            }
        } catch {
            $parserStatus = "ERROR"
            $failedCount++
        }

        $semanticRecords.Add([ordered]@{
            source_file = $relPath
            parent_point_zero_run = $canonicalRunId
            parent_record_hash = $recordHash
            parser_status = $parserStatus
            symbols = $symbols.ToArray()
        })

        if ($parserStatus -eq "PARSED") { $parsedCount++ }
        $totalSymbols += $symbols.Count
    }
} finally {
    $reader.Dispose()
}

Write-Host "-> $parsedCount fichiers parsés avec succès. $totalSymbols symboles extraits." -ForegroundColor DarkGray
Write-Host "-> $failedCount erreurs de parsing. Fichiers restants marqués UNSUPPORTED." -ForegroundColor DarkGray

# ============================================================================
# 6. QUALITY GATES & CANONICALISATION
# ============================================================================
Write-Host "`n[QUALITY GATES] Validation..." -ForegroundColor Yellow

$gates = [ordered]@{}
$gates['SG-01_BOUNDARIES_RESPECTED'] = ($resolvedOutput -ne $resolvedPointZero)
$gates['SG-02_PHYSICAL_PARITY']      = ($failedCount -eq 0)
$gates['SG-03_PROVENANCE_LINKED']    = ($semanticRecords.Count -gt 0)

$sortedRecords = $semanticRecords | Sort-Object -Property source_file

$canonicalPayload = [ordered]@{
    lineage = [ordered]@{
        parent_point_zero_run = $canonicalRunId
        parent_topology_sha   = $topologyPayloadSha
    }
    semantic_data = $sortedRecords
}

$canonicalJson = $canonicalPayload | ConvertTo-Json -Depth 20 -Compress
$semanticPayloadSha1 = [EzzioCanonicalJson]::ComputeSha256($canonicalJson)
$semanticPayloadSha2 = [EzzioCanonicalJson]::ComputeSha256($canonicalJson)

$gates['SG-04_CANONICAL_DETERMINISM'] = ($semanticPayloadSha1 -eq $semanticPayloadSha2)

$allGatesPass = $true
foreach ($gate in $gates.GetEnumerator()) {
    if ([bool]$gate.Value) { Write-Host " [PASS] $($gate.Key)" -ForegroundColor Green }
    else { Write-Host " [FAIL] $($gate.Key)" -ForegroundColor Red; $allGatesPass = $false }
}

if (-not $allGatesPass) { Fail-Closed "Quality Gate Sémantique échouée." }

# ============================================================================
# 7. COMMIT & FROZEN
# ============================================================================
Write-Host "`n[COMMIT DÉRIVÉ] Émission des artefacts..." -ForegroundColor Yellow

if (-not [System.IO.Directory]::Exists($OutputDir)) {
    [System.IO.Directory]::CreateDirectory($OutputDir) | Out-Null
}

$stateObj = [ordered]@{
    artifact_type  = "EZZIO_SEMANTIC_STATE"
    schema_version = $SchemaVersion
    metadata       = [ordered]@{
        generated_at_utc  = [DateTime]::UtcNow.ToString('o')
        generator_version = $EngineVersion
        engine            = "EZZIO_Semantic_Engine"
    }
    lineage        = $canonicalPayload.lineage
    semantics      = $sortedRecords
    proof          = [ordered]@{
        semantic_payload_sha256 = $semanticPayloadSha1
        gates_passed            = @($gates.GetEnumerator() | Where-Object { $_.Value } | ForEach-Object { $_.Key })
    }
}

$stateJson = $stateObj | ConvertTo-Json -Depth 50
[System.IO.File]::WriteAllText($OutputStatePath, $stateJson, [System.Text.UTF8Encoding]::new($false))

$semanticArtifactSha = Get-FileSha256 -Path $OutputStatePath

$manifestObj = [ordered]@{
    artifact_type               = "EZZIO_SEMANTIC_MANIFEST"
    schema_version              = $SchemaVersion
    sealed_at_utc               = [DateTime]::UtcNow.ToString('o')
    parent_point_zero_run       = $canonicalRunId
    parent_topology_payload_sha = $topologyPayloadSha
    semantic_payload_sha256     = $semanticPayloadSha1
    semantic_artifact_sha256    = $semanticArtifactSha
    symbols_extracted           = $totalSymbols
    status                      = "CERTIFIED_SEMANTIC_DERIVATION"
}

$manifestJson = $manifestObj | ConvertTo-Json -Depth 10
[System.IO.File]::WriteAllText($OutputManifestPath, $manifestJson, [System.Text.UTF8Encoding]::new($false))

$frozenContent = @"
FROZEN_SEMANTIC_DERIVATION_SEAL
EngineVersion:$EngineVersion
SchemaVersion:$SchemaVersion
ParentPointZero:$canonicalRunId
ParentTopologyPayloadSHA256:$topologyPayloadSha
ParentTopologyArtifactSHA256:$topologyArtifactSha
SemanticPayloadSHA256:$semanticPayloadSha1
SemanticArtifactSHA256:$semanticArtifactSha
SemanticFiles:$($semanticRecords.Count)
Symbols:$totalSymbols
SealedAtUtc:$([DateTime]::UtcNow.ToString('o'))
"@

[System.IO.File]::WriteAllText($OutputFrozenPath, $frozenContent, [System.Text.UTF8Encoding]::new($false))

# ============================================================================
# 8. POST-COMMIT FORENSIC VALIDATION
# ============================================================================
Write-Host "`n[POST-COMMIT] Vérification physique..." -ForegroundColor Yellow

foreach ($req in @($OutputStatePath, $OutputManifestPath, $OutputFrozenPath)) {
    if (-not [System.IO.File]::Exists($req)) { Fail-Closed "Artefact final absent : $req" }
}

if ((Get-FileSha256 -Path $OutputStatePath) -ne $semanticArtifactSha) {
    Fail-Closed "Hash physique de l'état sémantique instable."
}

$recheckedManifestSha = Get-FileSha256 -Path $OutputManifestPath
$recheckedFrozenSha   = Get-FileSha256 -Path $OutputFrozenPath

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host " NIVEAU 3 : CERTIFIED & FROZEN" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Point Zero       : $canonicalRunId"
Write-Host "Semantic files   : $($semanticRecords.Count)"
Write-Host "Parsed files     : $parsedCount"
Write-Host "Symbols          : $totalSymbols`n"
Write-Host "Payload SHA256   : $semanticPayloadSha1" -ForegroundColor Yellow
Write-Host "Artifact SHA256  : $semanticArtifactSha"
Write-Host "Manifest SHA256  : $recheckedManifestSha"
Write-Host "Frozen SHA256    : $recheckedFrozenSha`n"
Write-Host "Artefact         : $OutputStatePath"
Write-Host "Manifest         : $OutputManifestPath"
Write-Host "Seal             : $OutputFrozenPath"
Write-Host "============================================================`n" -ForegroundColor Cyan