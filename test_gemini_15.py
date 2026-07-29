import os
from dotenv import load_dotenv
from google import genai

load_dotenv("secrets/.env", override=True)

keys_to_test = [
    ("Index 0 (Principale)", os.getenv("GEMINI_API_KEY")),
    ("Index 1 (Secondaire)", os.getenv("GEMINI_API_KEY_2"))
]

print("=" * 60)
print("🔍 TEST DE SURVIE AVEC GEMINI 1.5 FLASH")
print("=" * 60)

for name, key in keys_to_test:
    if not key:
        continue
        
    print(f"\n🚀 Test avec {name}...")
    try:
        client = genai.Client(api_key=key)
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents='Ceci est un test. Réponds uniquement "OK".'
        )
        print(f"✅ SUCCÈS ABSOLU ! L'API a répondu : {response.text.strip()}")
    except Exception as api_err:
        print(f"❌ ÉCHEC : {repr(api_err)}")
