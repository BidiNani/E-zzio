import json
from pathlib import Path
from typing import Dict, List, Set
import logging

logger = logging.getLogger("ezzio.core.domain_scope")


class DomainScopeResolver:
    """
    Résout un domaine (memory, router, security, etc.) vers une liste de fichiers concrets.
    Combinaison de 3 sources :
    1. Tags explicites dans manifest.json
    2. Fermeture du graphe de dépendances (V49 - à implémenter)
    3. FTS5 en renfort pour rattraper les fichiers mal taggés
    """

    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.manifest_path = self.project_root / "manifest.json"
        self.domain_index: Dict[str, Set[str]] = {}
        self._build_index()

    def _build_index(self):
        """Construit l'index domaine → fichiers au démarrage."""
        # 1. Tags explicites dans manifest.json
        if self.manifest_path.exists():
            try:
                with open(self.manifest_path, "r", encoding="utf-8") as f:
                    manifest = json.load(f)

                for file_entry in manifest.get("files", []):
                    filepath = file_entry.get("path", "")
                    domains = file_entry.get("domains", [])

                    for domain in domains:
                        if domain not in self.domain_index:
                            self.domain_index[domain] = set()
                        self.domain_index[domain].add(filepath)

                logger.info(f"[OK] Index domaine construit depuis manifest.json : {len(self.domain_index)} domaines")
            except Exception as e:
                logger.warning(f"[WARN] Erreur lecture manifest.json : {e}")

        # 2. Fermeture du graphe de dépendances (V49 - placeholder)
        # TODO: implémenter quand le graphe de dépendances sera prêt
        # Pour l'instant, on se base sur les tags explicites

        # 3. FTS5 en renfort (à implémenter plus tard)
        # TODO: recherche BM25 sur noms de fichiers/docstrings pour rattraper les fichiers mal taggés

    def resolve_domain(self, domain: str) -> List[str]:
        """Retourne la liste des fichiers pour un domaine donné."""
        return sorted(self.domain_index.get(domain, set()))

    def resolve_intention(self, intention: str) -> Dict[str, List[str]]:
        """
        Mappe une intention (ex: "optimise la mémoire") vers un ou plusieurs domaines.
        Retourne un dict domaine → fichiers.
        """
        # Mapping simple intention → domaine (à étendre)
        intention_map = {
            "mémoire": ["memory"],
            "memory": ["memory"],
            "router": ["router"],
            "security": ["security"],
            "discord": ["discord"],
            "codebase": ["core", "runtime"],
            "structure": ["core", "runtime"],
            "pipeline": ["pipeline", "runtime"],
            "modèle": ["model"],
            "model": ["model"],
        }

        result = {}
        for keyword, domains in intention_map.items():
            if keyword.lower() in intention.lower():
                for domain in domains:
                    files = self.resolve_domain(domain)
                    if files:
                        result[domain] = files

        return result
