import ast
import difflib
import os
import shutil

from tools.guard import check_for_infinite_loop, is_path_allowed


def generate_unified_diff(original_text: str, modified_text: str, file_path: str) -> str:
    """Génère un patch au format Unified Diff standard."""
    orig_lines = original_text.splitlines(keepends=True)
    mod_lines = modified_text.splitlines(keepends=True)

    diff = difflib.unified_diff(orig_lines, mod_lines, fromfile=f"a/{file_path}", tofile=f"b/{file_path}")
    return "".join(diff)


def calculate_confidence_score(file_path: str, new_content: str) -> tuple[float, list[str]]:
    """Calcule le score de confiance global avant validation (0 à 100%)."""
    score = 100.0
    logs = []

    # 1. Contrôle d'accès
    allowed, msg = is_path_allowed(file_path)
    if not allowed:
        return 0.0, [msg]

    # 2. Contrôle de boucle infinie
    is_loop, hash_msg = check_for_infinite_loop(new_content)
    if is_loop:
        return 0.0, [hash_msg]

    # 3. Validation de la syntaxe Python (AST)
    if file_path.endswith(".py"):
        try:
            ast.parse(new_content)
            logs.append("✅ Syntaxe Python AST : 100%")
        except SyntaxError as e:
            score -= 60.0
            logs.append(f"❌ Erreur de syntaxe Python (Ligne {e.lineno}) : -60%")

    # 4. Analyse de la taille du Diff
    if os.path.exists(file_path):
        with open(file_path, encoding="utf-8", errors="ignore") as f:
            old_content = f.read()

        diff_lines = len(list(difflib.unified_diff(old_content.splitlines(), new_content.splitlines())))
        if diff_lines > 150:
            score -= 15.0
            logs.append(f"⚠️ Diff très volumineux ({diff_lines} lignes modifiées) : -15%")

    return max(0.0, score), logs


def apply_patch_safely(file_path: str, new_content: str) -> str:
    """Applique la modification de manière atomique avec sauvegarde .bak et .patch."""
    # 1. Calcul du Score de Confiance
    score, audit_logs = calculate_confidence_score(file_path, new_content)

    if score < 80.0:
        return f"❌ ÉCHEC DE LA GOUVERNANCE (Score de confiance : {score}%)\n" + "\n".join(audit_logs)

    try:
        # 2. Lecture ancien contenu pour le .patch
        old_content = ""
        if os.path.exists(file_path):
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                old_content = f.read()
            # Sauvegarde préventive .bak
            shutil.copy2(file_path, file_path + ".bak")

        # 3. Enregistrement du fichier .patch
        patch_text = generate_unified_diff(old_content, new_content, file_path)
        with open(file_path + ".patch", "w", encoding="utf-8") as f:
            f.write(patch_text)

        # 4. Écriture atomique dans un fichier .tmp puis deplacement
        tmp_path = file_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        os.replace(tmp_path, file_path)

        return f"✅ PATCH APPLIQUÉ AVEC SUCCÈS (Score de confiance : {score}%)\n" + "\n".join(audit_logs)

    except Exception as e:
        # Rollback d'urgence
        if os.path.exists(file_path + ".bak"):
            shutil.copy2(file_path + ".bak", file_path)
        return f"❌ ERREUR SÉVÈRE - ROLLBACK EFFECTUÉ : {e}"
