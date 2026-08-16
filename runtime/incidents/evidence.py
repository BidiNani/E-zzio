from __future__ import annotations
from enum import Enum
import os
import json
from pathlib import Path
from typing import List, Optional, Dict, Any

from .model import IncidentRecord, IncidentSeverity, IncidentCategory

class EvidenceLedger:
    """
    Registre de preuves append-only et chaîné par hachage cryptographique pour V4.4.
    Garantit l'immutabilité et l'auditabilité forensic des incidents capturés.
    
    GARDE-FOU STRICT : Stockage d'observation isolé, aucune incidence sur le noyau V4.2.
    """
    def __init__(self, storage_path: Optional[Path | str] = None) -> None:
        if storage_path is None:
            project_root = Path(__file__).resolve().parent.parent.parent
            self.storage_path = project_root / "runtime" / "incidents" / "evidence_ledger.jsonl"
        else:
            self.storage_path = Path(storage_path)

        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.storage_path.exists():
            self.storage_path.touch()

    def _get_last_record(self) -> Optional[IncidentRecord]:
        """Récupère le dernier enregistrement du ledger pour chaîner le hash précédent."""
        if not self.storage_path.exists() or self.storage_path.stat().st_size == 0:
            return None
        
        last_line = None
        with open(self.storage_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    last_line = line

        if not last_line:
            return None

        try:
            data = json.loads(last_line)
            return IncidentRecord(
                incident_id=data.get("incident_id", ""),
                timestamp=data.get("timestamp", ""),
                severity=IncidentSeverity(data.get("severity", "INFO")),
                category=IncidentCategory(data.get("category", "EXECUTION_ERROR")),
                source=data.get("source", ""),
                phase=data.get("phase", ""),
                error_type=data.get("error_type", ""),
                message=data.get("message", ""),
                context_hash=data.get("context_hash", ""),
                runtime_state=data.get("runtime_state", ""),
                evidence=data.get("evidence", []),
                resolved=data.get("resolved", False),
                previous_hash=data.get("previous_hash"),
                payload_hash=data.get("payload_hash")
            )
        except Exception:
            return None

    def append(self, record: IncidentRecord) -> IncidentRecord:
        """
        Scelle et ajoute un enregistrement d'incident au registre de preuves.
        Associe le previous_hash du bloc précédent et recalcule le payload_hash.
        """
        last_record = self._get_last_record()
        if last_record and last_record.payload_hash:
            record.previous_hash = last_record.payload_hash
        else:
            record.previous_hash = "0" * 64  # Genesis hash pour la chaîne de preuves

        # S'assure que le payload_hash est à jour avec le previous_hash intégré ou calculé
        record.payload_hash = record.compute_payload_hash()

        # Écriture append-only (JSON Lines)
        with open(self.storage_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record.to_dict(), sort_keys=True, ensure_ascii=False) + "\n")

        return record

    def load_all(self) -> List[IncidentRecord]:
        """Charge l'intégralité des enregistrements du registre."""
        records = []
        if not self.storage_path.exists() or self.storage_path.stat().st_size == 0:
            return records

        with open(self.storage_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    rec = IncidentRecord(
                        incident_id=data.get("incident_id", ""),
                        timestamp=data.get("timestamp", ""),
                        severity=IncidentSeverity(data.get("severity", "INFO")),
                        category=IncidentCategory(data.get("category", "EXECUTION_ERROR")),
                        source=data.get("source", ""),
                        phase=data.get("phase", ""),
                        error_type=data.get("error_type", ""),
                        message=data.get("message", ""),
                        context_hash=data.get("context_hash", ""),
                        runtime_state=data.get("runtime_state", ""),
                        evidence=data.get("evidence", []),
                        resolved=data.get("resolved", False),
                        previous_hash=data.get("previous_hash"),
                        payload_hash=data.get("payload_hash")
                    )
                    records.append(rec)
                except Exception:
                    continue
        return records

    def verify_chain(self) -> bool:
        """
        Vérifie l'intégrité cryptographique et séquentielle de la chaîne d'incidents.
        Renvoie True si aucun enregistrement n'a été corrompu ou falsifié.
        """
        records = self.load_all()
        if not records:
            return True

        expected_previous_hash = "0" * 64

        for i, rec in enumerate(records):
            # 1. Vérifie la liaison du hash précédent
            if rec.previous_hash != expected_previous_hash:
                return False

            # 2. Recalcule et vérifie le payload_hash du bloc courant
            # Note: pour valider le payload_hash, on s'assure que le calcul correspond
            computed_hash = rec.compute_payload_hash()
            if rec.payload_hash != computed_hash:
                return False

            expected_previous_hash = rec.payload_hash

        return True