# ==============================================================================
# E-ZZIO — Script de Certification Intégrale 100%
# File: G:\AI\E-zzio\ezzio_certify_100.ps1
# ==============================================================================

$ErrorActionPreference = "Stop"
$Root = "G:\AI\E-zzio"
Set-Location $Root
$PythonExe = "$Root\.venv\Scripts\python.exe"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "       E-ZZIO SOVEREIGN SYSTEM — CERTIFICATION 100%        " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$score = 0
$total_checks = 5

# --- CHECK 1 : Environnement Virtuel & Interpréteur Python ---
Write-Host "`n[1/5] Vérification de l'environnement Python..." -NoNewline
if (Test-Path $PythonExe) {
    $py_version = & $PythonExe --version 2>&1
    Write-Host " [OK] ($py_version)" -ForegroundColor Green
    $score++
} else {
    Write-Host " [ERREUR] Interpréteur introuvable dans .venv." -ForegroundColor Red
}

# --- CHECK 2 : Intégrité Syntaxique & Compilation AST ---
Write-Host "[2/5] Vérification de l'intégrité AST des modules Core..." -NoNewline
$ast_script = @'
import ast
import sys
from pathlib import Path

root = Path(r"G:\AI\E-zzio")
modules = ["core/llm_engine.py", "core/dispatcher.py", "core/ezzio_master.py", "core/memory_vault.py", "core/tasks/manager.py", "web_server.py"]
failed = False

for mod in modules:
    p = root / mod
    if not p.exists():
        print(f"\n[!] Manquant : {mod}")
        sys.exit(1)
    try:
        ast.parse(p.read_text(encoding="utf-8"))
    except SyntaxError as e:
        print(f"\n[!] Erreur syntaxe dans {mod} (Ligne {e.lineno}): {e.msg}")
        sys.exit(2)

print(" [OK] Tous les modules sont conformes.")
sys.exit(0)
'@

& $PythonExe -c $ast_script
if ($LASTEXITCODE -eq 0) {
    Write-Host " [OK]" -ForegroundColor Green
    $score++
} else {
    Write-Host " [ERREUR] Échec de la compilation AST." -ForegroundColor Red
}

# --- CHECK 3 : Connectivité et Modèle Ollama (Port 11434) ---
Write-Host "[3/5] Vérification du moteur Ollama et du modèle qwen2.5:7b..." -NoNewline
try {
    $ollama_resp = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -Method Get -TimeoutSec 3 -ErrorAction Stop
    $models = $ollama_resp.models.name
    if ($models -contains "qwen2.5:7b") {
        Write-Host " [OK] (Modèle qwen2.5:7b actif)" -ForegroundColor Green
        $score++
    } else {
        Write-Host " [AVERTISSEMENT] Ollama répond mais qwen2.5:7b est absent." -ForegroundColor Yellow
    }
} catch {
    Write-Host " [ERREUR] Ollama injoignable sur le port 11434." -ForegroundColor Red
}

# --- CHECK 4 : Intégrité des Bases de Données SQLite (Mémoire & Tâches) ---
Write-Host "[4/5] Vérification des coffres SQLite (deterministic_memory.db & tasks.db)..." -NoNewline
$db_script = @'
import sqlite3
import sys
from pathlib import Path

root = Path(r"G:\AI\E-zzio")
mem_db = root / "runtime" / "state" / "deterministic_memory.db"
tasks_db = root / "runtime" / "state" / "tasks.db"

try:
    with sqlite3.connect(mem_db) as conn:
        conn.execute("SELECT count(*) FROM session_kv")
    with sqlite3.connect(tasks_db) as conn:
        conn.execute("SELECT count(*) FROM governed_tasks")
    print(" [OK] Bases SQLite opérationnelles.")
    sys.exit(0)
except Exception as e:
    print(f"\n[!] Erreur SQLite : {e}")
    sys.exit(1)
'@

& $PythonExe -c $db_script
if ($LASTEXITCODE -eq 0) {
    Write-Host " [OK]" -ForegroundColor Green
    $score++
} else {
    Write-Host " [ERREUR] Problème d'accès aux bases de données." -ForegroundColor Red
}

# --- CHECK 5 : Santé de l'API Sovereign (Port 8001) ---
Write-Host "[5/5] Vérification de l'API Backend (/health sur le port 8001)..." -NoNewline
try {
    $api_resp = Invoke-RestMethod -Uri "http://127.0.0.1:8001/health" -Method Get -TimeoutSec 3 -ErrorAction Stop
    if ($api_resp.service -eq "E-ZZIO" -and $api_resp.status -eq "ONLINE") {
        Write-Host " [OK] (API en ligne, PID: $($api_resp.pid))" -ForegroundColor Green
        $score++
    } else {
        Write-Host " [ERREUR] Réponse inattendue de l'API." -ForegroundColor Red
    }
} catch {
    Write-Host " [ERREUR] API injoignable (Le backend Uvicorn est-il démarré ?)." -ForegroundColor Red
}

# --- RAPPORT FINAL ---
Write-Host "`n============================================================" -ForegroundColor Cyan
$percentage = ($score / $total_checks) * 100
if ($percentage -eq 100) {
    Write-Host "         CERTIFICATION E-ZZIO : 100% OPÉRATIONNEL        " -ForegroundColor Black -BackgroundColor Green
} else {
    Write-Host "         CERTIFICATION PARTIELLE : $percentage% ($score/$total_checks)     " -ForegroundColor Black -BackgroundColor Yellow
}
Write-Host "============================================================" -ForegroundColor Cyan