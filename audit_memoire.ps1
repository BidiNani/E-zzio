Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ProjectPath = "G:\AI\E-zzio"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " AUDIT ET DÉCOUVERTE DE LA MÉMOIRE EXISTANTE D'E-ZZIO (CORRIGÉ)" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

if (-not (Test-Path $ProjectPath)) {
    Write-Host "[!] Le chemin du projet $ProjectPath est introuvable." -ForegroundColor Red
    exit
}

Write-Host "[*] Recherche des fichiers de mémoire, bases de données et stores..." -ForegroundColor Yellow

$MemoryPatterns = @("*memory*", "*.db", "*store*", "*index*")
# Ajout strict du switch -File pour ignorer les répertoires et cibler la propriété Length
$FoundFiles = Get-ChildItem -Path $ProjectPath -Recurse -File -Include $MemoryPatterns -ErrorAction SilentlyContinue

if ($FoundFiles) {
    Write-Host "[OK] Fichiers de mémoire et index détectés :" -ForegroundColor Green
    foreach ($file in $FoundFiles) {
        $relative = $file.FullName.Substring($ProjectPath.Length)
        Write-Host "  -> $relative ($([Math]::Round($file.Length / 1KB, 2)) KB)" -ForegroundColor Cyan
    }
} else {
    Write-Host "[!] Aucun fichier de mémoire spécifique trouvé." -ForegroundColor Yellow
}

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " AUDIT TERMINÉ." -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
