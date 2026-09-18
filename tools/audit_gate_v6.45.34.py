from __future__ import annotations

import ast
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_DIRS = {"audit", "snapshot", "snapshots", "backup", "backups", "old", "archive", ".venv", "venv", "__pycache__", ".pytest_cache", ".git", "tests"}

IDENTITY_KEYWORDS = {"forge", "vault", "identity", "constitution", "organism_identity", "genesis", "soul"}

class IdentityAndKernelVisitor(ast.NodeVisitor):
    def __init__(self, rel_path: str):
        self.rel_path = rel_path
        self.kernel_inits: list[dict[str, Any]] = []
        self.interface_inits: list[dict[str, Any]] = []
        self.identity_references: list[dict[str, Any]] = []

    def visit_ClassDef(self, node: ast.ClassDef):
        if node.name in {"OrganismKernel", "EzzioInterface"}:
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)) and sub.name == "__init__":
                    inits = []
                    for child in ast.walk(sub):
                        if isinstance(child, ast.Call):
                            inits.append(ast.unparse(child))

                    target_list = self.kernel_inits if node.name == "OrganismKernel" else self.interface_inits
                    target_list.append({
                        "file": self.rel_path,
                        "class": node.name,
                        "line": sub.lineno,
                        "calls_inside": inits
                    })
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        mod = (node.module or "").lower()
        if any(kw in mod for kw in IDENTITY_KEYWORDS):
            for alias in node.names:
                self.identity_references.append({
                    "file": self.rel_path,
                    "type": "IMPORT_FROM",
                    "source": f"{node.module}.{alias.name}",
                    "line": node.lineno
                })
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        call_str = ast.unparse(node.func).lower()
        if any(kw in call_str for kw in IDENTITY_KEYWORDS):
            self.identity_references.append({
                "file": self.rel_path,
                "type": "IDENTITY_CALL",
                "source": ast.unparse(node),
                "line": node.lineno
            })
        self.generic_visit(node)

def main():
    print("=" * 80)
    print(" GATE v6.45.34 — KERNEL, INTERFACE & IDENTITY PROVENANCE TRACE")
    print("=" * 80)
    print(f"[RACINE] {PROJECT_ROOT}\n")

    py_files = [p for p in PROJECT_ROOT.glob("**/*.py") if not (set(p.parts) & EXCLUDED_DIRS)]

    all_kernels = []
    all_interfaces = []
    all_identities = []

    for path in py_files:
        rel_path = str(path.relative_to(PROJECT_ROOT))
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(content, filename=rel_path)
            visitor = IdentityAndKernelVisitor(rel_path)
            visitor.visit(tree)
            all_kernels.extend(visitor.kernel_inits)
            all_interfaces.extend(visitor.interface_inits)
            all_identities.extend(visitor.identity_references)
        except Exception as e:
            print(f"[WARN] Erreur parsing {rel_path} : {e}", file=sys.stderr)

    print(f"[1] CONSTRUCTEURS ORGANISM KERNEL ({len(all_kernels)} trouvés)")
    for k in all_kernels:
        print(f"  • {k['file']}:ligne {k['line']} -> class {k['class']}")
        for c in k['calls_inside'][:5]:
            print(f"    - Interne : {c}")

    print(f"\n[2] CONSTRUCTEURS EZZIO INTERFACE ({len(all_interfaces)} trouvés)")
    for i in all_interfaces:
        print(f"  • {i['file']}:ligne {i['line']} -> class {i['class']}")
        for c in i['calls_inside'][:5]:
            print(f"    - Interne : {c}")

    print(f"\n[3] RÉFÉRENCES IDENTITÉ / FORGE / VAULT ({len(all_identities)} trouvées)")
    for id_ref in all_identities[:15]:
        print(f"  • [{id_ref['file']}:{id_ref['line']}] ({id_ref['type']}) -> {id_ref['source']}")

    out_file = PROJECT_ROOT / "tools" / "gate_v6_45_34_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({"kernels": all_kernels, "interfaces": all_interfaces, "identities": all_identities}, f, indent=2)
    print(f"\n[+] Rapport JSON exporté : {out_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()
