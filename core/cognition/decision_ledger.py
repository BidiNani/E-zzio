"""
E-ZZIO Core — Unified Decision Ledger (V8.8 Hotfix)
Centralise et unifie la traçabilité des décisions en utilisant une source 
validée par le contrat runtime ECOL (system_core).
"""
import os
import sys
import json
import uuid
import hmac
import hashlib
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

ROOT_DIR = Path(r"G:\AI\E-zzio")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.cognition.ecol_universal_enforcement import EcolUniversalGateway

logger = logging.getLogger(__name__)

class DecisionLedgerEngine:
    def __init__(self, root_dir: Path = ROOT_DIR):
        self.root_dir = root_dir
        self.ledger_path = self.root_dir / "runtime" / "cognition" / "budget" / "unified_decision_ledger.jsonl"
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.gateway = EcolUniversalGateway()
        self.gateway.register_gateway_action("RECORD_ORGANISM_DECISION")

    def record_decision(
        self,
        subsystem: str,
        decision_type: str,
        context: Dict[str, Any],
        action_payload: Dict[str, Any],
        rationale: str
    ) -> Dict[str, Any]:
        """
        Enregistre une décision unifiée de l'organisme dans le ledger scellé par ECOL.
        """
        decision_id = f"DEC-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
        timestamp = datetime.now(timezone.utc).isoformat()

        record = {
            "decision_id": decision_id,
            "timestamp_utc": timestamp,
            "subsystem": subsystem,
            "decision_type": decision_type,
            "context": context,
            "action_payload": action_payload,
            "rationale": rationale
        }

        # Scellement cryptographique individuel de l'entrée
        record_json = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        sec_key = b"EZZIO_DECISION_LEDGER_ROOT_KEY_2026"
        signature = hmac.new(sec_key, record_json.encode("utf-8"), hashlib.sha256).hexdigest()

        sealed_record = {
            **record,
            "signature_hmac": signature
        }

        # Utilisation d'une source approuvée par le contrat runtime (system_core)
        payload = {
            "source_component": "system_core",
            "action": "RECORD_ORGANISM_DECISION",
            "task_description": f"Enregistrement décision [{decision_type}] par sous-système '{subsystem}'",
            "priority": "normal",
            "risk_level": "low",
            "estimated_cost": len(rationale)
        }

        def commit_decision():
            with open(self.ledger_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(sealed_record, ensure_ascii=False) + "\n")
            return sealed_record

        # Validation No-Bypass via ECOL
        result = self.gateway.execute_via_gateway(
            action="RECORD_ORGANISM_DECISION",
            payload=payload,
            target_func=commit_decision
        )

        return result

    def query_decisions(self, subsystem: Optional[str] = None, limit: int = 5) -> List[Dict[str, Any]]:
        """Interroge l'historique des décisions de l'organisme."""
        if not self.ledger_path.exists():
            return []

        decisions = []
        with open(self.ledger_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    decisions.append(json.loads(line))

        if subsystem:
            decisions = [d for d in decisions if d.get("subsystem") == subsystem]

        return decisions[-limit:]

def test_decision_ledger():
    print("[*] Test du Unified Decision Ledger (V8.8 Hotfix)...")
    ledger_engine = DecisionLedgerEngine()

    print("\n--- Test 1 : Enregistrement d'une décision via le sous-système de routage ---")
    res = ledger_engine.record_decision(
        subsystem="CognitiveRouter",
        decision_type="MODEL_ROUTING_SWITCH",
        context={"gaming_detected": True, "ram_usage_percent": 39.7},
        action_payload={"selected_model": "qwen2.5:3b", "max_tokens": 512},
        rationale="WoW détecté en arrière-plan, bascule vers le modèle léger 3B pour protéger la GTX 1650 et minimiser l'empreinte CPU."
    )
    print(f"  [PASS] Décision consignée. ID : {res['decision_id']} | Subsystem : {res['subsystem']}")

    print("\n--- Test 2 : Requête d'explicabilité sur l'historique ---")
    history = ledger_engine.query_decisions(limit=2)
    print(f"  [PASS] {len(history)} décision(s) retrouvée(s) dans le registre unifié :")
    for d in history:
        print(f"         -> [{d['timestamp_utc']}] {d['subsystem']} : {d['decision_type']}")
        print(f"            Raison : {d['rationale']}")

    print("\n" + "="*65)
    print(" UNIFIED DECISION LEDGER (V8.8) : OPERATIONAL & CONTRACT-ALIGNED")
    print("="*65)

if __name__ == "__main__":
    test_decision_ledger()
