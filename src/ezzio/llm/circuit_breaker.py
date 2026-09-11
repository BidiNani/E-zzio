"""
Circuit Breaker Pattern pour la bascule résiliente Cloud / Local d'E-ZzIO.
Gère les états CLOSED (nominal), OPEN (panne cloud -> repli local immédiat), HALF_OPEN (sonde de rétablissement).
"""

import time
import logging
from enum import Enum

logger = logging.getLogger("EzzioCircuitBreaker")


class CircuitState(str, Enum):
    CLOSED = "CLOSED"      # Cloud actif et sain
    OPEN = "OPEN"          # Cloud en panne -> repli local immédiat sans latence
    HALF_OPEN = "HALF_OPEN"# Tentative de reconnexion


class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 2,
        cooldown_seconds: float = 30.0,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        self.last_state_change = time.time()

    def can_attempt_cloud(self) -> bool:
        """Indique si un appel Cloud peut être tenté sans risquer un blocage."""
        now = time.time()
        if self.state == CircuitState.CLOSED:
            return True
        elif self.state == CircuitState.OPEN:
            if now - self.last_state_change >= self.cooldown_seconds:
                logger.info("[CIRCUIT-BREAKER] Cooldown expiré -> Passage en HALF_OPEN pour tester le Cloud.")
                self.state = CircuitState.HALF_OPEN
                self.last_state_change = now
                return True
            return False
        elif self.state == CircuitState.HALF_OPEN:
            return True
        return False

    def record_success(self) -> None:
        """Enregistre un succès Cloud et rétablit l'état CLOSED."""
        if self.state != CircuitState.CLOSED:
            logger.info("[CIRCUIT-BREAKER] Rétablissement du Cloud confirmé -> Retour en état CLOSED.")
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        self.last_state_change = time.time()

    def record_failure(self, error: Exception | str) -> None:
        """Enregistre un échec Cloud et ouvre le disjoncteur si le seuil est dépassé."""
        self.failure_count += 1
        logger.warning(
            "[CIRCUIT-BREAKER] Échec Cloud (%d/%d) : %s",
            self.failure_count, self.failure_threshold, error
        )
        if self.failure_count >= self.failure_threshold or self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            self.last_state_change = time.time()
            logger.warning(
                "[CIRCUIT-BREAKER] Disjoncteur OUVERT (OPEN). Bascule automatique 100%% locale pendant %ds.",
                self.cooldown_seconds
            )


# Instance globale partagée
circuit_breaker = CircuitBreaker()
