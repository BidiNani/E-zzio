"""
E-ZZIO V7.28.6 — Historical Archive Tampering Certification Test
Simule une modification malveillante dans une archive passée (Archive #1)
et vérifie que l'auditeur intercepte la compromission.
"""

import sys
import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.security.ledger_engine import LedgerEngine
from core.security.archive_validator import archive_validator


def run_tamper_test():
    print("============================================================")
    print(" E-ZZIO V7.28.6 — TEST DE FALSIFICATION HISTORIQUE D'ARCHIVE")
    print("============================================================\n")

    ledger_path = ROOT_DIR / "runtime" / "decisions" / "router_decisions.jsonl"
    archive_dir = ROOT_DIR / "runtime" / "decisions" / "archive"
    state_path = ROOT_DIR / "runtime" / "state" / "ledger_chain_state.json"

    # Nettoyage initial
    if ledger_path.exists():
        ledger_path.unlink()
    if state_path.exists():
        state_path.unlink()
    for meta in archive_dir.glob("*.meta.json"):
        meta.unlink()
    for arc in archive_dir.glob("*.jsonl"):
        arc.unlink()

    # Génération des archives via 100 transactions (seuil à 50 -> 2 archives créées)
    engine = LedgerEngine(archive_threshold=50)
    print("[*] Génération de la chaîne d'archives (100 transactions)...")
    for i in range(100):
        engine.commit_transaction(
            intent="tamper_test",
            request_id=f"req-t-{i}",
            candidates=[],
            selected="qwen3:8b",
            state="COMPLETED",
            execution_details={"index": i},
        )

    # Vérification que l'état initial est parfaitement valide
    initial_audit = archive_validator.verify_archive_lineage()
    print(f"  -> Audit initial des archives saines : {initial_audit}")
    assert initial_audit["valid"] is True, "L'audit initial des archives a échoué !"

    # FALSIFICATION RÉTROACTIVE : Modification d'une transaction dans la première archive (Archive #1)
    print("\n[!] SIMULATION D'ATTAQUE : Modification d'une transaction au milieu de l'Archive #1...")
    archive_1_jsonl = archive_dir / "ledger_000001.jsonl"
    assert archive_1_jsonl.exists(), "Archive #1 introuvable !"

    lines = archive_1_jsonl.read_text(encoding="utf-8").strip().splitlines()
    record = json.loads(lines[20])  # Ligne 21 de l'archive 1
    record["selected"] = "modele_corrompu_par_attaquant"
    lines[20] = json.dumps(record, ensure_ascii=False)

    # Réécriture de l'archive #1 falsifiée
    archive_1_jsonl.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("  [OK] Archive #1 altérée de manière silencieuse sur le disque.")

    # Lancement de l'auditeur rétroactif
    print("\n[*] Lancement de l'audit de lignage des archives...")
    audit_res = archive_validator.verify_archive_lineage()
    print(f"  -> Résultat de l'audit post-altération : {audit_res}")

    # Vérification que l'attaque a été interceptée
    assert audit_res["valid"] is False, "L'auditeur n'a pas détecté la falsification historique !"
    assert "ALTÉRATION HISTORIQUE DÉTECTÉE" in audit_res["error"] or "ROOT HASH" in audit_res["error"], (
        f"Erreur inattendue rapportée par l'auditeur : {audit_res.get('error')}"
    )
    print("  [CERT] Compromission de l'Archive historique #1 interceptée avec succès !")
    print(f"  [CERT] Archive incriminée : {audit_res.get('compromised_archive')}")

    print("\n============================================================")
    print(" V7.28.6 CERTIFIÉ : IMMUTABILITÉ RÉTROACTIVE DES ARCHIVES VALIDÉE")
    print("============================================================\n")


if __name__ == "__main__":
    run_tamper_test()
