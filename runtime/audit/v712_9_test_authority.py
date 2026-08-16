import sys
from pathlib import Path

ROOT_DIR = Path("G:/AI/E-zzio").resolve()
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from runtime.contracts.authority import ModelRegistryAuthority, RegistryIntegrityError

def test_authority():
    print("[*] Démarrage du test de ModelRegistryAuthority...")
    try:
        authority = ModelRegistryAuthority()
        print(f"  [OK] Version du registre chargée : {authority.get_registry_version()}")
        
        # Test de vérification d'un modèle Ollama connu
        test_model = "qwen2.5-coder:7b"
        is_auth = authority.is_model_authorized(test_model)
        print(f"  [OK] Modèle '{test_model}' autorisé ? -> {is_auth}")

        if is_auth:
            print("🟢 TEST AUTORITÉ RÉUSSI : L'accès au registre est sécurisé et fonctionnel.")
        else:
            print("🔴 Avertissement : Le modèle testé n'a pas été trouvé dans les fournisseurs externes.")
            
    except RegistryIntegrityError as rie:
        print(f"🔴 ERREUR D'INTÉGRITÉ : {str(rie)}")
        sys.exit(1)
    except Exception as e:
        print(f"🔴 ERREUR INATTENDUE : {str(e)}")
        sys.exit(2)

if __name__ == "__main__":
    test_authority()
