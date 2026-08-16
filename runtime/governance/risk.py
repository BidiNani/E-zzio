class RiskEngine:
    @staticmethod
    def calculate_risk(action: str, target: str, resource_cost: dict) -> float:
        """
        Recalcule objectivement le score de risque. L'agent ne peut pas fixer son propre risque.
        """
        base_risk = 0.1
        
        # Facteur cible critique
        if "kernel" in target or "policy" in target or "engine" in target:
            base_risk += 0.5
        elif "contracts" in target or "registry" in target:
            base_risk += 0.3

        # Facteur action sensible
        if "modify" in action or "delete" in action or "execute" in action:
            base_risk += 0.3

        # Facteur coût en ressources
        cpu_cost = resource_cost.get("cpu", 0)
        if cpu_cost > 4:
            base_risk += 0.1

        return min(round(base_risk, 2), 1.0)
