"""
E-ZZIO V7.40 — Certification Test Suite (Google Identity Bridge)
Valide le chiffrement, le scellement HMAC et la détection d'altération du Vault OAuth2.
"""
import sys
import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.tool_gateway.google_bridge import google_bridge

def run_google_bridge_certification():
    print("============================================================")
    print(" E-ZZIO V7.40 — GOOGLE IDENTITY BRIDGE CERTIFICATION")
    print("============================================================\n")

    vault_file = ROOT_DIR / "runtime" / "vault" / "google_oauth.vault"

    # [1/3] Création et Chiffrement
    success = google_bridge.store_tokens(
        access_token="ya29.simulated_access_token_v740",
        refresh_token="1//0g_simulated_refresh_token",
        scopes=["gmail.readonly", "drive.file"],
        expires_in_sec=3600
    )
    assert success is True, "Échec de l'écriture dans le Vault."
    
    # Vérification que le fichier ne contient pas les tokens en clair
    vault_content = vault_file.read_text(encoding="utf-8")
    assert "ya29." not in vault_content, "CRITIQUE : Le token est lisible en clair dans le Vault !"
    print(" [1/3] Stockage chiffré (AES-Fernet) : OK")

    # [2/3] Déchiffrement et Restitution
    retrieval = google_bridge.retrieve_tokens()
    assert retrieval["valid"] is True, f"Échec du déchiffrement : {retrieval.get('error')}"
    assert retrieval["tokens"]["access_token"] == "ya29.simulated_access_token_v740", "Token corrompu après déchiffrement."
    print(" [2/3] Lecture et restitution sécurisée : OK")

    # [3/3] Détection d'altération (Anti-Tampering)
    vault_data = json.loads(vault_content)
    # Simulation d'une attaque : modification de la signature HMAC
    vault_data["hmac_signature"] = "0000000000000000000000000000000000000000000000000000000000000000"
    vault_file.write_text(json.dumps(vault_data), encoding="utf-8")

    tampered_retrieval = google_bridge.retrieve_tokens()
    assert tampered_retrieval["valid"] is False, "Le Vault a accepté une charge altérée !"
    assert tampered_retrieval["error"] == "VAULT_CORRUPTED_OR_TAMPERED", "Code d'erreur de corruption incorrect."
    print(" [3/3] Détection d'altération cryptographique (Sceau HMAC) : OK")

    print("\n============================================================")
    print(" V7.40 CERTIFIÉ : GOOGLE BRIDGE & SECURE VAULT ACTIFS")
    print("============================================================\n")

if __name__ == "__main__":
    run_google_bridge_certification()
