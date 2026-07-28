import os
import re

print("[*] E-ZZIO v1.9.1.4 - Déploiement de l'Algorithme de Résolution Absolue...")

# ------------------------------------------------------------------------------
# 1. SQLITE STORE FIX : RECONSTRUCTION CHIRURGICALE
# ------------------------------------------------------------------------------
store_path = "runtime/action/store.py"
if os.path.exists(store_path):
    with open(store_path, "r", encoding="utf-8") as f:
        code = f.read()

    # On écrase totalement l'ancienne requête mutée pour y placer le SQL pur et validé
    code = re.sub(
        r'"SELECT exec_id, action_name, status, payload, result, cost, duration_ms, timestamp FROM execution_ledger WHERE action_name = \?.*?"',
        '"SELECT exec_id, action_name, status, payload, result, cost, duration_ms, timestamp FROM execution_ledger WHERE action_name = ? ORDER BY rowid DESC LIMIT ?"',
        code, flags=re.DOTALL
    )
    
    code = re.sub(
        r'"SELECT from_state, to_state, timestamp, signature FROM state_transitions WHERE exec_id = \?.*?"',
        '"SELECT from_state, to_state, timestamp, signature FROM state_transitions WHERE exec_id = ? ORDER BY rowid ASC"',
        code, flags=re.DOTALL
    )
    
    # Restauration de sécurité au cas où la signature Python aurait été corrompue
    code = re.sub(r'ORDER BY rowid DESC LIMIT: int = 50', 'limit: int = 50', code)

    with open(store_path, "w", encoding="utf-8") as f:
        f.write(code)
    print("[+] store.py : Requêtes SQLite réinitialisées sur 'ORDER BY rowid DESC'.")

# ------------------------------------------------------------------------------
# 2. NETTOYAGE DES EXÉCUTEURS (Conversion en pur dictionnaire)
# ------------------------------------------------------------------------------
executors = [
    "runtime/tools/executors/powershell.py",
    "runtime/tools/executors/filesystem.py",
    "runtime/tools/executors/git.py"
]

for path in executors:
    if not os.path.exists(path): continue
    with open(path, "r", encoding="utf-8") as f:
        code = f.read()

    # Éradication de toutes les anciennes classes ToolResult injectées
    code = re.sub(r'class ToolResult[\s\S]*?(?=class [A-Za-z]+Executor)', '', code)
    
    # Transformation de l'instanciation ToolResult(...) en dict(...)
    code = re.sub(r'\bToolResult\(', 'dict(', code)

    with open(path, "w", encoding="utf-8") as f:
        f.write(code)
    print(f"[+] {os.path.basename(path):<20} : Converti au format Dictionnaire Natif.")

# ------------------------------------------------------------------------------
# 3. IMMUNITÉ SUPERVISEUR (Patch global du dot-access sur les dict)
# ------------------------------------------------------------------------------
patched_files = 0
for root, dirs, files in os.walk("runtime"):
    for file in files:
        if file.endswith(".py"):
            path = os.path.join(root, file)
            with open(path, "r", encoding="utf-8") as f:
                code = f.read()

            new_code = code
            # On intercepte les accès risqués (res.metadata) et on les sécurise dynamiquement
            new_code = re.sub(r'\b(res|result|out)\.metadata\b', r'(\1.get("metadata", {}) if isinstance(\1, dict) else getattr(\1, "metadata", {}))', new_code)
            new_code = re.sub(r'\b(res|result|out)\.success\b', r'(\1.get("success", False) if isinstance(\1, dict) else getattr(\1, "success", False))', new_code)
            new_code = re.sub(r'\b(res|result|out)\.error\b', r'(\1.get("error", "") if isinstance(\1, dict) else getattr(\1, "error", ""))', new_code)
            new_code = re.sub(r'\b(res|result|out)\.output\b', r'(\1.get("output", "") if isinstance(\1, dict) else getattr(\1, "output", ""))', new_code)

            if new_code != code:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(new_code)
                patched_files += 1

print(f"[+] Immunités dictionnaire injectées dans {patched_files} fichiers du système.")
