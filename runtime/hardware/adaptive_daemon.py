import time
import psutil
from .governor_service import HardwareGovernorService

class AdaptiveHardwareDaemon:
    """
    Moteur auto-adaptatif surveillant la télémétrie système.
    Intègre un timer d'hystérésis pour éviter le battement (flapping) de profil.
    """
    def __init__(self, governor: HardwareGovernorService, hysteresis_sec: float = 5.0):
        self.governor = governor
        self.hysteresis_sec = hysteresis_sec
        self.last_switch_time = 0
        
        # Liste indicative des processus déclencheurs du mode GAMING
        self.gaming_targets = {"steam.exe", "unreal.exe", "cyberpunk2077.exe", "wow.exe", "leagueoflegends.exe"}

    def evaluate_system_state(self) -> str:
        """Analyse les processus et la charge CPU/RAM pour déterminer le profil idéal."""
        now = time.time()
        if (now - self.last_switch_time) < self.hysteresis_sec:
            return self.governor.current_profile

        detected_gaming = False
        try:
            for proc in psutil.process_iter(['name']):
                p_name = proc.info['name']
                if p_name and p_name.lower() in self.gaming_targets:
                    detected_gaming = True
                    break
        except Exception:
            pass

        target_profile = "COMPUTE"
        if detected_gaming:
            target_profile = "GAMING"

        if target_profile != self.governor.current_profile:
            self.governor.set_profile(target_profile)
            self.last_switch_time = now

        return target_profile
