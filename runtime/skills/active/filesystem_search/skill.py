from pathlib import Path
import os

def run(params: dict) -> dict:
    query = params.get("query", "")
    target_dir = params.get("path", ".")
    
    results = []
    root_path = Path(target_dir)
    
    if not root_path.exists():
        return {"success": False, "error": f"Chemin introuvable: {target_dir}"}

    for path in root_path.rglob(f"*{query}*"):
        if path.is_file():
            results.append({
                "name": path.name,
                "path": str(path.resolve()),
                "size_bytes": path.stat().st_size
            })
            if len(results) >= 20: # Limite de sécurité
                break

    return {
        "success": True,
        "count": len(results),
        "results": results
    }
