import logging


class PolicyDecision:
    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRE_HUMAN = "REQUIRE_HUMAN"


class PolicyEngine:
    """Le Gatekeeper unifié. Vérifie la constitution et la réputation (Trust Score) de l'acteur."""

    def __init__(self, constitution: dict, trust_scorer=None):
        self.constitution = constitution
        self.trust_scorer = trust_scorer

    def evaluate_intent(self, actor: str, action: str, target: str, context_permissions: list) -> str:
        # 1. Vérification du Trust Score (Quarantaine si score insuffisant)
        if self.trust_scorer is not None:
            if not self.trust_scorer.is_trusted(actor, threshold=50.0):
                score = self.trust_scorer.get_score(actor)
                logging.warning(f"[POLICY] QUARANTINE DENY: L'acteur '{actor}' a un score de confiance insuffisant ({score}/100).")
                return PolicyDecision.DENY

        # 2. Vérification des invariants (Kernel Lock)
        if self.constitution.get("kernel_lock"):
            for path in self.constitution.get("immutable_paths", []):
                if path in target:
                    logging.warning(f"[POLICY] DENY: Tentative de modification d'un chemin immuable ({target}) par {actor}")
                    return PolicyDecision.DENY

        # 3. Règles nécessitant une approbation humaine
        for rule in self.constitution.get("require_human_approval", []):
            if rule in action:
                logging.info(f"[POLICY] REQUIRE_HUMAN: Action sensible demandée ({action})")
                return PolicyDecision.REQUIRE_HUMAN

        # 4. Vérification des permissions
        if action not in context_permissions:
            logging.warning(f"[POLICY] DENY: L'acteur {actor} n'a pas la permission {action}")
            return PolicyDecision.DENY

        return PolicyDecision.ALLOW
