from runtime.policy.engine import PolicyEngine
from runtime.security.secrets import SecretKeyManager
from runtime.tools.manifest_provider import ManifestProvider
from runtime.tools.tool_schema import ToolRequest

class SecurityGuard:
    """
    Pont de rétrocompatibilité natif conforme au contrat PolicyEngine.authorize.
    """
    def __init__(self, policy_engine = None):
        if policy_engine:
            self.policy_engine = policy_engine
        else:
            key_mgr = SecretKeyManager()
            manifest_prov = ManifestProvider()
            self.policy_engine = PolicyEngine(manifest_provider=manifest_prov, key_manager=key_mgr)

    def check_permission(self, subject: str, permission: str) -> bool:
        try:
            # Création du ToolRequest attendu par le PolicyEngine moderne
            request = ToolRequest(name=permission, arguments={}, call_id="bridge-call")
            # authorize retourne un tuple (success: bool, reason: str, token)
            success, _, _ = self.policy_engine.authorize(request, session_id=subject)
            return bool(success)
        except Exception:
            return False

class OutputGuard:
    """Limits executor output size safely."""
    MAX_OUTPUT = 10000
    @classmethod
    def sanitize(cls, output):
        if output is None:
            return ""
        text = str(output)
        if len(text) > cls.MAX_OUTPUT:
            return text[:cls.MAX_OUTPUT] + "\n...[TRUNCATED]"
        return text
