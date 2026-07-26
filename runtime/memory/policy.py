from runtime.tools.manifest_provider import ManifestProvider

class MemoryPolicyEngine:
    """Décide si un événement mérite d'être cristallisé dans la mémoire à long terme."""

    def __init__(self, manifest_provider: ManifestProvider):
        self.manifest = manifest_provider

    def should_memorize(self, event_type: str, payload: dict) -> bool:
        policy = {"store_failures": True, "store_tool_calls": True}

        try:
            import json
            raw_manifest = json.loads(self.manifest.path.read_text(encoding="utf-8"))
            policy = raw_manifest.get("memory_policy", policy)
        except Exception:
            pass

        if event_type == "ExecutionFinished":
            if not policy.get("store_tool_calls", True):
                return False

            execution = payload.get("execution", {})
            success = (
                payload.get("success", False)
                if "success" in payload
                else execution.get("success", False)
            )

            if not success and not policy.get("store_failures", True):
                return False

            return True

        if event_type == "PreferenceLearned":
            return policy.get("store_preferences", True)

        return False