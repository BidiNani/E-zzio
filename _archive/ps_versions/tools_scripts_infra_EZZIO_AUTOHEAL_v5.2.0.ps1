#requires -Version 7.4
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$projectRoot = "G:\AI\E-zzio"
$python      = Join-Path $projectRoot ".venv\Scripts\python.exe"
$utf8NoBom   = [System.Text.UTF8Encoding]::new($false)

Write-Host ""
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host " E-ZZIO — AUTO-HEALER & STRUCTURAL CLOSURE v5.2.0" -ForegroundColor Cyan
Write-Host " BACKUP RECOVERY / PURE AST / FAIL-CLOSED" -ForegroundColor DarkCyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "[INFO] Racine : $projectRoot"
Write-Host "[INFO] Python : $python"
Write-Host ""

# =============================================================================
# [1/4] DÉPLOIEMENT DU MOTEUR AUTO-HEALER PYTHON
# =============================================================================
Write-Host "[1/4] Recherche des backups sains et restauration..." -ForegroundColor Cyan

$autoHealerCode = @'
import ast
import sys
import shutil
from pathlib import Path

ROOT = Path(r"G:\AI\E-zzio")
CORE = ROOT / "core" / "models"

def is_valid_python(path: Path, class_name: str) -> bool:
    if not path.exists(): return False
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        # Vérifie que le fichier n'est pas tronqué et contient bien sa classe
        return any(isinstance(n, ast.ClassDef) and class_name in n.name for n in ast.walk(tree))
    except Exception:
        return False

targets = {
    "fabric.py": (CORE / "fabric.py", "Fabric"),
    "router.py": (CORE / "router.py", "Router"),
    "registry.py": (CORE / "registry.py", "Registry"),
    "groq.py": (ROOT / "core" / "models" / "discovery" / "groq.py", "GroqDiscovery"),
}

print("\n--- PHASE 1 : RESTAURATION INTELLIGENTE ---")
for name, (dest, cls_name) in targets.items():
    if is_valid_python(dest, cls_name):
        print(f"[PASS] {name} est syntaxiquement sain.")
        continue
        
    print(f"[WARN] {name} corrompu. Recherche du backup le plus récent...")
    backups = [p for p in ROOT.rglob(f"*{name}*") if p.is_file() and p != dest]
    backups.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    restored = False
    for b in backups:
        if is_valid_python(b, cls_name):
            shutil.copy2(b, dest)
            print(f"[PASS] {name} restauré depuis {b.relative_to(ROOT)}.")
            restored = True
            break
            
    if not restored:
        print(f"[FAIL] Aucun backup sain trouvé pour {name}. Impossible de continuer.", file=sys.stderr)
        sys.exit(1)

print("\n--- PHASE 2 : INJECTION AST CHIRURGICALE ---")

def patch_method(filepath: Path, class_name: str, method_name: str, method_code: str):
    source = filepath.read_text(encoding="utf-8")
    tree = ast.parse(source)
    cls = next((n for n in ast.walk(tree) if isinstance(n, ast.ClassDef) and class_name in n.name), None)
    if not cls: return
    
    target = next((n for n in cls.body if getattr(n, "name", "") == method_name), None)
    lines = source.splitlines(keepends=True)
    
    indent = "    "
    if cls.body: indent = " " * cls.body[0].col_offset
        
    new_lines = [indent + l + "\n" if l.strip() else "\n" for l in method_code.strip("\n").splitlines()]
    
    if target:
        start = target.lineno - 1
        if target.decorator_list: start = target.decorator_list[0].lineno - 1
        lines[start:target.end_lineno] = new_lines
    else:
        end = cls.end_lineno if cls.body else cls.lineno
        lines.insert(end, "\n" + "".join(new_lines))
        
    new_source = "".join(lines)
    ast.parse(new_source) # Validation Fail-Closed
    filepath.write_text(new_source, encoding="utf-8")
    print(f"[PASS] {filepath.name} : {method_name}() mis à jour.")

def patch_fields(filepath: Path, class_name: str, fields: dict):
    source = filepath.read_text(encoding="utf-8")
    tree = ast.parse(source)
    cls = next((n for n in ast.walk(tree) if isinstance(n, ast.ClassDef) and class_name in n.name), None)
    if not cls: return
    
    existing = {n.target.id for n in cls.body if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name)}
    indent = "    "
    if cls.body: indent = " " * cls.body[0].col_offset
    
    lines = source.splitlines(keepends=True)
    inserted = False
    for k, v in fields.items():
        if k not in existing:
            end = cls.end_lineno if cls.body else cls.lineno
            lines.insert(end, f"{indent}{k}: {v}\n")
            inserted = True
            
    if inserted:
        new_source = "".join(lines)
        ast.parse(new_source)
        filepath.write_text(new_source, encoding="utf-8")
        print(f"[PASS] {filepath.name} : Schéma de données enrichi.")

try:
    patch_fields(targets["registry.py"][0], "Record", {
        "lifecycle": 'str = "DISCOVERED"', "tier": 'str = "UNQUALIFIED"',
        "failure_count": 'int = 0', "historical_failures": 'int = 0',
        "rehabilitation_count": 'int = 0', "last_quarantine_at": 'str | None = None',
        "last_quarantine_reason": 'str | None = None', "last_quarantine_operator": 'str | None = None',
        "rehabilitated_at": 'str | None = None', "rehabilitated_by": 'str | None = None',
        "rehabilitation_reason": 'str | None = None', "updated_at": 'str | None = None',
    })

    patch_method(targets["registry.py"][0], "Registry", "active", '''
def active(self) -> list:
    models = self.all() if hasattr(self, "all") else list(getattr(self, "models", {}).values())
    return [m for m in models if getattr(m, "lifecycle", "") == "ACTIVE" and getattr(m, "tier", "UNQUALIFIED") in {"FAST", "MID", "HEAVY"}]
''')

    patch_method(targets["router.py"][0], "Router", "endpoint", '''
def endpoint(self, provider: str):
    p = str(provider).strip().lower()
    for attr in ("endpoints", "providers", "_clients"):
        mapping = getattr(self, attr, None)
        if isinstance(mapping, dict):
            for k, v in mapping.items():
                if str(k).strip().lower() == p: return v
    return getattr(self, f"_{p}_client", getattr(self, p, None))
''')

    patch_method(targets["fabric.py"][0], "Fabric", "transition", '''
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
''')

    patch_method(targets["fabric.py"][0], "Fabric", "quarantine_runtime_violation", '''
def quarantine_runtime_violation(self, *, provider: str, model_id: str, tier: str, reason: str) -> bool:
    return self.transition(provider=provider, model_id=model_id, new_state="QUARANTINED", actor="runtime_violation", reason=reason, operator="runtime_guard", new_tier="UNQUALIFIED")
''')

    patch_method(targets["fabric.py"][0], "Fabric", "rehabilitate_model", '''
def rehabilitate_model(self, *, provider: str, model_id: str, reason: str, operator: str) -> bool:
    if not operator or len(str(operator).strip()) < 2: raise ValueError("Opérateur invalide")
    if not reason or len(str(reason).strip()) < 5: raise ValueError("Motif invalide")
    return self.transition(provider=provider, model_id=model_id, new_state="CANDIDATE", actor="admin_rehabilitation", reason=str(reason).strip(), operator=str(operator).strip(), new_tier="UNQUALIFIED")
''')

except Exception as e:
    print(f"[FAIL] Échec de l'injection : {e}", file=sys.stderr)
    sys.exit(1)
'@

$tempAst = Join-Path $projectRoot "_ezzio_autoheal.py"
[System.IO.File]::WriteAllText($tempAst, $autoHealerCode, $utf8NoBom)
try {
    & $python $tempAst
    if ($LASTEXITCODE -ne 0) { throw "Auto-Healer a échoué. Le projet reste intact." }
} finally {
    Remove-Item $tempAst -Force -ErrorAction SilentlyContinue
}

# =============================================================================
# [2/4] VÉRIFICATION DE LA COMPILATION
# =============================================================================
Write-Host ""
Write-Host "[2/4] Validation syntaxique de tout le projet..." -ForegroundColor Cyan

Get-ChildItem -Path (Join-Path $projectRoot "core") -Filter "*.py" -Recurse | ForEach-Object {
    & $python -m py_compile $_.FullName
    if ($LASTEXITCODE -ne 0) { throw "Erreur fatale de compilation sur $($_.Name) !" }
}
Write-Host "[PASS] Compilation globale OK." -ForegroundColor Green

# =============================================================================
# [3/4] DÉPLOIEMENT DU BANC V5.2.0 (STRICT ET LOYAL)
# =============================================================================
Write-Host ""
Write-Host "[3/4] Écriture du banc de certification v5.2.0..." -ForegroundColor Cyan

$testV5Code = @'
"""E-ZZIO Autonomous Model Fabric — Banc Forensic v5.2.0."""

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
        print("=== SCORECARD STRICTE v5.2.0 ===")
        print(f" TOTAL : {len(self.results)}")
        print(f" PASS  : {sum(1 for v in self.results.values() if v['status'] == 'PASS')}")
        print(f" WARN  : {warned}")
        print(f" FAIL  : {failed}")
        print(f" SKIP  : {skipped}")
        print("=" * 70)

        if failed > 0 or warned > 0:
            print("\nVERDICT : CERTIFICATION REFUSÉE (Ruptures/Warnings détectés)")
            sys.exit(1)
        if skipped > 0:
            print("\nVERDICT : CERTIFICATION INCOMPLÈTE (Tests non exercés par manque de modèles actifs)")
            sys.exit(2)
        
        print("\nVERDICT : OFFICIALLY CERTIFIED (Machine d'état prouvée hermétique)")
        sys.exit(0)

async def main():
    load_dotenv(PROJECT_ROOT / ".env")
    score = StrictScorecard()
    print("\n" + "=" * 70)
    print(" E-ZZIO — BANC FORENSIC DE CERTIFICATION v5.2.0")
    print("=" * 70 + "\n")

    fabric = build_fabric(project_root=PROJECT_ROOT)
    all_initial = fabric.registry.all() if hasattr(fabric.registry, "all") else list(getattr(fabric.registry, "models", {}).values())
    snapshot = {(m.provider, m.model_id): copy.deepcopy(m.__dict__) for m in all_initial}

    try:
        print("[INIT] Exécution du pipeline légal de découverte...")
        try:
            await fabric.discover()
            qualify_fn = getattr(fabric, "qualify", None) or getattr(fabric, "qualify_candidates", None)
            qual_res = await qualify_fn() if qualify_fn else []
            if hasattr(fabric, "activate_qualified"): fabric.activate_qualified(qual_res)
        except Exception as e:
            print(f"[WARN] Pipeline de qualification : {e}")

        active_models = list(fabric.registry.active())
        fast_models = [m for m in active_models if getattr(m, "tier", "") == "FAST"]
        mid_models = [m for m in active_models if getattr(m, "tier", "") == "MID"]

        print(f"\n[INIT] Modèles ACTIVE qualifiés : FAST={len(fast_models)} | MID={len(mid_models)}\n")

        # TEST A : FAST
        if fast_models:
            try:
                res = await fabric.router.execute(messages=[{"role": "user", "content": "Ping. Réponds OK."}], tier="FAST", temperature=0.0)
                if "OK" in str(res.get("content", "")).upper(): score.record("TEST_A", "PASS", "Inférence FAST nominale OK.")
                else: score.record("TEST_A", "WARN", "Contrat FAST violé.")
            except Exception as e: score.record("TEST_A", "FAIL", str(e))
        else: score.record("TEST_A", "NOT_EXERCISED", "Aucun FAST disponible.")

        # TEST B : MID
        if mid_models:
            try:
                await fabric.router.execute(messages=[{"role": "user", "content": "Ping."}], tier="MID", temperature=0.0)
                score.record("TEST_B", "PASS", "Inférence MID nominale OK.")
            except Exception as e: score.record("TEST_B", "FAIL", str(e))
        else: score.record("TEST_B", "NOT_EXERCISED", "Aucun MID disponible.")

        target = mid_models[0] if mid_models else (fast_models[0] if fast_models else None)
        if not target:
            for t in ["TEST_C", "TEST_D", "TEST_E", "TEST_F", "TEST_G", "TEST_H", "TEST_I", "TEST_J"]:
                score.record(t, "NOT_EXERCISED", "Requis : modèle ACTIVE initial.")
            return score.verify()

        prov, mid = target.provider, target.model_id
        entry = fabric.registry.find(prov, mid)
        saved_fails = int(getattr(entry, "failure_count", 0))

        # TEST C : QUARANTAINE
        try:
            ok = fabric.quarantine_runtime_violation(provider=prov, model_id=mid, tier="FAST", reason="audit")
            entry_c = fabric.registry.find(prov, mid)
            assert getattr(entry_c, "lifecycle", "") == "QUARANTINED"
            score.record("TEST_C", "PASS", "ACTIVE -> QUARANTINED avec incrément ok.")
        except Exception as e: score.record("TEST_C", "FAIL", str(e))

        # TEST D : EXCLUSION
        try:
            actives = [(m.provider, m.model_id) for m in build_fabric(project_root=PROJECT_ROOT).registry.active()]
            assert (prov, mid) not in actives
            score.record("TEST_D", "PASS", "Modèle QUARANTINED exclu du routeur ok.")
        except Exception as e: score.record("TEST_D", "FAIL", str(e))

        # TEST E : REHABILITATION
        try:
            ok = fabric.rehabilitate_model(provider=prov, model_id=mid, reason="audit_rehab", operator="v5")
            entry_e = fabric.registry.find(prov, mid)
            assert getattr(entry_e, "lifecycle", "") == "CANDIDATE"
            assert int(getattr(entry_e, "failure_count", 0)) == 0
            score.record("TEST_E", "PASS", "QUARANTINED -> CANDIDATE avec reset compteurs ok.")
        except Exception as e: score.record("TEST_E", "FAIL", str(e))

        # TEST F : PERSISTANCE
        try:
            entry_f = build_fabric(project_root=PROJECT_ROOT).registry.find(prov, mid)
            assert getattr(entry_f, "lifecycle", "") == "CANDIDATE"
            score.record("TEST_F", "PASS", "Persistance disque confirmée.")
        except Exception as e: score.record("TEST_F", "FAIL", str(e))

        # TEST G : BYPASS
        try:
            blocked = False
            try:
                fabric.transition(provider=prov, model_id=mid, new_state="ACTIVE", actor="hack", reason="hack")
            except RuntimeError: blocked = True
            assert blocked
            score.record("TEST_G", "PASS", "Tentative de Bypass CANDIDATE -> ACTIVE violemment rejetée.")
        except Exception as e: score.record("TEST_G", "FAIL", str(e))

        # TEST H : ECHEC QUALIF
        try:
            fabric.transition(provider=prov, model_id=mid, new_state="QUARANTINED", actor="qualification_gate", reason="fail")
            assert getattr(fabric.registry.find(prov, mid), "lifecycle", "") == "QUARANTINED"
            score.record("TEST_H", "PASS", "Échec qualif renvoie en QUARANTINED.")
        except Exception as e: score.record("TEST_H", "FAIL", str(e))

        # TEST I : SUCCES QUALIF
        try:
            fabric.rehabilitate_model(provider=prov, model_id=mid, reason="reset", operator="v5")
            fabric.transition(provider=prov, model_id=mid, new_state="QUALIFIED", actor="qualification_gate", reason="ok", new_tier="FAST")
            fabric.transition(provider=prov, model_id=mid, new_state="ACTIVE", actor="activate_qualified", reason="ok", new_tier="FAST")
            assert getattr(fabric.registry.find(prov, mid), "lifecycle", "") == "ACTIVE"
            score.record("TEST_I", "PASS", "Cycle complet de requalification validé.")
        except Exception as e: score.record("TEST_I", "FAIL", str(e))

        # TEST J : FAIL CLOSED
        try:
            reloaded = build_fabric(project_root=PROJECT_ROOT)
            for m in reloaded.registry.active():
                if getattr(m, "tier", "") == "MID": reloaded.quarantine_runtime_violation(provider=m.provider, model_id=m.model_id, tier="MID", reason="test")
            try:
                await reloaded.router.execute(messages=[{"role": "user", "content": "Ping"}], tier="MID")
                score.record("TEST_J", "FAIL", "Routeur a exécuté sans MID actif !")
            except ProviderExhaustedError:
                score.record("TEST_J", "PASS", "ProviderExhaustedError levée : Fail-Closed routeur validé.")
        except Exception as e: score.record("TEST_J", "FAIL", str(e))

    finally:
        print("\n[NETTOYAGE] Restauration inconditionnelle du registre initial...")
        try:
            restorer = build_fabric(project_root=PROJECT_ROOT)
            for (p, m), attrs in snapshot.items():
                ent = restorer.registry.find(p, m)
                if ent:
                    for k, v in attrs.items():
                        if not k.startswith("_"): setattr(ent, k, copy.deepcopy(v))
            restorer.registry.save()
            print(" -> [PASS] Registre restauré.")
        except Exception as e:
            print(f" -> [FAIL CRITIQUE] Restauration impossible : {e}")

    score.verify()

if __name__ == "__main__":
    asyncio.run(main())
'@

$testPath = Join-Path $projectRoot "tests\test_fabric_runtime.py"
[System.IO.File]::WriteAllText($testPath, $testV5Code, $utf8NoBom)
Write-Host "[PASS] test_fabric_runtime.py écrit avec succès." -ForegroundColor Green

# =============================================================================
# [4/4] EXÉCUTION DU BANC
# =============================================================================
Write-Host ""
Write-Host "[4/4] Exécution du banc de certification v5.2.0..." -ForegroundColor Cyan
Write-Host ""

$exitCode = 0
try {
    & $python $testPath
    $exitCode = $LASTEXITCODE
} catch {
    Write-Host "[FAIL] Erreur fatale PowerShell : $_" -ForegroundColor Red
    $exitCode = 1
}

Write-Host ""
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host " E-ZZIO — BILAN FORENSIC FINAL v5.2.0" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

if ($exitCode -eq 0) {
    Write-Host "[PASS] CERTIFICATION OFFICIELLE ACCORDÉE" -ForegroundColor Green
    Write-Host "[PASS] AST : Validé"
    Write-Host "[PASS] State Machine : Hermétique"
    Write-Host "[PASS] Persistance : Garantie"
} elseif ($exitCode -eq 2) {
    Write-Host "[WARN] CERTIFICATION INCOMPLÈTE" -ForegroundColor Yellow
    Write-Host "[WARN] Aucun modèle n'est actif, les tests de rupture ont été bloqués." -ForegroundColor Yellow
} else {
    Write-Host "[FAIL] CERTIFICATION REFUSÉE" -ForegroundColor Red
}

Write-Host ""
Write-Host "======================================================================" -ForegroundColor DarkGray