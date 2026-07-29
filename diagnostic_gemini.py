import os
import traceback
from dotenv import load_dotenv
from google import genai

# override=True force l'écrasement des variables d'environnement Windows en cache
load_dotenv("secrets/.env", override=True)

keys_to_test = [
    ("Index 0 (Principale)", os.getenv("GEMINI_API_KEY")),
    ("Index 1 (Secondaire)", os.getenv("GEMINI_API_KEY_2"))
]

print("=" * 60)
print("🔍 DIAGNOSTIC DU POOL GEMINI - LECTURE EN MÉMOIRE")
print("=" * 60)

for name, key in keys_to_test:
    if not key:
        print(f"[{name}] -> ❌ ERREUR : Variable introuvable ou vide")
    else:
        masked = f"{key[:10]} ... {key[-6:]}" if len(key) > 15 else "CLÉ ANORMALEMENT COURTE"
        print(f"[{name}] -> {masked}")

print("=" * 60)

for name, key in keys_to_test:
    if not key:
        continue
        
    print(f"\n🚀 Test de requête pure avec {name}...")
    try:
        client = genai.Client(api_key=key)
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents='Ceci est un test de diagnostic API. Réponds uniquement "OK".'
        )
        print(f"✅ SUCCÈS ! L'API a répondu : {response.text.strip()}")
    except Exception as api_err:
        print(f"❌ ÉCHEC TOTAL SUR {name}")
        print(f"   [Type]  : {type(api_err)}")
        print(f"   [Brut]  : {repr(api_err)}")
