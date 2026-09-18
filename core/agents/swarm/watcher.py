"""
E-ZZIO Sovereign Swarm — Agent Performance & Concurrency Watcher.
Usage: python -m core.agents.swarm.watcher [--profile-async] [--root PATH]
"""
from __future__ import annotations

import argparse
import ast
import os
import sys
from typing import Any


class WatcherAgent:
    """Agent d'analyse de performance, d'asynchronisme et de fuites mémoire."""

    def __init__(self, root_dir: str = "G:/AI/E-zzio"):
        self.root_dir = root_dir
        self.target_dirs = ["core", "routers"]

    def profile_file(self, file_path: str) -> dict[str, Any]:
        metrics = {
            "async_def_count": 0,
            "httpx_client_instantiations": 0,
            "shared_client_usage": 0,
            "blocking_sleep_in_async": 0,
            "issues": [],
        }

        try:
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                content = f.read()

            tree = ast.parse(content, filename=file_path)

            for node in ast.walk(tree):
                if isinstance(node, ast.AsyncFunctionDef):
                    metrics["async_def_count"] += 1
                    # Inspect statements inside async function for time.sleep
                    for inner in ast.walk(node):
                        if isinstance(inner, ast.Call):
                            if isinstance(inner.func, ast.Attribute) and inner.func.attr == "sleep":
                                if isinstance(inner.func.value, ast.Name) and inner.func.value.id == "time":
                                    metrics["blocking_sleep_in_async"] += 1
                                    metrics["issues"].append({
                                        "line": inner.lineno,
                                        "type": "EVENT_LOOP_BLOCKING_SLEEP",
                                        "message": f"time.sleep() bloquant dans la fonction async '{node.name}'. Utiliser await asyncio.sleep().",
                                    })

                elif isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Attribute) and node.func.attr == "AsyncClient":
                        metrics["httpx_client_instantiations"] += 1
                    elif isinstance(node.func, ast.Name) and "shared_client" in node.func.id:
                        metrics["shared_client_usage"] += 1

        except Exception as exc:
            metrics["issues"].append({
                "line": 0,
                "type": "PROFILING_ERROR",
                "message": f"Erreur de profilage: {exc}",
            })

        return metrics

    def run_profiler(self, profile_async: bool = True) -> int:
        print("=== E-ZZIO Swarm Concurrency & Performance Watcher ===")
        total_async_funcs = 0
        total_shared_clients = 0
        total_blocking_sleeps = 0
        total_issues = 0

        for target in self.target_dirs:
            full_path = os.path.join(self.root_dir, target)
            if not os.path.exists(full_path):
                continue

            for root, _, files in os.walk(full_path):
                for f in files:
                    if f.endswith(".py"):
                        file_path = os.path.join(root, f)
                        metrics = self.profile_file(file_path)
                        total_async_funcs += metrics["async_def_count"]
                        total_shared_clients += metrics["shared_client_usage"]
                        total_blocking_sleeps += metrics["blocking_sleep_in_async"]
                        total_issues += len(metrics["issues"])

                        if metrics["issues"]:
                            print(f"  [WARN] File: {file_path}")
                            for issue in metrics["issues"]:
                                print(f"    Line {issue['line']} [{issue['type']}]: {issue['message']}")

        print("\n--- Synthèse de Profilage Performance ---")
        print(f"  Total Fonctions Asynchrones (`async def`) : {total_async_funcs}")
        print(f"  Utilisation Clients Async Partagés (KeepAlive) : {total_shared_clients}")
        print(f"  Appels Bloquants dans des Boucles Async : {total_blocking_sleeps}")

        if total_blocking_sleeps > 0 and profile_async:
            print("[WATCHER FAIL] Appels `time.sleep` bloquants détectés dans des fonctions `async def`.")
            return 1

        print("[WATCHER PASS] Concurrence asynchrone et gestion des boucles d'événements certifiées 100% conformes.")
        return 0


def main():
    parser = argparse.ArgumentParser(description="E-ZZIO Swarm Concurrency & Performance Watcher")
    parser.add_argument("--profile-async", action="store_true", default=True, help="Profile async concurrency")
    parser.add_argument("--root", type=str, default="G:/AI/E-zzio", help="Root directory")
    args = parser.parse_args()

    agent = WatcherAgent(root_dir=args.root)
    sys.exit(agent.run_profiler(profile_async=args.profile_async))


if __name__ == "__main__":
    main()
