# ==============================================================================
# E-ZZIO TOOLS HARDENING FIX (.PS1)
# 1) Sort inject_godot_core.ps1 de tools/ (script auto-modifiant)
# 2) Deploie guard.py / patch_pipeline.py / exec_tools.py durcis
# 3) Redemarre les services
# ==============================================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ProjectPath = "G:\AI\E-zzio"
$ToolsPath = Join-Path $ProjectPath "tools"
$DeployScriptsPath = Join-Path $ProjectPath "deploy_scripts"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " DURCISSEMENT DU DOSSIER tools/" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# 1. Arret des process en cours
Write-Host "[..] Arret des services en cours..." -ForegroundColor Yellow
Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" | Where-Object {
    $_.CommandLine -like "*web_server.py*" -or $_.CommandLine -like "*discord_agent_v2.py*"
} | ForEach-Object {
    Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
}
try {
    $conn = Get-NetTCPConnection -LocalPort 8001 -ErrorAction SilentlyContinue
    if ($conn) { Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue }
} catch {}

# 2. Deplacement du script auto-modifiant HORS de tools/
if (-not (Test-Path $DeployScriptsPath)) {
    New-Item -ItemType Directory -Path $DeployScriptsPath -Force | Out-Null
}
$InjectGodot = Join-Path $ToolsPath "inject_godot_core.ps1"
if (Test-Path $InjectGodot) {
    Write-Host "[..] Deplacement de inject_godot_core.ps1 vers deploy_scripts/ (hors du perimetre executable par le LLM)..." -ForegroundColor Yellow
    Move-Item -LiteralPath $InjectGodot -Destination (Join-Path $DeployScriptsPath "inject_godot_core.ps1") -Force
    Write-Host "[OK] Deplace. Ce script ne sera plus jamais indexe/executable via executer_outil_g_drive." -ForegroundColor Green
} else {
    Write-Host "[OK] inject_godot_core.ps1 deja absent de tools/." -ForegroundColor Green
}

# 3. Sauvegarde des anciens fichiers avant ecrasement
Write-Host "[..] Sauvegarde des anciens fichiers (.bak)..." -ForegroundColor Yellow
foreach ($f in @("guard.py", "patch_pipeline.py", "exec_tools.py")) {
    $src = Join-Path $ToolsPath $f
    if (Test-Path $src) {
        Copy-Item -LiteralPath $src -Destination "$src.bak" -Force
    }
}

# 4. Deploiement de guard.py (source unique de verite pour les listes protegees)
Write-Host "[..] Deploiement de guard.py..." -ForegroundColor Yellow
$GuardCode = @'
import os
import hashlib
import pathlib

# --- Racine du projet (confinement) --------------------------------------
PROJECT_ROOT = pathlib.Path(r"G:\AI\E-zzio").resolve()

# Répertoires strictement interdits à la modification / lecture par le LLM
FORBIDDEN_DIRS = [
    r"G:\AI\E-zzio\secrets",
    r"G:\AI\E-zzio\.git",
    r"G:\AI\E-zzio\venv",
    r"G:\AI\E-zzio__pycache__",
    r"G:\AI\E-zzio\deploy_scripts",  # scripts d'auto-modification : jamais exécutables par le LLM
]

# SOURCE UNIQUE DE VÉRITÉ pour les fichiers protégés.
# guard.py, patch_pipeline.py et exec_tools.py importent tous cette même
# liste — plus de divergence entre modules.
FORBIDDEN_FILES = {
    ".env",
    "id_rsa",
    "secrets.json",
    "working_memory.json",
    "memory.sqlite3",
    "indexer_config.json",
}

# Historique des hashs pour détecter les boucles infinies (A -> B -> A)
SEEN_HASHES = set()


def is_path_allowed(file_path: str) -> tuple[bool, str]:
    """Vérifie si le fichier peut être lu ou modifié selon la politique ACL.
    Combine : (1) confinement au projet, (2) liste noire de fichiers/dossiers."""
    abs_path = os.path.abspath(file_path)

    # 1. Confinement : le chemin doit rester sous PROJECT_ROOT
    try:
        pathlib.Path(abs_path).resolve().relative_to(PROJECT_ROOT)
    except ValueError:
        return False, f"⛔ ACCÈS REFUSÉ : chemin hors du projet ({PROJECT_ROOT}) : {file_path}"

    # 2. Fichiers interdits
    base_name = os.path.basename(abs_path)
    if base_name in FORBIDDEN_FILES:
        return False, f"⛔ ACCÈS REFUSÉ : Le fichier '{base_name}' est protégé par la politique de sécurité."

    # 3. Répertoires interdits
    for forbidden in FORBIDDEN_DIRS:
        if abs_path.startswith(os.path.abspath(forbidden)):
            return False, f"⛔ ACCÈS REFUSÉ : Le répertoire '{forbidden}' est strictement interdit au LLM."

    return True, "Autorisé"


def compute_sha256(content: str) -> str:
    """Calcule l'empreinte SHA256 d'un contenu texte."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def check_for_infinite_loop(content: str) -> tuple[bool, str]:
    """Détecte si la version générée a déjà été testée précédemment."""
    content_hash = compute_sha256(content)
    if content_hash in SEEN_HASHES:
        return True, f"⚠️ BOUCLE INFINIE DÉTECTÉE ! Le code généré a un Hash déjà vu ({content_hash[:8]}). Interruption."

    SEEN_HASHES.add(content_hash)
    return False, content_hash

'@
Set-Content -LiteralPath (Join-Path $ToolsPath "guard.py") -Value $GuardCode -Encoding UTF8

# 5. Deploiement de patch_pipeline.py (utilise desormais guard.FORBIDDEN_FILES)
Write-Host "[..] Deploiement de patch_pipeline.py..." -ForegroundColor Yellow
$PatchPipelineCode = @'
import os
import shutil
import py_compile
import traceback
from typing import Dict, Any
from tools.guard import is_path_allowed

class PatchPipeline:
    """Pipeline industriel pour modifier des fichiers avec validation syntaxique et rollback."""

    @classmethod
    def apply_patch(cls, file_path: str, new_content: str) -> Dict[str, Any]:
        """Remplace atomiquement le contenu d'un fichier avec validation et auto-rollback."""
        target_path = os.path.abspath(file_path)
        filename = os.path.basename(target_path)

        # Guard : confinement au projet + liste noire unifiée (voir guard.py)
        allowed, msg = is_path_allowed(target_path)
        if not allowed:
            return {"success": False, "error": f"SÉCURITÉ: {msg}"}

        if target_path.endswith('.sqlite3'):
            return {"success": False, "error": f"SÉCURITÉ: Modification de '{filename}' strictement interdite."}

        backup_path = target_path + ".bak"
        tmp_path = target_path + ".tmp"
        file_exists = os.path.exists(target_path)

        try:
            if file_exists:
                shutil.copy2(target_path, backup_path)

            with open(tmp_path, 'w', encoding='utf-8') as f:
                f.write(new_content)

            # Auto-Check Syntaxique (Règle 9 : Détection/Correction)
            if target_path.endswith('.py'):
                try:
                    py_compile.compile(tmp_path, doraise=True)
                except py_compile.PyCompileError as e:
                    os.remove(tmp_path)
                    return {"success": False, "error": f"Erreur de syntaxe interceptée (Rollback effectué) :\n{str(e)}"}

            os.replace(tmp_path, target_path)
            return {"success": True, "message": f"Fichier {file_path} patché avec succès."}

        except Exception:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            if file_exists and os.path.exists(backup_path):
                shutil.copy2(backup_path, target_path)
            return {"success": False, "error": f"Erreur critique I/O : {traceback.format_exc()}"}

patch_pipeline = PatchPipeline()

'@
Set-Content -LiteralPath (Join-Path $ToolsPath "patch_pipeline.py") -Value $PatchPipelineCode -Encoding UTF8

# 6. Deploiement de exec_tools.py (execution restreinte au projet, plus de commande arbitraire)
Write-Host "[..] Deploiement de exec_tools.py..." -ForegroundColor Yellow
$ExecToolsCode = @'
import subprocess
import sys
import os
from tools.guard import is_path_allowed

def test_python_syntax(file_path: str) -> str:
    """Vérifie la compilation d'un fichier Python sans l'exécuter."""
    allowed, msg = is_path_allowed(file_path)
    if not allowed:
        return f"⛔ {msg}"
    if not os.path.exists(file_path):
        return f"❌ Fichier introuvable : {file_path}"
    try:
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", file_path],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return "✅ Compilation Python réussie (Aucune erreur de syntaxe)."
        else:
            return f"❌ Erreur de compilation :\n{result.stderr}"
    except Exception as e:
        return f"❌ Erreur lors du test de compilation : {e}"

def run_python_script(file_path: str, timeout_sec: int = 15) -> str:
    """Exécute un script Python localement et renvoie stdout / stderr.
    Restreint aux fichiers du projet (voir guard.is_path_allowed) — ne peut
    plus exécuter un chemin arbitraire ailleurs sur le disque."""
    allowed, msg = is_path_allowed(file_path)
    if not allowed:
        return f"⛔ {msg}"
    if not os.path.exists(file_path):
        return f"❌ Fichier introuvable : {file_path}"
    try:
        result = subprocess.run(
            [sys.executable, file_path],
            capture_output=True, text=True, timeout=timeout_sec
        )
        output = []
        if result.stdout:
            output.append(f"--- STDOUT ---\n{result.stdout.strip()}")
        if result.stderr:
            output.append(f"--- STDERR (Erreur) ---\n{result.stderr.strip()}")

        status = "✅ EXÉCUTION RÉUSSIE (Exit code 0)" if result.returncode == 0 else f"❌ ÉCHEC D'EXÉCUTION (Exit code {result.returncode})"
        return f"{status}\n" + "\n".join(output)
    except subprocess.TimeoutExpired:
        return f"⚠️ Exécution interrompue : Timeout dépassé ({timeout_sec}s)."
    except Exception as e:
        return f"❌ Erreur d'exécution : {e}"

def run_powershell_script(file_path: str, timeout_sec: int = 15) -> str:
    """Exécute un script .ps1 du projet, confiné par guard.is_path_allowed.

    REMPLACE l'ancienne run_powershell_command(command: str), qui exécutait
    une commande PowerShell arbitraire fournie en texte libre — c'était une
    exécution de code non restreinte, équivalente à un accès shell complet
    pour quiconque peut faire appeler cette fonction (y compris le LLM via
    function calling). Ici on n'exécute plus qu'un FICHIER .ps1 déjà présent
    et confiné au projet, jamais une chaîne de commande arbitraire.
    """
    allowed, msg = is_path_allowed(file_path)
    if not allowed:
        return f"⛔ {msg}"
    if not os.path.exists(file_path) or not file_path.lower().endswith(".ps1"):
        return f"❌ Script .ps1 introuvable ou invalide : {file_path}"
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", file_path],
            capture_output=True, text=True, timeout=timeout_sec
        )
        out = result.stdout.strip() if result.stdout else ""
        err = result.stderr.strip() if result.stderr else ""

        if result.returncode == 0:
            return f"✅ Script exécuté avec succès :\n{out}"
        else:
            return f"❌ Erreur PowerShell (Code {result.returncode}) :\n{err}\n{out}"
    except Exception as e:
        return f"❌ Erreur d'exécution PowerShell : {e}"

'@
Set-Content -LiteralPath (Join-Path $ToolsPath "exec_tools.py") -Value $ExecToolsCode -Encoding UTF8

Write-Host "[OK] Fichiers durcis deployes avec succes." -ForegroundColor Green

# 7. Redemarrage des services
Write-Host "[..] Redemarrage des services E-zzio..." -ForegroundColor Yellow
& (Join-Path $ProjectPath "Start-EzzioBackground.ps1")

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " DURCISSEMENT TERMINE" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Rappel : run_powershell_command a ete remplace par run_powershell_script" -ForegroundColor Yellow
Write-Host "(execution d'un fichier .ps1 confine au projet, plus de commande texte libre)." -ForegroundColor Yellow
Write-Host "Si du code appelle encore l'ancienne fonction par son nom, il faudra le mettre a jour." -ForegroundColor Yellow
