"""
core/routing/model_registry.py

Hub d'API pour les rôles métier des modèles.

ARCHITECTURE :
  - registry.py       : SOURCE UNIQUE des modèles (cloud + local)
  - model_registry.py : HUB API (rôles + compatibilité)
  - provider_http.py : HTTP fetch + pricing

API PUBLIQUE (13 consommateurs) :
  - canonical_model_registry (SINGLETON)
  - CanonicalModelRegistry (classe)
  - CanonicalModelRecord (structure, champ `name` + alias `model_id`)
  - ModelSource, LatencyTier, ModelQualificationStatus

Pour ajouter un rôle : modifier ROLE_MAP ci-dessous.
Pour ajouter un modèle : modifier registry.py.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto

from core.routing.registry import (
    LOCAL_MODELS as _LOCAL_MODELS,
)
from core.routing.registry import (
    all_models as _all_cloud_models,
)

# ============================================================
# ENUMS (API PUBLIQUE)
# ============================================================

class ModelSource(Enum):
    LOCAL = auto()
    GEMINI = auto()
    GROQ = auto()
    NVIDIA = auto()
    ANTHROPIC = auto()
    OPENAI = auto()
    MISTRAL = auto()


class LatencyTier(Enum):
    ULTRA_FAST = auto()
    FAST = auto()
    MEDIUM = auto()
    SLOW = auto()


class ModelQualificationStatus(Enum):
    QUALIFIED = auto()
    DISQUALIFIED = auto()
    DISABLED = auto()
    EXPERIMENTAL = auto()


# ============================================================
# STRUCTURE (API PUBLIQUE — champ `name` conservé)
# ============================================================

@dataclass
class CanonicalModelRecord:
    """Structure d'un modèle avec rôles.

    Le champ `name` est l'API historique (utilisé par 3 consommateurs).
    Le champ `model_id` est un alias en lecture seule.
    """
    name: str
    source: ModelSource = ModelSource.GEMINI
    provider: str = ""  # Phase 2.3A : provider canonique (gemini, groq, ollama, ...)
    latency_tier: LatencyTier = LatencyTier.FAST
    qualification_status: ModelQualificationStatus = ModelQualificationStatus.QUALIFIED
    enabled: bool = True
    role: str = "general"
    roles: list[str] = field(default_factory=list)
    thinking_level: str = "off"

    @property
    def model_id(self) -> str:
        """Alias historique pour `name`."""
        return self.name

    def __post_init__(self):
        if self.role and self.role not in self.roles:
            self.roles.append(self.role)


# ============================================================
# RÔLES MÉTIER (seule info "locale" à ce fichier)
# ============================================================
# Format : model_id -> (role_principal, [roles_additionnels])

ROLE_MAP: dict[str, tuple[str, list[str]]] = {
    # --- Gemini cloud ---
    "gemini-3.8-flash": ("MASTER", ["MASTER", "MASTER_STRATEGIC"]),
    "gemini-3.7-flash": ("CODING", ["CODING"]),
    "gemini-3.6-flash": ("FORENSIC", ["FORENSIC"]),
    "gemini-3.5-flash-lite": ("STANDARD_CHAT", ["STANDARD_CHAT", "FAST_CHAT", "FAST", "FALLBACK"]),
    "gemini-3.5-flash": ("REFACTOR", ["REFACTOR"]),

    # --- Local Ollama ---
    "qwen2.5-coder:7b-instruct-q4_K_M": ("LOCAL", ["LOCAL", "LOCAL_CODING"]),
    "qwen3.5-mtp:4b": ("FAST_LOCAL", ["FAST_LOCAL"]),
    "phi4-mini:latest": ("LOCAL_MINI", ["LOCAL_MINI"]),
    "hermes3:8b": ("LOCAL_AGENT", ["LOCAL_AGENT"]),
    "qwen3.5:9b": ("GENERALIST", ["GENERALIST", "THINKING"]),
    "deepseek-r1:7b": ("REASONING", ["REASONING", "THINKING"]),
}


_PROVIDER_TO_SOURCE: dict[str, ModelSource] = {
    "gemini": ModelSource.GEMINI,
    "groq": ModelSource.GROQ,
    "anthropic": ModelSource.ANTHROPIC,
    "openai": ModelSource.OPENAI,
    "mistral": ModelSource.MISTRAL,
}


# ============================================================
# REGISTRE (assemble registry.py + ROLE_MAP)
# ============================================================

class CanonicalModelRegistry:
    """Registre qui assemble registry.py + ROLE_MAP."""

    def __init__(self):
        self._models: list[CanonicalModelRecord] = []
        self._by_name: dict[str, CanonicalModelRecord] = {}
        self._build()

    def _build(self) -> None:
        # 1. Modèles cloud (via registry.py)
        for model in _all_cloud_models():
            if model.id not in ROLE_MAP:
                continue
            role, extra_roles = ROLE_MAP[model.id]
            source = _PROVIDER_TO_SOURCE.get(model.provider, ModelSource.GEMINI)
            thinking = (
                model.thinking_levels[0] if model.thinking_levels else "off"
            )
            self._add(CanonicalModelRecord(
                name=model.id,
                source=source,
                provider=model.provider,  # Phase 2.3A
                role=role,
                roles=list(extra_roles),
                thinking_level=thinking,
            ))

        # 2. Modèles locaux (via registry.py)
        for model in _LOCAL_MODELS:
            if model.id not in ROLE_MAP:
                continue
            role, extra_roles = ROLE_MAP[model.id]
            thinking = "low" if model.thinking else "off"
            self._add(CanonicalModelRecord(
                name=model.id,
                source=ModelSource.LOCAL,
                provider="ollama",  # Phase 2.3A
                role=role,
                roles=list(extra_roles),
                thinking_level=thinking,
            ))

    def _add(self, record: CanonicalModelRecord) -> None:
        if record.name in self._by_name:
            return
        self._models.append(record)
        self._by_name[record.name] = record

    # ---------- API PUBLIQUE ----------

    def list_models(
        self,
        qualified_only: bool = True,
        include_disabled: bool = False,
    ) -> list[CanonicalModelRecord]:
        return list(self._models)

    def get(self, name: str) -> CanonicalModelRecord | None:
        return self._by_name.get(name)

    def get_by_role(self, role: str) -> CanonicalModelRecord | None:
        for m in self._models:
            if role in m.roles or m.role == role:
                return m
        return None

    def get_all_by_role(self, role: str) -> list[CanonicalModelRecord]:
        return [m for m in self._models if role in m.roles or m.role == role]

    def resolve_cloud_role(self, role: str) -> CanonicalModelRecord | None:
        """Résolution canonique d'une cible cloud pour un rôle donné (force_cloud).

        Procédure obligatoire :
          1. Recherche tous les records associés au rôle via get_all_by_role().
          2. Filtre les modèles non-Ollama (provider != 'ollama' et source != ModelSource.LOCAL).
          3. S'il y a 0 candidat cloud -> FAIL-CLOSED (None).
          4. S'il y a 1 candidat cloud -> cible canonique valide.
          5. S'il y a >1 candidats cloud -> ambiguïté architecturale -> FAIL-CLOSED (None).
        """
        all_records = self.get_all_by_role(role)
        cloud_records = [
            m for m in all_records
            if m.provider != "ollama" and m.source != ModelSource.LOCAL
        ]

        if len(cloud_records) == 1:
            return cloud_records[0]
        # 0 candidats ou >1 candidats (ambiguïté architecturale) -> FAIL-CLOSED
        return None



# ============================================================
# SINGLETON (API PUBLIQUE — CRITIQUE)
# ============================================================

canonical_model_registry = CanonicalModelRegistry()


def get_registry() -> CanonicalModelRegistry:
    return canonical_model_registry
