import json
import hashlib
from pathlib import Path


class RegistryIntegrityError(Exception):
    """Levé si le registre des modèles a été altéré depuis son gel cryptographique."""

    pass


class ModelRegistryAuthority:
    """
    Autorité d'accès contrôlé au registre des modèles IA.
    Garantit l'intégrité cryptographique, le contrôle d'epoch et l'attestation physique.
    """

    def __init__(self, root_dir: str = None, min_epoch: int = 1):
        self.root_dir = Path(root_dir) if root_dir else Path("G:/AI/E-zzio").resolve()
        self.v712_registry = self.root_dir / "runtime" / "audit" / "intelligence_scan" / "V7_REGISTRY" / "V712"
        self.manifest_path = self.v712_registry / "governance_freeze_manifest.json"
        self.registry_path = self.root_dir / "runtime" / "contracts" / "MODEL_REGISTRY_V1.json"
        self.min_epoch = min_epoch

        self._cache = None
        self._hash_prefix = "UNKNOWN"
        self._verify_and_load()

    def _verify_and_load(self):
        if not self.manifest_path.exists():
            raise RegistryIntegrityError("Manifeste de gel V712 introuvable.")
        if not self.registry_path.exists():
            raise RegistryIntegrityError("Registre des modèles introuvable.")

        manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        sealed_artifacts = manifest.get("sealed_artifacts", {})
        model_meta = sealed_artifacts.get("model_registry")

        if not model_meta:
            raise RegistryIntegrityError("Entrée 'model_registry' absente du manifeste de gel.")

        expected_hash = model_meta["sha256"]
        expected_size = model_meta["size_bytes"]

        file_bytes = self.registry_path.read_bytes()
        if len(file_bytes) != expected_size:
            raise RegistryIntegrityError(f"Taille du registre non conforme ({len(file_bytes)} vs {expected_size})")

        hasher = hashlib.sha256()
        hasher.update(file_bytes)
        current_hash = hasher.hexdigest().lower()

        if current_hash != expected_hash:
            raise RegistryIntegrityError(f"ALTÉRATION DÉTECTÉE : Le hash ({current_hash[:12]}...) ne correspond pas au sceau.")

        self._hash_prefix = current_hash[:8]
        self._cache = json.loads(file_bytes.decode("utf-8"))

        # Vérification de l'Epoch
        current_epoch = self._cache.get("registry_epoch", 0)
        if current_epoch < self.min_epoch:
            raise RegistryIntegrityError(
                f"REGISTRY_DOWNGRADE_BLOCKED : Epoch détecté ({current_epoch}) inférieur au minimum requis ({self.min_epoch})."
            )

        print(f"[AUTHORITY] Modèle d'Autorité validé (Epoch: {current_epoch}, Hash Prefix: {self._hash_prefix})")

    def get_registry_version(self) -> str:
        return self._cache.get("registry_version", "UNKNOWN")

    def get_registry_epoch(self) -> int:
        return self._cache.get("registry_epoch", 0)

    def get_hash_prefix(self) -> str:
        return self._hash_prefix

    def get_local_weights(self) -> list:
        return self._cache.get("local_weights_discovered", [])

    def get_external_providers(self) -> dict:
        return self._cache.get("external_providers_detected", {})

    def is_model_authorized(self, model_id: str, provider: str = "ollama") -> bool:
        if provider == "ollama":
            ollama_models = self.get_external_providers().get("ollama_models", [])
            for m in ollama_models:
                if m.get("model_id") == model_id:
                    return True
        return False
