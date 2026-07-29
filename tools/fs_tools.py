import os
import shutil
import ast
import json
import datetime

AUDIT_LOG_PATH = r"G:\AI\E-zzio\data\fs_audit.log"

def _log_audit(action: str, details: str):
    """Enregistre chaque opération de fichier dans un journal d'audit."""
    try:
        os.makedirs(os.path.dirname(AUDIT_LOG_PATH), exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] [{action}] {details}\n")
    except Exception:
        pass

def validate_syntax(content: str, file_path: str) -> tuple[bool, str]:
    """Vérifie la syntaxe du contenu avant écriture (Python, JSON)."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".py":
        try:
            ast.parse(content)
            return True, "Syntaxe Python valide."
        except SyntaxError as e:
            return False, f"Erreur de syntaxe Python (Ligne {e.lineno}): {e.msg}"
    elif ext == ".json":
        try:
            json.loads(content)
            return True, "JSON valide."
        except Exception as e:
            return False, f"JSON invalide: {e}"
    return True, "Format non contrôlé (supposé valide)."

def list_directory(folder_path: str, limit: int = 50) -> str:
    """Liste et trie le contenu d'un répertoire sur le disque."""
    if not os.path.exists(folder_path):
        return f"❌ Dossier introuvable : {folder_path}"
    try:
        items = sorted(os.listdir(folder_path))
        formatted = []
        for item in items[:limit]:
            full_path = os.path.join(folder_path, item)
            kind = "📁 [DIR]" if os.path.isdir(full_path) else "📄 [FILE]"
            formatted.append(f"{kind} {item}")
        return "\n".join(formatted) if formatted else "Dossier vide."
    except Exception as e:
        return f"❌ Erreur d'accès au dossier : {e}"

def read_file(file_path: str, max_lines: int = 400) -> str:
    """Lit le contenu d'un fichier texte ou code sur le disque."""
    if not os.path.exists(file_path):
        return f"❌ Fichier introuvable : {file_path}"
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = [f.readline() for _ in range(max_lines)]
        return "".join(lines)
    except Exception as e:
        return f"❌ Erreur lors de la lecture : {e}"

def write_file(file_path: str, content: str, make_backup: bool = True, validate: bool = True) -> str:
    """Crée ou écrase un fichier de manière atomique avec backup et validation."""
    if validate:
        is_valid, msg = validate_syntax(content, file_path)
        if not is_valid:
            return f"❌ Écriture annulée (Validation échouée) : {msg}"

    try:
        # 1. Sauvegarde préventive (.bak)
        if make_backup and os.path.exists(file_path):
            shutil.copy2(file_path, file_path + ".bak")

        # 2. Gestion propre du dossier parent
        parent = os.path.dirname(file_path)
        if parent:
            os.makedirs(parent, exist_ok=True)

        # 3. Écriture atomique (.tmp -> replace)
        tmp_path = file_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(content)

        os.replace(tmp_path, file_path)
        _log_audit("WRITE_FILE", f"Succès: {file_path}")
        return f"✅ Fichier écrit avec succès (Écriture atomique) : {file_path}"
    except Exception as e:
        if os.path.exists(file_path + ".tmp"):
            try: os.remove(file_path + ".tmp")
            except: pass
        return f"❌ Erreur lors de l'écriture : {e}"

def replace_in_file(file_path: str, old_text: str, new_text: str, count: int = 1, make_backup: bool = True, validate: bool = True) -> str:
    """Remplace une chaîne par une autre avec backup et contrôle d'occurrence."""
    if not os.path.exists(file_path):
        return f"❌ Fichier introuvable : {file_path}"
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        if old_text not in content:
            return f"⚠️ Le texte cible n'a pas été trouvé dans {file_path}."

        new_content = content.replace(old_text, new_text, count) if count > 0 else content.replace(old_text, new_text)

        if validate:
            is_valid, msg = validate_syntax(new_content, file_path)
            if not is_valid:
                return f"❌ Modification annulée (Erreur de syntaxe générée) : {msg}"

        if make_backup:
            shutil.copy2(file_path, file_path + ".bak")

        tmp_path = file_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        os.replace(tmp_path, file_path)
        _log_audit("REPLACE_IN_FILE", f"Modifié: {file_path}")
        return f"✅ Remplacement effectué dans {file_path} (Backup .bak créé)"
    except Exception as e:
        return f"❌ Erreur lors de la modification : {e}"

def restore_backup(file_path: str) -> str:
    """Restaure la version précédente d'un fichier depuis sa sauvegarde .bak."""
    backup_path = file_path + ".bak"
    if not os.path.exists(backup_path):
        return f"❌ Aucune sauvegarde (.bak) trouvée pour {file_path}"
    try:
        shutil.copy2(backup_path, file_path)
        _log_audit("RESTORE_BACKUP", f"Restauration: {file_path}")
        return f"✅ Fichier restauré avec succès depuis {backup_path}"
    except Exception as e:
        return f"❌ Erreur lors de la restauration : {e}"

def delete_file(file_path: str, make_backup: bool = True) -> str:
    """Supprime un fichier en conservant une copie de secours .bak."""
    if not os.path.exists(file_path):
        return f"❌ Fichier introuvable : {file_path}"
    try:
        if make_backup:
            shutil.copy2(file_path, file_path + ".bak")
        os.remove(file_path)
        _log_audit("DELETE_FILE", f"Supprimé: {file_path}")
        return f"✅ Fichier supprimé : {file_path} (Sauvegarde .bak conservée)"
    except Exception as e:
        return f"❌ Erreur lors de la suppression : {e}"

def copy_file(src: str, dst: str) -> str:
    """Copie un fichier d'un emplacement à un autre."""
    try:
        parent = os.path.dirname(dst)
        if parent: os.makedirs(parent, exist_ok=True)
        shutil.copy2(src, dst)
        _log_audit("COPY_FILE", f"De {src} vers {dst}")
        return f"✅ Fichier copié de {src} vers {dst}"
    except Exception as e:
        return f"❌ Erreur lors de la copie : {e}"

def move_file(src: str, dst: str) -> str:
    """Déplace un fichier d'un emplacement à un autre."""
    try:
        parent = os.path.dirname(dst)
        if parent: os.makedirs(parent, exist_ok=True)
        shutil.move(src, dst)
        _log_audit("MOVE_FILE", f"De {src} vers {dst}")
        return f"✅ Fichier déplacé de {src} vers {dst}"
    except Exception as e:
        return f"❌ Erreur lors du déplacement : {e}"
