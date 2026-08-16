import ast
import subprocess
from pathlib import Path

root = Path(r"G:\AI\E-zzio")

deleted = subprocess.run(
    ["git", "diff", "--name-only", "--diff-filter=D"],
    cwd=root,
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    check=True,
).stdout.splitlines()

deleted_modules = {}

for raw_path in deleted:
    path = Path(raw_path)

    if path.suffix != ".py" or path.name == "__init__.py":
        continue

    deleted_modules[".".join(path.with_suffix("").parts)] = raw_path

source_roots = ["core", "routers", "interfaces", "runtime", "providers", "tools"]
excluded_parts = {".venv", "venv", "__pycache__", "site-packages"}

findings = []

for source_root in source_roots:
    base = root / source_root
    if not base.exists():
        continue

    for source in base.rglob("*.py"):
        if any(part in excluded_parts for part in source.parts):
            continue

        try:
            tree = ast.parse(
                source.read_text(encoding="utf-8", errors="replace")
            )
        except SyntaxError as exc:
            findings.append({
                "kind": "syntax_error",
                "source": str(source.relative_to(root)).replace("\\", "/"),
                "target": "",
                "line": exc.lineno or 0,
                "detail": exc.msg,
            })
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in deleted_modules:
                        findings.append({
                            "kind": "direct_import_deleted",
                            "source": str(source.relative_to(root)).replace("\\", "/"),
                            "target": deleted_modules[alias.name],
                            "line": node.lineno,
                            "detail": f"import {alias.name}",
                        })

            elif isinstance(node, ast.ImportFrom) and node.module:
                if node.module in deleted_modules:
                    findings.append({
                        "kind": "from_import_deleted_module",
                        "source": str(source.relative_to(root)).replace("\\", "/"),
                        "target": deleted_modules[node.module],
                        "line": node.lineno,
                        "detail": f"from {node.module} import ...",
                    })

                for alias in node.names:
                    full_name = f"{node.module}.{alias.name}"
                    if full_name in deleted_modules:
                        findings.append({
                            "kind": "from_import_deleted_symbol_module",
                            "source": str(source.relative_to(root)).replace("\\", "/"),
                            "target": deleted_modules[full_name],
                            "line": node.lineno,
                            "detail": f"from {node.module} import {alias.name}",
                        })

report = root / "runtime" / "audit" / "active_import_breakage_audit.md"
report.parent.mkdir(parents=True, exist_ok=True)

lines = [
    "# Audit des imports actifs vers modules supprimés",
    "",
    "Analyse AST des imports statiques.",
    "Exclusions : .venv, venv, __pycache__, site-packages.",
    "",
    f"Modules supprimés analysés : {len(deleted_modules)}",
    f"Références actives trouvées : {len(findings)}",
    "",
]

if not findings:
    lines.append("## Aucun import actif vers un module supprimé trouvé.")
else:
    lines.append("## Références à examiner")
    lines.append("")
    for item in findings:
        lines.append(
            f"- **{item['kind']}** — "
            f"`{item['source']}:{item['line']}` → `{item['target']}`  "
        )
        lines.append(f"  `{item['detail']}`")

report.write_text("\n".join(lines), encoding="utf-8")

for item in findings:
    print(
        f"{item['kind']}: "
        f"{item['source']}:{item['line']} -> {item['target']}"
    )

print(f"Rapport : {report}")
print(f"Références actives trouvées : {len(findings)}")
