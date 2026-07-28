import re

class CommandPolicyEngine:
    """Valide les commandes externes selon une politique de sécurité déclarative."""
    
    @staticmethod
    def validate(command: str, constraints: dict) -> tuple[bool, str]:
        allowed = constraints.get("allowed_commands", [])
        blocked = constraints.get("blocked_commands", [])

        # 1. Vérification stricte de la Blocklist (Fail-Fast)
        lower_cmd = command.lower()
        for b in blocked:
            # Recherche de mot entier pour éviter les faux positifs
            if re.search(rf'\b{b.lower()}\b', lower_cmd):
                return False, f"Mot-clé ou commande interdite détectée : '{b}'"

        # 2. Vérification de l'Allowlist (La commande principale doit être autorisée)
        if not allowed:
            return False, "Aucune commande autorisée dans la politique (Allowlist vide)."

        first_word = re.split(r'\s+', command.strip())[0].lower()
        allowed_lower = [a.lower() for a in allowed]

        if first_word not in allowed_lower:
            return False, f"Commande principale non reconnue ou interdite : '{first_word}'"

        return True, "OK"