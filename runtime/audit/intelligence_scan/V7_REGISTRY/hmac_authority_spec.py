# ==============================================================================
# E-ZZIO V7.9 REFERENCE SPECIFICATION — Unified HMAC-SHA256 Authority & Bridge
# Mode: REFERENCE / NON-PRODUCTION DEPLOYMENT (Read-Only Engineering)
# ==============================================================================

import hmac
import hashlib
import json

class UnifiedHMACAuthority:
    """
    Fournit l'autorité cryptographique unique pour l'ensemble des composants d'E-ZZIO.
    Intègre un pont de compatibilité (Bridge) pour tolérer temporairement le format legacy.
    """
    
    @staticmethod
    def canonicalize_payload(payload: dict) -> bytes:
        """Sérialise un dictionnaire en JSON canonique (clés triées, sans espaces superflus)."""
        # Exclut le champ signature lui-même du calcul d'intégrité
        clean_payload = {k: v for k, v in payload.items() if k != "signature"}
        return json.dumps(clean_payload, sort_keys=True, separators=(',', ':')).encode("utf-8")

    @classmethod
    def sign(cls, payload: dict, secret_key: str) -> str:
        """Génère une signature HMAC-SHA256 standardisée."""
        canonical_bytes = cls.canonicalize_payload(payload)
        key_bytes = secret_key.encode("utf-8")
        return hmac.new(key_bytes, canonical_bytes, hashlib.sha256).hexdigest()

    @classmethod
    def verify(cls, payload: dict, provided_signature: str, secret_key: str) -> bool:
        """
        Vérifie la signature avec un pont de transition (Bridge) :
        1. Tente d'abord la vérification HMAC-SHA256 standard.
        2. En cas d'échec, bascule sur la vérification Legacy (SHA256(payload + secret))
           pour assurer la rétrocompatibilité des contrats de modèles existants.
        """
        # Mode 1 : Standard HMAC-SHA256
        expected_hmac = cls.sign(payload, secret_key)
        if hmac.compare_digest(expected_hmac, provided_signature):
            return True

        # Mode 2 : Bridge Legacy (SHA256 avec secret incorporé, tel que contract_signer.py)
        try:
            canonical_bytes = cls.canonicalize_payload(payload)
            legacy_encoded = canonical_bytes + secret_key.encode("utf-8")
            legacy_expected = hashlib.sha256(legacy_encoded).hexdigest()
            if hmac.compare_digest(legacy_expected, provided_signature):
                return True
        except Exception:
            pass

        return False

if __name__ == "__main__":
    print("[*] Spécification de l'autorité HMAC-SHA256 chargée avec succès.")
    
    # Test de démonstration du pont
    secret = "dummy_secret_seed_123"
    test_payload = {"model_id": "qwen2.5-7b", "provider": "ollama", "contract_version": "1.0"}
    
    # Signature standard
    sig = UnifiedHMACAuthority.sign(test_payload, secret)
    print(f"[OK] Signature HMAC générée : {sig}")
    
    # Vérification standard
    assert UnifiedHMACAuthority.verify(test_payload, sig, secret) == True
    print("[OK] Vérification standard réussie.")
