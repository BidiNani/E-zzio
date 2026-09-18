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
