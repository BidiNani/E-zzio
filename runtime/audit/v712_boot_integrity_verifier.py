import os
import sys
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone

ROOT_DIR = Path("G:/AI/E-zzio").resolve()
REGISTRY_OUT = ROOT_DIR / "runtime" / "audit" / "intelligence_scan" / "V7_REGISTRY"
V712_REGISTRY = REGISTRY_OUT / "V712"
MANIFEST_PATH = V712_REGISTRY / "governance_freeze_manifest.json"

def run_physical_attestation():
    print("[*] -----------------------------------------------------------------")
    print("[*] E-ZZIO V7.12.8 — Attestation Physique & Intégrité au Boot...")
    print("[*] -----------------------------------------------------------------")

    if not MANIFEST_PATH.exists():
        print("[!] ERREUR CRITIQUE : Manifeste de gel de gouvernance introuvable.")
        sys.exit(1)

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    sealed_artifacts = manifest.get("sealed_artifacts", {})

    violations = []
    attestation_results = []
    checked_count = 0

    for key, meta in sealed_artifacts.items():
        rel_path = meta["path"]
        expected_hash = meta["sha256"]
        expected_size = meta["size_bytes"]
        target_path = ROOT_DIR / rel_path

        checked_count += 1
        artifact_report = {
            "key": key,
            "path": rel_path,
            "exists": False,
            "size_match": False,
            "sha256_match": False,
            "status": "FAILED"
        }

        # 1. Vérification de la présence physique
        if not target_path.exists():
            violations.append(f"ARTIFACT_MISSING: {key} ({rel_path}) est introuvable sur le disque.")
            attestation_results.append(artifact_report)
            continue
        
        artifact_report["exists"] = True

        # 2. Lecture et vérification de la taille exacte
        try:
            current_bytes = target_path.read_bytes()
            current_size = len(current_bytes)
        except Exception as e:
            violations.append(f"READ_ERROR: Impossible de lire {rel_path}: {str(e)}")
            attestation_results.append(artifact_report)
            continue

        if current_size != expected_size:
            violations.append(f"SIZE_MISMATCH: {key} ({rel_path}) taille incorrecte ! (Attendu: {expected_size} bytes, Obtenu: {current_size} bytes)")
            attestation_results.append(artifact_report)
            continue

        artifact_report["size_match"] = True

        # 3. Vérification du hash cryptographique SHA-256
        hasher = hashlib.sha256()
        hasher.update(current_bytes)
        current_hash = hasher.hexdigest().lower()

        if current_hash != expected_hash:
            violations.append(f"HASH_MISMATCH: {key} ({rel_path}) empreinte altérée ! (Attendu: {expected_hash[:16]}..., Obtenu: {current_hash[:16]}...)")
            attestation_results.append(artifact_report)
            continue

        artifact_report["sha256_match"] = True
        artifact_report["status"] = "SEALED_TRUSTED"
        attestation_results.append(artifact_report)
        print(f"  [VERIFIED] Artefact '{key}' -> Attestation physique et cryptographique OK ({current_size} bytes).")

    boot_status = "BOOT_AUTHORIZED_SECURE" if not violations else "BOOT_BLOCKED_PHYSICAL_ATTESTATION_FAILURE"

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "boot_status": boot_status,
        "attestation_engine": "V7.12.8-STRICT",
        "artifacts_checked": checked_count,
        "attestation_details": attestation_results,
        "violations": violations
    }

    report_json = V712_REGISTRY / "physical_attestation_verification_report.json"
    report_json.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    build_markdown_report(report, V712_REGISTRY / "V712_PHYSICAL_ATTESTATION_REPORT.md")
    
    print(f"\n[*] -----------------------------------------------------------------")
    print(f"[*] STATUT DU BOOT E-ZZIO (V7.12.8) : {boot_status}")
    print(f"[*] -----------------------------------------------------------------")

    if violations:
        print("[!] ALERTE DE SÉCURITÉ : Le système refuse de démarrer en raison de ruptures d'attestation physique.")
        for v in violations:
            print(f"    - {v}")
        sys.exit(2)
    else:
        print("[OK] Attestation physique validée. Le socle est intransigeant et souverain.")

def build_markdown_report(report: dict, md_path: Path):
    lines = [
        "# E-ZZIO V7.12.8 — Physical Artifact Attestation Report",
        f"**Date :** {report['timestamp']}",
        f"**Statut du Boot :** `{report['boot_status']}`",
        f"**Moteur d'attestation :** `{report['attestation_engine']}`",
        f"**Artéfacts audités :** `{report['artifacts_checked']}`",
        "",
        "## 1. Matrice d'Attestation Physique & Cryptographique",
        "| Clé Artefact | Chemin Relatif | Présence | Taille Conforme | Hash Conforme | Statut |",
        "| :--- | :--- | :---: | :---: | :---: | :---: |"
    ]

    for item in report["attestation_details"]:
        ex_icon = "🟢" if item["exists"] else "🔴"
        sz_icon = "🟢" if item["size_match"] else "🔴"
        hs_icon = "🟢" if item["sha256_match"] else "🔴"
        lines.append(f"| `{item['key']}` | `{item['path']}` | {ex_icon} | {sz_icon} | {hs_icon} | `{item['status']}` |")

    lines.extend([
        "",
        "## 2. Synthèse des Violations"
    ])

    if not report["violations"]:
        lines.append("🟢 **SUCCÈS ABSOLU : Tous les artéfacts scellés existent physiquement, possèdent la taille exacte attendue et leurs empreintes SHA-256 correspondent à 100%.**")
    else:
        lines.append("🔴 **ÉCHEC DE L'ATTESTATION PHYSIQUE :**")
        for v in report["violations"]:
            lines.append(f"- `❌ {v}`")

    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] Rapport Markdown d'attestation généré : {md_path.name}")

if __name__ == "__main__":
    run_physical_attestation()
