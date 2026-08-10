# ==============================================================================
# E-ZZIO FULL REUSE AUDIT v1.0
# ==============================================================================
# OBJECTIF
#   Cartographier intégralement E-ZZIO afin de réutiliser l'existant.
#
# MODE
#   READ ONLY
#   AUCUN DELETE
#   AUCUN MOVE
#   AUCUN MODIFY
#
# ANALYSE
#   - Tous fichiers / dossiers
#   - Extensions / tailles / dates
#   - Python : fonctions / classes / imports
#   - PowerShell
#   - JS / TS / Svelte
#   - JSON / YAML / TOML / INI / XML
#   - Documentation
#   - SQLite / DB
#   - Git
#   - Signatures architecture
#   - SHA256 des sources/configs
#   - Fichiers volumineux
#   - Candidats à réutilisation
#   - Candidats à redondance
#   - Rapport JSON + CSV + TXT
# ==============================================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ------------------------------------------------------------------------------
# CONFIGURATION
# ------------------------------------------------------------------------------

$ProjectRoot = 'G:\AI\E-zzio'

$ReportRoot = Join-Path $ProjectRoot 'runtime\audit\full_reuse'

$Timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'

$JsonReport = Join-Path $ReportRoot "EZZIO_FULL_REUSE_$Timestamp.json"
$TxtReport  = Join-Path $ReportRoot "EZZIO_FULL_REUSE_$Timestamp.txt"
$CsvReport  = Join-Path $ReportRoot "EZZIO_FULL_REUSE_FILES_$Timestamp.csv"

$ExcludedDirs = @(
    '.git',
    '__pycache__',
    'node_modules',
    '.venv',
    'venv',
    'env'
)

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
    '.vue',
    '.json',
    '.yaml',
    '.yml',
    '.toml',
    '.ini',
    '.cfg',
    '.conf',
    '.xml',
    '.md',
    '.txt',
    '.sql',
    '.bat',
    '.cmd'
)

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

$ArchitectureKeywords = @(
    'memory',
    'guardian',
    'llm',
    'gemini',
    'ollama',
    'tool',
    'tools',
    'router',
    'agent',
    'provider',
    'dispatcher',
    'brain',
    'cognitive',
    'knowledge',
    'vision',
    'embedding',
    'embed',
    'autonomy',
    'autonomous',
    'governor',
    'supervisor',
    'telemetry',
    'audit',
    'recovery',
    'backup',
    'sandbox',
    'policy',
    'security',
    'identity',
    'persona',
    'message',
    'chat',
    'discord',
    'web',
    'api',
    'runtime',
    'pipeline',
    'discovery',
    'forge',
    'creative',
    'model',
    'registry',
    'execution',
    'orchestration',
    'context',
    'knowledge',
    'database',
    'sqlite'
)

# ------------------------------------------------------------------------------
# VALIDATION
# ------------------------------------------------------------------------------

if (-not (Test-Path -LiteralPath $ProjectRoot)) {
    throw "Projet introuvable : $ProjectRoot"
}

New-Item `
    -ItemType Directory `
    -Path $ReportRoot `
    -Force |
    Out-Null

Set-Location -LiteralPath $ProjectRoot

# ------------------------------------------------------------------------------
# OUTILS
# ------------------------------------------------------------------------------

function Format-EzzioSize {
    param(
        [Int64]$Bytes
    )

    if ($Bytes -ge 1TB) {
        return '{0:N2} TB' -f ($Bytes / 1TB)
    }

    if ($Bytes -ge 1GB) {
        return '{0:N2} GB' -f ($Bytes / 1GB)
    }

    if ($Bytes -ge 1MB) {
        return '{0:N2} MB' -f ($Bytes / 1MB)
    }

    if ($Bytes -ge 1KB) {
        return '{0:N2} KB' -f ($Bytes / 1KB)
    }

    return "$Bytes B"
}

function Test-EzzioExcluded {
    param(
        [string]$Path
    )

    foreach ($Dir in $ExcludedDirs) {
        if (
            $Path -match [regex]::Escape("\$Dir\") -or
            $Path.EndsWith("\$Dir")
        ) {
            return $true
        }
    }

    return $false
}

function Get-EzzioCategory {
    param(
        [string]$Extension
    )

    switch ($Extension.ToLowerInvariant()) {

        '.py'   { return 'Python' }
        '.ps1'  { return 'PowerShell' }
        '.psm1' { return 'PowerShell Module' }
        '.psd1' { return 'PowerShell Data' }

        '.js'   { return 'JavaScript' }
        '.jsx'  { return 'JavaScript React' }
        '.ts'   { return 'TypeScript' }
        '.tsx'  { return 'TypeScript React' }
        '.svelte'{ return 'Svelte' }
        '.vue'  { return 'Vue' }

        '.json' { return 'JSON' }
        '.yaml' { return 'YAML' }
        '.yml'  { return 'YAML' }
        '.toml' { return 'TOML' }
        '.ini'  { return 'INI' }
        '.cfg'  { return 'Config' }
        '.conf' { return 'Config' }
        '.xml'  { return 'XML' }

        '.md'   { return 'Documentation' }
        '.txt'  { return 'Text' }

        '.sql'  { return 'SQL' }

        '.db'   { return 'Database' }
        '.sqlite'{ return 'Database' }
        '.sqlite3'{ return 'Database' }

        '.dll'  { return 'Binary' }
        '.exe'  { return 'Executable' }
        '.pyd'  { return 'Python Binary' }
        '.node' { return 'Node Binary' }

        default { return 'Other' }
    }
}

function Get-EzzioMemoryMB {
    try {
        return [math]::Round(
            (Get-Process -Id $PID -ErrorAction Stop).WorkingSet64 / 1MB,
            0
        )
    }
    catch {
        return 0
    }
}

# ------------------------------------------------------------------------------
# HEADER
# ------------------------------------------------------------------------------

Clear-Host

Write-Host ""
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host " E-ZZIO FULL REUSE AUDIT v1.0" -ForegroundColor Cyan
Write-Host " CARTOGRAPHIE INTÉGRALE DU PROJET" -ForegroundColor Cyan
Write-Host " READ ONLY — AUCUNE MODIFICATION" -ForegroundColor Green
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Projet : $ProjectRoot" -ForegroundColor White
Write-Host "Rapport: $ReportRoot" -ForegroundColor White
Write-Host ""

# ------------------------------------------------------------------------------
# PHASE 1 — INVENTAIRE
# ------------------------------------------------------------------------------

Write-Host "[1/8] INVENTAIRE COMPLET DES FICHIERS" -ForegroundColor Yellow
Write-Host ""

$Files = @(
    Get-ChildItem `
        -LiteralPath $ProjectRoot `
        -Recurse `
        -File `
        -Force `
        -ErrorAction SilentlyContinue |
    Where-Object {
        -not (Test-EzzioExcluded -Path $_.FullName)
    }
)

$TotalFiles = $Files.Count

Write-Host "Fichiers détectés : $TotalFiles" -ForegroundColor Green
Write-Host ""

$FileInventory = [System.Collections.Generic.List[object]]::new()

$Index = 0
$StartTime = Get-Date

foreach ($File in $Files) {

    $Index++

    $Elapsed = ((Get-Date) - $StartTime).TotalSeconds

    if ($Index -gt 0 -and $Elapsed -gt 0) {
        $Speed = $Index / $Elapsed
        $Remaining = ($TotalFiles - $Index) / [math]::Max($Speed, 0.001)
    }
    else {
        $Speed = 0
        $Remaining = 0
    }

    $Percent = if ($TotalFiles -gt 0) {
        [math]::Round(($Index / $TotalFiles) * 100, 1)
    }
    else {
        100
    }

    Write-Progress `
        -Activity "E-ZZIO — Inventaire des fichiers" `
        -Status "$Index / $TotalFiles — $($File.Name)" `
        -PercentComplete $Percent `
        -CurrentOperation "$Percent% | $([math]::Round($Speed,1)) fichiers/s | ETA $([timespan]::FromSeconds($Remaining).ToString('hh\:mm\:ss')) | RAM $(Get-EzzioMemoryMB) MB"

    $Extension = $File.Extension

    if ([string]::IsNullOrWhiteSpace($Extension)) {
        $Extension = '(sans extension)'
    }

    $FileInventory.Add(
        [PSCustomObject]@{
            Path          = $File.FullName
            RelativePath  = $File.FullName.Substring($ProjectRoot.Length).TrimStart('\')
            Name          = $File.Name
            Extension     = $Extension
            Category      = Get-EzzioCategory -Extension $Extension
            SizeBytes     = [Int64]$File.Length
            Size          = Format-EzzioSize $File.Length
            LastWriteTime = $File.LastWriteTime
            CreationTime  = $File.CreationTime
            Attributes    = $File.Attributes.ToString()
        }
    )
}

Write-Progress `
    -Activity "E-ZZIO — Inventaire des fichiers" `
    -Completed

Write-Host ""
Write-Host "[OK] Inventaire terminé." -ForegroundColor Green
Write-Host ""

# ------------------------------------------------------------------------------
# PHASE 2 — STATISTIQUES
# ------------------------------------------------------------------------------

Write-Host "[2/8] STATISTIQUES GLOBALES" -ForegroundColor Yellow
Write-Host ""

$TotalBytes = ($FileInventory | Measure-Object -Property SizeBytes -Sum).Sum

$ExtensionStats = @(
    $FileInventory |
        Group-Object Extension |
        ForEach-Object {

            $Bytes = ($_.Group | Measure-Object SizeBytes -Sum).Sum

            [PSCustomObject]@{
                Extension = $_.Name
                Files     = $_.Count
                Bytes     = [Int64]$Bytes
                Size      = Format-EzzioSize $Bytes
            }
        } |
        Sort-Object Bytes -Descending
)

$CategoryStats = @(
    $FileInventory |
        Group-Object Category |
        ForEach-Object {

            $Bytes = ($_.Group | Measure-Object SizeBytes -Sum).Sum

            [PSCustomObject]@{
                Category = $_.Name
                Files    = $_.Count
                Bytes    = [Int64]$Bytes
                Size     = Format-EzzioSize $Bytes
            }
        } |
        Sort-Object Bytes -Descending
)

Write-Host "Fichiers : $TotalFiles" -ForegroundColor White
Write-Host "Volume   : $(Format-EzzioSize $TotalBytes)" -ForegroundColor White
Write-Host ""

Write-Host "TOP EXTENSIONS :" -ForegroundColor Cyan

$ExtensionStats |
    Select-Object -First 20 |
    ForEach-Object {
        Write-Host ("  {0,-16} {1,8} fichiers  {2}" -f `
            $_.Extension,
            $_.Files,
            $_.Size)
    }

Write-Host ""

# ------------------------------------------------------------------------------
# PHASE 3 — ARCHITECTURE SOURCE
# ------------------------------------------------------------------------------

Write-Host "[3/8] ANALYSE DES SOURCES PYTHON / POWERSHELL / WEB" -ForegroundColor Yellow
Write-Host ""

$PythonFiles = @(
    $Files |
        Where-Object { $_.Extension -eq '.py' }
)

$PowerShellFiles = @(
    $Files |
        Where-Object {
            $_.Extension -in @('.ps1','.psm1','.psd1')
        }
)

$WebFiles = @(
    $Files |
        Where-Object {
            $_.Extension -in @(
                '.js','.jsx','.ts','.tsx','.svelte','.vue'
            )
        }
)

Write-Host "Python      : $($PythonFiles.Count)"
Write-Host "PowerShell  : $($PowerShellFiles.Count)"
Write-Host "Web         : $($WebFiles.Count)"
Write-Host ""

$PythonFunctions = [System.Collections.Generic.List[object]]::new()
$PythonClasses   = [System.Collections.Generic.List[object]]::new()
$PythonImports   = [System.Collections.Generic.List[object]]::new()

$SourceFiles = @(
    $Files |
        Where-Object {
            $_.Extension.ToLowerInvariant() -in $SourceExtensions
        }
)

$SourceTotal = $SourceFiles.Count
$SourceIndex = 0
$SourceStart = Get-Date

foreach ($File in $SourceFiles) {

    $SourceIndex++

    $Elapsed = ((Get-Date) - $SourceStart).TotalSeconds
    $Speed = if ($Elapsed -gt 0) {
        $SourceIndex / $Elapsed
    }
    else {
        0
    }

    $Remaining = if ($Speed -gt 0) {
        ($SourceTotal - $SourceIndex) / $Speed
    }
    else {
        0
    }

    $Percent = if ($SourceTotal -gt 0) {
        [math]::Round(($SourceIndex / $SourceTotal) * 100, 1)
    }
    else {
        100
    }

    Write-Progress `
        -Activity "E-ZZIO — Analyse du code source" `
        -Status "$SourceIndex / $SourceTotal — $($File.Name)" `
        -PercentComplete $Percent `
        -CurrentOperation "$Percent% | $([math]::Round($Speed,1)) fichiers/s | ETA $([timespan]::FromSeconds($Remaining).ToString('hh\:mm\:ss'))"

    if ($File.Extension -ne '.py') {
        continue
    }

    try {
        $Lines = Get-Content `
            -LiteralPath $File.FullName `
            -Encoding UTF8 `
            -ErrorAction Stop

        for ($i = 0; $i -lt $Lines.Count; $i++) {

            $Line = $Lines[$i]

            if ($Line -match '^\s*def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(') {

                $PythonFunctions.Add(
                    [PSCustomObject]@{
                        File = $File.FullName
                        Line = $i + 1
                        Name = $Matches[1]
                    }
                )
            }

            if ($Line -match '^\s*class\s+([A-Za-z_][A-Za-z0-9_]*)') {

                $PythonClasses.Add(
                    [PSCustomObject]@{
                        File = $File.FullName
                        Line = $i + 1
                        Name = $Matches[1]
                    }
                )
            }

            if ($Line -match '^\s*(from\s+.+\s+import\s+.+|import\s+.+)') {

                $PythonImports.Add(
                    [PSCustomObject]@{
                        File = $File.FullName
                        Line = $i + 1
                        Import = $Line.Trim()
                    }
                )
            }
        }
    }
    catch {
        # Lecture source non bloquante
    }
}

Write-Progress `
    -Activity "E-ZZIO — Analyse du code source" `
    -Completed

Write-Host ""
Write-Host "[OK] Analyse source terminée." -ForegroundColor Green
Write-Host ""

# ------------------------------------------------------------------------------
# PHASE 4 — SIGNATURES ARCHITECTURE
# ------------------------------------------------------------------------------

Write-Host "[4/8] CARTOGRAPHIE DES COMPOSANTS RÉUTILISABLES" -ForegroundColor Yellow
Write-Host ""

$KeywordHits = [System.Collections.Generic.List[object]]::new()

$KeywordFiles = @(
    $Files |
        Where-Object {
            $_.Extension.ToLowerInvariant() -in $SourceExtensions
        }
)

$KeywordTotal = $KeywordFiles.Count
$KeywordIndex = 0

foreach ($File in $KeywordFiles) {

    $KeywordIndex++

    $Percent = if ($KeywordTotal -gt 0) {
        [math]::Round(($KeywordIndex / $KeywordTotal) * 100, 1)
    }
    else {
        100
    }

    Write-Progress `
        -Activity "E-ZZIO — Cartographie architecture" `
        -Status "$KeywordIndex / $KeywordTotal — $($File.Name)" `
        -PercentComplete $Percent

    try {

        $Lines = Get-Content `
            -LiteralPath $File.FullName `
            -Encoding UTF8 `
            -ErrorAction Stop

        foreach ($Keyword in $ArchitectureKeywords) {

            $MatchesCount = @(
                $Lines |
                    Select-String `
                        -Pattern ([regex]::Escape($Keyword)) `
                        -SimpleMatch `
                        -ErrorAction SilentlyContinue
            ).Count

            if ($MatchesCount -gt 0) {

                $KeywordHits.Add(
                    [PSCustomObject]@{
                        Keyword = $Keyword
                        File    = $File.FullName
                        Matches = $MatchesCount
                    }
                )
            }
        }
    }
    catch {
        # Non bloquant
    }
}

Write-Progress `
    -Activity "E-ZZIO — Cartographie architecture" `
    -Completed

Write-Host ""
Write-Host "[OK] Cartographie terminée." -ForegroundColor Green
Write-Host ""

# ------------------------------------------------------------------------------
# PHASE 5 — HASH DES SOURCES
# ------------------------------------------------------------------------------

Write-Host "[5/8] EMPREINTES SHA256 DES SOURCES / CONFIGS" -ForegroundColor Yellow
Write-Host ""

$HashFiles = @(
    $Files |
        Where-Object {
            $_.Extension.ToLowerInvariant() -in $HashExtensions
        }
)

$HashResults = [System.Collections.Generic.List[object]]::new()

$HashTotal = $HashFiles.Count
$HashIndex = 0

foreach ($File in $HashFiles) {

    $HashIndex++

    $Percent = if ($HashTotal -gt 0) {
        [math]::Round(($HashIndex / $HashTotal) * 100, 1)
    }
    else {
        100
    }

    Write-Progress `
        -Activity "E-ZZIO — SHA256 sources" `
        -Status "$HashIndex / $HashTotal — $($File.Name)" `
        -PercentComplete $Percent

    try {

        $Hash = Get-FileHash `
            -LiteralPath $File.FullName `
            -Algorithm SHA256 `
            -ErrorAction Stop

        $HashResults.Add(
            [PSCustomObject]@{
                Path   = $File.FullName
                SHA256 = $Hash.Hash
                Bytes  = [Int64]$File.Length
            }
        )
    }
    catch {
        # Non bloquant
    }
}

Write-Progress `
    -Activity "E-ZZIO — SHA256 sources" `
    -Completed

Write-Host ""
Write-Host "[OK] Empreintes terminées." -ForegroundColor Green
Write-Host ""

# ------------------------------------------------------------------------------
# PHASE 6 — GROS FICHIERS
# ------------------------------------------------------------------------------

Write-Host "[6/8] ANALYSE DES PLUS GROS FICHIERS" -ForegroundColor Yellow
Write-Host ""

$LargestFiles = @(
    $FileInventory |
        Sort-Object SizeBytes -Descending |
        Select-Object -First 50
)

Write-Host "TOP 20 :" -ForegroundColor Cyan

$LargestFiles |
    Select-Object -First 20 |
    ForEach-Object {
        Write-Host ""
        Write-Host "  $($_.Size)" -ForegroundColor Magenta
        Write-Host "  $($_.Path)" -ForegroundColor White
    }

Write-Host ""

# ------------------------------------------------------------------------------
# PHASE 7 — CANDIDATS DE REDONDANCE
# ------------------------------------------------------------------------------

Write-Host "[7/8] RECHERCHE DE REDONDANCES EXACTES" -ForegroundColor Yellow
Write-Host ""

$DuplicateGroups = @(
    $FileInventory |
        Where-Object { $_.SizeBytes -gt 0 } |
        Group-Object {
            "$($_.SizeBytes)|$($_.Name.ToLowerInvariant())"
        } |
        Where-Object { $_.Count -gt 1 } |
        Sort-Object Count -Descending
)

Write-Host "Groupes potentiellement redondants : $($DuplicateGroups.Count)" -ForegroundColor White
Write-Host ""

$PotentialDuplicates = [System.Collections.Generic.List[object]]::new()

foreach ($Group in ($DuplicateGroups | Select-Object -First 200)) {

    $Items = @($Group.Group)

    $PotentialDuplicates.Add(
        [PSCustomObject]@{
            Key   = $Group.Name
            Count = $Items.Count
            Files = @($Items.Path)
        }
    )
}

# ------------------------------------------------------------------------------
# PHASE 8 — RAPPORT FINAL
# ------------------------------------------------------------------------------

Write-Host "[8/8] CONSTRUCTION DU RAPPORT GLOBAL" -ForegroundColor Yellow
Write-Host ""

$Report = [PSCustomObject]@{
    AuditDate = (Get-Date).ToString('o')

    Project = [PSCustomObject]@{
        Root       = $ProjectRoot
        TotalFiles = $TotalFiles
        TotalBytes = [Int64]$TotalBytes
        TotalSize  = Format-EzzioSize $TotalBytes
    }

    Statistics = [PSCustomObject]@{
        Extensions = $ExtensionStats
        Categories = $CategoryStats
    }

    Architecture = [PSCustomObject]@{
        PythonFiles       = $PythonFiles.Count
        PowerShellFiles   = $PowerShellFiles.Count
        WebFiles          = $WebFiles.Count
        PythonFunctions   = $PythonFunctions
        PythonClasses     = $PythonClasses
        PythonImports     = $PythonImports
        ArchitectureHits  = $KeywordHits
    }

    Files = $FileInventory

    LargestFiles = $LargestFiles

    PotentialDuplicates = $PotentialDuplicates

    SHA256 = $HashResults

    Git = [PSCustomObject]@{
        Exists = Test-Path -LiteralPath (Join-Path $ProjectRoot '.git')
    }

    ReuseTargets = [PSCustomObject]@{
        Memory    = @($KeywordHits | Where-Object Keyword -in @('memory','cognitive','knowledge','embedding','sqlite'))
        Guardian  = @($KeywordHits | Where-Object Keyword -in @('guardian','recovery','backup','audit'))
        LLM       = @($KeywordHits | Where-Object Keyword -in @('llm','gemini','ollama','model','provider'))
        Tools     = @($KeywordHits | Where-Object Keyword -in @('tool','tools','dispatcher','execution','sandbox'))
        Agents    = @($KeywordHits | Where-Object Keyword -in @('agent','autonomy','autonomous','supervisor'))
        Vision    = @($KeywordHits | Where-Object Keyword -in @('vision','forge','creative'))
        Web       = @($KeywordHits | Where-Object Keyword -in @('web','api','discord'))
        Context   = @($KeywordHits | Where-Object Keyword -in @('context','message','chat','identity','persona'))
    }
}

# ------------------------------------------------------------------------------
# EXPORT JSON
# ------------------------------------------------------------------------------

$Report |
    ConvertTo-Json `
        -Depth 12 |
    Set-Content `
        -LiteralPath $JsonReport `
        -Encoding UTF8

# ------------------------------------------------------------------------------
# EXPORT CSV
# ------------------------------------------------------------------------------

$FileInventory |
    Export-Csv `
        -LiteralPath $CsvReport `
        -NoTypeInformation `
        -Encoding UTF8

# ------------------------------------------------------------------------------
# RAPPORT TEXTE
# ------------------------------------------------------------------------------

$ReportLines = [System.Collections.Generic.List[string]]::new()

$ReportLines.Add('======================================================================')
$ReportLines.Add(' E-ZZIO FULL REUSE AUDIT')
$ReportLines.Add('======================================================================')
$ReportLines.Add('')
$ReportLines.Add("Date       : $($Report.AuditDate)")
$ReportLines.Add("Projet     : $ProjectRoot")
$ReportLines.Add("Fichiers   : $TotalFiles")
$ReportLines.Add("Volume     : $(Format-EzzioSize $TotalBytes)")
$ReportLines.Add('')

$ReportLines.Add('--- LANGAGES / COMPOSANTS ---')
$ReportLines.Add("Python     : $($PythonFiles.Count)")
$ReportLines.Add("PowerShell : $($PowerShellFiles.Count)")
$ReportLines.Add("Web        : $($WebFiles.Count)")
$ReportLines.Add("Fonctions  : $($PythonFunctions.Count)")
$ReportLines.Add("Classes    : $($PythonClasses.Count)")
$ReportLines.Add("Imports    : $($PythonImports.Count)")
$ReportLines.Add('')

$ReportLines.Add('--- TOP EXTENSIONS ---')

foreach ($Item in ($ExtensionStats | Select-Object -First 30)) {
    $ReportLines.Add(
        ("{0,-20} {1,8} fichiers  {2}" -f `
            $Item.Extension,
            $Item.Files,
            $Item.Size)
    )
}

$ReportLines.Add('')
$ReportLines.Add('--- TOP FICHIERS ---')

foreach ($Item in ($LargestFiles | Select-Object -First 30)) {
    $ReportLines.Add("$($Item.Size) | $($Item.Path)")
}

$ReportLines.Add('')
$ReportLines.Add('--- FONCTIONS PYTHON ---')

foreach ($Item in $PythonFunctions) {
    $ReportLines.Add(
        "$($Item.File):$($Item.Line) -> $($Item.Name)"
    )
}

$ReportLines.Add('')
$ReportLines.Add('--- CLASSES PYTHON ---')

foreach ($Item in $PythonClasses) {
    $ReportLines.Add(
        "$($Item.File):$($Item.Line) -> $($Item.Name)"
    )
}

$ReportLines.Add('')
$ReportLines.Add('--- SIGNATURES ARCHITECTURE ---')

foreach ($Item in (
    $KeywordHits |
        Group-Object Keyword |
        Sort-Object Count -Descending
)) {
    $ReportLines.Add(
        "$($Item.Name) : $($Item.Count) occurrences"
    )
}

$ReportLines.Add('')
$ReportLines.Add('--- GROUPES POTENTIELLEMENT REDONDANTS ---')

foreach ($Group in ($PotentialDuplicates | Select-Object -First 100)) {

    $ReportLines.Add(
        "GROUPE $($Group.Key) — $($Group.Count) fichiers"
    )

    foreach ($Path in $Group.Files) {
        $ReportLines.Add("    $Path")
    }
}

$ReportLines |
    Set-Content `
        -LiteralPath $TxtReport `
        -Encoding UTF8

# ------------------------------------------------------------------------------
# FINAL
# ------------------------------------------------------------------------------

Write-Host ""
Write-Host "======================================================================" -ForegroundColor Green
Write-Host " E-ZZIO FULL REUSE AUDIT — TERMINÉ" -ForegroundColor Green
Write-Host "======================================================================" -ForegroundColor Green
Write-Host ""

Write-Host "Fichiers analysés        : $TotalFiles"
Write-Host "Volume total             : $(Format-EzzioSize $TotalBytes)"
Write-Host "Python                   : $($PythonFiles.Count)"
Write-Host "PowerShell               : $($PowerShellFiles.Count)"
Write-Host "Web                      : $($WebFiles.Count)"
Write-Host "Fonctions Python        : $($PythonFunctions.Count)"
Write-Host "Classes Python          : $($PythonClasses.Count)"
Write-Host "Imports Python          : $($PythonImports.Count)"
Write-Host "Signatures architecture : $($KeywordHits.Count)"
Write-Host "Hashes SHA256            : $($HashResults.Count)"
Write-Host "Groupes redondants       : $($PotentialDuplicates.Count)"
Write-Host ""

Write-Host "RAPPORT JSON :" -ForegroundColor Cyan
Write-Host "  $JsonReport"

Write-Host ""
Write-Host "RAPPORT TXT :" -ForegroundColor Cyan
Write-Host "  $TxtReport"

Write-Host ""
Write-Host "INVENTAIRE CSV :" -ForegroundColor Cyan
Write-Host "  $CsvReport"

Write-Host ""
Write-Host "READ ONLY : aucun fichier E-ZZIO n'a été modifié." -ForegroundColor Green
Write-Host ""