from pathlib import Path
import re

provider_file = Path(r"G:\AI\E-zzio\runtime\model_router\providers\ollama.py")

if not provider_file.exists():
    print("[FAIL] ollama.py introuvable.")
    exit(1)

content = provider_file.read_text(encoding="utf-8")

# Vérification et remplacement de la signature de generate pour accepter **kwargs / options
# On recherche une définition de type "def generate(self, ...):"
if "def generate(" in content:
    # Remplacement sécurisé pour accepter **kwargs ou options dynamiques
    # Si la méthode n'a pas déjà **kwargs, on s'assure qu'elle les intercepte
    print("[INFO] Analyse et mise à jour de la méthode generate dans ollama.py...")
    
    # Pattern pour intercepter la définition de generate
    # On injecte **kwargs si absent pour éviter le TypeError
    old_def_pattern = re.compile(r"def generate\(self,\s*prompt,\s*model[^)]*\):")
    
    new_def = "def generate(self, prompt, model, **kwargs):"
    
    if old_def_pattern.search(content):
        content = old_def_pattern.sub(new_def, content)
        print("[OK] Signature de generate() mise à jour avec **kwargs.")
    else:
        # Fallback global si la signature diffère légèrement
        content = content.replace("def generate(self, prompt, model):", "def generate(self, prompt, model, **kwargs):")

    # S'assurer que le dictionnaire envoyé à l'API Ollama intègre les options issues de kwargs
    payload_injection = """
        # Construction sécurisée des options pour Ollama
        options = {
            "num_ctx": kwargs.get("num_ctx", 4096),
            "num_predict": kwargs.get("num_predict", 512),
            "temperature": kwargs.get("temperature", 0.7)
        }
        if "think" in kwargs:
            options["think"] = kwargs["think"]
            
        # Fusion avec d'éventuels kwargs supplémentaires non listés
        for k, v in kwargs.items():
            if k not in options:
                options[k] = v
    """
    
    if "options =" not in content and "json=" in content:
        # Injection des options dans le payload JSON juste avant l'appel request
        content = content.replace("payload = {", payload_injection + "\n        payload = {")
        content = content.replace('"options":', '"options": options, #') # Active ou complète le champ options si présent

    provider_file.write_text(content, encoding="utf-8")
    print("[OK] Provider Ollama patché avec succès.")
else:
    print("[FAIL] Méthode generate introuvable dans ollama.py.")
