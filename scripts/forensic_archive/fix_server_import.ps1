Set-Location "G:\AI\E-zzio"

$ServerPath = "interfaces/api/server.py"

if (!(Test-Path $ServerPath)) {
    Write-Host "[ERREUR] Fichier $ServerPath introuvable." -ForegroundColor Red
    exit 1
}

$Content = Get-Content $ServerPath -Raw

# 1. Corriger l'import erroné depuis routers.stats
$BadImport = "from routers.stats import router as stats_router, init_research_router"
$GoodImport = "from routers.stats import router as stats_router"

if ($Content -match [regex]::Escape($BadImport)) {
    $Content = $Content.Replace($BadImport, $GoodImport)
    Write-Host "[OK] Import 'init_research_router' retiré de routers.stats." -ForegroundColor Green
} else {
    Write-Host "[INFO] L'import erroné n'est pas présent." -ForegroundColor Yellow
}

# 2. Vérifier que routers.research est bien importé avec init_research_router
if ($Content -notmatch "from routers.research import.*init_research_router") {
    # On cherche une ligne existante qui importe research_router
    if ($Content -match "from routers.research import router as research_router") {
        $Content = $Content.Replace(
            "from routers.research import router as research_router",
            "from routers.research import router as research_router, init_research_router"
        )
        Write-Host "[OK] init_research_router ajouté à l'import routers.research." -ForegroundColor Green
    } else {
        Write-Host "[AVERTISSEMENT] Aucune ligne 'from routers.research import router as research_router' trouvée." -ForegroundColor Yellow
        Write-Host "              Vérifie manuellement les imports dans server.py." -ForegroundColor Yellow
    }
} else {
    Write-Host "[INFO] routers.research est déjà correctement importé." -ForegroundColor Yellow
}

# 3. Vérifier que stats_router est bien inclus dans app.include_router
if ($Content -notmatch "app.include_router\(stats_router\)") {
    # On l'ajoute après research_router
    if ($Content -match "app.include_router\(research_router\)") {
        $Content = $Content.Replace(
            "app.include_router(research_router)",
            "app.include_router(research_router)`r`napp.include_router(stats_router)"
        )
        Write-Host "[OK] stats_router ajouté aux routeurs de l'application." -ForegroundColor Green
    } else {
        Write-Host "[AVERTISSEMENT] Aucune ligne 'app.include_router(research_router)' trouvée." -ForegroundColor Yellow
        Write-Host "              Vérifie manuellement server.py." -ForegroundColor Yellow
    }
} else {
    Write-Host "[INFO] stats_router est déjà inclus dans l'application." -ForegroundColor Yellow
}

# 4. Sauvegarde
Set-Content -Path $ServerPath -Value $Content -Encoding UTF8

Write-Host "[OK] interfaces/api/server.py corrigé." -ForegroundColor Green
Write-Host "[*] Tu peux relancer l'API :" -ForegroundColor Cyan
Write-Host "     .\.venv\Scripts\python.exe -m uvicorn interfaces.api.server:app --host 127.0.0.1 --port 8001" -ForegroundColor Gray