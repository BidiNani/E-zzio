# ==============================================================================
# E-ZZIO QUARANTINE & CLEANUP SCRIPT (.PS1)
# ==============================================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Continue' # Permet de continuer si un fichier est verrouillé par un processus

$ProjectPath = "G:\AI\E-zzio"
$QuarantinePath = Join-Path $ProjectPath "_a_verifier"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " TRI ET MISE EN QUARANTAINE DES FICHIERS REDONDANTS" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

if (-not (Test-Path $QuarantinePath)) {
    New-Item -ItemType Directory -Path $QuarantinePath | Out-Null
    Write-Host "[*] Dossier de quarantaine créé : _a_verifier" -ForegroundColor Yellow
}

# Liste structurée des fichiers et motifs à isoler
$FilesToMove = @(
    # 1. Scripts de démarrage redondants
    "start.ps1", "start_ezzio.ps1", "Start-Ezzio.ps1", "start_ezzio_daemon.ps1", "run_ezzio.ps1", "Lancer_Ezzio.ps1",
    
    # 2. Anciens agents et lanceurs
    "discord_agent.py", "Sentinelle_Discord.bat", "Sentinelle_Discord.ps1", "Sentinelle_Invisible.vbs",
    
    # 3. Scripts de nettoyage et d'audit obsolètes
    "EZZIO_Audit_*.ps1", "EZZIO_Guardian_*.ps1", "EZZIO_Assainissement*.ps1", "EZZIO_Clean_*.ps1", "EZZIO_Menage_*.ps1", "EZZIO_Allègement_*.ps1", "EZZIO_Inventaire_*.ps1", "EZZIO_Supprimer_*.ps1", "EZZIO_PHASE_*.ps1",
    
    # 4. Bases de données suspectes/doublons
    "memoire_ezzio.db", "memory_expiry.db", "test_memory_expiry.db", "actions.db",
    
    # 5. Fichiers hors-sujet (WoW)
    "guide_conquest_of_azeroth.md", "research_addons.md", "research_classes.md", "research_reaper_macros.md",
    
    # 6. Scripts jetables et fichiers risqués (dont le vieux script d'injection non sécurisé)
    "capture_temp.png", "update_latency_temp.py", "test_gemini_15.py", "ultimate_polish.py", "write_clean.py", "final_strike.py", "inject_advanced_skills.ps1"
)

$MovedCount = 0

foreach ($Pattern in $FilesToMove) {
    # On force la recherche uniquement à la racine du projet pour ne pas casser l'intérieur des sous-dossiers sains
    $FoundFiles = Get-ChildItem -Path $ProjectPath -Filter $Pattern -File -ErrorAction SilentlyContinue
    
    foreach ($File in $FoundFiles) {
        $Destination = Join-Path $QuarantinePath $File.Name
        
        # Gestion des collisions : renomme si un fichier du même nom existe déjà dans _a_verifier
        if (Test-Path $Destination) {
            $NewName = "$($File.BaseName)_$(Get-Date -Format 'yyyyMMdd_HHmmss')$($File.Extension)"
            $Destination = Join-Path $QuarantinePath $NewName
        }
        
        try {
            Move-Item -Path $File.FullName -Destination $Destination -Force -ErrorAction Stop
            Write-Host "  -> Déplacé : $($File.Name)" -ForegroundColor Green
            $MovedCount++
        } catch {
            Write-Host "  [!] Impossible de déplacer $($File.Name) (probablement en cours d'utilisation)." -ForegroundColor Red
        }
    }
}

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " OPÉRATION TERMINÉE : $MovedCount fichier(s) mis en quarantaine." -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
