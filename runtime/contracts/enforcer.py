import json
from datetime import datetime, timezone
from pathlib import Path
from runtime.contracts.authority import ModelRegistryAuthority


class UnauthorizedModelError(Exception):
    """Levé lorsqu'un composant tente d'exécuter un modèle non gouverné ou non attesté."""

    pass


class EnforcedModelRouter:
    """
    Routeur d'inférence dynamique sous contrainte de gouvernance stricte.
    Génère un journal d'audit immuable (JSONL) pour chaque décision ALLOW / DENY.
    """

    def __init__(self, authority: ModelRegistryAuthority = None, root_dir: str = None):
        self.authority = authority if authority else ModelRegistryAuthority()
        self.root_dir = Path(root_dir) if root_dir else Path("G:/AI/E-zzio").resolve()
        self.audit_log_path = self.root_dir / "runtime" / "audit" / "model_authority_events.jsonl"
        self.audit_log_path.parent.mkdir(parents=True, exist_ok=True)

    def _log_decision(self, model: str, provider: str, decision: str, reason: str = None):
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "model": model,
            "provider": provider,
            "decision": decision,
            "registry_version": self.authority.get_registry_version(),
            "registry_epoch": self.authority.get_registry_epoch(),
            "hash_prefix": self.authority.get_hash_prefix(),
        }
        if reason:
            event["reason"] = reason

        with open(self.audit_log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")

    def route_inference(self, requested_model: str, provider: str = "ollama", payload: dict = None):
        print(f"[ENFORCER] Interception de la requête pour le modèle : '{requested_model}' (Provider: {provider})")

        if not self.authority.is_model_authorized(requested_model, provider):
            reason_msg = f"Modèle '{requested_model}' non enregistré ou inactif dans le registre V7.12."
            self._log_decision(requested_model, provider, "DENY", reason="NOT_REGISTERED")
            raise UnauthorizedModelError(f"SHADOW INFERENCE BLOCKED : {reason_msg}")

        self._log_decision(requested_model, provider, "ALLOW")
        print(f"[ENFORCER] ✅ Modèle '{requested_model}' validé et audité. Exécution autorisée.")
        return {"status": "DISPATCHED", "model": requested_model, "provider": provider, "governance": "VERIFIED_V712_AUDITED"}
