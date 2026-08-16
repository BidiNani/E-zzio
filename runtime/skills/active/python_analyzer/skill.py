import ast
from pathlib import Path

def run(params: dict) -> dict:
    target_path = params.get("path", "")
    file_path = Path(target_path)
    
    if not file_path.exists() or not file_path.is_file():
        return {"success": False, "error": f"Fichier Python introuvable : {target_path}"}
    
    try:
        source_code = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source_code, filename=str(file_path))
        
        functions = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        
        return {
            "success": True,
            "file": str(file_path.resolve()),
            "functions_count": len(functions),
            "classes_count": len(classes),
            "functions": functions,
            "classes": classes,
            "syntax_valid": True
        }
    except SyntaxError as e:
        return {
            "success": True,
            "syntax_valid": False,
            "error": str(e),
            "line": e.lineno
        }
    except Exception as ex:
        return {"success": False, "error": str(ex)}
