"""
E-ZZIO Sovereign Governance — HITL Approval Manager.
Fournit le cycle de vie complet :
demande -> PENDING -> APPROVE/REJECT/EXPIRE/CANCEL -> reprise contrôlée -> audit append-only.
"""
from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from core.governance.approval.models import (
    ApprovalRequest,
    ApprovalStatus,
    DecisionChoice,
    utc_now,
)
from core.governance.approval.store import SqliteApprovalStore
from core.security.audit_ledger import AuditLedger
from core.tasks.manager import task_manager

logger = logging.getLogger("ApprovalManager")


class ApprovalError(Exception):
    """Exception de base pour les erreurs du système d'approbation."""
    pass


class PayloadIntegrityViolation(ApprovalError):
    """Levée si le payload à réexécuter ne correspond pas cryptographiquement au hash scellé."""
    pass


class ApprovalExpiredError(ApprovalError):
    """Levée si une décision ou reprise est tentée sur une requête expirée."""
    pass


class StateTransitionError(ApprovalError):
    """Levée si une transition interdite est demandée."""
    pass


class DoubleExecutionError(ApprovalError):
    """Levée en cas de tentative de ré-exécution d'une approbation déjà engagée ou consommée."""
    pass


class ContextMismatchError(ApprovalError):
    """Levée si le contexte d'exécution (task, session, capability, scope) ne correspond pas."""
    pass


def canonical_json(data: dict[str, Any]) -> str:
    """Génère une représentation JSON canonique déterministe (clés triées, sans espace superfétatoire)."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def compute_payload_hash(data: dict[str, Any]) -> str:
    """Calcule l'empreinte SHA-256 du JSON canonique."""
    c_json = canonical_json(data)
    return hashlib.sha256(c_json.encode("utf-8")).hexdigest()


class ApprovalManager:
    def __init__(
        self,
        store: SqliteApprovalStore | None = None,
        audit_ledger: AuditLedger | None = None,
    ):
        self.store = store or SqliteApprovalStore()
        self.audit_ledger = audit_ledger or AuditLedger()

    def request_approval(
        self,
        task_id: str,
        session_id: str,
        agent_id: str,
        capability_name: str,
        scope: str,
        safe_summary: str,
        params: dict[str, Any],
        ttl_seconds: int = 300,
        requested_by: str = "system",
        approval_id: str | None = None,
    ) -> ApprovalRequest:
        """Crée une nouvelle demande d'approbation scellée et l'enregistre dans l'AuditLedger."""
        c_params = canonical_json(params)
        p_hash = hashlib.sha256(c_params.encode("utf-8")).hexdigest()

        req = ApprovalRequest.create(
            task_id=task_id,
            session_id=session_id,
            agent_id=agent_id,
            capability_name=capability_name,
            scope=scope,
            safe_summary=safe_summary,
            payload_hash=p_hash,
            params_payload=c_params,
            ttl_seconds=ttl_seconds,
            requested_by=requested_by,
            approval_id=approval_id,
        )

        self.store.save_request(req)

        # Liaison avec le cycle de vie de la tâche
        try:
            task = task_manager.get_task(task_id)
            if task:
                if task["state"] == "PLANNED":
                    task_manager.transition_task(task_id, "POLICY_CHECKED")
                    task = task_manager.get_task(task_id)
                if task and task["state"] == "POLICY_CHECKED":
                    task_manager.transition_task(task_id, "AWAITING_APPROVAL", approval_id=req.approval_id)
        except Exception as e:
            logger.warning("[APPROVAL] Impossible d'associer la tâche %s : %s", task_id, e)

        # Audit append-only
        try:
            self.audit_ledger.record_event(
                actor=agent_id,
                action="APPROVAL_REQUESTED",
                payload={
                    "approval_id": req.approval_id,
                    "task_id": req.task_id,
                    "capability": req.capability_name,
                    "scope": req.scope,
                    "safe_summary": req.safe_summary,
                    "payload_hash": req.payload_hash,
                    "expires_at": req.expires_at,
                },
                status="PENDING",
            )
        except Exception as e:
            logger.error("[APPROVAL] Échec d'enregistrement d'audit : %s", e)

        return req

    def get(self, approval_id: str) -> ApprovalRequest | None:
        """Récupère une demande et évalue son expiration éventuelle."""
        req = self.store.get_by_id(approval_id)
        if not req:
            return None

        # Expiration dynamique à la lecture si PENDING
        if req.status == ApprovalStatus.PENDING and utc_now() >= req.expires_at:
            self.expire(approval_id)
            return self.store.get_by_id(approval_id)

        return req

    def get_pending(self) -> list[ApprovalRequest]:
        """Liste les demandes en attente valides (purge/expire celles dont le TTL est dépassé)."""
        all_pending = self.store.list_pending()
        valid_pending = []
        now_str = utc_now()

        for req in all_pending:
            if now_str >= req.expires_at:
                self.expire(req.approval_id)
            else:
                valid_pending.append(req)

        return valid_pending

    def decide(
        self,
        approval_id: str,
        choice: DecisionChoice,
        decided_by: str,
        reason: str | None = None,
    ) -> ApprovalRequest:
        """Enregistre la décision humaine sous transaction atomique et journalise dans l'audit."""
        new_status = ApprovalStatus.APPROVED if choice == DecisionChoice.APPROVE else ApprovalStatus.REJECTED
        decided_at = utc_now()

        ok, updated_req, err = self.store.update_decision_atomic(
            approval_id=approval_id,
            new_status=new_status,
            decided_by=decided_by,
            decided_at=decided_at,
            reason=reason,
        )

        if not ok:
            if err == "APPROVAL_EXPIRED":
                try:
                    self.audit_ledger.record_event(
                        actor="system",
                        action="APPROVAL_EXPIRED",
                        payload={"approval_id": approval_id, "attempted_by": decided_by},
                        status="EXPIRED",
                    )
                except Exception:
                    pass
                raise ApprovalExpiredError(f"La demande {approval_id} a expiré.")
            elif err == "APPROVAL_NOT_FOUND":
                raise KeyError(f"Demande inconnue : {approval_id}")
            else:
                raise StateTransitionError(f"Transition interdite : {err}")

        # Journalisation d'audit
        event_action = "APPROVAL_APPROVED" if choice == DecisionChoice.APPROVE else "APPROVAL_REJECTED"
        try:
            self.audit_ledger.record_event(
                actor=decided_by,
                action=event_action,
                payload={
                    "approval_id": updated_req.approval_id,
                    "task_id": updated_req.task_id,
                    "decision": choice.value,
                    "reason": reason or "",
                },
                status=updated_req.status.value,
            )
        except Exception as e:
            logger.error("[APPROVAL] Échec d'enregistrement d'audit : %s", e)

        # Synchronisation avec le TaskManager si rejet
        if choice == DecisionChoice.REJECT:
            try:
                task_manager.transition_task(
                    updated_req.task_id,
                    "CANCELLED",
                    error_message=f"Rejeté par {decided_by}: {reason or 'Sans motif'}",
                )
            except Exception:
                pass

        return updated_req

    def expire(self, approval_id: str) -> ApprovalRequest | None:
        """Marque explicitement une requête comme expirée."""
        req = self.store.get_by_id(approval_id)
        if not req or req.status != ApprovalStatus.PENDING:
            return req

        now_str = utc_now()
        if now_str < req.expires_at:
            # Forçage ou expiration prématurée non autorisée si le temps n'est pas écoulé
            pass

        # Expiration atomique
        self.store.update_decision_atomic(
            approval_id=approval_id,
            new_status=ApprovalStatus.EXPIRED,
            decided_by="system",
            decided_at=now_str,
            reason="TTL_EXCEEDED",
        )

        updated = self.store.get_by_id(approval_id)
        try:
            self.audit_ledger.record_event(
                actor="system",
                action="APPROVAL_EXPIRED",
                payload={"approval_id": approval_id, "task_id": req.task_id},
                status="EXPIRED",
            )
        except Exception:
            pass

        # Synchronisation TaskManager
        try:
            task_manager.transition_task(
                req.task_id,
                "CANCELLED",
                error_message="Demande d'approbation expirée.",
            )
        except Exception:
            pass

        return updated

    def cancel(self, approval_id: str, reason: str = "Tâche annulée") -> ApprovalRequest | None:
        """Annule une demande en cours."""
        req = self.store.get_by_id(approval_id)
        if not req or req.status != ApprovalStatus.PENDING:
            return req

        self.store.update_decision_atomic(
            approval_id=approval_id,
            new_status=ApprovalStatus.CANCELLED,
            decided_by="system",
            decided_at=utc_now(),
            reason=reason,
        )
        return self.store.get_by_id(approval_id)

    async def resume_execution(
        self,
        approval_id: str,
        target_executor_func: Any,
        expected_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Déclenche la reprise de l'exécution sous barrière de sécurité et d'idempotence stricte.
        target_executor_func : async callable(capability_name, params)
        """
        req = self.store.get_by_id(approval_id)
        if not req:
            raise KeyError(f"Demande d'approbation introuvable : {approval_id}")

        # 1. Vérification du statut
        if req.status == ApprovalStatus.REJECTED:
            raise StateTransitionError("Impossible de reprendre une demande REJECTED.")
        if req.status in (ApprovalStatus.EXPIRED, ApprovalStatus.CANCELLED):
            raise ApprovalExpiredError(f"Impossible de reprendre une demande en statut {req.status.value}.")
        if req.status != ApprovalStatus.APPROVED:
            raise StateTransitionError(f"La demande n'est pas APPROVED (statut actuel: {req.status.value}).")

        # 2. Vérification TTL
        if utc_now() >= req.expires_at:
            self.expire(approval_id)
            raise ApprovalExpiredError("Le délai d'approbation a expiré avant l'engagement de la reprise.")

        # 3. Vérification de contexte si fourni
        if expected_context:
            if "task_id" in expected_context and expected_context["task_id"] != req.task_id:
                raise ContextMismatchError("task_id ne correspond pas.")
            if "session_id" in expected_context and expected_context["session_id"] != req.session_id:
                raise ContextMismatchError("session_id ne correspond pas.")
            if "capability_name" in expected_context and expected_context["capability_name"] != req.capability_name:
                raise ContextMismatchError("capability_name ne correspond pas.")
            if "scope" in expected_context and expected_context["scope"] != req.scope:
                raise ContextMismatchError("scope ne correspond pas.")

        # 4. Vérification d'intégrité cryptographique du payload
        params = json.loads(req.params_payload)
        computed_hash = hashlib.sha256(canonical_json(params).encode("utf-8")).hexdigest()
        if computed_hash != req.payload_hash:
            raise PayloadIntegrityViolation("[SECURITY BREACH] Le payload stocké a été corrompu ou altéré !")

        # 5. Revendication atomique d'exécution (anti-rejeu / barrière de concurrence)
        ok, current_req, err = self.store.claim_execution_atomic(approval_id)
        if not ok:
            if err == "ALREADY_CONSUMED":
                # Idempotence : si le résultat est déjà en cache, le retourner sans réexécuter
                if current_req and current_req.result_cache:
                    return json.loads(current_req.result_cache)
                raise DoubleExecutionError("Action déjà consommée sans cache de résultat.")
            elif err == "ALREADY_RUNNING":
                raise DoubleExecutionError("Une exécution est déjà engagée en parallèle pour cette approbation.")
            else:
                raise StateTransitionError(f"Échec de revendication d'exécution : {err}")

        # 6. Audit reprise engagée
        try:
            self.audit_ledger.record_event(
                actor="system",
                action="APPROVAL_RESUMED",
                payload={
                    "approval_id": approval_id,
                    "task_id": req.task_id,
                    "capability": req.capability_name,
                    "scope": req.scope,
                },
                status="RUNNING",
            )
        except Exception:
            pass

        # 7. Transition de la tâche dans le TaskManager (AWAITING_APPROVAL -> RUNNING)
        try:
            task_manager.transition_task(req.task_id, "RUNNING", approval_id=approval_id)
        except Exception as e:
            logger.warning("[APPROVAL] Erreur transition task vers RUNNING : %s", e)

        # 8. Exécution réelle de la fonction cible
        execution_success = False
        result_to_return: dict[str, Any] = {}
        try:
            res = await target_executor_func(req.capability_name, params)
            result_to_return = res
            execution_success = True

            # Consignation Audit Succès
            try:
                self.audit_ledger.record_event(
                    actor="system",
                    action="APPROVAL_EXECUTION_SUCCEEDED",
                    payload={"approval_id": approval_id, "task_id": req.task_id},
                    status="SUCCESS",
                )
            except Exception:
                pass

            # Transition Task vers VERIFYING
            try:
                task_manager.transition_task(req.task_id, "VERIFYING")
            except Exception:
                pass

            return res

        except Exception as exc:
            result_to_return = {"ok": False, "error": str(exc)}
            try:
                self.audit_ledger.record_event(
                    actor="system",
                    action="APPROVAL_EXECUTION_FAILED",
                    payload={"approval_id": approval_id, "task_id": req.task_id, "error": str(exc)},
                    status="FAILED",
                )
            except Exception:
                pass
            raise exc

        finally:
            # 9. Scellement final CONSUMED ou FAILED_DURING_EXECUTION
            self.store.finalize_execution_atomic(
                approval_id=approval_id,
                success=execution_success,
                result_cache=json.dumps(result_to_return, ensure_ascii=False),
            )


approval_manager = ApprovalManager()
