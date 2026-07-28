import json
from pathlib import Path
from runtime.state.state_manager import StateManager
from runtime.sensors.sensor_manager import SensorManager
from runtime.tools.manifest_loader import ManifestLoader

class ContextBuilder:
    def __init__(self, registry_build_dir="registry/build"):
        self.root_dir = Path(__file__).resolve().parents[2]
        self.build_dir = self.root_dir / registry_build_dir
        self.state_manager = StateManager()
        self.sensor_manager = SensorManager()

    def get_compiled_persona(self, profile="production"):
        persona_file = self.build_dir / f"persona.{profile}.md"
        if persona_file.exists():
            return persona_file.read_text(encoding="utf-8")
        
        master_file = self.root_dir / "registry" / "persona.txt"
        if master_file.exists():
            return master_file.read_text(encoding="utf-8")
        
        return "Tu es E-zzio, l'acolyte technique."

    def _get_tools_prompt_block(self) -> str:
        tools = ManifestLoader.get_tools()
        if not tools:
            return "[OUTILS DISPONIBLES]\nAucun outil enregistré ou erreur de manifest."
            
        lines = ["[OUTILS DISPONIBLES DYNAMIQUES]"]
        for name, config in tools.items():
            lines.append(f"• {name} : {config.get('description', '')} (Permission: {config.get('permission_level')})")
        
        rules = """
- INTERDICTION ABSOLUE d'inventer du contenu de fichier. Si tu as besoin d'un outil, ta réponse DOIT contenir EXCLUSIVEMENT et UNIQUEMENT un objet JSON brut, SANS AUCUNE balise markdown, sous ce format exact :
{
  "type": "tool_call",
  "tool": "nom_de_l_outil",
  "arguments": {
    "cle": "valeur"
  }
}
"""
        return "\n".join(lines) + "\n" + rules

    def build_full_prompt(self, user_query, memory, profile="production", thought_history=None):
        persona = self.get_compiled_persona(profile)
        state_block = self.state_manager.get_state_prompt_block()
        world_block = self.sensor_manager.get_world_state_prompt_block()
        tools_block = self._get_tools_prompt_block()
        
        trajectory_str = ""
        if thought_history and len(thought_history) > 0:
            traj_lines = ["[TRAJECTOIRE D'EXÉCUTION AGENT]"]
            for item in thought_history:
                traj_lines.append(f"- Étape {item.get('step')} | Outil appelé: {item.get('tool')} | Statut: {item.get('status')}")
            trajectory_str = "\n" + "\n".join(traj_lines) + "\n"

        recent_messages = memory.recent(6)
        history_str = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in recent_messages])

        full_prompt = f"""{persona}

{state_block}

{world_block}

{tools_block}
{trajectory_str}
[HISTORIQUE RÉCENT DE CONVERSATION]
{history_str}

USER: {user_query}
ASSISTANT:"""
        return full_prompt