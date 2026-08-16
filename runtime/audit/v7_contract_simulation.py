import os
import sys
import json
import hashlib
import hmac
import ast
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path("G:/AI/E-zzio").resolve()
REGISTRY_OUT = ROOT_DIR / "runtime" / "audit" / "intelligence_scan" / "V7_REGISTRY"
REGISTRY_OUT.mkdir(parents=True, exist_ok=True)

def simulate_contract_resolution(model_id: str):
    """Simule la recherche et la validation d'un contrat pour un modèle donné."""
    contracts_dir = ROOT_DIR / "runtime" / "hardware" / "trust" / "models" / "contracts"
    simulation_result = {
        "target_model": model_id,
        "discovery": "FAILED",
        "contract_path": None,
        "checks": {}
    }

    if not contracts_dir.exists():
        simulation_result["error"] = "Dossier contracts introuvable"
        return simulation_result

    # Recherche du contrat correspondant
    target_file = contracts_dir / f"{model_id}.contract.json"
    if not target_file.exists():
        # Recherche par pattern
        matches = list(contracts_dir.glob("*.contract.json"))
        if matches:
            target_file = matches[0]  # Utilise le premier disponible pour la simulation
        else:
            return simulation_result

    simulation_result["discovery"] = "SUCCESS"
    simulation_result["contract_path"] = str(target_file.relative_to(ROOT_DIR)).replace("\\", "/")

    try:
        contract_data = json.loads(target_file.read_text(encoding="utf-8"))
        
        # Test 1 : Vérification Trust & Origine
        trust = contract_data.get("trust", {})
        simulation_result["checks"]["trust_status"] = {
            "status": trust.get("status"),
            "origin_verified": trust.get("origin_verified"),
            "passed": trust.get("status") == "TRUSTED" and trust.get("origin_verified") is True
        }

        # Test 2 : Vérification Ressources (Simulation d'une machine avec 16GB RAM / 8 workers)
        resources = contract_data.get("resources", {})
        max_ram = resources.get("max_ram_mb", 8192)
        max_workers = resources.get("max_allowed_workers", 8)
        
        simulated_machine_ram = 16384 # 16 GB dispo
        simulated_machine_workers = 8

        simulation_result["checks"]["resource_constraints"] = {
            "contract_max_ram_mb": max_ram,
            "contract_max_workers": max_workers,
            "ram_passed": simulated_machine_ram >= max_ram,
            "workers_passed": simulated_machine_workers <= max_workers,
            "passed": (simulated_machine_ram >= max_ram) and (simulated_machine_workers <= max_workers)
        }

        # Test 3 : Présence et structure de la signature
        signature = contract_data.get("signature")
        simulation_result["checks"]["signature_integrity"] = {
            "signature_present": bool(signature),
            "signature_length": len(signature) if signature else 0,
            "passed": bool(signature)
        }

        # Bilan global de la simulation
        all_passed = all(chk.get("passed", False) for chk in simulation_result["checks"].values())
        simulation_result["overall_simulation_status"] = "ALLOW" if all_passed else "DENY"

    except Exception as e:
        simulation_result["error"] = str(e)
        simulation_result["overall_simulation_status"] = "ERROR"

    return simulation_result

def search_hmac_implementation():
    """Recherche les modules qui manipulent HMAC ou clés secrètes pour la validation."""
    hmac_modules = []
    for py_file in ROOT_DIR.rglob("*.py"):
        if any(ex in py_file.parts for ex in {".git", "__pycache__", "venv", "node_modules", "runtime/audit"}):
            continue
        try:
            content = py_file.read_text(encoding="utf-8", errors="replace")
            if "hmac" in content.lower() or "secret" in content.lower():
                rel = str(py_file.relative_to(ROOT_DIR)).replace("\\", "/")
                hmac_modules.append(rel)
        except Exception:
            pass
    return hmac_modules

def run_simulation():
    print("[*] Lancement de la simulation d'autorité contractuelle V7.5...")
    
    sim_result = simulate_contract_resolution("qwen2.5-7b")
    hmac_sources = search_hmac_implementation()

    payload = {
        "simulation_timestamp": datetime.now().isoformat(),
        "contract_simulation": sim_result,
        "hmac_potential_verifiers": hmac_sources
    }

    # Sauvegarde JSON
    out_json = REGISTRY_OUT / "contract_simulation_result.json"
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    # Génération du rapport Markdown
    build_simulation_markdown(sim_result, hmac_sources)
    print(f"[OK] Simulation V7.5 terminée. Rapport généré dans {REGISTRY_OUT}")

def build_simulation_markdown(sim: dict, hmac_sources: list):
    md_path = REGISTRY_OUT / "V7_CONTRACT_AUTHORITY_SIMULATION.md"
    
    lines = [
        "# E-ZZIO V7.5 — Rapport de Simulation de l'Autorité Contractuelle",
        f"**Date :** {datetime.now().isoformat()}",
        "",
        "## 1. Résultat de la Simulation de Résolution",
        f"- **Modèle testé :** `{sim.get('target_model')}`",
        f"- **Découverte du contrat :** `{sim.get('discovery')}`",
        f"- **Chemin du contrat :** `{sim.get('contract_path')}`",
        f"- **Statut global simulé :** `{sim.get('overall_simulation_status')}`",
        "",
        "## 2. Détail des Contrôles",
    ]

    checks = sim.get("checks", {})
    for check_name, check_data in checks.items():
        lines.append(f"### Contrôle : `{check_name}`")
        for k, v in check_data.items():
            lines.append(f"  - {k} : `{v}`")

    lines.extend([
        "",
        "## 3. Recherche des Implémentations HMAC / Secret dans le Dépôt",
        f"**Nombre de fichiers mentionnant HMAC ou Secret :** {len(hmac_sources)}",
        ""
    ])
    for s in hmac_sources[:10]:
        lines.append(f"- `{s}`")

    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] Rapport Markdown de simulation généré : {md_path}")

if __name__ == "__main__":
    run_simulation()
