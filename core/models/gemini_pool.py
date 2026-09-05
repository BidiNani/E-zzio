"""
E-ZZIO Core — Project-Aware Gemini Pool & Capability-Based Model Router.
Gère les projets Google Cloud (les quotas sont par projet, pas par clé individuelle),
la rotation immédiate sans sleep artificiel sur 429 (avec Retry-After),
l'invalidation sur 401/403, et la sélection par profil de tâche.
"""
from __future__ import annotations
import os
import re
import time
import random
import logging
from typing import Any, Dict, List, Optional, Tuple
from core.models.capability_registry_source import get_capability_registry
from dataclasses import dataclass, field
from threading import Lock

logger = logging.getLogger("EzzioGeminiPool")

# Modèles officiels Gemini 3.x supportés et gouvernés
OFFICIAL_GEMINI_MODELS = [
    "gemini-3.7-flash",       # TIER 1 : Agentique, Coding, Outils (1M ctx, 64k out, thinking levels)
    "gemini-3.5-flash",       # TIER 2 : Généraliste GA, Haut débit
    "gemini-3.5-flash-lite",  # TIER 3 : Haute fréquence, sous-tâches, extraction (Fast default)
    "gemini-3.1-flash-lite",  # TIER 3 : Migration programmée -> 2027-05-07
    "gemini-3.1-pro-preview", # TIER 4 : Raisonnement profond, architecture
    "gemini-3.6-flash",       # TIER 5 : Previous-generation Flash fallback
    "gemini-3.1-flash-image", # TIER IMAGE : Nano Banana 2 (Génération/Édition d'images)
    "gemini-3-pro-image",     # TIER IMAGE : Nano Banana Pro (Haute fidélité)
    "gemini-omni-1.1-flash",  # TIER VIDÉO : Gemini Omni Flash (Génération/Édition vidéo jusqu'à 4K)
]

# Registre contractuel du cycle de vie des modèles (Lifecycle Registry)
MODEL_LIFECYCLE_REGISTRY: Dict[str, Dict[str, Any]] = {
    "gemini-3.7-flash": {
        "status": "GA",
        "tier": "AGENTIC_CODING",
        "context_window": 1048576,
        "max_output_tokens": 65536,
        "thinking_support": ["low", "medium", "high"],
        "recommended_for": ["complex_coding", "multi_step_agent", "tool_use"]
    },
    "gemini-3.5-flash": {
        "status": "GA",
        "tier": "GENERAL",
        "context_window": 1048576,
        "max_output_tokens": 8192,
        "recommended_for": ["general_chat", "summarization", "analysis"]
    },
    "gemini-3.5-flash-lite": {
        "status": "GA",
        "tier": "FAST",
        "context_window": 1048576,
        "max_output_tokens": 8192,
        "recommended_for": ["low_latency_gateway", "fast_extraction", "subagents"]
    },
    "gemini-3.1-flash-lite": {
        "status": "ACTIVE",
        "tier": "LEGACY_FAST",
        "shutdown_date": "2027-05-07",
        "replacement_model": "gemini-3.5-flash-lite",
        "recommended_for": ["transition_only"]
    },
    "gemini-3.1-pro-preview": {
        "status": "ACTIVE",
        "tier": "DEEP_REASONING",
        "context_window": 2097152,
        "max_output_tokens": 8192,
        "recommended_for": ["complex_architecture", "formal_verification"]
    },
    "gemini-3.6-flash": {
        "status": "PREVIOUS_GEN",
        "tier": "FALLBACK_COMPAT",
        "context_window": 1048576,
        "max_output_tokens": 8192,
        "recommended_for": ["compatibility_fallback"]
    },
    "gemini-3.1-flash-image": {
        "status": "GA",
        "tier": "IMAGE_GENERATION",
        "codename": "Nano Banana 2",
        "recommended_for": ["ai_image_synthesis", "image_editing"]
    },
    "gemini-3-pro-image": {
        "status": "GA",
        "tier": "IMAGE_GENERATION_PRO",
        "codename": "Nano Banana Pro",
        "recommended_for": ["high_fidelity_image_synthesis"]
    },
    "gemini-omni-1.1-flash": {
        "status": "GA",
        "tier": "VIDEO_GENERATION",
        "release_date": "2026-08-27",
        "recommended_for": ["video_generation", "image_to_video", "video_extension_4k"]
    }
}

# Classement des modèles par profil de capacité
CAPABILITY_MODEL_RANKING = {
    "fast": ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3.5-flash"],
    "extraction": ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite"],
    "subagent": ["gemini-3.1-flash-lite", "gemini-3.5-flash-lite"],
    "general": ["gemini-3.5-flash", "gemini-3.7-flash", "gemini-3.6-flash"],
    "coding": ["gemini-3.7-flash", "gemini-3.5-flash", "gemini-3.6-flash"],
    "agentic": ["gemini-3.7-flash", "gemini-3.5-flash"],
    "tools": ["gemini-3.7-flash", "gemini-3.5-flash"],
    "reasoning": ["gemini-3.1-pro-preview", "gemini-3.7-flash", "gemini-3.5-flash"],
    "architecture": ["gemini-3.1-pro-preview", "gemini-3.7-flash"],
    "image": ["gemini-3.1-flash-image", "gemini-3-pro-image"],
    "video": ["gemini-omni-1.1-flash"],
}


@dataclass
class GeminiKeySlot:
    key: str = field(repr=False)
    is_valid: bool = True
    consecutive_errors: int = 0
    total_calls: int = 0


@dataclass
class GeminiProjectSlot:
    project_id: str
    keys: List[GeminiKeySlot] = field(default_factory=list)
    blocked_until: float = 0.0
    current_key_index: int = 0
    total_requests: int = 0
    quota_exhaustions: int = 0

    def is_available(self, now: float | None = None) -> bool:
        now = time.time() if now is None else now
        if now < self.blocked_until:
            return False
        return any(k.is_valid for k in self.keys)

    def get_active_key(self) -> Tuple[int, Optional[str]]:
        valid_indices = [idx for idx, k in enumerate(self.keys) if k.is_valid]
        if not valid_indices:
            return -1, None
        chosen_idx = valid_indices[self.current_key_index % len(valid_indices)]
        slot = self.keys[chosen_idx]
        self.current_key_index += 1
        slot.total_calls += 1
        self.total_requests += 1
        return chosen_idx, slot.key

    def mark_rate_limited(self, retry_after_sec: float = 60.0):
        self.blocked_until = time.time() + max(1.0, retry_after_sec)
        self.quota_exhaustions += 1
        logger.warning(
            "[GEMINI-POOL] Projet '%s' marqué en Quota-Exhausted (429) pendant %.1fs",
            self.project_id, retry_after_sec
        )

    def mark_key_invalid(self, key_str: str):
        for k in self.keys:
            if k.key == key_str:
                k.is_valid = False
                logger.error("[GEMINI-POOL] Clé invalidée (401/403) dans le projet '%s'", self.project_id)


class GeminiPoolManager:
    """Gestionnaire de pool de projets Google Gemini thread-safe et résilient."""

    def __init__(self):
        self.projects: List[GeminiProjectSlot] = []
        self._lock = Lock()
        self._unsupported_models: Dict[str, float] = {}  # model -> blocked_until
        self._capability_registry = get_capability_registry()
        self.OFFICIAL_GEMINI_MODELS = OFFICIAL_GEMINI_MODELS
        # Preserve canonical capability ranking with dynamic registry augmentations if present
        self.CAPABILITY_MODEL_RANKING = dict(CAPABILITY_MODEL_RANKING)
        self._load_from_vault_and_env()

    def _load_from_vault_and_env(self):
        from core.security.unified_vault import key_vault
        primary_key = key_vault.get_provider_key("gemini") or os.getenv("GEMINI_API_KEY", "")

        # Projet par défaut (Project A)
        proj_a_keys = []
        seen_keys = set()

        # Clé primaire issue du vault ou de GEMINI_API_KEY.
        if primary_key and primary_key.strip():
            normalized = primary_key.strip()
            proj_a_keys.append(GeminiKeySlot(key=normalized))
            seen_keys.add(normalized)

        # Découverte robuste de toutes les clés GEMINI_API_KEY[_N].
        # Le suffixe commence à 1 et reste extensible.
        for i in range(1, 100):
            env_name = f"GEMINI_API_KEY_{i}"
            k = os.getenv(env_name)

            if k and k.strip():
                normalized = k.strip()

                if normalized not in seen_keys:
                    proj_a_keys.append(GeminiKeySlot(key=normalized))
                    seen_keys.add(normalized)

        if proj_a_keys:
            self.projects.append(
                GeminiProjectSlot(
                    project_id="project_default",
                    keys=proj_a_keys
                )
            )

        # Projets distincts explicitement configurés (Project B, C...)
        for env_k, env_v in os.environ.items():
            m = re.match(r"^GEMINI_PROJECT_([A-Z0-9]+)_KEY.*", env_k)
            if m and env_v.strip():
                p_id = f"project_{m.group(1).lower()}"
                existing = next((p for p in self.projects if p.project_id == p_id), None)
                if not existing:
                    existing = GeminiProjectSlot(project_id=p_id, keys=[])
                    self.projects.append(existing)
                existing.keys.append(GeminiKeySlot(key=env_v.strip()))

    def get_candidate_models(self, capability: str = "general") -> List[str]:
        """Retourne la liste ordonnée des modèles candidats pour une capacité donnée."""
        ranking = self.CAPABILITY_MODEL_RANKING.get(capability.lower(), self.CAPABILITY_MODEL_RANKING["general"])
        now = time.time()
        return [
            m for m in ranking
            if m in self.OFFICIAL_GEMINI_MODELS and self._unsupported_models.get(m, 0.0) <= now
        ]

    def acquire_execution_target(self, capability: str = "general") -> Tuple[Optional[str], Optional[str], int, Optional[GeminiProjectSlot]]:
        """
        Sélectionne le meilleur (modèle, clé, index_clé, projet) disponible immédiatement sans attente.
        """
        with self._lock:
            candidates = self.get_candidate_models(capability)
            if not candidates:
                candidates = [self._capability_registry.model_for("fast_cloud")]

            now = time.time()
            available_projects = [p for p in self.projects if p.is_available(now)]

            if not available_projects:
                logger.warning("[GEMINI-POOL] Tous les projets Gemini sont actuellement limités ou épuisés.")
                return None, None, -1, None

            selected_project = min(available_projects, key=lambda p: p.total_requests)
            key_idx, key = selected_project.get_active_key()
            selected_model = candidates[0]

            return selected_model, key, key_idx, selected_project

    def acquire_target(self, capability: str = "general", model_override: Optional[str] = None) -> Tuple[str, str, int, GeminiProjectSlot]:
        """Acquiert un tuple (modèle, clé, index_clé, projet) avec prise en charge d'un modèle forcé."""
        selected_model, key, key_idx, selected_project = self.acquire_execution_target(capability)
        if not key or not selected_project:
            raise RuntimeError("No available Gemini project slot in pool")
        if model_override:
            selected_model = model_override
        return selected_model, key, key_idx, selected_project

    def handle_error(
        self,
        project: Optional[GeminiProjectSlot],
        key: Optional[str],
        model: str,
        status_code: int,
        headers: Optional[Dict[str, str]] = None
    ) -> None:
        """Met à jour l'état du pool suite à un échec HTTP sans délai bloquant."""
        with self._lock:
            if status_code == 429:
                retry_after = 60.0
                if headers:
                    ra_hdr = headers.get("retry-after") or headers.get("Retry-After")
                    if ra_hdr and ra_hdr.isdigit():
                        retry_after = float(ra_hdr)
                if project:
                    project.mark_rate_limited(retry_after)

            elif status_code in (401, 403):
                if project and key:
                    project.mark_key_invalid(key)

            elif status_code == 404:
                self._unsupported_models[model] = time.time() + 86400.0
                logger.warning("[GEMINI-POOL] Modèle '%s' indisponible (404). Écarté temporairement.", model)


# Singleton partagé pour la gouvernance des modèles
gemini_pool = GeminiPoolManager()

# Alias canoniques
GeminiPool = GeminiPoolManager
GeminiProjectConfig = GeminiProjectSlot
GeminiKeyConfig = GeminiKeySlot
