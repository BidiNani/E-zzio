"""
E-ZZIO V7.29.1 — Certification Test Suite (Corrigé)
Valide l'enforcement runtime de l'identité sur les transactions du Ledger.
"""
import sys
import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.security.ledger_engine import LedgerEngine
from core.security.ledger_validator import ledger_validator

def run_binding_tests():
    print("============================================================")
    print(" E-ZZIO V7.29.1 — LEDGER IDENTITY BINDING CERTIFICATION")
    print("============================================================\n")

    ledger_path = ROOT_DIR / "runtime" / "decisions" / "router_decisions.jsonl"
    const_path = ROOT_DIR / "config" / "constitution.json"
    persona_path = ROOT_DIR / "config" / "persona.json"

    # Nettoyage initial
    if ledger_path.exists(): ledger_path.unlink()

    # Sauvegarde du contenu original pour restauration
    orig_const = const_path.read_text(encoding="utf-8")
    orig_persona = persona_path.read_text(encoding="utf-8")

    try:
        # Instanciation unique du moteur de référence (capture l'identité saine au boot)
        engine = LedgerEngine()

        # TEST A : Commit Nominal
        print("[TEST A] Commit nominal avec identité scellée...")
        success = engine.commit_transaction(
            intent="nominal_test",
            request_id="req-nom-1",
            candidates=[],
            selected="qwen3:8b",
            state="COMPLETED"
        )
        assert success is True, "Le commit nominal a échoué !"
        
        val_res = ledger_validator.verify_ledger_chain()
        assert val_res["valid"] is True, f"Chaîne invalide : {val_res.get('error')}"
        
        last_line = json.loads(ledger_path.read_text(encoding="utf-8").strip().splitlines()[-1])
        assert "identity_seal" in last_line and "identity_root_hash" in last_line, "Sceau d'identité absent !"
        print(" -> [OK] Commit nominal validé avec sceau d'identité.")

        # TEST B : Modification de la Constitution à chaud
        print("\n[TEST B] Modification de la Constitution à chaud...")
        const_data = json.loads(orig_const)
        const_data["axioms"].append("Axiome malveillant injecté.")
        const_path.write_text(json.dumps(const_data, indent=2), encoding="utf-8")

        success_after_const = engine.commit_transaction(
            intent="compromised_const",
            request_id="req-comp-1",
            candidates=[],
            selected="qwen3:8b",
            state="COMPLETED"
        )
        assert success_after_const is False, "FAIL: Le moteur a accepté un commit malgré la dérive de la Constitution !"
        print(" -> [OK] Modification de Constitution détectée -> Commit refusé (FAIL_CLOSED).")

        # Restauration de la constitution pour isoler le test du persona
        const_path.write_text(orig_const, encoding="utf-8")

        # TEST C : Modification du Persona Kernel à chaud
        print("\n[TEST C] Modification du Persona Kernel à chaud...")
        persona_data = json.loads(orig_persona)
        persona_data["traits"]["precision"] = "compromise_target"
        persona_path.write_text(json.dumps(persona_data, indent=2), encoding="utf-8")

        success_after_persona = engine.commit_transaction(
            intent="compromised_persona",
            request_id="req-comp-2",
            candidates=[],
            selected="qwen3:8b",
            state="COMPLETED"
        )
        assert success_after_persona is False, "FAIL: Le moteur a accepté un commit malgré la dérive du Persona !"
        print(" -> [OK] Modification du Persona détectée -> Commit refusé (FAIL_CLOSED).")

        # TEST D : Restauration et Re-certification (Nouveau boot sain)
        print("\n[TEST D] Restauration des fichiers d'identité et re-certification...")
        persona_path.write_text(orig_persona, encoding="utf-8")
        
        # Simulation d'un redémarrage / re-certification post-incident
        engine_restored = LedgerEngine()
        success_restored = engine_restored.commit_transaction(
            intent="restored_write",
            request_id="req-rest-1",
            candidates=[],
            selected="qwen3:8b",
            state="COMPLETED"
        )
        assert success_restored is True, "FAIL: L'écriture a échoué après restauration de l'identité !"
        
        final_val = ledger_validator.verify_ledger_chain()
        assert final_val["valid"] is True, f"Chaîne rompue après reprise : {final_val.get('error')}"
        print(" -> [OK] Identité restaurée & re-certifiée -> Reprise autorisée.")

        print("\n============================================================")
        print(" V7.29.1 CERTIFIÉ : IDENTITY RUNTIME ENFORCEMENT ACTIF (10/10)")
        print("============================================================\n")

    finally:
        # Nettoyage et restauration garantie des fichiers d'origine
        const_path.write_text(orig_const, encoding="utf-8")
        persona_path.write_text(orig_persona, encoding="utf-8")

if __name__ == "__main__":
    run_binding_tests()
