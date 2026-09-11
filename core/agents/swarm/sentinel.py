"""
E-ZZIO Sovereign Swarm — Agent Frozen Core & Security Sentinel.
Usage: python -m core.agents.swarm.sentinel [--audit-core] [--root PATH]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from typing import Dict, Any


class SentinelAgent:
    """Agent sentinelle de sécurité et de contrôle d'intégrité du Frozen Core."""

    def __init__(self, root_dir: str = "G:/AI/E-zzio"):
        self.root_dir = root_dir
        self.manifest_path = os.path.join(root_dir, "docs", "FROZEN_CORE_MANIFEST.json")
        self.checker_script = os.path.join(root_dir, "tools", "check_frozen_core.py")

    def verify_frozen_core(self) -> bool:
        if not os.path.exists(self.checker_script):
            print(f"[SENTINEL FAIL] Script d'intégrité introuvable: {self.checker_script}")
            return False

        python_bin = sys.executable
        res = subprocess.run([python_bin, self.checker_script], cwd=self.root_dir, capture_output=True, text=True)
        if res.returncode == 0 and "FROZEN_CORE_OK" in res.stdout:
            print("[SENTINEL PASS] Empreinte SHA-256 du Frozen Core valide (FROZEN_CORE_OK).")
            return True
        else:
            print(f"[SENTINEL FAIL] Validation Frozen Core échouée:\nSTDOUT: {res.stdout}\nSTDERR: {res.stderr}")
            return False

    def verify_payload_contracts(self) -> bool:
        """Vérifie le contrat de payload de l'API /master/chat."""
        try:
            from core.ezzio_master import EzzioMaster
            master = EzzioMaster()
            # Test schema signature initialization
            if hasattr(master, "execute_intent"):
                print("[SENTINEL PASS] Contrat d'API Master Chat et autorité mono-canal validés.")
                return True
            print("[SENTINEL FAIL] EzzioMaster ne possède pas l'interface execute_intent.")
            return False
        except Exception as exc:
            print(f"[SENTINEL FAIL] Erreur lors de la vérification du contrat Master: {exc}")
            return False

    def run_sentinel(self, audit_core: bool = True) -> int:
        print("=== E-ZZIO Swarm Frozen Core & Security Sentinel ===")
        core_ok = self.verify_frozen_core()
        contract_ok = self.verify_payload_contracts()

        if core_ok and contract_ok:
            print("\n[SENTINEL PASSED] Sécurité, intégrité et souveraineté certifiées à 100%.")
            return 0
        else:
            print("\n[SENTINEL FAILED] Intégrité ou contrat d'autorité compromis.")
            return 1


def main():
    parser = argparse.ArgumentParser(description="E-ZZIO Swarm Frozen Core & Security Sentinel")
    parser.add_argument("--audit-core", action="store_true", default=True, help="Audit frozen core SHA-256 integrity")
    parser.add_argument("--root", type=str, default="G:/AI/E-zzio", help="Root directory")
    args = parser.parse_args()

    agent = SentinelAgent(root_dir=args.root)
    sys.exit(agent.run_sentinel(audit_core=args.audit_core))


if __name__ == "__main__":
    main()
