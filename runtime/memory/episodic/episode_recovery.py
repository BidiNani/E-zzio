from typing import List
from runtime.memory.episodic.episode import Episode
from runtime.memory.sqlite.store import SQLiteEventStore
from runtime.memory.episode_store import EpisodeStore
from runtime.memory.episode_extractor import EpisodeExtractor

class EpisodeRecovery:
    """Récupère les événements non consolidés au démarrage et reconstruit les épisodes."""

    def __init__(
        self,
        event_store: SQLiteEventStore,
        episode_store: EpisodeStore,
        extractor: EpisodeExtractor
    ):
        self.event_store = event_store
        self.episode_store = episode_store
        self.extractor = extractor

    def recover(self) -> List[Episode]:
        # 1. Récupération des événements bruts orphelins (consolidated = 0)
        events = self.event_store.get_unconsolidated_events()
        if not events:
            return []

        # 2. Extraction des épisodes via l'extracteur déterministe
        episodes = self.extractor.extract_from_events(events)

        # 3. Sauvegarde et marquage de consolidation
        for episode in episodes:
            self.episode_store.save_episode(episode)
            
            # Marquer tous les steps de l'épisode comme consolidés
            event_ids = [step.event_id for step in episode.steps]
            self.event_store.mark_consolidated(event_ids)

        return episodes