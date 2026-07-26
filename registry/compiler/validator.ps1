param($Manifest, $RegistryDir)
Write-Host "🔍 [Validator] Vérification du schéma et des types de chemins..." -ForegroundColor Gray
$HasError = $false
$SeenPaths = @()

foreach ($mod in $Manifest.modules | Where-Object { $_.enabled -eq $true }) {
    if (-not $mod.path) {
        Write-Host "❌ Erreur : Chemin de module manquant." -ForegroundColor Red
        $HasError = $true
        continue
    }
    if ($SeenPaths -contains $mod.path) {
        Write-Host "❌ Erreur : Doublon de chemin -> $($mod.path)" -ForegroundColor Red
        $HasError = $true
    }
    $SeenPaths += $mod.path

    $FullPath = Join-Path $RegistryDir $mod.path
    if (-not (Test-Path $FullPath)) {
        if ($mod.required) {
            Write-Host "❌ Erreur critique : Module requis absent -> $($mod.path)" -ForegroundColor Red
            $HasError = $true
        } else {
            Write-Host "⚠ Optionnel absent -> $($mod.path)" -ForegroundColor Yellow
        }
    } else {
        $Item = Get-Item $FullPath -ErrorAction SilentlyContinue
        if ($Item -and $Item.PSIsContainer) {
            Write-Host "❌ Erreur : Le module pointe vers un dossier au lieu d'un fichier -> $($mod.path)" -ForegroundColor Red
            $HasError = $true
        }
    }
}
if ($HasError) { throw "Validation du registre échouée." }
Write-Host "✅ [Validator] Registre valide et sécurisé." -ForegroundColor Green