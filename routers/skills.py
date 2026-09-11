from fastapi import APIRouter, HTTPException, Body
from pathlib import Path
import sys

# Import du gestionnaire de skills
sys.path.append(str(Path(__file__).resolve().parent.parent / "runtime" / "skills"))
from skill_manager import EzzioSkillManager

router = APIRouter(prefix="/api/skills", tags=["Auto-Evolution Skills"])
manager = EzzioSkillManager()


@router.post("/deploy")
def deploy_and_load_skill(payload: dict = Body(...)):
    """
    Reçoit un nom de fichier et un code source brut,
    le place en staging, le valide via AST et l'importe à chaud.
    """
    filename = payload.get("filename")
    code = payload.get("code")

    if not filename or not code:
        raise HTTPException(status_code=400, detail="Les champs 'filename' et 'code' sont requis.")

    # 1. Écriture dans le dossier staging
    staging_file = manager.staging_dir / filename
    try:
        staging_file.write_text(code, encoding="utf-8")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur d'écriture en staging : {str(e)}")

    # 2. Exécution du pipeline (Validation AST -> Promotion -> Hot-Reload)
    result = manager.promote_and_load(filename)

    if not result.get("ok"):
        return {"status": "rejected", "message": "Le skill a échoué aux tests de sécurité du micro-noyau.", "details": result}

    return {"status": "success", "message": "Skill validé, promu et chargé en mémoire avec succès.", "details": result}


@router.get("/active")
def list_active_skills():
    """Liste l'ensemble des skills actuellement actifs et chargés en mémoire."""
    return {"active_skills": list(manager.loaded_skills.keys()), "count": len(manager.loaded_skills)}
