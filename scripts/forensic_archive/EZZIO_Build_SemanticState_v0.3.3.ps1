#Requires -Version 7.0

<#
.SYNOPSIS
    E-ZZIO — SEMANTIC TRUTH ENGINE v0.3.3

.DESCRIPTION
    Moteur de dérivation sémantique forensic de niveau 3.

    Principes :

      1. READ-ONLY sur le Point Zero.
      2. FAIL-CLOSED.
      3. Identité physique/logique canonique.
      4. RootPathScanned du manifest = ancre physique officielle.
      5. Aucune supposition ou reconstruction de SourceRoot.
      6. Découverte dynamique de l'environnement forensic.
      7. Validation SHA-256 avant analyse.
      8. Traitement streaming des records.
      9. Pas de chargement massif de semanticRecords en RAM.
     10. Aucun CERTIFIED/FROZEN avant validation post-commit.
     11. Aucun état de succès fondé uniquement sur un booléen déclaratif.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [string]$PointZeroDir = `
        'G:\AI\_forensic\ContentTruth\run_20260820_130134_380',

    [Parameter(Mandatory = $false)]
    [string]$OutputDir = `
        'G:\AI\_forensic\SelfBody\semantic\run_20260820_130134_380',

    [Parameter(Mandatory = $false)]
    [switch]$Force,

    [Parameter(Mandatory = $false)]
    [switch]$PauseOnExit
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$EngineVersion = '0.3.3'
$SchemaVersion = '1.0'

$script:Fatal = $false
$script:LogPath = $null

# ============================================================================
# CONSOLE
# ============================================================================

function Write-Section {
    param(
        [Parameter(Mandatory)]
        [string]$Title
    )

    Write-Host ''
    Write-Host '==============================================================================' `
        -ForegroundColor Cyan
    Write-Host " $Title" -ForegroundColor Cyan
    Write-Host '==============================================================================' `
        -ForegroundColor Cyan
}

function Write-Pass {
    param(
        [Parameter(Mandatory)]
        [string]$Message
    )

    Write-Host "[PASS] $Message" -ForegroundColor Green
}

function Write-Fail {
    param(
        [Parameter(Mandatory)]
        [string]$Message
    )

    Write-Host "[FAIL] $Message" -ForegroundColor Red
}

function Write-Info {
    param(
        [Parameter(Mandatory)]
        [string]$Message
    )

    Write-Host $Message -ForegroundColor DarkGray
}

function Write-Log {
    param(
        [Parameter(Mandatory)]
        [string]$Message,

        [ValidateSet('INFO','PASS','FAIL','WARN')]
        [string]$Level = 'INFO'
    )

    $line = '[{0}] [{1}] {2}' -f `
        [DateTime]::UtcNow.ToString('o'),
        $Level,
        $Message

    if ($script:LogPath) {

        [System.IO.File]::AppendAllText(
            $script:LogPath,
            $line + [Environment]::NewLine,
            [System.Text.UTF8Encoding]::new($false)
        )
    }
}

# ============================================================================
# FAIL-CLOSED
# ============================================================================

function Fail-Closed {
    param(
        [Parameter(Mandatory)]
        [string]$Message,

        [System.Exception]$Exception
    )

    $script:Fatal = $true

    Write-Host ''
    Write-Host '!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!' `
        -ForegroundColor Red
    Write-Host ' E-ZZIO — FAIL-CLOSED' -ForegroundColor Red
    Write-Host '!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!' `
        -ForegroundColor Red
    Write-Host ''

    Write-Host "ERROR : $Message" -ForegroundColor Red

    if ($Exception) {

        Write-Host `
            "TYPE  : $($Exception.GetType().FullName)" `
            -ForegroundColor DarkRed

        Write-Host `
            "DETAIL: $($Exception.Message)" `
            -ForegroundColor DarkRed
    }

    Write-Host ''
    Write-Host 'AUCUN CERTIFIED/FROZEN ÉMIS.' -ForegroundColor Yellow
    Write-Host 'POINT ZERO NON MODIFIÉ.' -ForegroundColor Yellow
    Write-Host ''

    try {
        Write-Log -Level FAIL -Message $Message

        if ($Exception) {
            Write-Log `
                -Level FAIL `
                -Message "$($Exception.GetType().FullName): $($Exception.Message)"
        }
    }
    catch {
        Write-Host `
            '[WARN] Impossible d''écrire le log de FAIL-CLOSED.' `
            -ForegroundColor Yellow
    }

    return $false
}

# ============================================================================
# SHA-256
# ============================================================================

function Get-FileSha256 {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    if (-not [System.IO.File]::Exists($Path)) {
        throw "Fichier absent : $Path"
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

    return `
        [System.BitConverter]::ToString($hash).
        Replace('-', '').
        ToLowerInvariant()
}

# ============================================================================
# CHEMIN CANONIQUE
# ============================================================================

function Resolve-CanonicalPath {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    $full = [System.IO.Path]::GetFullPath($Path)

    return $full.TrimEnd('\','/')
}

# ============================================================================
# IDENTITÉ POINT ZERO
# ============================================================================

function Get-CanonicalRunId {
    param(
        [Parameter(Mandatory)]
        [string]$PhysicalDir,

        [Parameter(Mandatory)]
        [string]$ManifestRunId
    )

    $leaf = Split-Path -Leaf $PhysicalDir

    if (-not $leaf.StartsWith(
        'run_',
        [System.StringComparison]::Ordinal
    )) {

        throw `
            "Le dossier PointZero '$leaf' ne respecte pas le préfixe canonique 'run_'."
    }

    $normalized = $leaf.Substring(4)

    if ($normalized -notmatch '^\d{8}_\d{6}_\d{3}$') {

        throw `
            "RunId physique malformé : '$normalized'."
    }

    if ($ManifestRunId -notmatch '^\d{8}_\d{6}_\d{3}$') {

        throw `
            "RunId manifest malformé : '$ManifestRunId'."
    }

    if ($normalized -cne $ManifestRunId) {

        throw @"
RUPTURE D'IDENTITÉ CANONIQUE

Manifest : $ManifestRunId
Physique : $normalized

La relation logique/physique ne peut pas être certifiée.
"@
    }

    return $normalized
}

# ============================================================================
# FRONTIÈRES
# ============================================================================

function Test-PathInside {
    param(
        [Parameter(Mandatory)]
        [string]$Child,

        [Parameter(Mandatory)]
        [string]$Parent
    )

    $childFull = Resolve-CanonicalPath $Child
    $parentFull = Resolve-CanonicalPath $Parent

    $childPrefix = $parentFull + '\'

    return (
        $childFull.Equals(
            $parentFull,
            [System.StringComparison]::OrdinalIgnoreCase
        ) -or
        $childFull.StartsWith(
            $childPrefix,
            [System.StringComparison]::OrdinalIgnoreCase
        )
    )
}

# ============================================================================
# TOPOLOGIE
# ============================================================================

function Find-TopologyArtifact {
    param(
        [Parameter(Mandatory)]
        [string]$ForensicRoot,

        [Parameter(Mandatory)]
        [string]$RunId,

        [Parameter(Mandatory)]
        [string]$OutputDir
    )

    $expectedName = 'EZZIO_TOPOLOGY_STATE.json'

    $candidatePaths =
        [System.Collections.Generic.List[string]]::new()

    # ------------------------------------------------------------------------
    # CANDIDATS DÉTERMINISTES
    # ------------------------------------------------------------------------

    $candidatePaths.Add(
        (Join-Path `
            $ForensicRoot `
            "SelfBody\topology\run_$RunId\$expectedName")
    )

    $candidatePaths.Add(
        (Join-Path `
            $ForensicRoot `
            "SelfBody\semantic\topology\run_$RunId\$expectedName")
    )

    $candidatePaths.Add(
        (Join-Path `
            $ForensicRoot `
            "topology\run_$RunId\$expectedName")
    )

    $outputParent = Split-Path $OutputDir -Parent

    $candidatePaths.Add(
        (Join-Path `
            $outputParent `
            "..\topology\run_$RunId\$expectedName")
    )

    # ------------------------------------------------------------------------
    # VÉRIFICATION
    # ------------------------------------------------------------------------

    foreach ($candidate in $candidatePaths) {

        try {
            $resolved = [System.IO.Path]::GetFullPath($candidate)
        }
        catch {
            continue
        }

        if ([System.IO.File]::Exists($resolved)) {
            return $resolved
        }
    }

    # ------------------------------------------------------------------------
    # DÉCOUVERTE FORENSIC CONTRÔLÉE
    # ------------------------------------------------------------------------

    if ([System.IO.Directory]::Exists($ForensicRoot)) {

        $matches = @(
            Get-ChildItem `
                -LiteralPath $ForensicRoot `
                -Filter $expectedName `
                -File `
                -Recurse `
                -ErrorAction SilentlyContinue |
            Where-Object {
                $_.FullName -match `
                    "\\run_$([regex]::Escape($RunId))\\$([regex]::Escape($expectedName))$"
            }
        )

        if ($matches.Count -eq 1) {
            return $matches[0].FullName
        }

        if ($matches.Count -gt 1) {

            throw `
                "Ambiguïté topologique : plusieurs EZZIO_TOPOLOGY_STATE.json correspondent au RunId $RunId."
        }
    }

    return $null
}

# ============================================================================
# JSON STRICT
# ============================================================================

function Read-JsonStrict {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    if (-not [System.IO.File]::Exists($Path)) {
        throw "JSON absent : $Path"
    }

    $text = [System.IO.File]::ReadAllText(
        $Path,
        [System.Text.Encoding]::UTF8
    )

    if ([string]::IsNullOrWhiteSpace($text)) {
        throw "JSON vide : $Path"
    }

    return (
        $text |
        ConvertFrom-Json -ErrorAction Stop
    )
}

# ============================================================================
# PRÉPARATION
# ============================================================================

$resolvedPointZero = Resolve-CanonicalPath $PointZeroDir
$resolvedOutput = Resolve-CanonicalPath $OutputDir

$forensicRoot = Resolve-CanonicalPath (
    Split-Path (
        Split-Path $resolvedPointZero -Parent
    ) -Parent
)

$OutputStatePath = Join-Path `
    $resolvedOutput `
    'EZZIO_SEMANTIC_STATE.json'

$OutputManifestPath = Join-Path `
    $resolvedOutput `
    'semantic_manifest.json'

$OutputFrozenPath = Join-Path `
    $resolvedOutput `
    'FROZEN'

$OutputPayloadPath = Join-Path `
    $resolvedOutput `
    'semantic_payload.jsonl'

$OutputLogPath = Join-Path `
    $resolvedOutput `
    'semantic_engine.log'

# ============================================================================
# HEADER
# ============================================================================

Write-Section `
    "E-ZZIO — SEMANTIC TRUTH ENGINE v$EngineVersion"

Write-Host "Mode              : NIVEAU 3 / FORENSIC"
Write-Host "PointZeroDir      : $resolvedPointZero"
Write-Host "OutputDir         : $resolvedOutput"
Write-Host "ForensicRoot      : $forensicRoot"
Write-Host "Engine             : $EngineVersion"
Write-Host ''

# ============================================================================
# INITIALISATION
# ============================================================================

try {

    # ------------------------------------------------------------------------
    # OUTPUT
    # ------------------------------------------------------------------------

    if (-not [System.IO.Directory]::Exists($resolvedOutput)) {

        [System.IO.Directory]::CreateDirectory(
            $resolvedOutput
        ) | Out-Null
    }

    $script:LogPath = $OutputLogPath

    Write-Log `
        -Level INFO `
        -Message "Semantic Truth Engine $EngineVersion démarré."

    Write-Log `
        -Level INFO `
        -Message "PointZero=$resolvedPointZero"

    Write-Log `
        -Level INFO `
        -Message "Output=$resolvedOutput"

    # ========================================================================
    # SG-00
    # ========================================================================

    Write-Section "SG-00 — ENVIRONMENT PREFLIGHT"

    if (-not [System.IO.Directory]::Exists($resolvedPointZero)) {
        throw "PointZeroDir inexistant : $resolvedPointZero"
    }

    if (-not [System.IO.Directory]::Exists($forensicRoot)) {
        throw "Racine forensic inexistante : $forensicRoot"
    }

    if (
        Test-PathInside `
            -Child $resolvedOutput `
            -Parent $resolvedPointZero
    ) {

        throw `
            "OutputDir situé à l'intérieur du PointZero."
    }

    Write-Pass "PointZero existe"
    Write-Pass "ForensicRoot existe"
    Write-Pass "Output séparé du PointZero"

    # ========================================================================
    # SG-01 — IDENTITÉ + ROOTPATHSCANNED
    # ========================================================================

    Write-Section "SG-01 — IDENTITÉ CANONIQUE + ROOTPATHSCANNED"

    $ManifestPath = Join-Path `
        $resolvedPointZero `
        'run_manifest.json'

    $RecordsPath = Join-Path `
        $resolvedPointZero `
        'records.jsonl'

    if (-not [System.IO.File]::Exists($ManifestPath)) {
        throw "run_manifest.json introuvable."
    }

    if (-not [System.IO.File]::Exists($RecordsPath)) {
        throw "records.jsonl introuvable."
    }

    $manifest = Read-JsonStrict -Path $ManifestPath

    # ------------------------------------------------------------------------
    # RunId
    # ------------------------------------------------------------------------

    $manifestRunId = [string]$manifest.RunId

    if ([string]::IsNullOrWhiteSpace($manifestRunId)) {
        throw "RunId absent du manifest."
    }

    $canonicalRunId = Get-CanonicalRunId `
        -PhysicalDir $resolvedPointZero `
        -ManifestRunId $manifestRunId

    Write-Pass `
        "Identité canonique : $canonicalRunId"

    # ------------------------------------------------------------------------
    # RootPathScanned
    #
    # CONTRAT RÉEL DU MANIFEST.
    #
    # Nous ne cherchons PAS SourceRoot.
    # Nous ne reconstruisons PAS le chemin.
    # Nous utilisons uniquement le champ explicitement présent.
    # ------------------------------------------------------------------------

    $sourceRoot = $null

    if (
        $manifest.PSObject.Properties.Name `
            -contains 'RootPathScanned'
    ) {

        $sourceRoot = [string]$manifest.RootPathScanned
    }

    if ([string]::IsNullOrWhiteSpace($sourceRoot)) {

        throw @"
ROOTPATHSCANNED ABSENT DU MANIFEST

Le champ contractuel RootPathScanned est absent ou vide.

Le moteur refuse :
  - de deviner le SourceRoot ;
  - de reconstruire un chemin ;
  - d'utiliser le répertoire courant ;
  - d'utiliser le PointZero comme source physique.

FAIL-CLOSED.
"@
    }

    if (
        -not [System.IO.Directory]::Exists($sourceRoot)
    ) {

        throw @"
ROOTPATHSCANNED INACCESSIBLE

RootPathScanned :
$sourceRoot

Le chemin est déclaré par le manifest mais n'existe pas
ou n'est pas accessible.

FAIL-CLOSED.
"@
    }

    $sourceRoot = Resolve-CanonicalPath $sourceRoot

    Write-Pass "RootPathScanned présent dans le manifest"
    Write-Host `
        "Source Root live : $sourceRoot" `
        -ForegroundColor DarkGray

    # ------------------------------------------------------------------------
    # Vérification supplémentaire :
    # RootPathScanned ne doit pas être le PointZero.
    # ------------------------------------------------------------------------

    if (
        $sourceRoot.Equals(
            $resolvedPointZero,
            [System.StringComparison]::OrdinalIgnoreCase
        )
    ) {

        throw @"
CONTRAT PHYSIQUE INVALIDE

RootPathScanned pointe directement vers le PointZero.

Le moteur exige une séparation entre :
  - la preuve immuable du PointZero ;
  - la matière physique source.

FAIL-CLOSED.
"@
    }

    # ------------------------------------------------------------------------
    # HASH DES PREUVES POINT ZERO
    # ------------------------------------------------------------------------

    $manifestSha = Get-FileSha256 $ManifestPath
    $recordsSha = Get-FileSha256 $RecordsPath

    Write-Host "Manifest SHA256 : $manifestSha"
    Write-Host "Records SHA256  : $recordsSha"

    Write-Log `
        -Level PASS `
        -Message "CanonicalRunId=$canonicalRunId"

    Write-Log `
        -Level PASS `
        -Message "RootPathScanned=$sourceRoot"

    # ========================================================================
    # SG-02 — TOPOLOGIE
    # ========================================================================

    Write-Section "SG-02 — DISCOVERY TOPOLOGIQUE"

    Write-Host `
        "Recherche de EZZIO_TOPOLOGY_STATE.json..." `
        -ForegroundColor Yellow

    $topologyStatePath = Find-TopologyArtifact `
        -ForensicRoot $forensicRoot `
        -RunId $canonicalRunId `
        -OutputDir $resolvedOutput

    if (-not $topologyStatePath) {

        throw @"
Artefact topologique introuvable.

RunId : $canonicalRunId

Le moteur refuse toute supposition de chemin.
Aucun artefact sémantique ne sera certifié.
"@
    }

    $topologyStatePath = Resolve-CanonicalPath `
        $topologyStatePath

    Write-Pass "Topologie découverte automatiquement"

    Write-Host `
        "Topology : $topologyStatePath"

    $topologyState = Read-JsonStrict `
        -Path $topologyStatePath

    $topologyRunId = `
        [string]$topologyState.lineage.parent_point_zero_run

    $topologyRecordsSha = `
        [string]$topologyState.lineage.parent_records_sha256

    if ($topologyRunId -cne $canonicalRunId) {

        throw `
            "Topologie RunId incohérent : $topologyRunId != $canonicalRunId"
    }

    if ($topologyRecordsSha -cne $recordsSha) {

        throw `
            "Topologie/records SHA-256 incohérents."
    }

    $topologyPayloadSha = `
        [string]$topologyState.proof.topology_payload_sha256

    if ([string]::IsNullOrWhiteSpace($topologyPayloadSha)) {

        throw `
            "topology_payload_sha256 absent."
    }

    $topologyArtifactSha = `
        Get-FileSha256 $topologyStatePath

    Write-Pass `
        "SG-02_TOPOLOGY_LINEAGE_VALIDATED"

    # ========================================================================
    # SG-03 — ÉTAT DE SORTIE
    # ========================================================================

    Write-Section "SG-03 — ÉTAT DE SORTIE"

    if (
        [System.IO.File]::Exists($OutputFrozenPath) `
        -and -not $Force
    ) {

        throw @"
Une dérivation FROZEN existe déjà.

Output :
$resolvedOutput

Utiliser -Force uniquement pour une nouvelle dérivation explicite.
"@
    }

    if (
        $Force `
        -and [System.IO.Directory]::Exists($resolvedOutput)
    ) {

        foreach ($old in @(
            $OutputStatePath,
            $OutputManifestPath,
            $OutputFrozenPath,
            $OutputPayloadPath
        )) {

            if ([System.IO.File]::Exists($old)) {

                Remove-Item `
                    -LiteralPath $old `
                    -Force
            }
        }

        Write-Info `
            "Anciens artefacts sémantiques supprimés sous -Force."
    }

    Write-Pass "Sortie disponible"

    # ========================================================================
    # SG-04 — EXTRACTION STREAMING
    # ========================================================================

    Write-Section `
        "SG-04 — EXTRACTION SÉMANTIQUE STREAMING"

    $PayloadWriter = $null
    $Reader = $null

    $parsedCount = 0
    $unsupportedCount = 0
    $errorCount = 0
    $processedCount = 0
    $totalSymbols = 0

    $PayloadWriter = [System.IO.StreamWriter]::new(
        $OutputPayloadPath,
        $false,
        [System.Text.UTF8Encoding]::new($false)
    )

    $Reader = [System.IO.StreamReader]::new(
        $RecordsPath,
        [System.Text.UTF8Encoding]::new($false, $true),
        $true,
        1048576
    )

    try {

        while (-not $Reader.EndOfStream) {

            $line = $Reader.ReadLine()

            if ([string]::IsNullOrWhiteSpace($line)) {
                continue
            }

            $line = $line.Trim().Trim([char]0xFEFF)

            if ([string]::IsNullOrWhiteSpace($line)) {
                continue
            }

            $processedCount++

            # ----------------------------------------------------------------
            # PARSE RECORD
            # ----------------------------------------------------------------

            try {

                $rec = $line |
                    ConvertFrom-Json -ErrorAction Stop
            }
            catch {

                throw `
                    "records.jsonl invalide à l'enregistrement $processedCount : $($_.Exception.Message)"
            }

            $relPath = [string]$rec.RelativePath
            $recordHash = [string]$rec.Hash

            if ([string]::IsNullOrWhiteSpace($relPath)) {

                throw `
                    "RelativePath vide à l'enregistrement $processedCount."
            }

            if ([string]::IsNullOrWhiteSpace($recordHash)) {

                throw `
                    "Hash vide pour '$relPath'."
            }

            # ----------------------------------------------------------------
            # RÉSOLUTION PHYSIQUE SUR RootPathScanned
            # ----------------------------------------------------------------

            try {

                $physicalPath = `
                    [System.IO.Path]::GetFullPath(
                        (Join-Path $sourceRoot $relPath)
                    )
            }
            catch {

                throw @"
RÉSOLUTION PHYSIQUE IMPOSSIBLE

RelativePath : $relPath
RootPathScanned : $sourceRoot

$($_.Exception.Message)

FAIL-CLOSED.
"@
            }

            # ----------------------------------------------------------------
            # ANTI PATH TRAVERSAL
            #
            # La frontière physique est RootPathScanned.
            # ----------------------------------------------------------------

            if (
                -not (
                    Test-PathInside `
                        -Child $physicalPath `
                        -Parent $sourceRoot
                )
            ) {

                throw @"
PATH TRAVERSAL DÉTECTÉ

RelativePath : $relPath
ResolvedPath : $physicalPath
RootPath     : $sourceRoot

Le record tente de sortir de RootPathScanned.
FAIL-CLOSED.
"@
            }

            # ----------------------------------------------------------------
            # EXTENSION
            # ----------------------------------------------------------------

            $ext = `
                [System.IO.Path]::GetExtension(
                    $relPath
                ).ToLowerInvariant()

            if (
                $ext -notin @(
                    '.ps1',
                    '.py',
                    '.json',
                    '.gd',
                    '.lua'
                )
            ) {

                $unsupportedCount++
                continue
            }

            # ----------------------------------------------------------------
            # PRÉSENCE PHYSIQUE
            # ----------------------------------------------------------------

            if (
                -not [System.IO.File]::Exists($physicalPath)
            ) {

                throw @"
RÉFÉRENCE PHYSIQUE ABSENTE

RelativePath : $relPath
PhysicalPath : $physicalPath
RootPath     : $sourceRoot
RecordHash   : $recordHash

Le record affirme l'existence d'un artefact qui n'est plus présent
dans RootPathScanned.

FAIL-CLOSED.
"@
            }

            # ----------------------------------------------------------------
            # HASH PHYSIQUE
            # ----------------------------------------------------------------

            $actualSha256 = `
                Get-FileSha256 $physicalPath

            if (
                $actualSha256 -cne `
                    $recordHash.ToLowerInvariant()
            ) {

                throw @"
MUTATION PHYSIQUE DÉTECTÉE

File       : $relPath
RootPath   : $sourceRoot
Expected   : $recordHash
Actual     : $actualSha256

FAIL-CLOSED.
"@
            }

            # ----------------------------------------------------------------
            # SYMBOLS
            # ----------------------------------------------------------------

            $symbols =
                [System.Collections.Generic.List[object]]::new()

            $parserStatus = 'UNSUPPORTED'

            try {

                switch ($ext) {

                    # --------------------------------------------------------
                    # JSON
                    # --------------------------------------------------------

                    '.json' {

                        $jsonText =
                            [System.IO.File]::ReadAllText(
                                $physicalPath,
                                [System.Text.Encoding]::UTF8
                            )

                        $null =
                            $jsonText |
                            ConvertFrom-Json -ErrorAction Stop

                        $parserStatus = 'PARSED'

                        $symbols.Add(
                            [ordered]@{
                                type = 'document'
                                name = 'json_root'
                            }
                        )
                    }

                    # --------------------------------------------------------
                    # POWERSHELL
                    # --------------------------------------------------------

                    '.ps1' {

                        $tokens = $null
                        $errors = $null

                        $ast =
                            [System.Management.Automation.Language.Parser]::ParseFile(
                                $physicalPath,
                                [ref]$tokens,
                                [ref]$errors
                            )

                        if ($errors.Count -eq 0) {

                            $parserStatus = 'PARSED'

                            $functions =
                                $ast.FindAll(
                                    {
                                        param($node)

                                        $node -is `
                                            [System.Management.Automation.Language.FunctionDefinitionAst]
                                    },
                                    $true
                                )

                            foreach ($function in $functions) {

                                $symbols.Add(
                                    [ordered]@{
                                        type = 'function'
                                        name = $function.Name
                                    }
                                )
                            }
                        }
                        else {

                            $parserStatus = 'ERROR'
                            $errorCount++

                            throw `
                                "PowerShell AST invalide."
                        }
                    }

                    # --------------------------------------------------------
                    # PYTHON
                    # --------------------------------------------------------

                    '.py' {

                        # v0.3.x ne prétend toujours PAS faire
                        # un AST Python complet.

                        $parserStatus = 'PARTIAL_PYTHON'

                        $moduleName =
                            [System.IO.Path]::GetFileNameWithoutExtension(
                                $relPath
                            )

                        $symbols.Add(
                            [ordered]@{
                                type = 'module'
                                name = $moduleName
                            }
                        )
                    }

                    # --------------------------------------------------------
                    # GODOT
                    # --------------------------------------------------------

                    '.gd' {

                        $parserStatus = 'UNSUPPORTED_GD'
                    }

                    # --------------------------------------------------------
                    # LUA
                    # --------------------------------------------------------

                    '.lua' {

                        $parserStatus = 'UNSUPPORTED_LUA'
                    }
                }

            }
            catch {

                if ($parserStatus -eq 'ERROR') {
                    throw
                }

                $parserStatus = 'ERROR'
                $errorCount++

                throw
            }

            if (
                $parserStatus -eq 'PARSED' `
                -or
                $parserStatus -eq 'PARTIAL_PYTHON'
            ) {

                $parsedCount++
            }

            $totalSymbols += $symbols.Count

            # ----------------------------------------------------------------
            # ÉMISSION STREAMING
            # ----------------------------------------------------------------

            $semanticRecord = [ordered]@{

                source_file =
                    $relPath

                parent_point_zero_run =
                    $canonicalRunId

                parent_record_hash =
                    $recordHash

                physical_source_root =
                    $sourceRoot

                physical_path =
                    $physicalPath

                parser_status =
                    $parserStatus

                symbols =
                    @($symbols)
            }

            $semanticJson =
                $semanticRecord |
                ConvertTo-Json `
                    -Depth 20 `
                    -Compress

            $PayloadWriter.WriteLine($semanticJson)

            # ----------------------------------------------------------------
            # PROGRESSION
            # ----------------------------------------------------------------

            if (($processedCount % 1000) -eq 0) {

                Write-Host (
                    "Records: {0:N0} | Analysés: {1:N0} | Symboles: {2:N0}" -f
                    $processedCount,
                    $parsedCount,
                    $totalSymbols
                ) -ForegroundColor DarkGray

                $PayloadWriter.Flush()
            }
        }
    }
    finally {

        if ($Reader) {
            $Reader.Dispose()
        }

        if ($PayloadWriter) {

            $PayloadWriter.Flush()
            $PayloadWriter.Dispose()
        }
    }

    Write-Host ''
    Write-Pass "Streaming terminé"

    Write-Host "Records lus      : $processedCount"
    Write-Host "Fichiers analysés: $parsedCount"
    Write-Host "Unsupported      : $unsupportedCount"
    Write-Host "Symboles         : $totalSymbols"

    # ========================================================================
    # SG-05 — QUALITY GATES
    # ========================================================================

    Write-Section "SG-05 — QUALITY GATES"

    $gates =
        [ordered]@{}

    $gates['SG-05_BOUNDARIES'] = (
        -not (
            Test-PathInside `
                -Child $resolvedOutput `
                -Parent $resolvedPointZero
        )
    )

    $gates['SG-05_IDENTITY'] = (
        -not [string]::IsNullOrWhiteSpace($canonicalRunId) `
        -and
        $canonicalRunId -eq $manifestRunId
    )

    $gates['SG-05_ROOTPATHSCANNED'] = (
        -not [string]::IsNullOrWhiteSpace($sourceRoot) `
        -and
        [System.IO.Directory]::Exists($sourceRoot)
    )

    $gates['SG-05_TOPOLOGY'] = (
        $topologyRunId -eq $canonicalRunId `
        -and
        $topologyRecordsSha -eq $recordsSha
    )

    $gates['SG-05_STREAMING'] = (
        $processedCount -gt 0 `
        -and
        [System.IO.File]::Exists($OutputPayloadPath)
    )

    $gates['SG-05_PHYSICAL_PARITY'] = (
        $errorCount -eq 0
    )

    $gates['SG-05_PROVENANCE'] = (
        $parsedCount -gt 0
    )

    foreach ($gate in $gates.GetEnumerator()) {

        if ([bool]$gate.Value) {
            Write-Pass $gate.Key
        }
        else {
            Write-Fail $gate.Key
        }
    }

    $allGatesPass = $true

    foreach ($gate in $gates.GetEnumerator()) {

        if (-not [bool]$gate.Value) {

            $allGatesPass = $false
        }
    }

    if (-not $allGatesPass) {

        throw `
            'Une ou plusieurs Quality Gates ont échoué.'
    }

    # ========================================================================
    # SG-06 — HASH PAYLOAD
    # ========================================================================

    Write-Section "SG-06 — PAYLOAD FORENSIC"

    $payloadSha256 =
        Get-FileSha256 $OutputPayloadPath

    Write-Host `
        "Semantic Payload SHA256 : $payloadSha256"

    # ========================================================================
    # SG-07 — CONSTRUCTION STATE
    # ========================================================================

    Write-Section "SG-07 — CONSTRUCTION STATE"

    $stateObj = [ordered]@{

        artifact_type =
            'EZZIO_SEMANTIC_STATE'

        schema_version =
            $SchemaVersion

        metadata = [ordered]@{

            generated_at_utc =
                [DateTime]::UtcNow.ToString('o')

            generator_version =
                $EngineVersion

            engine =
                'EZZIO_Semantic_Truth_Engine'
        }

        lineage = [ordered]@{

            parent_point_zero_run =
                $canonicalRunId

            parent_manifest_sha256 =
                $manifestSha

            parent_records_sha256 =
                $recordsSha

            parent_root_path_scanned =
                $sourceRoot

            parent_topology_payload_sha =
                $topologyPayloadSha

            parent_topology_artifact_sha256 =
                $topologyArtifactSha
        }

        semantic_payload = [ordered]@{

            format =
                'JSONL'

            path =
                $OutputPayloadPath

            sha256 =
                $payloadSha256
        }

        statistics = [ordered]@{

            records_read =
                $processedCount

            files_analyzed =
                $parsedCount

            unsupported =
                $unsupportedCount

            errors =
                $errorCount

            symbols_extracted =
                $totalSymbols
        }

        proof = [ordered]@{

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
        $stateObj |
        ConvertTo-Json -Depth 30

    [System.IO.File]::WriteAllText(
        $OutputStatePath,
        $stateJson,
        [System.Text.UTF8Encoding]::new($false)
    )

    $stateSha256 =
        Get-FileSha256 $OutputStatePath

    Write-Pass `
        "EZZIO_SEMANTIC_STATE.json écrit"

    Write-Host `
        "State SHA256 : $stateSha256"

    # ========================================================================
    # SG-08 — SEMANTIC MANIFEST
    # ========================================================================

    Write-Section "SG-08 — SEMANTIC MANIFEST"

    $manifestObj = [ordered]@{

        artifact_type =
            'EZZIO_SEMANTIC_MANIFEST'

        schema_version =
            $SchemaVersion

        engine_version =
            $EngineVersion

        parent_point_zero_run =
            $canonicalRunId

        parent_manifest_sha256 =
            $manifestSha

        parent_records_sha256 =
            $recordsSha

        parent_root_path_scanned =
            $sourceRoot

        parent_topology_payload_sha256 =
            $topologyPayloadSha

        parent_topology_artifact_sha256 =
            $topologyArtifactSha

        semantic_payload_sha256 =
            $payloadSha256

        semantic_state_sha256 =
            $stateSha256

        statistics = [ordered]@{

            records_read =
                $processedCount

            files_analyzed =
                $parsedCount

            unsupported =
                $unsupportedCount

            errors =
                $errorCount

            symbols_extracted =
                $totalSymbols
        }

        status =
            'VALIDATED_SEMANTIC_DERIVATION'

        sealed_at_utc =
            [DateTime]::UtcNow.ToString('o')
    }

    $manifestJson =
        $manifestObj |
        ConvertTo-Json -Depth 20

    [System.IO.File]::WriteAllText(
        $OutputManifestPath,
        $manifestJson,
        [System.Text.UTF8Encoding]::new($false)
    )

    $semanticManifestSha =
        Get-FileSha256 $OutputManifestPath

    Write-Pass `
        "semantic_manifest.json écrit"

    # ========================================================================
    # SG-09 — POST COMMIT FORENSIC
    # ========================================================================

    Write-Section "SG-09 — POST-COMMIT FORENSIC"

    foreach ($required in @(
        $OutputPayloadPath,
        $OutputStatePath,
        $OutputManifestPath
    )) {

        if (
            -not [System.IO.File]::Exists($required)
        ) {

            throw `
                "Artefact final absent : $required"
        }

        Write-Pass `
            ([System.IO.Path]::GetFileName($required))
    }

    $recheckPayloadSha =
        Get-FileSha256 $OutputPayloadPath

    $recheckStateSha =
        Get-FileSha256 $OutputStatePath

    $recheckManifestSha =
        Get-FileSha256 $OutputManifestPath

    if ($recheckPayloadSha -cne $payloadSha256) {

        throw `
            'Payload SHA-256 instable après commit.'
    }

    if ($recheckStateSha -cne $stateSha256) {

        throw `
            'State SHA-256 instable après commit.'
    }

    if ($recheckManifestSha -cne $semanticManifestSha) {

        throw `
            'Manifest SHA-256 instable après commit.'
    }

    Write-Pass 'Payload SHA-256 stable'
    Write-Pass 'State SHA-256 stable'
    Write-Pass 'Manifest SHA-256 stable'

    # ========================================================================
    # SG-10 — FROZEN SEAL
    # ========================================================================

    Write-Section "SG-10 — FROZEN SEAL"

    $frozenContent = @"
EZZIO_FROZEN_SEMANTIC_DERIVATION
EngineVersion:$EngineVersion
SchemaVersion:$SchemaVersion

ParentPointZero:$canonicalRunId
ParentManifestSHA256:$manifestSha
ParentRecordsSHA256:$recordsSha

RootPathScanned:$sourceRoot

ParentTopologyPayloadSHA256:$topologyPayloadSha
ParentTopologyArtifactSHA256:$topologyArtifactSha

SemanticPayloadSHA256:$payloadSha256
SemanticStateSHA256:$stateSha256
SemanticManifestSHA256:$semanticManifestSha

RecordsRead:$processedCount
FilesAnalyzed:$parsedCount
Unsupported:$unsupportedCount
Errors:$errorCount
Symbols:$totalSymbols

SealedAtUtc:$([DateTime]::UtcNow.ToString('o'))
"@

    [System.IO.File]::WriteAllText(
        $OutputFrozenPath,
        $frozenContent,
        [System.Text.UTF8Encoding]::new($false)
    )

    $frozenSha256 =
        Get-FileSha256 $OutputFrozenPath

    Write-Pass 'FROZEN seal écrit'

    # ========================================================================
    # SG-11 — FROZEN POST-SEAL VALIDATION
    # ========================================================================

    Write-Section "SG-11 — FROZEN POST-SEAL VALIDATION"

    if (
        -not [System.IO.File]::Exists($OutputFrozenPath)
    ) {

        throw `
            'FROZEN absent après création.'
    }

    $recheckFrozenSha =
        Get-FileSha256 $OutputFrozenPath

    if ($recheckFrozenSha -cne $frozenSha256) {

        throw `
            'FROZEN SHA-256 instable après scellement.'
    }

    Write-Pass 'FROZEN SHA-256 stable'

    # ========================================================================
    # FINAL
    # ========================================================================

    Write-Section `
        "E-ZZIO — NIVEAU 3 : CERTIFIED & FROZEN"

    Write-Host "Point Zero       : $canonicalRunId"
    Write-Host "RootPathScanned  : $sourceRoot"
    Write-Host "Records lus      : $processedCount"
    Write-Host "Fichiers analysés: $parsedCount"
    Write-Host "Unsupported      : $unsupportedCount"
    Write-Host "Erreurs          : $errorCount"
    Write-Host "Symboles         : $totalSymbols"
    Write-Host ''

    Write-Host "Manifest SHA256  : $manifestSha"
    Write-Host "Records SHA256   : $recordsSha"
    Write-Host "Topology SHA256  : $topologyArtifactSha"
    Write-Host "Payload SHA256   : $payloadSha256"
    Write-Host "State SHA256     : $stateSha256"
    Write-Host "Semantic Manifest: $semanticManifestSha"
    Write-Host "Frozen SHA256    : $frozenSha256"
    Write-Host ''

    Write-Host "Payload          : $OutputPayloadPath"
    Write-Host "State            : $OutputStatePath"
    Write-Host "Manifest         : $OutputManifestPath"
    Write-Host "Frozen           : $OutputFrozenPath"
    Write-Host "Log              : $script:LogPath"
    Write-Host ''

    Write-Host `
        '==============================================================================' `
        -ForegroundColor Green

    Write-Host `
        ' ENVIRONMENT / TOPOLOGY / SEMANTIC TRUTH : VALIDATED' `
        -ForegroundColor Green

    Write-Host `
        ' CERTIFIED : TRUE' `
        -ForegroundColor Green

    Write-Host `
        ' FROZEN    : TRUE' `
        -ForegroundColor Green

    Write-Host `
        '==============================================================================' `
        -ForegroundColor Green

    Write-Log `
        -Level PASS `
        -Message `
            'Semantic Truth Derivation certifiée et frozen.'

}
catch {

    Fail-Closed `
        -Message 'Échec fatal du Semantic Truth Engine.' `
        -Exception $_.Exception

    Write-Host ''
    Write-Host `
        'Le moteur s''est arrêté proprement.' `
        -ForegroundColor Yellow

    Write-Host `
        'Le Point Zero n''a pas été modifié.' `
        -ForegroundColor Yellow

    Write-Host ''

    if ($PauseOnExit) {
        Read-Host 'Appuyez sur Entrée pour fermer'
    }

    exit 1
}

if ($PauseOnExit) {

    Write-Host ''
    Read-Host 'Appuyez sur Entrée pour fermer'
}

exit 0
