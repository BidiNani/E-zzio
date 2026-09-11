"""
E-ZZIO V7.24.0 — Provider Response Contract
Objet typé unifié pour toutes les réponses des fournisseurs cloud.
Élimine les dictionnaires libres et isole le routeur des SDKs tiers.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List


@dataclass
class ProviderResponse:
    ok: bool
    provider: str
    model: str
    content: str = ""
    latency_ms: float = 0.0
    sources: List[Dict[str, str]] = field(default_factory=list)
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
