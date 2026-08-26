from __future__ import annotations
import threading
import time
import logging
from runtime.kernel.context import RuntimeContext
from runtime.events.bus import Event
from runtime.kernel.state import RuntimePhase


class RuntimeWatchdog(threading.Thread):
    """
    Chien de garde du Runtime.
    Surveille en arrière-plan la santé de l'OS, la charge du Governor et l'état de la machine d'état.
    """

    def __init__(self, context: RuntimeContext, check_interval_sec: float = 2.0):
        super().__init__(daemon=True)
        self.context = context
        self.interval = check_interval_sec
        self._stop_event = threading.Event()
        self.health_status = "HEALTHY"

    def run(self):
        logging.info("[WATCHDOG] Chien de garde du Runtime activé.")
        while not self._stop_event.is_set():
            try:
                # 1. Vérification de la phase du noyau
                phase = self.context.state.current_phase
                if phase == RuntimePhase.PANIC or phase == RuntimePhase.HALTED:
                    self.health_status = "CRITICAL"
                    break

                # 2. Audit de la charge du Governor
                active_workers = self.context.governor._active_workers
                max_workers = self.context.governor.limits.get("max_parallel_workers", 8)

                if active_workers >= max_workers:
                    self.health_status = "CONGESTED"
                    self.context.bus.publish(
                        Event(
                            type="RuntimeCongested",
                            actor="RuntimeWatchdog",
                            source="governance.watchdog",
                            payload={"active_workers": active_workers, "max_workers": max_workers},
                        )
                    )
                else:
                    self.health_status = "HEALTHY"

            except Exception as e:
                logging.error(f"[WATCHDOG] Erreur durant le cycle de surveillance : {e}")
                self.health_status = "DEGRADED"

            time.sleep(self.interval)

    def stop(self):
        self._stop_event.set()
