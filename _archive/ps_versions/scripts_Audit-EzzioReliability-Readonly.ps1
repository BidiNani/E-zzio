[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$RootPath = "G:\AI\E-zzio"
Set-Location $RootPath

$ReliabilityAuditDir = "$RootPath\runtime\audit\reliability"
New-Item -ItemType Directory -Force -Path $ReliabilityAuditDir | Out-Null

Write-Host "[*] Démarrage de l'audit de fiabilité optimisé (v1.5)..." -ForegroundColor Cyan

$ExcludedDirs = @("\.venv", "\.git", "__pycache__", "\node_modules", "\archive")

$AllFiles = Get-ChildItem -Path $RootPath -Recurse -File | Where-Object {
    $path = $_.FullName
    $skip = $false
    foreach ($ex in $ExcludedDirs) {
        if ($path -match [regex]::Escape($ex)) { $skip = $true; break }
    }
    -not $skip -and ($_.Extension -in @(".py", ".ps1", ".json", ".md"))
}

$Corpus = @{}
$CorpusPathsLower = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)

foreach ($file in $AllFiles) {
    $relPath = $file.FullName.Substring($RootPath.Length + 1)
    $CorpusPathsLower.Add($relPath.ToLower())
    try {
        $raw = Get-Content $file.FullName -Raw -ErrorAction SilentlyContinue
        $Corpus[$relPath] = if ($null -ne $raw) { $raw } else { "" }
    } catch {
        $Corpus[$relPath] = ""
    }
}

$DependencyGraph = @()
$BrokenReferences = @()

foreach ($path in $Corpus.Keys) {
    $content = $Corpus[$path]
    if ($null -eq $content) { continue }
    
    $ext = [System.IO.Path]::GetExtension($path)
    $references = @()

    if ($ext -eq ".py" -and $content.Length -gt 0) {
        $matches = [regex]::Matches($content, '^\s*(?:import|from)\s+([a-zA-Z0-9_\.]+)', [System.Text.RegularExpressions.RegexOptions]::Multiline)
        foreach ($m in $matches) {
            $modName = $m.Groups[1].Value -replace '\.', '\'
            $references += "$modName.py"
        }
    }
    elseif (($ext -eq ".ps1" -or $ext -eq ".json") -and $content.Length -gt 0) {
        $matches = [regex]::Matches($content, '["'']([^"'']+\.(?:ps1|py|json))["'']')
        foreach ($m in $matches) {
            $references += $m.Groups[1].Value
        }
    }

    foreach ($ref in $references) {
        $cleanRef = ($ref -replace '/', '\').ToLower()
        $resolved = $false
        
        # Recherche instantanée via l'index en mémoire O(1)
        foreach ($knownPath in $CorpusPathsLower) {
            if ($knownPath.EndsWith($cleanRef) -or $knownPath.Contains($cleanRef)) {
                $resolved = $true
                break
            }
        }

        $DependencyGraph += [PSCustomObject]@{
            Source    = $path
            Reference = $ref
            Resolved  = $resolved
        }

        if (-not $resolved -and $ref -notmatch "^(?:uvicorn|psutil|logging|json|pathlib|urllib|time|os|sys|subprocess|asyncio|fastapi|pydantic|typing)\.py$") {
            $BrokenReferences += [PSCustomObject]@{
                Source    = $path
                Reference = $ref
            }
        }
    }
}

$GraphReportPath = "$ReliabilityAuditDir\dependency_graph.json"
$DependencyGraph | ConvertTo-Json -Depth 5 | Set-Content $GraphReportPath -Encoding UTF8

$BrokenReportPath = "$ReliabilityAuditDir\broken_references.json"
$BrokenReferences | ConvertTo-Json -Depth 5 | Set-Content $BrokenReportPath -Encoding UTF8

Write-Host "`n=== SYNTHÈSE DE FIABILITÉ (PHASES 1 & 2) ===" -ForegroundColor Cyan
Write-Host "Total dépendances indexées : $($DependencyGraph.Count)" -ForegroundColor Yellow
Write-Host "Références brisées : $($BrokenReferences.Count)" -ForegroundColor $(if($BrokenReferences.Count -eq 0){"Green"}else{"Red"})
Write-Host "[OK] Rapports générés dans : $ReliabilityAuditDir" -ForegroundColor Green
