from __future__ import annotations
import sys
import json
import hashlib
import os
import uuid
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from runtime.events.bus import Event, kernel_bus
from runtime.kernel.state import RuntimePhase, kernel_state
from runtime.security.trust import TrustRegistry
from runtime.policy.engine import PolicyEngine
from runtime.capabilities.registry import CapabilityRegistry
from runtime.execution.governor import ResourceGovernor
from runtime.execution.ledger import ExecutionLedger
from runtime.kernel.context import RuntimeContext


def _pid_is_alive(pid: int) -> bool:
    """
    Vérifie si un PID est réellement vivant.
    Sous Windows :
      - os.kill(pid, 0) est trompeur : CPython ouvre le handle mais
        ne vérifie pas si le processus est un zombie (handle maintenu
        par le parent).
      - OpenProcess() doit être couplé à GetExitCodeProcess pour
        vérifier strictement STILL_ACTIVE (259).
    """
    import os

    if pid == os.getpid():
        return True

    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        STILL_ACTIVE = 259

        kernel32 = ctypes.windll.kernel32
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]

        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            return False

        try:
            exit_code = wintypes.DWORD()
            ok = kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))
            if not ok:
                return False
            return exit_code.value == STILL_ACTIVE
        finally:
            kernel32.CloseHandle(handle)
    else:
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False


class EzzioBootloader:
    def __init__(self):
        self.root = PROJECT_ROOT
        self.context = None
        self.constitution_hash = None
        self.lock_path = str(self.root / "runtime" / "kernel" / "boot.lock")
        self.boot_id = str(uuid.uuid4())

        self.trust = TrustRegistry(self.root)
        self.capabilities = CapabilityRegistry()
        self.policy = None
        self.governor = None
        self.ledger = ExecutionLedger()

    def _acquire_process_lock(self) -> bool:
        import os
        import json

        # Étape 1 : Tentative naïve (chemin nominal)
        try:
            with open(self.lock_path, "x", encoding="utf-8") as f:
                json.dump({"pid": os.getpid(), "boot_id": self.boot_id}, f)
            return True
        except (FileExistsError, OSError):
            pass

        # Étape 2 : Analyse de la contention
        try:
            with open(self.lock_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            old_pid = data.get("pid")
            old_boot = data.get("boot_id")

            if old_pid == os.getpid():
                if old_boot == self.boot_id:
                    return True
                return False

            if old_pid is not None and _pid_is_alive(old_pid):
                return False

            # Stale lock détecté -> Nettoyage
            try:
                os.remove(self.lock_path)
            except OSError:
                pass
        except Exception:
            # Corruption ou lock évanescent -> Nettoyage
            try:
                os.remove(self.lock_path)
            except OSError:
                pass

        # Étape 3 : Deuxième tentative après nettoyage (zéro récursion)
        try:
            with open(self.lock_path, "x", encoding="utf-8") as f:
                json.dump({"pid": os.getpid(), "boot_id": self.boot_id}, f)
            return True
        except Exception:
            return False

    def release_process_lock(self):
        """
        V4.2.5.7
        Release kernel process lock.
        Safe non-blocking cleanup.
        """

        path = self.lock_path

        if not path:
            return True

        try:
            if os.path.exists(path):
                try:
                    os.unlink(path)
                except Exception:
                    pass
        except Exception:
            pass

        return True

    def _load_constitution(self) -> bool:
        try:
            kernel_state.transition(RuntimePhase.CONSTITUTION_CHECK)
        except Exception:
            kernel_state._phase = RuntimePhase.CONSTITUTION_CHECK

        const_path = self.root / "runtime" / "constitution" / "invariants.json"
        sig_path = self.root / "runtime" / "constitution" / "invariants.sig"

        try:
            if not self.trust.verify_file(const_path, sig_path):
                raise ValueError("SIGNATURE INVALIDE ou fichier .sig manquant.")

            raw = const_path.read_bytes()
            self.constitution_hash = hashlib.sha256(raw).hexdigest()
            constitution_data = json.loads(raw.decode("utf-8"))

            self.policy = PolicyEngine(constitution_data)
            hard_limits = constitution_data.get(
                "resource_hard_limits",
                {"max_cpu_threads_per_worker": 8, "max_ram_mb_per_sandbox": 4096, "max_execution_time_sec": 300, "max_parallel_workers": 8},
            )
            self.governor = ResourceGovernor(hard_limits)
            return True

        except Exception as exc:
            err_msg = f"Constitution failure: {exc}"
            try:
                kernel_state.transition(RuntimePhase.PANIC, reason=err_msg)
            except Exception:
                pass

            kernel_state._phase = RuntimePhase.PANIC
            if hasattr(kernel_state, "_panic_reason"):
                kernel_state._panic_reason = err_msg
            return False

    def ignite(self) -> bool:
        if not self._acquire_process_lock():
            err_msg = "Kernel boot lock acquisition failure."
            try:
                kernel_state.transition(RuntimePhase.PANIC, reason=err_msg)
            except Exception:
                kernel_state._phase = RuntimePhase.PANIC
                if hasattr(kernel_state, "_panic_reason"):
                    kernel_state._panic_reason = err_msg
            return False

        if kernel_state.current_phase == RuntimePhase.READY:
            self.release_process_lock()
            return False

        if not self._load_constitution():
            if kernel_state.current_phase != RuntimePhase.PANIC:
                try:
                    kernel_state.transition(RuntimePhase.PANIC, reason="Constitution failure")
                except Exception:
                    pass
                kernel_state._phase = RuntimePhase.PANIC
                if hasattr(kernel_state, "_panic_reason"):
                    kernel_state._panic_reason = "Constitution failure"

            self.release_process_lock()

            try:
                kernel_state.transition(RuntimePhase.HALTED)
            except Exception:
                pass
            kernel_state._phase = RuntimePhase.HALTED
            return False

        try:
            kernel_state.transition(RuntimePhase.SECURING_VAULT)
        except Exception:
            kernel_state._phase = RuntimePhase.SECURING_VAULT

        self.context = RuntimeContext(
            bus=kernel_bus,
            state=kernel_state,
            trust=self.trust,
            policy=self.policy,
            capabilities=self.capabilities,
            governor=self.governor,
            ledger=self.ledger,
        )

        try:
            kernel_state.transition(RuntimePhase.READY)
        except Exception:
            kernel_state._phase = RuntimePhase.READY

        kernel_bus.publish(
            Event(
                type="RuntimeReady",
                actor="Bootloader",
                source="kernel.boot",
                payload={"message": "E-ZZIO Fully Certified Runtime operational."},
            )
        )
        return True


if __name__ == "__main__":
    bootloader = EzzioBootloader()
    if not bootloader.ignite():
        sys.exit(1)
