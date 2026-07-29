import os
from dotenv import load_dotenv
from google import genai

load_dotenv("secrets/.env", override=True)
key = os.getenv("GEMINI_API_KEY")

print("=" * 60)
print("🔍 LISTE DES MODÈLES AUTORISÉS POUR TA CLÉ")
print("=" * 60)

try:
    client = genai.Client(api_key=key)
    # On interroge l'API pour obtenir le catalogue autorisé
    models = client.models.list()
    
    count = 0
    for m in models:
        # On affiche uniquement le nom du modèle
        print(f"✅ Autorisé : {m.name}")
        count += 1
        
    if count == 0:
        print("❌ La clé est valide, mais Google ne t'autorise l'accès à AUCUN modèle.")
except Exception as e:
    print(f"❌ Erreur lors de la récupération : {e}")
