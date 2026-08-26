import uuid
import threading
from typing import Dict


class BudgetTransaction:
    """Context manager garantissant le commit ou le rollback automatique."""

    def __init__(self, manager: "BudgetManager", cost: int):
        self.manager = manager
        self.cost = cost
        self.res_id = None

    def __enter__(self):
        self.res_id = self.manager.reserve(self.cost)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.manager.commit(self.res_id)
        else:
            self.manager.rollback(self.res_id)
        return False  # Ne masque pas l'exception d'origine


class BudgetManager:
    """Gestionnaire de budget thread-safe avec mode transactionnel nativement intégré."""

    def __init__(self, max_actions: int = 50):
        self.max_actions = max_actions
        self.used_actions = 0
        self.reservations: Dict[str, int] = {}
        self._lock = threading.Lock()

    def transaction(self, cost: int = 1) -> BudgetTransaction:
        return BudgetTransaction(self, cost)

    def reserve(self, cost: int = 1) -> str:
        with self._lock:
            if self.used_actions + sum(self.reservations.values()) + cost > self.max_actions:
                raise PermissionError("Budget de session épuisé.")
            res_id = str(uuid.uuid4())
            self.reservations[res_id] = cost
            return res_id

    def commit(self, res_id: str):
        with self._lock:
            if res_id in self.reservations:
                self.used_actions += self.reservations.pop(res_id)

    def rollback(self, res_id: str):
        with self._lock:
            if res_id in self.reservations:
                self.reservations.pop(res_id)
