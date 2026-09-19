"""fix_all_v3.py - Nettoyage final ruff."""
import datetime
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(r"G:\AI\E-zzio")
PY   = str(ROOT / ".venv" / "Scripts" / "python.exe")
LOG  = ROOT / "state" / "ruff_logs" / f"fix_v3_{datetime.datetime.now():%Y%m%d_%H%M%S}.log"
LOG.parent.mkdir(parents=True, exist_ok=True)

def log(msg, level="INFO"):
    line = f"[{datetime.datetime.now():%H:%M:%S}] [{level}] {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")

def run(args, cwd=ROOT):
    r = subprocess.run(args, cwd=str(cwd), capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return r.returncode, r.stdout, r.stderr

def git(*args):
    rc, out, err = run(["git"] + list(args))
    return rc, out.strip(), err.strip()

# ============================================================
log("=== FIX v3 START ===", "CYAN")

rc, safe_ref, _ = git("rev-parse", "HEAD")
log(f"Rollback : {safe_ref}", "GRAY")

# ------------------------------------------------------------
# 1. F401 : imports d'API publique dans __init__.py
# ------------------------------------------------------------
log("--- 1. F401 (imports API) ---", "CYAN")

# core/kernel/__init__.py : tout est un re-export
p = ROOT / "core" / "kernel" / "__init__.py"
if p.exists():
    src = p.read_text(encoding="utf-8")
    if "# ruff: noqa: F401" not in src:
        # Insérer après le docstring (1re ligne)
        lines = src.splitlines(keepends=True)
        # Chercher fin du docstring
        if lines[0].strip().startswith('"""'):
            # Cas docstring sur une ligne
            if lines[0].rstrip().endswith('"""') and len(lines[0].strip()) > 6:
                insert_at = 1
            else:
                # Docstring multiligne
                for i, ln in enumerate(lines[1:], 1):
                    if '"""' in ln:
                        insert_at = i + 1
                        break
        else:
            insert_at = 0
        lines.insert(insert_at, "# ruff: noqa: F401 — re-exports API publique\n")
        p.write_text("".join(lines), encoding="utf-8")
        log("  [OK] core/kernel/__init__.py", "OK")
    else:
        log("  [SKIP] core/kernel/__init__.py", "GRAY")

p = ROOT / "core" / "models" / "qualification" / "__init__.py"
if p.exists():
    src = p.read_text(encoding="utf-8")
    if "# ruff: noqa: F401" not in src:
        lines = src.splitlines(keepends=True)
        if lines[0].strip().startswith('"""'):
            if lines[0].rstrip().endswith('"""') and len(lines[0].strip()) > 6:
                insert_at = 1
            else:
                for i, ln in enumerate(lines[1:], 1):
                    if '"""' in ln:
                        insert_at = i + 1
                        break
        else:
            insert_at = 0
        lines.insert(insert_at, "# ruff: noqa: F401 — re-exports API publique\n")
        p.write_text("".join(lines), encoding="utf-8")
        log("  [OK] core/models/qualification/__init__.py", "OK")
    else:
        log("  [SKIP] core/models/qualification/__init__.py", "GRAY")

# core/generators/doc_engine.py : retirer Inches
p = ROOT / "core" / "generators" / "doc_engine.py"
if p.exists():
    src = p.read_text(encoding="utf-8")
    old = "    from docx.shared import Inches, Pt, RGBColor"
    new = "    from docx.shared import Pt, RGBColor"
    if old in src:
        p.write_text(src.replace(old, new), encoding="utf-8")
        log("  [OK] doc_engine.py (Inches retiré)", "OK")
    else:
        log("  [SKIP] doc_engine.py", "GRAY")

# ------------------------------------------------------------
# 2. UP035 : typing.Dict → dict (tests)
# ------------------------------------------------------------
log("--- 2. UP035 (typing.Dict) ---", "CYAN")

up035_files = [
    "tests/test_action_verification_engine.py",
    "tests/test_decision_router.py",
    "tests/test_ezzio_core.py",
    "tests/test_research_router.py",
]
for rel in up035_files:
    p = ROOT / rel
    if not p.exists():
        log(f"  [SKIP] {rel}", "GRAY")
        continue
    src = p.read_text(encoding="utf-8")
    # Remplacements sûrs (uniquement Dict en typage)
    new_src = src
    # from typing import Any, Dict  ->  from typing import Any
    new_src = re.sub(r"from typing import Any, Dict\b", "from typing import Any", new_src)
    new_src = re.sub(r"from typing import Dict, Any\b", "from typing import Any", new_src)
    new_src = re.sub(r"from typing import Dict\b", "", new_src)
    # Dict[...] -> dict[...]
    new_src = re.sub(r"\bDict\[", "dict[", new_src)
    # : Dict  ->  : dict   (annotation nue)
    new_src = re.sub(r":\s*Dict\b", ": dict", new_src)
    # -> Dict\b  ->  -> dict
    new_src = re.sub(r"->\s*Dict\b", "-> dict", new_src)
    if new_src != src:
        p.write_text(new_src, encoding="utf-8")
        log(f"  [OK] {rel}", "OK")
    else:
        log(f"  [SKIP] {rel} (aucun changement)", "GRAY")

# ------------------------------------------------------------
# 3. F841 : audit_gate_v6_45_54.py
# ------------------------------------------------------------
log("--- 3. F841 ---", "CYAN")
p = ROOT / "tools" / "archive_gates" / "audit_gate_v6_45_54.py"
if p.exists():
    src = p.read_text(encoding="utf-8")
    old = '    print(files_info := f"[1] CONSOMMATEURS ACTIFS DE AgentProviderAdapter ({len(consumers)} trouvés) :")'
    new = '    print(f"[1] CONSOMMATEURS ACTIFS DE AgentProviderAdapter ({len(consumers)} trouvés) :")'
    if old in src:
        p.write_text(src.replace(old, new), encoding="utf-8")
        log("  [OK] audit_gate_v6_45_54.py", "OK")
    else:
        log("  [SKIP] pattern introuvable", "GRAY")

# ------------------------------------------------------------
# 4. E701 : éclater les "if X: Y" en 2 lignes
# ------------------------------------------------------------
log("--- 4. E701 (one-line colons) ---", "CYAN")

def split_one_line_colons(src):
    """Transforme 'indent code1: code2' en 2 lignes avec indent correct."""
    lines = src.split("\n")
    out = []
    for ln in lines:
        # Regex conservatrice : éviter dict literals, lambdas, etc.
        # Cherche "if X: Y" ou "elif X: Y" ou "else: Y" ou "try: X" ou "except E: X"
        m = re.match(r"^(\s*)(if|elif|else|try|except[^:]*|finally|for [^:]+|while [^:]+|with [^:]+)\s*:\s*(.+)$", ln)
        if m:
            indent = m.group(1)
            keyword = m.group(2)
            body = m.group(3).rstrip()
            # Skip si le body est un commentaire ou vide
            if not body.strip() or body.strip().startswith("#"):
                out.append(ln)
                continue
            # Skip si body contient un autre ":" au même niveau (ex: dict)
            # (heuristique : si body finit par "}" ou contient "{", skip)
            if body.rstrip().endswith(("{", "[", "(")) or "{" in body.split("#")[0]:
                out.append(ln)
                continue
            out.append(f"{indent}{keyword}:")
            out.append(f"{indent}    {body}")
        else:
            out.append(ln)
    return "\n".join(out)

e701_files = [
    "core/accounts/oauth_flow.py",
    "tests/test_fabric_runtime.py",
    "tools/check_secrets.py",
]
for rel in e701_files:
    p = ROOT / rel
    if not p.exists():
        log(f"  [SKIP] {rel}", "GRAY")
        continue
    src = p.read_text(encoding="utf-8")
    new_src = split_one_line_colons(src)
    if new_src != src:
        p.write_text(new_src, encoding="utf-8")
        log(f"  [OK] {rel}", "OK")
    else:
        log(f"  [SKIP] {rel} (aucun changement)", "GRAY")

# ------------------------------------------------------------
# 5. F811 : corrections manuelles ciblées
# ------------------------------------------------------------
log("--- 5. F811 (redefinitions) ---", "CYAN")

# 5a. core/models/fabric.py : supprimer la 2e définition (lignes 485-...)
p = ROOT / "core" / "models" / "fabric.py"
if p.exists():
    src = p.read_text(encoding="utf-8")
    lines = src.splitlines(keepends=True)
    # Trouver les 2 définitions
    def_indices = []
    for i, ln in enumerate(lines):
        if ln.strip().startswith(("def quarantine_runtime_violation", "def rehabilitate_model")):
            def_indices.append((i, ln.strip()[:50]))
    log(f"  [INFO] fabric.py : {len(def_indices)} definitions trouvees")
    for idx, sig in def_indices:
        log(f"    L{idx+1}: {sig}")
    # Ne rien faire automatiquement — risqué sans voir le code

# 5b. core/observability/metrics.py : latency_snapshot (2e def)
p = ROOT / "core" / "observability" / "metrics.py"
if p.exists():
    src = p.read_text(encoding="utf-8")
    lines = src.splitlines(keepends=True)
    def_indices = [i for i, ln in enumerate(lines)
                   if ln.strip().startswith("def latency_snapshot")]
    log(f"  [INFO] metrics.py : {len(def_indices)} definitions latency_snapshot")
    for i in def_indices:
        log(f"    L{i+1}")

# 5c. core/safe_actions.py : 4 fonctions
p = ROOT / "core" / "safe_actions.py"
if p.exists():
    src = p.read_text(encoding="utf-8")
    lines = src.splitlines(keepends=True)
    targets = ["augment_queue_items", "ledger", "status", "run_proposal"]
    for t in targets:
        idxs = [i for i, ln in enumerate(lines) if ln.strip().startswith(f"def {t}")]
        log(f"  [INFO] safe_actions.py : {t} defini {len(idxs)}x aux lignes {[i+1 for i in idxs]}")

log("  [MANUEL] F811 necessite inspection manuelle", "YELLOW")

# ------------------------------------------------------------
# 6. AST check
# ------------------------------------------------------------
log("--- 6. AST check ---", "CYAN")
import ast

bad = []
for f in ROOT.rglob("*.py"):
    if any(x in f.parts for x in (".venv",".git","__pycache__",
                                   ".ruff_cache","node_modules",
                                   "state","_backup_ruff","_archive")):
        continue
    try:
        ast.parse(f.read_text(encoding="utf-8"))
    except SyntaxError as e:
        bad.append(f"{f}:{e.lineno}: {e.msg}")
if bad:
    log(f"AST CASSE : {len(bad)}", "ERROR")
    for b in bad[:10]:
        log("  " + b)
    git("reset", "--hard", safe_ref)
    log("Rollback", "RED")
    sys.exit(1)
log("AST OK", "OK")

# ------------------------------------------------------------
# 7. Frozen core regen (au cas où)
# ------------------------------------------------------------
log("--- 7. Frozen core regen ---", "CYAN")
rc, out, err = run([PY, "-c",
    "from core.frozen_core.manifest import regenerate_manifest; "
    "m = regenerate_manifest(); print('OK', len(m['files']))"])
log(out or err)

# ------------------------------------------------------------
# 8. Pytest
# ------------------------------------------------------------
log("--- 8. pytest ---", "CYAN")
rc, out, err = run([PY, "-m", "pytest", "tests/", "-q", "--tb=line",
                   "--no-header"])
combined = out + err
for line in combined.splitlines()[-15:]:
    log("  " + line)
if rc != 0:
    log("TESTS CASSES - rollback", "ERROR")
    git("reset", "--hard", safe_ref)
    sys.exit(1)
log("Tests OK", "OK")

# ------------------------------------------------------------
# 9. Stats
# ------------------------------------------------------------
log("--- 9. Stats ---", "CYAN")
rc, out, err = run([PY, "-m", "ruff", "check", ".", "--statistics", "--no-cache"])
for line in (out + err).splitlines()[-30:]:
    log("  " + line)

# ------------------------------------------------------------
# 10. Commit
# ------------------------------------------------------------
git("add", "-A")
rc, out, err = run(["git", "commit", "-m",
                   "chore(ruff): E701,F401,F841,UP035 cleanup"])
log(out or err)

log("=== FIX v3 TERMINE ===", "GREEN")
log(f"Log : {LOG}", "GRAY")
