import mss
import mss.tools
import os
import pathlib
from dotenv import load_dotenv
from google import genai
from google.genai import types

print("1. Demarrage du module de vision avec Gemini...")

# Ciblage explicite du dossier secrets
env_path = os.path.join("secrets", ".env")
if os.path.exists(env_path):
    print("Fichier de configuration localise : " + env_path)
    load_dotenv(dotenv_path=env_path)
else:
    print(f"ATTENTION : Le fichier de secrets est introuvable a l'emplacement : {env_path}")

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("ERREUR FATALE : Cle GEMINI_API_KEY introuvable dans " + env_path)
    exit(1)

print("2. Cle API detectee. Configuration du client Gemini...")
client = genai.Client(api_key=api_key)

def analyse_ecran(question="Decris brievement ce que tu vois sur cet ecran."):
    print("3. Capture de l ecran en cours...")
    try:
        with mss.MSS() as sct:
            monitor = sct.monitors[1]
            sct_img = sct.grab(monitor)
            img_path = "capture_temp.png"
            mss.tools.to_png(sct_img.rgb, sct_img.size, output=img_path)
        print("4. Fichier temporaire cree avec succes.")
    except Exception as e:
        print("ERREUR CAPTURE : " + str(e))
        return

    print("5. Formatage de l'image et envoi de la requete au modele gemini-2.5-flash...")
    try:
        image_bytes = pathlib.Path(img_path).read_bytes()
        
        image_part = types.Part.from_bytes(
            data=image_bytes,
            mime_type='image/png'
        )
        
        # Utilisation d'un modele versionne stable propose
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[question, image_part]
        )
        
        print("\nREPONSE D E-ZZIO :")
        print(response.text)
        
    except Exception as e:
        print("ERREUR RESEAU/API : " + str(e))
        print("\n--- DIAGNOSTIC AUTOMATIQUE ---")
        print("Modeles disponibles sur cette cle API :")
        try:
            for m in client.models.list():
                print(f"- {m.name}")
        except Exception as ex:
            print("Impossible de recuperer la liste des modeles : " + str(ex))
        print("------------------------------")

if __name__ == "__main__":
    analyse_ecran()
