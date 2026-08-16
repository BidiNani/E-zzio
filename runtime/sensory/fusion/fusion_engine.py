"""
E-ZZIO V9.0.3 — Sensory Fusion Engine
Agrège les Percepts récents du Sensory Bus pour générer une 'Situation' unifiée.
Prépare le terrain pour la fusion Multimodale (Hardware + Vision + Audio).
"""
from typing import Dict, Any, List
from datetime import datetime, timezone
from runtime.sensory.bus.sensory_bus import SensoryBus
from runtime.sensory.bus.percept import Percept

class FusionEngine:
    def __init__(self, bus: SensoryBus):
        self.bus = bus

    def get_current_situation(self) -> Dict[str, Any]:
        """
        Extrait le dernier Percept connu pour chaque modalité sensorielle
        et génère un contexte unifié pour le Cognitive Router.
        """
        situation = {
            "fusion_timestamp": datetime.now(timezone.utc).isoformat(),
            "highest_attention": "LOW",
            "modalities": {}
        }

        # On parcourt l'historique récent du bus pour extraire la vérité actuelle
        # On utilise un dictionnaire pour écraser les vieux percepts d'une même source
        # par les plus récents.
        latest_percepts: Dict[str, Percept] = {}
        for p in self.bus._history:
            latest_percepts[p.source] = p

        highest_prio_level = 0
        prio_weights = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}

        for source, percept in latest_percepts.items():
            situation["modalities"][source] = {
                "timestamp": percept.timestamp,
                "data": percept.data
            }
            
            # Calcul du niveau d'attention global requis
            current_weight = prio_weights.get(percept.priority, 0)
            if current_weight > highest_prio_level:
                highest_prio_level = current_weight
                situation["highest_attention"] = percept.priority

        return situation
