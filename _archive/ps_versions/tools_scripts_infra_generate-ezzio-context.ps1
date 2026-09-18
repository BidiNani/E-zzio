param(
    [string]$RootPath = ".",
    [string]$OutputFile = "EZZIO_CONTEXT.md"
)

$includeExtensions = @(
    ".md", ".txt", ".lua", ".py", ".ps1", ".sh", ".bat",
    ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg",
    ".gitignore", ".editorconfig"
)

$excludeDirs = @("node_modules", ".git", "__pycache__", ".venv", "dist", "build", "output", "audit")
$excludeFiles = @("package-lock.json", "yarn.lock", "Cargo.lock", "*.log", "*.sqlite", "*.db", "*.zip")

function Should-IncludeFile {
    param([string]$FilePath)
    $fileName = Split-Path $FilePath -Leaf
    $ext = (Get-Item $FilePath).Extension.ToLower()
    if ($includeExtensions -notcontains $ext) { return $false }
    foreach ($ex in $excludeFiles) {
        if ($fileName -like $ex) { return $false }
    }
    return $true
}

function Should-IncludeDir {
    param([string]$DirPath)
    $dirName = Split-Path $DirPath -Leaf
    return $excludeDirs -notcontains $dirName
}

$treeLines = [System.Collections.Generic.List[string]]::new()
$treeLines.Add("# Projet E-zzio - Cartographie & Contexte")
$treeLines.Add("")
$treeLines.Add("## Structure des fichiers")
$treeLines.Add('```')

$allFiles = Get-ChildItem -Path $RootPath -Recurse -File | Where-Object {
    $dirOk = $true
    $parts = $_.DirectoryName.Substring($RootPath.Length).Split([System.IO.Path]::DirectorySeparatorChar)
    foreach ($p in $parts) {
        if ($excludeDirs -contains $p) { $dirOk = $false; break }
    }
    $dirOk -and (Should-IncludeFile $_.FullName)
} | Sort-Object FullName

foreach ($f in $allFiles) {
    $rel = $f.FullName.Substring((Resolve-Path $RootPath).Path.Length).TrimStart('\','/')
    $treeLines.Add($rel)
}
$treeLines.Add('```')
$treeLines.Add("")
$treeLines.Add("## Contenu des sources critiques")
$treeLines.Add("")

foreach ($f in $allFiles) {
    $rel = $f.FullName.Substring((Resolve-Path $RootPath).Path.Length).TrimStart('\','/')
    $treeLines.Add("### Fichier : $rel")
    $ext = $f.Extension.TrimStart('.')
$treeLines.Add(('```' + $ext))
    try {
        $content = Get-Content $f.FullName -Raw -Encoding UTF8
        $lines = $content -split "`n"
        if ($lines.Count -gt 500) {
            $content = ($lines[0..499] -join "`n") + "`n# ... [Tronque a 500 lignes]"
        }
        $treeLines.Add($content)
    } catch {
        $treeLines.Add("# Lecture impossible")
    }
$treeLines.Add('```')
    $treeLines.Add("")
}

$treeLines | Set-Content -LiteralPath $OutputFile -Encoding UTF8
Write-Host "[OK] Contexte exporte avec succes : $OutputFile ($($allFiles.Count) fichiers inclus)" -ForegroundColor Green
