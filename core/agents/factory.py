"""
E-ZZIO Core V10.2 — Governed Hierarchical Agent Factory & Sub-Agent Engine.
Gère la création dynamique de sous-agents, la propagation du budget,
la délégation de capacités, le contrôle de profondeur et le Kill Switch sous supervision Master.
"""
from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from core.agents.registry import (
    AgentDescriptor,
    AgentRegistry,
    AgentStatus,
    agent_registry,
)

logger = logging.getLogger("ezzio.agents.factory")


class HierarchicalLimitError(Exception):
    """Exception levée lorsque la profondeur maximale ou le nombre de sous-agents est dépassé."""
    pass


class BudgetExceededError(Exception):
    """Exception levée si le budget attribué au sous-agent dépasse le solde du parent."""
    pass


class SecurityViolationError(Exception):
    """Exception levée en cas de tentative d'escalade de privilèges par un sous-agent."""
    pass


class AgentFactory:
    """Usine souveraine de création et gouvernance des sous-agents hiérarchiques."""

    MAX_AGENT_DEPTH = 3  # Master (0) -> Agent (1) -> Sub-agent (2) -> Sub-sub-agent (3)
    MAX_CHILDREN_PER_AGENT = 5
    MAX_SPAWNS_PER_MINUTE = 20

    def __init__(self, registry: AgentRegistry | None = None):
        self.registry = registry or agent_registry
        self._spawn_timestamps: list[float] = []

    def _check_spawn_rate_limit(self) -> None:
        """Vérifie que la limite de création par minute n'est pas dépassée."""
        now = time.time()
        self._spawn_timestamps = [t for t in self._spawn_timestamps if now - t < 60.0]
        if len(self._spawn_timestamps) >= self.MAX_SPAWNS_PER_MINUTE:
            raise HierarchicalLimitError(
                f"Rate limit de création dépassé: max {self.MAX_SPAWNS_PER_MINUTE} agents/min."
            )
        self._spawn_timestamps.append(now)

    def _detect_cycle(self, parent_id: str, child_id: str) -> None:
        """Détecte les cycles de dépendance ou la récursion infinie d'agents."""
        curr = self.registry.get_agent(parent_id)
        visited = {child_id}
        while curr:
            if curr.agent_id in visited:
                raise HierarchicalLimitError(
                    f"Cycle hiérarchique détecté: '{curr.agent_id}' est un ancêtre de '{parent_id}'"
                )
            visited.add(curr.agent_id)
            if not curr.parent_id:
                break
            curr = self.registry.get_agent(curr.parent_id)

    def create_sub_agent(
        self,
        parent_id: str,
        role: str,
        name: str | None = None,
        purpose: str | None = None,
        capabilities: list[str] | None = None,
        tools: list[str] | None = None,
        budget: float = 20.0,
        model: str | None = None,
        provider: str | None = None,
        ephemeral: bool = True,
        room: str = "dev_lab",
    ) -> AgentDescriptor:
        """
        Crée un sous-agent gouverné sous l'autorité d'un agent parent.
        Applique strictement la profondeur max, le budget, la délégation de capacités et la gouvernance.
        """
        self._check_spawn_rate_limit()

        parent = self.registry.get_agent(parent_id)
        if not parent:
            raise ValueError(f"Agent parent introuvable: '{parent_id}'")

        # 1. Vérification de la profondeur hiérarchique
        child_depth = parent.depth + 1
        if child_depth > self.MAX_AGENT_DEPTH:
            raise HierarchicalLimitError(
                f"Profondeur maximale dépassée: depth={child_depth} > max={self.MAX_AGENT_DEPTH}"
            )

        # 2. Limite du nombre d'enfants
        if len(parent.children_ids) >= self.MAX_CHILDREN_PER_AGENT:
            raise HierarchicalLimitError(
                f"Nombre maximal de sous-agents atteint pour '{parent_id}': max={self.MAX_CHILDREN_PER_AGENT}"
            )

        # 3. Validation de la propagation de budget
        parent_available = parent.budget - parent.budget_used
        if budget > parent_available:
            raise BudgetExceededError(
                f"Budget insuffisant chez le parent '{parent_id}': disponible={parent_available:.2f}, demandé={budget:.2f}"
            )

        # 4. Strict Capability Delegation (CHILD <= PARENT unless parent is Master)
        requested_caps = capabilities or list(parent.capabilities)
        if not parent.is_master:
            parent_caps_upper = {c.upper() for c in parent.capabilities}
            for cap in requested_caps:
                if cap.upper() not in parent_caps_upper:
                    raise SecurityViolationError(
                        f"Tentative d'escalade de privilèges: la capacité '{cap}' n'est pas possédée par le parent '{parent_id}'"
                    )

        # 5. Restricteur d'outils (Sandboxing)
        requested_tools = tools or list(parent.tools)
        forbidden_tools = {"SecretsVault", "FrozenCoreWriter", "AdminPolicyOverride"}
        restricted_tools = [t for t in requested_tools if t not in forbidden_tools]

        # ID unique du sous-agent
        short_uuid = str(uuid.uuid4())[:8]
        agent_id = f"sub_{parent.agent_id}_{short_uuid}"
        agent_name = name or f"Sub-{role}-{short_uuid}"

        # Détection de cycle
        self._detect_cycle(parent_id, agent_id)

        # Déduction du budget du parent
        parent.budget_used += budget

        child_desc = AgentDescriptor(
            agent_id=agent_id,
            name=agent_name,
            role=role,
            room=room,
            avatar="robot_sub",
            model=model or parent.model,
            provider=provider or parent.provider,
            tools=restricted_tools,
            capabilities=requested_caps,
            risk_level=parent.risk_level,
            status=AgentStatus.IDLE,
            current_action=purpose or f"Sub-task initialized by {parent.name}",
            parent_id=parent_id,
            depth=child_depth,
            max_depth=self.MAX_AGENT_DEPTH,
            budget=budget,
            budget_used=0.0,
            ephemeral=ephemeral,
            lifecycle_state="READY",
        )

        # Enregistrement
        self.registry.register(child_desc)
        parent.children_ids.append(agent_id)

        logger.info(
            f"[AGENT-FACTORY] Sous-agent créé: {agent_id} (parent={parent_id}, depth={child_depth}, budget={budget})"
        )
        return child_desc

    def terminate_agent(self, agent_id: str, reason: str = "Completed") -> dict[str, Any]:
        """Termine un agent ou sous-agent et libère les ressources."""
        agent = self.registry.get_agent(agent_id)
        if not agent:
            return {"ok": False, "error": "Agent non trouvé"}

        agent.status = AgentStatus.OFFLINE
        agent.lifecycle_state = "TERMINATED"
        agent.current_action = f"Terminé: {reason}"

        logger.info(f"[AGENT-FACTORY] Agent {agent_id} terminé (raison: {reason})")
        return {
            "ok": True,
            "agent_id": agent_id,
            "lifecycle_state": "TERMINATED",
            "reason": reason,
        }

    def cancel_subtree(self, root_agent_id: str, reason: str = "Kill Switch Triggered") -> list[str]:
        """
        Kill Switch central : annule immédiatement un agent et toute son arborescence de sous-agents.
        """
        cancelled_ids = []
        queue = [root_agent_id]

        while queue:
            curr_id = queue.pop(0)
            agent = self.registry.get_agent(curr_id)
            if not agent:
                continue

            agent.status = AgentStatus.OFFLINE
            agent.lifecycle_state = "CANCELLED"
            agent.current_action = f"Annulé par Kill Switch: {reason}"
            cancelled_ids.append(curr_id)

            # Ajouter tous les enfants à la file
            queue.extend(agent.children_ids)

        logger.warning(
            f"[KILL-SWITCH] Arborescence annulée depuis '{root_agent_id}': {len(cancelled_ids)} agents neutralisés."
        )
        return cancelled_ids


agent_factory = AgentFactory()
