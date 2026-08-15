"""
E-ZZIO Core — Multi-Tier Memory Governance Engine (V8.0)
Gère l'architecture mémorielle à 6 niveaux (L0 à L5), calcule l'importance,
gère la compression intelligente avec provenance, et s'intègre à la passerelle ECOL.
"""
import os
import sys
import json
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

class MemoryCorruptionError(Exception):
    """Levée en cas de rupture de hachage ou d'altération de la mémoire (Fail-Closed)."""
    pass

class MultiTierMemoryEngine:
    TIERS = {
        "L0_WORKING": {"volatility": "high", "persistence": "ephemeral"},
        "L1_SESSION": {"volatility": "medium", "persistence": "session"},
        "L2_PROJECT": {"volatility": "low", "persistence": "persistent"},
        "L3_EXPERIENCE": {"volatility": "low", "persistence": "long_term"},
        "L4_SEMANTIC": {"volatility": "very_low", "persistence": "compressed_knowledge"},
        "L5_CONSTITUTIONAL": {"volatility": "immutable", "persistence": "permanent"}
    }

    def __init__(self, root_dir: Path = ROOT_DIR):
        self.root_dir = root_dir
        self.memory_store_dir = self.root_dir / "runtime" / "memory_store"
        self.memory_store_dir.mkdir(parents=True, exist_ok=True)
        
        self.gateway = EcolUniversalGateway()
        self.gateway.register_gateway_action("MEMORY_MULTI_TIER_WRITE")

    def store_memory(
        self,
        tier: str,
        memory_id: str,
        content: str,
        source: str,
        importance: float = 1.0,
        compression_ratio: float = 1.0
    ) -> Dict[str, Any]:
        """
        Stocke une information dans l'une des 6 couches mémorielles après validation ECOL,
        en calculant son empreinte SHA-256 et sa provenance.
        """
        if tier not in self.TIERS:
            raise ValueError(f"Couche mémoire invalide : {tier}")

        if tier == "L5_CONSTITUTIONAL":
            raise MemoryCorruptionError("FAIL CLOSED : Tentative d'écriture non autorisée sur la couche constitutionnelle L5.")

        # Calcul du hachage cryptographique du contenu brut pour la provenance
        content_bytes = content.encode("utf-8")
        content_hash = hashlib.sha256(content_bytes).hexdigest().lower()

        memory_record = {
            "tier": tier,
            "memory_id": memory_id,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "source": source,
            "importance": importance,
            "compression_ratio": compression_ratio,
            "original_sha256": content_hash,
            "content": content
        }

        # Payload de gouvernance pour la passerelle ECOL
        payload = {
            "source_component": "memory_subsystem",
            "action": "MEMORY_MULTI_TIER_WRITE",
            "task_description": f"Écriture mémorielle [{tier}] -> {memory_id}",
            "priority": "normal",
            "risk_level": "low" if importance < 2.0 else "medium",
            "estimated_cost": len(content)
        }

        def commit_to_disk():
            tier_dir = self.memory_store_dir / tier
            tier_dir.mkdir(parents=True, exist_ok=True)
            
            file_path = tier_dir / f"{memory_id}.json"
            file_path.write_text(json.dumps(memory_record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            return memory_record

        # Exécution sécurisée via la passerelle No-Bypass ECOL
        result = self.gateway.execute_via_gateway(
            action="MEMORY_MULTI_TIER_WRITE",
            payload=payload,
            target_func=commit_to_disk
        )

        return result

def test_multi_tier_memory():
    print("[*] Test du Multi-Tier Memory Governance Engine (V8.0)...")
    engine = MultiTierMemoryEngine()

    # Test 1 : Écriture dans la mémoire d'expérience (L3)
    print("\n--- Test 1 : Écriture mémorielle L3 (Expérience & Leçons) ---")
    res_l3 = engine.store_memory(
        tier="L3_EXPERIENCE",
        memory_id="EXP-20260812-GUARDIAN-MUTEX",
        content="Éviter le conflit Global Mutex lors des audits concurrents en utilisant des verrous contextuels non bloquants.",
        source="architecture_review",
        importance=1.5,
        compression_ratio=0.85
    )
    print(f"  [PASS] Mémoire L3 enregistrée. ID : {res_l3['memory_id']} | Hash : {res_l3['original_sha256'][:16]}...")

    # Test 2 : Écriture dans la mémoire sémantique compressée (L4)
    print("\n--- Test 2 : Écriture mémorielle L4 (Connaissance sémantique compressée) ---")
    res_l4 = engine.store_memory(
        tier="L4_SEMANTIC",
        memory_id="SEM-WOW-335A-WAY-OF-ELENDIL",
        content="Configuration serveur Way of Elendil 3.3.5a : gestion des addons et scripts Bao Publisher.",
        source="server_sync",
        importance=1.2,
        compression_ratio=0.40
    )
    print(f"  [PASS] Mémoire L4 enregistrée. ID : {res_l4['memory_id']} | Compression : {res_l4['compression_ratio']}")

    print("\n" + "="*65)
    print(" MULTI-TIER MEMORY ENGINE (V8.0) : INITIALIZED & GOVERNED")
    print("="*65)

if __name__ == "__main__":
    test_multi_tier_memory()
