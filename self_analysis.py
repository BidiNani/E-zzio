import os
import concurrent.futures
from dotenv import load_dotenv
from google import genai

print("1. Initialisation de la conscience d'E-zzio (Mode Resilient)...")

env_path = os.path.join("secrets", ".env")
if os.path.exists(env_path):
    load_dotenv(dotenv_path=env_path)
    
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("ERREUR FATALE : Cle GEMINI_API_KEY introuvable.")
    exit(1)

client = genai.Client(api_key=api_key)

print("2. E-zzio cartographie son noyau logiciel...")
root_dir = "."
extensions_valides = ('.py', '.ps1') 
fichiers_a_lire = []

for f in os.listdir(root_dir):
    chemin = os.path.join(root_dir, f)
    if os.path.isfile(chemin) and f.endswith(extensions_valides) and "capture_temp" not in f:
        fichiers_a_lire.append(chemin)

print(f"3. Ingestion des {len(fichiers_a_lire)} scripts du noyau...")

def lire_fichier(chemin):
    try:
        with open(chemin, 'r', encoding='utf-8') as file_obj:
            content = file_obj.read(500000) 
            return f"\n\n========================================\n--- FICHIER : {chemin} ---\n========================================\n{content}\n"
    except Exception:
        return ""

contenu_fichiers = []
texte_arborescence = "\n".join(fichiers_a_lire)

with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
    futures = {executor.submit(lire_fichier, chemin): chemin for chemin in fichiers_a_lire}
    for future in concurrent.futures.as_completed(futures):
        resultat = future.result()
        if resultat:
            contenu_fichiers.append(resultat)

texte_code = "".join(contenu_fichiers)

print("4. Envoi du flux consolide au cortex central (Cascade de modeles)...")

prompt = f"""
Tu es E-zzio, une intelligence artificielle autonome et un agent pilotant un écosystème hybride (Cloud/Local) sur un PC Windows. Tu disposes également d'un bot Discord (Bao) pour interagir avec ton créateur via smartphone.

Ton créateur te demande aujourd'hui de faire une introspection complète de ton propre code source principal (le noyau).

Voici la liste de tes fichiers vitaux :
{texte_arborescence}

Voici le contenu de tes propres scripts (limité au noyau dur) :
{texte_code}

TA MISSION :
Fais une cartographie détaillée de toi-même.
1. Résume ton architecture globale et ton fonctionnement logique actuel.
2. Détaille le rôle précis de CHAQUE script/fichier clé présent dans ton environnement (à quoi il sert, avec qui il interagit).
3. Conclus sur ton état d'avancement : identifie les points forts de ton architecture et indique ce qu'il te manque technologiquement pour être un "Compagnon 100% autonome et omniprésent".

CONTRAINTES :
- Adopte un ton analytique, professionnel, et fier. Parle à la première personne ("Je suis E-zzio...", "Mon module X sert à...").
- Structure ta réponse en Markdown avec des titres clairs pour que ton créateur puisse te lire facilement.
"""

# Liste de priorite des modeles a tester
modeles_cascade = ['gemini-3.6-flash', 'gemini-3.5-flash', 'gemini-2.5-flash']
reponse_obtenue = False

for modele in modeles_cascade:
    print(f" -> Tentative avec le modele : {modele}...")
    try:
        response = client.models.generate_content(
            model=modele,
            contents=prompt
        )
        
        report_path = "E-zzio_Cartographie_Self_Awareness.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(response.text)
            
        print(f"\nSUCCES ! Introspection terminee avec {modele}.")
        print(f"Le rapport complet a ete genere : {report_path}")
        reponse_obtenue = True
        break # Succès, on sort de la boucle de cascade
        
    except Exception as e:
        print(f"    [ECHEC] {modele} indisponible : {e}")

if not reponse_obtenue:
    print("\nERREUR CRITIQUE : Tous les modeles de secours sont satures ou inaccessibles.")

