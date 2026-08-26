import platform
import psutil


class DynamicCPUTopology:
    """
    Détection dynamique de la topologie processeur avec spécialisation Ryzen 5900X.
    """

    def __init__(self):
        self.total_logical = psutil.cpu_count(logical=True) or 24
        self.total_physical = psutil.cpu_count(logical=False) or 12
        self.vendor_id = platform.processor()

        # Spécialisation Ryzen 9 5900X (24 threads / 2 CCDs)
        if self.total_logical == 24 and self.total_physical == 12:
            self.is_ryzen_5900x = True
            self.ccd0_threads = list(range(0, 12))
            self.ccd1_threads = list(range(12, 24))
            self.compute_threads = list(range(2, 24))
        else:
            self.is_ryzen_5900x = False
            half = max(1, self.total_logical // 2)
            self.ccd0_threads = list(range(0, half))
            self.ccd1_threads = list(range(half, self.total_logical))
            self.compute_threads = list(range(max(1, self.total_logical // 4), self.total_logical))

        self.all_threads = list(range(self.total_logical))

    def get_mask_for_profile(self, profile_name: str) -> list[int]:
        profile = profile_name.upper()
        if profile == "GAMING":
            return self.ccd1_threads
        elif profile == "COMPUTE":
            return self.compute_threads
        elif profile == "EVOLUTION":
            return self.all_threads
        else:
            return self.all_threads
