"""
E-ZZIO Sovereign Swarm — Agent Linter & Code Inspector.
Usage: python -m core.agents.swarm.inspector [--strict] [--path PATH]
"""
from __future__ import annotations

import ast
import argparse
import os
import sys
from typing import List, Dict, Any


class InspectorAgent:
    """Agent d'inspection statique et d'audit de qualité de code."""

    def __init__(self, root_dir: str = "G:/AI/E-zzio"):
        self.root_dir = root_dir
        self.target_dirs = ["core", "routers"]

    def inspect_file(self, file_path: str) -> Dict[str, Any]:
        issues = []
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            tree = ast.parse(content, filename=file_path)

            for node in ast.walk(tree):
                # Detection forbidden import requests
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name == "requests" or alias.name.startswith("requests."):
                            issues.append({
                                "line": node.lineno,
                                "type": "FORBIDDEN_IMPORT",
                                "message": "Import bloquant 'requests' interdit. Utiliser 'httpx' asynchrone.",
                            })
                elif isinstance(node, ast.ImportFrom):
                    if node.module == "requests" or (node.module and node.module.startswith("requests.")):
                        issues.append({
                            "line": node.lineno,
                            "type": "FORBIDDEN_IMPORT",
                            "message": "Import bloquant 'requests' interdit. Utiliser 'httpx' asynchrone.",
                        })

        except SyntaxError as e:
            issues.append({
                "line": e.lineno or 0,
                "type": "SYNTAX_ERROR",
                "message": f"Erreur de syntaxe Python: {e.msg}",
            })
        except Exception as exc:
            issues.append({
                "line": 0,
                "type": "INSPECTION_ERROR",
                "message": f"Erreur d me lecture/analyse: {exc}",
            })

        return {
            "file": file_path,
            "issues": issues,
        }

    def run_audit(self, strict: bool = True) -> int:
        print("=== E-ZZIO Swarm Inspector Agent ===")
        total_files = 0
        total_issues = 0
        report = []

        for target in self.target_dirs:
            full_path = os.path.join(self.root_dir, target)
            if not os.path.exists(full_path):
                continue

            for root, _, files in os.walk(full_path):
                for f in files:
                    if f.endswith(".py"):
                        file_path = os.path.join(root, f)
                        res = self.inspect_file(file_path)
                        total_files += 1
                        if res["issues"]:
                            total_issues += len(res["issues"])
                            report.append(res)

        print(f"Fichiers analysés: {total_files}")
        if total_issues == 0:
            print("[INSPECTOR PASS] Aucune anomalie ni import bloquant (requests) détecté.")
            return 0
        else:
            print(f"[INSPECTOR WARNING/FAIL] {total_issues} anomalie(s) trouvée(s) dans {len(report)} fichier(s):")
            for r in report:
                print(f"  File: {r['file']}")
                for issue in r["issues"]:
                    print(f"    Line {issue['line']} [{issue['type']}]: {issue['message']}")

            if strict:
                return 1
            return 0


def main():
    parser = argparse.ArgumentParser(description="E-ZZIO Swarm Inspector Agent")
    parser.add_argument("--strict", action="store_true", default=True, help="Fail closed on issues")
    parser.add_argument("--root", type=str, default="G:/AI/E-zzio", help="Root directory")
    args = parser.parse_args()

    agent = InspectorAgent(root_dir=args.root)
    sys.exit(agent.run_audit(strict=args.strict))


if __name__ == "__main__":
    main()
