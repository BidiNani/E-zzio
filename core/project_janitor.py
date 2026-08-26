from __future__ import annotations

import py_compile
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path("G:/AI/E-zzio")
CORE_DIR = PROJECT_ROOT / "core"
ROUTERS_DIR = PROJECT_ROOT / "routers"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
QUARANTINE_DIR = PROJECT_ROOT / "quarantine"

EXCLUDED_PARTS = {
    "backups",
    "logs",
    "quarantine",
    ".git",
    ".venv",
    "node_modules",
    "__pycache__",
}

BAD_PATTERNS = [
    "`r`n",
    "@WebServer",
    "E-ZZZIO",
    "fonctionner sans connexion Internet",
    "sans connexion Internet pour fonctionner",
    "gemma4:12b",
    "qwen2.5:3b",
    "mistral:7b",
]

# Ces fichiers contiennent volontairement certains motifs pour les neutraliser.
ALLOWED_PATTERN_FILES = {
    "core/response_guard.py": {
        "E-ZZZIO",
        "fonctionner sans connexion Internet",
        "sans connexion Internet pour fonctionner",
    },
    "core/pc_model_router.py": set(BAD_PATTERNS),
    "core/project_janitor.py": set(BAD_PATTERNS),
    "core/human_chat_guard.py": set(BAD_PATTERNS),
}


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def rel_posix(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def is_excluded(path: Path) -> bool:
    try:
        parts = set(path.relative_to(PROJECT_ROOT).parts)
    except Exception:
        return True
    return bool(parts.intersection(EXCLUDED_PARTS))


def allowed_for_file(path: Path, pattern: str) -> bool:
    rel = rel_posix(path)
    return pattern in ALLOWED_PATTERN_FILES.get(rel, set())


def interesting_files() -> List[Path]:
    files: List[Path] = []

    for root in [CORE_DIR, ROUTERS_DIR, SCRIPTS_DIR]:
        if root.exists():
            files.extend([p for p in root.rglob("*") if p.is_file()])

    web = PROJECT_ROOT / "web_server.py"
    if web.exists():
        files.append(web)

    return sorted(set(files))


def collect_pattern_issues(path: Path, text: str) -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []

    for pattern in BAD_PATTERNS:
        if pattern not in text:
            continue

        if allowed_for_file(path, pattern):
            continue

        line_no = 1
        context = ""

        for idx, line in enumerate(text.splitlines(), start=1):
            if pattern in line:
                line_no = idx
                context = line.strip()[:220]
                break

        issues.append(
            {
                "kind": "bad_pattern",
                "pattern": pattern,
                "line": line_no,
                "context": context,
            }
        )

    return issues


def audit_python(path: Path) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "path": str(path),
        "relative_path": rel_posix(path),
        "ok": True,
        "type": "python",
        "compile_ok": None,
        "issues": [],
    }

    try:
        py_compile.compile(str(path), doraise=True)
        result["compile_ok"] = True
    except Exception as exc:
        result["compile_ok"] = False
        result["ok"] = False
        result["issues"].append(
            {
                "kind": "compile_error",
                "message": str(exc),
            }
        )

    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        result["lines"] = text.count("\n") + 1
        result["bytes"] = path.stat().st_size

        pattern_issues = collect_pattern_issues(path, text)
        if pattern_issues:
            result["ok"] = False
            result["issues"].extend(pattern_issues)

    except Exception as exc:
        result["ok"] = False
        result["issues"].append(
            {
                "kind": "read_error",
                "message": str(exc),
            }
        )

    return result


def audit_text(path: Path) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "path": str(path),
        "relative_path": rel_posix(path),
        "ok": True,
        "type": path.suffix.lower().lstrip(".") or "file",
        "issues": [],
    }

    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        result["lines"] = text.count("\n") + 1
        result["bytes"] = path.stat().st_size

        pattern_issues = collect_pattern_issues(path, text)
        if pattern_issues:
            result["ok"] = False
            result["issues"].extend(pattern_issues)

    except Exception as exc:
        result["ok"] = False
        result["issues"].append(
            {
                "kind": "read_error",
                "message": str(exc),
            }
        )

    return result


def audit_project() -> Dict[str, Any]:
    files = interesting_files()
    results = []

    for path in files:
        if is_excluded(path):
            continue

        if path.suffix.lower() == ".py":
            results.append(audit_python(path))
        elif path.suffix.lower() in [".ps1", ".json", ".txt", ".md"]:
            results.append(audit_text(path))

    bad = [item for item in results if not item.get("ok")]

    return {
        "ok": len(bad) == 0,
        "created_at": now(),
        "version": "v2.20.2-smart-audit-guard-allowlist",
        "project_root": str(PROJECT_ROOT),
        "checked_count": len(results),
        "bad_count": len(bad),
        "bad": bad,
        "results": results,
        "policy": {
            "cpu_ram_only": True,
            "gpu": "untouched",
            "no_ads": True,
            "audit": "smart_allowlist_for_guard_files",
        },
    }


def dust_candidates() -> List[Dict[str, Any]]:
    candidates: List[Dict[str, Any]] = []

    for path in PROJECT_ROOT.rglob("*"):
        if not path.exists():
            continue
        if is_excluded(path):
            continue

        name = path.name.lower()

        if path.is_dir() and name == "__pycache__":
            candidates.append(
                {
                    "path": str(path),
                    "kind": "dir",
                    "reason": "__pycache__",
                }
            )
        elif path.is_file() and path.suffix.lower() in [".pyc", ".pyo"]:
            candidates.append(
                {
                    "path": str(path),
                    "kind": "file",
                    "reason": "compiled_python_cache",
                }
            )
        elif path.is_file() and name.endswith(".tmp"):
            candidates.append(
                {
                    "path": str(path),
                    "kind": "file",
                    "reason": "temporary_file",
                }
            )

    return candidates


def quarantine_dust(apply: bool = False) -> Dict[str, Any]:
    candidates = dust_candidates()
    stamp = time.strftime("%Y%m%d_%H%M%S")
    target_root = QUARANTINE_DIR / f"dust_{stamp}"

    moved = []
    errors = []

    if apply:
        target_root.mkdir(parents=True, exist_ok=True)

    for item in candidates:
        src = Path(item["path"])
        try:
            if apply:
                rel = src.relative_to(PROJECT_ROOT)
                dst = target_root / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(dst))
                item["quarantined_to"] = str(dst)
            moved.append(item)
        except Exception as exc:
            errors.append(
                {
                    "path": str(src),
                    "error": str(exc),
                }
            )

    return {
        "ok": len(errors) == 0,
        "created_at": now(),
        "version": "v2.20.2-smart-audit-guard-allowlist",
        "apply": apply,
        "candidate_count": len(candidates),
        "moved_count": len(moved) if apply else 0,
        "quarantine_root": str(target_root) if apply else None,
        "candidates": candidates,
        "moved": moved if apply else [],
        "errors": errors,
    }


def maintenance_status() -> Dict[str, Any]:
    audit = audit_project()
    dust = dust_candidates()

    return {
        "ok": audit["ok"],
        "created_at": now(),
        "version": "v2.20.2-smart-audit-guard-allowlist",
        "audit_ok": audit["ok"],
        "checked_count": audit["checked_count"],
        "bad_count": audit["bad_count"],
        "dust_candidate_count": len(dust),
        "policy": {
            "cpu_ram_only": True,
            "gpu": "untouched",
            "no_ads": True,
            "cleanup_mode": "quarantine_only",
        },
    }
