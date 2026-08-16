from __future__ import annotations
import hashlib
import json
import threading
from pathlib import Path
from datetime import datetime
from typing import Any, Dict

class ExecutionLedger:
    """Registre append-only vérifiable des exécutions et décisions du Runtime."""
    
    def __init__(self, log_dir: Path = Path("runtime/ledger/logs")):
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.ledger_file = self.log_dir / "execution_chain.log"
        self._lock = threading.RLock()
        self._last_hash = self._compute_initial_hash()

    def _compute_initial_hash(self) -> str:
        if not self.ledger_file.exists() or self.ledger_file.stat().st_size == 0:
            return "GENESIS_BLOCK_HASH"
        try:
            lines = self.ledger_file.read_text(encoding="utf-8").splitlines()
            if lines:
                last_entry = json.loads(lines[-1])
                return last_entry.get("hash", "GENESIS_BLOCK_HASH")
        except Exception:
            pass
        return "GENESIS_BLOCK_HASH"

    def record(self, execution_id: str, actor: str, capability: str, policy_decision: str, budget: Dict[str, Any], result: str) -> str:
        with self._lock:
            timestamp = datetime.now().isoformat()
            record_data = {
                "execution_id": execution_id,
                "timestamp": timestamp,
                "actor": actor,
                "capability": capability,
                "policy_decision": policy_decision,
                "resource_budget": budget,
                "result": result,
                "previous_hash": self._last_hash
            }
            
            # Copie temporaire sans le hash pour calcul déterministe
            calc_data = record_data.copy()
            raw_str = json.dumps(calc_data, sort_keys=True)
            current_hash = hashlib.sha256(raw_str.encode("utf-8")).hexdigest()
            record_data["hash"] = current_hash
            
            with open(self.ledger_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(record_data) + "\n")
                
            self._last_hash = current_hash
            return current_hash

    def verify_chain(self) -> bool:
        """Audit cryptographique : Vérifie l'inviolabilité de toute la chaîne de blocs."""
        with self._lock:
            if not self.ledger_file.exists() or self.ledger_file.stat().st_size == 0:
                return True
            
            lines = self.ledger_file.read_text(encoding="utf-8").splitlines()
            previous = "GENESIS_BLOCK_HASH"
            
            for line in lines:
                if not line.strip():
                    continue
                try:
                    block = json.loads(line)
                    stored_hash = block.get("hash")
                    
                    if block.get("previous_hash") != previous:
                        return False
                    
                    # On retire le hash pour recalculer la signature exacte
                    calc_block = block.copy()
                    calc_block.pop("hash", None)
                    raw_str = json.dumps(calc_block, sort_keys=True)
                    expected_hash = hashlib.sha256(raw_str.encode("utf-8")).hexdigest()
                    
                    if stored_hash != expected_hash:
                        return False
                        
                    previous = stored_hash
                except Exception:
                    return False
            return True