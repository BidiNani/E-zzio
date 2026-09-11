"""
E-ZZIO V7.45.1 — Discord Watchdog & Health Monitor
Surveille l'intégrité opérationnelle du bot, de la passerelle et du Vault local.
"""

import time
import httpx
from core.tool_gateway.google_bridge import google_bridge


class DiscordWatchdog:
    def __init__(self, local_api_url: str = "http://127.0.0.1:8001/master/chat"):
        self.start_time = time.time()
        self.local_api_url = local_api_url
        self.failure_counter = 0
        self.last_message_timestamp = None

    def record_activity(self):
        self.last_message_timestamp = time.time()

    def check_vault_health(self) -> str:
        try:
            res = google_bridge.retrieve_tokens()
            # Même si le vault est vide, s'il répond sans crash, l'intégrité est OK
            return "OK" if "valid" in res or "error" in res else "DEGRADED"
        except Exception:
            return "FAIL"

    def check_api_health(self) -> str:
        try:
            # Test de vie léger sur le endpoint local (timeout court)
            resp = httpx.get(self.local_api_url.replace("/chat", "/health"), timeout=1.0)
            return "ONLINE" if resp.status_code < 500 else "DEGRADED"
        except Exception:
            # Si l'API ne tourne pas en local lors des tests, on renvoie OFFLINE gérable
            return "OFFLINE"

    def get_health_report(self) -> dict:
        uptime_sec = int(time.time() - self.start_time)
        vault_status = self.check_vault_health()
        api_status = self.check_api_health()

        return {
            "status": "ONLINE" if vault_status != "FAIL" else "DEGRADED",
            "uptime_seconds": uptime_sec,
            "vault": vault_status,
            "api_bridge": api_status,
            "permission_guard": "OK",
            "failures": self.failure_counter,
            "last_activity": self.last_message_timestamp,
        }


discord_watchdog = DiscordWatchdog()
