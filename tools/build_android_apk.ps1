# ==============================================================================
# E-ZZIO V9.1 — Canonical Android APK Build & Verification Script
# File: G:\AI\E-zzio\tools\build_android_apk.ps1
# Produit le package binaire compilé E-ZzIO-v9.0.1.apk (classes.dex, resources.arsc, APK v2 signature)
# ==============================================================================
param (
    [string]$OutputDir = "dist\android",
    [switch]$Release = $true,
    [switch]$Debug = $false
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir
$AndroidDir = Join-Path $RootDir "android"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   E-ZZIO ANDROID APK BUILD & PACKAGING PIPELINE (v9.0.1)" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# 1. Vérification de l'environnement SDK Android & JDK
if (-not $env:ANDROID_HOME) {
    if (Test-Path "G:\tools\android-sdk") {
        $env:ANDROID_HOME = "G:\tools\android-sdk"
    } elseif (Test-Path "$env:LOCALAPPDATA\Android\Sdk") {
        $env:ANDROID_HOME = "$env:LOCALAPPDATA\Android\Sdk"
    } else {
        Write-Error "[BUILD BLOCKED] ANDROID_HOME non défini et aucun SDK Android détecté."
        exit 1
    }
}

Write-Host "[ENV] ANDROID_HOME: $env:ANDROID_HOME" -ForegroundColor Gray

# 2. Vérification des sources Android
$ManifestPath = Join-Path $AndroidDir "app\src\main\AndroidManifest.xml"
$MainActivityPath = Join-Path $AndroidDir "app\src\main\java\ai\ezzio\office\MainActivity.java"

if (-not (Test-Path $ManifestPath) -or -not (Test-Path $MainActivityPath)) {
    Write-Error "[FATAL] Composants Android sources manquants dans $AndroidDir"
    exit 1
}

# 3. Audit de sécurité pré-build : Zéro secret en clair dans les sources Android
Write-Host "[SECURITY] Audit de sécurité pré-build (Recherche de clés API & secrets)..." -ForegroundColor Yellow
$ForbiddenPatterns = @("AIza[0-9A-Za-z-_]{35}", "gsk_[0-9A-Za-z]{40,}", "Bearer\s+[A-Za-z0-9\-\._~\+\/]+=*")
$SourceFiles = Get-ChildItem -Path $AndroidDir -Recurse -File | Where-Object { $_.FullName -notmatch "build[\\/]" -and $_.FullName -notmatch "\.gradle" }

foreach ($file in $SourceFiles) {
    $content = Get-Content $file.FullName -Raw
    foreach ($pattern in $ForbiddenPatterns) {
        if ($content -match $pattern) {
            Write-Error "[SECURITY VIOLATION] Secret détecté dans $($file.FullName) !"
            exit 1
        }
    }
}
Write-Host "[OK] Zéro secret détecté dans le code source Android." -ForegroundColor Green

# 4. Exécution du build natif Gradle
$BuildTask = if ($Debug) { "assembleDebug" } else { "assembleRelease" }
Write-Host "[BUILD] Compilation du binaire Android avec Gradle ($BuildTask)..." -ForegroundColor Cyan
Push-Location $AndroidDir
try {
    $gradlew = Join-Path $AndroidDir "gradlew.bat"
    if (-not (Test-Path $gradlew)) {
        Write-Error "[FATAL] Gradle wrapper manquant : $gradlew"
        exit 1
    }
    
    & $gradlew $BuildTask --no-daemon
    if ($LASTEXITCODE -ne 0) {
        Write-Error "[FATAL] Échec de la compilation Gradle $BuildTask (Exit Code: $LASTEXITCODE)"
        exit 1
    }
} finally {
    Pop-Location
}

# 5. Localisation de l'APK produit par Gradle
$GradleApk = if ($Debug) {
    Join-Path $AndroidDir "app\build\outputs\apk\debug\app-debug.apk"
} else {
    Join-Path $AndroidDir "app\build\outputs\apk\release\app-release.apk"
}
if (-not (Test-Path $GradleApk)) {
    Write-Error "[FATAL] L'APK compilé n'a pas été généré à l'emplacement attendu : $GradleApk"
    exit 1
}

# 6. Création du dossier de distribution et copie de l'APK certifié
$TargetDist = Join-Path $RootDir $OutputDir
if (-not (Test-Path $TargetDist)) {
    New-Item -ItemType Directory -Path $TargetDist -Force | Out-Null
}

$ApkDest = Join-Path $TargetDist "E-ZzIO-v9.0.1.apk"
$ZipDest = Join-Path $TargetDist "E-ZzIO-Android-Source-v9.0.1.zip"

Copy-Item $GradleApk -Destination $ApkDest -Force
if (-not $Debug) {
    $ReleaseApkDest = Join-Path $TargetDist "E-ZzIO-v9.1-release.apk"
    Copy-Item $GradleApk -Destination $ReleaseApkDest -Force
}

# Archivage des sources pour bundle source distinct (séparé du binaire APK)
Write-Host "[PACKAGE] Génération du bundle source d'accompagnement..." -ForegroundColor Cyan
Compress-Archive -Path "$AndroidDir\app", "$AndroidDir\build.gradle", "$AndroidDir\settings.gradle", "$AndroidDir\gradle.properties" -DestinationPath $ZipDest -Force

# 7. Contrôle forensique immédiat anti-faux-APK
Write-Host "[VERIFY] Contrôle de validité du binaire APK compilé..." -ForegroundColor Yellow
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [System.IO.Compression.ZipFile]::OpenRead($ApkDest)
$entries = $zip.Entries | ForEach-Object { $_.FullName }
$zip.Dispose()

$hasDex = $entries -contains "classes.dex"
$hasArsc = $entries -contains "resources.arsc"
$hasManifest = $entries -contains "AndroidManifest.xml"

if (-not $hasDex -or -not $hasArsc -or -not $hasManifest) {
    Remove-Item $ApkDest -Force -ErrorAction SilentlyContinue
    Write-Error "[ANTI-FAUX-APK] Le fichier produit ne contient pas classes.dex ou resources.arsc ! Build rejeté."
    exit 1
}

$apkItem = Get-Item $ApkDest
$apkHash = (Get-FileHash -Path $ApkDest -Algorithm SHA256).Hash

Write-Host "============================================================" -ForegroundColor Green
Write-Host "   BUILD SUCCÈS : VRAI APK ANDROID COMPILLÉ & CERTIFIÉ" -ForegroundColor Green
Write-Host "   Fichier : $ApkDest" -ForegroundColor White
Write-Host "   Taille  : $([math]::Round($apkItem.Length / 1MB, 2)) MB ($($apkItem.Length) octets)" -ForegroundColor White
Write-Host "   SHA-256 : $apkHash" -ForegroundColor White
Write-Host "   Bytecode: classes.dex PRÉSENT" -ForegroundColor Green
Write-Host "   Res     : resources.arsc PRÉSENT" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
