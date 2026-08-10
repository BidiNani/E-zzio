import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

print("1. Initialisation d'E-zzio avec module de recherche Web...")

# Chargement sécurisé de la clé
env_path = os.path.join("secrets", ".env")
if os.path.exists(env_path):
    load_dotenv(dotenv_path=env_path)
    
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("ERREUR FATALE : Cle GEMINI_API_KEY introuvable.")
    exit(1)

client = genai.Client(api_key=api_key)

print("2. Lancement de la requete avec Google Search Grounding activé...")

# La question nécessite des informations en temps réel
prompt = "Quelles sont les actualités mondiales majeures ou technologiques d'aujourd'hui ? Intègre des liens vers les sources web que tu as consultées."

try:
    # C'est ICI que la magie opère : on active l'outil "google_search"
    response = client.models.generate_content(
        model='gemini-3.6-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[{"google_search": {}}]
        )
    )
    
    print("\n============================================")
    print(" REPONSE D'E-ZZIO (CONNECTE AU WEB)")
    print("============================================\n")
    print(response.text)
    print("\n============================================")
    
except Exception as e:
    # Fallback si 3.6-flash est saturé
    print(f"Erreur avec 3.6-flash ({e}). Tentative avec 2.5-flash...")
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[{"google_search": {}}]
            )
        )
        print("\n" + response.text)
    except Exception as e2:
        print(f"Erreur API : {e2}")

