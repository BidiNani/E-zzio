from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class CapabilityRegistryError(RuntimeError):
    pass


class CapabilityRegistrySource:
    SUPPORTED_SCHEMAS = ("5.2", "6.1")
    REQUIRED_HEALTHY_KEYS = 6
    REQUIRED_TOTAL_KEYS = 6

    def __init__(self, path: Path | None = None) -> None:
        root = Path(__file__).resolve().parents[2]
        self.path = Path(path) if path is not None else (
            root
            / "state"
            / "audit"
            / "current"
            / "capability_registry"
            / "llm_capability_registry.json"
        )
        self.data = self._load()

    def _load(self) -> dict[str, Any]:
        if not self.path.is_file():
            # [TOLERANT] Registre = artefact runtime optionnel.
            import warnings
            warnings.warn(
                f"CapabilityRegistry absent (non bloquant): {self.path}",
                RuntimeWarning, stacklevel=2,
            )
            return {}

        try:
            raw = self.path.read_text(encoding="utf-8")
            data = json.loads(raw)
        except Exception as exc:
            raise CapabilityRegistryError(
                f"Registry JSON invalide: {self.path}"
            ) from exc

        if not isinstance(data, dict):
            raise CapabilityRegistryError("Registry root must be an object")

        schema = str(data.get("schema_version", ""))
        if schema not in self.SUPPORTED_SCHEMAS:
            raise CapabilityRegistryError(
                f"Schema registry invalide: {schema!r}, attendu {self.SUPPORTED_SCHEMAS}"
            )

        availability = data.get("availability")
        if not isinstance(availability, dict):
            raise CapabilityRegistryError("Registry availability section missing")

        healthy = availability.get("healthy_keys")
        total = availability.get("total_keys")
        common_count = availability.get("common_models")

        if healthy != self.REQUIRED_HEALTHY_KEYS:
            raise CapabilityRegistryError(
                f"healthy_keys invalide: {healthy!r}, attendu 6"
            )

        if total != self.REQUIRED_TOTAL_KEYS:
            raise CapabilityRegistryError(
                f"total_keys invalide: {total!r}, attendu 6"
            )

        if healthy != total:
            raise CapabilityRegistryError(
                f"Pool Gemini non pleinement sain: {healthy}/{total}"
            )

        common = data.get("common_gemini_models")
        if not isinstance(common, list) or not common:
            raise CapabilityRegistryError(
                "common_gemini_models absent ou vide"
            )

        if common_count != len(common):
            raise CapabilityRegistryError(
                f"common_models incoherent: metadata={common_count}, actual={len(common)}"
            )

        gemini_models = data.get("gemini_models")
        if not isinstance(gemini_models, list) or not gemini_models:
            raise CapabilityRegistryError(
                "gemini_models absent ou vide"
            )

                # Rétrocompatibilité schéma 6.1 (routing -> selected)
        if "selected" not in data and isinstance(data.get("routing"), dict):
            data["selected"] = {
                role: {"model": model_name} if isinstance(model_name, str) else model_name
                for role, model_name in data["routing"].items()
            }

        selected = data.get("selected")
        if not isinstance(selected, dict):
            raise CapabilityRegistryError("selected section missing")

        for role in (
            "primary",
            "fast_cloud",
            "ultra_fast_cloud",
            "escalation",
        ):
            entry = selected.get(role)
            if not isinstance(entry, dict):
                raise CapabilityRegistryError(
                    f"selected.{role} missing"
                )
            model = entry.get("model")
            if not isinstance(model, str) or not model.strip():
                raise CapabilityRegistryError(
                    f"selected.{role}.model invalide"
                )
            if model not in common:
                raise CapabilityRegistryError(
                    f"selected.{role}.model absent de common_gemini_models: {model}"
                )

        return data

    @property
    def schema_version(self) -> str:
        return str(self.data["schema_version"])

    @property
    def common_models(self) -> list[str]:
        return list(self.data["common_gemini_models"])

    @property
    def gemini_models(self) -> list[dict[str, Any]]:
        return list(self.data["gemini_models"])

    def model_for(self, role: str) -> str:
        aliases = {
            "ultra": "ultra_fast_cloud",
        }
        canonical_role = aliases.get(role, role)

        try:
            return str(self.data["selected"][canonical_role]["model"])
        except Exception as exc:
            raise CapabilityRegistryError(
                f"Role registre inconnue: {canonical_role}"
            ) from exc

    def models_for_capability(self, capability: str) -> list[str]:
        wanted = capability.lower().strip()
        result: list[str] = []

        for record in self.gemini_models:
            if not isinstance(record, dict):
                continue

            name = record.get("name")
            capabilities = record.get("capabilities", [])

            if not isinstance(name, str):
                continue
            if name not in self.common_models:
                continue

            if isinstance(capabilities, list):
                normalized = {
                    str(value).lower().strip()
                    for value in capabilities
                    if value is not None
                }
            else:
                normalized = set()

            if wanted in normalized:
                result.append(name)

        return self._dedupe(result)

    @staticmethod
    def _dedupe(models: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []

        for model in models:
            if model and model not in seen:
                seen.add(model)
                result.append(model)

        return result

    def candidate_pools(self) -> dict[str, list[str]]:
        primary = self.model_for("primary")
        fast = self.model_for("fast_cloud")
        ultra = self.model_for("ultra_fast_cloud")
        escalation = self.model_for("escalation")

        def safe_model(model: str) -> bool:
            name = str(model).lower()

            if not name.startswith(("gemini-", "gemma-")):
                return False

            blocked = (
                "gemini-2.",
                "gemini-flash-latest",
                "gemini-flash-lite-latest",
                "gemini-pro-latest",
                "computer-use-preview",
                "deep-research",
                "omni-flash-preview",
                "native-audio",
                "transcribe",
                "tts",
                "lyria",
                "veo",
                "robotics",
                "embedding",
                "image",
            )

            return not any(token in name for token in blocked)

        def common_safe() -> list[str]:
            return [
                model
                for model in self.common_models
                if safe_model(model)
            ]

        def capability_safe(capability: str) -> list[str]:
            return [
                model
                for model in self.models_for_capability(capability)
                if safe_model(model)
            ]

        def dedupe(values: list[str]) -> list[str]:
            seen: set[str] = set()
            result: list[str] = []

            for value in values:
                if value not in seen:
                    seen.add(value)
                    result.append(value)

            return result

        all_safe = common_safe()

        fast_models = capability_safe("fast")
        reasoning_models = capability_safe("reasoning")
        deep_models = capability_safe("deep_reasoning")
        chat_models = capability_safe("chat")
        tools_models = capability_safe("tools")
        coding_models = capability_safe("coding")
        agentic_models = capability_safe("agentic")
        architecture_models = capability_safe("architecture")

        fast_pool = dedupe(
            [fast, ultra]
            + fast_models
            + [primary]
        )

        general_pool = dedupe(
            [primary, fast, ultra]
            + chat_models
            + reasoning_models
            + all_safe
        )

        coding_pool = dedupe(
            [primary]
            + coding_models
            + tools_models
            + [escalation]
        )

        agentic_pool = dedupe(
            [primary]
            + agentic_models
            + tools_models
            + [escalation]
        )

        architecture_pool = dedupe(
            [escalation]
            + architecture_models
            + reasoning_models
            + [primary]
        )

        deep_reasoning_pool = dedupe(
            [escalation]
            + deep_models
            + reasoning_models
            + [primary]
        )

        pools = {
            "fast": fast_pool,
            "general": general_pool,
            "coding": coding_pool,
            "agentic": agentic_pool,
            "architecture": architecture_pool,
            "deep_reasoning": deep_reasoning_pool,
        }

        for pool_name, candidates in pools.items():
            invalid = [
                model
                for model in candidates
                if model not in self.common_models or not safe_model(model)
            ]

            if invalid:
                raise CapabilityRegistryError(
                    f"Pool {pool_name} contient des modèles non opérationnels: {invalid}"
                )

        required_heads = {
            "primary": primary,
            "fast": fast,
            "ultra": ultra,
            "escalation": escalation,
        }

        for label, model in required_heads.items():
            if model not in self.common_models:
                raise CapabilityRegistryError(
                    f"Modèle sélectionné absent de common_models: {label}={model}"
                )

            if not safe_model(model):
                raise CapabilityRegistryError(
                    f"Modèle sélectionné bloqué par le filtre de sécurité: {label}={model}"
                )

        return pools
        primary = self.model_for("primary")
        fast = self.model_for("fast_cloud")
        ultra = self.model_for("ultra_fast_cloud")
        escalation = self.model_for("escalation")

        fast_models = self.models_for_capability("fast")
        reasoning_models = self.models_for_capability("reasoning")
        deep_models = self.models_for_capability("deep_reasoning")
        chat_models = self.models_for_capability("chat")
        tools_models = self.models_for_capability("tools")
        coding_models = self.models_for_capability("coding")
        agentic_models = self.models_for_capability("agentic")
        architecture_models = self.models_for_capability("architecture")

        def is_text_generation_model(record: dict[str, Any]) -> bool:
            name = str(record.get("name", "")).lower()
            capabilities = {
                str(value).lower().strip()
                for value in record.get("capabilities", [])
                if value is not None
            }
            methods = {
                str(value).lower().strip()
                for value in record.get("supported_generation_methods", [])
                if value is not None
            }

            if not name or name not in self.common_models:
                return False

            if "generatecontent" not in methods and "generate_content" not in methods:
                return False

            if "embedding" in capabilities and "chat" not in capabilities:
                return False

            # Exclude modality-specific generation from normal text routing.
            modality_markers = (
                "embedding",
                "veo",
                "lyria",
                "transcribe",
                "tts",
                "native-audio",
                "live",
                "robotics",
                "image",
                "banana",
            )

            if any(marker in name for marker in modality_markers):
                return False

            return "chat" in capabilities

        generative_chat_models = self._dedupe(
            [
                str(record["name"])
                for record in self.gemini_models
                if isinstance(record, dict)
                and is_text_generation_model(record)
            ]
        )

        if not generative_chat_models:
            raise CapabilityRegistryError(
                "Aucun modele de generation textuelle utilisable dans le registre"
            )

        def generative_only(models: list[str]) -> list[str]:
            return [
                model
                for model in self._dedupe(models)
                if model in generative_chat_models
            ]

        fast_models = generative_only(fast_models)
        reasoning_models = generative_only(reasoning_models)
        deep_models = generative_only(deep_models)
        chat_models = generative_only(chat_models)
        tools_models = generative_only(tools_models)
        coding_models = generative_only(coding_models)
        agentic_models = generative_only(agentic_models)
        architecture_models = generative_only(architecture_models)

        general_models = generative_only(
            [primary, fast, ultra]
            + chat_models
            + reasoning_models
        )

        if primary not in general_models:
            raise CapabilityRegistryError(
                f"Primary absent du pool general: {primary}"
            )

        if fast not in fast_models:
            fast_models.insert(0, fast)

        if ultra not in fast_models:
            fast_models.insert(1, ultra)

        fast_models = self._dedupe(fast_models)
        pools = {
            "fast": self._dedupe(
                fast_models + [primary]
            ),
            "general": general_models,
            "coding": generative_only(
                [primary] + coding_models + tools_models + [escalation]
            ),
            "agentic": generative_only(
                [primary] + agentic_models + tools_models + [escalation]
            ),
            "architecture": generative_only(
                [escalation] + architecture_models + reasoning_models + [primary]
            ),
            "deep_reasoning": generative_only(
                [escalation] + deep_models + reasoning_models + [primary]
            ),
        }
        for role, candidates in pools.items():
            valid = [
                model for model in candidates
                if model in self.common_models
            ]
            if not valid:
                raise CapabilityRegistryError(
                    f"Aucun candidat registre valide pour role={role}"
                )
            pools[role] = valid

        return pools


_registry_cache: CapabilityRegistrySource | None = None


def get_capability_registry() -> CapabilityRegistrySource:
    global _registry_cache

    if _registry_cache is None:
        _registry_cache = CapabilityRegistrySource()

    return _registry_cache


__all__ = [
    "CapabilityRegistryError",
    "CapabilityRegistrySource",
    "get_capability_registry",
]


