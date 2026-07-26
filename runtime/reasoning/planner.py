from typing import Dict, Any, List

class DeterministicPlanner:
    """Deterministic task planner translating cognitive analysis into concrete actions."""
    @staticmethod
    def plan(analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        importance = analysis.get("importance", 0.5)
        category = analysis.get("category", "general")
        requires_action = analysis.get("requires_action", False)

        if not requires_action or importance < 0.5:
            return [{"action": "IGNORE", "reason": "Importance or threshold insufficient"}]

        plans = []
        if category == "news_feed" or category == "tech":
            plans.append({"action": "STORE_KNOWLEDGE", "priority": int(importance * 10)})
            plans.append({"action": "NOTIFY_USER", "priority": int(importance * 8)})
        else:
            plans.append({"action": "STORE_KNOWLEDGE", "priority": int(importance * 10)})

        return plans
