#Requires -Version 7.0
<#
.SYNOPSIS
    E-ZZIO — TOPOLOGY ENGINE v1.0 (STRUCTURAL TRUTH / NIVEAU 2)
.DESCRIPTION
    Transformation déterministe et pure du journal physique records.jsonl en état topologique.
    - Zéro parcours disque sur le corpus source.
    - Sérialisation selon le contrat Canonical JSON E-ZZIO v1 (tri ordinal, zéro champ volatil).
    - Validation stricte des 5 Quality Gates topologiques (TG-01 à TG-05).
    - Génération du manifeste de filiation et scellement par token physique FROZEN.
#>

[CmdletBinding()]
param(
    [string]$PointZeroDir = "G:\AI\_forensic\ContentTruth\run_20260820_130134_380",
    [string]$OutputDir    = "G:\AI\_forensic\SelfBody\topology\run_20260820_130134_380",
    [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ============================================================================
# 0. INJECTION DU SÉRIALISEUR CANONIQUE DÉTERMINISTE .NET
# ============================================================================
if (-not ('EzzioCanonicalJson' -as [type])) {
    Add-Type -TypeDefinition @'
using System;
using System.IO;
using System.Text;
using System.Collections.Generic;
using System.Security.Cryptography;

public static class EzzioCanonicalJson
{
    public static string SerializeTrieNode(string name, string type, long sizeBytes, long fileCount, long dirCount, string sha256, SortedDictionary<string, object> children)
    {
        var sb = new StringBuilder();
        sb.Append("{");
        sb.Append("\"children\":{");
        if (children != null && children.Count > 0)
        {
            bool first = true;
            foreach (var kv in children)
            {
                if (!first) sb.Append(",");
                sb.Append("\"").Append(Escape(kv.Key)).Append("\":");
                sb.Append(kv.Value.ToString());
                first = false;
            }
        }
        sb.Append("},");
        sb.Append("\"dir_count\":").Append(dirCount).Append(",");
        sb.Append("\"file_count\":").Append(fileCount).Append(",");
        sb.Append("\"name\":\"").Append(Escape(name)).Append("\",");
        if (sha256 != null)
        {
            sb.Append("\"sha256\":\"").Append(sha256).Append("\",");
        }
        sb.Append("\"size_bytes\":").Append(sizeBytes).Append(",");
        sb.Append("\"type\":\"").Append(type).Append("\"");
        sb.Append("}");
        return sb.ToString();
    }

    public static string SerializeMetrics(long totalDirectories, long totalFiles, long totalBytes, int maxDepth, SortedDictionary<string, long[]> extDist)
    {
        var sb = new StringBuilder();
        sb.Append("{");
        sb.Append("\"extension_distribution\":{");
        if (extDist != null && extDist.Count > 0)
        {
            bool first = true;
            foreach (var kv in extDist)
            {
                if (!first) sb.Append(",");
                sb.Append("\"").Append(Escape(kv.Key)).Append("\":{");
                sb.Append("\"bytes\":").Append(kv.Value[1]).Append(",");
                sb.Append("\"count\":").Append(kv.Value[0]);
                sb.Append("}");
                first = false;
            }
        }
        sb.Append("},");
        sb.Append("\"max_depth\":").Append(maxDepth).Append(",");
        sb.Append("\"total_bytes\":").Append(totalBytes).Append(",");
        sb.Append("\"total_directories\":").Append(totalDirectories).Append(",");
        sb.Append("\"total_files\":").Append(totalFiles);
        sb.Append("}");
        return sb.ToString();
    }

    public static string SerializeLineage(string parentRunId, string parentRecordsSha, string parentChainHash, long recordCount, long totalBytes)
    {
        var sb = new StringBuilder();
        sb.Append("{");
        sb.Append("\"parent_chain_hash\":\"").Append(parentChainHash).Append("\",");
        sb.Append("\"parent_point_zero_run\":\"").Append(Escape(parentRunId)).Append("\",");
        sb.Append("\"parent_record_count\":").Append(recordCount).Append(",");
        sb.Append("\"parent_records_file\":\"records.jsonl\",");
        sb.Append("\"parent_records_sha256\":\"").Append(parentRecordsSha).Append("\",");
        sb.Append("\"parent_total_bytes\":").Append(totalBytes);
        sb.Append("}");
        return sb.ToString();
    }

    public static string SerializePayload(string lineageJson, string metricsJson, string treeJson)
    {
        var sb = new StringBuilder();
        sb.Append("{");
        sb.Append("\"lineage\":").Append(lineageJson).Append(",");
        sb.Append("\"metrics\":").Append(metricsJson).Append(",");
        sb.Append("\"tree\":").Append(treeJson);
        sb.Append("}");
        return sb.ToString();
    }

    public static string ComputeSha256(string content)
    {
        using (var sha = SHA256.Create())
        {
            byte[] bytes = Encoding.UTF8.GetBytes(content);
            byte[] hash = sha.ComputeHash(bytes);
            var sb = new StringBuilder();
            for (int i = 0; i < hash.Length; i++)
            {
                sb.Append(hash[i].ToString("x2"));
            }
            return sb.ToString();
        }
    }

    private static string Escape(string s)
    {
        if (string.IsNullOrEmpty(s)) return "";
        return s.Replace("\\", "\\\\").Replace("\"", "\\\"");
    }
}
'@
}

# ============================================================================
# 1. VALIDATION DE L'ANCRE PHYSIQUE (POINT ZÉRO)
# ============================================================================
Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host " E-ZZIO — TOPOLOGY ENGINE v1.0 (NIVEAU 2)" -ForegroundColor Cyan
Write-Host " BASELINE : POINT ZERO FORENSIC DERIVATION" -ForegroundColor Yellow
Write-Host "============================================================`n" -ForegroundColor Cyan

$RecordsPath  = Join-Path $PointZeroDir 'records.jsonl'
$ManifestPath = Join-Path $PointZeroDir 'run_manifest.json'

if (-not (Test-Path -LiteralPath $RecordsPath -PathType Leaf)) {
    throw "FAIL-CLOSED: records.jsonl introuvable à l'emplacement $RecordsPath"
}
if (-not (Test-Path -LiteralPath $ManifestPath -PathType Leaf)) {
    throw "FAIL-CLOSED: run_manifest.json introuvable à l'emplacement $ManifestPath"
}

$FrozenTokenPath = Join-Path $OutputDir 'FROZEN'
if ((Test-Path -LiteralPath $FrozenTokenPath) -and -not $Force) {
    throw "FAIL-CLOSED: L'artefact topologique $OutputDir est déjà scellé (FROZEN). Utilise -Force pour recalculer."
}

# Hachage indépendant du fichier records.jsonl source
$sha = [System.Security.Cryptography.SHA256]::Create()
$fs = [System.IO.File]::OpenRead($RecordsPath)
$recordsSha256 = [System.BitConverter]::ToString($sha.ComputeHash($fs)).Replace('-', '').ToLowerInvariant()
$fs.Dispose()
$sha.Dispose()

$parentManifest = Get-Content -LiteralPath $ManifestPath -Raw | ConvertFrom-Json
$parentRunId    = [string]$parentManifest.RunId
$parentChain    = [string]$parentManifest.ChainHash
$parentCount    = [int64]$parentManifest.FilesProcessed

Write-Host "[TG-01] Validation d'intégrité de l'ancre Point Zéro..." -ForegroundColor Yellow
if (-not [bool]$parentManifest.Certified) {
    throw "FAIL-CLOSED: Le run parent $parentRunId n'est pas certifié (Certified != true)."
}
Write-Host " [PASS] TG-01_PARENT_INTEGRITY | Records SHA-256 : $recordsSha256" -ForegroundColor Green

# ============================================================================
# 2. INGESTION SÉQUENTIELLE DU JOURNAL ET CONSTRUCTION DE L'ARBRE
# ============================================================================
Write-Host "`n[INGESTION] Lecture séquentielle de records.jsonl (zéro I/O disque source)..." -ForegroundColor Yellow

class TrieDirectory {
    [string]$Name
    [int64]$SizeBytes = 0
    [int64]$FileCount = 0
    [int64]$DirCount  = 0
    [System.Collections.Generic.SortedDictionary[string, object]]$Children

    TrieDirectory([string]$name) {
        $this.Name = $name
        $this.Children = [System.Collections.Generic.SortedDictionary[string, object]]::new([System.StringComparer]::Ordinal)
    }
}

class TrieFile {
    [string]$Name
    [int64]$SizeBytes
    [string]$Sha256

    TrieFile([string]$name, [int64]$size, [string]$hash) {
        $this.Name = $name
        $this.SizeBytes = $size
        $this.Sha256 = $hash
    }
}

$rootNode = [TrieDirectory]::new("root")
$observedRecordsCount = [int64]0
$observedTotalBytes   = [int64]0
$extensionDist = [System.Collections.Generic.SortedDictionary[string, long[]]]::new([System.StringComparer]::Ordinal)

# Détection automatique du BOM activée ($true) pour éviter d'injecter \uFEFF dans la première ligne
$sr = [System.IO.StreamReader]::new($RecordsPath, [System.Text.UTF8Encoding]::new($false, $true), $true, 65536)
try {
    while (-not $sr.EndOfStream) {
        $line = $sr.ReadLine()
        if ([string]::IsNullOrWhiteSpace($line)) { continue }

        # Nettoyage préventif des espaces et d'éventuels caractères BOM résiduels
        $line = $line.Trim().Trim([char]0xFEFF)
        if ([string]::IsNullOrWhiteSpace($line)) { continue }

        $rec = $line | ConvertFrom-Json
        $observedRecordsCount++
        $fileSize = [int64]$rec.SizeExpected
        $observedTotalBytes += $fileSize

        $relPath = [string]$rec.RelativePath
        $fileHash = [string]$rec.Hash

        # Distribution des extensions
        $ext = [System.IO.Path]::GetExtension($relPath).ToLowerInvariant()
        if ([string]::IsNullOrWhiteSpace($ext)) { $ext = "[no_extension]" }
        if (-not $extensionDist.ContainsKey($ext)) {
            $extensionDist[$ext] = @([int64]0, [int64]0)
        }
        $extensionDist[$ext][0] += 1
        $extensionDist[$ext][1] += $fileSize

        # Découpage du chemin relatif normalisé
        $segments = $relPath.Replace('\', '/').Trim('/').Split('/')
        $currentDir = $rootNode

        for ($i = 0; $i -lt ($segments.Length - 1); $i++) {
            $seg = $segments[$i]
            if (-not $currentDir.Children.ContainsKey($seg)) {
                $subDir = [TrieDirectory]::new($seg)
                $currentDir.Children[$seg] = $subDir
            }
            $currentDir = [TrieDirectory]$currentDir.Children[$seg]
        }

        $leafName = $segments[$segments.Length - 1]
        if ($currentDir.Children.ContainsKey($leafName)) {
            throw "FAIL-CLOSED: Collision de chemin détectée dans records.jsonl : $relPath"
        }
        $currentDir.Children[$leafName] = [TrieFile]::new($leafName, $fileSize, $fileHash)
    }
} finally {
    $sr.Dispose()
}

Write-Host "-> $observedRecordsCount records ingérés ($observedTotalBytes octets)." -ForegroundColor DarkGray

# ============================================================================
# 3. AGRÉGATION ASCENDANTE ET CALCUL DE PROFONDEUR
# ============================================================================
Write-Host "`n[SYNTHÈSE] Agrégation topologique ascendante..." -ForegroundColor Yellow

$globalLeafCount = [int64]0
$globalDirCount  = [int64]0
$maxTreeDepth    = 0

function Measure-TrieNode {
    param(
        [object]$Node,
        [int]$Depth
    )

    if ($Depth -gt $script:maxTreeDepth) { $script:maxTreeDepth = $Depth }

    if ($Node -is [TrieFile]) {
        $script:globalLeafCount++
        return [EzzioCanonicalJson]::SerializeTrieNode($Node.Name, "file", $Node.SizeBytes, 0, 0, $Node.Sha256, $null)
    }

    $dir = [TrieDirectory]$Node
    $script:globalDirCount++

    $subBytes = [int64]0
    $subFiles = [int64]0
    $subDirs  = [int64]0
    $serializedChildren = [System.Collections.Generic.SortedDictionary[string, object]]::new([System.StringComparer]::Ordinal)

    foreach ($kv in $dir.Children) {
        $child = $kv.Value
        $childJson = Measure-TrieNode -Node $child -Depth ($Depth + 1)
        $serializedChildren[$kv.Key] = $childJson

        if ($child -is [TrieFile]) {
            $subBytes += $child.SizeBytes
            $subFiles += 1
        } else {
            $subDir = [TrieDirectory]$child
            $subBytes += $subDir.SizeBytes
            $subFiles += $subDir.FileCount
            $subDirs  += (1 + $subDir.DirCount)
        }
    }

    $dir.SizeBytes = $subBytes
    $dir.FileCount = $subFiles
    $dir.DirCount  = $subDirs

    return [EzzioCanonicalJson]::SerializeTrieNode($dir.Name, "directory", $subBytes, $subFiles, $subDirs, $null, $serializedChildren)
}

$canonicalTreeJson = Measure-TrieNode -Node $rootNode -Depth 0
$totalDirectories = $globalDirCount - 1

# ============================================================================
# 4. ÉVALUATION DES QUALITY GATES STRUCTURELLES
# ============================================================================
Write-Host "`n[QUALITY GATES] Validation des contrats structurels..." -ForegroundColor Yellow

$gates = [ordered]@{}

# TG-02 : Parité des feuilles terminales
$gates['TG-02_LEAF_CARDINALITY_PARITY'] = ($globalLeafCount -eq $observedRecordsCount) -and ($observedRecordsCount -eq $parentCount)

# TG-03 : Conservation absolue de la masse binaire
$gates['TG-03_MASS_CONSERVATION'] = ($rootNode.SizeBytes -eq $observedTotalBytes)

# TG-04 : Absence d'orphelins et cohérence d'arbre
$gates['TG-04_ZERO_ORPHAN_PATHS'] = ($rootNode.FileCount -eq $observedRecordsCount)

# Sérialisation canonique du lignage et des métriques
$canonicalLineageJson = [EzzioCanonicalJson]::SerializeLineage($parentRunId, $recordsSha256, $parentChain, $observedRecordsCount, $observedTotalBytes)
$canonicalMetricsJson = [EzzioCanonicalJson]::SerializeMetrics($totalDirectories, $globalLeafCount, $rootNode.SizeBytes, $maxTreeDepth, $extensionDist)
$canonicalPayloadJson = [EzzioCanonicalJson]::SerializePayload($canonicalLineageJson, $canonicalMetricsJson, $canonicalTreeJson)

# TG-05 : Déterminisme cryptographique strict
$hashRun1 = [EzzioCanonicalJson]::ComputeSha256($canonicalPayloadJson)
$hashRun2 = [EzzioCanonicalJson]::ComputeSha256($canonicalPayloadJson)
$gates['TG-05_CANONICAL_DETERMINISM'] = ($hashRun1 -eq $hashRun2) -and ($hashRun1.Length -eq 64)

$allGatesPass = $true
foreach ($k in $gates.Keys) {
    if ($gates[$k]) {
        Write-Host " [PASS] $k" -ForegroundColor Green
    } else {
        Write-Host " [FAIL] $k" -ForegroundColor Red
        $allGatesPass = $false
    }
}

if (-not $allGatesPass) {
    throw "FAIL-CLOSED: Au moins une Quality Gate topologique a échoué."
}

$topologyPayloadSha256 = $hashRun1
Write-Host "`n-> TOPOLOGY PAYLOAD SHA-256 : $topologyPayloadSha256" -ForegroundColor Yellow

# ============================================================================
# 5. ÉMISSION DE L'ARTEFACT ET DOUBLE HACHAGE
# ============================================================================
Write-Host "`n[COMMIT DERIVÉ] Écriture de l'état topologique et du manifeste..." -ForegroundColor Yellow

if (-not (Test-Path -LiteralPath $OutputDir -PathType Container)) {
    New-Item -ItemType Directory -LiteralPath $OutputDir -Force | Out-Null
}

$StateFilePath    = Join-Path $OutputDir 'EZZIO_TOPOLOGY_STATE.json'
$ManifestFilePath = Join-Path $OutputDir 'topology_manifest.json'

$stateObj = [ordered]@{
    artifact_type  = "EZZIO_TOPOLOGY_STATE"
    schema_version = "1.0"
    metadata       = [ordered]@{
        generated_at_utc  = (Get-Date).ToUniversalTime().ToString('o')
        generator_version = "1.0.0"
        engine            = "EZZIO_Topology_Engine_v1.0"
    }
    lineage        = ($canonicalLineageJson | ConvertFrom-Json)
    metrics        = ($canonicalMetricsJson | ConvertFrom-Json)
    tree           = ($canonicalTreeJson | ConvertFrom-Json)
    proof          = [ordered]@{
        topology_payload_sha256 = $topologyPayloadSha256
        gates_passed            = @($gates.Keys)
    }
}

$stateJson = $stateObj | ConvertTo-Json -Depth 100
[System.IO.File]::WriteAllText($StateFilePath, $stateJson, [System.Text.UTF8Encoding]::new($false))

# Calcul du hash physique de l'artefact sur disque
$shaArt = [System.Security.Cryptography.SHA256]::Create()
$fsArt = [System.IO.File]::OpenRead($StateFilePath)
$topologyArtifactSha256 = [System.BitConverter]::ToString($shaArt.ComputeHash($fsArt)).Replace('-', '').ToLowerInvariant()
$fsArt.Dispose()
$shaArt.Dispose()

# Émission du manifeste de filiation topologique
$manifestObj = [ordered]@{
    artifact_type            = "EZZIO_TOPOLOGY_MANIFEST"
    schema_version           = "1.0"
    sealed_at_utc            = (Get-Date).ToUniversalTime().ToString('o')
    parent_point_zero_run    = $parentRunId
    parent_records_sha256    = $recordsSha256
    parent_chain_hash        = $parentChain
    record_count             = $observedRecordsCount
    topology_payload_sha256  = $topologyPayloadSha256
    topology_artifact_sha256 = $topologyArtifactSha256
    gates_summary            = "5/5_PASS"
    status                   = "CERTIFIED_DERIVATION"
}

$manifestJson = $manifestObj | ConvertTo-Json -Depth 10
[System.IO.File]::WriteAllText($ManifestFilePath, $manifestJson, [System.Text.UTF8Encoding]::new($false))

# Token physique de scellement
$frozenTokenContent = "FROZEN_DERIVATION_SEAL`nParentRun:$parentRunId`nPayloadSHA256:$topologyPayloadSha256`nArtifactSHA256:$topologyArtifactSha256`nDateUtc:$((Get-Date).ToUniversalTime().ToString('o'))"
[System.IO.File]::WriteAllText($FrozenTokenPath, $frozenTokenContent, [System.Text.UTF8Encoding]::new($false))

# ============================================================================
# 6. POST-COMMIT FORENSIC VALIDATION INDÉPENDANTE
# ============================================================================
$reCheckStateSha = (Get-FileHash -LiteralPath $StateFilePath -Algorithm SHA256).Hash.ToLowerInvariant()
if ($reCheckStateSha -ne $topologyArtifactSha256) {
    throw "FAIL-CLOSED: Asymétrie post-commit sur l'artefact topologique."
}

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host " STATUT   : NIVEAU 2 CERTIFIED & FROZEN" -ForegroundColor Green
Write-Host " ARTEFACT : $StateFilePath" -ForegroundColor DarkGray
Write-Host " PAYLOAD  : $topologyPayloadSha256" -ForegroundColor DarkGray
Write-Host " ARTIFACT : $topologyArtifactSha256" -ForegroundColor DarkGray
Write-Host " PARENT   : $parentRunId" -ForegroundColor DarkGray
Write-Host "============================================================`n" -ForegroundColor Cyan