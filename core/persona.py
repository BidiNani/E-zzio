from pathlib import Path

class PersonaLoader:
    """Chargeur centralisé de la personnalité et du lore d'E-zzio."""
    def __init__(self, base_dir: str = "runtime/identity"):
        self.base_dir = Path(base_dir)

    def load_lore(self) -> str:
        lore_path = self.base_dir / "lore.md"
        if lore_path.exists():
            return lore_path.read_text(encoding="utf-8")
        return "Lore non disponible."

    def load_persona(self) -> str:
        persona_path = self.base_dir / "persona.full.md"
        if persona_path.exists():
            return persona_path.read_text(encoding="utf-8")
        return "Persona non disponible."

    def get_system_prompt_identity(self) -> str:
        persona = self.load_persona()
        lore = self.load_lore()
        return f"=== PERSONA IDENTITY ===\n{persona}\n\n=== LORE & ORIGIN ===\n{lore}"

# Instance globale prête pour l'injection dans le LLM Engine
persona_loader = PersonaLoader()