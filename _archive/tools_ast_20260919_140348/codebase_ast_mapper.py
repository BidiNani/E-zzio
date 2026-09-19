#!/usr/bin/env python3
"""E-ZZIO — AST static mapper (Phase 1). Zero-token-waste cartography.

Scans core/, runtime/, routers/ with stdlib ast.
Output: data/audit_graph.json
"""
import ast
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGETS = [ROOT / "core", ROOT / "runtime", ROOT / "routers"]
OUT = ROOT / "data" / "audit_graph.json"

SQLITE_CALLS = {"connect", "execute", "executemany", "executescript", "commit"}
SQLITE_MODS = {"sqlite3", "aiosqlite"}
MODEL_NAME_RE = re.compile(
    r"(gemini-[\w.\-]+|qwen[\w.\-:/]*|llama-[\w.\-:/]*|nemotron[\w.\-:/]*|"
    r"phi4[\w.\-:/]*|granite[\w.\-:/]*|gpt-oss[\w.\-:/]*|nomic-[\w.\-:/]*|"
    r"bge-m3[\w.\-:/]*|claude[\w.\-:/]*|deepseek[\w.\-:/]*)",
    re.IGNORECASE,
)


def module_of(path: Path) -> str:
    return ".".join(path.relative_to(ROOT).with_suffix("").parts)


def parse_file(path: Path) -> dict | None:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception as exc:
        return {"path": str(path.relative_to(ROOT)), "parse_error": str(exc)}
    classes, funcs, imports_out, sqlite_writes, hard_models = [], [], [], [], []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            classes.append(node.name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # top-level + methods (flat, cheap)
            funcs.append(node.name)
        elif isinstance(node, ast.Import):
            for a in node.names:
                imports_out.append(a.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports_out.append("." * node.level + node.module)
        elif isinstance(node, ast.Call):
            f = node.func
            fname = ""
            if isinstance(f, ast.Attribute):
                fname = f.attr
                val = f.value
                mod = ""
                if isinstance(val, ast.Name):
                    mod = val.id
                elif isinstance(val, ast.Attribute):
                    mod = val.attr
                if fname in SQLITE_CALLS and mod in SQLITE_MODS:
                    sqlite_writes.append(f"{mod}.{fname}@{node.lineno}")
            elif isinstance(f, ast.Name):
                fname = f.id
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            for m in MODEL_NAME_RE.findall(node.value):
                if len(m) > 3:
                    hard_models.append(f"{m}@{node.lineno}")
    return {
        "path": str(path.relative_to(ROOT)),
        "module": module_of(path),
        "classes": sorted(set(classes)),
        "functions": sorted(set(funcs)),
        "imports_out": sorted(set(imports_out)),
        "sqlite_writes": sqlite_writes,
        "hardcoded_models": sorted(set(hard_models))[:20],
        "loc": sum(1 for _ in path.read_text(encoding="utf-8", errors="ignore").splitlines()),
    }


def main() -> None:
    files = []
    for base in TARGETS:
        if base.exists():
            files.extend(sorted(base.rglob("*.py")))
    # exclude venv/pycache just in case
    files = [f for f in files if ".venv" not in f.parts and "__pycache__" not in f.parts]

    records = {}
    for f in files:
        rec = parse_file(f)
        if rec:
            records[rec["path"]] = rec

    # incoming imports: map module -> importers
    incoming: dict[str, list[str]] = {r["module"]: [] for r in records.values() if "module" in r}
    for r in records.values():
        if "module" not in r:
            continue
        for imp in r.get("imports_out", []):
            target = imp.lstrip(".")
            for mod in incoming:
                if target == mod or target.startswith(mod + ".") or mod.startswith(target + "."):
                    if r["module"] != mod and r["module"] not in incoming[mod]:
                        incoming[mod].append(r["module"])

    # test mentions
    test_texts: dict[str, str] = {}
    tdir = ROOT / "tests"
    if tdir.exists():
        for t in tdir.rglob("*.py"):
            try:
                test_texts[str(t.relative_to(ROOT))] = t.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                pass
    all_tests = "\n".join(test_texts.values())

    orphans, sqlite_direct, hardcoded = [], [], []
    for path, r in records.items():
        if "module" not in r:
            continue
        mod = r["module"]
        stem = Path(path).stem
        mentioned = any(
            mod in t or stem in t or path.replace("\\", "/") in t.replace("\\", "/")
            for t in test_texts.values()
        ) or (mod in all_tests)
        if not incoming.get(mod) and not mentioned:
            # entry points / __init__ / __main__ guards excluded
            orphans.append(path)
        if r.get("sqlite_writes") and "unified_gateway" not in path.replace("\\", "/"):
            sqlite_direct.append({"file": path, "calls": r["sqlite_writes"][:10]})
        if r.get("hardcoded_models") and "routing/model_registry" not in path.replace("\\", "/"):
            hardcoded.append({"file": path, "models": r["hardcoded_models"][:10]})

    report = {
        "files_scanned": len(records),
        "parse_errors": [p for p, r in records.items() if "parse_error" in r],
        "incoming": incoming,
        "orphans": sorted(orphans),
        "sqlite_direct_writes": sqlite_direct,
        "hardcoded_models_outside_canonical": hardcoded,
        "files": records,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"files={len(records)} orphans={len(orphans)} "
          f"sqlite_direct={len(sqlite_direct)} hardmodel_files={len(hardcoded)}")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    sys.exit(main())
