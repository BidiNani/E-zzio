#requires -Version 7.4
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$projectRoot = "G:\AI\E-zzio"
$python      = Join-Path $projectRoot ".venv\Scripts\python.exe"
$utf8NoBom   = [System.Text.UTF8Encoding]::new($false)
$timestamp   = Get-Date -Format "yyyyMMdd_HHmmss"

Write-Host ""
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host " E-ZZIO — EMERGENCY RECOVERY & STRICT CERTIFICATION v5.1.0" -ForegroundColor Cyan
Write-Host " TEXT TRUNCATE / PURE AST / NO CHEATING / FAIL-CLOSED" -ForegroundColor DarkCyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "[INFO] Racine : $projectRoot"
Write-Host "[INFO] Python : $python"
Write-Host ""

# =============================================================================
# [1/8] PRÉREQUIS & SNAPSHOT
# =============================================================================
Write-Host "[1/8] Création du snapshot forensique intégral..." -ForegroundColor Cyan

if (-not (Test-Path -LiteralPath $projectRoot -PathType Container)) { throw "Racine introuvable." }
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) { throw "Python introuvable." }

$backupDir = Join-Path $projectRoot "audit\v5.1.0_$timestamp"
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null

Get-ChildItem -Path (Join-Path $projectRoot "core") -Filter "*.py" -Recurse | ForEach-Object {
    $rel = $_.FullName.Substring($projectRoot.Length).TrimStart('\', '/')
    $dest = Join-Path $backupDir $rel
    $destDir = Split-Path $dest -Parent
    if (-not (Test-Path $destDir)) { New-Item -ItemType Directory -Path $destDir -Force | Out-Null }
    Copy-Item -LiteralPath $_.FullName -Destination $dest -Force
}
Write-Host "[PASS] Snapshot garanti dans $backupDir." -ForegroundColor Green

# =============================================================================
# [2/8] EMERGENCY SYNTAX RECOVERY (TEXT TRUNCATE)
# =============================================================================
Write-Host ""
Write-Host "[2/8] Nettoyage d'urgence des corruptions syntaxiques..." -ForegroundColor Cyan

$recoveryScript = @'
import sys
from pathlib import Path

PROJECT_ROOT = Path(r"G:\AI\E-zzio")

def truncate_at(filepath: Path, markers: list[str]):
    if not filepath.exists(): return
    text = filepath.read_text(encoding="utf-8")
    original_text = text
    for marker in markers:
        idx = text.find(marker)
        if idx != -1:
            text = text[:idx]
            
    if text != original_text:
        filepath.write_text(text, encoding="utf-8")
        print(f"[PASS] Fichier tronqué (nettoyé) : {filepath.name}")

def fix_groq(filepath: Path):
    if not filepath.exists(): return
    lines = filepath.read_text(encoding="utf-8").splitlines(keepends=True)
    fixed = []
    changed = False
    for line in lines:
        if 'headers["Authorization"] =' in line and '""}' in line:
            indent = line[:len(line) - len(line.lstrip())]
            fixed.append(indent + 'headers["Authorization"] = f"Bearer {self.api_key.strip()}"\n')
            changed = True
        elif 'headers={"Authorization":' in line and '} if' in line:
            pass # Ignorer les lignes corrompues par regex
        else:
            fixed.append(line)
            
    if changed:
        filepath.write_text("".join(fixed), encoding="utf-8")
        print(f"[PASS] groq.py : Ligne d'en-tête corrompue réparée.")

print("[INFO] Lancement du nettoyage textuel...")
truncate_at(PROJECT_ROOT / "core" / "models" / "router.py", ["    def endpoint(self", "def endpoint(self"])
truncate_at(PROJECT_ROOT / "core" / "models" / "registry.py", ["    def active(self", "def active(self"])
truncate_at(PROJECT_ROOT / "core" / "models" / "fabric.py", ["    def transition(self", "def transition(self", "    def status(self", "def status(self"])
fix_groq(PROJECT_ROOT / "core" / "models" / "discovery" / "groq.py")
print("[PASS] Récupération d'urgence terminée.")
'@

$tempRecovery = Join-Path $projectRoot "_ezzio_emergency_recovery.py"
[System.IO.File]::WriteAllText($tempRecovery, $recoveryScript, $utf8NoBom)
& $python $tempRecovery
Remove-Item $tempRecovery -Force

# =============================================================================
# [3/8] VÉRIFICATION DE COMPILATION (BARRIÈRE STRICTE)
# =============================================================================
Write-Host ""
Write-Host "[3/8] Vérification de la syntaxe Python (Compile Check)..." -ForegroundColor Cyan

$criticalFiles = @(
    (Join-Path $projectRoot "core\models\registry.py"),
    (Join-Path $projectRoot "core\models\router.py"),
    (Join-Path $projectRoot "core\models\fabric.py"),
    (Join-Path $projectRoot "core\models\discovery\groq.py")
)

foreach ($file in $criticalFiles) {
    if (Test-Path $file) {
        & $python -m py_compile $file
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[CRITICAL FAIL] Le fichier $(Split-Path $file -Leaf) est toujours invalide." -ForegroundColor Red
            Write-Host "Arrêt immédiat pour empêcher de nouvelles corruptions." -ForegroundColor Red
            exit 1
        }
        Write-Host "[PASS] $(Split-Path $file -Leaf) est syntaxiquement valide." -ForegroundColor Green
    }
}

# =============================================================================
# [4/8] INJECTION AST CHIRURGICALE
# =============================================================================
Write-Host ""
Write-Host "[4/8] Injection AST propre et vérifiée..." -ForegroundColor Cyan

$astScript = @'
import ast
import sys
from pathlib import Path

PROJECT_ROOT = Path(r"G:\AI\E-zzio")

def get_class(tree: ast.Module, names: list[str]) -> ast.ClassDef:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and any(n in node.name for n in names):
            return node
    raise ValueError(f"Classe {names} introuvable.")

def append_code(filepath: Path, class_names: list[str], code: str):
    source = filepath.read_text("utf-8")
    tree = ast.parse(source)
    cls = get_class(tree, class_names)
    
    end_line = cls.end_lineno if cls.body else cls.lineno
    lines = source.splitlines(keepends=True)
    
    indented = "\n".join(("    " + line if line.strip() else "") for line in code.strip().splitlines())
    lines.insert(end_line, "\n" + indented + "\n")
    
    new_source = "".join(lines)
    ast.parse(new_source) # Validation avant écriture
    filepath.write_text(new_source, "utf-8")

# 1. MODEL RECORD
for p in (PROJECT_ROOT / "core").rglob("*.py"):
    if "class ModelRecord" in p.read_text("utf-8"):
        append_code(p, ["ModelRecord"], '''
lifecycle: str = "DISCOVERED"
tier: str = "UNQUALIFIED"
failure_count: int = 0
historical_failures: int = 0
rehabilitation_count: int = 0
last_quarantine_at: str | None = None
last_quarantine_reason: str | None = None
last_quarantine_operator: str | None = None
rehabilitated_at: str | None = None
rehabilitated_by: str | None = None
rehabilitation_reason: str | None = None
updated_at: str | None = None
''')
        print(f"[PASS] Schéma ModelRecord complété dans {p.name}")

# 2. REGISTRY
reg_path = PROJECT_ROOT / "core" / "models" / "registry.py"
append_code(reg_path, ["Registry"], '''
def active(self) -> list:
    models = self.all() if hasattr(self, "all") else list(getattr(self, "models", {}).values())
    return [m for m in models if getattr(m, "lifecycle", "") == "ACTIVE" and getattr(m, "tier", "UNQUALIFIED") in {"FAST", "MID", "HEAVY"}]
''')
print("[PASS] registry.active() sécurisé.")

# 3. ROUTER
rout_path = PROJECT_ROOT / "core" / "models" / "router.py"
append_code(rout_path, ["Router"], '''
def endpoint(self, provider: str):
    p = str(provider).strip().lower()
    for attr in ("endpoints", "providers", "_clients"):
        mapping = getattr(self, attr, None)
        if isinstance(mapping, dict):
            for k, v in mapping.items():
                if str(k).strip().lower() == p: return v
    return getattr(self, f"_{p}_client", getattr(self, p, None))
''')
print("[PASS] router.endpoint() sécurisé.")

# 4. FABRIC
fab_path = PROJECT_ROOT / "core" / "models" / "fabric.py"
source = fab_path.read_text("utf-8")
source = source.replace("endpoint = self.router.endpoint(provider)", "endpoint = getattr(self.router, 'endpoint', lambda p: None)(provider)")
fab_path.write_text(source, "utf-8")

append_code(fab_path, ["Fabric"], '''
def transition(self, *, provider: str, model_id: str, new_state: str, actor: str, reason: str, operator: str = "system", new_tier: str | None = None) -> bool:
    from datetime import datetime, timezone
    entry = self.registry.find(provider, model_id)
    if not entry: return False
    old_state = getattr(entry, "lifecycle", "DISCOVERED")
    now_iso = datetime.now(timezone.utc).isoformat()
    allowed = {
        ("DISCOVERED", "CANDIDATE"): ["discovery"],
        ("CANDIDATE", "QUALIFIED"): ["qualification_gate"], ("CANDIDATE", "QUARANTINED"): ["qualification_gate"],
        ("QUALIFIED", "ACTIVE"): ["activate_qualified"], ("QUALIFIED", "UNQUALIFIED"): ["qualification_gate"],
        ("ACTIVE", "QUARANTINED"): ["runtime_violation"], ("ACTIVE", "SUPERSEDED"): ["lifecycle_manager"],
        ("ACTIVE", "RETIRED"): ["lifecycle_manager"], ("QUARANTINED", "CANDIDATE"): ["admin_rehabilitation"],
        ("QUARANTINED", "UNQUALIFIED"): ["qualification_gate"],
    }
    if (old_state, new_state) not in allowed or actor not in allowed[(old_state, new_state)]:
        raise RuntimeError(f"Transition illégale : {old_state} -> {new_state} par {actor}")
        
    if new_state == "QUARANTINED":
        setattr(entry, "tier", "UNQUALIFIED")
        setattr(entry, "failure_count", int(getattr(entry, "failure_count", 0)) + 1)
        setattr(entry, "last_quarantine_at", now_iso)
        setattr(entry, "last_quarantine_reason", str(reason)[:300])
        setattr(entry, "last_quarantine_operator", str(operator)[:100])
        if hasattr(self, "router") and hasattr(self.router, "invalidate_cache"):
            try: self.router.invalidate_cache(provider, model_id)
            except: pass
    elif new_state == "CANDIDATE" and old_state == "QUARANTINED":
        failures = int(getattr(entry, "failure_count", 0))
        setattr(entry, "historical_failures", int(getattr(entry, "historical_failures", 0)) + failures)
        setattr(entry, "failure_count", 0)
        setattr(entry, "rehabilitation_count", int(getattr(entry, "rehabilitation_count", 0)) + 1)
        setattr(entry, "rehabilitated_at", now_iso)
        setattr(entry, "rehabilitated_by", str(operator)[:100])
        setattr(entry, "rehabilitation_reason", str(reason)[:300])
        setattr(entry, "tier", "UNQUALIFIED")
    elif new_state == "ACTIVE":
        if new_tier: setattr(entry, "tier", new_tier)
        
    setattr(entry, "lifecycle", new_state)
    setattr(entry, "updated_at", now_iso)
    self.registry.save()
    return True

def quarantine_runtime_violation(self, *, provider: str, model_id: str, tier: str, reason: str) -> bool:
    return self.transition(provider=provider, model_id=model_id, new_state="QUARANTINED", actor="runtime_violation", reason=reason, operator="runtime_guard", new_tier="UNQUALIFIED")

def rehabilitate_model(self, *, provider: str, model_id: str, reason: str, operator: str) -> bool:
    if not operator or len(str(operator).strip()) < 2: raise ValueError("Opérateur invalide")
    if not reason or len(str(reason).strip()) < 5: raise ValueError("Motif invalide")
    return self.transition(provider=provider, model_id=model_id, new_state="CANDIDATE", actor="admin_rehabilitation", reason=str(reason).strip(), operator=str(operator).strip(), new_tier="UNQUALIFIED")
''')
print("[PASS] fabric.py : Machine d'état centralisée injectée.")
'@

$tempAst = Join-Path $projectRoot "_ezzio_ast_v5.py"
[System.IO.File]::WriteAllText($tempAst, $astScript, $utf8NoBom)
& $python $tempAst
if ($LASTEXITCODE -ne 0) {
    Remove-Item $tempAst -Force
    Write-Host "[CRITICAL FAIL] L'injection AST a échoué." -ForegroundColor Red
    exit 1
}
Remove-Item $tempAst -Force

# =============================================================================
# [5/8] DEUXIÈME VÉRIFICATION DE COMPILATION
# =============================================================================
Write-Host ""
Write-Host "[5/8] Vérification de la syntaxe post-injection..." -ForegroundColor Cyan

foreach ($file in $criticalFiles) {
    if (Test-Path $file) {
        & $python -m py_compile $file
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[CRITICAL FAIL] L'injection a corrompu $(Split-Path $file -Leaf)." -ForegroundColor Red
            exit 1
        }
    }
}
Write-Host "[PASS] Les fichiers sont sains et compilables." -ForegroundColor Green

# =============================================================================
# [6/8] DÉPLOIEMENT DU BANC V5.1.0 LÉGITIME
# =============================================================================
Write-Host ""
Write-Host "[6/8] Génération du banc d'essai (No-Cheat)..." -ForegroundColor Cyan

$testV5Code = @'
"""E-ZZIO Autonomous Model Fabric — Banc Forensic v5.1.0."""

import asyncio
import copy
import sys
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(r"G:\AI\E-zzio").resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.models.fabric import build_fabric
try:
    from core.exceptions import ProviderExhaustedError
except ImportError:
    try:
        from core.models.router import ProviderExhaustedError
    except ImportError:
        class ProviderExhaustedError(Exception): pass

class StrictScorecard:
    def __init__(self): self.results = {}
    def record(self, tid, status, msg):
        self.results[tid] = {"status": status}
        print(f" [{status:<13}] {tid:<8} : {msg}")
    
    def verify(self):
        failed = sum(1 for v in self.results.values() if v["status"] == "FAIL")
        warned = sum(1 for v in self.results.values() if v["status"] == "WARN")
        skipped = sum(1 for v in self.results.values() if v["status"] == "NOT_EXERCISED")
        
        print("\n" + "=" * 70)
        print("=== SCORECARD STRICTE v5.1.0 ===")
        print(f" TOTAL : {len(self.results)}")
        print(f" PASS  : {sum(1 for v in self.results.values() if v['status'] == 'PASS')}")
        print(f" WARN  : {warned}")
        print(f" FAIL  : {failed}")
        print(f" SKIP  : {skipped}")
        print("=" * 70)

        if failed > 0:
            print("\nVERDICT : CERTIFICATION REFUSÉE (Échecs critiques)")
            sys.exit(1)
        if warned > 0:
            print("\nVERDICT : CERTIFICATION REFUSÉE (Avertissements de sécurité)")
            sys.exit(1)
        if skipped > 0:
            print("\nVERDICT : CERTIFICATION INCOMPLÈTE (Tests non exercés)")
            sys.exit(2)
        
        print("\nVERDICT : OFFICIALLY CERTIFIED (Machine d'état prouvée hermétique)")
        sys.exit(0)

async def main():
    load_dotenv(PROJECT_ROOT / ".env")
    score = StrictScorecard()
    print("\n" + "=" * 70)
    print(" E-ZZIO — BANC FORENSIC DE CERTIFICATION v5.1.0")
    print("=" * 70 + "\n")

    fabric = build_fabric(project_root=PROJECT_ROOT)
    all_initial = fabric.registry.all() if hasattr(fabric.registry, "all") else list(getattr(fabric.registry, "models", {}).values())
    snapshot = {(m.provider, m.model_id): copy.deepcopy(m.__dict__) for m in all_initial}

    try:
        # [PIPELINE INITIAL LÉGITIME]
        print("[INIT] Exécution légale du pipeline de qualification...")
        try:
            await fabric.discover()
            qualify_fn = getattr(fabric, "qualify", None) or getattr(fabric, "qualify_candidates", None)
            qual_res = await qualify_fn() if qualify_fn else []
            if hasattr(fabric, "activate_qualified"): fabric.activate_qualified(qual_res)
        except Exception as e:
            print(f"[WARN] Erreur pipeline : {e}")

        active_models = list(fabric.registry.active())
        fast_models = [m for m in active_models if getattr(m, "tier", "") == "FAST"]
        mid_models = [m for m in active_models if getattr(m, "tier", "") == "MID"]

        print(f"[INIT] Modèles ACTIVE : FAST={len(fast_models)} | MID={len(mid_models)}\n")

        # TEST A : FAST
        if fast_models:
            try:
                res = await fabric.router.execute(messages=[{"role": "user", "content": "Ping. Réponds OK."}], tier="FAST", temperature=0.0)
                if "OK" in str(res.get("content", "")).upper(): score.record("TEST_A", "PASS", "Inférence FAST OK.")
                else: score.record("TEST_A", "WARN", "Contrat FAST violé.")
            except Exception as e: score.record("TEST_A", "FAIL", str(e))
        else: score.record("TEST_A", "NOT_EXERCISED", "Aucun FAST.")

        # TEST B : MID
        if mid_models:
            try:
                await fabric.router.execute(messages=[{"role": "user", "content": "Ping."}], tier="MID", temperature=0.0)
                score.record("TEST_B", "PASS", "Inférence MID OK.")
            except Exception as e: score.record("TEST_B", "FAIL", str(e))
        else: score.record("TEST_B", "NOT_EXERCISED", "Aucun MID.")

        # SÉLECTION CIBLE (Sans triche)
        target = mid_models[0] if mid_models else (fast_models[0] if fast_models else None)
        if not target:
            for t in ["TEST_C", "TEST_D", "TEST_E", "TEST_F", "TEST_G", "TEST_H", "TEST_I", "TEST_J"]:
                score.record(t, "NOT_EXERCISED", "Requis : modèle ACTIVE.")
            return score.verify()

        prov, mid = target.provider, target.model_id
        entry = fabric.registry.find(prov, mid)
        saved_fails = int(getattr(entry, "failure_count", 0))

        # TEST C : QUARANTAINE
        try:
            ok = fabric.quarantine_runtime_violation(provider=prov, model_id=mid, tier="FAST", reason="audit")
            entry_c = fabric.registry.find(prov, mid)
            assert getattr(entry_c, "lifecycle", "") == "QUARANTINED"
            score.record("TEST_C", "PASS", "ACTIVE -> QUARANTINED ok.")
        except Exception as e: score.record("TEST_C", "FAIL", str(e))

        # TEST D : EXCLUSION
        try:
            actives = [(m.provider, m.model_id) for m in build_fabric(project_root=PROJECT_ROOT).registry.active()]
            assert (prov, mid) not in actives
            score.record("TEST_D", "PASS", "Exclusion de registry.active() ok.")
        except Exception as e: score.record("TEST_D", "FAIL", str(e))

        # TEST E : REHABILITATION
        try:
            ok = fabric.rehabilitate_model(provider=prov, model_id=mid, reason="audit_rehab", operator="v5")
            entry_e = fabric.registry.find(prov, mid)
            assert getattr(entry_e, "lifecycle", "") == "CANDIDATE"
            score.record("TEST_E", "PASS", "QUARANTINED -> CANDIDATE ok.")
        except Exception as e: score.record("TEST_E", "FAIL", str(e))

        # TEST F : PERSISTANCE
        try:
            entry_f = build_fabric(project_root=PROJECT_ROOT).registry.find(prov, mid)
            assert getattr(entry_f, "lifecycle", "") == "CANDIDATE"
            score.record("TEST_F", "PASS", "Persistance disque ok.")
        except Exception as e: score.record("TEST_F", "FAIL", str(e))

        # TEST G : BYPASS
        try:
            blocked = False
            try:
                fabric.transition(provider=prov, model_id=mid, new_state="ACTIVE", actor="hack", reason="hack")
            except RuntimeError: blocked = True
            assert blocked
            score.record("TEST_G", "PASS", "Bypass direct rejeté.")
        except Exception as e: score.record("TEST_G", "FAIL", str(e))

        # TEST H : ECHEC QUALIF
        try:
            fabric.transition(provider=prov, model_id=mid, new_state="QUARANTINED", actor="qualification_gate", reason="fail")
            assert getattr(fabric.registry.find(prov, mid), "lifecycle", "") == "QUARANTINED"
            score.record("TEST_H", "PASS", "Échec qualif -> QUARANTINED ok.")
        except Exception as e: score.record("TEST_H", "FAIL", str(e))

        # TEST I : SUCCES QUALIF
        try:
            fabric.rehabilitate_model(provider=prov, model_id=mid, reason="reset", operator="v5")
            fabric.transition(provider=prov, model_id=mid, new_state="QUALIFIED", actor="qualification_gate", reason="ok", new_tier="FAST")
            fabric.transition(provider=prov, model_id=mid, new_state="ACTIVE", actor="activate_qualified", reason="ok", new_tier="FAST")
            assert getattr(fabric.registry.find(prov, mid), "lifecycle", "") == "ACTIVE"
            score.record("TEST_I", "PASS", "Cycle complet validé.")
        except Exception as e: score.record("TEST_I", "FAIL", str(e))

        # TEST J : FAIL CLOSED
        try:
            reloaded = build_fabric(project_root=PROJECT_ROOT)
            for m in reloaded.registry.active():
                if getattr(m, "tier", "") == "MID": reloaded.quarantine_runtime_violation(provider=m.provider, model_id=m.model_id, tier="MID", reason="test")
            try:
                await reloaded.router.execute(messages=[{"role": "user", "content": "Ping"}], tier="MID")
                score.record("TEST_J", "FAIL", "Routeur a exécuté sans MID !")
            except ProviderExhaustedError:
                score.record("TEST_J", "PASS", "ProviderExhaustedError : Fail-Closed ok.")
        except Exception as e: score.record("TEST_J", "FAIL", str(e))

    finally:
        print("\n[NETTOYAGE] Restauration inconditionnelle...")
        restorer = build_fabric(project_root=PROJECT_ROOT)
        for (p, m), attrs in snapshot.items():
            ent = restorer.registry.find(p, m)
            if ent:
                for k, v in attrs.items():
                    if not k.startswith("_"): setattr(ent, k, copy.deepcopy(v))
        restorer.registry.save()

    score.verify()

if __name__ == "__main__":
    asyncio.run(main())
'@

$testPath = Join-Path $projectRoot "tests\test_fabric_runtime.py"
[System.IO.File]::WriteAllText($testPath, $testV5Code, $utf8NoBom)
Write-Host "[PASS] test_fabric_runtime.py écrit." -ForegroundColor Green

# =============================================================================
# [7/8] EXÉCUTION DU BANC
# =============================================================================
Write-Host ""
Write-Host "[7/8] Exécution du banc de certification..." -ForegroundColor Cyan
Write-Host ""

$exitCode = 0
try {
    & $python $testPath
    $exitCode = $LASTEXITCODE
} catch {
    Write-Host "[FAIL] Erreur critique PowerShell : $_" -ForegroundColor Red
    $exitCode = 1
}

# =============================================================================
# [8/8] VERDICT FORENSIC
# =============================================================================
Write-Host ""
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host " E-ZZIO — BILAN FORENSIC FINAL v5.1.0" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

if ($exitCode -eq 0) {
    Write-Host "[PASS] CERTIFICATION OFFICIELLE ACCORDÉE" -ForegroundColor Green
    Write-Host "[PASS] AST : Validé & Conforme"
    Write-Host "[PASS] State Machine : Hermétique"
    Write-Host "[PASS] Persistance : Garantie"
} elseif ($exitCode -eq 2) {
    Write-Host "[WARN] CERTIFICATION INCOMPLÈTE" -ForegroundColor Yellow
    Write-Host "[WARN] L'état actuel du catalogue (aucun modèle qualifié)" -ForegroundColor Yellow
    Write-Host "[WARN] n'a pas permis d'exercer tous les contrats." -ForegroundColor Yellow
} else {
    Write-Host "[FAIL] CERTIFICATION REFUSÉE" -ForegroundColor Red
    Write-Host "[INFO] Les erreurs bloquantes ont été enregistrées." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "======================================================================" -ForegroundColor DarkGray
Write-Host " Session terminée." -ForegroundColor White
Write-Host "======================================================================" -ForegroundColor DarkGray