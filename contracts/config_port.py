from typing import Protocol, Optional

class IConfigProvider(Protocol):
    """
    Port d'accès à la configuration du système.
    Le noyau ne doit jamais connaître l'origine des secrets (.env, DPAPI, Vault...).
    """
    
    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Récupère une valeur de configuration optionnelle."""
        ...

    def require(self, key: str) -> str:
        """
        Récupère une valeur de configuration obligatoire.
        Lève une RuntimeError explicite si la clé est manquante.
        """
        ...