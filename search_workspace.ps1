param (
    [string]$RootPath = "G:\",
    [string]$Keyword = "",
    [string[]]$Extensions = @("*.py", "*.ps1", "*.gd", "*.md", "*.txt", "*.json", "*.env", "*.cfg")
)

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "🔍 EXPLORATEUR ET INDEXEUR DU DISQUE G:\ POUR E-ZZIO" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

if (-not (Test-Path $RootPath)) {
    Write-Host "❌ Erreur : Le répertoire '$RootPath' n'existe pas." -ForegroundColor Red
    exit
}

if ($Keyword) {
    Write-Host "[*] Recherche du texte/code : '$Keyword' dans $RootPath..." -ForegroundColor Yellow
    Write-Host "[*] Extensions ciblées : $($Extensions -join ', ')" -ForegroundColor DarkGray
    Write-Host "------------------------------------------------------------"

    $results = Get-ChildItem -Path $RootPath -Recurse -Include $Extensions -ErrorAction SilentlyContinue |
        Select-String -Pattern $Keyword -SimpleMatch

    if ($results) {
        Write-Host "`n✅ $($results.Count) occurrence(s) trouvée(s) :`n" -ForegroundColor Green
        foreach ($res in $results) {
            $relativePath = $res.Path.Replace($RootPath, "")
            Write-Host "📄 $relativePath (Ligne $($res.LineNumber))" -ForegroundColor Yellow
            Write-Host "   └─> $($res.Line.Trim())" -ForegroundColor White
        }
    } else {
        Write-Host "❌ Aucune occurrence trouvée pour '$Keyword'." -ForegroundColor Red
    }
} else {
    Write-Host "[*] Numérisation globale et création de l'index pour E-ZZIO..." -ForegroundColor Yellow
    
    $files = Get-ChildItem -Path $RootPath -Recurse -Include $Extensions -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -notmatch '\\(\.git|venv|__pycache__|\.godot)\\' }

    Write-Host "`n✅ Fichiers détectés : $($files.Count)" -ForegroundColor Green

    # Affichage de la répartition par type
    $grouped = $files | Group-Object Extension
    foreach ($group in $grouped) {
        Write-Host "  • Type $($group.Name) : $($group.Count) fichier(s)" -ForegroundColor Gray
    }

    # Export pour la mémoire locale d'E-ZZIO
    $dataFolder = "G:\AI\E-zzio\data"
    if (-not (Test-Path $dataFolder)) {
        New-Item -ItemType Directory -Force -Path $dataFolder | Out-Null
    }

    $indexPath = "$dataFolder\workspace_index.json"
    
    $exportList = $files | Select-Object @{Name="Path"; Expression={$_.FullName}},
                                         @{Name="Extension"; Expression={$_.Extension}},
                                         @{Name="SizeKB"; Expression={[math]::Round($_.Length / 1KB, 2)}},
                                         LastWriteTime

    $exportList | ConvertTo-Json -Depth 3 | Set-Content -Path $indexPath -Encoding UTF8
    Write-Host "`n💾 Index sauvegardé avec succès dans :" -ForegroundColor Green
    Write-Host "   👉 $indexPath" -ForegroundColor Yellow
    Write-Host "   (E-ZZIO peut maintenant lire cet index pour connaître tous tes projets !)" -ForegroundColor Cyan
}
