import json
import hashlib
from pathlib import Path


class CoreModelRegistry:
    def __init__(self, contract_dir: Path, secret_seed: str = "EZZIO_CORE_ROOT_KEY"):
        self.contract_dir = contract_dir
        self.secret_seed = secret_seed
        self._registry = {}
        self._load_all_contracts()

    def _load_all_contracts(self):
        for path in self.contract_dir.glob("*.contract.json"):
            with open(path, "r", encoding="utf-8") as f:
                contract = json.load(f)
                if self._verify_contract(contract):
                    self._registry[contract["model_id"]] = contract
                else:
                    print(f"[WARN] Contrat corrompu ignoré: {path}")

    def _verify_contract(self, contract: dict) -> bool:
        sig = contract.get("signature")
        # Copie sans signature pour calcul
        payload = {k: v for k, v in contract.items() if k != "signature"}
        encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
        expected = hashlib.sha256(encoded + self.secret_seed.encode("utf-8")).hexdigest()
        return sig == expected

    def resolve_contract(self, model_id: str) -> dict:
        return self._registry.get(model_id, {"status": "QUARANTINE"})
