```powershell
# ==============================================================================
# E-ZZIO FULL REUSE AUDIT v1.2 — CORRECTION STRICTMODE
# ==============================================================================
# CORRECTIONS :
#   - $_ correctement utilisé
#   - suppression des "|*" / "*Group-Object"
#   - aucune modification du projet E-ZZIO
#   - SHA256 conservé
#   - détection des doublons conservée
#   - scoring de réutilisabilité conservé
# ==============================================================================

# -------------------- PHASE 3 : ANALYSE SOURCES --------------------

Write-Host "[3/7] Analyse sources (passe unique, patchée)..." -ForegroundColor Yellow

$PythonFunctions = [System.Collections.Generic.List[object]]::new()
$PythonClasses   = [System.Collections.Generic.List[object]]::new()
$PythonImports   = [System.Collections.Generic.List[object]]::new()
$KeywordHits     = [System.Collections.Generic.List[object]]::new()
$ReuseScores     = [System.Collections.Generic.List[object]]::new()

$SourceFiles = @(
    $Files | Where-Object {
        $_.Extension.ToLowerInvariant() -in @(
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
    }
)

$sIdx = 0
$sTotal = [math]::Max($SourceFiles.Count, 1)

foreach ($file in $SourceFiles) {

    $sIdx++

    if (($sIdx % 25) -eq 0 -or $sIdx -eq $SourceFiles.Count) {
        Write-Progress `
            -Activity "Analyse des sources" `
            -Status "$sIdx / $($SourceFiles.Count) : $($file.Name)" `
            -PercentComplete (($sIdx / $sTotal) * 100)
    }

    $isPy = $file.Extension.ToLowerInvariant() -eq '.py'

    $funcCount   = 0
    $classCount  = 0
    $importCount = 0
    $keywordScore = 0

    $hitKeywords = @{}

    try {

        $content = Get-Content `
            -LiteralPath $file.FullName `
            -Raw `
            -ErrorAction Stop

        # ----------------------------------------------------------------------
        # PYTHON
        # ----------------------------------------------------------------------

        if ($isPy) {

            $functionMatches = [regex]::Matches(
                $content,
                '(?m)^\s*(?:async\s+)?def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\('
            )

            foreach ($match in $functionMatches) {

                $funcCount++

                $PythonFunctions.Add(
                    [PSCustomObject]@{
                        File = $file.FullName
                        Name = $match.Groups[1].Value
                    }
                )
            }

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
        # KEYWORDS ARCHITECTURE
        # ----------------------------------------------------------------------

        foreach ($kw in $ArchitectureKeywords.Keys) {

            $count = [regex]::Matches(
                $content,
                [regex]::Escape($kw),
                [System.Text.RegularExpressions.RegexOptions]::IgnoreCase
            ).Count

            if ($count -gt 0) {

                $hitKeywords[$kw] = $count

                $keywordScore += `
                    $count * [int]$ArchitectureKeywords[$kw]
            }
        }

        # ----------------------------------------------------------------------
        # ENREGISTREMENT DES KEYWORD HITS
        # ----------------------------------------------------------------------

        foreach ($kw in $hitKeywords.Keys) {

            $KeywordHits.Add(
                [PSCustomObject]@{
                    Keyword = $kw
                    File    = $file.FullName
                    Matches = $hitKeywords[$kw]
                    Weight  = $ArchitectureKeywords[$kw]
                }
            )
        }

        # ----------------------------------------------------------------------
        # SCORE DE RÉUTILISABILITÉ
        # ----------------------------------------------------------------------

        $score = 0

        if ($isPy) {

            $score += [math]::Min($funcCount * 3, 30)
            $score += [math]::Min($classCount * 5, 25)
            $score += [math]::Min($importCount, 15)
            $score += [math]::Min($keywordScore, 20)

            if (
                $file.DirectoryName -match '\\(core|memory|tools|agents|runtime|guardian)\\'
            ) {
                $score += 10
            }
        }
        elseif (
            $file.Extension.ToLowerInvariant() -in @('.ps1', '.psm1')
        ) {

            $score += [math]::Min($keywordScore, 40)

            if (
                $file.Name -match 'watchdog|daemon|audit|guardian|start_'
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
                    Extension    = $file.Extension
                    Score        = [math]::Min($score, 100)
                    Functions    = $funcCount
                    Classes      = $classCount
                    KeywordScore = $keywordScore
                }
            )
        }

    }
    catch {
        # READ ONLY :
        # une erreur de lecture n'arrête pas tout l'audit.
    }
}

Write-Progress -Activity "Analyse des sources" -Completed

Write-Host (
    "  → Fonctions: {0} | Classes: {1} | Imports: {2}" -f `
    $PythonFunctions.Count,
    $PythonClasses.Count,
    $PythonImports.Count
) -ForegroundColor Green


# -------------------- PHASE 4 : SHA256 --------------------

Write-Host "[4/7] Empreintes SHA256 (sources/configs)..." -ForegroundColor Yellow

$HashResults = [System.Collections.Generic.List[object]]::new()

$HashFiles = @(
    $Files | Where-Object {
        $_.Extension.ToLowerInvariant() -in $HashExtensions
    }
)

$hIdx = 0
$hTotal = [math]::Max($HashFiles.Count, 1)

foreach ($f in $HashFiles) {

    $hIdx++

    if (
        ($hIdx % 25) -eq 0 -or
        $hIdx -eq $HashFiles.Count
    ) {

        Write-Progress `
            -Activity "SHA256" `
            -Status "$hIdx / $($HashFiles.Count) : $($f.Name)" `
            -PercentComplete (($hIdx / $hTotal) * 100)
    }

    try {

        $h = Get-FileHash `
            -LiteralPath $f.FullName `
            -Algorithm SHA256 `
            -ErrorAction Stop

        $HashResults.Add(
            [PSCustomObject]@{
                Path   = $f.FullName
                SHA256 = $h.Hash
                Bytes  = [Int64]$f.Length
            }
        )
    }
    catch {
        # READ ONLY : fichier inaccessible ignoré.
    }
}

Write-Progress -Activity "SHA256" -Completed


# -------------------- PHASE 5 : GROS FICHIERS --------------------

Write-Host "[5/7] Plus gros fichiers..." -ForegroundColor Yellow

$LargestFiles = @(
    $FileInventory |
        Sort-Object SizeBytes -Descending |
        Select-Object -First 40
)


# -------------------- PHASE 6 : REDONDANCES --------------------

Write-Host "[6/7] Redondances (Name+Size → SHA256)..." -ForegroundColor Yellow

# Première passe :
# mêmes nom + même taille
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

$PotentialDuplicates = [System.Collections.Generic.List[object]]::new()

$filesToHash = [System.Collections.Generic.List[object]]::new()

foreach ($g in $phaseA) {

    foreach ($item in $g.Group) {
        $filesToHash.Add($item)
    }
}

$hashMap = @{}

$dIdx = 0
$dTotal = [math]::Max($filesToHash.Count, 1)

foreach ($item in $filesToHash) {

    $dIdx++

    if (
        ($dIdx % 25) -eq 0 -or
        $dIdx -eq $filesToHash.Count
    ) {

        Write-Progress `
            -Activity "Validation des doublons SHA256" `
            -Status "$dIdx / $($filesToHash.Count)" `
            -PercentComplete (($dIdx / $dTotal) * 100)
    }

    try {

        $h = (
            Get-FileHash `
                -LiteralPath $item.Path `
                -Algorithm SHA256 `
                -ErrorAction Stop
        ).Hash

        if (-not $hashMap.ContainsKey($h)) {

            $hashMap[$h] =
                [System.Collections.Generic.List[string]]::new()
        }

        $hashMap[$h].Add($item.Path)
    }
    catch {
        # Fichier inaccessible : ignoré.
    }
}

Write-Progress -Activity "Validation des doublons SHA256" -Completed


foreach ($h in $hashMap.Keys) {

    $paths = $hashMap[$h]

    if ($paths.Count -gt 1) {

        $PotentialDuplicates.Add(
            [PSCustomObject]@{
                SHA256 = $h
                Count  = $paths.Count
                Files  = @($paths)
            }
        )
    }
}

Write-Host (
    "  → Groupes exacts (SHA256) : {0}" -f
    $PotentialDuplicates.Count
) -ForegroundColor Green


# -------------------- PHASE 7 : RAPPORT --------------------

Write-Host "[7/7] Génération des rapports..." -ForegroundColor Yellow

$TopReusable = @(
    $ReuseScores |
        Sort-Object Score -Descending |
        Select-Object -First 50
)

$Report = [ordered]@{

    AuditDate = (Get-Date).ToString('o')

    Version = '1.2'

    Project = @{
        Root       = $ProjectRoot
        TotalFiles = $TotalFiles
        TotalBytes = [Int64]$TotalBytes
        TotalSize  = Format-Size $TotalBytes
    }

    Statistics = @{
        Extensions = $ExtensionStats
        Categories = $CategoryStats
    }

    Architecture = @{

        PythonFiles = @(
            $Files |
                Where-Object {
                    $_.Extension.ToLowerInvariant() -eq '.py'
                }
        ).Count

        PowerShellFiles = @(
            $Files |
                Where-Object {
                    $_.Extension.ToLowerInvariant() -in @(
                        '.ps1',
                        '.psm1',
                        '.psd1'
                    )
                }
        ).Count

        WebFiles = @(
            $Files |
                Where-Object {
                    $_.Extension.ToLowerInvariant() -in @(
                        '.js',
                        '.jsx',
                        '.ts',
                        '.tsx',
                        '.svelte',
                        '.vue'
                    )
                }
        ).Count

        PythonFunctions = $PythonFunctions
        PythonClasses   = $PythonClasses
        PythonImports   = $PythonImports
        ArchitectureHits = $KeywordHits
    }

    TopReusable      = $TopReusable
    LargestFiles     = $LargestFiles
    ExactDuplicates  = $PotentialDuplicates
    SHA256           = $HashResults

    Git = @{
        Exists = (
            Test-Path (
                Join-Path $ProjectRoot '.git'
            )
        )
    }
}


# -------------------- JSON --------------------

$Report |
    ConvertTo-Json -Depth 10 |
    Set-Content `
        -LiteralPath $JsonReport `
        -Encoding UTF8


# -------------------- CSV --------------------

$FileInventory |
    Export-Csv `
        -LiteralPath $CsvReport `
        -NoTypeInformation `
        -Encoding UTF8


# -------------------- TXT --------------------

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

    $Lines.Add(
        (
            '{0,-18} {1,8} fichiers  {2}' -f
            $e.Extension,
            $e.Files,
            $e.Size
        )
    )
}

$Lines.Add('')

$Lines.Add('--- TOP FICHIERS RÉUTILISABLES (score) ---')

foreach ($r in ($TopReusable | Select-Object -First 30)) {

    $Lines.Add(
        (
            '{0,3} pts | {1}' -f
            $r.Score,
            $r.RelativePath
        )
    )
}

$Lines.Add('')

$Lines.Add('--- DOUBLONS EXACTS (SHA256) ---')
$Lines.Add("Groupes : $($PotentialDuplicates.Count)")

foreach ($d in ($PotentialDuplicates | Select-Object -First 40)) {

    $Lines.Add(
        "SHA256 $($d.SHA256.Substring(0,12))...  x$($d.Count)"
    )

    foreach ($p in $d.Files) {
        $Lines.Add("   - $p")
    }
}

$Lines |
    Set-Content `
        -LiteralPath $TxtReport `
        -Encoding UTF8


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
```
