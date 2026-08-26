"""
E-ZZIO V7.29.3 — Identity Guardian Engine
Exécute le contrôle anti-dérive continu entre le disque et le contexte de boot.
"""

import hashlib
from pathlib import Path
from core.identity.identity_context import ImmutableIdentityContext
from core.identity.identity_events import IdentityState, IdentityEventManager

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR = ROOT_DIR / "config"
RUNTIME_IDENTITY_DIR = ROOT_DIR / "runtime" / "identity"


class IdentityGuardian:
    def __init__(self, context: ImmutableIdentityContext):
        self.context = context
        self.current_state = IdentityState.VERIFIED

    def _hash_file(self, path: Path) -> str:
        if not path.exists():
            return hashlib.sha256(b"EMPTY").hexdigest()
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def audit_now(self) -> dict:
        """Audite les fichiers sur le disque et bascule en FAIL_CLOSED si dérive détectée."""
        if self.current_state == IdentityState.FAIL_CLOSED:
            return {"state": IdentityState.FAIL_CLOSED, "valid": False, "error": "SYSTEM_IN_FAIL_CLOSED_STATE"}

        current_const = self._hash_file(CONFIG_DIR / "constitution.json")
        current_persona = self._hash_file(CONFIG_DIR / "persona.json")
        current_lore = self._hash_file(CONFIG_DIR / "lore.md")
        current_skills = self._hash_file(CONFIG_DIR / "skills_manifest.json")
        current_memory = self._hash_file(CONFIG_DIR / "memory_graph.json")
        current_spec = self._hash_file(RUNTIME_IDENTITY_DIR / "identity.json")

        mismatches = []
        if current_const != self.context.constitution_hash:
            mismatches.append("constitution.json")
        if current_persona != self.context.persona_hash:
            mismatches.append("persona.json")
        if current_lore != self.context.lore_hash:
            mismatches.append("lore.md")
        if current_skills != self.context.skill_manifest_hash:
            mismatches.append("skills_manifest.json")
        if current_memory != self.context.memory_anchor_hash:
            mismatches.append("memory_graph.json")

        recalculated_combined = current_const + current_persona + current_lore + current_skills + current_memory + current_spec
        recalculated_root = hashlib.sha256(recalculated_combined.encode("utf-8")).hexdigest()

        if mismatches or recalculated_root != self.context.identity_root_hash:
            self.current_state = IdentityState.FAIL_CLOSED
            IdentityEventManager.log_event(
                event_type="IDENTITY_DRIFT_DETECTED",
                state=IdentityState.FAIL_CLOSED,
                details={"mismatches": mismatches, "recalculated_root": recalculated_root},
            )
            return {
                "state": IdentityState.FAIL_CLOSED,
                "valid": False,
                "error": f"UNAUTHORIZED IDENTITY MUTATION DETECTED: {', '.join(mismatches)}",
            }

        return {"state": IdentityState.VERIFIED, "valid": True, "error": None}
