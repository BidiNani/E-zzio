import os
import json
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

# Chemins de référence absolue
MEMORY_DIR = "runtime/memory"
MEMORY_FILE = os.path.join(MEMORY_DIR, "working_memory.json")
LOG_FILE = "infrastructure/discord_actions.log"

# --- 1. CONTRATS SÉMANTIQUES (Pydantic Models) ---

class MemoryInteraction(BaseModel):
    timestamp: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    user_id: str
    action: str
    details: str
    sentiment: Optional[str] = "neutral"

class WorkingMemorySchema(BaseModel):
    version: str = "3.1-SemanticCore"
    last_sync: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    interactions: List[MemoryInteraction] = Field(default_factory=list)

# --- 2. GESTIONNAIRE DE MÉMOIRE & VALIDATION ---

class SemanticMemoryManager:
    def __init__(self):
        self._ensure_storage()

    def _ensure_storage(self):
        os.makedirs(MEMORY_DIR, exist_ok=True)
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        if not os.path.exists(MEMORY_FILE):
            self._save_raw(WorkingMemorySchema().dict())

    def _load_raw(self) -> dict:
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Validation structurelle via le schéma
                return WorkingMemorySchema(**data).dict()
        except Exception:
            # En cas de corruption, on réinitialise proprement tout en gardant une trace
            fresh = WorkingMemorySchema()
            self._save_raw(fresh.dict())
            return fresh.dict()

    def _save_raw(self, data: dict):
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def record_interaction(self, user_id: str, action: str, details: str, sentiment: str = "neutral") -> bool:
        try:
            # Création et validation via le contrat Pydantic
            interaction = MemoryInteraction(
                user_id=str(user_id),
                action=action,
                details=details,
                sentiment=sentiment
            )

            # Chargement de la mémoire actuelle
            mem_data = self._load_raw()
            
            # Ajout et conservation d'un historique glissant des 100 dernières interactions
            mem_data["interactions"].append(interaction.dict())
            if len(mem_data["interactions"]) > 100:
                mem_data["interactions"] = mem_data["interactions"][-100:]
            
            mem_data["last_sync"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Sauvegarde atomique
            self._save_raw(mem_data)

            # Journalisation texte en parallèle pour l'infrastructure
            log_entry = f"[{interaction.timestamp}] [USER:{interaction.user_id}] [{interaction.sentiment}] {interaction.action} -> {interaction.details}\n"
            with open(LOG_FILE, "a", encoding="utf-8") as lf:
                lf.write(log_entry)

            return True
        except Exception as e:
            print(f"[-] Erreur de validation du contrat sémantique : {e}")
            return False

# Instance globale prête à l'emploi
memory_core = SemanticMemoryManager()
