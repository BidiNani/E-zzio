import sys
from pathlib import Path

ROOT_DIR = Path("G:/AI/E-zzio").resolve()
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from runtime.contracts.authority import ModelRegistryAuthority

def run_negative_and_enforcement_test():
    print("[*] -----------------------------------------------------------------")
    print("[*] E-ZZIO V7.13.0 — Test Négatif (Anti-Shadow Inference) & Enforcement...")
    print("[*] -----------------------------------------------------------------")
    
    authority = ModelRegistryAuthority()
    
    # 1. Test Nominal (Positif)
    valid_model = "qwen2.5-coder:7b"
    res_valid = authority.is_model_authorized(valid_model)
    print(f"  [TEST POSITIF] Modèle autorisé '{valid_model}' -> {res_valid}")
    assert res_valid is True, f"Le modèle valide {valid_model} a été rejeté par erreur !"

    # 2. Test Négatif (Anti-Shadow Inference)
    shadow_model = "fake-shadow-model:999"
    res_shadow = authority.is_model_authorized(shadow_model)
    print(f"  [TEST NÉGISATIF] Modèle non déclaré '{shadow_model}' -> {res_shadow}")
    assert res_shadow is False, f"ALERTE ROUGE : Le modèle non déclaré {shadow_model} a été accepté !"

    print("\n🟢 RÉSULTAT : Le portillon d'autorité bloque hermétiquement le Shadow Inference.")

if __name__ == "__main__":
    run_negative_and_enforcement_test()
