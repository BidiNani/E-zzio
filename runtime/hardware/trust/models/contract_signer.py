import json
import hashlib
import sys
from pathlib import Path

class ContractSigner:
    def __init__(self, secret_seed: str = "EZZIO_CORE_ROOT_KEY"):
        self.secret_seed = secret_seed

    def sign_file(self, file_path: Path):
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Extraction du payload pour signature (tout sauf "signature")
        payload = {k: v for k, v in data.items() if k != "signature"}
        
        # Sérialisation déterministe
        encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
        
        # Calcul du HMAC-SHA256 (via hash avec secret)
        signature = hashlib.sha256(encoded + self.secret_seed.encode("utf-8")).hexdigest()
        
        data["signature"] = signature
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, sort_keys=True)
        print(f"[SIGNED] {file_path.name} | Sig: {signature[:12]}...")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python contract_signer.py <file.contract.json>")
        sys.exit(1)
        
    signer = ContractSigner()
    signer.sign_file(Path(sys.argv[1]))
