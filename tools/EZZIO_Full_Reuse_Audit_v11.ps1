# ==============================================================================
# E-ZZIO FULL REUSE AUDIT v1.2 (PATCH STRICTMODE)
# READ ONLY — AUCUN DELETE / MOVE / MODIFY
# ==============================================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# -------------------- CONFIG --------------------
$ProjectRoot   = 'G:\AI\E-zzio'
$ReportRoot    = Join-Path $ProjectRoot 'runtime\audit\full_reuse'
$Timestamp     = Get-Date -Format 'yyyyMMdd_HHmmss'
$JsonReport    = Join-Path $ReportRoot "EZZIO_FULL_REUSE_v12_$Timestamp.json"
$TxtReport     = Join-Path $ReportRoot "EZZIO_FULL_REUSE_v12_$Timestamp.txt"
$CsvReport     = Join-Path $ReportRoot "EZZIO_FULL_REUSE_FILES_v12_$Timestamp.csv"

$ExcludedDirs = @('.git', '__pycache__', 'node_modules', '.venv', 'venv', 'env')

$SourceExtensions = @(
    '.py','.ps1','.psm1','.psd1','.js','.jsx','.ts','.tsx',
    '.svelte','.vue','.json','.yaml','.yml','.toml','.ini',
    '.cfg','.conf','.xml','.md','.txt','.sql','.bat','.cmd'
)

$HashExtensions = @(
    '.py','.ps1','.psm1','.psd1','.js','.jsx','.ts','.tsx',
    '.svelte','.vue','.json','.yaml','.yml','.toml','.ini',
    '.cfg','.conf','.xml','.sql'
)

# Keywords pondérés
$ArchitectureKeywords = @{
    'guardian'     = 5; 'cognitive'    = 5; 'memory'       = 4
    'embedding'    = 4; 'orchestr'     = 4; 'dispatcher'   = 4
    'supervisor'   = 4; 'autonomy'     = 4; 'autonomous'   = 4
    'recovery'     = 3; 'sandbox'      = 3; 'persona'      = 3
    'identity'     = 3; 'telemetry'    = 3; 'llm'          = 3
    'ollama'       = 3; 'gemini'       = 3; 'provider'     = 3
    'router'       = 3; 'agent'        = 3; 'tool'         = 2
    'tools'        = 2; 'pipeline'     = 2; 'context'      = 2
    'knowledge'    = 2; 'vision'       = 2; 'forge'        = 2
    'discord'      = 2; 'web_server'   = 2; 'sqlite'       = 2
    'audit'        = 1; 'backup'       = 1; 'model'        = 1
    'api'          = 1
}

# -------------------- VALIDATION --------------------
if (-not (Test-Path -LiteralPath $ProjectRoot)) {
    throw "Projet introuvable : $ProjectRoot"
}
New-Item -ItemType Directory -Path $ReportRoot -Force | Out-Null
Set-Location -LiteralPath $ProjectRoot

# -------------------- HELPERS --------------------
function Format-Size {
    param([Int64]$Bytes)
    switch ($Bytes) {
        { $_ -ge 1TB } { '{0:N2} TB' -f ($Bytes / 1TB); break }
        { $_ -ge 1GB } { '{0:N2} GB' -f ($Bytes / 1GB); break }
        { $_ -ge 1MB } { '{0:N2} MB' -f ($Bytes / 1MB); break }
        { $_ -ge 1KB } { '{0:N2} KB' -f ($Bytes / 1KB); break }
        default { "$Bytes B" }
    }
}

function Test-Excluded {
    param([string]$Path)
    foreach ($d in $ExcludedDirs) {
        if ($Path -match [regex]::Escape("\$d\") -or $Path.EndsWith("\$d")) {
            return $true
        }
    }
    return $false
}

function Get-Category {
    param([string]$Ext)
    switch ($Ext.ToLowerInvariant()) {
        '.py'      { 'Python' }
        '.ps1'     { 'PowerShell' }
        '.psm1'    { 'PowerShell Module' }
        '.psd1'    { 'PowerShell Data' }
        '.js'      { 'JavaScript' }
        '.jsx'     { 'JavaScript React' }
        '.ts'      { 'TypeScript' }
        '.tsx'     { 'TypeScript React' }
        '.svelte'  { 'Svelte' }
        '.vue'     { 'Vue' }
        '.json'    { 'JSON' }
        '.yaml'    { 'YAML' }
        '.yml'     { 'YAML' }
        '.toml'    { 'TOML' }
        '.md'      { 'Documentation' }
        '.sql'     { 'SQL' }
        '.db'      { 'Database' }
        '.sqlite'  { 'Database' }
        '.sqlite3' { 'Database' }
        default    { 'Other' }
    }
}

# -------------------- HEADER --------------------
Clear-Host
Write-Host ""
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host " E-ZZIO FULL REUSE AUDIT v1.2 (STRICTMODE PATCHED)" -ForegroundColor Cyan
Write-Host " READ ONLY — AUCUNE MODIFICATION" -ForegroundColor Green
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""

# -------------------- PHASE 1 : INVENTAIRE --------------------
Write-Host "[1/7] Inventaire des fichiers..." -ForegroundColor Yellow

$Files = @(
    Get-ChildItem -LiteralPath $ProjectRoot -Recurse -File -Force -ErrorAction SilentlyContinue |
    Where-Object { -not (Test-Excluded -Path $_.FullName) }
)

$TotalFiles = $Files.Count
$FileInventory = [System.Collections.Generic.List[object]]::new()
$idx = 0

foreach ($f in $Files) {
    $idx++
    if ($idx % 200 -eq 0 -or $idx -eq $TotalFiles) {
        $pct = [math]::Round(($idx / [math]::Max($TotalFiles,1)) * 100, 1)
        Write-Progress -Activity "Inventaire" -Status "$idx / $TotalFiles" -PercentComplete $pct
    }

    $ext = if ([string]::IsNullOrWhiteSpace($f.Extension)) { '(sans extension)' } else { $f.Extension }

    $FileInventory.Add([PSCustomObject]@{
        Path         = $f.FullName
        RelativePath = $f.FullName.Substring($ProjectRoot.Length).TrimStart('\')
        Name         = $f.Name
        Extension    = $ext
        Category     = Get-Category $ext
        SizeBytes    = [Int64]$f.Length
        Size         = Format-Size $f.Length
        LastWriteTime= $f.LastWriteTime
    })
}
Write-Progress -Activity "Inventaire" -Completed

$TotalBytes = ($FileInventory | Measure-Object SizeBytes -Sum).Sum
Write-Host "  → $TotalFiles fichiers | $(Format-Size $TotalBytes)" -ForegroundColor Green

# -------------------- PHASE 2 : STATS --------------------
Write-Host "[2/7] Statistiques..." -ForegroundColor Yellow

$ExtensionStats = @(
    $FileInventory | Group-Object Extension | ForEach-Object {
        $b = ($_.Group | Measure-Object SizeBytes -Sum).Sum
        [PSCustomObject]@{
            Extension = $_.Name
            Files     = $_.Count
            Bytes     = [Int64]$b
            Size      = Format-Size $b
        }
    } | Sort-Object Bytes -Descending
)

$CategoryStats = @(
    $FileInventory | Group-Object Category | ForEach-Object {
        $b = ($_.Group | Measure-Object SizeBytes -Sum).Sum
        [PSCustomObject]@{
            Category = $_.Name
            Files    = $_.Count
            Bytes    = [Int64]$b
            Size     = Format-Size $b
        }
    } | Sort-Object Bytes -Descending
)

# -------------------- PHASE 3 : ANALYSE SOURCE (BLINDÉE) --------------------
Write-Host "[3/7] Analyse sources (passe unique, patchée)..." -ForegroundColor Yellow

$PythonFunctions = [System.Collections.Generic.List[object]]::new()
$PythonClasses   = [System.Collections.Generic.List[object]]::new()
$PythonImports   = [System.Collections.Generic.List[object]]::new()
$KeywordHits     = [System.Collections.Generic.List[object]]::new()
$ReuseScores     = [System.Collections.Generic.List[object]]::new()

$SourceFiles = @($Files | Where-Object { $_.Extension.ToLowerInvariant() -in $SourceExtensions })
$srcTotal = $SourceFiles.Count
$srcIdx = 0

foreach ($file in $SourceFiles) {
    $srcIdx++
    if ($srcIdx % 50 -eq 0 -or $srcIdx -eq $srcTotal) {
        $pct = [math]::Round(($srcIdx / [math]::Max($srcTotal,1)) * 100, 1)
        Write-Progress -Activity "Analyse sources" -Status "$srcIdx / $srcTotal — $($file.Name)" -PercentComplete $pct
    }

    $isPy = ($file.Extension -eq '.py')
    
    # --- CORRECTIF APPLIQUÉ ICI ---
    $content = $null
    try {
        $raw = Get-Content -LiteralPath $file.FullName -Encoding UTF8 -ErrorAction Stop
        $content = @($raw)   # ← force tableau même si 0 ou 1 ligne
    } catch {
        continue
    }

    if ($null -eq $content -or $content.Count -eq 0) {
        continue
    }

    $funcCount = 0
    $classCount = 0
    $importCount = 0
    $keywordScore = 0
    $hitKeywords = @{}

    for ($i = 0; $i -lt $content.Count; $i++) {
        $line = $content[$i]

        if ($isPy) {
            if ($line -match '^\s*(async\s+)?def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(') {
                $PythonFunctions.Add([PSCustomObject]@{
                    File = $file.FullName
                    Line = $i + 1
                    Name = $Matches[2]
                    Async = [bool]$Matches[1]
                })
                $funcCount++
            }
            if ($line -match '^\s*class\s+([A-Za-z_][A-Za-z0-9_]*)') {
                $PythonClasses.Add([PSCustomObject]@{
                    File = $file.FullName
                    Line = $i + 1
                    Name = $Matches[1]
                })
                $classCount++
            }
            if ($line -match '^\s*(from\s+\S+\s+import\s+.+|import\s+\S+)') {
                $PythonImports.Add([PSCustomObject]@{
                    File   = $file.FullName
                    Line   = $i + 1
                    Import = $line.Trim()
                })
                $importCount++
            }
        }

        foreach ($kw in $ArchitectureKeywords.Keys) {
            if ($line -match [regex]::Escape($kw)) {
                $weight = $ArchitectureKeywords[$kw]
                $keywordScore += $weight
                if (-not $hitKeywords.ContainsKey($kw)) {
                    $hitKeywords[$kw] = 0
                }
                $hitKeywords[$kw]++
            }
        }
    }
    # --- FIN DU CORRECTIF ---

    foreach ($kw in $hitKeywords.Keys) {
        $KeywordHits.Add([PSCustomObject]@{
            Keyword = $kw
            File    = $file.FullName
            Matches = $hitKeywords[$kw]
            Weight  = $ArchitectureKeywords[$kw]
        })
    }

    $score = 0
    if ($isPy) {
        $score += [math]::Min($funcCount * 3, 30)
        $score += [math]::Min($classCount * 5, 25)
        $score += [math]::Min($importCount, 15)
        $score += [math]::Min($keywordScore, 20)
        if ($file.DirectoryName -match '\\(core|memory|tools|agents|runtime|guardian)\\') {
            $score += 10
        }
    } elseif ($file.Extension -in @('.ps1','.psm1')) {
        $score += [math]::Min($keywordScore, 40)
        if ($file.Name -match 'watchdog|daemon|audit|guardian|start_') {
            $score += 15
        }
    }

    if ($score -gt 0) {
        $ReuseScores.Add([PSCustomObject]@{
            Path          = $file.FullName
            RelativePath  = $file.FullName.Substring($ProjectRoot.Length).TrimStart('\')
            Extension     = $file.Extension
            Score         = [math]::Min($score, 100)
            Functions     = $funcCount
            Classes       = $classCount
            KeywordScore  = $keywordScore
        })
    }
}
Write-Progress -Activity "Analyse sources" -Completed

Write-Host "  → Fonctions: $($PythonFunctions.Count) | Classes: $($PythonClasses.Count) | Imports: $($PythonImports.Count)" -ForegroundColor Green

# -------------------- PHASE 4 : SHA256 (sources seulement) --------------------
Write-Host "[4/7] Empreintes SHA256 (sources/configs)..." -ForegroundColor Yellow

$HashResults = [System.Collections.Generic.List[object]]::new()
$HashFiles = @($Files | Where-Object { $_.Extension.ToLowerInvariant() -in $HashExtensions })
$hIdx = 0
foreach ($f in $HashFiles) {
    $hIdx++
    if ($hIdx % 100 -eq 0) {
        Write-Progress -Activity "SHA256" -Status "$hIdx / $($HashFiles.Count)" -PercentComplete (($hIdx / $HashFiles.Count) * 100)
    }
    try {
        $h = Get-FileHash -LiteralPath $f.FullName -Algorithm SHA256 -ErrorAction Stop
        $HashResults.Add([PSCustomObject]@{
            Path   = $f.FullName
            SHA256 = $h.Hash
            Bytes  = [Int64]$f.Length
        })
    } catch {}
}
Write-Progress -Activity "SHA256" -Completed

# -------------------- PHASE 5 : GROS FICHIERS --------------------
Write-Host "[5/7] Plus gros fichiers..." -ForegroundColor Yellow
$LargestFiles = @($FileInventory | Sort-Object SizeBytes -Descending | Select-Object -First 40)

# -------------------- PHASE 6 : REDONDANCES 2 PHASES --------------------
Write-Host "[6/7] Redondances (Name+Size → SHA256)..." -ForegroundColor Yellow

$phaseA = @(
    $FileInventory |
    Where-Object { $_.SizeBytes -gt 0 } |
    Group-Object { "$($_.SizeBytes)|$($_.Name.ToLowerInvariant())" } |
    Where-Object { $_.Count -gt 1 }
)

$PotentialDuplicates = [System.Collections.Generic.List[object]]::new()
$filesToHash = @()
foreach ($g in $phaseA) {
    $filesToHash += $g.Group
}

$hashMap = @{}
foreach ($item in $filesToHash) {
    try {
        $h = (Get-FileHash -LiteralPath $item.Path -Algorithm SHA256 -ErrorAction Stop).Hash
        if (-not $hashMap.ContainsKey($h)) {
            $hashMap[$h] = [System.Collections.Generic.List[string]]::new()
        }
        $hashMap[$h].Add($item.Path)
    } catch {}
}

foreach ($h in $hashMap.Keys) {
    $paths = $hashMap[$h]
    if ($paths.Count -gt 1) {
        $PotentialDuplicates.Add([PSCustomObject]@{
            SHA256 = $h
            Count  = $paths.Count
            Files  = @($paths)
        })
    }
}

Write-Host "  → Groupes exacts (SHA256) : $($PotentialDuplicates.Count)" -ForegroundColor Green

# -------------------- PHASE 7 : RAPPORT --------------------
Write-Host "[7/7] Génération des rapports..." -ForegroundColor Yellow

$TopReusable = @($ReuseScores | Sort-Object Score -Descending | Select-Object -First 50)

$Report = [ordered]@{
    AuditDate     = (Get-Date).ToString('o')
    Version       = '1.2'
    Project       = @{
        Root       = $ProjectRoot
        TotalFiles = $TotalFiles
        TotalBytes = [Int64]$TotalBytes
        TotalSize  = Format-Size $TotalBytes
    }
    Statistics    = @{
        Extensions = $ExtensionStats
        Categories = $CategoryStats
    }
    Architecture  = @{
        PythonFiles      = @($Files | Where-Object Extension -eq '.py').Count
        PowerShellFiles  = @($Files | Where-Object { $_.Extension -in @('.ps1','.psm1','.psd1') }).Count
        WebFiles         = @($Files | Where-Object { $_.Extension -in @('.js','.jsx','.ts','.tsx','.svelte','.vue') }).Count
        PythonFunctions  = $PythonFunctions
        PythonClasses    = $PythonClasses
        PythonImports    = $PythonImports
        ArchitectureHits = $KeywordHits
    }
    TopReusable   = $TopReusable
    LargestFiles  = $LargestFiles
    ExactDuplicates = $PotentialDuplicates
    SHA256        = $HashResults
    Git           = @{ Exists = (Test-Path (Join-Path $ProjectRoot '.git')) }
}

$Report | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $JsonReport -Encoding UTF8
$FileInventory | Export-Csv -LiteralPath $CsvReport -NoTypeInformation -Encoding UTF8

# TXT résumé
$Lines = [System.Collections.Generic.List[string]]::new()
$Lines.Add('E-ZZIO FULL REUSE AUDIT v1.2')
$Lines.Add('==========================================')
$Lines.Add("Date     : $($Report.AuditDate)")
$Lines.Add("Projet   : $ProjectRoot")
$Lines.Add("Fichiers : $TotalFiles")
$Lines.Add("Volume   : $(Format-Size $TotalBytes)")
$Lines.Add('')
$Lines.Add('--- TOP EXTENSIONS ---')
foreach ($e in ($ExtensionStats | Select-Object -First 15)) {
    $Lines.Add(('{0,-18} {1,8} fichiers  {2}' -f $e.Extension, $e.Files, $e.Size))
}
$Lines.Add('')
$Lines.Add('--- TOP FICHIERS RÉUTILISABLES (score) ---')
foreach ($r in ($TopReusable | Select-Object -First 30)) {
    $Lines.Add(('{0,3} pts | {1}' -f $r.Score, $r.RelativePath))
}
$Lines.Add('')
$Lines.Add('--- DOUBLONS EXACTS (SHA256) ---')
$Lines.Add("Groupes : $($PotentialDuplicates.Count)")
foreach ($d in ($PotentialDuplicates | Select-Object -First 30)) {
    $Lines.Add("SHA256 $($d.SHA256.Substring(0,12))...  x$($d.Count)")
    foreach ($p in $d.Files) { $Lines.Add("   - $p") }
}
$Lines | Set-Content -LiteralPath $TxtReport -Encoding UTF8

# -------------------- FINAL --------------------
Write-Host ""
Write-Host "======================================================================" -ForegroundColor Green
Write-Host " AUDIT v1.2 TERMINÉ" -ForegroundColor Green
Write-Host "======================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Fichiers          : $TotalFiles"
Write-Host "Volume            : $(Format-Size $TotalBytes)"
Write-Host "Fonctions Python  : $($PythonFunctions.Count)"
Write-Host "Classes Python    : $($PythonClasses.Count)"
Write-Host "Top réutilisables : $($TopReusable.Count)"
Write-Host "Doublons exacts   : $($PotentialDuplicates.Count)"
Write-Host ""
Write-Host "JSON : $JsonReport"
Write-Host "TXT  : $TxtReport"
Write-Host "CSV  : $CsvReport"
Write-Host ""
Write-Host "READ ONLY — aucun fichier modifié." -ForegroundColor Green
Write-Host ""