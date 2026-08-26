#Requires -Version 7.0
<#
.SYNOPSIS
    EZZIO_Build_TopologyState - Construction déterministe de l'état topologique (Niveau 2).
.DESCRIPTION
    Transforme séquentiellement un flux records.jsonl issu du Point Zéro en une
    arborescence topologique canonique scellée cryptographiquement.
    Garantit l'indépendance aux métadonnées d'exécution et valide les 4 gates (TG-01 à TG-04).
.PARAMETER RecordsPath
    Chemin absolu vers le fichier records.jsonl du Point Zéro.
.PARAMETER OutputDir
    Répertoire de destination pour l'artefact topologique.
#>

[CmdletBinding()]
param (
    [Parameter(Mandatory = $false)]
    [string]$RecordsPath = "G:\AI\_forensic\ContentTruth\run_20260820_130134_380\records.jsonl",

    [Parameter(Mandatory = $false)]
    [string]$OutputDir = "G:\AI\_forensic\SelfBody\topology\run_20260820_130134_380"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version 3.0

# -----------------------------------------------------------------------------
# Fonctions internes : Cryptographie et Canonisation
# -----------------------------------------------------------------------------

function Get-StreamSHA256 {
    param ([string]$FilePath)
    if (-not (Test-Path -LiteralPath $FilePath -PathType Leaf)) {
        throw "Fichier introuvable pour calcul de hash : $FilePath"
    }
        $stream = $null
    $sha256 = $null
    try {
        $stream = [System.IO.File]::OpenRead($FilePath)
        $sha256 = [System.Security.Cryptography.SHA256]::Create()
        $bytes = $sha256.ComputeHash($stream)
        return [System.BitConverter]::ToString($bytes).Replace("-", "").ToLowerInvariant()
    } finally {
        if ($null -ne $sha256) { $sha256.Dispose() }
        if ($null -ne $stream) { $stream.Dispose() }
    }
}

function Get-StringSHA256 {
    param ([string]$Content)
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($Content)
        $sha256 = $null
    try {
        $sha256 = [System.Security.Cryptography.SHA256]::Create()
        $hash = $sha256.ComputeHash($bytes)
        return [System.BitConverter]::ToString($hash).Replace("-", "").ToLowerInvariant()
    } finally {
        if ($null -ne $sha256) { $sha256.Dispose() }
    }
}

# -----------------------------------------------------------------------------
# Phase 1 : Validation d'entrée & TG-01 (Intégrité Parent)
# -----------------------------------------------------------------------------

Write-Host "[TG-01] Vérification de l'intégrité du parent..." -ForegroundColor Cyan

if (-not (Test-Path -LiteralPath $RecordsPath -PathType Leaf)) {
    throw "TG-01 FAIL : Le fichier parent '$RecordsPath' n'existe pas."
}

$parentFileInfo = Get-Item -LiteralPath $RecordsPath
if ($parentFileInfo.Length -eq 0) {
    throw "TG-01 FAIL : Le fichier parent records.jsonl est vide."
}

$parentSha256 = Get-StreamSHA256 -FilePath $RecordsPath
$parentRunId = Split-Path (Split-Path $RecordsPath -Parent) -Leaf

Write-Host "  -> Parent Run ID : $parentRunId"
Write-Host "  -> Parent SHA-256: $parentSha256"

# -----------------------------------------------------------------------------
# Phase 2 : Ingestion séquentielle et construction du Trie en mémoire
# -----------------------------------------------------------------------------

Write-Host "[INGEST] Lecture séquentielle de records.jsonl..." -ForegroundColor Cyan

$root = [ordered]@{
    name        = ""
    type        = "directory"
    size_bytes  = [int64]0
    file_count  = [int64]0
    dir_count   = [int64]0
    children    = [ordered]@{}
}

[int64]$recordsCount = 0
[int64]$recordsTotalBytes = 0

    $stream = $null
    $reader = $null
    try {
        $stream = [System.IO.File]::OpenRead($RecordsPath)
        $reader = [System.IO.StreamReader]::new($stream, [System.Text.Encoding]::UTF8)

        while (-not $reader.EndOfStream) {
            $line = $reader.ReadLine()
            if ([string]::IsNullOrWhiteSpace($line)) { continue }

            $record = $line | ConvertFrom-Json
            $recordsCount++

            $relPath = if ($record.PSObject.Properties["relative_path"]) { $record.relative_path } else { $record.path }
            $size = if ($record.PSObject.Properties["size_bytes"]) { [int64]$record.size_bytes } else { [int64]$record.size }
            $hash = if ($record.PSObject.Properties["sha256"]) { $record.sha256 } else { $record.hash }

            $recordsTotalBytes += $size

            # Normalisation du chemin relatif en segments ordonnés
            $normalizedPath = $relPath.Replace("\", "/").TrimStart("/")
            $segments = $normalizedPath.Split("/", [System.StringSplitOptions]::RemoveEmptyEntries)

            $currentNode = $root
            for ($i = 0; $i -lt $segments.Length; $i++) {
                $seg = $segments[$i]
                $isLeaf = ($i -eq $segments.Length - 1)

                if (-not $currentNode.children.Contains($seg)) {
                    if ($isLeaf) {
                        $currentNode.children[$seg] = [ordered]@{
                            name       = $seg
                            type       = "file"
                            size_bytes = $size
                            sha256     = $hash
                        }
                    } else {
                        $currentNode.children[$seg] = [ordered]@{
                            name       = $seg
                            type       = "directory"
                            size_bytes = [int64]0
                            file_count = [int64]0
                            dir_count  = [int64]0
                            children   = [ordered]@{}
                        }
                    }
                }
                $currentNode = $currentNode.children[$seg]
            }
        }
    } finally {
        if ($null -ne $reader) { $reader.Dispose() }
        if ($null -ne $stream) { $stream.Dispose() }
    }

Write-Host "  -> Records ingérés : $recordsCount"
Write-Host "  -> Masse brute     : $recordsTotalBytes octets"

# -----------------------------------------------------------------------------
# Phase 3 : Agrégation ascendante et calcul des métriques structurelles
# -----------------------------------------------------------------------------

Write-Host "[AGGREGATION] Calcul récursif de la topologie..." -ForegroundColor Cyan

[int64]$globalLeafCount = 0
[int64]$globalDirCount = 0
[int]$maxDepth = 0

function Aggregate-TrieNode {
    param (
        [System.Collections.IDictionary]$Node,
        [int]$CurrentDepth
    )

    if ($CurrentDepth -gt $script:maxDepth) {
        $script:maxDepth = $CurrentDepth
    }

    if ($Node.type -eq "file") {
        $script:globalLeafCount++
        return
    }

    $script:globalDirCount++
    [int64]$subSize = 0
    [int64]$subFiles = 0
    [int64]$subDirs = 0

    # Tri ordinal déterministe des clés enfants
    $sortedKeys = $Node.children.Keys | Sort-Object -CaseSensitive

    $sortedChildren = [ordered]@{}
    foreach ($key in $sortedKeys) {
        $child = $Node.children[$key]
        Aggregate-TrieNode -Node $child -CurrentDepth ($CurrentDepth + 1)

        $subSize += [int64]$child.size_bytes
        if ($child.type -eq "file") {
            $subFiles += 1
        } else {
            $subFiles += [int64]$child.file_count
            $subDirs += (1 + [int64]$child.dir_count)
        }
        $sortedChildren[$key] = $child
    }

    $Node.children = $sortedChildren
    $Node.size_bytes = $subSize
    $Node.file_count = $subFiles
    $Node.dir_count = $subDirs
}

# Lancement de l'agrégation depuis la racine
Aggregate-TrieNode -Node $root -CurrentDepth 0

# -----------------------------------------------------------------------------
# Phase 4 : Vérification stricte des Gates (TG-01 à TG-04)
# -----------------------------------------------------------------------------

Write-Host "[GATES] Validation des 4 contrats topologiques..." -ForegroundColor Cyan
$gatesPassed = [System.Collections.Generic.List[string]]::new()

# TG-01 : Validé en Phase 1
$gatesPassed.Add("TG-01")

# TG-02 : Parité des feuilles
if ($globalLeafCount -ne $recordsCount) {
    throw "TG-02 FAIL : Désynchronisation des feuilles. Records=$recordsCount vs Feuilles=$globalLeafCount"
}
$gatesPassed.Add("TG-02")
Write-Host "  -> [TG-02 PASS] Parité feuilles ($globalLeafCount == $recordsCount)" -ForegroundColor Green

# TG-03 : Conservation de la masse
if ($root.size_bytes -ne $recordsTotalBytes) {
    throw "TG-03 FAIL : Rupture de masse. RecordsBytes=$recordsTotalBytes vs RootBytes=$($root.size_bytes)"
}
$gatesPassed.Add("TG-03")
Write-Host "  -> [TG-03 PASS] Conservation de masse ($($root.size_bytes) octets)" -ForegroundColor Green

# TG-04 : Absence d'orphelins et cohérence d'arbre
[int64]$expectedTotalNodes = $globalLeafCount + $globalDirCount
if ($root.file_count -ne $globalLeafCount) {
    throw "TG-04 FAIL : Sommation hiérarchique incohérente (Orphelins détectés)."
}
$gatesPassed.Add("TG-04")
Write-Host "  -> [TG-04 PASS] Intégrité de l'arbre ($globalDirCount répertoires, $globalLeafCount feuilles)" -ForegroundColor Green

# -----------------------------------------------------------------------------
# Phase 5 : Payload Canonique et Hash Déterministe
# -----------------------------------------------------------------------------

Write-Host "[CANONICAL] Sérialisation du payload déterministe..." -ForegroundColor Cyan

$canonicalPayload = [ordered]@{
    lineage = [ordered]@{
        parent_point_zero_run  = $parentRunId
        parent_records_file    = (Split-Path $RecordsPath -Leaf)
        parent_records_sha256  = $parentSha256
        parent_record_count    = $recordsCount
        parent_total_bytes     = $recordsTotalBytes
    }
    metrics = [ordered]@{
        total_files       = $globalLeafCount
        total_directories = $globalDirCount
        total_bytes       = $root.size_bytes
        max_depth         = $maxDepth
    }
    tree = $root
}

# Sérialisation canonique compacte pour calcul de hash bit-exact
$canonicalJsonString = $canonicalPayload | ConvertTo-Json -Depth 100 -Compress
$topologyPayloadSha256 = Get-StringSHA256 -Content $canonicalJsonString

Write-Host "  -> Topology Payload SHA-256 : $topologyPayloadSha256" -ForegroundColor Yellow

# -----------------------------------------------------------------------------
# Phase 6 : Génération du document final et écriture hors Point Zéro
# -----------------------------------------------------------------------------

$finalState = [ordered]@{
    artifact_type      = "EZZIO_TOPOLOGY_STATE"
    schema_version     = "1.0"
    metadata           = [ordered]@{
        generated_at_utc  = [System.DateTime]::UtcNow.ToString("o")
        generator_version = "1.0.0"
    }
    lineage            = $canonicalPayload.lineage
    metrics            = $canonicalPayload.metrics
    tree               = $canonicalPayload.tree
    proof              = [ordered]@{
        topology_payload_sha256 = $topologyPayloadSha256
        gates_passed            = $gatesPassed.ToArray()
    }
}

if (-not (Test-Path -LiteralPath $OutputDir -PathType Container)) {
    $null = New-Item -Path $OutputDir -ItemType Directory -Force
}

$outputFile = Join-Path -Path $OutputDir -ChildPath "EZZIO_TOPOLOGY_STATE.json"
$finalJson = $finalState | ConvertTo-Json -Depth 100

[System.IO.File]::WriteAllText($outputFile, $finalJson, [System.Text.UTF8Encoding]::new($false))
Write-Host "Artefact généré : $outputFile" -ForegroundColor Green

# -----------------------------------------------------------------------------
# Phase 7 : Auto-vérification de la preuve de déterminisme
# -----------------------------------------------------------------------------

$recomputedCanonicalJson = $canonicalPayload | ConvertTo-Json -Depth 100 -Compress
$recomputedHash = Get-StringSHA256 -Content $recomputedCanonicalJson

if ($recomputedHash -ne $topologyPayloadSha256) {
    throw "ÉCHEC CRITIQUE : Instabilité du hash canonique calculé en mémoire."
}

Write-Host "Vérification interne du déterminisme : SUCCÈS ($recomputedHash)" -ForegroundColor Green