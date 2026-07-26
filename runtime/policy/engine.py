import uuid
from datetime import datetime, timedelta
from typing import Tuple, Optional
from runtime.contracts.execution_context import CapabilityToken, TokenSigner
from runtime.tools.tool_schema import ToolRequest
from runtime.tools.manifest_provider import ManifestProvider

class PolicyEngine:
    def __init__(self, manifest_provider: ManifestProvider, key_manager, allowed_runtime_level: int = 0):
        self.manifest = manifest_provider
        self.key_manager = key_manager
        self.allowed_runtime_level = allowed_runtime_level
        self.GRACE_PERIOD_SEC = 10

    def authorize(self, request: ToolRequest, session_id: str) -> Tuple[bool, str, Optional[CapabilityToken]]:
        tools_config = self.manifest.get_tools()
        config = tools_config.get(request.name)
        if not config:
            return False, f"Outil inconnu : {request.name}", None

        req_level = config.get("permission_level", 999)
        if req_level > self.allowed_runtime_level:
            return False, "Privilège insuffisant.", None

        timeout_sec = config.get("timeout_sec", 10)
        
        mode = config.get("execution_mode")
        if mode not in ["internal", "external"]:
            return False, f"Mode d'exécution invalide ou manquant : {mode}", None

        raw_token = CapabilityToken(
            token_id=str(uuid.uuid4()),
            session_id=session_id,
            tool_name=request.name,
            executor_type=config.get("executor", "python"),
            execution_mode=mode,
            timeout_sec=timeout_sec,
            budget_cost=config.get("budget_cost", 1),
            refund_on_failure=config.get("refund_on_failure", False),
            manifest_hash=self.manifest.get_manifest_hash(),
            issued_at=datetime.now(),
            expires_at=datetime.now() + timedelta(seconds=timeout_sec + self.GRACE_PERIOD_SEC),
            constraints=config.get("sandbox", {}),
            key_id=self.key_manager.key_id
        )
        return True, "AUTHORIZED", TokenSigner.sign(raw_token, self.key_manager.get_key())