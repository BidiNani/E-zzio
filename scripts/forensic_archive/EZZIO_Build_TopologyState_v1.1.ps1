#Requires -Version 7.0
<#
.SYNOPSIS
    E-ZZIO — TOPOLOGY ENGINE v1.1
    NIVEAU 2 — STRUCTURAL TRUTH

.DESCRIPTION
    Transforme exclusivement le records.jsonl du Point Zéro
    en représentation topologique déterministe.

    CONTRAT :
      - Aucun parcours du corpus E-ZZIO.
      - Aucune lecture de fichier du corpus source.
      - Entrée : records.jsonl + run_manifest.json du Point Zéro.
      - Sortie : artefact dérivé hors Point Zéro.
      - Aucun écrasement d'une dérivation FROZEN.
      - FAIL-CLOSED.
      - Provenance cryptographique obligatoire.

.NOTES
    Point Zero :
      run_20260820_130134_380

    Le statut FROZEN est un verrou logique/forensic du moteur.
    Il ne prétend pas constituer une protection OS absolue.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [string]$PointZeroDir =
        "G:\AI\_forensic\ContentTruth\run_20260820_130134_380",

    [Parameter(Mandatory = $false)]
    [string]$OutputDir =
        "G:\AI\_forensic\SelfBody\topology\run_20260820_130134_380"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ============================================================================
# 0. CONSTANTES DU CONTRAT
# ============================================================================

$EngineVersion = "1.1.0"
$SchemaVersion = "1.0"

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " E-ZZIO — TOPOLOGY ENGINE v$EngineVersion" -ForegroundColor Cyan
Write-Host " NIVEAU 2 — STRUCTURAL TRUTH" -ForegroundColor Cyan
Write-Host " BASELINE : POINT ZERO FORENSIC DERIVATION" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# ============================================================================
# 1. UTILITAIRES CRYPTOGRAPHIQUES
# ============================================================================

function Get-FileSha256 {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    if (-not [System.IO.File]::Exists($Path)) {
        throw "FAIL-CLOSED: Fichier absent : $Path"
    }

    $sha = [System.Security.Cryptography.SHA256]::Create()

    try {
        $stream = [System.IO.File]::Open(
            $Path,
            [System.IO.FileMode]::Open,
            [System.IO.FileAccess]::Read,
            [System.IO.FileShare]::Read
        )

        try {
            $hash = $sha.ComputeHash($stream)
        }
        finally {
            $stream.Dispose()
        }
    }
    finally {
        $sha.Dispose()
    }

    return [System.BitConverter]::ToString(
        $hash
    ).Replace('-', '').ToLowerInvariant()
}

function Get-StringSha256 {
    param(
        [Parameter(Mandatory)]
        [string]$Content
    )

    $bytes = [System.Text.Encoding]::UTF8.GetBytes($Content)

    $sha = [System.Security.Cryptography.SHA256]::Create()

    try {
        $hash = $sha.ComputeHash($bytes)
    }
    finally {
        $sha.Dispose()
    }

    return [System.BitConverter]::ToString(
        $hash
    ).Replace('-', '').ToLowerInvariant()
}

# ============================================================================
# 2. CANONICAL JSON .NET
# ============================================================================

if (-not ('EzzioCanonicalJson' -as [type])) {

Add-Type -TypeDefinition @'
using System;
using System.Text;
using System.Collections.Generic;
using System.Security.Cryptography;

public static class EzzioCanonicalJson
{
    public static string Escape(string value)
    {
        if (value == null)
            return "";

        return value
            .Replace("\\", "\\\\")
            .Replace("\"", "\\\"");
    }

    public static string SerializeTrieNode(
        string name,
        string type,
        long sizeBytes,
        long fileCount,
        long dirCount,
        string sha256,
        SortedDictionary<string, object> children)
    {
        var sb = new StringBuilder();

        sb.Append("{");
        sb.Append("\"children\":{");

        bool first = true;

        if (children != null)
        {
            foreach (var kv in children)
            {
                if (!first)
                    sb.Append(",");

                sb.Append("\"")
                  .Append(Escape(kv.Key))
                  .Append("\":")
                  .Append((string)kv.Value);

                first = false;
            }
        }

        sb.Append("},");
        sb.Append("\"dir_count\":").Append(dirCount).Append(",");
        sb.Append("\"file_count\":").Append(fileCount).Append(",");
        sb.Append("\"name\":\"").Append(Escape(name)).Append("\",");

        if (sha256 != null)
        {
            sb.Append("\"sha256\":\"")
              .Append(Escape(sha256))
              .Append("\",");
        }

        sb.Append("\"size_bytes\":").Append(sizeBytes).Append(",");
        sb.Append("\"type\":\"").Append(Escape(type)).Append("\"");
        sb.Append("}");

        return sb.ToString();
    }

    public static string SerializeMetrics(
        long totalDirectories,
        long totalFiles,
        long totalBytes,
        int maxDepth,
        SortedDictionary<string, long[]> extensionDistribution)
    {
        var sb = new StringBuilder();

        sb.Append("{");
        sb.Append("\"extension_distribution\":{");

        bool first = true;

        foreach (var kv in extensionDistribution)
        {
            if (!first)
                sb.Append(",");

            sb.Append("\"")
              .Append(Escape(kv.Key))
              .Append("\":{");

            sb.Append("\"bytes\":")
              .Append(kv.Value[1])
              .Append(",");

            sb.Append("\"count\":")
              .Append(kv.Value[0]);

            sb.Append("}");

            first = false;
        }

        sb.Append("},");
        sb.Append("\"max_depth\":").Append(maxDepth).Append(",");
        sb.Append("\"total_bytes\":").Append(totalBytes).Append(",");
        sb.Append("\"total_directories\":").Append(totalDirectories).Append(",");
        sb.Append("\"total_files\":").Append(totalFiles);
        sb.Append("}");

        return sb.ToString();
    }

    public static string SerializeLineage(
        string parentRunId,
        string parentRecordsSha,
        string parentChainHash,
        long recordCount,
        long totalBytes)
    {
        var sb = new StringBuilder();

        sb.Append("{");

        sb.Append("\"parent_chain_hash\":\"")
          .Append(Escape(parentChainHash))
          .Append("\",");

        sb.Append("\"parent_point_zero_run\":\"")
          .Append(Escape(parentRunId))
          .Append("\",");

        sb.Append("\"parent_record_count\":")
          .Append(recordCount)
          .Append(",");

        sb.Append("\"parent_records_file\":\"records.jsonl\",");

        sb.Append("\"parent_records_sha256\":\"")
          .Append(Escape(parentRecordsSha))
          .Append("\",");

        sb.Append("\"parent_total_bytes\":")
          .Append(totalBytes);

        sb.Append("}");

        return sb.ToString();
    }

    public static string SerializePayload(
        string lineageJson,
        string metricsJson,
        string treeJson)
    {
        return
            "{\"lineage\":" +
            lineageJson +
            ",\"metrics\":" +
            metricsJson +
            ",\"tree\":" +
            treeJson +
            "}";
    }

    public static string ComputeSha256(string content)
    {
        using (var sha = SHA256.Create())
        {
            byte[] bytes = Encoding.UTF8.GetBytes(content);
            byte[] hash = sha.ComputeHash(bytes);

            var sb = new StringBuilder();

            foreach (byte b in hash)
                sb.Append(b.ToString("x2"));

            return sb.ToString();
        }
    }
}
'@
}

# ============================================================================
# 3. CLASSES DU TRIE
# ============================================================================

class TrieDirectory {

    [string]$Name
    [int64]$SizeBytes
    [int64]$FileCount
    [int64]$DirCount

    [System.Collections.Generic.SortedDictionary[string, object]]$Children

    TrieDirectory([string]$name) {

        $this.Name = $name
        $this.SizeBytes = 0
        $this.FileCount = 0
        $this.DirCount = 0

        $this.Children =
            [System.Collections.Generic.SortedDictionary[string, object]]::new(
                [System.StringComparer]::Ordinal
            )
    }
}

class TrieFile {

    [string]$Name
    [int64]$SizeBytes
    [string]$Sha256

    TrieFile(
        [string]$name,
        [int64]$size,
        [string]$hash
    ) {

        $this.Name = $name
        $this.SizeBytes = $size
        $this.Sha256 = $hash
    }
}

# ============================================================================
# 4. CHEMINS ET CONFINEMENT
# ============================================================================

$RecordsPath  = Join-Path $PointZeroDir 'records.jsonl'
$ManifestPath = Join-Path $PointZeroDir 'run_manifest.json'

$StateFilePath =
    Join-Path $OutputDir 'EZZIO_TOPOLOGY_STATE.json'

$TopologyManifestPath =
    Join-Path $OutputDir 'topology_manifest.json'

$FrozenTokenPath =
    Join-Path $OutputDir 'FROZEN'

# Vérification absolue que OutputDir n'est pas PointZeroDir
$resolvedPointZero =
    [System.IO.Path]::GetFullPath($PointZeroDir).TrimEnd('\')

$resolvedOutput =
    [System.IO.Path]::GetFullPath($OutputDir).TrimEnd('\')

if (
    [string]::Equals(
        $resolvedPointZero,
        $resolvedOutput,
        [System.StringComparison]::OrdinalIgnoreCase
    )
) {
    throw "FAIL-CLOSED: OutputDir est identique au Point Zero."
}

# ============================================================================
# 5. REFUS D'ÉCRASER UNE DÉRIVATION GELÉE
# ============================================================================

if ([System.IO.File]::Exists($FrozenTokenPath)) {
    throw @"
FAIL-CLOSED:
La dérivation topologique est déjà FROZEN.

Output :
$OutputDir

Aucun écrasement n'est autorisé.

Pour produire une nouvelle dérivation, utiliser un nouveau répertoire
de génération/version.
"@
}

# ============================================================================
# 6. VALIDATION DE L'ANCRE
# ============================================================================

if (-not [System.IO.File]::Exists($RecordsPath)) {
    throw "FAIL-CLOSED: records.jsonl introuvable : $RecordsPath"
}

if (-not [System.IO.File]::Exists($ManifestPath)) {
    throw "FAIL-CLOSED: run_manifest.json introuvable : $ManifestPath"
}

Write-Host "[TG-01] Validation de l'intégrité du Point Zéro..." -ForegroundColor Yellow

$recordsSha256 = Get-FileSha256 -Path $RecordsPath

$manifestText =
    [System.IO.File]::ReadAllText(
        $ManifestPath,
        [System.Text.Encoding]::UTF8
    )

$parentManifest = $manifestText | ConvertFrom-Json

$parentRunId =
    [string]$parentManifest.RunId

$parentChain =
    [string]$parentManifest.ChainHash

$parentCertified =
    [bool]$parentManifest.Certified

$parentCount =
    [int64]$parentManifest.FilesProcessed

if ([string]::IsNullOrWhiteSpace($parentRunId)) {
    throw "FAIL-CLOSED: RunId parent absent."
}

if ([string]::IsNullOrWhiteSpace($parentChain)) {
    throw "FAIL-CLOSED: ChainHash parent absent."
}

if (-not $parentCertified) {
    throw "FAIL-CLOSED: Point Zero non certifié."
}

if ($parentCount -le 0) {
    throw "FAIL-CLOSED: FilesProcessed parent invalide."
}

Write-Host " [PASS] TG-01_PARENT_INTEGRITY" -ForegroundColor Green
Write-Host "        RunId      : $parentRunId"
Write-Host "        Records SHA: $recordsSha256"
Write-Host "        Chain Hash : $parentChain"
Write-Host "        Files      : $parentCount"

# ============================================================================
# 7. INGESTION STRICTEMENT SÉQUENTIELLE
# ============================================================================

Write-Host ""
Write-Host "[INGESTION] Lecture séquentielle de records.jsonl..." -ForegroundColor Yellow
Write-Host "            Aucun parcours du corpus E-ZZIO." -ForegroundColor DarkGray

$rootNode =
    [TrieDirectory]::new("root")

[int64]$observedRecordsCount = 0
[int64]$observedTotalBytes = 0

$extensionDist =
    [System.Collections.Generic.SortedDictionary[string, long[]]]::new(
        [System.StringComparer]::Ordinal
    )

$utf8Strict =
    [System.Text.UTF8Encoding]::new(
        $false,
        $true
    )

$reader =
    [System.IO.StreamReader]::new(
        $RecordsPath,
        $utf8Strict,
        $true,
        65536
    )

try {

    while (-not $reader.EndOfStream) {

        $line = $reader.ReadLine()

        if ([string]::IsNullOrWhiteSpace($line)) {
            continue
        }

        $line =
            $line.Trim().Trim([char]0xFEFF)

        if ([string]::IsNullOrWhiteSpace($line)) {
            continue
        }

        try {
            $rec = $line | ConvertFrom-Json
        }
        catch {
            throw "FAIL-CLOSED: JSONL invalide au record $($observedRecordsCount + 1)."
        }

        $observedRecordsCount++

        if (-not $rec.PSObject.Properties['SizeExpected']) {
            throw "FAIL-CLOSED: SizeExpected absent au record $observedRecordsCount."
        }

        if (-not $rec.PSObject.Properties['RelativePath']) {
            throw "FAIL-CLOSED: RelativePath absent au record $observedRecordsCount."
        }

        if (-not $rec.PSObject.Properties['Hash']) {
            throw "FAIL-CLOSED: Hash absent au record $observedRecordsCount."
        }

        [int64]$fileSize =
            $rec.SizeExpected

        [string]$relPath =
            $rec.RelativePath

        [string]$fileHash =
            $rec.Hash

        if ($fileSize -lt 0) {
            throw "FAIL-CLOSED: taille négative au record $observedRecordsCount."
        }

        if ([string]::IsNullOrWhiteSpace($relPath)) {
            throw "FAIL-CLOSED: RelativePath vide au record $observedRecordsCount."
        }

        if ([string]::IsNullOrWhiteSpace($fileHash)) {
            throw "FAIL-CLOSED: Hash vide au record $observedRecordsCount."
        }

        $observedTotalBytes += $fileSize

        # ------------------------------------------------------------
        # Extension
        # ------------------------------------------------------------

        $ext =
            [System.IO.Path]::GetExtension($relPath)

        if ([string]::IsNullOrWhiteSpace($ext)) {
            $ext = "[no_extension]"
        }
        else {
            $ext = $ext.ToLowerInvariant()
        }

        if (-not $extensionDist.ContainsKey($ext)) {

            $extensionDist[$ext] =
                @(
                    [int64]0,
                    [int64]0
                )
        }

        $extensionDist[$ext][0]++
        $extensionDist[$ext][1] += $fileSize

        # ------------------------------------------------------------
        # Chemin
        # ------------------------------------------------------------

        $normalizedPath =
            $relPath.Replace('\', '/').Trim('/')

        if ([string]::IsNullOrWhiteSpace($normalizedPath)) {
            throw "FAIL-CLOSED: chemin normalisé vide."
        }

        $segments =
            $normalizedPath.Split(
                '/',
                [System.StringSplitOptions]::RemoveEmptyEntries
            )

        if ($segments.Length -eq 0) {
            throw "FAIL-CLOSED: aucun segment de chemin."
        }

        $currentDir = $rootNode

        # Répertoires parents
        for (
            $i = 0;
            $i -lt ($segments.Length - 1);
            $i++
        ) {

            $seg = $segments[$i]

            if ($currentDir.Children.ContainsKey($seg)) {

                $existing =
                    $currentDir.Children[$seg]

                if ($existing -is [TrieFile]) {
                    throw @"
FAIL-CLOSED:
Collision structurelle fichier/répertoire.

Chemin :
$relPath

Segment :
$seg
"@
                }

                $currentDir =
                    [TrieDirectory]$existing
            }
            else {

                $subDir =
                    [TrieDirectory]::new($seg)

                $currentDir.Children.Add(
                    $seg,
                    $subDir
                )

                $currentDir = $subDir
            }
        }

        # Feuille
        $leafName =
            $segments[$segments.Length - 1]

        if ($currentDir.Children.ContainsKey($leafName)) {
            throw "FAIL-CLOSED: Collision de chemin : $relPath"
        }

        $currentDir.Children.Add(
            $leafName,
            [TrieFile]::new(
                $leafName,
                $fileSize,
                $fileHash
            )
        )
    }
}
finally {
    $reader.Dispose()
}

Write-Host "-> $observedRecordsCount records ingérés." -ForegroundColor Green
Write-Host "-> $observedTotalBytes octets observés." -ForegroundColor Green

# ============================================================================
# 8. PARITÉ IMMÉDIATE AVEC LE POINT ZERO
# ============================================================================

if ($observedRecordsCount -ne $parentCount) {

    throw @"
FAIL-CLOSED: Parité Point Zero impossible.

Manifest parent : $parentCount
Records observés: $observedRecordsCount
"@
}

# ============================================================================
# 9. AGRÉGATION
# ============================================================================

Write-Host ""
Write-Host "[SYNTHÈSE] Agrégation topologique ascendante..." -ForegroundColor Yellow

[int64]$globalLeafCount = 0
[int64]$globalDirCount = 0
[int]$maxTreeDepth = 0

function Measure-TrieNode {

    param(
        [Parameter(Mandatory)]
        [object]$Node,

        [Parameter(Mandatory)]
        [int]$Depth
    )

    if ($Depth -gt $script:maxTreeDepth) {
        $script:maxTreeDepth = $Depth
    }

    # ------------------------------------------------------------
    # Feuille
    # ------------------------------------------------------------

    if ($Node -is [TrieFile]) {

        $script:globalLeafCount++

        return [EzzioCanonicalJson]::SerializeTrieNode(
            $Node.Name,
            "file",
            $Node.SizeBytes,
            1,
            0,
            $Node.Sha256,
            $null
        )
    }

    # ------------------------------------------------------------
    # Répertoire
    # ------------------------------------------------------------

    $dir =
        [TrieDirectory]$Node

    $script:globalDirCount++

    [int64]$subBytes = 0
    [int64]$subFiles = 0
    [int64]$subDirs = 0

    $serializedChildren =
        [System.Collections.Generic.SortedDictionary[string, object]]::new(
            [System.StringComparer]::Ordinal
        )

    # IMPORTANT :
    # Énumération .NET explicite.
    # Ne jamais utiliser :
    # foreach ($kv in $dir.Children)
    #
    # car PowerShell peut adapter l'énumération.
    foreach ($kv in $dir.Children.GetEnumerator()) {

        [string]$key = $kv.Key
        $child = $kv.Value

        if ($null -eq $child) {
            throw "FAIL-CLOSED: Enfant null dans le trie : $key"
        }

        $childJson =
            Measure-TrieNode `
                -Node $child `
                -Depth ($Depth + 1)

        if ([string]::IsNullOrWhiteSpace($childJson)) {
            throw "FAIL-CLOSED: Sérialisation vide pour : $key"
        }

        $serializedChildren.Add(
            $key,
            $childJson
        )

        if ($child -is [TrieFile]) {

            $subBytes += $child.SizeBytes
            $subFiles++

        }
        elseif ($child -is [TrieDirectory]) {

            $subDir =
                [TrieDirectory]$child

            $subBytes += $subDir.SizeBytes
            $subFiles += $subDir.FileCount
            $subDirs +=
                1 + $subDir.DirCount
        }
        else {

            throw "FAIL-CLOSED: Type de nœud inconnu."
        }
    }

    $dir.SizeBytes = $subBytes
    $dir.FileCount = $subFiles
    $dir.DirCount = $subDirs

    return [EzzioCanonicalJson]::SerializeTrieNode(
        $dir.Name,
        "directory",
        $subBytes,
        $subFiles,
        $subDirs,
        $null,
        $serializedChildren
    )
}

$canonicalTreeJson =
    Measure-TrieNode `
        -Node $rootNode `
        -Depth 0

$totalDirectories =
    $globalDirCount - 1

# ============================================================================
# 10. QUALITY GATES
# ============================================================================

Write-Host ""
Write-Host "[QUALITY GATES] Validation..." -ForegroundColor Yellow

$gates =
    [ordered]@{}

$gates['TG-01_PARENT_INTEGRITY'] =
    (
        $parentCertified -and
        ($parentCount -eq $observedRecordsCount) -and
        (-not [string]::IsNullOrWhiteSpace($parentChain))
    )

$gates['TG-02_LEAF_CARDINALITY_PARITY'] =
    (
        $globalLeafCount -eq
        $observedRecordsCount
    )

$gates['TG-03_MASS_CONSERVATION'] =
    (
        $rootNode.SizeBytes -eq
        $observedTotalBytes
    )

$gates['TG-04_ZERO_ORPHAN_PATHS'] =
    (
        $rootNode.FileCount -eq
        $observedRecordsCount
    )

# ============================================================================
# 11. CANONICAL PAYLOAD
# ============================================================================

$canonicalLineageJson =
    [EzzioCanonicalJson]::SerializeLineage(
        $parentRunId,
        $recordsSha256,
        $parentChain,
        $observedRecordsCount,
        $observedTotalBytes
    )

$canonicalMetricsJson =
    [EzzioCanonicalJson]::SerializeMetrics(
        $totalDirectories,
        $globalLeafCount,
        $rootNode.SizeBytes,
        $maxTreeDepth,
        $extensionDist
    )

$canonicalPayloadJson =
    [EzzioCanonicalJson]::SerializePayload(
        $canonicalLineageJson,
        $canonicalMetricsJson,
        $canonicalTreeJson
    )

$hashRun1 =
    [EzzioCanonicalJson]::ComputeSha256(
        $canonicalPayloadJson
    )

$hashRun2 =
    [EzzioCanonicalJson]::ComputeSha256(
        $canonicalPayloadJson
    )

$gates['TG-05_CANONICAL_DETERMINISM'] =
    (
        ($hashRun1 -eq $hashRun2) -and
        ($hashRun1 -match '^[0-9a-f]{64}$')
    )

# ============================================================================
# 12. AFFICHAGE DES GATES
# ============================================================================

$allGatesPass = $true

foreach ($gate in $gates.GetEnumerator()) {

    if ([bool]$gate.Value) {

        Write-Host `
            " [PASS] $($gate.Key)" `
            -ForegroundColor Green
    }
    else {

        Write-Host `
            " [FAIL] $($gate.Key)" `
            -ForegroundColor Red

        $allGatesPass = $false
    }
}

if (-not $allGatesPass) {
    throw "FAIL-CLOSED: Quality Gate topologique échouée."
}

$topologyPayloadSha256 =
    $hashRun1

Write-Host ""
Write-Host "-> TOPOLOGY PAYLOAD SHA-256 : $topologyPayloadSha256" `
    -ForegroundColor Yellow

# ============================================================================
# 13. PRÉ-COMMIT — SORTIE HORS POINT ZERO
# ============================================================================

Write-Host ""
Write-Host "[COMMIT DÉRIVÉ] Émission des artefacts..." -ForegroundColor Yellow

if (-not [System.IO.Directory]::Exists($OutputDir)) {

    [System.IO.Directory]::CreateDirectory(
        $OutputDir
    ) | Out-Null
}

# ============================================================================
# 14. ÉTAT TOPOLOGIQUE
# ============================================================================

$stateObj =
    [ordered]@{

        artifact_type =
            "EZZIO_TOPOLOGY_STATE"

        schema_version =
            $SchemaVersion

        metadata =
            [ordered]@{
                generated_at_utc =
                    [DateTime]::UtcNow.ToString('o')

                generator_version =
                    $EngineVersion

                engine =
                    "EZZIO_Topology_Engine"
            }

        lineage =
            ($canonicalLineageJson | ConvertFrom-Json)

        metrics =
            ($canonicalMetricsJson | ConvertFrom-Json)

        tree =
            ($canonicalTreeJson | ConvertFrom-Json)

        proof =
            [ordered]@{
                topology_payload_sha256 =
                    $topologyPayloadSha256

                gates_passed =
                    @(
                        $gates.GetEnumerator() |
                            Where-Object { $_.Value } |
                            ForEach-Object { $_.Key }
                    )
            }
    }

$stateJson =
    $stateObj |
        ConvertTo-Json -Depth 100

[System.IO.File]::WriteAllText(
    $StateFilePath,
    $stateJson,
    [System.Text.UTF8Encoding]::new($false)
)

# ============================================================================
# 15. HASH PHYSIQUE DE L'ARTEFACT
# ============================================================================

$topologyArtifactSha256 =
    Get-FileSha256 -Path $StateFilePath

# ============================================================================
# 16. MANIFESTE DE FILIATION
# ============================================================================

$manifestObj =
    [ordered]@{

        artifact_type =
            "EZZIO_TOPOLOGY_MANIFEST"

        schema_version =
            $SchemaVersion

        sealed_at_utc =
            [DateTime]::UtcNow.ToString('o')

        generator_version =
            $EngineVersion

        parent_point_zero_run =
            $parentRunId

        parent_records_sha256 =
            $recordsSha256

        parent_chain_hash =
            $parentChain

        record_count =
            $observedRecordsCount

        total_bytes =
            $observedTotalBytes

        topology_payload_sha256 =
            $topologyPayloadSha256

        topology_artifact_sha256 =
            $topologyArtifactSha256

        gates_summary =
            "5/5_PASS"

        status =
            "CERTIFIED_DERIVATION"
    }

$manifestJson =
    $manifestObj |
        ConvertTo-Json -Depth 20

[System.IO.File]::WriteAllText(
    $TopologyManifestPath,
    $manifestJson,
    [System.Text.UTF8Encoding]::new($false)
)

# ============================================================================
# 17. SCELLEMENT FROZEN
# ============================================================================

$frozenContent = @"
FROZEN_DERIVATION_SEAL
EngineVersion:$EngineVersion
SchemaVersion:$SchemaVersion
ParentRun:$parentRunId
ParentRecordsSHA256:$recordsSha256
ParentChainHash:$parentChain
PayloadSHA256:$topologyPayloadSha256
ArtifactSHA256:$topologyArtifactSha256
RecordCount:$observedRecordsCount
SealedAtUtc:$([DateTime]::UtcNow.ToString('o'))
"@

[System.IO.File]::WriteAllText(
    $FrozenTokenPath,
    $frozenContent,
    [System.Text.UTF8Encoding]::new($false)
)

# ============================================================================
# 18. POST-COMMIT FORENSIC VALIDATION
# ============================================================================

Write-Host ""
Write-Host "[POST-COMMIT] Vérification physique..." -ForegroundColor Yellow

$recheckedStateSha =
    Get-FileSha256 -Path $StateFilePath

if ($recheckedStateSha -ne $topologyArtifactSha256) {
    throw "FAIL-CLOSED: Hash physique de l'artefact instable."
}

$recheckedManifestSha =
    Get-FileSha256 -Path $TopologyManifestPath

$recheckedFrozenSha =
    Get-FileSha256 -Path $FrozenTokenPath

foreach ($required in @(
    $StateFilePath,
    $TopologyManifestPath,
    $FrozenTokenPath
)) {

    if (-not [System.IO.File]::Exists($required)) {
        throw "FAIL-CLOSED: Artefact final absent : $required"
    }
}

# ============================================================================
# 19. VERDICT
# ============================================================================

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " NIVEAU 2 : CERTIFIED & FROZEN" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan

Write-Host "Point Zero     : $parentRunId"
Write-Host "Records        : $observedRecordsCount"
Write-Host "Bytes          : $observedTotalBytes"
Write-Host "Directories    : $totalDirectories"
Write-Host "Max Depth      : $maxTreeDepth"
Write-Host ""
Write-Host "Payload SHA256 : $topologyPayloadSha256"
Write-Host "Artifact SHA256: $topologyArtifactSha256"
Write-Host "Manifest SHA256: $recheckedManifestSha"
Write-Host "Frozen SHA256  : $recheckedFrozenSha"
Write-Host ""
Write-Host "Artefact       : $StateFilePath"
Write-Host "Manifest       : $TopologyManifestPath"
Write-Host "Seal           : $FrozenTokenPath"
Write-Host "============================================================" -ForegroundColor Cyan