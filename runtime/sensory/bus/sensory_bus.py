"""
E-ZZIO V9 — Sensory Bus
Achemine les Percepts des capteurs vers le moteur de fusion (sans prise de décision).
"""

from queue import Queue
from typing import List
from .percept import Percept


class SensoryBus:
    def __init__(self):
        self._stream = Queue(maxsize=100)
        self._history: List[Percept] = []

    def transmit(self, percept: Percept):
        if not self._stream.full():
            self._stream.put(percept)
            self._history.append(percept)

            # Rotation de l'historique léger (mémoire à court terme du bus)
            if len(self._history) > 50:
                self._history.pop(0)

    def consume_all(self) -> List[dict]:
        percepts = []
        while not self._stream.empty():
            percepts.append(self._stream.get().to_dict())
        return percepts
