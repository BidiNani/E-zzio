"""
E-ZZIO V9.0.2 — Autonomic Watcher (Sensory Daemon)
Boucle de surveillance asynchrone appliquant le filtre d'efférence (anti-bruit).
Ne réveille l'organisme que si le budget d'attention change.
"""
import time
import threading
from typing import Optional, Callable
from runtime.sensory.bus.sensory_bus import SensoryBus
from runtime.sensory.sensors.proprioception_sensor import ProprioceptionSensor

class AutonomicWatcher:
    def __init__(self, bus: SensoryBus, interval_sec: int = 5):
        self.bus = bus
        self.sensor = ProprioceptionSensor()
        self.interval = interval_sec
        self._running = False
        self._thread: Optional[threading.Thread] = None
        
        # Filtre d'efférence : mémorise le dernier état d'attention
        self.last_attention_state = "UNKNOWN"
        
        # Callback pour réveiller le système extérieur uniquement en cas d'alerte
        self.on_state_change: Optional[Callable] = None

    def start(self):
        if not self._running:
            self._running = True
            self._thread = threading.Thread(target=self._loop, daemon=True, name="SensoryDaemon")
            self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)

    def _loop(self):
        while self._running:
            try:
                # 1. Sensation (Capture de l'état)
                percept = self.sensor.sense()
                
                # 2. Routage dans le bus
                self.bus.transmit(percept)
                
                # 3. Efference Copy (Filtre anti-bruit)
                current_attention = percept.priority
                
                if current_attention != self.last_attention_state:
                    # Changement d'état détecté ! On déclenche l'alerte.
                    if self.on_state_change:
                        self.on_state_change(self.last_attention_state, current_attention, percept)
                    self.last_attention_state = current_attention

            except Exception:
                # Un sens périphérique ne doit jamais faire crasher l'organisme
                pass
            
            # Respiration du thread
            time.sleep(self.interval)
