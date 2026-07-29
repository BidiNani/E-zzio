import os
import time
from dotenv import load_dotenv
from google import genai

load_dotenv("secrets/.env", override=True)
key = os.getenv("GEMINI_API_KEY")

candidates = [
    "gemini-flash-latest",
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash",
    "gemini-2.0-flash-lite",
    "gemini-3.1-flash-lite"
]

print("=" * 60)
print("🔍 RECHERCHE DU MODÈLE GRATUIT ACTIF (QUOTA > 0)")
print("=" * 60)

client = genai.Client(api_key=key)

for model_name in candidates:
    print(f"\n🚀 Test de la limite sur {model_name}...")
    try:
        response = client.models.generate_content(
            model=model_name,
            contents='Ceci est un test API. Réponds juste "OK".'
        )
        print(f"✅ BINGO ! Le modèle [{model_name}] est gratuit et accessible !")
        print(f"   Réponse : {response.text.strip()}")
        print("\n👉 C'est ce modèle que tu dois mettre dans ton web_server.py !")
        break
    except Exception as e:
        err_str = str(e)
        if "limit: 0" in err_str:
            print(f"❌ Rejeté (Quota Free Tier à 0)")
        elif "404" in err_str:
            print(f"❌ Rejeté (Modèle introuvable)")
        else:
            print(f"❌ Échec inattendu : {err_str[:150]}")
    time.sleep(1.5)
