```powershell
# ==============================================================================
# E-ZZIO FULL REUSE AUDIT v1.3
# ==============================================================================
# CARTOGRAPHIE INTÉGRALE DU PROJET
#
# READ ONLY
#   - Aucun DELETE
#   - Aucun MOVE
#   - Aucun fichier E-ZZIO existant modifié
#
# OBJECTIFS
#   1. Inventaire complet
#   2. Statistiques extensions / catégories
#   3. Analyse Python / PowerShell / Web
#   4. Extraction fonctions / classes / imports
#   5. Détection des composants architecturaux
#   6. Score de réutilisabilité
#   7. SHA256 des sources/configurations
#   8. Détection exacte des doublons
#   9. Top des fichiers réutilisables
#  10. Top des fichiers volumineux
#  11. Rapport JSON + TXT + CSV
#
# StrictMode-safe
# Progression visuelle
# Défensif
# ==============================================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ==============================================================================
# CONFIGURATION
# ==============================================================================

$ProjectRoot = 'G:\AI\E-zzio'

$ReportRoot = Join-Path $ProjectRoot 'runtime\audit\full_reuse'

$Timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'

$JsonReport = Join-Path $ReportRoot "EZZIO_FULL_REUSE_v13_$Timestamp.json"
$TxtReport  = Join-Path $ReportRoot "EZZIO_FULL_REUSE_v13_$Timestamp.txt"
$CsvReport  = Join-Path $ReportRoot "EZZIO_FULL_REUSE_FILES_v13_$Timestamp.csv"

# ------------------------------------------------------------------------------
# Dossiers exclus de l'analyse
# ------------------------------------------------------------------------------

$ExcludedDirs = @(
    '.git',
    '__pycache__',
    'node_modules',
    '.venv',
    'venv',
    'env'
)

# ------------------------------------------------------------------------------
# Extensions considérées comme code
# ------------------------------------------------------------------------------

$SourceExtensions = @(
    '.py',
    '.ps1',
    '.psm1',
    '.psd1',
    '.js',
    '.jsx',
    '.ts',
    '.tsx',
    '.svelte',
    '.vue'
)

# ------------------------------------------------------------------------------
# Extensions à hasher
# ------------------------------------------------------------------------------

$HashExtensions = @(
    '.py',
    '.ps1',
    '.psm1',
    '.psd1',
    '.js',
    '.jsx',
    '.ts',
    '.tsx',
    '.svelte',
    '.vue',
    '.json',
    '.yaml',
    '.yml',
    '.toml',
    '.ini',
    '.cfg',
    '.conf',
    '.xml',
    '.sql'
)

# ------------------------------------------------------------------------------
# Mots-clés architecturaux
# ------------------------------------------------------------------------------

$ArchitectureKeywords = [ordered]@{
    'guardian'   = 5
    'cognitive'  = 5
    'memory'     = 4
    'embedding'  = 4
    'orchestr'   = 4
    'dispatcher' = 4
    'supervisor' = 4
    'autonomy'   = 4
    'autonomous' = 4
    'recovery'   = 3
    'sandbox'    = 3
    'persona'    = 3
    'identity'   = 3
    'telemetry'  = 3
    'llm'        = 3
    'ollama'     = 3
    'gemini'     = 3
    'provider'   = 3
    'router'     = 3
    'agent'      = 3
    'tool'       = 2
    'tools'      = 2
    'pipeline'   = 2
    'context'    = 2
    'knowledge'  = 2
    'vision'     = 2
    'forge'      = 2
    'discord'    = 2
    'web_server' = 2
    'sqlite'     = 2
    'audit'      = 1
    'backup'     = 1
    'model'      = 1
    'api'        = 1
}

# ==============================================================================
# VALIDATION
# ==============================================================================

if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) {
    throw "Projet introuvable : $ProjectRoot"
}

# Création du seul emplacement que le script est autorisé à écrire :
# les rapports d'audit.
New-Item -ItemType Directory -Path $ReportRoot -Force | Out-Null

Set-Location -LiteralPath $ProjectRoot

# ==============================================================================
# HELPERS
# ==============================================================================

function Format-Size {
    param(
        [Parameter(Mandatory)]
        [Int64]$Bytes
    )

    if ($Bytes -ge 1TB) {
        return ('{0:N2} TB' -f ($Bytes / 1TB))
    }

    if ($Bytes -ge 1GB) {
        return ('{0:N2} GB' -f ($Bytes / 1GB))
    }

    if ($Bytes -ge 1MB) {
        return ('{0:N2} MB' -f ($Bytes / 1MB))
    }

    if ($Bytes -ge 1KB) {
        return ('{0:N2} KB' -f ($Bytes / 1KB))
    }

    return "$Bytes B"
}

function Test-Excluded {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    foreach ($directory in $ExcludedDirs) {

        $escaped = [regex]::Escape("\$directory\")

        if (
            $Path -match $escaped -or
            $Path.EndsWith("\$directory", [System.StringComparison]::OrdinalIgnoreCase)
        ) {
            return $true
        }
    }

    return $false
}

function Get-Category {
    param(
        [Parameter(Mandatory)]
        [string]$Extension
    )

    switch ($Extension.ToLowerInvariant()) {

        '.py'      { return 'Python' }
        '.ps1'     { return 'PowerShell' }
        '.psm1'    { return 'PowerShell Module' }
        '.psd1'    { return 'PowerShell Data' }

        '.js'      { return 'JavaScript' }
        '.jsx'     { return 'JavaScript React' }
        '.ts'      { return 'TypeScript' }
        '.tsx'     { return 'TypeScript React' }

        '.svelte'  { return 'Svelte' }
        '.vue'     { return 'Vue' }

        '.json'    { return 'JSON' }
        '.yaml'    { return 'YAML' }
        '.yml'     { return 'YAML' }
        '.toml'    { return 'TOML' }

        '.md'      { return 'Documentation' }

        '.sql'     { return 'SQL' }

        '.db'      { return 'Database' }
        '.sqlite'  { return 'Database' }
        '.sqlite3' { return 'Database' }

        default    { return 'Other' }
    }
}

# ==============================================================================
# HEADER
# ==============================================================================

Clear-Host

Write-Host ""
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host " E-ZZIO FULL REUSE AUDIT v1.3" -ForegroundColor Cyan
Write-Host " CARTOGRAPHIE INTÉGRALE DU PROJET" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Projet : $ProjectRoot" -ForegroundColor White
Write-Host "Mode   : READ ONLY" -ForegroundColor Green
Write-Host "Rapport: $ReportRoot" -ForegroundColor DarkGray
Write-Host ""

# ==============================================================================
# PHASE 1 — INVENTAIRE
# ==============================================================================

Write-Host "[1/7] INVENTAIRE COMPLET DES FICHIERS" -ForegroundColor Yellow
Write-Host ""

$Files = @(
    Get-ChildItem `
        -LiteralPath $ProjectRoot `
        -Recurse `
        -File `
        -Force `
        -ErrorAction SilentlyContinue |
    Where-Object {
        -not (Test-Excluded -Path $_.FullName)
    }
)

$TotalFiles = $Files.Count

$FileInventory = [System.Collections.Generic.List[object]]::new()

$idx = 0

foreach ($file in $Files) {

    $idx++

    if (
        ($idx % 250 -eq 0) -or
        ($idx -eq $TotalFiles)
    ) {

        $percent = [math]::Round(
            ($idx / [math]::Max($TotalFiles, 1)) * 100,
            1
        )

        Write-Progress `
            -Activity "E-ZZIO — INVENTAIRE" `
            -Status "$idx / $TotalFiles — $($file.Name)" `
            -PercentComplete $percent
    }

    $extension = if (
        [string]::IsNullOrWhiteSpace($file.Extension)
    ) {
        '(sans extension)'
    }
    else {
        $file.Extension.ToLowerInvariant()
    }

    $relative = $file.FullName.Substring(
        $ProjectRoot.Length
    ).TrimStart('\')

    $FileInventory.Add(
        [PSCustomObject]@{
            Path          = $file.FullName
            RelativePath  = $relative
            Name          = $file.Name
            Extension     = $extension
            Category      = Get-Category -Extension $extension
            SizeBytes     = [Int64]$file.Length
            Size          = Format-Size -Bytes ([Int64]$file.Length)
            LastWriteTime = $file.LastWriteTime
        }
    )
}

Write-Progress `
    -Activity "E-ZZIO — INVENTAIRE" `
    -Completed

# ------------------------------------------------------------------------------
# Total volume
# ------------------------------------------------------------------------------

$TotalBytes = [Int64]0

foreach ($item in $FileInventory) {
    $TotalBytes += [Int64]$item.SizeBytes
}

Write-Host ""
Write-Host "  [OK] Fichiers : $TotalFiles" -ForegroundColor Green
Write-Host "  [OK] Volume   : $(Format-Size -Bytes $TotalBytes)" -ForegroundColor Green
Write-Host ""

# ==============================================================================
# PHASE 2 — STATISTIQUES
# ==============================================================================

Write-Host "[2/7] STATISTIQUES GLOBALES" -ForegroundColor Yellow
Write-Host ""

$ExtensionStats = @(
    $FileInventory |
    Group-Object -Property Extension |
    ForEach-Object {

        $bytes = [Int64]0

        foreach ($entry in $_.Group) {
            $bytes += [Int64]$entry.SizeBytes
        }

        [PSCustomObject]@{
            Extension = $_.Name
            Files     = $_.Count
            Bytes     = $bytes
            Size      = Format-Size -Bytes $bytes
        }
    } |
    Sort-Object -Property Bytes -Descending
)

$CategoryStats = @(
    $FileInventory |
    Group-Object -Property Category |
    ForEach-Object {

        $bytes = [Int64]0

        foreach ($entry in $_.Group) {
            $bytes += [Int64]$entry.SizeBytes
        }

        [PSCustomObject]@{
            Category = $_.Name
            Files    = $_.Count
            Bytes    = $bytes
            Size     = Format-Size -Bytes $bytes
        }
    } |
    Sort-Object -Property Bytes -Descending
)

Write-Host "  TOP EXTENSIONS :" -ForegroundColor Cyan

foreach ($extension in ($ExtensionStats | Select-Object -First 15)) {

    Write-Host (
        "    {0,-18} {1,8} fichiers  {2}" -f `
        $extension.Extension,
        $extension.Files,
        $extension.Size
    )
}

Write-Host ""

# ==============================================================================
# PHASE 3 — ANALYSE DES SOURCES
# ==============================================================================

Write-Host "[3/7] ANALYSE DES SOURCES" -ForegroundColor Yellow
Write-Host ""

$PythonFunctions = [System.Collections.Generic.List[object]]::new()
$PythonClasses   = [System.Collections.Generic.List[object]]::new()
$PythonImports   = [System.Collections.Generic.List[object]]::new()
$KeywordHits     = [System.Collections.Generic.List[object]]::new()
$ReuseScores     = [System.Collections.Generic.List[object]]::new()

$ReadErrors = [System.Collections.Generic.List[object]]::new()

$SourceFiles = @(
    $Files |
    Where-Object {
        $_.Extension.ToLowerInvariant() -in $SourceExtensions
    }
)

$sIdx = 0
$sTotal = [math]::Max($SourceFiles.Count, 1)

foreach ($file in $SourceFiles) {

    $sIdx++

    $percent = [math]::Round(
        ($sIdx / $sTotal) * 100,
        1
    )

    Write-Progress `
        -Activity "E-ZZIO — ANALYSE SOURCES" `
        -Status "$sIdx / $($SourceFiles.Count) — $($file.Name)" `
        -PercentComplete $percent

    $extension = $file.Extension.ToLowerInvariant()

    $isPython = $extension -eq '.py'

    $functionCount = 0
    $classCount    = 0
    $importCount   = 0
    $keywordScore  = 0

    $hitKeywords = @{}

    try {

        $content = Get-Content `
            -LiteralPath $file.FullName `
            -Raw `
            -ErrorAction Stop

        if ([string]::IsNullOrWhiteSpace($content)) {
            continue
        }

        # ----------------------------------------------------------------------
        # PYTHON FUNCTIONS
        # ----------------------------------------------------------------------

        if ($isPython) {

            $functionMatches = [regex]::Matches(
                $content,
                '(?m)^\s*(?:async\s+)?def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\('
            )

            foreach ($match in $functionMatches) {

                $functionCount++

                $PythonFunctions.Add(
                    [PSCustomObject]@{
                        File = $file.FullName
                        Name = $match.Groups[1].Value
                    }
                )
            }

            # ------------------------------------------------------------------
            # PYTHON CLASSES
            # ------------------------------------------------------------------

            $classMatches = [regex]::Matches(
                $content,
                '(?m)^\s*class\s+([A-Za-z_][A-Za-z0-9_]*)'
            )

            foreach ($match in $classMatches) {

                $classCount++

                $PythonClasses.Add(
                    [PSCustomObject]@{
                        File = $file.FullName
                        Name = $match.Groups[1].Value
                    }
                )
            }

            # ------------------------------------------------------------------
            # PYTHON IMPORTS
            # ------------------------------------------------------------------

            $importMatches = [regex]::Matches(
                $content,
                '(?m)^\s*(?:from\s+([A-Za-z_][A-Za-z0-9_\.]*)\s+import|import\s+([A-Za-z_][A-Za-z0-9_\.]*))'
            )

            foreach ($match in $importMatches) {

                $importName = if ($match.Groups[1].Success) {
                    $match.Groups[1].Value
                }
                else {
                    $match.Groups[2].Value
                }

                $importCount++

                $PythonImports.Add(
                    [PSCustomObject]@{
                        File   = $file.FullName
                        Import = $importName
                    }
                )
            }
        }

        # ----------------------------------------------------------------------
        # ARCHITECTURE KEYWORDS
        # ----------------------------------------------------------------------

        foreach ($keyword in $ArchitectureKeywords.Keys) {

            $count = [regex]::Matches(
                $content,
                [regex]::Escape($keyword),
                [System.Text.RegularExpressions.RegexOptions]::IgnoreCase
            ).Count

            if ($count -gt 0) {

                $hitKeywords[$keyword] = $count

                $keywordScore += (
                    $count *
                    [int]$ArchitectureKeywords[$keyword]
                )
            }
        }

        foreach ($keyword in $hitKeywords.Keys) {

            $KeywordHits.Add(
                [PSCustomObject]@{
                    Keyword = $keyword
                    File    = $file.FullName
                    Matches = [int]$hitKeywords[$keyword]
                    Weight  = [int]$ArchitectureKeywords[$keyword]
                }
            )
        }

        # ----------------------------------------------------------------------
        # SCORE DE RÉUTILISABILITÉ
        # ----------------------------------------------------------------------

        $score = 0

        if ($isPython) {

            $score += [math]::Min(
                $functionCount * 3,
                30
            )

            $score += [math]::Min(
                $classCount * 5,
                25
            )

            $score += [math]::Min(
                $importCount,
                15
            )

            $score += [math]::Min(
                $keywordScore,
                20
            )

            if (
                $file.DirectoryName -match
                '\\(core|memory|tools|agents|runtime|guardian)(\\|$)'
            ) {
                $score += 10
            }
        }
        elseif (
            $extension -in @('.ps1', '.psm1')
        ) {

            $score += [math]::Min(
                $keywordScore,
                40
            )

            if (
                $file.Name -match
                'watchdog|daemon|audit|guardian|start_'
            ) {
                $score += 15
            }
        }

        if ($score -gt 0) {

            $ReuseScores.Add(
                [PSCustomObject]@{
                    Path         = $file.FullName
                    RelativePath = $file.FullName.Substring(
                        $ProjectRoot.Length
                    ).TrimStart('\')
                    Extension    = $extension
                    Score        = [math]::Min($score, 100)
                    Functions    = $functionCount
                    Classes      = $classCount
                    Imports      = $importCount
                    KeywordScore = $keywordScore
                }
            )
        }
    }
    catch {

        $ReadErrors.Add(
            [PSCustomObject]@{
                Path    = $file.FullName
                Error   = $_.Exception.Message
                Phase   = 'SourceAnalysis'
                Time    = (Get-Date).ToString('o')
            }
        )
    }
}

Write-Progress `
    -Activity "E-ZZIO — ANALYSE SOURCES" `
    -Completed

Write-Host ""
Write-Host (
    "  [OK] Python : {0} fonctions | {1} classes | {2} imports" -f `
    $PythonFunctions.Count,
    $PythonClasses.Count,
    $PythonImports.Count
) -ForegroundColor Green

Write-Host (
    "  [INFO] Composants réutilisables scorés : {0}" -f `
    $ReuseScores.Count
) -ForegroundColor Cyan

Write-Host ""

# ==============================================================================
# PHASE 4 — SHA256
# ==============================================================================

Write-Host "[4/7] EMPREINTES SHA256" -ForegroundColor Yellow
Write-Host ""

$HashResults = [System.Collections.Generic.List[object]]::new()

# Cache central : évite de recalculer le même fichier
$HashCache = @{}

$HashFiles = @(
    $Files |
    Where-Object {
        $_.Extension.ToLowerInvariant() -in $HashExtensions
    }
)

$hIdx = 0
$hTotal = [math]::Max($HashFiles.Count, 1)

foreach ($file in $HashFiles) {

    $hIdx++

    $percent = [math]::Round(
        ($hIdx / $hTotal) * 100,
        1
    )

    Write-Progress `
        -Activity "E-ZZIO — SHA256" `
        -Status "$hIdx / $($HashFiles.Count) — $($file.Name)" `
        -PercentComplete $percent

    try {

        $hash = $null

        if ($HashCache.ContainsKey($file.FullName)) {

            $hash = $HashCache[$file.FullName]
        }
        else {

            $hash = (
                Get-FileHash `
                    -LiteralPath $file.FullName `
                    -Algorithm SHA256 `
                    -ErrorAction Stop
            ).Hash

            $HashCache[$file.FullName] = $hash
        }

        $HashResults.Add(
            [PSCustomObject]@{
                Path   = $file.FullName
                SHA256 = $hash
                Bytes  = [Int64]$file.Length
            }
        )
    }
    catch {

        $ReadErrors.Add(
            [PSCustomObject]@{
                Path  = $file.FullName
                Error = $_.Exception.Message
                Phase = 'SHA256'
                Time  = (Get-Date).ToString('o')
            }
        )
    }
}

Write-Progress `
    -Activity "E-ZZIO — SHA256" `
    -Completed

Write-Host ""
Write-Host (
    "  [OK] Fichiers hashés : {0}" -f
    $HashResults.Count
) -ForegroundColor Green

Write-Host ""

# ==============================================================================
# PHASE 5 — GROS FICHIERS
# ==============================================================================

Write-Host "[5/7] ANALYSE DES PLUS GROS FICHIERS" -ForegroundColor Yellow
Write-Host ""

$LargestFiles = @(
    $FileInventory |
    Sort-Object -Property SizeBytes -Descending |
    Select-Object -First 40
)

$rank = 0

foreach ($file in ($LargestFiles | Select-Object -First 20)) {

    $rank++

    Write-Host (
        "  {0,2}. {1,12} | {2}" -f `
        $rank,
        $file.Size,
        $file.RelativePath
    ) -ForegroundColor DarkGray
}

Write-Host ""

# ==============================================================================
# PHASE 6 — DOUBLONS EXACTS
# ==============================================================================

Write-Host "[6/7] REDONDANCES : NOM + TAILLE → SHA256" -ForegroundColor Yellow
Write-Host ""

$phaseA = @(
    $FileInventory |
    Where-Object {
        $_.SizeBytes -gt 0
    } |
    Group-Object {
        "$($_.SizeBytes)|$($_.Name.ToLowerInvariant())"
    } |
    Where-Object {
        $_.Count -gt 1
    }
)

Write-Host (
    "  [INFO] Groupes candidats : {0}" -f
    $phaseA.Count
) -ForegroundColor Cyan

$PotentialDuplicates = [System.Collections.Generic.List[object]]::new()

$filesToHash = [System.Collections.Generic.List[object]]::new()

foreach ($group in $phaseA) {

    foreach ($item in $group.Group) {
        $filesToHash.Add($item)
    }
}

$dIdx = 0
$dTotal = [math]::Max($filesToHash.Count, 1)

$duplicateHashMap = @{}

foreach ($item in $filesToHash) {

    $dIdx++

    $percent = [math]::Round(
        ($dIdx / $dTotal) * 100,
        1
    )

    Write-Progress `
        -Activity "E-ZZIO — VALIDATION DOUBLONS" `
        -Status "$dIdx / $($filesToHash.Count) — $($item.Name)" `
        -PercentComplete $percent

    try {

        if ($HashCache.ContainsKey($item.Path)) {

            $hash = $HashCache[$item.Path]
        }
        else {

            $hash = (
                Get-FileHash `
                    -LiteralPath $item.Path `
                    -Algorithm SHA256 `
                    -ErrorAction Stop
            ).Hash

            $HashCache[$item.Path] = $hash
        }

        if (-not $duplicateHashMap.ContainsKey($hash)) {

            $duplicateHashMap[$hash] =
                [System.Collections.Generic.List[string]]::new()
        }

        $duplicateHashMap[$hash].Add($item.Path)
    }
    catch {

        $ReadErrors.Add(
            [PSCustomObject]@{
                Path  = $item.Path
                Error = $_.Exception.Message
                Phase = 'DuplicateSHA256'
                Time  = (Get-Date).ToString('o')
            }
        )
    }
}

Write-Progress `
    -Activity "E-ZZIO — VALIDATION DOUBLONS" `
    -Completed

foreach ($hash in $duplicateHashMap.Keys) {

    $paths = $duplicateHashMap[$hash]

    if ($paths.Count -gt 1) {

        $PotentialDuplicates.Add(
            [PSCustomObject]@{
                SHA256 = $hash
                Count  = $paths.Count
                Files  = @($paths)
            }
        )
    }
}

Write-Host ""
Write-Host (
    "  [OK] Groupes exactement identiques : {0}" -f
    $PotentialDuplicates.Count
) -ForegroundColor Green

Write-Host ""

# ==============================================================================
# PHASE 7 — RAPPORTS
# ==============================================================================

Write-Host "[7/7] CONSTRUCTION DES RAPPORTS" -ForegroundColor Yellow
Write-Host ""

$TopReusable = @(
    $ReuseScores |
    Sort-Object -Property Score, Functions, Classes -Descending |
    Select-Object -First 50
)

$Report = [ordered]@{

    AuditDate = (Get-Date).ToString('o')

    Version = '1.3'

    Mode = 'READ_ONLY'

    Project = [ordered]@{
        Root       = $ProjectRoot
        TotalFiles = $TotalFiles
        TotalBytes = [Int64]$TotalBytes
        TotalSize  = Format-Size -Bytes $TotalBytes
    }

    Statistics = [ordered]@{
        Extensions = @($ExtensionStats)
        Categories = @($CategoryStats)
    }

    Architecture = [ordered]@{

        PythonFiles = @(
            $Files |
            Where-Object {
                $_.Extension.ToLowerInvariant() -eq '.py'
            }
        ).Count

        PowerShellFiles = @(
            $Files |
            Where-Object {
                $_.Extension.ToLowerInvariant() -in
                @('.ps1', '.psm1', '.psd1')
            }
        ).Count

        WebFiles = @(
            $Files |
            Where-Object {
                $_.Extension.ToLowerInvariant() -in
                @('.js', '.jsx', '.ts', '.tsx', '.svelte', '.vue')
            }
        ).Count

        PythonFunctions  = @($PythonFunctions)
        PythonClasses    = @($PythonClasses)
        PythonImports    = @($PythonImports)
        ArchitectureHits = @($KeywordHits)
    }

    ReuseAnalysis = [ordered]@{
        TopReusable = @($TopReusable)
        ScoredFiles = $ReuseScores.Count
    }

    LargestFiles = @($LargestFiles)

    ExactDuplicates = @($PotentialDuplicates)

    SHA256 = @($HashResults)

    Errors = @($ReadErrors)

    AuditHealth = [ordered]@{
        ReadErrors = $ReadErrors.Count
        Hashes     = $HashResults.Count
        FilesSeen  = $TotalFiles
    }

    Git = [ordered]@{
        Exists = Test-Path -LiteralPath (
            Join-Path $ProjectRoot '.git'
        )
    }
}

# ==============================================================================
# JSON
# ==============================================================================

$Report |
    ConvertTo-Json -Depth 20 |
    Set-Content `
        -LiteralPath $JsonReport `
        -Encoding UTF8

# ==============================================================================
# CSV
# ==============================================================================

$FileInventory |
    Export-Csv `
        -LiteralPath $CsvReport `
        -NoTypeInformation `
        -Encoding UTF8

# ==============================================================================
# TXT
# ==============================================================================

$Lines = [System.Collections.Generic.List[string]]::new()

$Lines.Add('E-ZZIO FULL REUSE AUDIT v1.3')
$Lines.Add('======================================================================')
$Lines.Add("Date     : $($Report.AuditDate)")
$Lines.Add("Projet   : $ProjectRoot")
$Lines.Add("Mode     : READ ONLY")
$Lines.Add("Fichiers : $TotalFiles")
$Lines.Add("Volume   : $(Format-Size -Bytes $TotalBytes)")
$Lines.Add("Erreurs  : $($ReadErrors.Count)")
$Lines.Add('')

$Lines.Add('--- TOP EXTENSIONS ---')

foreach ($extension in ($ExtensionStats | Select-Object -First 20)) {

    $Lines.Add(
        ('{0,-20} {1,8} fichiers  {2}' -f `
            $extension.Extension,
            $extension.Files,
            $extension.Size)
    )
}

$Lines.Add('')
$Lines.Add('--- TOP FICHIERS RÉUTILISABLES ---')

foreach ($reuse in ($TopReusable | Select-Object -First 50)) {

    $Lines.Add(
        ('{0,3} pts | {1}' -f `
            $reuse.Score,
            $reuse.RelativePath)
    )
}

$Lines.Add('')
$Lines.Add('--- DOUBLONS EXACTS SHA256 ---')
$Lines.Add("Groupes : $($PotentialDuplicates.Count)")

foreach (
    $duplicate in
    ($PotentialDuplicates | Select-Object -First 100)
) {

    $shortHash = if (
        $duplicate.SHA256.Length -ge 12
    ) {
        $duplicate.SHA256.Substring(0, 12)
    }
    else {
        $duplicate.SHA256
    }

    $Lines.Add(
        "SHA256 $shortHash...  x$($duplicate.Count)"
    )

    foreach ($path in $duplicate.Files) {
        $Lines.Add("   - $path")
    }
}

$Lines.Add('')
$Lines.Add('--- ERREURS DE LECTURE ---')
$Lines.Add("Nombre : $($ReadErrors.Count)")

foreach ($errorItem in ($ReadErrors | Select-Object -First 200)) {

    $Lines.Add(
        "[{0}] {1} -> {2}" -f `
        $errorItem.Phase,
        $errorItem.Path,
        $errorItem.Error
    )
}

$Lines |
    Set-Content `
        -LiteralPath $TxtReport `
        -Encoding UTF8

# ==============================================================================
# FINAL
# ==============================================================================

Write-Host ""
Write-Host "======================================================================" -ForegroundColor Green
Write-Host " E-ZZIO FULL REUSE AUDIT v1.3 — TERMINÉ" -ForegroundColor Green
Write-Host "======================================================================" -ForegroundColor Green
Write-Host ""

Write-Host "Fichiers analysés     : $TotalFiles"
Write-Host "Volume                : $(Format-Size -Bytes $TotalBytes)"
Write-Host "Fonctions Python      : $($PythonFunctions.Count)"
Write-Host "Classes Python        : $($PythonClasses.Count)"
Write-Host "Imports Python        : $($PythonImports.Count)"
Write-Host "Fichiers scorés       : $($ReuseScores.Count)"
Write-Host "Doublons exacts       : $($PotentialDuplicates.Count)"
Write-Host "SHA256 calculés       : $($HashResults.Count)"
Write-Host "Erreurs de lecture    : $($ReadErrors.Count)"
Write-Host ""

Write-Host "TOP 15 RÉUTILISABLES :" -ForegroundColor Cyan

$rank = 0

foreach ($reuse in ($TopReusable | Select-Object -First 15)) {

    $rank++

    Write-Host (
        "  {0,2}. [{1,3}/100] {2}" -f `
        $rank,
        $reuse.Score,
        $reuse.RelativePath
    ) -ForegroundColor White
}

Write-Host ""

Write-Host "RAPPORTS :" -ForegroundColor Cyan
Write-Host "  JSON : $JsonReport"
Write-Host "  TXT  : $TxtReport"
Write-Host "  CSV  : $CsvReport"
Write-Host ""

if ($ReadErrors.Count -eq 0) {

    Write-Host "INTÉGRITÉ AUDIT : OK — aucune erreur de lecture." `
        -ForegroundColor Green
}
else {

    Write-Host (
        "INTÉGRITÉ AUDIT : ATTENTION — {0} erreur(s) de lecture." -f
        $ReadErrors.Count
    ) -ForegroundColor Yellow
}

Write-Host ""
Write-Host "READ ONLY — aucun fichier E-ZZIO existant n'a été modifié." `
    -ForegroundColor Green
Write-Host ""
