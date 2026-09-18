import ast
import os


def run(args: dict, workspace_root: str) -> str:
    path = args.get("path", "")
    full_path = path if os.path.isabs(path) else os.path.join(workspace_root, path)
    if not os.path.exists(full_path):
        return f"[ERROR] Fichier introuvable pour analyse : {path}"

    with open(full_path, encoding="utf-8", errors="ignore") as f:
        code = f.read()

    try:
        tree = ast.parse(code)
        functions = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]

        report = {
            "file": path,
            "lines": len(code.splitlines()),
            "classes_count": len(classes),
            "classes": classes,
            "functions_count": len(functions),
            "functions": functions
        }
        return f"[SUCCESS] Analyse de code réussie :\n{report}"
    except Exception as exc:
        return f"[AST ERROR] Impossible d'analyser le code : {exc}"
