from dataclasses import dataclass

@dataclass
class MemorySignal:
    """Vecteur de pondération cognitive pour un événement vécu."""
    novelty: float
    importance: float
    emotional_weight: float
    future_value: float
    confidence: float

    @property
    def retention_score(self) -> float:
        """Calcule le score de rétention biologique (0.0 à 1.0)."""
        return (
            self.novelty * 0.25 +
            self.importance * 0.30 +
            self.future_value * 0.30 +
            self.confidence * 0.15
        )

class SalienceEngine:
    """Évalue la pertinence d'un événement pour décider de sa mémorisation."""
    
    @staticmethod
    def evaluate(event_type: str, payload: dict) -> MemorySignal:
        # Heuristiques de base (Phase 7.05). 
        # À terme, le LLM ou un modèle local rapide pourrait générer ces scores.
        novelty = 0.5
        importance = 0.5
        emotional_weight = 0.1
        future_value = 0.5
        confidence = 1.0

        if event_type == "ToolExecuted":
            execution = payload.get("execution", {})
            success = execution.get("success", False)
            
            if not success:
                # La douleur/l'échec enseigne : haute importance, haute nouveauté
                importance = 0.85
                novelty = 0.7
                emotional_weight = 0.6 # "Frustration" systémique
                future_value = 0.9 # Ne pas reproduire cette erreur
            else:
                # Succès routinier : importance modérée
                importance = 0.6
                future_value = 0.6

        elif event_type == "PreferenceLearned":
            importance = 0.9
            future_value = 1.0
            novelty = 0.8

        return MemorySignal(
            novelty=novelty,
            importance=importance,
            emotional_weight=emotional_weight,
            future_value=future_value,
            confidence=confidence
        )