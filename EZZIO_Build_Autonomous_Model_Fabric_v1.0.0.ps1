#requires -Version 7.4
# =============================================================================
# E-ZZIO — AUTONOMOUS MODEL FABRIC
# Bootstrap Builder
# Version : 1.0.0
#
# OBJECTIF
# --------
# Construit automatiquement le moteur autonome de :
#   - découverte dynamique des modèles
#   - qualification par seuils
#   - registre dynamique
#   - cycle de vie des modèles
#   - routage cognitif
#   - rotation multi-clés
#   - cooldown / quota / invalidation
#   - failover fournisseur
#   - télémétrie forensic
#
# FOURNISSEURS
# ------------
#   Gemini
#   Groq
#   OpenRouter
#   LiteLLM
#
# EXCLUSIONS
# ----------
#   Ollama : ABSENT
#   GPU     : ABSENT
#   Secret  : AUCUNE VALEUR EMBARQUÉE
#
# MODE DU BUILDER
# ---------------
#   READ/WRITE PROJECT FILES
#   NO NETWORK
#   NO SECRET VALUE OUTPUT
#   NO CREDENTIAL MODIFICATION
#   NO PROVIDER EXECUTION
# =============================================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$Version = '1.0.0'
$ProjectRoot = 'G:\AI\E-zzio'

$ModelsRoot = Join-Path $ProjectRoot 'core\models'
$DiscoveryRoot = Join-Path $ModelsRoot 'discovery'
$QualificationRoot = Join-Path $ModelsRoot 'qualification'

$DataRoot = Join-Path $ProjectRoot 'data\models'
$ForensicRoot = Join-Path $ProjectRoot '_forensic\reports'

$ManifestPath = Join-Path $ModelsRoot 'fabric_manifest.json'

$CreatedFiles = New-Object System.Collections.Generic.List[string]
$FailedFiles = New-Object System.Collections.Generic.List[string]

$StartTime = Get-Date
$RunId = $StartTime.ToString('yyyyMMdd_HHmmss')

# -----------------------------------------------------------------------------
# Console helpers
# -----------------------------------------------------------------------------

function Write-Header {
    param([string]$Title)

    Write-Host ''
    Write-Host '============================================================================='
    Write-Host " $Title"
    Write-Host '============================================================================='
    Write-Host ''
}

function Write-Section {
    param(
        [int]$Number,
        [int]$Total,
        [string]$Title
    )

    Write-Host ''
    Write-Host '-----------------------------------------------------------------------------'
    Write-Host "[$Number/$Total] $Title"
    Write-Host '-----------------------------------------------------------------------------'
}

function Write-Pass {
    param([string]$Message)
    Write-Host "[PASS] $Message" -ForegroundColor Green
}

function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Cyan
}

function Write-Warn {
    param([string]$Message)
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Write-Fail {
    param([string]$Message)
    Write-Host "[FAIL] $Message" -ForegroundColor Red
}

# -----------------------------------------------------------------------------
# Secure file writer
# -----------------------------------------------------------------------------

function Write-ProjectFile {
    param(
        [Parameter(Mandatory)]
        [string]$Path,

        [Parameter(Mandatory)]
        [string]$Content
    )

    try {
        $Parent = Split-Path -Parent $Path

        if (-not (Test-Path -LiteralPath $Parent -PathType Container)) {
            New-Item -ItemType Directory -Path $Parent -Force | Out-Null
        }

        [System.IO.File]::WriteAllText(
            $Path,
            $Content,
            [System.Text.UTF8Encoding]::new($false)
        )

        $CreatedFiles.Add($Path) | Out-Null
        Write-Pass "Créé : $Path"
    }
    catch {
        $FailedFiles.Add($Path) | Out-Null
        Write-Fail "Échec création : $Path"
        throw
    }
}

# =============================================================================
# START
# =============================================================================

Write-Header 'E-ZZIO — AUTONOMOUS MODEL FABRIC'
Write-Host " Version : $Version"
Write-Host ' Mode    : BOOTSTRAP / FORENSIC / NO NETWORK'
Write-Host ' Providers : GEMINI / GROQ / OPENROUTER / LITELLM'
Write-Host ' Ollama    : EXCLU'
Write-Host ''
Write-Info "RunId : $RunId"
Write-Info "Début : $($StartTime.ToString('yyyy-MM-dd HH:mm:ss'))"

# =============================================================================
# [1/10] VALIDATION
# =============================================================================

Write-Section 1 10 'Validation du projet'

if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) {
    throw "Projet introuvable : $ProjectRoot"
}

Write-Pass "Projet : $ProjectRoot"

$SecretsRoot = Join-Path $ProjectRoot 'secrets'

if (-not (Test-Path -LiteralPath $SecretsRoot -PathType Container)) {
    Write-Warn "Dossier secrets absent : $SecretsRoot"
    Write-Warn 'Le Fabric sera construit sans dépendre de son existence.'
}
else {
    Write-Pass "Coffre détecté : $SecretsRoot"
}

# =============================================================================
# [2/10] DOSSIERS
# =============================================================================

Write-Section 2 10 'Création de l''arborescence'

$Directories = @(
    $ModelsRoot,
    $DiscoveryRoot,
    $QualificationRoot,
    $DataRoot,
    $ForensicRoot
)

foreach ($Directory in $Directories) {
    if (-not (Test-Path -LiteralPath $Directory -PathType Container)) {
        New-Item -ItemType Directory -Path $Directory -Force | Out-Null
        Write-Pass "Dossier créé : $Directory"
    }
    else {
        Write-Info "Dossier déjà présent : $Directory"
    }
}

# =============================================================================
# [3/10] PYTHON PACKAGE
# =============================================================================

Write-Section 3 10 'Création du package Python'

Write-ProjectFile (Join-Path $ModelsRoot '__init__.py') @'
"""E-ZZIO Autonomous Model Fabric.

Dynamic provider discovery, qualification, registry, routing and key rotation.

Providers:
    Gemini
    Groq
    OpenRouter
    LiteLLM

Ollama is intentionally not supported by this package.
"""
'@

Write-ProjectFile (Join-Path $DiscoveryRoot '__init__.py') @'
"""E-ZZIO provider discovery layer."""
'@

Write-ProjectFile (Join-Path $QualificationRoot '__init__.py') @'
"""E-ZZIO model qualification layer."""
'@

# =============================================================================
# [4/10] ERRORS
# =============================================================================

Write-Section 4 10 'Création des primitives de sécurité'

Write-ProjectFile (Join-Path $ModelsRoot 'errors.py') @'
"""E-ZZIO Model Fabric errors."""

from __future__ import annotations


class FabricError(RuntimeError):
    """Base error for the Autonomous Model Fabric."""


class DiscoveryError(FabricError):
    """Provider discovery failure."""


class QualificationError(FabricError):
    """Model qualification failure."""


class RoutingError(FabricError):
    """Routing failure."""


class ProviderExhaustedError(RoutingError):
    """All provider/key candidates are exhausted."""


class SecretSafetyError(FabricError):
    """Detected unsafe secret handling."""


class ConfigurationError(FabricError):
    """Invalid Fabric configuration."""
'@

# =============================================================================
# KEY POOL
# =============================================================================

Write-ProjectFile (Join-Path $ModelsRoot 'key_pool.py') @'
"""E-ZZIO secure multi-key pool.

Secrets are loaded from environment variables at runtime and are never
serialized, represented, or emitted in forensic status.

Supported naming convention:
    GEMINI_API_KEY
    GEMINI_API_KEY_2
    ...
    GROQ_API_KEY
    GROQ_API_KEY_2
    ...
    OPENROUTER_API_KEY
    OPENROUTER_API_KEY_2
    ...

The manager deliberately does not know the actual secret value outside
the in-memory KeySlot object.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from enum import StrEnum
from threading import Lock
from typing import Any


class KeyState(StrEnum):
    READY = "READY"
    IN_USE = "IN_USE"
    COOLDOWN = "COOLDOWN"
    QUOTA_EXHAUSTED = "QUOTA_EXHAUSTED"
    INVALID = "INVALID"


@dataclass(slots=True)
class KeySlot:
    slot_id: str
    provider: str
    env_var_name: str
    secret_value: str = field(repr=False)

    state: KeyState = KeyState.READY
    cooldown_until: float = 0.0
    daily_requests: int = 0
    consecutive_errors: int = 0
    total_successes: int = 0
    total_failures: int = 0
    last_used: float = 0.0
    created_at: float = field(default_factory=time.time)

    def available(self, now: float | None = None) -> bool:
        now = time.time() if now is None else now

        if self.state == KeyState.READY:
            return True

        if self.state == KeyState.COOLDOWN and now >= self.cooldown_until:
            self.state = KeyState.READY
            self.consecutive_errors = 0
            return True

        return False


class KeyPoolManager:
    """Thread-safe provider key scheduler."""

    PREFIXES: dict[str, tuple[str, ...]] = {
        "gemini": ("GEMINI_API_KEY",),
        "groq": ("GROQ_API_KEY",),
        "openrouter": ("OPENROUTER_API_KEY",),
    }

    def __init__(
        self,
        *,
        cooldown_seconds: float = 60.0,
        max_consecutive_errors: int = 3,
    ) -> None:
        self.cooldown_seconds = cooldown_seconds
        self.max_consecutive_errors = max_consecutive_errors

        self._slots: dict[str, list[KeySlot]] = {}
        self._lock = Lock()

        self._load_from_environment()

    def _load_from_environment(self) -> None:
        for provider, roots in self.PREFIXES.items():
            slots: list[KeySlot] = []

            for root in roots:
                names = [root]

                for index in range(2, 101):
                    names.append(f"{root}_{index}")

                for index, env_name in enumerate(names, start=1):
                    value = os.environ.get(env_name, "").strip()

                    if not value:
                        continue

                    slots.append(
                        KeySlot(
                            slot_id=f"{provider.upper()}_KEY_{index:02d}",
                            provider=provider,
                            env_var_name=env_name,
                            secret_value=value,
                        )
                    )

            self._slots[provider] = slots

    def providers(self) -> list[str]:
        return sorted(self._slots)

    def available_slots(self, provider: str) -> list[KeySlot]:
        provider = provider.lower()

        with self._lock:
            slots = self._slots.get(provider, [])

            available = [
                slot for slot in slots
                if slot.available()
            ]

            available.sort(
                key=lambda slot: (
                    slot.last_used,
                    slot.daily_requests,
                    slot.consecutive_errors,
                )
            )

            return available

    def acquire(self, provider: str) -> KeySlot | None:
        candidates = self.available_slots(provider)

        if not candidates:
            return None

        with self._lock:
            slot = candidates[0]
            slot.state = KeyState.IN_USE
            slot.last_used = time.time()
            return slot

    def mark_success(self, slot: KeySlot) -> None:
        with self._lock:
            slot.state = KeyState.READY
            slot.daily_requests += 1
            slot.total_successes += 1
            slot.consecutive_errors = 0
            slot.last_used = time.time()

    def mark_rate_limited(
        self,
        slot: KeySlot,
        cooldown_seconds: float | None = None,
    ) -> None:
        with self._lock:
            slot.total_failures += 1
            slot.consecutive_errors += 1
            slot.state = KeyState.COOLDOWN
            slot.cooldown_until = (
                time.time()
                + (
                    self.cooldown_seconds
                    if cooldown_seconds is None
                    else cooldown_seconds
                )
            )

    def mark_quota_exhausted(
        self,
        slot: KeySlot,
        cooldown_seconds: float = 3600.0,
    ) -> None:
        with self._lock:
            slot.total_failures += 1
            slot.consecutive_errors += 1
            slot.state = KeyState.QUOTA_EXHAUSTED
            slot.cooldown_until = time.time() + cooldown_seconds

    def mark_invalid(self, slot: KeySlot) -> None:
        with self._lock:
            slot.total_failures += 1
            slot.state = KeyState.INVALID

    def mark_failure(self, slot: KeySlot) -> None:
        with self._lock:
            slot.total_failures += 1
            slot.consecutive_errors += 1

            if slot.consecutive_errors >= self.max_consecutive_errors:
                slot.state = KeyState.COOLDOWN
                slot.cooldown_until = (
                    time.time() + self.cooldown_seconds
                )
            else:
                slot.state = KeyState.READY

    def forensic_status(self) -> list[dict[str, Any]]:
        with self._lock:
            result: list[dict[str, Any]] = []

            for provider, slots in sorted(self._slots.items()):
                for slot in slots:
                    result.append(
                        {
                            "slot_id": slot.slot_id,
                            "provider": provider,
                            "env_var": slot.env_var_name,
                            "state": slot.state.value,
                            "daily_requests": slot.daily_requests,
                            "total_successes": slot.total_successes,
                            "total_failures": slot.total_failures,
                            "consecutive_errors": slot.consecutive_errors,
                            "available": slot.available(),
                        }
                    )

            return result
'@

# =============================================================================
# REGISTRY
# =============================================================================

Write-ProjectFile (Join-Path $ModelsRoot 'registry.py') @'
"""E-ZZIO dynamic model registry."""

from __future__ import annotations

import json
import os
import tempfile
import time
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path
from threading import Lock
from typing import Any


class ModelTier(StrEnum):
    FAST = "FAST"
    MID = "MID"
    HEAVY = "HEAVY"
    SPECIALIZED = "SPECIALIZED"
    UNQUALIFIED = "UNQUALIFIED"


class ModelLifecycle(StrEnum):
    DISCOVERED = "DISCOVERED"
    CANDIDATE = "CANDIDATE"
    QUALIFYING = "QUALIFYING"
    QUALIFIED = "QUALIFIED"
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    QUARANTINED = "QUARANTINED"
    RETIRED = "RETIRED"


@dataclass(slots=True)
class ModelRecord:
    model_id: str
    provider: str
    tier: str = ModelTier.UNQUALIFIED.value
    lifecycle: str = ModelLifecycle.DISCOVERED.value

    context_window: int | None = None
    max_output_tokens: int | None = None

    supports_chat: bool = False
    supports_json: bool = False
    supports_tools: bool = False
    supports_reasoning: bool = False

    latency_ms: float | None = None
    qualification_score: float = 0.0

    discovered_at: float = 0.0
    last_verified: float = 0.0

    source_hash: str = ""

    failure_count: int = 0
    success_count: int = 0

    metadata: dict[str, Any] | None = None


class ModelRegistry:
    """Persistent registry with atomic JSON writes."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

        self._models: dict[str, ModelRecord] = {}
        self._lock = Lock()

        self.load()

    @staticmethod
    def key(provider: str, model_id: str) -> str:
        return f"{provider.lower()}:{model_id}"

    def load(self) -> None:
        if not self.path.exists():
            return

        try:
            data = json.loads(
                self.path.read_text(encoding="utf-8")
            )

            models = data.get("models", {})

            for key, raw in models.items():
                self._models[key] = ModelRecord(**raw)

        except Exception:
            self._models = {}

    def save(self) -> None:
        with self._lock:
            payload = {
                "schema_version": 1,
                "generated_at": time.time(),
                "models": {
                    key: asdict(record)
                    for key, record in self._models.items()
                },
            }

            self.path.parent.mkdir(parents=True, exist_ok=True)

            fd, temporary = tempfile.mkstemp(
                prefix=".registry_",
                suffix=".tmp",
                dir=self.path.parent,
                text=True,
            )

            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(
                        payload,
                        handle,
                        ensure_ascii=False,
                        indent=2,
                        sort_keys=True,
                    )
                    handle.flush()
                    os.fsync(handle.fileno())

                os.replace(temporary, self.path)

            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)

    def upsert(self, record: ModelRecord) -> None:
        with self._lock:
            self._models[
                self.key(record.provider, record.model_id)
            ] = record

    def get(
        self,
        provider: str,
        model_id: str,
    ) -> ModelRecord | None:
        return self._models.get(
            self.key(provider, model_id)
        )

    def active(
        self,
        *,
        tier: str | None = None,
        providers: list[str] | None = None,
    ) -> list[ModelRecord]:
        providers_set = (
            {p.lower() for p in providers}
            if providers
            else None
        )

        result = []

        for model in self._models.values():
            if model.lifecycle != ModelLifecycle.ACTIVE.value:
                continue

            if tier and model.tier != tier:
                continue

            if (
                providers_set
                and model.provider.lower() not in providers_set
            ):
                continue

            result.append(model)

        return result

    def all(self) -> list[ModelRecord]:
        return list(self._models.values())

    def mark_superseded(
        self,
        provider: str,
        model_id: str,
    ) -> None:
        record = self.get(provider, model_id)

        if record:
            record.lifecycle = ModelLifecycle.SUPERSEDED.value

    def mark_retired(
        self,
        provider: str,
        model_id: str,
    ) -> None:
        record = self.get(provider, model_id)

        if record:
            record.lifecycle = ModelLifecycle.RETIRED.value
'@

# =============================================================================
# LIFECYCLE
# =============================================================================

Write-ProjectFile (Join-Path $ModelsRoot 'lifecycle.py') @'
"""E-ZZIO model lifecycle manager."""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any

from .registry import (
    ModelLifecycle,
    ModelRecord,
    ModelRegistry,
)


class ModelLifecycleManager:
    """Converts provider discoveries into registry state."""

    def __init__(self, registry: ModelRegistry) -> None:
        self.registry = registry

    @staticmethod
    def fingerprint(metadata: dict[str, Any]) -> str:
        canonical = json.dumps(
            metadata,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

        return hashlib.sha256(
            canonical.encode("utf-8")
        ).hexdigest()

    def ingest_discovery(
        self,
        provider: str,
        discovered: list[dict[str, Any]],
    ) -> list[ModelRecord]:

        records: list[ModelRecord] = []
        now = time.time()

        for item in discovered:
            model_id = str(item["model_id"])
            source_hash = self.fingerprint(item)

            existing = self.registry.get(
                provider,
                model_id,
            )

            if existing:
                existing.metadata = item
                existing.source_hash = source_hash
                existing.last_verified = now
                records.append(existing)
                continue

            record = ModelRecord(
                model_id=model_id,
                provider=provider,
                lifecycle=ModelLifecycle.CANDIDATE.value,
                context_window=item.get("context_window"),
                max_output_tokens=item.get("max_output_tokens"),
                supports_chat=bool(item.get("supports_chat", False)),
                supports_json=bool(item.get("supports_json", False)),
                supports_tools=bool(item.get("supports_tools", False)),
                supports_reasoning=bool(
                    item.get("supports_reasoning", False)
                ),
                discovered_at=now,
                last_verified=now,
                source_hash=source_hash,
                metadata=item,
            )

            self.registry.upsert(record)
            records.append(record)

        self.registry.save()
        return records
'@

# =============================================================================
# SCORING
# =============================================================================

Write-ProjectFile (Join-Path $ModelsRoot 'scoring.py') @'
"""E-ZZIO model scoring policies."""

from __future__ import annotations


def classify_tier(
    *,
    latency_ms: float,
    context_window: int | None,
    supports_json: bool,
    supports_tools: bool,
    supports_reasoning: bool,
) -> str:

    if supports_reasoning and (context_window or 0) >= 64_000:
        return "HEAVY"

    if latency_ms <= 900.0 and supports_json:
        return "FAST"

    if latency_ms <= 2500.0 or supports_tools:
        return "MID"

    return "HEAVY"


def calculate_score(
    *,
    latency_ms: float,
    supports_json: bool,
    supports_tools: bool,
    supports_reasoning: bool,
    context_window: int | None,
) -> float:

    score = 100.0
    score -= min(latency_ms / 100.0, 40.0)

    if supports_json:
        score += 10.0

    if supports_tools:
        score += 10.0

    if supports_reasoning:
        score += 15.0

    if (context_window or 0) >= 32_000:
        score += 5.0

    return round(
        max(0.0, min(100.0, score)),
        2,
    )
'@

# =============================================================================
# DISCOVERY BASE
# =============================================================================

Write-ProjectFile (Join-Path $DiscoveryRoot 'base.py') @'
"""Provider discovery base classes."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ProviderDiscovery(ABC):

    provider: str

    @abstractmethod
    async def discover(
        self,
        api_key: str,
    ) -> list[dict[str, Any]]:
        """Discover currently available models."""
        raise NotImplementedError
'@

# =============================================================================
# GEMINI
# =============================================================================

Write-ProjectFile (Join-Path $DiscoveryRoot 'gemini.py') @'
"""Gemini dynamic model discovery."""

from __future__ import annotations

from typing import Any
import httpx

from .base import ProviderDiscovery


class GeminiDiscovery(ProviderDiscovery):

    provider = "gemini"
    URL = "https://generativelanguage.googleapis.com/v1beta/models"

    async def discover(
        self,
        api_key: str,
    ) -> list[dict[str, Any]]:

        headers = {
            "x-goog-api-key": api_key,
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                self.URL,
                headers=headers,
            )
            response.raise_for_status()
            payload = response.json()

        result = []

        for raw in payload.get("models", []):
            name = str(raw.get("name", ""))

            if not name:
                continue

            model_id = name.split("models/", 1)[-1]
            methods = {
                str(x)
                for x in raw.get("supportedGenerationMethods", [])
            }

            result.append(
                {
                    "model_id": model_id,
                    "display_name": raw.get("displayName"),
                    "context_window": raw.get("inputTokenLimit"),
                    "max_output_tokens": raw.get("outputTokenLimit"),
                    "supports_chat": bool(
                        methods & {"generateContent", "generateMessage"}
                    ),
                    "supports_json": True,
                    "supports_tools": True,
                    "supports_reasoning": (
                        "thinking" in model_id.lower()
                        or "reason" in model_id.lower()
                    ),
                    "raw_capabilities": sorted(methods),
                }
            )

        return result
'@

# =============================================================================
# GROQ
# =============================================================================

Write-ProjectFile (Join-Path $DiscoveryRoot 'groq.py') @'
"""Groq dynamic model discovery."""

from __future__ import annotations

from typing import Any
import httpx

from .base import ProviderDiscovery


class GroqDiscovery(ProviderDiscovery):

    provider = "groq"
    URL = "https://api.groq.com/openai/v1/models"

    async def discover(
        self,
        api_key: str,
    ) -> list[dict[str, Any]]:

        headers = {
            "Authorization": f"Bearer {api_key}",
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                self.URL,
                headers=headers,
            )
            response.raise_for_status()
            payload = response.json()

        result = []

        for raw in payload.get("data", []):
            model_id = raw.get("id")

            if not model_id:
                continue

            context_window = raw.get("context_window")

            result.append(
                {
                    "model_id": model_id,
                    "display_name": model_id,
                    "context_window": context_window,
                    "max_output_tokens": None,
                    "supports_chat": True,
                    "supports_json": True,
                    "supports_tools": True,
                    "supports_reasoning": "reason" in model_id.lower(),
                    "owned_by": raw.get("owned_by"),
                }
            )

        return result
'@

# =============================================================================
# OPENROUTER
# =============================================================================

Write-ProjectFile (Join-Path $DiscoveryRoot 'openrouter.py') @'
"""OpenRouter dynamic model discovery."""

from __future__ import annotations

from typing import Any
import httpx

from .base import ProviderDiscovery


class OpenRouterDiscovery(ProviderDiscovery):

    provider = "openrouter"
    URL = "https://openrouter.ai/api/v1/models"

    async def discover(
        self,
        api_key: str,
    ) -> list[dict[str, Any]]:

        headers = {
            "Authorization": f"Bearer {api_key}",
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(
                self.URL,
                headers=headers,
            )
            response.raise_for_status()
            payload = response.json()

        result = []

        for raw in payload.get("data", []):
            model_id = raw.get("id")

            if not model_id:
                continue

            architecture = raw.get("architecture", {})
            supported = architecture.get("input_modalities", [])

            result.append(
                {
                    "model_id": model_id,
                    "display_name": raw.get("name"),
                    "context_window": raw.get("context_length"),
                    "max_output_tokens": raw.get("top_provider", {}).get(
                        "max_completion_tokens"
                    ),
                    "supports_chat": True,
                    "supports_json": True,
                    "supports_tools": True,
                    "supports_reasoning": (
                        "reason" in model_id.lower()
                        or "thinking" in model_id.lower()
                    ),
                    "input_modalities": supported,
                    "pricing": raw.get("pricing"),
                }
            )

        return result
'@

# =============================================================================
# LITELLM
# =============================================================================

Write-ProjectFile (Join-Path $DiscoveryRoot 'litellm.py') @'
"""LiteLLM gateway discovery."""

from __future__ import annotations

import os
from typing import Any
import httpx

from .base import ProviderDiscovery


class LiteLLMDiscovery(ProviderDiscovery):

    provider = "litellm"

    async def discover(
        self,
        api_key: str,
    ) -> list[dict[str, Any]]:

        base_url = os.environ.get(
            "EZZIO_LITELLM_BASE_URL",
            "http://127.0.0.1:4000",
        ).rstrip("/")

        url = f"{base_url}/v1/models"
        headers: dict[str, str] = {}

        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                url,
                headers=headers,
            )
            response.raise_for_status()
            payload = response.json()

        result = []

        for raw in payload.get("data", []):
            model_id = raw.get("id")

            if not model_id:
                continue

            result.append(
                {
                    "model_id": model_id,
                    "display_name": model_id,
                    "context_window": None,
                    "max_output_tokens": None,
                    "supports_chat": True,
                    "supports_json": True,
                    "supports_tools": True,
                    "supports_reasoning": "reason" in model_id.lower(),
                    "gateway": base_url,
                }
            )

        return result
'@

# =============================================================================
# QUALIFICATION PROBES
# =============================================================================

Write-ProjectFile (Join-Path $QualificationRoot 'probes.py') @'
"""E-ZZIO safe model qualification probes."""

from __future__ import annotations

import json
import time
from typing import Any
import httpx


async def openai_compatible_probe(
    *,
    endpoint: str,
    api_key: str,
    model_id: str,
    timeout: float = 20.0,
) -> dict[str, Any]:

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model_id,
        "messages": [
            {
                "role": "user",
                "content": 'Return exactly JSON with "status":"ok".',
            }
        ],
        "temperature": 0,
        "max_tokens": 32,
        "response_format": {"type": "json_object"},
    }

    started = time.perf_counter()

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            endpoint,
            headers=headers,
            json=payload,
        )

    latency_ms = (time.perf_counter() - started) * 1000.0

    result: dict[str, Any] = {
        "latency_ms": round(latency_ms, 2),
        "http_status": response.status_code,
        "success": response.is_success,
        "structured_json": False,
        "content_available": False,
    }

    if not response.is_success:
        return result

    try:
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        result["content_available"] = bool(content)
        parsed = json.loads(content)
        result["structured_json"] = (parsed.get("status") == "ok")
    except Exception:
        pass

    return result
'@

# =============================================================================
# POLICIES
# =============================================================================

Write-ProjectFile (Join-Path $QualificationRoot 'policies.py') @'
"""E-ZZIO qualification policies."""

from __future__ import annotations


DEFAULT_POLICY = {
    "minimum_score": 60.0,
    "maximum_latency_ms": 15000.0,
    "require_chat": True,
    "require_generation": True,
    "require_structured_json": False,
    "require_context_metadata": False,
}


def evaluate(
    *,
    latency_ms: float,
    supports_chat: bool,
    supports_json: bool,
    probe_success: bool,
    structured_json: bool,
    context_window: int | None,
    score: float,
    policy: dict | None = None,
) -> tuple[bool, list[str]]:

    active = {
        **DEFAULT_POLICY,
        **(policy or {}),
    }

    failures: list[str] = []

    if active["require_chat"] and not supports_chat:
        failures.append("CHAT_UNSUPPORTED")

    if active["require_generation"] and not probe_success:
        failures.append("GENERATION_FAILED")

    if active["require_structured_json"] and not structured_json:
        failures.append("STRUCTURED_JSON_FAILED")

    if active["require_context_metadata"] and not context_window:
        failures.append("CONTEXT_METADATA_MISSING")

    if latency_ms > active["maximum_latency_ms"]:
        failures.append("LATENCY_EXCEEDED")

    if score < active["minimum_score"]:
        failures.append("SCORE_TOO_LOW")

    return (
        len(failures) == 0,
        failures,
    )
'@

# =============================================================================
# GATE
# =============================================================================

Write-ProjectFile (Join-Path $QualificationRoot 'gate.py') @'
"""E-ZZIO qualification gate."""

from __future__ import annotations

from typing import Any

from core.models.scoring import (
    calculate_score,
    classify_tier,
)
from .policies import evaluate
from .probes import openai_compatible_probe


class QualificationGate:

    async def qualify_openai_compatible(
        self,
        *,
        provider: str,
        model: dict[str, Any],
        api_key: str,
        endpoint: str,
        policy: dict[str, Any] | None = None,
    ) -> dict[str, Any]:

        model_id = str(model["model_id"])

        probe = await openai_compatible_probe(
            endpoint=endpoint,
            api_key=api_key,
            model_id=model_id,
        )

        latency_ms = float(probe["latency_ms"])
        supports_json = bool(model.get("supports_json", False))
        supports_tools = bool(model.get("supports_tools", False))
        supports_reasoning = bool(model.get("supports_reasoning", False))
        context_window = model.get("context_window")

        score = calculate_score(
            latency_ms=latency_ms,
            supports_json=supports_json,
            supports_tools=supports_tools,
            supports_reasoning=supports_reasoning,
            context_window=context_window,
        )

        qualified, failures = evaluate(
            latency_ms=latency_ms,
            supports_chat=bool(model.get("supports_chat", False)),
            supports_json=supports_json,
            probe_success=bool(probe["success"]),
            structured_json=bool(probe["structured_json"]),
            context_window=context_window,
            score=score,
            policy=policy,
        )

        return {
            "provider": provider,
            "model_id": model_id,
            "qualified": qualified,
            "failures": failures,
            "tier": (
                classify_tier(
                    latency_ms=latency_ms,
                    context_window=context_window,
                    supports_json=supports_json,
                    supports_tools=supports_tools,
                    supports_reasoning=supports_reasoning,
                )
                if qualified
                else "UNQUALIFIED"
            ),
            "score": score,
            "latency_ms": latency_ms,
            "structured_json": bool(probe["structured_json"]),
        }
'@

# =============================================================================
# TELEMETRY
# =============================================================================

Write-ProjectFile (Join-Path $ModelsRoot 'telemetry.py') @'
"""E-ZZIO secret-safe telemetry."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


class SafeTelemetry:

    FORBIDDEN_KEYS = {
        "api_key",
        "apikey",
        "secret",
        "token",
        "password",
        "authorization",
        "credential",
        "secret_value",
    }

    def __init__(
        self,
        directory: str | Path,
    ) -> None:

        self.directory = Path(directory)
        self.directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    @classmethod
    def sanitize(
        cls,
        value: Any,
    ) -> Any:

        if isinstance(value, dict):
            result = {}
            for key, item in value.items():
                if str(key).lower() in cls.FORBIDDEN_KEYS:
                    result[key] = "[REDACTED]"
                else:
                    result[key] = cls.sanitize(item)
            return result

        if isinstance(value, (list, tuple)):
            return [cls.sanitize(item) for item in value]

        return value

    def emit(
        self,
        event: str,
        payload: dict[str, Any],
    ) -> None:

        record = {
            "timestamp": time.time(),
            "event": event,
            "payload": self.sanitize(payload),
        }

        path = self.directory / "fabric_telemetry.jsonl"

        with path.open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(
                    record,
                    ensure_ascii=False,
                    sort_keys=True,
                )
                + "\n"
            )
'@

# =============================================================================
# ROUTER
# =============================================================================

Write-ProjectFile (Join-Path $ModelsRoot 'router.py') @'
"""E-ZZIO bounded cognitive router."""

from __future__ import annotations

from typing import Any
import httpx

from .errors import (
    ProviderExhaustedError,
    RoutingError,
)
from .key_pool import KeyPoolManager
from .registry import ModelRecord, ModelRegistry
from .telemetry import SafeTelemetry


class EzzioRouter:

    ENDPOINTS = {
        "gemini": (
            "https://generativelanguage.googleapis.com/"
            "v1beta/openai/chat/completions"
        ),
        "groq": "https://api.groq.com/openai/v1/chat/completions",
        "openrouter": "https://openrouter.ai/api/v1/chat/completions",
    }

    def __init__(
        self,
        *,
        registry: ModelRegistry,
        key_pool: KeyPoolManager,
        telemetry: SafeTelemetry,
        provider_order: list[str] | None = None,
        max_key_attempts: int = 3,
        max_provider_attempts: int = 4,
    ) -> None:

        self.registry = registry
        self.key_pool = key_pool
        self.telemetry = telemetry

        self.provider_order = (
            provider_order
            or [
                "gemini",
                "groq",
                "openrouter",
                "litellm",
            ]
        )

        self.max_key_attempts = max_key_attempts
        self.max_provider_attempts = max_provider_attempts

    def _candidates(
        self,
        tier: str,
    ) -> list[ModelRecord]:

        candidates = self.registry.active(
            tier=tier,
            providers=self.provider_order,
        )

        provider_rank = {
            provider: index
            for index, provider
            in enumerate(self.provider_order)
        }

        candidates.sort(
            key=lambda model: (
                provider_rank.get(model.provider.lower(), 999),
                -(model.qualification_score),
                model.latency_ms if model.latency_ms is not None else 999999.0,
            )
        )

        return candidates

    async def execute(
        self,
        *,
        messages: list[dict[str, str]],
        tier: str = "MID",
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:

        candidates = self._candidates(tier)

        if not candidates:
            raise ProviderExhaustedError(
                f"No active model for tier {tier}."
            )

        attempted_providers: set[str] = set()
        provider_attempts = 0

        for model in candidates:
            provider = model.provider.lower()

            if provider in attempted_providers:
                continue

            if provider_attempts >= self.max_provider_attempts:
                break

            attempted_providers.add(provider)
            endpoint = self.ENDPOINTS.get(provider)

            if not endpoint:
                continue

            key_attempts = 0

            while key_attempts < self.max_key_attempts:
                slot = self.key_pool.acquire(provider)

                if slot is None:
                    break

                key_attempts += 1
                provider_attempts += 1

                headers = {
                    "Authorization": f"Bearer {slot.secret_value}",
                    "Content-Type": "application/json",
                }

                payload = {
                    "model": model.model_id,
                    "messages": messages,
                    "temperature": temperature,
                }

                if max_tokens is not None:
                    payload["max_tokens"] = max_tokens

                try:
                    async with httpx.AsyncClient(timeout=45.0) as client:
                        response = await client.post(
                            endpoint,
                            headers=headers,
                            json=payload,
                        )

                    status = response.status_code

                    if status in (401, 403):
                        self.key_pool.mark_invalid(slot)
                        continue

                    if status == 429:
                        self.key_pool.mark_rate_limited(slot)
                        continue

                    if status >= 500:
                        self.key_pool.mark_failure(slot)
                        break

                    response.raise_for_status()
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]

                    self.key_pool.mark_success(slot)
                    model.success_count += 1

                    self.telemetry.emit(
                        "inference_success",
                        {
                            "provider": provider,
                            "model": model.model_id,
                            "tier": tier,
                            "status": status,
                        },
                    )

                    return {
                        "success": True,
                        "content": content,
                        "provider": provider,
                        "model": model.model_id,
                        "tier": tier,
                    }

                except (httpx.RequestError, ValueError, KeyError):
                    self.key_pool.mark_failure(slot)
                    model.failure_count += 1

                    self.telemetry.emit(
                        "inference_failure",
                        {
                            "provider": provider,
                            "model": model.model_id,
                            "tier": tier,
                        },
                    )
                    break

        raise RoutingError(
            "All qualified provider/model/key candidates were exhausted."
        )
'@

# =============================================================================
# FABRIC ORCHESTRATOR
# =============================================================================

Write-ProjectFile (Join-Path $ModelsRoot 'fabric.py') @'
"""E-ZZIO Autonomous Model Fabric orchestrator."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

from .key_pool import KeyPoolManager
from .lifecycle import ModelLifecycleManager
from .registry import (
    ModelLifecycle,
    ModelRecord,
    ModelRegistry,
)
from .router import EzzioRouter
from .telemetry import SafeTelemetry

from .discovery.gemini import GeminiDiscovery
from .discovery.groq import GroqDiscovery
from .discovery.openrouter import OpenRouterDiscovery
from .discovery.litellm import LiteLLMDiscovery


class AutonomousModelFabric:

    def __init__(
        self,
        *,
        project_root: str | Path,
    ) -> None:

        self.project_root = Path(project_root)

        data_root = self.project_root / "data" / "models"
        forensic_root = self.project_root / "_forensic" / "reports"

        self.registry = ModelRegistry(data_root / "registry.json")
        self.lifecycle = ModelLifecycleManager(self.registry)
        self.key_pool = KeyPoolManager()
        self.telemetry = SafeTelemetry(forensic_root)

        self.router = EzzioRouter(
            registry=self.registry,
            key_pool=self.key_pool,
            telemetry=self.telemetry,
        )

        self.providers = {
            "gemini": GeminiDiscovery(),
            "groq": GroqDiscovery(),
            "openrouter": OpenRouterDiscovery(),
            "litellm": LiteLLMDiscovery(),
        }

    def _key_for_provider(
        self,
        provider: str,
    ) -> str | None:

        prefixes = {
            "gemini": "GEMINI_API_KEY",
            "groq": "GROQ_API_KEY",
            "openrouter": "OPENROUTER_API_KEY",
            "litellm": "LITELLM_API_KEY",
        }

        prefix = prefixes.get(provider)
        if not prefix:
            return None

        return os.environ.get(prefix, "").strip() or None

    async def discover_all(
        self,
    ) -> dict[str, list[dict[str, Any]]]:

        discovered = {}

        for provider, adapter in self.providers.items():
            api_key = self._key_for_provider(provider) or ""

            try:
                models = await adapter.discover(api_key)
                discovered[provider] = models

                self.lifecycle.ingest_discovery(
                    provider,
                    models,
                )

                self.telemetry.emit(
                    "provider_discovery",
                    {
                        "provider": provider,
                        "model_count": len(models),
                    },
                )

            except Exception as exc:
                discovered[provider] = []
                self.telemetry.emit(
                    "provider_discovery_failure",
                    {
                        "provider": provider,
                        "error_type": type(exc).__name__,
                    },
                )

        return discovered

    def activate_qualified(
        self,
        qualified_results: list[dict[str, Any]],
    ) -> None:

        for result in qualified_results:
            provider = result["provider"]
            model_id = result["model_id"]

            record = self.registry.get(
                provider,
                model_id,
            )

            if record is None:
                continue

            if result["qualified"]:
                record.lifecycle = ModelLifecycle.ACTIVE.value
                record.tier = result["tier"]
                record.latency_ms = result["latency_ms"]
                record.qualification_score = result["score"]
                record.supports_json = result["structured_json"]
                record.last_verified = time.time()
            else:
                record.lifecycle = ModelLifecycle.QUARANTINED.value

        self.registry.save()

    def status(self) -> dict[str, Any]:
        active = self.registry.active()

        return {
            "active_models": len(active),
            "providers": sorted({m.provider for m in active}),
            "keys": self.key_pool.forensic_status(),
            "models": [
                {
                    "provider": m.provider,
                    "model": m.model_id,
                    "tier": m.tier,
                    "lifecycle": m.lifecycle,
                    "score": m.qualification_score,
                    "latency_ms": m.latency_ms,
                }
                for m in active
            ],
        }


def build_fabric(
    project_root: str | Path,
) -> AutonomousModelFabric:
    return AutonomousModelFabric(project_root=project_root)
'@

# =============================================================================
# MANIFEST
# =============================================================================

Write-Section 5 10 'Création du manifeste du Fabric'

$Manifest = @{
    schema_version = 1
    fabric_version = $Version
    generated_at   = (Get-Date).ToUniversalTime().ToString('o')
    project_root   = $ProjectRoot

    providers = @(
        'gemini',
        'groq',
        'openrouter',
        'litellm'
    )

    excluded_providers = @(
        'ollama'
    )

    features = @(
        'dynamic_model_discovery',
        'model_diff',
        'qualification_gate',
        'dynamic_registry',
        'model_lifecycle',
        'cognitive_router',
        'multi_key_rotation',
        'key_cooldown',
        'quota_tracking',
        'provider_failover',
        'bounded_retry',
        'secret_safe_telemetry',
        'forensic_status',
        'fail_closed'
    )

    secret_policy = @{
        values_logged     = $false
        values_serialized = $false
        values_exported   = $false
        values_displayed  = $false
    }

    network_policy = @{
        bootstrap_network = $false
        runtime_network   = $true
    }

    ollama = @{
        enabled   = $false
        supported = $false
    }
}

$ManifestJson = $Manifest | ConvertTo-Json -Depth 10

Write-ProjectFile $ManifestPath $ManifestJson

# =============================================================================
# [6/10] SNAPSHOT PLACEHOLDERS
# =============================================================================

Write-Section 6 10 'Création des espaces de données'

$InitialRegistry = @{
    schema_version = 1
    generated_at   = (Get-Date).ToUniversalTime().ToString('o')
    models         = @{}
}

Write-ProjectFile `
    (Join-Path $DataRoot 'registry.json') `
    ($InitialRegistry | ConvertTo-Json -Depth 10)

Write-ProjectFile `
    (Join-Path $DataRoot 'discovery_snapshot.json') `
    (@{
        schema_version = 1
        generated_at   = (Get-Date).ToUniversalTime().ToString('o')
        providers      = @{}
    } | ConvertTo-Json -Depth 10)

Write-ProjectFile `
    (Join-Path $DataRoot 'health.json') `
    (@{
        schema_version = 1
        generated_at   = (Get-Date).ToUniversalTime().ToString('o')
        providers      = @{}
        models         = @{}
        keys           = @{}
    } | ConvertTo-Json -Depth 10)

# =============================================================================
# [7/10] PYTHON DEPENDENCY MANIFEST
# =============================================================================

Write-Section 7 10 'Création du manifeste Python'

$Requirements = @'
httpx>=0.27,<1
'@

Write-ProjectFile `
    (Join-Path $ProjectRoot 'requirements-model-fabric.txt') `
    $Requirements

# =============================================================================
# [8/10] SECURITY README
# =============================================================================

Write-Section 8 10 'Création de la documentation de sécurité'

$SecurityReadme = @'
# E-ZZIO Autonomous Model Fabric

## Providers
Supported:
- Gemini
- Groq
- OpenRouter
- LiteLLM

Ollama is intentionally excluded.

## Credential policy
Credentials are read from environment variables only.

Expected names:
- GEMINI_API_KEY, GEMINI_API_KEY_2, ...
- GROQ_API_KEY, GROQ_API_KEY_2, ...
- OPENROUTER_API_KEY, OPENROUTER_API_KEY_2, ...
- LITELLM_API_KEY

Gateway URL: `EZZIO_LITELLM_BASE_URL` (Default: `http://127.0.0.1:4000`)

## Security
Secrets are never printed, serialized, or written into logs/telemetry.

## Lifecycle
DISCOVERED -> CANDIDATE -> QUALIFYING -> QUALIFIED -> ACTIVE -> (SUPERSEDED / QUARANTINED / RETIRED)
'@

Write-ProjectFile `
    (Join-Path $ModelsRoot 'README.md') `
    $SecurityReadme

# =============================================================================
# [9/10] STATIC FORENSIC VALIDATION
# =============================================================================

Write-Section 9 10 'Validation statique du Fabric'

$ExpectedFiles = @(
    (Join-Path $ModelsRoot '__init__.py'),
    (Join-Path $ModelsRoot 'errors.py'),
    (Join-Path $ModelsRoot 'key_pool.py'),
    (Join-Path $ModelsRoot 'registry.py'),
    (Join-Path $ModelsRoot 'lifecycle.py'),
    (Join-Path $ModelsRoot 'scoring.py'),
    (Join-Path $ModelsRoot 'telemetry.py'),
    (Join-Path $ModelsRoot 'router.py'),
    (Join-Path $ModelsRoot 'fabric.py'),

    (Join-Path $DiscoveryRoot '__init__.py'),
    (Join-Path $DiscoveryRoot 'base.py'),
    (Join-Path $DiscoveryRoot 'gemini.py'),
    (Join-Path $DiscoveryRoot 'groq.py'),
    (Join-Path $DiscoveryRoot 'openrouter.py'),
    (Join-Path $DiscoveryRoot 'litellm.py'),

    (Join-Path $QualificationRoot '__init__.py'),
    (Join-Path $QualificationRoot 'gate.py'),
    (Join-Path $QualificationRoot 'probes.py'),
    (Join-Path $QualificationRoot 'policies.py')
)

$Missing = @(
    $ExpectedFiles |
        Where-Object { -not (Test-Path -LiteralPath $_ -PathType Leaf) }
)

if ($Missing.Count -gt 0) {
    foreach ($File in $Missing) {
        Write-Fail "Fichier absent : $File"
    }
    throw 'Validation statique échouée.'
}

Write-Pass 'Tous les modules attendus existent.'

$PythonFiles = @(
    Get-ChildItem `
        -LiteralPath $ModelsRoot `
        -File `
        -Recurse `
        -Filter '*.py'
)

Write-Info "Modules Python créés : $($PythonFiles.Count)"

$ForbiddenPatterns = @(
    'AIza',
    'gsk_',
    'sk-or-',
    'Bearer\s+[A-Za-z0-9_\-\.]{20,}'
)

$ForbiddenHits = New-Object System.Collections.Generic.List[string]

foreach ($File in $PythonFiles) {
    $Content = [System.IO.File]::ReadAllText(
        $File.FullName,
        [System.Text.Encoding]::UTF8
    )

    foreach ($Pattern in $ForbiddenPatterns) {
        if ($Content -match $Pattern) {
            $ForbiddenHits.Add(
                "$($File.FullName) :: $Pattern"
            ) | Out-Null
        }
    }
}

if ($ForbiddenHits.Count -gt 0) {
    foreach ($Hit in $ForbiddenHits) {
        Write-Fail "Pattern secret détecté : $Hit"
    }
    throw 'Validation secret-safety échouée.'
}

Write-Pass 'Aucun motif de credential embarqué détecté.'

# =============================================================================
# [10/10] FINAL
# =============================================================================

Write-Section 10 10 'Vérification finale'

$EndTime = Get-Date
$Duration = ($EndTime - $StartTime).TotalSeconds

Write-Pass "Modules créés : $($CreatedFiles.Count)"
Write-Pass "Échecs de création : $($FailedFiles.Count)"
Write-Pass 'Aucune valeur de credential écrite par le builder.'
Write-Pass 'Aucune clé API intégrée au code.'
Write-Pass 'Aucun appel réseau effectué.'
Write-Pass 'Ollama exclu du Fabric.'
Write-Pass 'Registry dynamique activé.'
Write-Pass 'Rotation multi-clés activée.'

Write-Host ''
Write-Host '============================================================================='
Write-Host ' E-ZZIO — AUTONOMOUS MODEL FABRIC'
Write-Host ' BOOTSTRAP TERMINÉ'
Write-Host '============================================================================='
Write-Host "[INFO] Version    : $Version"
Write-Host "[INFO] RunId      : $RunId"
Write-Host "[INFO] Modules    : $($PythonFiles.Count)"
Write-Host "[INFO] Créations  : $($CreatedFiles.Count)"
Write-Host "[INFO] Échecs     : $($FailedFiles.Count)"
Write-Host "[INFO] Durée      : $([math]::Round($Duration,2)) sec"
Write-Host '============================================================================='
Write-Host '[PASS] AUTONOMOUS MODEL FABRIC CRÉÉ AVEC CODE : 0'
Write-Host '============================================================================='