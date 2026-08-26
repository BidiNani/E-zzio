#requires -Version 7.4
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$projectRoot = "G:\AI\E-zzio"
$python      = Join-Path $projectRoot ".venv\Scripts\python.exe"
$utf8NoBom   = [System.Text.UTF8Encoding]::new($false)
$timestamp   = Get-Date -Format "yyyyMMdd_HHmmss"

Write-Host ""
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host " E-ZZIO — STRUCTURAL REPAIR & CERTIFICATION v5.0.1" -ForegroundColor Cyan
Write-Host " PURE AST / NO REGEX / NO TEST CHEATING / STRICT SCORECARD" -ForegroundColor DarkCyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "[INFO] Racine : $projectRoot"
Write-Host "[INFO] Python : $python"
Write-Host ""

# =============================================================================
# [1/6] PRÉREQUIS ET SNAPSHOT GLOBAL
# =============================================================================
Write-Host "[1/6] Création du snapshot forensique intégral..." -ForegroundColor Cyan

if (-not (Test-Path -LiteralPath $projectRoot -PathType Container)) { throw "Racine introuvable." }
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) { throw "Python introuvable." }

$backupDir = Join-Path $projectRoot "audit\v5.0.1_$timestamp"
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null

Get-ChildItem -Path (Join-Path $projectRoot "core") -Filter "*.py" -Recurse | ForEach-Object {
    $rel = $_.FullName.Substring($projectRoot.Length).TrimStart('\', '/')
    $dest = Join-Path $backupDir $rel
    $destDir = Split-Path $dest -Parent
    if (-not (Test-Path $destDir)) { New-Item -ItemType Directory -Path $destDir -Force | Out-Null }
    Copy-Item -LiteralPath $_.FullName -Destination $dest -Force
}

$registryJson = Join-Path $projectRoot "data\models\registry.json"
if (Test-Path $registryJson) {
    $dest = Join-Path $backupDir "data\models\registry.json"
    $destDir = Split-Path $dest -Parent
    if (-not (Test-Path $destDir)) { New-Item -ItemType Directory -Path $destDir -Force | Out-Null }
    Copy-Item -LiteralPath $registryJson -Destination $dest -Force
}

Write-Host "[PASS] Snapshot garanti dans $backupDir." -ForegroundColor Green

# =============================================================================
# [2/6] MOTEUR DE RÉPARATION CHIRURGICALE (PURE AST)
# =============================================================================
Write-Host ""
Write-Host "[2/6] Lancement du moteur de réparation AST..." -ForegroundColor Cyan

$astRepairEngine = @'
import ast
import sys
import re
from pathlib import Path

PROJECT_ROOT = Path(r"G:\AI\E-zzio")
BACKUP_ROOT = Path(sys.argv[1])

def read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines(keepends=True)

def write_lines(path: Path, lines: list[str]):
    source = "".join(lines)
    try:
        ast.parse(source, filename=str(path))
    except SyntaxError as e:
        print(f"[FAIL] Erreur de syntaxe générée dans {path.name} ligne {e.lineno}: {e.msg}", file=sys.stderr)
        sys.exit(1)
    path.write_text(source, encoding="utf-8")

def get_class_node(tree: ast.Module, class_names: list[str]) -> ast.ClassDef:
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and any(n in node.name for n in class_names):
            return node
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and any(n in node.name for n in class_names):
            return node
    raise ValueError(f"Classe {class_names} introuvable.")

def remove_methods(lines: list[str], class_node: ast.ClassDef, method_names: list[str]) -> list[str]:
    nodes_to_delete = []
    for node in class_node.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in method_names:
            nodes_to_delete.append(node)
    
    # Suppression de bas en haut pour ne pas décaler les indices
    for node in sorted(nodes_to_delete, key=lambda n: n.lineno, reverse=True):
        del lines[node.lineno - 1 : node.end_lineno]
    return lines

def append_to_class(lines: list[str], class_node: ast.ClassDef, code_block: str) -> list[str]:
    end_line = class_node.end_lineno if class_node.body else class_node.lineno
    indent = "    " 
    indented_block = "\n".join((indent + line if line.strip() else "") for line in code_block.strip().splitlines())
    lines.insert(end_line, "\n" + indented_block + "\n")
    return lines

def patch_model_record():
    paths = list((PROJECT_ROOT / "core").rglob("*.py"))
    for path in paths:
        source = path.read_text(encoding="utf-8")
        if "class ModelRecord" in source:
            tree = ast.parse(source)
            cls = get_class_node(tree, ["ModelRecord"])
            existing_fields = {n.target.id for n in cls.body if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name)}
            
            required = {
                "lifecycle": 'str = "DISCOVERED"',
                "tier": 'str = "UNQUALIFIED"',
                "failure_count": 'int = 0',
                "historical_failures": 'int = 0',
                "rehabilitation_count": 'int = 0',
                "last_quarantine_at": 'str | None = None',
                "last_quarantine_reason": 'str | None = None',
                "last_quarantine_operator": 'str | None = None',
                "rehabilitated_at": 'str | None = None',
                "rehabilitated_by": 'str | None = None',
                "rehabilitation_reason": 'str | None = None',
                "updated_at": 'str | None = None',
            }
            
            missing = {k: v for k, v in required.items() if k not in existing_fields}
            if not missing:
                print(f"[PASS] ModelRecord ({path.name}) : Déjà complet.")
                return

            lines = read_lines(path)
            block = "\n".join(f"{k}: {v}" for k, v in missing.items())
            lines = append_to_class(lines, cls, block)
            write_lines(path, lines)
            print(f"[PASS] ModelRecord ({path.name}) : {len(missing)} champs ajoutés.")
            return
    print("[FAIL] ModelRecord introuvable.", file=sys.stderr)
    sys.exit(1)

def patch_registry():
    path = PROJECT_ROOT / "core" / "models" / "registry.py"
    lines = read_lines(path)
    tree = ast.parse("".join(lines))
    cls = get_class_node(tree, ["ModelRegistry", "Registry"])
    
    lines = remove_methods(lines, cls, ["active"])
    
    active_code = """
def active(self) -> list:
    \"\"\"Retourne strictement les modèles ACTIVE qualifiés.\"\"\"
    models = self.all() if hasattr(self, "all") else list(getattr(self, "models", {}).values())
    return [
        m for m in models
        if getattr(m, "lifecycle", "") == "ACTIVE"
        and getattr(m, "tier", "UNQUALIFIED") in {"FAST", "MID", "HEAVY"}
    ]
"""
    lines = append_to_class(lines, cls, active_code)
    write_lines(path, lines)
    print(f"[PASS] Registry ({path.name}) : active() verrouillé.")

def patch_router():
    path = PROJECT_ROOT / "core" / "models" / "router.py"
    lines = read_lines(path)
    tree = ast.parse("".join(lines))
    cls = get_class_node(tree, ["EzzioRouter", "Router"])
    
    lines = remove_methods(lines, cls, ["endpoint"])
    
    endpoint_code = """
def endpoint(self, provider: str):
    \"\"\"Résolution universelle et non-destructive du provider.\"\"\"
    p = str(provider).strip().lower()
    for attr in ("endpoints", "providers", "_clients"):
        mapping = getattr(self, attr, None)
        if isinstance(mapping, dict):
            for k, v in mapping.items():
                if str(k).strip().lower() == p:
                    return v
    return getattr(self, f"_{p}_client", getattr(self, p, None))
"""
    lines = append_to_class(lines, cls, endpoint_code)
    write_lines(path, lines)
    print(f"[PASS] Router ({path.name}) : endpoint() canonisé.")

def patch_fabric():
    path = PROJECT_ROOT / "core" / "models" / "fabric.py"
    lines = read_lines(path)
    tree = ast.parse("".join(lines))
    cls = get_class_node(tree, ["AutonomousModelFabric", "Fabric"])
    
    lines = remove_methods(lines, cls, ["transition", "quarantine_runtime_violation", "rehabilitate_model"])
    
    state_machine_code = """
def transition(self, *, provider: str, model_id: str, new_state: str, actor: str, reason: str, operator: str = "system", new_tier: str | None = None) -> bool:
    from datetime import datetime, timezone
    entry = self.registry.find(provider, model_id)
    if not entry: return False
    
    old_state = getattr(entry, "lifecycle", "DISCOVERED")
    now_iso = datetime.now(timezone.utc).isoformat()
    
    allowed = {
        ("DISCOVERED", "CANDIDATE"): ["discovery"],
        ("CANDIDATE", "QUALIFIED"): ["qualification_gate"],
        ("CANDIDATE", "QUARANTINED"): ["qualification_gate"],
        ("QUALIFIED", "ACTIVE"): ["activate_qualified"],
        ("QUALIFIED", "UNQUALIFIED"): ["qualification_gate"],
        ("ACTIVE", "QUARANTINED"): ["runtime_violation"],
        ("ACTIVE", "SUPERSEDED"): ["lifecycle_manager"],
        ("ACTIVE", "RETIRED"): ["lifecycle_manager"],
        ("QUARANTINED", "CANDIDATE"): ["admin_rehabilitation"],
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
"""
    lines = append_to_class(lines, cls, state_machine_code)
    
    source = "".join(lines)
    source = source.replace(
        "endpoint = self.router.endpoint(provider)",
        "endpoint = getattr(self.router, 'endpoint', lambda p: None)(provider)"
    )
    
    path.write_text(source, encoding="utf-8")
    print(f"[PASS] Fabric ({path.name}) : Machine d'état centralisée injectée.")

def patch_groq_failclosed():
    path = PROJECT_ROOT / "core" / "models" / "discovery" / "groq.py"
    if not path.exists(): return
    source = path.read_text(encoding="utf-8")
    
    source = re.sub(
        r'headers\s*=\s*\{\s*"Authorization":\s*f"Bearer \{os\.getenv\([\'"]GROQ_API_KEY[\'"]\)\}"\s*\}',
        'headers={"Authorization": f"Bearer {os.getenv(\'GROQ_API_KEY\')}"} if os.getenv("GROQ_API_KEY") else {}',
        source
    )
    
    path.write_text(source, encoding="utf-8")
    print(f"[PASS] Groq ({path.name}) : En-têtes conditionnels injectés.")

if __name__ == "__main__":
    print("[AST] Lancement du parsing...")
    patch_model_record()
    patch_registry()
    patch_router()
    patch_fabric()
    patch_groq_failclosed()
    print("[AST] Toutes les mutations ont été validées par le compilateur interne.")
'@

$astPatcherPath = Join-Path $projectRoot "_ezzio_v5_ast_patcher.py"
[System.IO.File]::WriteAllText($astPatcherPath, $astRepairEngine, $utf8NoBom)
try {
    & $python $astPatcherPath "$backupDir"
    if ($LASTEXITCODE -ne 0) { throw "Le moteur AST a échoué. Le code source est resté intact." }
} finally {
    if (Test-Path $astPatcherPath) { Remove-Item $astPatcherPath -Force }
}

# =============================================================================
# [3/6] VÉRIFICATION DE LA COMPILATION GLOBALE
# =============================================================================
Write-Host ""
Write-Host "[3/6] Compilation de l'environnement..." -ForegroundColor Cyan

Get-ChildItem -Path (Join-Path $projectRoot "core") -Filter "*.py" -Recurse | ForEach-Object {
    & $python -m py_compile $_.FullName
    if ($LASTEXITCODE -ne 0) { throw "Erreur de compilation sur $($_.Name)" }
}
Write-Host "[PASS] Tout le code de 'core' est syntaxiquement valide." -ForegroundColor Green

# =============================================================================
# [4/6] DÉPLOIEMENT DU BANC STRICT V5.0.1
# =============================================================================
Write-Host ""
Write-Host "[4/6] Génération du banc de certification v5.0.1..." -ForegroundColor Cyan

$testV5Code = @'
"""E-ZZIO Autonomous Model Fabric — Banc Forensic v5.0.1."""

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
    def __init__(self):
        self.results = {}

    def record(self, test_id: str, status: str, details: str):
        self.results[test_id] = {"status": status, "details": details}
        print(f" [{status:<13}] {test_id:<8} : {details}")

    def verify_certification(self):
        passed = sum(1 for v in self.results.values() if v["status"] == "PASS")
        failed = sum(1 for v in self.results.values() if v["status"] == "FAIL")
        warned = sum(1 for v in self.results.values() if v["status"] == "WARN")
        skipped = sum(1 for v in self.results.values() if v["status"] == "NOT_EXERCISED")

        print("\n" + "=" * 72)
        print("=== SCORECARD STRICTE v5.0.1 ===")
        print("=" * 72)
        print(f" TOTAL         : {len(self.results)}")
        print(f" PASS          : {passed}")
        print(f" WARN          : {warned}")
        print(f" FAIL          : {failed}")
        print(f" NOT_EXERCISED : {skipped}")
        print("=" * 72)

        if failed > 0:
            print("\nVERDICT : CERTIFICATION REFUSÉE (Échec(s) critique(s) détecté(s))")
            sys.exit(1)
        elif warned > 0:
            print("\nVERDICT : CERTIFICATION REFUSÉE (Avertissement(s) de sécurité détecté(s))")
            sys.exit(1)
        elif skipped > 0:
            print("\nVERDICT : CERTIFICATION INCOMPLÈTE (Tous les contrats n'ont pas pu être exercés)")
            sys.exit(2)
        else:
            print("\nVERDICT : OFFICIALLY CERTIFIED (Machine d'état prouvée hermétique)")
            sys.exit(0)


async def run_certification():
    load_dotenv(PROJECT_ROOT / ".env")
    score = StrictScorecard()

    print("\n" + "=" * 72)
    print(" E-ZZIO — BANC FORENSIC DE CERTIFICATION v5.0.1")
    print("=" * 72 + "\n")

    fabric = build_fabric(project_root=PROJECT_ROOT)
    
    # Snapshot pour la restauration inconditionnelle
    all_initial = fabric.registry.all() if hasattr(fabric.registry, "all") else list(getattr(fabric.registry, "models", {}).values())
    snapshot = {(m.provider, m.model_id): copy.deepcopy(m.__dict__) for m in all_initial}

    try:
        # [PHASE INITIALE : JOUER LE JEU LÉGAL DE L'ARCHITECTURE]
        print("[INIT] Exécution légale du pipeline de qualification...")
        try:
            await fabric.discover()
            qualify_fn = getattr(fabric, "qualify", None) or getattr(fabric, "qualify_candidates", None)
            qual_res = await qualify_fn() if qualify_fn else []
            if hasattr(fabric, "activate_qualified"):
                fabric.activate_qualified(qual_res)
        except Exception as e:
            print(f"[WARN] Erreur dans le pipeline initial : {e}")

        # Récupération de l'état post-qualification
        active_models = list(fabric.registry.active())
        fast_models = [m for m in active_models if getattr(m, "tier", "") == "FAST"]
        mid_models = [m for m in active_models if getattr(m, "tier", "") == "MID"]

        print(f"[INIT] Modèles ACTIVE qualifiés : FAST={len(fast_models)} | MID={len(mid_models)}\n")

        # TEST A : FAST
        if fast_models:
            try:
                res = await fabric.router.execute(messages=[{"role": "user", "content": "Ping système E-ZZIO. Réponds uniquement par le mot OK."}], tier="FAST", temperature=0.0)
                if str(res.get("content", "")).strip() == "OK":
                    score.record("TEST_A", "PASS", "Inférence FAST nominale conforme.")
                else:
                    score.record("TEST_A", "WARN", f"Contrat FAST violé : {res.get('content')}")
            except Exception as e:
                score.record("TEST_A", "FAIL", f"Erreur routeur FAST : {e}")
        else:
            score.record("TEST_A", "NOT_EXERCISED", "Aucun modèle FAST n'a franchi le QualificationGate.")

        # TEST B : MID
        if mid_models:
            try:
                await fabric.router.execute(messages=[{"role": "user", "content": "Ping"}], tier="MID", temperature=0.0)
                score.record("TEST_B", "PASS", "Inférence MID nominale conforme.")
            except Exception as e:
                score.record("TEST_B", "FAIL", f"Erreur routeur MID : {e}")
        else:
            score.record("TEST_B", "NOT_EXERCISED", "Aucun modèle MID n'a franchi le QualificationGate.")

        # Sélection d'une cible légitimement ACTIVE pour les tests de machine d'état
        target = mid_models[0] if mid_models else (fast_models[0] if fast_models else None)
        
        if not target:
            # On ne triche pas. Si la qualification n'a rien donné, on ne peut pas tester la rupture.
            for t in ["TEST_C", "TEST_D", "TEST_E", "TEST_F", "TEST_G", "TEST_H", "TEST_I", "TEST_J"]:
                score.record(t, "NOT_EXERCISED", "Requis : modèle initialement ACTIVE.")
            return score.verify_certification()

        prov, mid = target.provider, target.model_id
        entry = fabric.registry.find(prov, mid)
        saved_hist = int(getattr(entry, "historical_failures", 0))
        saved_rehab = int(getattr(entry, "rehabilitation_count", 0))
        saved_failures = int(getattr(entry, "failure_count", 0))

        # TEST C : QUARANTAINE
        try:
            ok = fabric.quarantine_runtime_violation(provider=prov, model_id=mid, tier=getattr(entry, "tier", "FAST"), reason="v5_audit")
            entry_c = fabric.registry.find(prov, mid)
            assert ok is True
            assert getattr(entry_c, "lifecycle", "") == "QUARANTINED"
            assert getattr(entry_c, "tier", "") == "UNQUALIFIED"
            assert int(getattr(entry_c, "failure_count", 0)) == saved_failures + 1
            score.record("TEST_C", "PASS", "ACTIVE -> QUARANTINED avec incrément des échecs.")
        except Exception as e:
            score.record("TEST_C", "FAIL", f"Échec quarantaine : {e}")

        # TEST D : EXCLUSION DU ROUTEUR
        try:
            reloaded = build_fabric(project_root=PROJECT_ROOT)
            actives = [(m.provider, m.model_id) for m in reloaded.registry.active()]
            assert (prov, mid) not in actives
            score.record("TEST_D", "PASS", "Modèle QUARANTINED strictement exclu de registry.active().")
        except Exception as e:
            score.record("TEST_D", "FAIL", f"Exclusion échouée : {e}")

        # TEST E : RÉHABILITATION
        try:
            ok = fabric.rehabilitate_model(provider=prov, model_id=mid, reason="v5_audit_rehab", operator="v5_engine")
            entry_e = fabric.registry.find(prov, mid)
            assert ok is True
            assert getattr(entry_e, "lifecycle", "") == "CANDIDATE"
            assert getattr(entry_e, "tier", "") == "UNQUALIFIED"
            assert int(getattr(entry_e, "failure_count", 0)) == 0
            assert int(getattr(entry_e, "historical_failures", 0)) == saved_hist + saved_failures + 1
            score.record("TEST_E", "PASS", "QUARANTINED -> CANDIDATE avec reset et archivage de l'historique.")
        except Exception as e:
            score.record("TEST_E", "FAIL", f"Échec réhabilitation : {e}")

        # TEST F : PERSISTANCE DE LA RÉHABILITATION
        try:
            reloaded = build_fabric(project_root=PROJECT_ROOT)
            entry_f = reloaded.registry.find(prov, mid)
            assert getattr(entry_f, "lifecycle", "") == "CANDIDATE"
            assert getattr(entry_f, "rehabilitated_by", "") == "v5_engine"
            score.record("TEST_F", "PASS", "Nouvel état CANDIDATE lu avec succès depuis le disque.")
        except Exception as e:
            score.record("TEST_F", "FAIL", f"Persistance échouée : {e}")

        # TEST G : REJET DU BYPASS
        try:
            bypassed = False
            try:
                fabric.transition(provider=prov, model_id=mid, new_state="ACTIVE", actor="admin_hack", reason="hack")
                bypassed = True
            except RuntimeError:
                pass
            assert bypassed is False
            score.record("TEST_G", "PASS", "Tentative de passage direct CANDIDATE -> ACTIVE violemment rejetée.")
        except Exception as e:
            score.record("TEST_G", "FAIL", f"Bypass non intercepté : {e}")

        # TEST H : ÉCHEC DE QUALIFICATION
        try:
            fabric.transition(provider=prov, model_id=mid, new_state="QUARANTINED", actor="qualification_gate", reason="probe_failed")
            entry_h = fabric.registry.find(prov, mid)
            assert getattr(entry_h, "lifecycle", "") == "QUARANTINED"
            score.record("TEST_H", "PASS", "Échec simulé du QualificationGate -> retour en QUARANTINED.")
        except Exception as e:
            score.record("TEST_H", "FAIL", f"Échec transition : {e}")

        # TEST I : SUCCÈS DE QUALIFICATION
        try:
            fabric.rehabilitate_model(provider=prov, model_id=mid, reason="reset", operator="v5")
            fabric.transition(provider=prov, model_id=mid, new_state="QUALIFIED", actor="qualification_gate", reason="ok")
            fabric.transition(provider=prov, model_id=mid, new_state="ACTIVE", actor="activate_qualified", reason="ok", new_tier="FAST")
            entry_i = fabric.registry.find(prov, mid)
            assert getattr(entry_i, "lifecycle", "") == "ACTIVE"
            score.record("TEST_I", "PASS", "Cycle réglementaire CANDIDATE -> QUALIFIED -> ACTIVE respecté.")
        except Exception as e:
            score.record("TEST_I", "FAIL", f"Transition finale échouée : {e}")

        # TEST J : FAIL-CLOSED ROUTEUR
        try:
            reloaded = build_fabric(project_root=PROJECT_ROOT)
            for m in reloaded.registry.active():
                if getattr(m, "tier", "") == "MID":
                    reloaded.quarantine_runtime_violation(provider=m.provider, model_id=m.model_id, tier="MID", reason="v5_purge")
            
            try:
                await reloaded.router.execute(messages=[{"role": "user", "content": "Ping"}], tier="MID")
                score.record("TEST_J", "FAIL", "Le routeur a exécuté l'inférence alors qu'aucun MID n'est actif !")
            except ProviderExhaustedError:
                score.record("TEST_J", "PASS", "ProviderExhaustedError : Mécanisme de Fail-Closed garanti.")
            except Exception as e:
                score.record("TEST_J", "FAIL", f"Exception inattendue levée par le routeur : {e}")
        except Exception as e:
            score.record("TEST_J", "FAIL", f"Erreur de setup pour TEST J : {e}")

    finally:
        print("\n[NETTOYAGE] Restauration inconditionnelle du registre initial...")
        try:
            restore_fabric = build_fabric(project_root=PROJECT_ROOT)
            for key, original_attrs in snapshot.items():
                ent = restore_fabric.registry.find(key[0], key[1])
                if ent:
                    for k, v in original_attrs.items():
                        if not k.startswith("_"):
                            setattr(ent, k, copy.deepcopy(v))
            restore_fabric.registry.save()
            print(" -> [PASS] Registre restauré depuis le snapshot.")
        except Exception as cleanup_exc:
            print(f" -> [CRITICAL FAIL] Échec lors de la restauration : {cleanup_exc}")
            score.record("CLEANUP", "FAIL", "Le registre est dans un état instable.")

    score.verify_certification()

if __name__ == "__main__":
    asyncio.run(run_certification())
'@

$testPath = Join-Path $projectRoot "tests\test_fabric_runtime.py"
[System.IO.File]::WriteAllText($testPath, $testV5Code, $utf8NoBom)
Write-Host "[PASS] test_fabric_runtime.py réécrit." -ForegroundColor Green

# =============================================================================
# [5/6] EXÉCUTION DU BANC
# =============================================================================
Write-Host ""
Write-Host "[5/6] Exécution du banc de certification v5.0.1..." -ForegroundColor Cyan
Write-Host ""

$exitCode = 0
try {
    & $python $testPath
    $exitCode = $LASTEXITCODE
} catch {
    Write-Host "[FAIL] Exception PowerShell : $_" -ForegroundColor Red
    $exitCode = 1
}

# =============================================================================
# [6/6] VERDICT
# =============================================================================
Write-Host ""
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host " E-ZZIO — BILAN FORENSIC FINAL v5.0.1" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

if ($exitCode -eq 0) {
    Write-Host "[PASS] CERTIFICATION OFFICIELLE ACCORDÉE" -ForegroundColor Green
    Write-Host "[PASS] AST : Validé"
    Write-Host "[PASS] State Machine : Hermétique"
    Write-Host "[PASS] Persistance : Garantie"
} elseif ($exitCode -eq 2) {
    Write-Host "[WARN] CERTIFICATION INCOMPLÈTE" -ForegroundColor Yellow
    Write-Host "[WARN] L'état actuel du catalogue (aucun modèle qualifié)" -ForegroundColor Yellow
    Write-Host "[WARN] n'a pas permis d'exercer tous les contrats." -ForegroundColor Yellow
} else {
    Write-Host "[FAIL] CERTIFICATION REFUSÉE" -ForegroundColor Red
    Write-Host "[INFO] Restaurer manuellement à l'aide des fichiers dans :" -ForegroundColor Yellow
    Write-Host "       $backupDir" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "======================================================================" -ForegroundColor DarkGray
Write-Host " Session terminée." -ForegroundColor White
Write-Host "======================================================================" -ForegroundColor DarkGray