"""
E-ZZIO Core — Industrial Cognitive Governor with HMAC Attestation (ECOL V7.62.0)
Garantit l'intégrité absolue via une chaîne SHA-256 scellée par une signature HMAC-SHA256
et un manifeste d'intégrité global.
"""

import hashlib
import hmac
import json
import logging
import os
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.config.paths import get_project_root

logger = logging.getLogger(__name__)


class LedgerSecurityError(Exception):
    """Levée pour toute infraction à la sécurité du Ledger (fail-closed strict)."""

    pass


class CognitiveGovernor:
    _class_lock = threading.RLock()

    def __init__(self, root_dir: Path | None = None):
        # La valeur par défaut historique était Path(r"G:\\AI\E-zzio") : le
        # double antislash de la raw string produisait un chemin malformé.
        # La racine est désormais résolue dynamiquement (EZZIO_ROOT, puis
        # découverte ascendante), l'argument restant prioritaire pour isoler
        # une instance sur un dossier temporaire.
        logger.info("Initialisation du Cognitive Governor [HMAC Attestation Mode V7.62.0]...")
        self.root_dir = Path(root_dir) if root_dir is not None else get_project_root()
        self.budget_dir = self.root_dir / "runtime" / "cognition" / "budget"
        self.ledger_path = self.budget_dir / "cognitive_budget_ledger.jsonl"
        self.manifest_path = self.budget_dir / "ledger_manifest.json"
        self.keys_dir = self.budget_dir / ".keys"
        self.key_path = self.keys_dir / "ledger_hmac.secret"

        self.budget_dir.mkdir(parents=True, exist_ok=True)
        self.keys_dir.mkdir(parents=True, exist_ok=True)
        self.max_session_budget = 500000

        self.runtime_id = "EZZIO-RUNTIME-001"
        self.boot_id = "V7.62.0-SECURE-BOOT"
        self.kernel_version = "V7.62.0"

        # Chargement ou génération de la clé secrète HMAC externe
        self._secret_key = self._load_or_generate_hmac_key()

        with CognitiveGovernor._class_lock:
            self.verify_ledger_chain()

    def _load_or_generate_hmac_key(self) -> bytes:
        """Charge ou génère la clé secrète HMAC pour la signature asymétrique/symétrique du registre."""
        if self.key_path.exists():
            try:
                return self.key_path.read_bytes()
            except Exception as e:
                raise LedgerSecurityError(f"Impossible de lire la clé secrète HMAC : {e}") from e
        else:
            # Génération d'une clé secrète robuste de 256 bits
            secret = os.urandom(32)
            try:
                self.key_path.write_bytes(secret)
                # Restreindre les permissions si possible sous Windows (basique)
                os.chmod(self.key_path, 0o600)
            except Exception as e:
                logger.warning(f"Impossible de restreindre les permissions de la clé HMAC : {e}")
            return secret

    def _canonical_dump(self, payload: dict) -> str:
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    def _compute_hmac(self, data_str: str) -> str:
        """Calcule le HMAC-SHA256 du payload avec la clé secrète locale."""
        return hmac.new(self._secret_key, data_str.encode("utf-8"), hashlib.sha256).hexdigest()

    def _get_last_hash_unlocked(self) -> str:
        if not self.ledger_path.exists():
            return "0000000000000000000000000000000000000000000000000000000000000000"

        last_hash = "0000000000000000000000000000000000000000000000000000000000000000"
        try:
            with self._locked_open("r") as f:
                for line in f:
                    stripped = line.strip()
                    if not stripped:
                        continue
                    data = json.loads(stripped)
                    if "record_hash" in data:
                        last_hash = data["record_hash"]
        except Exception as e:
            raise LedgerSecurityError(f"Erreur critique de lecture _get_last_hash : {e}") from e
        return last_hash

    def verify_ledger_chain(self) -> bool:
        """Vérifie l'intégrité de la chaîne SHA-256 et la validité des signatures HMAC.

        Les lectures passent par le verrou OS (voir _locked_open) : _class_lock
        ne sérialise que les threads d'un même processus, pas contre les
        append d'autres processus (xdist/serveur)."""
        with CognitiveGovernor._class_lock:
            if not self.ledger_path.exists():
                return True

            expected_prev_hash = "0000000000000000000000000000000000000000000000000000000000000000"
            required_fields = [
                "runtime_id",
                "boot_id",
                "kernel_version",
                "timestamp",
                "task",
                "priority",
                "estimated_cost",
                "decision",
                "previous_hash",
                "reason",
                "record_hash",
                "hmac_signature",
                "current_spend_after",
            ]

            block_count = 0
            with self._locked_open("r") as f:
                for line_num, line in enumerate(f, 1):
                    stripped = line.strip()
                    if not stripped:
                        continue

                    try:
                        data = json.loads(stripped)
                    except json.JSONDecodeError as jde:
                        raise LedgerSecurityError(f"Corruption syntaxique JSON ligne {line_num} : {jde}") from jde

                    for field in required_fields:
                        if field not in data:
                            raise LedgerSecurityError(f"Violation de schéma ligne {line_num} : Champ manquant -> '{field}'")

                    if not isinstance(data["estimated_cost"], int) or data["estimated_cost"] < 0:
                        raise LedgerSecurityError(f"Type invalide ligne {line_num} : estimated_cost.")

                    if not isinstance(data["record_hash"], str) or len(data["record_hash"]) != 64:
                        raise LedgerSecurityError(f"Format invalide ligne {line_num} : record_hash.")

                    stored_prev = data["previous_hash"]
                    stored_self = data["record_hash"]
                    stored_hmac = data["hmac_signature"]

                    if stored_prev != expected_prev_hash:
                        raise LedgerSecurityError(f"Rupture de chaîne cryptographique à la ligne {line_num}.")

                    # 1. Vérification du hash SHA-256 du payload bloc
                    payload_to_hash = {
                        "runtime_id": data["runtime_id"],
                        "boot_id": data["boot_id"],
                        "kernel_version": data["kernel_version"],
                        "timestamp": data["timestamp"],
                        "task": data["task"],
                        "priority": data["priority"],
                        "estimated_cost": data["estimated_cost"],
                        "decision": data["decision"],
                        "previous_hash": stored_prev,
                    }

                    canonical_payload = self._canonical_dump(payload_to_hash)
                    computed_hash = hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()

                    if computed_hash != stored_self:
                        raise LedgerSecurityError(f"Altération des données détectée à la ligne {line_num} (Hash mismatch).")

                    # 2. Vérification de la signature HMAC-SHA256 (Protection contre la réécriture totale)
                    hmac_payload = {
                        **payload_to_hash,
                        "record_hash": stored_self,
                        "reason": data["reason"],
                        "current_spend_after": data["current_spend_after"],
                    }
                    computed_hmac = self._compute_hmac(self._canonical_dump(hmac_payload))

                    if not hmac.compare_digest(computed_hmac, stored_hmac):
                        raise LedgerSecurityError(f"Échec de l'attestation HMAC à la ligne {line_num} : Signature invalide ou falsifiée.")

                    expected_prev_hash = stored_self
                    block_count += 1

            # 3. Validation croisée avec le Manifeste d'Intégrité si présent
            if self.manifest_path.exists():
                try:
                    manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
                    if manifest.get("total_blocks") != block_count:
                        raise LedgerSecurityError("Incohérence entre le nombre de blocs du Ledger et le Manifeste d'intégrité.")
                    if manifest.get("head_hash") != expected_prev_hash:
                        raise LedgerSecurityError("Rupture de l'empreinte de tête (head_hash) avec le Manifeste.")
                except LedgerSecurityError:
                    raise
                except Exception as e:
                    raise LedgerSecurityError(f"Corruption du Manifeste d'intégrité : {e}") from e

            return True

    def _calculate_current_spend_unlocked(self) -> int:
        total_tokens = 0
        if not self.ledger_path.exists():
            return 0
        try:
            with self._locked_open("r") as f:
                for line in f:
                    stripped = line.strip()
                    if not stripped:
                        continue
                    data = json.loads(stripped)
                    if data.get("decision") in ["ALLOW", "ALLOW_EXCEED", "EMERGENCY_ALLOW"]:
                        total_tokens += data.get("estimated_cost", 0)
        except Exception as e:
            raise LedgerSecurityError(f"Échec critique du calcul des dépenses : {e}") from e
        return total_tokens

    def _update_manifest(self, total_blocks: int, head_hash: str):
        """Met à jour et signe le manifeste d'intégrité global."""
        manifest_data = {
            "runtime_id": self.runtime_id,
            "boot_id": self.boot_id,
            "kernel_version": self.kernel_version,
            "total_blocks": total_blocks,
            "head_hash": head_hash,
            "attestation_timestamp": datetime.now(UTC).isoformat(),
        }
        manifest_str = self._canonical_dump(manifest_data)
        manifest_signature = self._compute_hmac(manifest_str)

        final_manifest = {**manifest_data, "manifest_signature": manifest_signature}

        try:
            with open(self.manifest_path, "w", encoding="utf-8") as f:
                f.write(self._canonical_dump(final_manifest) + "\n")
                f.flush()
                os.fsync(f.fileno())
        except Exception as e:
            raise LedgerSecurityError(f"Échec critique de l'écriture du manifeste d'intégrité : {e}") from e

    def _locked_open(self, mode: str = "r", encoding: str = "utf-8"):
        """Ouvre le ledger en tenant le verrou OS inter-processus.

        Sérialise les LECTURES contre les ÉCRITURES (pytest-xdist, serveur web,
        CLI) : sans lui, un append verrouillé d'un autre processus laisse voir
        un bloc partiellement écrit aux lecteurs non verrouillés, d'où des
        LedgerSecurityError fallacieuses (governor=None -> mission crashée).
        Complément direct du verrou d'écriture d'evaluate_and_record."""
        lock_handle = open(str(self.budget_dir / "ledger.lock"), "a")
        locked = False
        try:
            import msvcrt

            msvcrt.locking(lock_handle.fileno(), msvcrt.LK_LOCK, 1)
            locked = True
        except ImportError:
            try:
                import fcntl

                fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
                locked = True
            except Exception:
                pass
        except OSError:
            pass

        fh = open(self.ledger_path, mode, encoding=None if "b" in mode else encoding)

        class _LockedFile:
            def __init__(self, inner: Any, lh: Any, got: bool) -> None:
                self._fh = inner
                self._lh = lh
                self._locked = got

            def __enter__(self) -> Any:
                return self._fh

            def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
                try:
                    if self._locked:
                        import msvcrt

                        msvcrt.locking(self._lh.fileno(), msvcrt.LK_UNLCK, 1)
                except (ImportError, OSError):
                    try:
                        import fcntl

                        fcntl.flock(self._lh.fileno(), fcntl.LOCK_UN)
                    except Exception:
                        pass
                finally:
                    self._fh.close()
                    self._lh.close()

        return _LockedFile(fh, lock_handle, locked)

    def evaluate_and_record(self, task: str, estimated_tokens: int, priority: str = "normal", risk_level: str = "low") -> dict[str, Any]:
        with CognitiveGovernor._class_lock:
            self.verify_ledger_chain()

            current_spend = self._calculate_current_spend_unlocked()
            decision = "ALLOW"
            reason = "Budget cognitif nominal."

            if current_spend + estimated_tokens > self.max_session_budget:
                if priority == "critical":
                    decision = "EMERGENCY_ALLOW"
                    reason = "Dépassement budgétaire autorisé suite à une escalade critique."
                else:
                    decision = "DENY"
                    reason = f"Budget insuffisant. Restant: {max(0, self.max_session_budget - current_spend)} tokens."

            if risk_level == "high" and priority != "critical":
                decision = "DENY"
                reason = "Rejet : Tâche à haut risque non justifiée."

            prev_hash = self._get_last_hash_unlocked()
            timestamp = datetime.now(UTC).isoformat()

            block_payload = {
                "runtime_id": self.runtime_id,
                "boot_id": self.boot_id,
                "kernel_version": self.kernel_version,
                "timestamp": timestamp,
                "task": task,
                "priority": priority,
                "estimated_cost": estimated_tokens,
                "decision": decision,
                "previous_hash": prev_hash,
            }

            record_hash = hashlib.sha256(self._canonical_dump(block_payload).encode("utf-8")).hexdigest()

            # Calcul du HMAC-SHA256 complet incluant la signature du bloc
            hmac_payload = {
                **block_payload,
                "record_hash": record_hash,
                "reason": reason,
                "current_spend_after": current_spend + (estimated_tokens if "ALLOW" in decision or "EMERGENCY" in decision else 0),
            }
            hmac_signature = self._compute_hmac(self._canonical_dump(hmac_payload))

            transaction = {
                **hmac_payload,
                "provenance": "LIVE_RECORD",
                "historical_integrity": "ATTESTED",
                "hmac_signature": hmac_signature,
            }

            line_to_write = self._canonical_dump(transaction) + "\n"

            # Garde de concurrence inter-processus : l'append + la mise a jour du
            # manifeste doivent etre atomiques vis-a-vis de tout autre processus
            # (pytest-xdist, serveur web, CLI). Sans ce verrou, deux ecrivains
            # simultanes produisent un manifeste dechire (total_blocks ou
            # head_hash obsolete) -> LedgerSecurityError au boot suivant.
            # Append + recount + manifeste sous le meme verrou OS (atomique
            # vis-a-vis de tout autre processus ET de tout lecteur verrouille).
            with self._locked_open("a") as f:
                try:
                    f.write(line_to_write)
                    f.flush()
                    os.fsync(f.fileno())
                except Exception as e:
                    raise LedgerSecurityError(f"Échec critique de l'écriture durable (fsync) : {e}") from e

                # Recompte du nombre total de blocs et mise à jour du manifeste signé
                total_blocks = sum(1 for line in open(self.ledger_path, encoding="utf-8") if line.strip())
                self._update_manifest(total_blocks, record_hash)

            self.verify_ledger_chain()
            return transaction
