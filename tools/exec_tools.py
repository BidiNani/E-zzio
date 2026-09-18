import os
import subprocess
import sys


def test_python_syntax(file_path: str) -> str:
    """Vérifie la compilation d'un fichier Python sans l'exécuter."""
    if not os.path.exists(file_path):
        return f"❌ Fichier introuvable : {file_path}"
    try:
        result = subprocess.run([sys.executable, "-m", "py_compile", file_path], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            return "✅ Compilation Python réussie (Aucune erreur de syntaxe)."
        else:
            return f"❌ Erreur de compilation :\n{result.stderr}"
    except Exception as e:
        return f"❌ Erreur lors du test de compilation : {e}"


def run_python_script(file_path: str, timeout_sec: int = 15) -> str:
    """Exécute un script Python localement et renvoie stdout / stderr."""
    if not os.path.exists(file_path):
        return f"❌ Fichier introuvable : {file_path}"
    try:
        result = subprocess.run([sys.executable, file_path], capture_output=True, text=True, timeout=timeout_sec)
        output = []
        if result.stdout:
            output.append(f"--- STDOUT ---\n{result.stdout.strip()}")
        if result.stderr:
            output.append(f"--- STDERR (Erreur) ---\n{result.stderr.strip()}")

        status = "✅ EXÉCUTION RÉUSSIE (Exit code 0)" if result.returncode == 0 else f"❌ ÉCHEC D'EXÉCUTION (Exit code {result.returncode})"
        return f"{status}\n" + "\n".join(output)
    except subprocess.TimeoutExpired:
        return f"⚠️ Exécution interrompue : Timeout dépassé ({timeout_sec}s)."
    except Exception as e:
        return f"❌ Erreur d'exécution : {e}"


def run_powershell_command(command: str) -> str:
    """Exécute une commande PowerShell sécurisée et retourne le résultat."""
    try:
        result = subprocess.run(["powershell", "-NoProfile", "-Command", command], capture_output=True, text=True, timeout=15)
        out = result.stdout.strip() if result.stdout else ""
        err = result.stderr.strip() if result.stderr else ""

        if result.returncode == 0:
            return f"✅ Commande exécutée avec succès :\n{out}"
        else:
            return f"❌ Erreur PowerShell (Code {result.returncode}) :\n{err}\n{out}"
    except Exception as e:
        return f"❌ Erreur d'exécution PowerShell : {e}"
