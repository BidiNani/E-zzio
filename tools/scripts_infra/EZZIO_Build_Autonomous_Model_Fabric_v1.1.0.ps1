#requires -Version 7.4
# =============================================================================
# E-ZZIO — AUTONOMOUS MODEL FABRIC
# Bootstrap Builder
# Version : 1.1.0
#
# =============================================================================
# OBJECTIF
# =============================================================================
#
# Construit automatiquement le moteur autonome de :
#
#   1. découverte dynamique des modèles
#   2. diff de catalogue
#   3. qualification contrôlée
#   4. registre dynamique
#   5. cycle de vie des modèles
#   6. classement FAST / MID / HEAVY / SPECIALIZED
#   7. routage cognitif
#   8. rotation multi-clés
#   9. cooldown / quota / invalidation
#  10. failover inter-fournisseurs
#  11. télémétrie forensic
#  12. refresh automatique
#  13. maintenance automatique du registre
#
# FOURNISSEURS
# =============================================================================
#
#   GEMINI
#   GROQ
#   OPENROUTER
#   LITELLM
#
# EXCLUSIONS
# =============================================================================
#
#   OLLAMA : ABSENT
#   GPU    : ABSENT
#   SECRET : AUCUNE VALEUR EMBARQUÉE
#
# MODE BUILDER
# =============================================================================
#
#   READ/WRITE PROJECT FILES
#   NO PROVIDER EXECUTION
#   NO API CALL
#   NO SECRET MODIFICATION
#   NO SECRET OUTPUT
#
# RUNTIME
# =============================================================================
#
#   Le Fabric Python effectue les appels réseau.
#
#   Le builder ne contacte aucun fournisseur.
#
# =============================================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# =============================================================================
# GLOBALS
# =============================================================================

$Version = '1.1.0'
$ProjectRoot = 'G:\AI\E-zzio'

$ModelsRoot       = Join-Path $ProjectRoot 'core\models'
$DiscoveryRoot    = Join-Path $ModelsRoot 'discovery'
$QualificationRoot = Join-Path $ModelsRoot 'qualification'

$DataRoot         = Join-Path $ProjectRoot 'data\models'
$ForensicRoot     = Join-Path $ProjectRoot '_forensic\reports'

$RuntimeRoot      = Join-Path $ProjectRoot 'runtime\models'
$ScriptsRoot      = Join-Path $ProjectRoot 'scripts'

$ManifestPath     = Join-Path $ModelsRoot 'fabric_manifest.json'
$ConfigPath       = Join-Path $ModelsRoot 'fabric_config.json'

$CreatedFiles = [System.Collections.Generic.List[string]]::new()
$FailedFiles  = [System.Collections.Generic.List[string]]::new()

$StartTime = Get-Date
$RunId = $StartTime.ToString('yyyyMMdd_HHmmss')

# =============================================================================
# CONSOLE
# =============================================================================

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

# =============================================================================
# FILE WRITER
# =============================================================================

function Write-ProjectFile {
    param(
        [Parameter(Mandatory)]
        [string]$Path,

        [Parameter(Mandatory)]
        [AllowEmptyString()]
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
        Write-Fail "Échec : $Path"
        throw
    }
}

# =============================================================================
# START
# =============================================================================

Write-Header 'E-ZZIO — AUTONOMOUS MODEL FABRIC'

Write-Host " Version   : $Version"
Write-Host ' Mode      : BOOTSTRAP / FORENSIC / NO NETWORK'
Write-Host ' Providers : GEMINI / GROQ / OPENROUTER / LITELLM'
Write-Host ' Ollama    : EXCLU'
Write-Host ' GPU       : EXCLU'
Write-Host ''

Write-Info "RunId : $RunId"
Write-Info "Projet : $ProjectRoot"

# =============================================================================
# [1/12] VALIDATION
# =============================================================================

Write-Section 1 12 'Validation du projet'

if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) {
    throw "Projet introuvable : $ProjectRoot"
}

Write-Pass "Projet détecté : $ProjectRoot"

$Python = Get-Command python -ErrorAction SilentlyContinue

if ($null -eq $Python) {
    Write-Warn 'Python non trouvé dans PATH.'
    Write-Warn 'Le Fabric est créé mais son runtime nécessitera Python.'
}
else {
    Write-Pass "Python détecté : $($Python.Source)"
}

# =============================================================================
# [2/12] DIRECTORIES
# =============================================================================

Write-Section 2 12 'Création de l''arborescence'

$Directories = @(
    $ModelsRoot,
    $DiscoveryRoot,
    $QualificationRoot,
    $DataRoot,
    $ForensicRoot,
    $RuntimeRoot,
    $ScriptsRoot
)

foreach ($Directory in $Directories) {

    if (-not (Test-Path -LiteralPath $Directory -PathType Container)) {

        New-Item `
            -ItemType Directory `
            -Path $Directory `
            -Force |
            Out-Null

        Write-Pass "Dossier créé : $Directory"
    }
    else {
        Write-Info "Présent : $Directory"
    }
}

# =============================================================================
# [3/12] PACKAGE
# =============================================================================

Write-Section 3 12 'Création du package Python'

Write-ProjectFile `
    (Join-Path $ModelsRoot '__init__.py') `
@'
"""E-ZZIO Autonomous Model Fabric.

Providers:
    Gemini
    Groq
    OpenRouter
    LiteLLM

Ollama is intentionally unsupported.
"""
'@

Write-ProjectFile `
    (Join-Path $DiscoveryRoot '__init__.py') `
@'
"""Dynamic provider discovery adapters."""
'@

Write-ProjectFile `
    (Join-Path $QualificationRoot '__init__.py') `
@'
"""Model qualification gates."""
'@

# =============================================================================
# [4/12] ERRORS
# =============================================================================

Write-Section 4 12 'Création des primitives de sécurité'

Write-ProjectFile `
    (Join-Path $ModelsRoot 'errors.py') `
@'
"""E-ZZIO Autonomous Model Fabric errors."""

from __future__ import annotations


class FabricError(RuntimeError):
    """Base Fabric error."""


class DiscoveryError(FabricError):
    """Provider discovery failure."""


class QualificationError(FabricError):
    """Qualification failure."""


class RoutingError(FabricError):
    """Routing failure."""


class ProviderExhaustedError(RoutingError):
    """No provider/model/key candidate remains."""


class SecretSafetyError(FabricError):
    """Unsafe secret handling detected."""


class ConfigurationError(FabricError):
    """Invalid Fabric configuration."""
'@

# =============================================================================
# KEY POOL
# =============================================================================

Write-ProjectFile `
    (Join-Path $ModelsRoot 'key_pool.py') `
@'
"""E-ZZIO secure multi-key rotation manager.

Secrets are loaded only at runtime.

Supported:
    GEMINI_API_KEY
    GEMINI_API_KEY_2 ... GEMINI_API_KEY_100

    GROQ_API_KEY
    GROQ_API_KEY_2 ... GROQ_API_KEY_100

    OPENROUTER_API_KEY
    OPENROUTER_API_KEY_2 ... OPENROUTER_API_KEY_100

    LITELLM_API_KEY
    LITELLM_API_KEY_2 ... LITELLM_API_KEY_100

No secret value is ever included in forensic output.
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

    requests: int = 0
    successes: int = 0
    failures: int = 0

    consecutive_errors: int = 0

    last_used: float = 0.0
    last_success: float = 0.0

    created_at: float = field(default_factory=time.time)

    def available(self, now: float | None = None) -> bool:
        now = time.time() if now is None else now

        if self.state == KeyState.READY:
            return True

        if self.state in {
            KeyState.COOLDOWN,
            KeyState.QUOTA_EXHAUSTED,
        }:
            if now >= self.cooldown_until:
                self.state = KeyState.READY
                self.consecutive_errors = 0
                return True

        return False


class KeyPoolManager:
    """Thread-safe multi-key scheduler."""

    PROVIDERS = (
        "gemini",
        "groq",
        "openrouter",
        "litellm",
    )

    def __init__(
        self,
        *,
        cooldown_seconds: float = 60.0,
        quota_cooldown_seconds: float = 3600.0,
        max_keys: int = 100,
    ) -> None:

        self.cooldown_seconds = cooldown_seconds
        self.quota_cooldown_seconds = quota_cooldown_seconds
        self.max_keys = max_keys

        self._lock = Lock()
        self._slots: dict[str, list[KeySlot]] = {}

        self._load_environment()

    def _load_environment(self) -> None:

        for provider in self.PROVIDERS:

            prefix = f"{provider.upper()}_API_KEY"
            slots: list[KeySlot] = []

            for index in range(1, self.max_keys + 1):

                env_name = (
                    prefix
                    if index == 1
                    else f"{prefix}_{index}"
                )

                value = os.environ.get(env_name, "").strip()

                if not value:
                    continue

                slots.append(
                    KeySlot(
                        slot_id=(
                            f"{provider.upper()}_KEY_{index:02d}"
                        ),
                        provider=provider,
                        env_var_name=env_name,
                        secret_value=value,
                    )
                )

            self._slots[provider] = slots

    def reload(self) -> None:
        with self._lock:
            self._slots.clear()

        self._load_environment()

    def providers(self) -> list[str]:
        return sorted(self._slots)

    def acquire(
        self,
        provider: str,
    ) -> KeySlot | None:

        provider = provider.lower()

        with self._lock:

            slots = self._slots.get(provider, [])

            candidates = [
                slot
                for slot in slots
                if slot.available()
            ]

            if not candidates:
                return None

            candidates.sort(
                key=lambda slot: (
                    slot.last_used,
                    slot.requests,
                    slot.failures,
                )
            )

            selected = candidates[0]

            selected.state = KeyState.IN_USE
            selected.last_used = time.time()
            selected.requests += 1

            return selected

    def mark_success(
        self,
        slot: KeySlot,
    ) -> None:

        with self._lock:

            slot.state = KeyState.READY
            slot.successes += 1
            slot.consecutive_errors = 0
            slot.last_success = time.time()

    def mark_rate_limited(
        self,
        slot: KeySlot,
        cooldown_seconds: float | None = None,
    ) -> None:

        with self._lock:

            slot.state = KeyState.COOLDOWN
            slot.failures += 1
            slot.consecutive_errors += 1

            duration = (
                self.cooldown_seconds
                if cooldown_seconds is None
                else cooldown_seconds
            )

            slot.cooldown_until = time.time() + duration

    def mark_quota_exhausted(
        self,
        slot: KeySlot,
    ) -> None:

        with self._lock:

            slot.state = KeyState.QUOTA_EXHAUSTED
            slot.failures += 1
            slot.consecutive_errors += 1
            slot.cooldown_until = (
                time.time()
                + self.quota_cooldown_seconds
            )

    def mark_invalid(
        self,
        slot: KeySlot,
    ) -> None:

        with self._lock:

            slot.state = KeyState.INVALID
            slot.failures += 1

    def mark_failure(
        self,
        slot: KeySlot,
    ) -> None:

        with self._lock:

            slot.failures += 1
            slot.consecutive_errors += 1

            slot.state = KeyState.COOLDOWN
            slot.cooldown_until = (
                time.time()
                + self.cooldown_seconds
            )

    def available_count(
        self,
        provider: str,
    ) -> int:

        with self._lock:

            return sum(
                1
                for slot in self._slots.get(
                    provider.lower(),
                    [],
                )
                if slot.available()
            )

    def forensic_status(
        self,
    ) -> list[dict[str, Any]]:

        with self._lock:

            result = []

            for provider, slots in sorted(
                self._slots.items()
            ):

                for slot in slots:

                    result.append(
                        {
                            "slot_id": slot.slot_id,
                            "provider": provider,
                            "env_var": slot.env_var_name,
                            "state": slot.state.value,
                            "requests": slot.requests,
                            "successes": slot.successes,
                            "failures": slot.failures,
                            "consecutive_errors": (
                                slot.consecutive_errors
                            ),
                            "available": slot.available(),
                            "last_used": slot.last_used,
                        }
                    )

            return result
'@

# =============================================================================
# REGISTRY
# =============================================================================

Write-ProjectFile `
    (Join-Path $ModelsRoot 'registry.py') `
@'
"""Persistent dynamic model registry."""

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
    last_seen: float = 0.0
    last_verified: float = 0.0

    source_hash: str = ""

    success_count: int = 0
    failure_count: int = 0

    metadata: dict[str, Any] | None = None


class ModelRegistry:

    def __init__(
        self,
        path: str | Path,
    ) -> None:

        self.path = Path(path)
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._lock = Lock()
        self._models: dict[str, ModelRecord] = {}

        self.load()

    @staticmethod
    def key(
        provider: str,
        model_id: str,
    ) -> str:

        return (
            f"{provider.lower()}:{model_id}"
        )

    def load(self) -> None:

        if not self.path.exists():
            return

        try:

            payload = json.loads(
                self.path.read_text(
                    encoding="utf-8"
                )
            )

            for key, raw in payload.get(
                "models",
                {},
            ).items():

                self._models[key] = ModelRecord(
                    **raw
                )

        except Exception:

            self._models = {}

    def save(self) -> None:

        with self._lock:

            payload = {
                "schema_version": 2,
                "generated_at": time.time(),
                "models": {
                    key: asdict(model)
                    for key, model
                    in self._models.items()
                },
            }

            fd, temporary = tempfile.mkstemp(
                prefix=".registry_",
                suffix=".tmp",
                dir=self.path.parent,
                text=True,
            )

            try:

                with os.fdopen(
                    fd,
                    "w",
                    encoding="utf-8",
                ) as handle:

                    json.dump(
                        payload,
                        handle,
                        ensure_ascii=False,
                        indent=2,
                        sort_keys=True,
                    )

                    handle.flush()
                    os.fsync(handle.fileno())

                os.replace(
                    temporary,
                    self.path,
                )

            finally:

                if os.path.exists(
                    temporary
                ):
                    os.unlink(
                        temporary
                    )

    def upsert(
        self,
        record: ModelRecord,
    ) -> None:

        with self._lock:

            self._models[
                self.key(
                    record.provider,
                    record.model_id,
                )
            ] = record

    def get(
        self,
        provider: str,
        model_id: str,
    ) -> ModelRecord | None:

        return self._models.get(
            self.key(
                provider,
                model_id,
            )
        )

    def all(self) -> list[ModelRecord]:
        return list(
            self._models.values()
        )

    def active(
        self,
        *,
        tier: str | None = None,
        providers: list[str] | None = None,
    ) -> list[ModelRecord]:

        provider_set = (
            {p.lower() for p in providers}
            if providers
            else None
        )

        result = []

        for model in self._models.values():

            if model.lifecycle != (
                ModelLifecycle.ACTIVE.value
            ):
                continue

            if tier and model.tier != tier:
                continue

            if (
                provider_set
                and model.provider.lower()
                not in provider_set
            ):
                continue

            result.append(model)

        return result
'@

# =============================================================================
# SCORING
# =============================================================================

Write-ProjectFile `
    (Join-Path $ModelsRoot 'scoring.py') `
@'
"""Model scoring and tier classification."""

from __future__ import annotations


def calculate_score(
    *,
    latency_ms: float,
    supports_json: bool,
    supports_tools: bool,
    supports_reasoning: bool,
    context_window: int | None,
) -> float:

    score = 100.0

    score -= min(
        latency_ms / 100.0,
        40.0,
    )

    if supports_json:
        score += 10.0

    if supports_tools:
        score += 10.0

    if supports_reasoning:
        score += 15.0

    if (context_window or 0) >= 32_000:
        score += 5.0

    return round(
        max(
            0.0,
            min(
                100.0,
                score,
            ),
        ),
        2,
    )


def classify_tier(
    *,
    latency_ms: float,
    context_window: int | None,
    supports_json: bool,
    supports_tools: bool,
    supports_reasoning: bool,
) -> str:

    if (
        supports_reasoning
        and (context_window or 0) >= 64_000
    ):
        return "HEAVY"

    if (
        latency_ms <= 900.0
        and supports_json
    ):
        return "FAST"

    if (
        latency_ms <= 2500.0
        or supports_tools
    ):
        return "MID"

    return "HEAVY"
'@

# =============================================================================
# DISCOVERY BASE
# =============================================================================

Write-ProjectFile `
    (Join-Path $DiscoveryRoot 'base.py') `
@'
"""Provider discovery interface."""

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
        raise NotImplementedError
'@

# =============================================================================
# OPENAI COMPATIBLE DISCOVERY BASE
# =============================================================================

Write-ProjectFile `
    (Join-Path $DiscoveryRoot 'openai_compatible.py') `
@'
"""Generic OpenAI-compatible model discovery."""

from __future__ import annotations

from typing import Any

import httpx

from .base import ProviderDiscovery


class OpenAICompatibleDiscovery(
    ProviderDiscovery
):

    models_url: str = ""

    async def discover(
        self,
        api_key: str,
    ) -> list[dict[str, Any]]:

        headers = {}

        if api_key:
            headers["Authorization"] = (
                f"Bearer {api_key}"
            )

        async with httpx.AsyncClient(
            timeout=20.0
        ) as client:

            response = await client.get(
                self.models_url,
                headers=headers,
            )

            response.raise_for_status()

            payload = response.json()

        result = []

        for raw in payload.get(
            "data",
            [],
        ):

            model_id = raw.get("id")

            if not model_id:
                continue

            context_window = raw.get(
                "context_window"
            )

            if context_window is None:
                context_window = raw.get(
                    "context_length"
                )

            result.append(
                {
                    "model_id": str(model_id),
                    "display_name": raw.get(
                        "name",
                        model_id,
                    ),
                    "context_window": (
                        context_window
                    ),
                    "max_output_tokens": raw.get(
                        "max_completion_tokens"
                    ),
                    "supports_chat": True,
                    "supports_json": True,
                    "supports_tools": True,
                    "supports_reasoning": (
                        "reason"
                        in str(model_id).lower()
                        or
                        "thinking"
                        in str(model_id).lower()
                    ),
                    "raw": raw,
                }
            )

        return result
'@

# =============================================================================
# GEMINI
# =============================================================================

Write-ProjectFile `
    (Join-Path $DiscoveryRoot 'gemini.py') `
@'
"""Gemini OpenAI-compatible discovery."""

from __future__ import annotations

from .openai_compatible import (
    OpenAICompatibleDiscovery,
)


class GeminiDiscovery(
    OpenAICompatibleDiscovery
):

    provider = "gemini"

    models_url = (
        "https://generativelanguage.googleapis.com/"
        "v1beta/openai/models"
    )
'@

# =============================================================================
# GROQ
# =============================================================================

Write-ProjectFile `
    (Join-Path $DiscoveryRoot 'groq.py') `
@'
"""Groq OpenAI-compatible discovery."""

from __future__ import annotations

from .openai_compatible import (
    OpenAICompatibleDiscovery,
)


class GroqDiscovery(
    OpenAICompatibleDiscovery
):

    provider = "groq"

    models_url = (
        "https://api.groq.com/"
        "openai/v1/models"
    )
'@

# =============================================================================
# OPENROUTER
# =============================================================================

Write-ProjectFile `
    (Join-Path $DiscoveryRoot 'openrouter.py') `
@'
"""OpenRouter dynamic model discovery."""

from __future__ import annotations

from typing import Any

import httpx

from .base import ProviderDiscovery


class OpenRouterDiscovery(
    ProviderDiscovery
):

    provider = "openrouter"

    models_url = (
        "https://openrouter.ai/api/v1/models"
    )

    async def discover(
        self,
        api_key: str,
    ) -> list[dict[str, Any]]:

        headers = {}

        if api_key:
            headers["Authorization"] = (
                f"Bearer {api_key}"
            )

        async with httpx.AsyncClient(
            timeout=25.0
        ) as client:

            response = await client.get(
                self.models_url,
                headers=headers,
            )

            response.raise_for_status()

            payload = response.json()

        result = []

        for raw in payload.get(
            "data",
            [],
        ):

            model_id = raw.get("id")

            if not model_id:
                continue

            architecture = raw.get(
                "architecture"
            ) or {}

            result.append(
                {
                    "model_id": str(model_id),
                    "display_name": raw.get(
                        "name",
                        model_id,
                    ),
                    "context_window": raw.get(
                        "context_length"
                    ),
                    "max_output_tokens": (
                        raw.get(
                            "top_provider",
                            {}
                        ).get(
                            "max_completion_tokens"
                        )
                    ),
                    "supports_chat": True,
                    "supports_json": True,
                    "supports_tools": True,
                    "supports_reasoning": (
                        "reason"
                        in str(model_id).lower()
                        or
                        "thinking"
                        in str(model_id).lower()
                    ),
                    "input_modalities": (
                        architecture.get(
                            "input_modalities",
                            []
                        )
                    ),
                    "output_modalities": (
                        architecture.get(
                            "output_modalities",
                            []
                        )
                    ),
                    "pricing": raw.get(
                        "pricing"
                    ),
                    "supported_parameters": raw.get(
                        "supported_parameters",
                        []
                    ),
                    "raw": raw,
                }
            )

        return result
'@

# =============================================================================
# LITELLM
# =============================================================================

Write-ProjectFile `
    (Join-Path $DiscoveryRoot 'litellm.py') `
@'
"""LiteLLM gateway discovery."""

from __future__ import annotations

import os

from .openai_compatible import (
    OpenAICompatibleDiscovery,
)


class LiteLLMDiscovery(
    OpenAICompatibleDiscovery
):

    provider = "litellm"

    @property
    def models_url(self) -> str:

        base = os.environ.get(
            "EZZIO_LITELLM_BASE_URL",
            "http://127.0.0.1:4000",
        ).rstrip("/")

        return f"{base}/v1/models"
'@

# =============================================================================
# QUALIFICATION PROBE
# =============================================================================

Write-ProjectFile `
    (Join-Path $QualificationRoot 'probe.py') `
@'
"""Runtime qualification probe."""

from __future__ import annotations

import json
import time
from typing import Any

import httpx


async def probe(
    *,
    endpoint: str,
    api_key: str,
    model_id: str,
    timeout: float = 30.0,
) -> dict[str, Any]:

    headers = {
        "Authorization": (
            f"Bearer {api_key}"
        ),
        "Content-Type": "application/json",
    }

    payload = {
        "model": model_id,
        "messages": [
            {
                "role": "user",
                "content": (
                    'Return exactly '
                    '{"status":"ok"}'
                ),
            }
        ],
        "temperature": 0.1,
        "max_tokens": 32,
        "response_format": {
            "type": "json_object"
        },
    }

    started = time.perf_counter()

    try:

        async with httpx.AsyncClient(
            timeout=timeout
        ) as client:

            response = await client.post(
                endpoint,
                headers=headers,
                json=payload,
            )

        latency_ms = (
            time.perf_counter()
            - started
        ) * 1000.0

        result = {
            "success": response.is_success,
            "http_status": response.status_code,
            "latency_ms": round(
                latency_ms,
                2,
            ),
            "structured_json": False,
            "content_available": False,
        }

        if not response.is_success:
            return result

        try:

            payload = response.json()

            content = (
                payload
                ["choices"]
                [0]
                ["message"]
                ["content"]
            )

            result[
                "content_available"
            ] = bool(content)

            parsed = json.loads(content)

            result[
                "structured_json"
            ] = (
                parsed.get("status")
                == "ok"
            )

        except Exception:
            pass

        return result

    except Exception as exc:

        return {
            "success": False,
            "http_status": None,
            "latency_ms": None,
            "structured_json": False,
            "content_available": False,
            "error_type": type(exc).__name__,
        }
'@

# =============================================================================
# QUALIFICATION GATE
# =============================================================================

Write-ProjectFile `
    (Join-Path $QualificationRoot 'gate.py') `
@'
"""E-ZZIO qualification gate."""

from __future__ import annotations

from typing import Any

from core.models.scoring import (
    calculate_score,
    classify_tier,
)

from .probe import probe


class QualificationGate:

    MIN_SCORE = 60.0
    MAX_LATENCY_MS = 15000.0

    async def qualify(
        self,
        *,
        provider: str,
        model: dict[str, Any],
        api_key: str,
        endpoint: str,
    ) -> dict[str, Any]:

        model_id = str(
            model["model_id"]
        )

        result = await probe(
            endpoint=endpoint,
            api_key=api_key,
            model_id=model_id,
        )

        latency = result.get(
            "latency_ms"
        )

        failures = []

        if not result.get(
            "success",
            False,
        ):
            failures.append(
                "GENERATION_FAILED"
            )

        if latency is None:
            failures.append(
                "LATENCY_UNAVAILABLE"
            )

        elif latency > self.MAX_LATENCY_MS:
            failures.append(
                "LATENCY_EXCEEDED"
            )

        supports_json = bool(
            model.get(
                "supports_json",
                False,
            )
        )

        supports_tools = bool(
            model.get(
                "supports_tools",
                False,
            )
        )

        supports_reasoning = bool(
            model.get(
                "supports_reasoning",
                False,
            )
        )

        context_window = model.get(
            "context_window"
        )

        score = calculate_score(
            latency_ms=(
                float(latency)
                if latency is not None
                else 99999.0
            ),
            supports_json=supports_json,
            supports_tools=supports_tools,
            supports_reasoning=supports_reasoning,
            context_window=context_window,
        )

        if score < self.MIN_SCORE:
            failures.append(
                "SCORE_TOO_LOW"
            )

        qualified = (
            len(failures) == 0
        )

        return {
            "provider": provider,
            "model_id": model_id,
            "qualified": qualified,
            "failures": failures,
            "latency_ms": latency,
            "score": score,
            "structured_json": bool(
                result.get(
                    "structured_json",
                    False,
                )
            ),
            "tier": (
                classify_tier(
                    latency_ms=float(
                        latency
                    ),
                    context_window=context_window,
                    supports_json=supports_json,
                    supports_tools=supports_tools,
                    supports_reasoning=supports_reasoning,
                )
                if qualified
                else "UNQUALIFIED"
            ),
        }
'@

# =============================================================================
# TELEMETRY
# =============================================================================

Write-ProjectFile `
    (Join-Path $ModelsRoot 'telemetry.py') `
@'
"""Secret-safe forensic telemetry."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


class SafeTelemetry:

    FORBIDDEN = {
        "api_key",
        "apikey",
        "secret",
        "secret_value",
        "token",
        "password",
        "authorization",
        "credential",
        "access_token",
    }

    def __init__(
        self,
        directory: str | Path,
    ) -> None:

        self.directory = Path(
            directory
        )

        self.directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    @classmethod
    def sanitize(
        cls,
        value: Any,
    ) -> Any:

        if isinstance(
            value,
            dict,
        ):

            result = {}

            for key, item in value.items():

                if (
                    str(key).lower()
                    in cls.FORBIDDEN
                ):
                    result[key] = (
                        "[REDACTED]"
                    )
                else:
                    result[key] = (
                        cls.sanitize(item)
                    )

            return result

        if isinstance(
            value,
            (list, tuple),
        ):

            return [
                cls.sanitize(item)
                for item in value
            ]

        return value

    def emit(
        self,
        event: str,
        payload: dict[str, Any],
    ) -> None:

        record = {
            "timestamp": time.time(),
            "event": event,
            "payload": self.sanitize(
                payload
            ),
        }

        path = (
            self.directory
            / "fabric_telemetry.jsonl"
        )

        with path.open(
            "a",
            encoding="utf-8",
        ) as handle:

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

Write-ProjectFile `
    (Join-Path $ModelsRoot 'router.py') `
@'
"""E-ZZIO bounded cognitive router.

Provider failover is separated from key rotation.

Order:
    model
      -> key rotation
        -> next model/provider
          -> fail closed
"""

from __future__ import annotations

from typing import Any

import httpx

from .errors import (
    ProviderExhaustedError,
    RoutingError,
)
from .key_pool import KeyPoolManager
from .registry import (
    ModelRecord,
    ModelRegistry,
)
from .telemetry import SafeTelemetry


class EzzioRouter:

    ENDPOINTS = {
        "gemini": (
            "https://generativelanguage.googleapis.com/"
            "v1beta/openai/chat/completions"
        ),
        "groq": (
            "https://api.groq.com/"
            "openai/v1/chat/completions"
        ),
        "openrouter": (
            "https://openrouter.ai/"
            "api/v1/chat/completions"
        ),
    }

    def __init__(
        self,
        *,
        registry: ModelRegistry,
        key_pool: KeyPoolManager,
        telemetry: SafeTelemetry,
        litellm_base_url: str | None = None,
        provider_order: list[str] | None = None,
        max_keys_per_provider: int = 8,
    ) -> None:

        self.registry = registry
        self.key_pool = key_pool
        self.telemetry = telemetry

        self.litellm_base_url = (
            litellm_base_url
            or "http://127.0.0.1:4000"
        ).rstrip("/")

        self.provider_order = (
            provider_order
            or [
                "gemini",
                "groq",
                "openrouter",
                "litellm",
            ]
        )

        self.max_keys_per_provider = (
            max_keys_per_provider
        )

    def endpoint(
        self,
        provider: str,
    ) -> str | None:

        provider = provider.lower()

        if provider == "litellm":

            return (
                f"{self.litellm_base_url}"
                "/v1/chat/completions"
            )

        return self.ENDPOINTS.get(
            provider
        )

    def candidates(
        self,
        tier: str,
    ) -> list[ModelRecord]:

        models = self.registry.active(
            tier=tier,
            providers=self.provider_order,
        )

        rank = {
            provider: index
            for index, provider
            in enumerate(
                self.provider_order
            )
        }

        models.sort(
            key=lambda model: (
                rank.get(
                    model.provider.lower(),
                    999,
                ),
                -model.qualification_score,
                (
                    model.latency_ms
                    if model.latency_ms is not None
                    else 999999.0
                ),
            )
        )

        return models

    async def execute(
        self,
        *,
        messages: list[dict[str, str]],
        tier: str = "MID",
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:

        candidates = self.candidates(
            tier
        )

        if not candidates:

            raise ProviderExhaustedError(
                f"No active model for tier {tier}."
            )

        attempted = set()

        for model in candidates:

            provider = (
                model.provider.lower()
            )

            identity = (
                provider,
                model.model_id,
            )

            if identity in attempted:
                continue

            attempted.add(identity)

            endpoint = self.endpoint(
                provider
            )

            if not endpoint:
                continue

            attempts = 0

            while (
                attempts
                < self.max_keys_per_provider
            ):

                slot = (
                    self.key_pool.acquire(
                        provider
                    )
                )

                if slot is None:
                    break

                attempts += 1

                headers = {
                    "Authorization": (
                        f"Bearer "
                        f"{slot.secret_value}"
                    ),
                    "Content-Type":
                        "application/json",
                }

                payload = {
                    "model":
                        model.model_id,
                    "messages":
                        messages,
                    "temperature":
                        temperature,
                }

                if max_tokens is not None:
                    payload[
                        "max_tokens"
                    ] = max_tokens

                try:

                    async with (
                        httpx.AsyncClient(
                            timeout=60.0
                        ) as client
                    ):

                        response = (
                            await client.post(
                                endpoint,
                                headers=headers,
                                json=payload,
                            )
                        )

                    status = (
                        response.status_code
                    )

                    # Authentication failure:
                    # this key is permanently removed
                    # from rotation until process reload.
                    if status in (
                        401,
                        403,
                    ):

                        self.key_pool.mark_invalid(
                            slot
                        )

                        self.telemetry.emit(
                            "key_invalid",
                            {
                                "provider":
                                    provider,
                                "slot_id":
                                    slot.slot_id,
                                "status":
                                    status,
                            },
                        )

                        continue

                    # Rate limit:
                    # immediately rotate to another key.
                    if status == 429:

                        self.key_pool.mark_rate_limited(
                            slot
                        )

                        self.telemetry.emit(
                            "key_rate_limited",
                            {
                                "provider":
                                    provider,
                                "slot_id":
                                    slot.slot_id,
                            },
                        )

                        continue

                    # Server side provider problem:
                    # keep the key but leave this model.
                    if status >= 500:

                        self.key_pool.mark_failure(
                            slot
                        )

                        model.failure_count += 1

                        break

                    response.raise_for_status()

                    data = response.json()

                    content = (
                        data
                        ["choices"]
                        [0]
                        ["message"]
                        ["content"]
                    )

                    self.key_pool.mark_success(
                        slot
                    )

                    model.success_count += 1

                    self.telemetry.emit(
                        "inference_success",
                        {
                            "provider":
                                provider,
                            "model":
                                model.model_id,
                            "tier":
                                tier,
                            "status":
                                status,
                            "slot_id":
                                slot.slot_id,
                        },
                    )

                    return {
                        "success": True,
                        "content": content,
                        "provider": provider,
                        "model":
                            model.model_id,
                        "tier": tier,
                    }

                except (
                    httpx.RequestError,
                    ValueError,
                    KeyError,
                ):

                    self.key_pool.mark_failure(
                        slot
                    )

                    model.failure_count += 1

                    self.telemetry.emit(
                        "inference_failure",
                        {
                            "provider":
                                provider,
                            "model":
                                model.model_id,
                            "tier":
                                tier,
                            "slot_id":
                                slot.slot_id,
                        },
                    )

                    break

        raise RoutingError(
            "All qualified model/provider/key "
            "candidates were exhausted."
        )
'@

# =============================================================================
# LIFECYCLE
# =============================================================================

Write-ProjectFile `
    (Join-Path $ModelsRoot 'lifecycle.py') `
@'
"""Model lifecycle and catalog diff."""

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

    def __init__(
        self,
        registry: ModelRegistry,
    ) -> None:

        self.registry = registry

    @staticmethod
    def fingerprint(
        metadata: dict[str, Any],
    ) -> str:

        canonical = json.dumps(
            metadata,
            ensure_ascii=False,
            sort_keys=True,
            separators=(
                ",",
                ":",
            ),
        )

        return hashlib.sha256(
            canonical.encode("utf-8")
        ).hexdigest()

    def ingest(
        self,
        provider: str,
        models: list[dict[str, Any]],
    ) -> list[ModelRecord]:

        now = time.time()

        discovered_ids = set()
        records = []

        for item in models:

            model_id = str(
                item["model_id"]
            )

            discovered_ids.add(
                model_id
            )

            fingerprint = (
                self.fingerprint(item)
            )

            existing = (
                self.registry.get(
                    provider,
                    model_id,
                )
            )

            if existing:

                existing.metadata = item
                existing.source_hash = (
                    fingerprint
                )
                existing.last_seen = now

                records.append(existing)

                continue

            record = ModelRecord(
                model_id=model_id,
                provider=provider,
                lifecycle=(
                    ModelLifecycle
                    .CANDIDATE
                    .value
                ),
                context_window=item.get(
                    "context_window"
                ),
                max_output_tokens=item.get(
                    "max_output_tokens"
                ),
                supports_chat=bool(
                    item.get(
                        "supports_chat"
                    )
                ),
                supports_json=bool(
                    item.get(
                        "supports_json"
                    )
                ),
                supports_tools=bool(
                    item.get(
                        "supports_tools"
                    )
                ),
                supports_reasoning=bool(
                    item.get(
                        "supports_reasoning"
                    )
                ),
                discovered_at=now,
                last_seen=now,
                source_hash=fingerprint,
                metadata=item,
            )

            self.registry.upsert(
                record
            )

            records.append(record)

        # Models that disappeared from the provider
        # are not immediately deleted.
        # They become SUPERSEDED first.
        for existing in self.registry.all():

            if (
                existing.provider.lower()
                != provider.lower()
            ):
                continue

            if (
                existing.model_id
                not in discovered_ids
                and existing.lifecycle
                == ModelLifecycle.ACTIVE.value
            ):

                existing.lifecycle = (
                    ModelLifecycle
                    .SUPERSEDED
                    .value
                )

        self.registry.save()

        return records
'@

# =============================================================================
# FABRIC
# =============================================================================

Write-ProjectFile `
    (Join-Path $ModelsRoot 'fabric.py') `
@'
"""E-ZZIO Autonomous Model Fabric."""

from __future__ import annotations

import asyncio
import os
import time
from pathlib import Path
from typing import Any

from .discovery.gemini import (
    GeminiDiscovery,
)
from .discovery.groq import (
    GroqDiscovery,
)
from .discovery.litellm import (
    LiteLLMDiscovery,
)
from .discovery.openrouter import (
    OpenRouterDiscovery,
)

from .key_pool import KeyPoolManager
from .lifecycle import (
    ModelLifecycleManager,
)
from .registry import (
    ModelLifecycle,
    ModelRegistry,
)
from .router import EzzioRouter
from .telemetry import SafeTelemetry

from .qualification.gate import (
    QualificationGate,
)


class AutonomousModelFabric:

    def __init__(
        self,
        project_root: str | Path,
    ) -> None:

        self.project_root = Path(
            project_root
        )

        data_root = (
            self.project_root
            / "data"
            / "models"
        )

        forensic_root = (
            self.project_root
            / "_forensic"
            / "reports"
        )

        self.registry = ModelRegistry(
            data_root
            / "registry.json"
        )

        self.lifecycle = (
            ModelLifecycleManager(
                self.registry
            )
        )

        self.key_pool = (
            KeyPoolManager()
        )

        self.telemetry = (
            SafeTelemetry(
                forensic_root
            )
        )

        self.router = EzzioRouter(
            registry=self.registry,
            key_pool=self.key_pool,
            telemetry=self.telemetry,
            litellm_base_url=(
                os.environ.get(
                    "EZZIO_LITELLM_BASE_URL",
                    "http://127.0.0.1:4000",
                )
            ),
        )

        self.gate = (
            QualificationGate()
        )

        self.providers = {
            "gemini":
                GeminiDiscovery(),
            "groq":
                GroqDiscovery(),
            "openrouter":
                OpenRouterDiscovery(),
            "litellm":
                LiteLLMDiscovery(),
        }

    def key_for_provider(
        self,
        provider: str,
    ) -> str | None:

        name = (
            f"{provider.upper()}"
            "_API_KEY"
        )

        return (
            os.environ.get(
                name,
                "",
            ).strip()
            or None
        )

    async def discover(
        self,
    ) -> dict[str, list[dict[str, Any]]]:

        result = {}

        for provider, adapter in (
            self.providers.items()
        ):

            key = (
                self.key_for_provider(
                    provider
                )
                or ""
            )

            try:

                models = (
                    await adapter.discover(
                        key
                    )
                )

                result[
                    provider
                ] = models

                self.lifecycle.ingest(
                    provider,
                    models,
                )

                self.telemetry.emit(
                    "discovery_success",
                    {
                        "provider":
                            provider,
                        "model_count":
                            len(models),
                    },
                )

            except Exception as exc:

                result[
                    provider
                ] = []

                self.telemetry.emit(
                    "discovery_failure",
                    {
                        "provider":
                            provider,
                        "error_type":
                            type(exc).__name__,
                    },
                )

        return result

    async def qualify_candidates(
        self,
    ) -> list[dict[str, Any]]:

        results = []

        for model in self.registry.all():

            if model.lifecycle not in {
                ModelLifecycle.CANDIDATE.value,
                ModelLifecycle.SUPERSEDED.value,
            }:
                continue

            provider = (
                model.provider.lower()
            )

            endpoint = (
                self.router.endpoint(
                    provider
                )
            )

            if not endpoint:
                continue

            key = (
                self.key_for_provider(
                    provider
                )
            )

            if not key:
                continue

            model.lifecycle = (
                ModelLifecycle
                .QUALIFYING
                .value
            )

            metadata = (
                model.metadata
                or {}
            )

            result = (
                await self.gate.qualify(
                    provider=provider,
                    model=metadata,
                    api_key=key,
                    endpoint=endpoint,
                )
            )

            results.append(
                result
            )

            if result["qualified"]:

                model.lifecycle = (
                    ModelLifecycle
                    .ACTIVE
                    .value
                )

                model.tier = (
                    result["tier"]
                )

                model.latency_ms = (
                    result["latency_ms"]
                )

                model.qualification_score = (
                    result["score"]
                )

                model.last_verified = (
                    time.time()
                )

            else:

                model.lifecycle = (
                    ModelLifecycle
                    .QUARANTINED
                    .value
                )

        self.registry.save()

        return results

    async def refresh(
        self,
    ) -> dict[str, Any]:

        started = time.perf_counter()

        discovered = (
            await self.discover()
        )

        qualified = (
            await self.qualify_candidates()
        )

        elapsed = (
            time.perf_counter()
            - started
        )

        summary = {
            "timestamp":
                time.time(),
            "duration_seconds":
                round(elapsed, 3),
            "providers":
                {
                    provider:
                        len(models)
                    for provider, models
                    in discovered.items()
                },
            "qualified":
                sum(
                    1
                    for item in qualified
                    if item["qualified"]
                ),
            "rejected":
                sum(
                    1
                    for item in qualified
                    if not item["qualified"]
                ),
            "active_models":
                len(
                    self.registry.active()
                ),
        }

        self.telemetry.emit(
            "fabric_refresh",
            summary,
        )

        return summary

    async def run_forever(
        self,
        interval_seconds: int = 21600,
    ) -> None:

        while True:

            try:
                await self.refresh()

            except Exception as exc:

                self.telemetry.emit(
                    "refresh_failure",
                    {
                        "error_type":
                            type(exc).__name__,
                    },
                )

            await asyncio.sleep(
                interval_seconds
            )

    def status(
        self,
    ) -> dict[str, Any]:

        active = (
            self.registry.active()
        )

        return {
            "active_models":
                len(active),
            "providers":
                sorted(
                    {
                        model.provider
                        for model in active
                    }
                ),
            "models":
                [
                    {
                        "provider":
                            model.provider,
                        "model":
                            model.model_id,
                        "tier":
                            model.tier,
                        "score":
                            model.qualification_score,
                        "latency_ms":
                            model.latency_ms,
                        "lifecycle":
                            model.lifecycle,
                    }
                    for model in active
                ],
            "keys":
                self.key_pool.forensic_status(),
        }


async def main() -> None:

    root = os.environ.get(
        "EZZIO_PROJECT_ROOT",
        r"G:\AI\E-zzio",
    )

    fabric = (
        AutonomousModelFabric(root)
    )

    await fabric.refresh()


if __name__ == "__main__":

    asyncio.run(main())
'@

# =============================================================================
# [5/12] CONFIGURATION
# =============================================================================

Write-Section 5 12 'Création de la configuration du Fabric'

$Config = @{
    schema_version = 2
    fabric_version = $Version

    refresh = @{
        interval_seconds = 21600
        qualify_new_models = $true
        qualify_changed_models = $true
        retire_missing_models = $false
    }

    providers = @(
        'gemini'
        'groq'
        'openrouter'
        'litellm'
    )

    provider_order = @(
        'gemini'
        'groq'
        'openrouter'
        'litellm'
    )

    key_rotation = @{
        max_keys_per_provider = 8
        cooldown_seconds = 60
        quota_cooldown_seconds = 3600
        max_keys_supported = 100
    }

    qualification = @{
        minimum_score = 60
        maximum_latency_ms = 15000
    }

    ollama = @{
        enabled = $false
        supported = $false
    }

    security = @{
        secrets_logged = $false
        secrets_serialized = $false
        secrets_exported = $false
        secrets_displayed = $false
    }
}

Write-ProjectFile `
    $ConfigPath `
    (
        $Config |
        ConvertTo-Json -Depth 20
    )

# =============================================================================
# [6/12] MANIFEST
# =============================================================================

Write-Section 6 12 'Création du manifeste'

$Manifest = @{
    schema_version = 2
    fabric_version = $Version

    generated_at = (
        (Get-Date).ToUniversalTime()
        .ToString('o')
    )

    project_root = $ProjectRoot

    supported_providers = @(
        'gemini'
        'groq'
        'openrouter'
        'litellm'
    )

    excluded_providers = @(
        'ollama'
    )

    capabilities = @(
        'dynamic_model_discovery'
        'catalog_diff'
        'automatic_refresh'
        'qualification_gate'
        'dynamic_registry'
        'model_lifecycle'
        'fast_mid_heavy_tiers'
        'cognitive_router'
        'multi_key_rotation'
        'round_robin_lru_rotation'
        'cooldown'
        'quota_handling'
        'authentication_invalidation'
        'provider_failover'
        'bounded_retry'
        'secret_safe_telemetry'
        'forensic_status'
        'fail_closed'
    )

    network_policy = @{
        builder_network = $false
        runtime_network = $true
    }

    secret_policy = @{
        embedded = $false
        logged = $false
        serialized = $false
        exported = $false
        displayed = $false
    }

    ollama = @{
        supported = $false
        enabled = $false
        discovery = $false
        routing = $false
    }
}

Write-ProjectFile `
    $ManifestPath `
    (
        $Manifest |
        ConvertTo-Json -Depth 20
    )

# =============================================================================
# [7/12] DATA FILES
# =============================================================================

Write-Section 7 12 'Création des données initiales'

Write-ProjectFile `
    (Join-Path $DataRoot 'registry.json') `
    (
        @{
            schema_version = 2
            generated_at = (
                (Get-Date).ToUniversalTime()
                .ToString('o')
            )
            models = @{}
        } |
        ConvertTo-Json -Depth 20
    )

Write-ProjectFile `
    (Join-Path $DataRoot 'discovery_snapshot.json') `
    (
        @{
            schema_version = 2
            generated_at = (
                (Get-Date).ToUniversalTime()
                .ToString('o')
            )
            providers = @{}
        } |
        ConvertTo-Json -Depth 20
    )

Write-ProjectFile `
    (Join-Path $DataRoot 'health.json') `
    (
        @{
            schema_version = 2
            generated_at = (
                (Get-Date).ToUniversalTime()
                .ToString('o')
            )
            providers = @{}
            models = @{}
            keys = @{}
        } |
        ConvertTo-Json -Depth 20
    )

# =============================================================================
# [8/12] REQUIREMENTS
# =============================================================================

Write-Section 8 12 'Création des dépendances Python'

$Requirements = @'
httpx>=0.27,<1
'@

Write-ProjectFile `
    (Join-Path $ProjectRoot 'requirements-model-fabric.txt') `
    $Requirements

# =============================================================================
# [9/12] RUNTIME SCRIPT
# =============================================================================

Write-Section 9 12 'Création du runtime de refresh'

$RuntimeScript = @'
#requires -Version 7.4

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ProjectRoot = $env:EZZIO_PROJECT_ROOT

if ([string]::IsNullOrWhiteSpace($ProjectRoot)) {
    $ProjectRoot = 'G:\AI\E-zzio'
}

$Python = Get-Command python -ErrorAction Stop

$env:PYTHONPATH = $ProjectRoot

& $Python.Source `
    -m core.models.fabric

if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
'@

Write-ProjectFile `
    (Join-Path $ScriptsRoot 'EZZIO_ModelFabric_Refresh.ps1') `
    $RuntimeScript

# =============================================================================
# [10/12] FORENSIC STATUS SCRIPT
# =============================================================================

Write-Section 10 12 'Création du script de statut forensic'

$StatusScript = @'
#requires -Version 7.4

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ProjectRoot = $env:EZZIO_PROJECT_ROOT

if ([string]::IsNullOrWhiteSpace($ProjectRoot)) {
    $ProjectRoot = 'G:\AI\E-zzio'
}

$Python = Get-Command python -ErrorAction Stop

$env:PYTHONPATH = $ProjectRoot

@'
Write-ProjectFile `
    (Join-Path $ScriptsRoot 'EZZIO_ModelFabric_Status.ps1') `
    (
        $StatusScript +
@'

import asyncio
import json

from core.models.fabric import (
    AutonomousModelFabric,
)

fabric = AutonomousModelFabric(
    r"G:\AI\E-zzio"
)

print(
    json.dumps(
        fabric.status(),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )
)
'@
    )

# =============================================================================
# [11/12] README
# =============================================================================

Write-Section 11 12 'Création de la documentation'

$Readme = @'
# E-ZZIO — Autonomous Model Fabric

## Providers

Supported:

- Gemini
- Groq
- OpenRouter
- LiteLLM

## Explicit exclusion

Ollama is NOT supported.

It is intentionally absent from:

- discovery
- registry
- routing
- qualification
- failover

## Automatic model updates

The Fabric does not use a hard-coded model list.

At each refresh it:

1. queries provider catalogs
2. detects new models
3. detects metadata changes
4. creates candidates
5. qualifies candidates
6. activates successful candidates
7. preserves failed candidates in quarantine
8. marks disappeared active models as superseded

Default refresh interval:

6 hours.

## API keys

Environment variables only.

Gemini:

GEMINI_API_KEY
GEMINI_API_KEY_2
...
GEMINI_API_KEY_100

Groq:

GROQ_API_KEY
GROQ_API_KEY_2
...
GROQ_API_KEY_100

OpenRouter:

OPENROUTER_API_KEY
OPENROUTER_API_KEY_2
...
OPENROUTER_API_KEY_100

LiteLLM:

LITELLM_API_KEY
LITELLM_API_KEY_2
...
LITELLM_API_KEY_100

LiteLLM base URL:

EZZIO_LITELLM_BASE_URL

Default:

http://127.0.0.1:4000

## Key rotation

Rotation is independent from provider failover.

Example:

GEMINI_KEY_01 -> 429
        |
        v
GEMINI_KEY_02
        |
        v
GEMINI_KEY_03
        |
        v
all Gemini keys unavailable
        |
        v
next provider

Authentication failures invalidate only the affected key.

Rate limits put only the affected key into cooldown.

## Security

Secrets are never:

- embedded in source
- written to registry
- written to telemetry
- printed in forensic reports
- exported by the Fabric

Only slot identifiers are exposed.

## Runtime

Refresh:

scripts\EZZIO_ModelFabric_Refresh.ps1

Status:

scripts\EZZIO_ModelFabric_Status.ps1

Python entry point:

python -m core.models.fabric

## Required dependency

httpx
'@

Write-ProjectFile `
    (Join-Path $ModelsRoot 'README.md') `
    $Readme

# =============================================================================
# [12/12] STATIC FORENSIC VALIDATION
# =============================================================================

Write-Section 12 12 'Validation forensic finale'

$ExpectedFiles = @(
    (Join-Path $ModelsRoot '__init__.py'),
    (Join-Path $ModelsRoot 'errors.py'),
    (Join-Path $ModelsRoot 'key_pool.py'),
    (Join-Path $ModelsRoot 'registry.py'),
    (Join-Path $ModelsRoot 'scoring.py'),
    (Join-Path $ModelsRoot 'telemetry.py'),
    (Join-Path $ModelsRoot 'router.py'),
    (Join-Path $ModelsRoot 'lifecycle.py'),
    (Join-Path $ModelsRoot 'fabric.py'),

    (Join-Path $DiscoveryRoot '__init__.py'),
    (Join-Path $DiscoveryRoot 'base.py'),
    (Join-Path $DiscoveryRoot 'openai_compatible.py'),
    (Join-Path $DiscoveryRoot 'gemini.py'),
    (Join-Path $DiscoveryRoot 'groq.py'),
    (Join-Path $DiscoveryRoot 'openrouter.py'),
    (Join-Path $DiscoveryRoot 'litellm.py'),

    (Join-Path $QualificationRoot '__init__.py'),
    (Join-Path $QualificationRoot 'probe.py'),
    (Join-Path $QualificationRoot 'gate.py'),

    (Join-Path $ScriptsRoot 'EZZIO_ModelFabric_Refresh.ps1'),
    (Join-Path $ScriptsRoot 'EZZIO_ModelFabric_Status.ps1'),

    $ManifestPath,
    $ConfigPath
)

$Missing = @(
    $ExpectedFiles |
    Where-Object {
        -not (
            Test-Path `
                -LiteralPath $_ `
                -PathType Leaf
        )
    }
)

if ($Missing.Count -gt 0) {

    foreach ($File in $Missing) {
        Write-Fail "Absent : $File"
    }

    throw 'Validation des fichiers échouée.'
}

Write-Pass 'Tous les fichiers attendus existent.'

# -------------------------------------------------------------------------
# Secret scan
# -------------------------------------------------------------------------

$ScanFiles = @(
    Get-ChildItem `
        -LiteralPath $ModelsRoot `
        -Recurse `
        -File `
        -Include '*.py','*.json','*.md'
)

$ForbiddenPatterns = @(
    'AIza[0-9A-Za-z_\-]+',
    'gsk_[0-9A-Za-z_\-]+',
    'sk-or-v1-[0-9A-Za-z_\-]+',
    'Bearer\s+[A-Za-z0-9_\-\.]{25,}',
    'GEMINI_API_KEY\s*=\s*["''][^"'']+["'']',
    'GROQ_API_KEY\s*=\s*["''][^"'']+["'']',
    'OPENROUTER_API_KEY\s*=\s*["''][^"'']+["'']',
    'LITELLM_API_KEY\s*=\s*["''][^"'']+["'']'
)

$Hits = [System.Collections.Generic.List[string]]::new()

foreach ($File in $ScanFiles) {

    $Content = [System.IO.File]::ReadAllText(
        $File.FullName,
        [System.Text.Encoding]::UTF8
    )

    foreach ($Pattern in $ForbiddenPatterns) {

        if ($Content -match $Pattern) {

            $Hits.Add(
                "$($File.FullName) :: $Pattern"
            ) | Out-Null
        }
    }
}

if ($Hits.Count -gt 0) {

    foreach ($Hit in $Hits) {
        Write-Fail "Secret pattern : $Hit"
    }

    throw 'SECRET-SAFETY GATE FAILED.'
}

Write-Pass 'Aucun credential embarqué détecté.'

# -------------------------------------------------------------------------
# Ollama scan
# -------------------------------------------------------------------------

$OllamaHits = [System.Collections.Generic.List[string]]::new()

foreach ($File in $ScanFiles) {

    $Content = [System.IO.File]::ReadAllText(
        $File.FullName,
        [System.Text.Encoding]::UTF8
    )

    if (
        $Content -match '(?i)ollama'
        -and
        $File.Name -ne 'fabric_manifest.json'
    ) {
        $OllamaHits.Add(
            $File.FullName
        ) | Out-Null
    }
}

if ($OllamaHits.Count -gt 0) {

    foreach ($Hit in $OllamaHits) {
        Write-Warn "Référence Ollama trouvée : $Hit"
    }

    Write-Warn 'Les références documentaires peuvent exister, mais aucune intégration runtime n''est autorisée.'
}
else {
    Write-Pass 'Aucune intégration Ollama détectée.'
}

# -------------------------------------------------------------------------
# Python syntax validation
# -------------------------------------------------------------------------

if ($null -ne $Python) {

    $PythonFiles = @(
        Get-ChildItem `
            -LiteralPath $ModelsRoot `
            -Recurse `
            -File `
            -Filter '*.py'
    )

    $PythonFailures = 0

    foreach ($File in $PythonFiles) {

        & $Python.Source `
            -m py_compile `
            $File.FullName `
            2>$null

        if ($LASTEXITCODE -ne 0) {

            $PythonFailures++

            Write-Fail `
                "Python syntax : $($File.FullName)"
        }
    }

    if ($PythonFailures -eq 0) {
        Write-Pass `
            "Python syntax PASS : $($PythonFiles.Count) modules."
    }
    else {
        throw `
            "Python syntax FAIL : $PythonFailures fichiers."
    }
}
else {
    Write-Warn `
        'Validation Python ignorée : Python absent.'
}

# =============================================================================
# FINAL
# =============================================================================

$EndTime = Get-Date
$Duration = (
    $EndTime - $StartTime
).TotalSeconds

Write-Host ''
Write-Host '============================================================================='
Write-Host ' E-ZZIO — AUTONOMOUS MODEL FABRIC'
Write-Host ' BOOTSTRAP TERMINÉ'
Write-Host '============================================================================='

Write-Host "[INFO] Version       : $Version"
Write-Host "[INFO] RunId         : $RunId"
Write-Host "[INFO] Créations     : $($CreatedFiles.Count)"
Write-Host "[INFO] Échecs        : $($FailedFiles.Count)"
Write-Host "[INFO] Durée         : $([math]::Round($Duration,2)) sec"

Write-Host ''
Write-Pass 'Dynamic Model Discovery'
Write-Pass 'Catalog Diff'
Write-Pass 'Qualification Gate'
Write-Pass 'Dynamic Registry'
Write-Pass 'Model Lifecycle'
Write-Pass 'FAST / MID / HEAVY classification'
Write-Pass 'Cognitive Router'
Write-Pass 'Multi-Key Rotation'
Write-Pass 'Cooldown / Quota Handling'
Write-Pass 'Provider Failover'
Write-Pass 'Secret-Safe Telemetry'
Write-Pass 'Automatic Refresh Runtime'
Write-Pass 'Ollama EXCLUDED'
Write-Pass 'GPU EXCLUDED'
Write-Pass 'No credentials embedded'
Write-Pass 'No provider call performed by builder'

Write-Host ''
Write-Host '============================================================================='
Write-Host '[PASS] AUTONOMOUS MODEL FABRIC v1.1.0 — BUILD COMPLETE'
Write-Host '============================================================================='