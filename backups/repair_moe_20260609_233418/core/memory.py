import json
from datetime import datetime
from pathlib import Path

class MemoryManager:
    def __init__(self, storage_path="G:/AI/E-zzio/registry/history.json"):
        self.storage_path = Path(storage_path)
        # Création du fichier si inexistant
        if not self.storage_path.exists():
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump([], f)

    def save_interaction(self, input_text, response_text, expert_name):
        """Enregistre un échange dans l'historique."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "input": input_text,
            "response": response_text,
            "expert": expert_name
        }
        
        with open(self.storage_path, 'r+', encoding='utf-8') as f:
            data = json.load(f)
            data.append(entry)
            f.seek(0)
            json.dump(data, f, indent=4)

    def get_context(self, last_n=3):
        """Récupère les derniers échanges pour donner du contexte au prochain modèle."""
        with open(self.storage_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data[-last_n:]

# Instance partagée
ezzio_memory = MemoryManager()