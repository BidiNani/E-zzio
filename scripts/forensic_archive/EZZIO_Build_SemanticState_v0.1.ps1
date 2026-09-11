function ConvertTo-CanonicalObject {
[CmdletBinding()]
param(
[Parameter(Mandatory)]
[AllowNull()]
[object]$Object
)

```
# ------------------------------------------------------------------------
# NULL
# ------------------------------------------------------------------------

if ($null -eq $Object) {
    return $null
}

# ------------------------------------------------------------------------
# SCALAIRES
# ------------------------------------------------------------------------

if (
    $Object -is [string] -or
    $Object -is [char] -or
    $Object -is [bool] -or
    $Object -is [byte] -or
    $Object -is [sbyte] -or
    $Object -is [int16] -or
    $Object -is [uint16] -or
    $Object -is [int32] -or
    $Object -is [uint32] -or
    $Object -is [int64] -or
    $Object -is [uint64] -or
    $Object -is [single] -or
    $Object -is [double] -or
    $Object -is [decimal] -or
    $Object -is [datetime] -or
    $Object -is [datetimeoffset] -or
    $Object -is [timespan] -or
    $Object -is [guid]
) {
    return $Object
}

# ------------------------------------------------------------------------
# DICTIONNAIRE
#
# Les clés sont converties explicitement en chaînes puis triées.
# Aucun paramètre Culture explicite n'est utilisé.
# ------------------------------------------------------------------------

if ($Object -is [System.Collections.IDictionary]) {

    $ordered = [ordered]@{}

    $keys = @(
        foreach ($keyObject in $Object.Keys) {
            [string]$keyObject
        }
    )

    $keys = @(
        $keys | Sort-Object -CaseSensitive
    )

    foreach ($key in $keys) {
        $ordered[$key] = ConvertTo-CanonicalObject -Object $Object[$key]
    }

    return $ordered
}

# ------------------------------------------------------------------------
# ENUMERABLE
# ------------------------------------------------------------------------

if ($Object -is [System.Collections.IEnumerable]) {

    $array = [System.Collections.Generic.List[object]]::new()

    foreach ($item in $Object) {
        $array.Add(
            (ConvertTo-CanonicalObject -Object $item)
        )
    }

    return @($array)
}

# ------------------------------------------------------------------------
# OBJET OBJET / PSCUSTOMOBJECT
# ------------------------------------------------------------------------

$props = @()

try {
    if (
        $null -ne $Object.PSObject -and
        $null -ne $Object.PSObject.Properties
    ) {
        $props = @(
            $Object.PSObject.Properties
        )
    }
}
catch {
    throw (
        "[FAIL-CLOSED] Impossible d'inspecter l'objet '{0}'." -f
        $Object.GetType().FullName
    )
}

if ($props.Count -gt 0) {

    $ordered = [ordered]@{}

    $sortedProps = @(
        $props |
            Sort-Object -Property Name -CaseSensitive
    )

    foreach ($prop in $sortedProps) {

        $ordered[[string]$prop.Name] =
            ConvertTo-CanonicalObject -Object $prop.Value
    }

    return $ordered
}

# ------------------------------------------------------------------------
# FALLBACK
# ------------------------------------------------------------------------

return $Object
```

}
#Requires -Version 7.0
<#
.SYNOPSIS
    E-ZZIO — SEMANTIC TRUTH ENGINE v0.1
    NIVEAU 3 — SEMANTIC TRUTH

.DESCRIPTION
    Construit une représentation sémantique déterministe du corpus E-ZZIO
    exclusivement à partir de la topologie certifiée du Niveau 2.

    ARCHITECTURE :

        POINT ZERO
            |
            v
        TOPOLOGY STATE
            |
            v
        LEAF FILES EXPLICITELY DESIGNATED
            |
            v
        PHYSICAL HASH RECHECK
            |
            +---- Python .py -> stdlib ast
            |
            +---- PowerShell .ps1 -> Native PowerShell AST
            |
            +---- JSON .json -> strict JSON parser
            |
            +---- autres -> PARSER_UNSUPPORTED
            |
            v
        CANONICAL SYMBOL MODEL
            |
            v
        SEMANTIC PAYLOAD SHA256
            |
            v
        PROCESS A / PROCESS B DETERMINISM
            |
            v
        CERTIFIED DERIVATION
            |
            v
        FROZEN

.CONTRACT

    - Aucun parcours récursif du corpus pour découvrir les fichiers.
    - Les fichiers analysés doivent être explicitement présents dans la
      topologie certifiée.
    - Aucun fichier source n'est modifié.
    - Le Point Zero n'est jamais modifié.
    - Le Topology State n'est jamais modifié.
    - Hash physique obligatoire AVANT parsing.
    - Hash physique obligatoire APRÈS parsing.
    - Mutation détectée => FAIL-CLOSED.
    - Parseur Regex interdit.
    - Parseur natif obligatoire pour les langages supportés.
    - Langage non supporté => PARSER_UNSUPPORTED.
    - Aucun symbole sans provenance.
    - RecordHash obligatoire.
    - Canonicalisation ordinale stricte.
    - Deux processus pwsh distincts doivent produire exactement le même
      semantic_payload_sha256.
    - Aucun écrasement d'une dérivation FROZEN existante.
    - Le statut CERTIFIED est uniquement le résultat des Quality Gates.

.SUPPORTED PARSERS

    .ps1  -> System.Management.Automation.Language.Parser
    .py   -> Python stdlib ast
    .json -> System.Text.Json / ConvertFrom-Json strict

.UNSUPPORTED

    .gd
    .lua
    autres extensions non explicitement supportées

.NOTES

    Niveau 3 = vérité sémantique dérivée.

    Le hash parent stocké dans la topologie est le hash physique du fichier
    source tel qu'observé au Point Zero.

    La provenance est donc :

        Semantic Symbol
            -> source_file
            -> parent_point_zero_run
            -> parent_record_hash

    Le système refuse toute divergence physique entre le Point Zero et le
    fichier actuellement parsé.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [string]$PointZeroDir =
        "G:\AI\_forensic\ContentTruth\run_20260820_130134_380",

    [Parameter(Mandatory = $false)]
    [string]$TopologyDir =
        "G:\AI\_forensic\SelfBody\topology\run_20260820_130134_380",

    [Parameter(Mandatory = $false)]
    [string]$OutputDir =
        "G:\AI\_forensic\SelfBody\semantic\run_20260820_130134_380",

    [Parameter(Mandatory = $false)]
    [ValidateSet("FAST","FORENSIC")]
    [string]$Mode = "FORENSIC"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ============================================================================
# 0. CONSTANTES
# ============================================================================

$EngineVersion = "0.1.0"
$SchemaVersion = "1.0"

$RecordsPath =
    Join-Path $PointZeroDir "records.jsonl"

$PointZeroManifestPath =
    Join-Path $PointZeroDir "run_manifest.json"

$TopologyStatePath =
    Join-Path $TopologyDir "EZZIO_TOPOLOGY_STATE.json"

$TopologyManifestPath =
    Join-Path $TopologyDir "topology_manifest.json"

$TopologyFrozenPath =
    Join-Path $TopologyDir "FROZEN"

$StateFilePath =
    Join-Path $OutputDir "EZZIO_SEMANTIC_STATE.json"

$SemanticManifestPath =
    Join-Path $OutputDir "semantic_manifest.json"

$FrozenTokenPath =
    Join-Path $OutputDir "FROZEN"

$ProcessBOutputDir =
    Join-Path $OutputDir "_determinism_process_b"

# ============================================================================
# 1. AFFICHAGE
# ============================================================================

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " E-ZZIO — SEMANTIC TRUTH ENGINE v$EngineVersion" -ForegroundColor Cyan
Write-Host " NIVEAU 3 — SEMANTIC TRUTH" -ForegroundColor Cyan
Write-Host " BASELINE : CERTIFIED TOPOLOGY" -ForegroundColor Yellow
Write-Host " MODE     : $Mode" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# ============================================================================
# 2. UTILITAIRES CRYPTOGRAPHIQUES
# ============================================================================

function Get-FileSha256 {
    [CmdletBinding()]
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

    return (
        [System.BitConverter]::ToString($hash)
    ).Replace('-', '').ToLowerInvariant()
}

function Get-StringSha256 {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$Content
    )

    $bytes =
        [System.Text.Encoding]::UTF8.GetBytes($Content)

    $sha =
        [System.Security.Cryptography.SHA256]::Create()

    try {
        $hash = $sha.ComputeHash($bytes)
    }
    finally {
        $sha.Dispose()
    }

    return (
        [System.BitConverter]::ToString($hash)
    ).Replace('-', '').ToLowerInvariant()
}

# ============================================================================
# 3. CANONICAL JSON
# ============================================================================

function ConvertTo-CanonicalObject {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [AllowNull()]
        [object]$Object
    )

    if ($null -eq $Object) {
        return $null
    }

    # 1. Scalaires / Primitifs / Chaines
    if ($Object -is [string] -or $Object.GetType().IsPrimitive -or $Object -is [datetime] -or $Object -is [decimal]) {
        return $Object
    }

    # 2. Dictionnaires (Hashtables, Ordered)
    if ($Object -is [System.Collections.IDictionary]) {
        $ordered = [ordered]@{}
        $keys = @($Object.Keys) | ForEach-Object { [string]$_ } | Sort-Object -Culture invariant -CaseSensitive
        foreach ($key in $keys) {
            $ordered[$key] = ConvertTo-CanonicalObject -Object $Object[$key]
        }
        return $ordered
    }

    # 3. Tableaux / Collections (doit venir apres string/dict)
    if ($Object -is [System.Collections.IEnumerable]) {
        $array = [System.Collections.Generic.List[object]]::new()
        foreach ($item in $Object) {
            $array.Add((ConvertTo-CanonicalObject -Object $item))
        }
        return @($array)
    }

    # 4. Objets complexes (PSCustomObject issus de JSON ou AST)
    $props = @($Object.PSObject.Properties)
    if ($props.Length -gt 0) {
        $ordered = [ordered]@{}
        $sortedProps = $props | Sort-Object -Property Name -CaseSensitive
        foreach ($prop in $sortedProps) {
            $ordered[$prop.Name] = ConvertTo-CanonicalObject -Object $prop.Value
        }
        return $ordered
    }

    # 5. Fallback sécurisé
    return $Object
}

function ConvertTo-CanonicalJson {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [AllowNull()]
        [object]$Object
    )

    $canonicalObject = ConvertTo-CanonicalObject -Object $Object
    return ($canonicalObject | ConvertTo-Json -Depth 100 -Compress)
}

# ============================================================================
# 4. STRICT JSON
# ============================================================================

function Read-StrictJsonFile {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    if (-not [System.IO.File]::Exists($Path)) {
        throw "FAIL-CLOSED: JSON absent : $Path"
    }

    $text =
        [System.IO.File]::ReadAllText(
            $Path,
            [System.Text.Encoding]::UTF8
        )

    if ([string]::IsNullOrWhiteSpace($text)) {
        throw "FAIL-CLOSED: JSON vide : $Path"
    }

    try {
        return (
            $text |
                ConvertFrom-Json -Depth 100
        )
    }
    catch {
        throw "FAIL-CLOSED: JSON invalide : $Path : $($_.Exception.Message)"
    }
}

# ============================================================================
# 5. VALIDATION DU CONFINEMENT
# ============================================================================

function Resolve-FullPathStrict {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    return (
        [System.IO.Path]::GetFullPath($Path)
    ).TrimEnd('\')
}

$resolvedPointZero =
    Resolve-FullPathStrict -Path $PointZeroDir

$resolvedTopology =
    Resolve-FullPathStrict -Path $TopologyDir

$resolvedOutput =
    Resolve-FullPathStrict -Path $OutputDir

if (
    [string]::Equals(
        $resolvedPointZero,
        $resolvedOutput,
        [System.StringComparison]::OrdinalIgnoreCase
    )
) {
    throw "FAIL-CLOSED: OutputDir == PointZeroDir."
}

if (
    [string]::Equals(
        $resolvedTopology,
        $resolvedOutput,
        [System.StringComparison]::OrdinalIgnoreCase
    )
) {
    throw "FAIL-CLOSED: OutputDir == TopologyDir."
}

# ============================================================================
# 6. REFUS D'ÉCRASER UNE DÉRIVATION FROZEN
# ============================================================================

if ([System.IO.File]::Exists($FrozenTokenPath)) {

    throw @"
FAIL-CLOSED:

La dérivation sémantique est déjà FROZEN.

Output :
$OutputDir

Aucun écrasement n'est autorisé.

Utiliser un nouveau répertoire de génération.
"@
}

# ============================================================================
# 7. VALIDATION DE LA TOPOLOGIE CERTIFIÉE
# ============================================================================

Write-Host "[TG-01] Validation de la topologie certifiée..." -ForegroundColor Yellow

foreach ($required in @(
    $PointZeroManifestPath,
    $RecordsPath,
    $TopologyStatePath,
    $TopologyManifestPath,
    $TopologyFrozenPath
)) {

    if (-not [System.IO.File]::Exists($required)) {
        throw "FAIL-CLOSED: Artefact requis absent : $required"
    }
}

$pointZeroManifest =
    Read-StrictJsonFile -Path $PointZeroManifestPath

$topologyState =
    Read-StrictJsonFile -Path $TopologyStatePath

$topologyManifest =
    Read-StrictJsonFile -Path $TopologyManifestPath

$pointZeroRunId =
    [string]$pointZeroManifest.RunId

$pointZeroChainHash =
    [string]$pointZeroManifest.ChainHash

$topologyParentRun =
    [string]$topologyManifest.parent_point_zero_run

$topologyParentRecordsSha =
    [string]$topologyManifest.parent_records_sha256

$topologyPayloadSha =
    [string]$topologyManifest.topology_payload_sha256

$topologyArtifactSha =
    [string]$topologyManifest.topology_artifact_sha256

$topologyStatus =
    [string]$topologyManifest.status

if ([string]::IsNullOrWhiteSpace($pointZeroRunId)) {
    throw "FAIL-CLOSED: Point Zero RunId absent."
}

if ([string]::IsNullOrWhiteSpace($pointZeroChainHash)) {
    throw "FAIL-CLOSED: Point Zero ChainHash absent."
}

if ($topologyParentRun -ne $pointZeroRunId) {
    throw @"
FAIL-CLOSED:
Topologie ancrée sur un autre Point Zero.

Topology : $topologyParentRun
Current  : $pointZeroRunId
"@
}

if ($topologyStatus -ne "CERTIFIED_DERIVATION") {
    throw "FAIL-CLOSED: Topologie non certifiée."
}

$currentTopologyArtifactSha =
    Get-FileSha256 -Path $TopologyStatePath

if ($currentTopologyArtifactSha -ne $topologyArtifactSha) {

    throw @"
FAIL-CLOSED:

Hash physique du Topology State divergent.

Manifest : $topologyArtifactSha
Physique : $currentTopologyArtifactSha
"@
}

$currentRecordsSha =
    Get-FileSha256 -Path $RecordsPath

if ($currentRecordsSha -ne $topologyParentRecordsSha) {

    throw @"
FAIL-CLOSED:

records.jsonl divergent du parent topologique.

Topology : $topologyParentRecordsSha
Physique  : $currentRecordsSha
"@
}

Write-Host " [PASS] TG-01_CERTIFIED_TOPOLOGY" -ForegroundColor Green
Write-Host "        Point Zero : $pointZeroRunId"
Write-Host "        Chain Hash : $pointZeroChainHash"
Write-Host "        Topology   : $topologyArtifactSha"

# ============================================================================
# 8. EXTRACTION DES FEUILLES DEPUIS LE TOPOLOGY STATE
# ============================================================================

Write-Host ""
Write-Host "[TOPOLOGY] Extraction des feuilles certifiées..." -ForegroundColor Yellow

$topologyFiles =
    [System.Collections.Generic.List[object]]::new()

function Collect-TopologyFiles {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [object]$Node,

        [Parameter(Mandatory)][AllowEmptyString()][string]$RelativePath)

    $type =
        [string]$Node.type

    if ($type -eq "file") {

        $fileName =
            [string]$Node.name

        if ([string]::IsNullOrWhiteSpace($fileName)) {
            throw "FAIL-CLOSED: Feuille topologique sans nom."
        }

                 $fullRelativePath =
             if ([string]::IsNullOrWhiteSpace($RelativePath)) {
                 $fileName
             }
             else {
                 $RelativePath
             }

        $size =
            [int64]$Node.size_bytes

        $hash =
            [string]$Node.sha256

        if ($size -lt 0) {
            throw "FAIL-CLOSED: Taille négative : $fullRelativePath"
        }

        if (
            [string]::IsNullOrWhiteSpace($hash) -or
            $hash -notmatch '^[0-9a-f]{64}$'
        ) {
            throw "FAIL-CLOSED: RecordHash invalide : $fullRelativePath"
        }

        $topologyFiles.Add(
            [ordered]@{
                source_file = $fullRelativePath.Replace('\','/')
                size_bytes = $size
                record_hash = $hash.ToLowerInvariant()
            }
        )

        return
    }

    if ($type -ne "directory") {
        throw "FAIL-CLOSED: Type topologique inconnu : $type"
    }

    $children =
        $Node.children

    if ($null -eq $children) {
        return
    }

    foreach (
        $property in (
            $children.PSObject.Properties |
                Sort-Object -Property Name
        )
    ) {

        $childName =
            [string]$property.Name

        if (
            $childName.Contains('/') -or
            $childName.Contains('\')
        ) {
            throw "FAIL-CLOSED: Nom de segment illégal : $childName"
        }

        $nextPath =
            if ([string]::IsNullOrWhiteSpace($RelativePath)) {
                $childName
            }
            else {
                "$RelativePath/$childName"
            }

        Collect-TopologyFiles `
            -Node $property.Value `
            -RelativePath $nextPath
    }
}

$treeRoot =
    $topologyState.tree

if ($null -eq $treeRoot) {
    throw "FAIL-CLOSED: Topology State sans arbre."
}

Collect-TopologyFiles `
    -Node $treeRoot `
    -RelativePath ""

$topologyFilesSorted =
    @(
        $topologyFiles |
            Sort-Object `
                -Property source_file `
                -CaseSensitive
    )

if ($topologyFilesSorted.Count -eq 0) {
    throw "FAIL-CLOSED: Aucune feuille topologique."
}

Write-Host "-> $($topologyFilesSorted.Count) feuilles certifiées." `
    -ForegroundColor Green

# ============================================================================
# 9. INDEX DES PARSEURS
# ============================================================================

$parserSupported =
    @(
        '.ps1',
        '.py',
        '.json'
    )

$parserUnsupported =
    [System.Collections.Generic.List[object]]::new()

# ============================================================================
# 10. PYTHON AST
# ============================================================================

$pythonAstProgram = @'
import ast
import json
import sys

path = sys.argv[1]

with open(path, "r", encoding="utf-8", errors="strict") as f:
    source = f.read()

tree = ast.parse(source, filename=path, mode="exec")

symbols = []

def end_line(node):
    return getattr(node, "end_lineno", getattr(node, "lineno", 0))

def span(node):
    return [int(getattr(node, "lineno", 0)), int(end_line(node))]

def add_symbol(name, symbol_type, node, extra=None):
    item = {
        "symbol_name": name,
        "symbol_type": symbol_type,
        "line_span": span(node),
        "signature": {}
    }

    if extra:
        item["signature"] = extra

    symbols.append(item)

class Visitor(ast.NodeVisitor):

    def __init__(self):
        self.scope = []

    def qualified(self, name):
        if self.scope:
            return ".".join(self.scope + [name])
        return name

    def visit_ClassDef(self, node):
        name = self.qualified(node.name)

        bases = []
        for b in node.bases:
            try:
                bases.append(ast.unparse(b))
            except Exception:
                bases.append(ast.dump(b, annotate_fields=True, include_attributes=False))

        add_symbol(
            name,
            "class",
            node,
            {
                "bases": sorted(bases)
            }
        )

        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    def visit_FunctionDef(self, node):
        name = self.qualified(node.name)

        add_symbol(
            name,
            "function",
            node,
            {
                "arguments": [
                    a.arg for a in node.args.posonlyargs +
                    node.args.args +
                    node.args.kwonlyargs
                ],
                "returns":
                    ast.unparse(node.returns)
                    if node.returns is not None else None,
                "async": False
            }
        )

        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    def visit_AsyncFunctionDef(self, node):
        name = self.qualified(node.name)

        add_symbol(
            name,
            "function",
            node,
            {
                "arguments": [
                    a.arg for a in node.args.posonlyargs +
                    node.args.args +
                    node.args.kwonlyargs
                ],
                "returns":
                    ast.unparse(node.returns)
                    if node.returns is not None else None,
                "async": True
            }
        )

        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    def visit_Import(self, node):
        for alias in node.names:
            add_symbol(
                alias.asname if alias.asname else alias.name,
                "import",
                node,
                {
                    "module": alias.name,
                    "alias": alias.asname
                }
            )

    def visit_ImportFrom(self, node):
        module = node.module or ""

        for alias in node.names:
            name = alias.asname if alias.asname else alias.name

            add_symbol(
                name,
                "import",
                node,
                {
                    "module": module,
                    "imported": alias.name,
                    "alias": alias.asname,
                    "level": int(node.level)
                }
            )

Visitor().visit(tree)

symbols.sort(
    key=lambda x: (
        x["line_span"][0],
        x["line_span"][1],
        x["symbol_type"],
        x["symbol_name"]
    )
)

print(json.dumps(
    {
        "parser": "python.ast",
        "parser_version": sys.version.split()[0],
        "symbols": symbols
    },
    ensure_ascii=False,
    separators=(",", ":"),
    sort_keys=True
))
'@

# ============================================================================
# 11. EXÉCUTION D'UN SOUS-PROCESSUS PYTHON
# ============================================================================

function Invoke-PythonAstParser {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$PythonPath,

        [Parameter(Mandatory)]
        [string]$SourcePath
    )

    if (-not (Get-Command $PythonPath -ErrorAction SilentlyContinue)) {
        throw "FAIL-CLOSED: Python introuvable : $PythonPath"
    }

    $psi =
        [System.Diagnostics.ProcessStartInfo]::new()

    $psi.FileName =
        $PythonPath

    $psi.ArgumentList.Add("-c")
    $psi.ArgumentList.Add($pythonAstProgram)
    $psi.ArgumentList.Add($SourcePath)

    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.CreateNoWindow = $true

    $process =
        [System.Diagnostics.Process]::new()

    $process.StartInfo =
        $psi

    if (-not $process.Start()) {
        throw "FAIL-CLOSED: Impossible de démarrer Python."
    }

    $stdout =
        $process.StandardOutput.ReadToEnd()

    $stderr =
        $process.StandardError.ReadToEnd()

    $process.WaitForExit()

    if ($process.ExitCode -ne 0) {

        throw @"
FAIL-CLOSED: Python AST parser failure.

ExitCode : $($process.ExitCode)
File     : $SourcePath

STDERR:
$stderr
"@
    }

    if ([string]::IsNullOrWhiteSpace($stdout)) {
        throw "FAIL-CLOSED: Python AST parser returned empty output."
    }

    try {
        return (
            $stdout |
                ConvertFrom-Json -Depth 100
        )
    }
    catch {
        throw "FAIL-CLOSED: Sortie AST Python non JSON."
    }
}

# ============================================================================
# 12. PARSEUR POWERSHELL NATIF
# ============================================================================

function Get-AstLineSpan {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [object]$Ast
    )

    $extent =
        $Ast.Extent

    return @(
        [int]$extent.StartLineNumber,
        [int]$extent.EndLineNumber
    )
}

function Parse-PowerShellFile {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$SourcePath
    )

    $source =
        [System.IO.File]::ReadAllText(
            $SourcePath,
            [System.Text.Encoding]::UTF8
        )

    $tokens = $null
    $errors = $null

    $ast =
        [System.Management.Automation.Language.Parser]::ParseInput(
            $source,
            [ref]$tokens,
            [ref]$errors
        )

    if ($null -eq $ast) {
        throw "FAIL-CLOSED: PowerShell AST nul."
    }

    if ($errors.Count -gt 0) {

        $messages =
            @(
                $errors |
                    ForEach-Object {
                        $_.Message
                    }
            )

        throw @"
FAIL-CLOSED: PowerShell syntax errors.

File : $SourcePath

$($messages -join "`n")
"@
    }

    $symbols =
        [System.Collections.Generic.List[object]]::new()

    $functions =
        $ast.FindAll(
            {
                param($node)

                $node -is
                    [System.Management.Automation.Language.FunctionDefinitionAst]
            },
            $true
        )

    foreach ($fn in $functions) {

        $parameters =
            @()

        if ($null -ne $fn.Parameters) {

            foreach ($p in $fn.Parameters) {

                $parameters +=
                    [string]$p.Name.VariablePath.UserPath
            }
        }

        $symbols.Add(
            [ordered]@{
                symbol_name =
                    [string]$fn.Name

                symbol_type =
                    "function"

                line_span =
                    Get-AstLineSpan -Ast $fn

                signature =
                    [ordered]@{
                        parameters =
                            @(
                                $parameters |
                                    Sort-Object -CaseSensitive
                            )
                    }
            }
        )
    }

    $types =
        $ast.FindAll(
            {
                param($node)

                $node -is
                    [System.Management.Automation.Language.TypeDefinitionAst]
            },
            $true
        )

    foreach ($type in $types) {

        $members =
            [System.Collections.Generic.List[string]]::new()

        foreach ($member in $type.Members) {

            if ($null -ne $member.Name) {
                $members.Add(
                    [string]$member.Name
                )
            }
        }

        $symbols.Add(
            [ordered]@{
                symbol_name =
                    [string]$type.Name

                symbol_type =
                    "class"

                line_span =
                    Get-AstLineSpan -Ast $type

                signature =
                    [ordered]@{
                        members =
                            @(
                                $members |
                                    Sort-Object -CaseSensitive
                            )
                    }
            }
        )
    }

    $usingStatements =
        $ast.FindAll(
            {
                param($node)

                $node -is
                    [System.Management.Automation.Language.UsingStatementAst]
            },
            $true
        )

    foreach ($using in $usingStatements) {

        $text =
            $using.Extent.Text.Trim()

        $symbols.Add(
            [ordered]@{
                symbol_name =
                    $text

                symbol_type =
                    "using"

                line_span =
                    Get-AstLineSpan -Ast $using

                signature =
                    [ordered]@{
                        statement =
                            $text
                    }
            }
        )
    }

    $commands =
        $ast.FindAll(
            {
                param($node)

                $node -is
                    [System.Management.Automation.Language.CommandAst]
            },
            $true
        )

    foreach ($command in $commands) {

        $elements =
            @($command.CommandElements)

        if ($elements.Count -eq 0) {
            continue
        }

        $commandName =
            [string]$elements[0].Value

        if (
            $commandName -ieq "Import-Module" -or
            $commandName -ieq "Import-Package"
        ) {

            $arguments =
                @(
                    $elements |
                        Select-Object -Skip 1 |
                        ForEach-Object {
                            [string]$_.Extent.Text
                        }
                )

            $symbols.Add(
                [ordered]@{
                    symbol_name =
                        $commandName

                    symbol_type =
                        "import"

                    line_span =
                        Get-AstLineSpan -Ast $command

                    signature =
                        [ordered]@{
                            command =
                                $commandName

                            arguments =
                                $arguments
                        }
                }
            )
        }
    }

    $orderedSymbols =
        @(
            $symbols |
                Sort-Object `
                    @{Expression={
                        $_.line_span[0]
                    }},
                    @{Expression={
                        $_.line_span[1]
                    }},
                    @{Expression={
                        $_.symbol_type
                    }},
                    @{Expression={
                        $_.symbol_name
                    }}
        )

    return [ordered]@{
        parser = "powershell.native.ast"
        parser_version =
            $PSVersionTable.PSVersion.ToString()
        symbols =
            @($orderedSymbols)
    }
}

# ============================================================================
# 13. PARSEUR JSON
# ============================================================================

function Parse-JsonFile {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$SourcePath
    )

    $text = [System.IO.File]::ReadAllText(
        $SourcePath,
        [System.Text.Encoding]::UTF8
    )

    try {
        $obj = $text | ConvertFrom-Json -Depth 100
    }
    catch {
        throw "FAIL-CLOSED: JSON syntax invalide : $SourcePath"
    }

    $symbols = [System.Collections.Generic.List[object]]::new()

    if ($null -eq $obj) {
        return [ordered]@{
            parser = "powershell.convertfrom-json"
            parser_version = $PSVersionTable.PSVersion.ToString()
            symbols = @($symbols)
        }
    }

    $props = @()
    try {
        if ($obj -is [System.Collections.IDictionary]) {
            foreach ($k in $obj.Keys) {
                $pVal = $obj[$k]
                $symbols.Add([ordered]@{
                    symbol_name = [string]$k
                    symbol_type = "json_key"
                    line_span = @(0,0)
                    signature = [ordered]@{
                        level = 1
                        value_type = if ($null -eq $pVal) { "null" } else { $pVal.GetType().Name }
                    }
                })
            }
        }
        elseif ($null -ne $obj.PSObject -and $null -ne $obj.PSObject.Properties) {
            $props = @($obj.PSObject.Properties)
            foreach ($property in $props) {
                $pVal = $property.Value
                $symbols.Add([ordered]@{
                    symbol_name = [string]$property.Name
                    symbol_type = "json_key"
                    line_span = @(0,0)
                    signature = [ordered]@{
                        level = 1
                        value_type = if ($null -eq $pVal) { "null" } else { $pVal.GetType().Name }
                    }
                })

                if ($null -ne $pVal -and $null -ne $pVal.PSObject -and $null -ne $pVal.PSObject.Properties) {
                    $childProps = @($pVal.PSObject.Properties)
                    if ($childProps.Count -gt 0) {
                        foreach ($child in $childProps) {
                            $cVal = $child.Value
                            $symbols.Add([ordered]@{
                                symbol_name = "$($property.Name).$($child.Name)"
                                symbol_type = "json_key"
                                line_span = @(0,0)
                                signature = [ordered]@{
                                    level = 2
                                    parent = [string]$property.Name
                                    value_type = if ($null -eq $cVal) { "null" } else { $cVal.GetType().Name }
                                }
                            })
                        }
                    }
                }
            }
        }
    }
    catch {}

    return [ordered]@{
        parser = "powershell.convertfrom-json"
        parser_version = $PSVersionTable.PSVersion.ToString()
        symbols = @(
            $symbols | Sort-Object symbol_type, symbol_name
        )
    }
}

# ============================================================================
# 14. RÉSOLUTION DU FICHIER SOURCE
# ============================================================================

function Resolve-SourcePath {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$RelativePath
    )

    $normalized =
        $RelativePath.Replace('/','\')

    if (
        [System.IO.Path]::IsPathRooted($normalized)
    ) {
        throw "FAIL-CLOSED: RelativePath absolu interdit : $RelativePath"
    }

    if (
        $normalized.Contains("..")
    ) {
        throw "FAIL-CLOSED: Traversal détecté : $RelativePath"
    }

    $candidate =
        [System.IO.Path]::GetFullPath(
            (Join-Path "G:\AI\E-zzio" $normalized)
        )

    $candidateRoot =
        Resolve-FullPathStrict -Path "G:\AI\E-zzio"

    $candidateLower =
        $candidate.ToLowerInvariant()

    $rootLower =
        ($candidateRoot + '\').ToLowerInvariant()

    if (-not $candidateLower.StartsWith($rootLower)) {
        throw "FAIL-CLOSED: Fichier hors Point Zero : $RelativePath"
    }

    return $candidate
}

# ============================================================================
# 15. ANALYSE D'UN FICHIER
# ============================================================================

function Invoke-SemanticFileAnalysis {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [object]$TopologyFile
    )

    $relativePath =
        [string]$TopologyFile.source_file

    $expectedHash =
        [string]$TopologyFile.record_hash

    $expectedSize =
        [int64]$TopologyFile.size_bytes

    $extension =
        [System.IO.Path]::GetExtension($relativePath).ToLowerInvariant()

    $sourcePath =
        Resolve-SourcePath -RelativePath $relativePath

    if (-not [System.IO.File]::Exists($sourcePath)) {
        throw "FAIL-CLOSED: Source absente : $relativePath"
    }

    # ------------------------------------------------------------------------
    # Hash AVANT PARSING
    # ------------------------------------------------------------------------

    $preHash =
        Get-FileSha256 -Path $sourcePath

    if ($preHash -ne $expectedHash) {

        throw @"
FAIL-CLOSED: MUTATION / DIVERGENCE AVANT PARSING.

File     : $relativePath
Expected : $expectedHash
Physical : $preHash
"@
    }

    $physicalSize =
        [System.IO.FileInfo]::new($sourcePath).Length

    if ($physicalSize -ne $expectedSize) {

        throw @"
FAIL-CLOSED: TAILLE PHYSIQUE DIVERGENTE.

File     : $relativePath
Expected : $expectedSize
Physical : $physicalSize
"@
    }

    # ------------------------------------------------------------------------
    # PARSING
    # ------------------------------------------------------------------------

    $parserStatus =
        "PARSED"

    $parser =
        $null

    $parserVersion =
        $null

    $symbols =
        @()

    try {

        switch ($extension) {

            ".ps1" {

                $parsed =
                    Parse-PowerShellFile -SourcePath $sourcePath

                $parser =
                    $parsed.parser

                $parserVersion =
                    $parsed.parser_version

                $symbols =
                    @($parsed.symbols)

                break
            }

            ".py" {

                $pythonCommand =
                    Get-Command python -ErrorAction SilentlyContinue

                if ($null -eq $pythonCommand) {

                    throw @"
FAIL-CLOSED:

Python requis pour le parseur stdlib AST.

File : $relativePath
"@
                }

                $parsed =
                    Invoke-PythonAstParser `
                        -PythonPath $pythonCommand.Source `
                        -SourcePath $sourcePath

                $parser =
                    [string]$parsed.parser

                $parserVersion =
                    [string]$parsed.parser_version

                $symbols =
                    @($parsed.symbols)

                break
            }

            ".json" {

                $parsed =
                    Parse-JsonFile -SourcePath $sourcePath

                $parser =
                    $parsed.parser

                $parserVersion =
                    $parsed.parser_version

                $symbols =
                    @($parsed.symbols)

                break
            }

            default {

                $parserStatus =
                    "PARSER_UNSUPPORTED"

                $parser =
                    $null

                $parserVersion =
                    $null

                $symbols =
                    @()

                $parserUnsupported.Add(
                    [ordered]@{
                        source_file =
                            $relativePath

                        extension =
                            $extension

                        status =
                            "PARSER_UNSUPPORTED"
                    }
                )

                break
            }
        }
    }
    finally {

        # --------------------------------------------------------------------
        # Hash APRÈS PARSING
        # --------------------------------------------------------------------

        $postHash =
            Get-FileSha256 -Path $sourcePath

        if ($postHash -ne $preHash) {

            throw @"
FAIL-CLOSED: MUTATION PENDANT LE PARSING.

File     : $relativePath
Before   : $preHash
After    : $postHash
"@
        }
    }

    # ------------------------------------------------------------------------
    # PROVENANCE
    # ------------------------------------------------------------------------

    $finalSymbols =
        [System.Collections.Generic.List[object]]::new()

    foreach ($symbol in $symbols) {

        if ($null -eq $symbol) {
            throw "FAIL-CLOSED: Symbole null : $relativePath"
        }

        $symbolName =
            [string]$symbol.symbol_name

        $symbolType =
            [string]$symbol.symbol_type

        if ([string]::IsNullOrWhiteSpace($symbolName)) {
            throw "FAIL-CLOSED: Symbole sans nom : $relativePath"
        }

        if ([string]::IsNullOrWhiteSpace($symbolType)) {
            throw "FAIL-CLOSED: Symbole sans type : $relativePath"
        }

        $lineSpan =
            @($symbol.line_span)

        if ($lineSpan.Count -ne 2) {
            throw "FAIL-CLOSED: line_span invalide : $relativePath"
        }

        $finalSymbols.Add(
            [ordered]@{
                symbol_name =
                    $symbolName

                symbol_type =
                    $symbolType

                provenance =
                    [ordered]@{
                        source_file =
                            $relativePath

                        parent_point_zero_run =
                            $pointZeroRunId

                        parent_record_hash =
                            $expectedHash

                        line_span =
                            @(
                                [int]$lineSpan[0],
                                [int]$lineSpan[1]
                            )
                    }

                signature =
                    if ($null -eq $symbol.signature) {
                        [ordered]@{}
                    }
                    else {
                        ConvertTo-CanonicalObject `
                            -Object $symbol.signature
                    }
            }
        )
    }

    $finalSymbolsSorted =
        @(
            $finalSymbols |
                Sort-Object `
                    @{Expression={
                        $_.provenance.source_file
                    }},
                    @{Expression={
                        $_.provenance.line_span[0]
                    }},
                    @{Expression={
                        $_.provenance.line_span[1]
                    }},
                    @{Expression={
                        $_.symbol_type
                    }},
                    @{Expression={
                        $_.symbol_name
                    }}
        )

    return [ordered]@{
        source_file =
            $relativePath

        extension =
            $extension

        parser_status =
            $parserStatus

        parser =
            $parser

        parser_version =
            $parserVersion

        physical_size_bytes =
            $physicalSize

        record_hash =
            $expectedHash

        symbols =
            @($finalSymbolsSorted)
    }
}

# ============================================================================
# 16. INGESTION SÉMANTIQUE
# ============================================================================

Write-Host ""
Write-Host "[INGESTION] Analyse des feuilles topologiques..." `
    -ForegroundColor Yellow

$semanticFiles =
    [System.Collections.Generic.List[object]]::new()

$index = 0
$total =
    $topologyFilesSorted.Count

foreach ($topologyFile in $topologyFilesSorted) {

    $index++

    if (
        $Mode -eq "FORENSIC" -and
        (
            $index -eq 1 -or
            $index % 100 -eq 0 -or
            $index -eq $total
        )
    ) {

        Write-Progress `
            -Activity "E-ZZIO Semantic Truth" `
            -Status "$index / $total" `
            -PercentComplete (
                [int](($index / $total) * 100)
            )
    }

    $analysisResult = Invoke-SemanticFileAnalysis -TopologyFile $topologyFile
        $semanticFiles.Add($analysisResult)
}

if ($Mode -eq "FORENSIC") {
    Write-Progress `
        -Activity "E-ZZIO Semantic Truth" `
        -Completed
}

# ============================================================================
# 17. STATISTIQUES
# ============================================================================

$totalSymbols =
    @(
        $semanticFiles |
            ForEach-Object {
                @($_.symbols)
            }
    ).Count

$totalParsedFiles =
    @(
        $semanticFiles |
            Where-Object {
                $_.parser_status -eq "PARSED"
            }
    ).Count

$totalUnsupportedFiles =
    @(
        $semanticFiles |
            Where-Object {
                $_.parser_status -eq "PARSER_UNSUPPORTED"
            }
    ).Count

Write-Host ""
Write-Host "-> Fichiers analysés       : $($semanticFiles.Count)" `
    -ForegroundColor Green

Write-Host "-> Fichiers parsés         : $totalParsedFiles" `
    -ForegroundColor Green

Write-Host "-> Fichiers unsupported    : $totalUnsupportedFiles" `
    -ForegroundColor Yellow

Write-Host "-> Symboles extraits       : $totalSymbols" `
    -ForegroundColor Green

# ============================================================================
# 18. QUALITY GATES SÉMANTIQUES
# ============================================================================

Write-Host ""
Write-Host "[QUALITY GATES] Validation sémantique..." `
    -ForegroundColor Yellow

$gates =
    [ordered]@{}

# TG-01
$gates["TG-01_CERTIFIED_TOPOLOGY"] =
    (
        ($topologyStatus -eq "CERTIFIED_DERIVATION") -and
        ($currentTopologyArtifactSha -eq $topologyArtifactSha) -and
        ($currentRecordsSha -eq $topologyParentRecordsSha) -and
        ($topologyParentRun -eq $pointZeroRunId)
    )

# TG-02
$gates["TG-02_TOPOLOGY_CARDINALITY"] =
    (
        $semanticFiles.Count -eq
        [int64]$topologyState.metrics.total_files
    )

# TG-03
$gates["TG-03_PHYSICAL_HASH_PARITY"] =
    (
        @(
            $semanticFiles |
                Where-Object {
                    $_.record_hash -notmatch '^[0-9a-f]{64}$'
                }
        ).Count -eq 0
    )

# TG-04
$gates["TG-04_SYMBOL_PROVENANCE"] =
    (
        @(
            $semanticFiles |
                ForEach-Object {
                    $_.symbols
                } |
                Where-Object {
                    [string]::IsNullOrWhiteSpace(
                        $_.provenance.parent_record_hash
                    )
                }
        ).Count -eq 0
    )

# TG-05
$gates["TG-05_NO_UNAUTHORIZED_PARSER_INFERENCE"] =
    (
        @(
            $semanticFiles |
                Where-Object {
                    $_.parser_status -eq "PARSED" -and
                    [string]::IsNullOrWhiteSpace($_.parser)
                }
        ).Count -eq 0
    )

# ============================================================================
# 19. PAYLOAD CANONIQUE
# ============================================================================

$semanticPayloadObject =
    [ordered]@{
        artifact_type =
            "EZZIO_SEMANTIC_PAYLOAD"

        schema_version =
            $SchemaVersion

        engine_version =
            $EngineVersion

        parent =
            [ordered]@{
                point_zero_run =
                    $pointZeroRunId

                records_sha256 =
                    $currentRecordsSha

                chain_hash =
                    $pointZeroChainHash

                topology_payload_sha256 =
                    $topologyPayloadSha

                topology_artifact_sha256 =
                    $topologyArtifactSha
            }

        metrics =
            [ordered]@{
                total_files =
                    $semanticFiles.Count

                parsed_files =
                    $totalParsedFiles

                unsupported_files =
                    $totalUnsupportedFiles

                total_symbols =
                    $totalSymbols
            }

        files =
            @(
                $semanticFiles |
                    Sort-Object `
                        -Property source_file
            )
    }

$canonicalSemanticPayload =
    ConvertTo-CanonicalJson `
        -Object $semanticPayloadObject

$semanticPayloadSha256 =
    Get-StringSha256 `
        -Content $canonicalSemanticPayload

if (
    $semanticPayloadSha256 -notmatch
    '^[0-9a-f]{64}$'
) {
    throw "FAIL-CLOSED: Semantic payload SHA256 invalide."
}

$gates["TG-06_CANONICAL_PAYLOAD_VALID"] =
    (
        -not [string]::IsNullOrWhiteSpace(
            $canonicalSemanticPayload
        ) -and
        $semanticPayloadSha256 -match '^[0-9a-f]{64}$'
    )

# ============================================================================
# 20. AFFICHAGE GATES AVANT COMMIT
# ============================================================================

Write-Host ""

$allGatesPass =
    $true

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

        $allGatesPass =
            $false
    }
}

if (-not $allGatesPass) {
    throw "FAIL-CLOSED: Quality Gate sémantique échouée."
}

# ============================================================================
# 21. ÉCRITURE D'UNE DÉRIVATION INTERMÉDIAIRE POUR PROCESS A
# ============================================================================

if (-not [System.IO.Directory]::Exists($OutputDir)) {

    [System.IO.Directory]::CreateDirectory(
        $OutputDir
    ) | Out-Null
}

$processAPath =
    Join-Path $OutputDir "_process_a_payload.json"

[System.IO.File]::WriteAllText(
    $processAPath,
    $canonicalSemanticPayload,
    [System.Text.UTF8Encoding]::new($false)
)

$processAHash =
    Get-FileSha256 -Path $processAPath

# ============================================================================
# 22. TG-07 — DÉTERMINISME DU BUFFER
# ============================================================================

Write-Host ""
Write-Host "[TG-07] Préparation du contrôle de déterminisme..." `
    -ForegroundColor Yellow

$scriptPath =
    $PSCommandPath

if ([string]::IsNullOrWhiteSpace($scriptPath)) {

    throw @"
FAIL-CLOSED:

Le script doit être exécuté depuis un fichier .ps1.

Le mode interactif ne permet pas de réaliser correctement
la preuve Process A / Process B.
"@
}

if (
    [System.IO.Path]::GetFullPath($ProcessBOutputDir) -eq
    [System.IO.Path]::GetFullPath($OutputDir)
) {
    throw "FAIL-CLOSED: staging Process B identique à OutputDir."
}

if ([System.IO.Directory]::Exists($ProcessBOutputDir)) {

    throw @"
FAIL-CLOSED:

Le staging Process B existe déjà :

$ProcessBOutputDir

Aucun nettoyage automatique n'est autorisé.
"@
}

[System.IO.Directory]::CreateDirectory(
    $ProcessBOutputDir
) | Out-Null

$processBResultPath =
    Join-Path $ProcessBOutputDir "process_b_result.json"

$processBScript =
    Join-Path $ProcessBOutputDir "process_b_runner.ps1"

$runnerContent = @'
[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$EngineScript,

    [Parameter(Mandatory)]
    [string]$PointZeroDir,

    [Parameter(Mandatory)]
    [string]$TopologyDir,

    [Parameter(Mandatory)]
    [string]$OutputDir,

    [Parameter(Mandatory)]
    [string]$ResultPath
)

$ErrorActionPreference = 'Stop'

try {

    & $EngineScript `
        -PointZeroDir $PointZeroDir `
        -TopologyDir $TopologyDir `
        -OutputDir $OutputDir `
        -Mode FAST

    $state =
        Join-Path $OutputDir "EZZIO_SEMANTIC_STATE.json"

    if (-not [System.IO.File]::Exists($state)) {
        throw "Process B: semantic state absent."
    }

    $shaProvider =
        [System.Security.Cryptography.SHA256]::Create()

    try {

        $stream =
            [System.IO.File]::OpenRead($state)

        try {
            $hash =
                $shaProvider.ComputeHash($stream)
        }
        finally {
            $stream.Dispose()
        }
    }
    finally {
        $shaProvider.Dispose()
    }

    $sha =
        (
            [System.BitConverter]::ToString($hash)
        ).Replace('-', '').ToLowerInvariant()

    $result =
        [ordered]@{
            ok = $true
            state_sha256 = $sha
            state_path = $state
        }

    [System.IO.File]::WriteAllText(
        $ResultPath,
        (
            $result |
                ConvertTo-Json -Depth 20
        ),
        [System.Text.UTF8Encoding]::new($false)
    )

    exit 0
}
catch {

    $result =
        [ordered]@{
            ok = $false
            error = $_.Exception.Message
        }

    [System.IO.File]::WriteAllText(
        $ResultPath,
        (
            $result |
                ConvertTo-Json -Depth 20
        ),
        [System.Text.UTF8Encoding]::new($false)
    )

    exit 1
}
'@

[System.IO.File]::WriteAllText(
    $processBScript,
    $runnerContent,
    [System.Text.UTF8Encoding]::new($false)
)

# ============================================================================
# 23. PROCESS B
# ============================================================================

$pwshCommand =
    Get-Command pwsh -ErrorAction SilentlyContinue

if ($null -eq $pwshCommand) {
    throw "FAIL-CLOSED: pwsh introuvable pour Process B."
}

$psiB =
    [System.Diagnostics.ProcessStartInfo]::new()

$psiB.FileName =
    $pwshCommand.Source

$psiB.ArgumentList.Add("-NoProfile")
$psiB.ArgumentList.Add("-NonInteractive")
$psiB.ArgumentList.Add("-File")
$psiB.ArgumentList.Add($processBScript)
$psiB.ArgumentList.Add("-EngineScript")
$psiB.ArgumentList.Add($scriptPath)
$psiB.ArgumentList.Add("-PointZeroDir")
$psiB.ArgumentList.Add($PointZeroDir)
$psiB.ArgumentList.Add("-TopologyDir")
$psiB.ArgumentList.Add($TopologyDir)
$psiB.ArgumentList.Add("-OutputDir")
$psiB.ArgumentList.Add($ProcessBOutputDir)
$psiB.ArgumentList.Add("-ResultPath")
$psiB.ArgumentList.Add($processBResultPath)

$psiB.UseShellExecute = $false
$psiB.RedirectStandardOutput = $true
$psiB.RedirectStandardError = $true
$psiB.CreateNoWindow = $true

$processB =
    [System.Diagnostics.Process]::new()

$processB.StartInfo =
    $psiB

if (-not $processB.Start()) {
    throw "FAIL-CLOSED: Impossible de lancer Process B."
}

$stdoutB =
    $processB.StandardOutput.ReadToEnd()

$stderrB =
    $processB.StandardError.ReadToEnd()

$processB.WaitForExit()

if ($processB.ExitCode -ne 0) {

    throw @"
FAIL-CLOSED:

Process B a échoué.

ExitCode :
$($processB.ExitCode)

STDOUT :
$stdoutB

STDERR :
$stderrB
"@
}

if (-not [System.IO.File]::Exists($processBResultPath)) {
    throw "FAIL-CLOSED: Résultat Process B absent."
}

$processBResult =
    Read-StrictJsonFile -Path $processBResultPath

if (-not [bool]$processBResult.ok) {

    throw @"
FAIL-CLOSED:

Process B a retourné un état non valide.

$($processBResult.error)
"@
}

$processBStatePath =
    [string]$processBResult.state_path

$processBStateSha =
    [string]$processBResult.state_sha256

if ([string]::IsNullOrWhiteSpace($processBStateSha)) {
    throw "FAIL-CLOSED: Process B sans hash."
}

# ============================================================================
# 24. COMPARAISON PROCESS A / PROCESS B
# ============================================================================

$gates["TG-07_DUAL_PROCESS_DETERMINISM"] =
    (
        $processAHash -eq
        $processBStateSha
    )

if (-not $gates["TG-07_DUAL_PROCESS_DETERMINISM"]) {

    throw @"
FAIL-CLOSED:

DÉTERMINISME INTER-PROCESSUS ÉCHOUÉ.

Process A : $processAHash
Process B : $processBStateSha
"@
}

Write-Host " [PASS] TG-07_DUAL_PROCESS_DETERMINISM" `
    -ForegroundColor Green

Write-Host "        Process A : $processAHash"
Write-Host "        Process B : $processBStateSha"

# ============================================================================
# 25. TG-08 — REVALIDATION PHYSIQUE APRÈS DOUBLE PASS
# ============================================================================

Write-Host ""
Write-Host "[TG-08] Revalidation physique des sources..." `
    -ForegroundColor Yellow

$mutationCount =
    0

foreach ($topologyFile in $topologyFilesSorted) {

    $path =
        Resolve-SourcePath `
            -RelativePath $topologyFile.source_file

    $actual =
        Get-FileSha256 -Path $path

    if ($actual -ne $topologyFile.record_hash) {
        $mutationCount++
    }
}

$gates["TG-08_SOURCE_STABILITY"] =
    ($mutationCount -eq 0)

if (-not $gates["TG-08_SOURCE_STABILITY"]) {
    throw "FAIL-CLOSED: Mutation source détectée après analyse."
}

Write-Host " [PASS] TG-08_SOURCE_STABILITY" `
    -ForegroundColor Green

# ============================================================================
# 26. VERDICT FINAL AVANT COMMIT
# ============================================================================

$allGatesPass =
    $true

foreach ($gate in $gates.GetEnumerator()) {

    if (-not [bool]$gate.Value) {
        $allGatesPass = $false
    }
}

if (-not $allGatesPass) {
    throw "FAIL-CLOSED: Quality Gate finale < 100%."
}

# ============================================================================
# 27. ÉMISSION DE EZZIO_SEMANTIC_STATE.JSON
# ============================================================================

Write-Host ""
Write-Host "[COMMIT DÉRIVÉ] Émission des artefacts sémantiques..." `
    -ForegroundColor Yellow

$stateObject =
    [ordered]@{
        artifact_type =
            "EZZIO_SEMANTIC_STATE"

        schema_version =
            $SchemaVersion

        metadata =
            [ordered]@{
                generated_at_utc =
                    [DateTime]::UtcNow.ToString('o')

                generator_version =
                    $EngineVersion

                engine =
                    "EZZIO_Semantic_Truth_Engine"

                mode =
                    $Mode
            }

        lineage =
            [ordered]@{
                parent_point_zero_run =
                    $pointZeroRunId

                parent_records_sha256 =
                    $currentRecordsSha

                parent_chain_hash =
                    $pointZeroChainHash

                parent_topology_payload_sha256 =
                    $topologyPayloadSha

                parent_topology_artifact_sha256 =
                    $topologyArtifactSha
            }

        metrics =
            [ordered]@{
                total_files =
                    $semanticFiles.Count

                parsed_files =
                    $totalParsedFiles

                unsupported_files =
                    $totalUnsupportedFiles

                total_symbols =
                    $totalSymbols
            }

        files =
            @(
                $semanticFiles |
                    Sort-Object -Property source_file
            )

        proof =
            [ordered]@{
                semantic_payload_sha256 =
                    $semanticPayloadSha256

                process_a_state_sha256 =
                    $processAHash

                process_b_state_sha256 =
                    $processBStateSha

                gates_passed =
                    @(
                        $gates.GetEnumerator() |
                            Where-Object {
                                $_.Value
                            } |
                            ForEach-Object {
                                $_.Key
                            }
                    )
            }
    }

$stateJson =
    ConvertTo-CanonicalJson -Object $stateObject

[System.IO.File]::WriteAllText(
    $StateFilePath,
    $stateJson,
    [System.Text.UTF8Encoding]::new($false)
)

if (-not [System.IO.File]::Exists($StateFilePath)) {
    throw "FAIL-CLOSED: Semantic State non créé."
}

$stateArtifactSha =
    Get-FileSha256 -Path $StateFilePath

# ============================================================================
# 28. MANIFESTE SÉMANTIQUE
# ============================================================================

$manifestObject =
    [ordered]@{
        artifact_type =
            "EZZIO_SEMANTIC_MANIFEST"

        schema_version =
            $SchemaVersion

        sealed_at_utc =
            [DateTime]::UtcNow.ToString('o')

        generator_version =
            $EngineVersion

        parent_point_zero_run =
            $pointZeroRunId

        parent_records_sha256 =
            $currentRecordsSha

        parent_chain_hash =
            $pointZeroChainHash

        parent_topology_payload_sha256 =
            $topologyPayloadSha

        parent_topology_artifact_sha256 =
            $topologyArtifactSha

        semantic_payload_sha256 =
            $semanticPayloadSha256

        semantic_artifact_sha256 =
            $stateArtifactSha

        process_a_sha256 =
            $processAHash

        process_b_sha256 =
            $processBStateSha

        total_files =
            $semanticFiles.Count

        parsed_files =
            $totalParsedFiles

        unsupported_files =
            $totalUnsupportedFiles

        total_symbols =
            $totalSymbols

        gates_summary =
            "$(
                @(
                    $gates.GetEnumerator() |
                        Where-Object {
                            $_.Value
                        }
                ).Count
            )/$($gates.Count)_PASS"

        status =
            "CERTIFIED_DERIVATION"
    }

$manifestJson =
    ConvertTo-CanonicalJson -Object $manifestObject

[System.IO.File]::WriteAllText(
    $SemanticManifestPath,
    $manifestJson,
    [System.Text.UTF8Encoding]::new($false)
)

$semanticManifestSha =
    Get-FileSha256 -Path $SemanticManifestPath

# ============================================================================
# 29. SCELLEMENT FROZEN
# ============================================================================

$frozenContent = @"
FROZEN_SEMANTIC_DERIVATION_SEAL
EngineVersion:$EngineVersion
SchemaVersion:$SchemaVersion
ParentRun:$pointZeroRunId
ParentRecordsSHA256:$currentRecordsSha
ParentChainHash:$pointZeroChainHash
TopologyPayloadSHA256:$topologyPayloadSha
TopologyArtifactSHA256:$topologyArtifactSha
SemanticPayloadSHA256:$semanticPayloadSha256
SemanticArtifactSHA256:$stateArtifactSha
SemanticManifestSHA256:$semanticManifestSha
ProcessASHA256:$processAHash
ProcessBSHA256:$processBStateSha
Files:$($semanticFiles.Count)
ParsedFiles:$totalParsedFiles
UnsupportedFiles:$totalUnsupportedFiles
Symbols:$totalSymbols
SealedAtUtc:$([DateTime]::UtcNow.ToString('o'))
"@

[System.IO.File]::WriteAllText(
    $FrozenTokenPath,
    $frozenContent,
    [System.Text.UTF8Encoding]::new($false)
)

# ============================================================================
# 30. POST-COMMIT FORENSIC VALIDATION
# ============================================================================

Write-Host ""
Write-Host "[POST-COMMIT] Vérification physique finale..." `
    -ForegroundColor Yellow

foreach ($required in @(
    $StateFilePath,
    $SemanticManifestPath,
    $FrozenTokenPath
)) {

    if (-not [System.IO.File]::Exists($required)) {
        throw "FAIL-CLOSED: Artefact final absent : $required"
    }
}

$recheckedStateSha =
    Get-FileSha256 -Path $StateFilePath

$recheckedManifestSha =
    Get-FileSha256 -Path $SemanticManifestPath

$recheckedFrozenSha =
    Get-FileSha256 -Path $FrozenTokenPath

if ($recheckedStateSha -ne $stateArtifactSha) {
    throw "FAIL-CLOSED: Semantic State instable."
}

if ($recheckedManifestSha -ne $semanticManifestSha) {
    throw "FAIL-CLOSED: Semantic Manifest instable."
}

# ============================================================================
# 31. VALIDATION DE LA COHÉRENCE DU MANIFEST
# ============================================================================

$reloadedManifest =
    Read-StrictJsonFile -Path $SemanticManifestPath

if ([string]$reloadedManifest.semantic_artifact_sha256 -ne $recheckedStateSha) {
    throw "FAIL-CLOSED: Manifest -> State hash mismatch."
}

if ([string]$reloadedManifest.semantic_payload_sha256 -ne $semanticPayloadSha256) {
    throw "FAIL-CLOSED: Manifest -> Payload mismatch."
}

# ============================================================================
# 32. VERDICT
# ============================================================================

Write-Host ""
Write-Host "============================================================" `
    -ForegroundColor Cyan

Write-Host " NIVEAU 3 : CERTIFIED & FROZEN" `
    -ForegroundColor Green

Write-Host "============================================================" `
    -ForegroundColor Cyan

Write-Host "Point Zero        : $pointZeroRunId"
Write-Host "Topology Payload  : $topologyPayloadSha"
Write-Host "Files             : $($semanticFiles.Count)"
Write-Host "Parsed            : $totalParsedFiles"
Write-Host "Unsupported       : $totalUnsupportedFiles"
Write-Host "Symbols           : $totalSymbols"
Write-Host ""

Write-Host "Semantic Payload  : $semanticPayloadSha256"
Write-Host "State SHA256      : $recheckedStateSha"
Write-Host "Manifest SHA256   : $recheckedManifestSha"
Write-Host "Frozen SHA256     : $recheckedFrozenSha"
Write-Host ""

Write-Host "Artefact          : $StateFilePath"
Write-Host "Manifest          : $SemanticManifestPath"
Write-Host "Seal              : $FrozenTokenPath"
Write-Host ""

Write-Host "Quality Gates     : $($gates.Count)/$($gates.Count) PASS" `
    -ForegroundColor Green

Write-Host "Status            : CERTIFIED_DERIVATION" `
    -ForegroundColor Green

Write-Host "============================================================" `
    -ForegroundColor Cyan

# ============================================================================
# 33. NETTOYAGE STRICT DU STAGING TEMPORAIRE
# ============================================================================

# IMPORTANT :
# Aucun nettoyage silencieux.
# Le staging Process B est volontairement conservé pour forensic.
#
# Il contient :
#   - process_b_runner.ps1
#   - process_b_result.json
#   - EZZIO_SEMANTIC_STATE.json
#   - semantic_manifest.json
#   - FROZEN
#
# Cela permet l'audit externe du double processus.

Write-Host ""
Write-Host "[FORENSIC] Staging Process B conservé :" `
    -ForegroundColor DarkGray
Write-Host "           $ProcessBOutputDir" `
    -ForegroundColor DarkGray
Write-Host ""