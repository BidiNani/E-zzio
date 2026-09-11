param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("build", "clean", "audit", "diff")]
    [string]$Action = "build",

    [Parameter(Mandatory=$false)]
    [string]$Profile = "all"
)

$ErrorActionPreference = "Stop"
# Utilisation de Split-Path -Parent au lieu du -replace fragile
$RegistryDir = Split-Path $PSScriptRoot -Parent
$ManifestPath = Join-Path $PSScriptRoot "manifest.json"
$BuildDir = Join-Path $RegistryDir "build"
$AuditDir = Join-Path $RegistryDir "audit"
$CachePath = Join-Path $PSScriptRoot "cache.json"

foreach ($dir in @($BuildDir, $AuditDir)) {
    if (!(Test-Path $dir)) { New-Item $dir -ItemType Directory | Out-Null }
}

$Manifest = Get-Content -Path $ManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
$CompilerVersion = $Manifest.version

if ($Action -eq "clean") {
    Write-Host "🧹 Nettoyage complet..." -ForegroundColor Yellow
    if (Test-Path $BuildDir) { Remove-Item "$BuildDir\*" -Recurse -Force }
    if (Test-Path $AuditDir) { Remove-Item "$AuditDir\*" -Recurse -Force }
    if (Test-Path $CachePath) { Remove-Item $CachePath -Force }
    Write-Host "✅ Nettoyage terminé." -ForegroundColor Green
    exit
}

& (Join-Path $PSScriptRoot "validator.ps1") -Manifest $Manifest -RegistryDir $RegistryDir
if ($Action -eq "audit") { exit }

$RegistryIndex = @{}

foreach ($mod in $Manifest.modules | Where-Object { $_.enabled -eq $true }) {
    if ([string]::IsNullOrWhiteSpace($mod.path)) { continue }
    
    $FullPath = Join-Path $RegistryDir $mod.path
    $Item = Get-Item $FullPath -ErrorAction SilentlyContinue
    if ($Item -and $Item.FullName -eq (Get-Item $RegistryDir).FullName) {
        throw "❌ Module invalide détecté (pointe vers la racine) : $($mod.path)"
    }

    if ($Item -and (-not $Item.PSIsContainer)) {
        $hash = (Get-FileHash -Path $FullPath -Algorithm SHA256).Hash
        $RegistryIndex[$mod.path] = @{
            path     = $mod.path
            priority = $mod.priority
            sha256   = $hash
            size     = $Item.Length
        }
    }
}

foreach ($pName in $Manifest.profiles.psobject.properties.name) {
    $pData = $Manifest.profiles.$pName
    foreach ($extraObj in @($pData.extra)) {
        if (-not $extraObj) { continue }
        $extraPath = if ($extraObj -is [string]) { $extraObj } else { $extraObj.path }
        if ([string]::IsNullOrWhiteSpace($extraPath)) { continue }

        if (-not $RegistryIndex.ContainsKey($extraPath)) {
            $FullPath = Join-Path $RegistryDir $extraPath
            $Item = Get-Item $FullPath -ErrorAction SilentlyContinue
            if ($Item -and (-not $Item.PSIsContainer)) {
                $hash = (Get-FileHash -Path $FullPath -Algorithm SHA256).Hash
                $RegistryIndex[$extraPath] = @{
                    path     = $extraPath
                    priority = 999
                    sha256   = $hash
                    size     = $Item.Length
                }
            }
        }
    }
}

$cacheResult = & (Join-Path $PSScriptRoot "cache.ps1") -ManifestPath $ManifestPath -RegistryIndex $RegistryIndex -CachePath $CachePath -CompilerVersion $CompilerVersion -BuildProfile $Profile
if ($Action -eq "diff") {
    if ($cacheResult.Changed) { Write-Host "🔄 Modifications détectées pour le profil '$Profile'." -ForegroundColor Yellow }
    else { Write-Host "✔ Registre stable pour le profil '$Profile'." -ForegroundColor Green }
    exit
}

if (-not $cacheResult.Changed) {
    Write-Host "✔ Cache à jour (Hash global inchangé pour le profil '$Profile'). Build ignoré." -ForegroundColor Green
    exit
}

$SortedModules = $null
try {
    $SortedModules = @(
        & (Join-Path $PSScriptRoot "resolver.ps1") -Manifest $Manifest -RegistryDir $RegistryDir
    )
} catch {
    throw
}

Write-Host "`n=== 🏗️ BUILD V10.3 (Profils: $Profile) ===" -ForegroundColor Cyan
$profilesToBuild = if ($Profile -eq "all") { $Manifest.profiles.psobject.properties.name } else { @($Profile) }

$ProfileStats = @{}
$OutputsMeta = @{}

foreach ($profileName in $profilesToBuild) {
    if (-not $Manifest.profiles.$profileName) {
        Write-Host "❌ Profil inconnu : $profileName" -ForegroundColor Red
        continue
    }

    $profileData = $Manifest.profiles.$profileName
    $extraModules = @($profileData.extra)
    $ContentParts = @()
    $InjectedPaths = @()

    $activeList = if ($profileName -eq "production") {
        $SortedModules | Where-Object { $_.path -ne "personality/lore.md" }
    } else {
        $SortedModules
    }

    foreach ($mod in $activeList) {
        if ([string]::IsNullOrWhiteSpace($mod.path)) { continue }
        if (-not $InjectedPaths.Contains($mod.path)) {
            $FullPath = Join-Path $RegistryDir $mod.path
            $Item = Get-Item $FullPath -ErrorAction SilentlyContinue
            if ($Item -and (-not $Item.PSIsContainer)) {
                $ModName = [System.IO.Path]::GetFileNameWithoutExtension($mod.path).ToUpper()
                $Body = Get-Content -Path $FullPath -Raw -Encoding UTF8
                $meta = $RegistryIndex[$mod.path]

                $Frontmatter = "---`r`nmodule: $($mod.path)`r`npriority: $($mod.priority)`r`nsha256: $($meta.sha256)`r`n---"
                $Header = "==================================`r`nMODULE: $ModName`r`n=================================="
                $ContentParts += "$Frontmatter`r`n`r`n$Header`r`n`r`n$Body"
                $InjectedPaths += $mod.path
            }
        }
    }

    foreach ($extraObj in $extraModules) {
        if (-not $extraObj) { continue }
        $extraPath = if ($extraObj -is [string]) { $extraObj } else { $extraObj.path }
        $isReq = if ($extraObj -is [string]) { $false } else { $extraObj.required }

        if ([string]::IsNullOrWhiteSpace($extraPath)) { continue }

        if (-not $InjectedPaths.Contains($extraPath)) {
            $FullPath = Join-Path $RegistryDir $extraPath
            $Item = Get-Item $FullPath -ErrorAction SilentlyContinue
            if ($Item -and (-not $Item.PSIsContainer)) {
                $ModName = [System.IO.Path]::GetFileNameWithoutExtension($extraPath).ToUpper()
                $Body = Get-Content -Path $FullPath -Raw -Encoding UTF8
                $hash = (Get-FileHash -Path $FullPath -Algorithm SHA256).Hash

                $Frontmatter = "---`r`nmodule: $extraPath`r`npriority: 999`r`nsha256: $hash`r`n---"
                $Header = "==================================`r`nMODULE: $ModName`r`n=================================="
                $ContentParts += "$Frontmatter`r`n`r`n$Header`r`n`r`n$Body"
                $InjectedPaths += $extraPath
            } else {
                if ($isReq) {
                    throw "❌ Erreur critique : Module extra requis introuvable -> $extraPath"
                } else {
                    Write-Host "⚠ Extra optionnel absent -> $extraPath" -ForegroundColor Yellow
                }
            }
        }
    }

    $CompiledText = $ContentParts -join "`r`n`r`n`r`n"
    $estTokens = [Math]::Round($CompiledText.Length / 3.3)

    $ProfileStats[$profileName] = @{
        tokens = $estTokens
        size   = $CompiledText.Length
    }

    $OutputPath = Join-Path $BuildDir "persona.$profileName.md"
    [System.IO.File]::WriteAllText($OutputPath, $CompiledText, [System.Text.UTF8Encoding]::new($false))
    
    $outHash = (Get-FileHash -Path $OutputPath -Algorithm SHA256).Hash
    $OutputsMeta["persona.$profileName.md"] = @{
        file   = "persona.$profileName.md"
        sha256 = $outHash
        tokens = $estTokens
        size   = (Get-Item $OutputPath).Length
    }

    Write-Host "✅ Compilé : persona.$profileName.md (~$estTokens tokens)" -ForegroundColor Green
}

# Synchro Master alias
$MasterAlias = Join-Path $RegistryDir "persona.txt"
$FullBuild = Join-Path $BuildDir "persona.full.md"
$ProdBuild = Join-Path $BuildDir "persona.production.md"

if (Test-Path $FullBuild) {
    Copy-Item -Path $FullBuild -Destination $MasterAlias -Force
    Write-Host "✅ Alias principal synchronisé depuis persona.full.md : registry/persona.txt" -ForegroundColor Cyan
} elseif (Test-Path $ProdBuild) {
    Copy-Item -Path $ProdBuild -Destination $MasterAlias -Force
    Write-Host "✅ Alias principal synchronisé depuis persona.production.md : registry/persona.txt" -ForegroundColor Cyan
}

# Génération du manifest d'artefacts (build_manifest.json) dans le dossier build
$BuildManifest = @{
    version   = $CompilerVersion
    generated = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    profiles  = $OutputsMeta
}
$BuildManifest | ConvertTo-Json -Depth 10 | Set-Content -Path (Join-Path $BuildDir "build_manifest.json") -Encoding utf8
Write-Host "✅ Manifest d'artefacts généré : registry/build/build_manifest.json" -ForegroundColor Cyan

# Sauvegarde d'un cache enrichi
@{
    compiler      = $CompilerVersion
    profile       = $Profile
    manifest_hash = $cacheResult.ManifestHash
    registry_hash = $cacheResult.GlobalHash
    timestamp     = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
} | ConvertTo-Json | Set-Content -Path $CachePath -Encoding utf8

# Rapport d'audit global
$ReportData = @{
    compiler = @{
        version = $CompilerVersion
    }
    registry = @{
        modules  = $RegistryIndex.Count
        resolved = $SortedModules.Count
        hash     = $cacheResult.GlobalHash
    }
    profiles = $ProfileStats
    outputs  = $OutputsMeta
    timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
}
$ReportData | ConvertTo-Json -Depth 10 | Set-Content -Path (Join-Path $AuditDir "report.json") -Encoding utf8
Write-Host "✅ Rapport d'audit complet généré : registry/audit/report.json" -ForegroundColor Cyan

Write-Host "`n🎉 Pipeline V10.3 exécuté avec succès !" -ForegroundColor Green