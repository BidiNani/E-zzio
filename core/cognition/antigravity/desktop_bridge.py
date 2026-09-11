from __future__ import annotations

import json
import subprocess
import threading
from pathlib import Path
from typing import Any, Dict, Optional


class AntigravityDesktopBridge:
    """
    Transport JSONL persistant vers le bridge Node Antigravity Desktop.

    Responsabilités limitées :
    - démarrer le bridge ;
    - envoyer une commande JSON ;
    - lire sa réponse JSON ;
    - conserver le processus vivant ;
    - arrêt propre.

    Aucune décision de policy, de routage ou de modèle.
    """

    def __init__(
        self,
        bridge_dir: Path = Path(__file__).with_name("desktop_bridge"),
        node_executable: str = "node",
    ) -> None:
        self.bridge_dir = Path(bridge_dir)
        self.node_executable = node_executable
        self.bridge_script = self.bridge_dir / "ezzio_antigravity_bridge.js"

        self._process: Optional[subprocess.Popen[str]] = None
        self._lock = threading.Lock()

    @property
    def available(self) -> bool:
        return self.bridge_script.exists() and self.bridge_dir.exists()

    def start(self) -> None:
        if not self.available:
            raise FileNotFoundError(
                f"Antigravity Desktop bridge unavailable: {self.bridge_script}"
            )

        if self._process is not None and self._process.poll() is None:
            return

        self._process = subprocess.Popen(
            [
                self.node_executable,
                str(self.bridge_script),
            ],
            cwd=str(self.bridge_dir),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )

    def request(self, action: str, **payload: Any) -> Dict[str, Any]:
        with self._lock:
            self.start()

            process = self._process
            if process is None:
                return {
                    "ok": False,
                    "error": "BRIDGE_NOT_STARTED",
                }

            if process.poll() is not None:
                self._process = None
                return {
                    "ok": False,
                    "error": "BRIDGE_PROCESS_EXITED",
                }

            if process.stdin is None or process.stdout is None:
                return {
                    "ok": False,
                    "error": "BRIDGE_PIPES_UNAVAILABLE",
                }

            command = {
                "action": action,
                **payload,
            }

            process.stdin.write(
                json.dumps(command, ensure_ascii=False) + "\n"
            )
            process.stdin.flush()

            line = process.stdout.readline()

            if not line:
                self._process = None
                return {
                    "ok": False,
                    "error": "BRIDGE_EOF",
                }

            try:
                result = json.loads(line)
            except json.JSONDecodeError as exc:
                return {
                    "ok": False,
                    "error": f"BRIDGE_INVALID_JSON:{exc}",
                    "raw": line.strip(),
                }

            if not isinstance(result, dict):
                return {
                    "ok": False,
                    "error": "BRIDGE_INVALID_RESPONSE",
                }

            if action == "shutdown":
                self._process = None

            return result

    def await_result(
        self,
        cascade_id: str,
        timeout_ms: int = 600000,
    ) -> Dict[str, Any]:
        """Waits for the current Desktop cascade turn and returns its result."""
        return self.request(
            "await_result",
            cascadeId=cascade_id,
            timeoutMs=timeout_ms,
        )
    def history_detail(self, cascade_id: str) -> Dict[str, Any]:
        """Returns the latest serialized Desktop cascade step."""
        return self.request(
            "history_detail",
            cascadeId=cascade_id,
        )
    def classify_history_detail(
        self,
        cascade_id: str,
    ) -> Dict[str, Any]:
        """Classifies the latest Desktop cascade state without generating."""
        detail = self.history_detail(cascade_id)

        if not detail.get("ok"):
            return detail

        last_step = detail.get("lastStep")

        if not isinstance(last_step, dict):
            return {
                "ok": True,
                "cascadeId": cascade_id,
                "classification": "UNKNOWN",
                "reason": "LAST_STEP_MISSING",
            }

        error_message = last_step.get("errorMessage")

        serialized = ""

        if error_message is not None:
            try:
                serialized = json.dumps(
                    error_message,
                    ensure_ascii=False,
                    default=str,
                )
            except Exception:
                serialized = str(error_message)

        upper = serialized.upper()

        if (
            "QUOTA_EXHAUSTED" in upper
            or "RESOURCE_EXHAUSTED" in upper
            or "INDIVIDUAL QUOTA REACHED" in upper
        ):
            return {
                "ok": True,
                "cascadeId": cascade_id,
                "classification": "BLOCKED_BY_EXTERNAL_QUOTA",
                "reason": "ANTIGRAVITY_QUOTA_EXHAUSTED",
                "stepCount": detail.get("stepCount", 0),
            }

        step_type = str(last_step.get("type", "")).upper()
        step_status = str(last_step.get("status", "")).upper()

        if "ERROR" in step_type:
            return {
                "ok": True,
                "cascadeId": cascade_id,
                "classification": "FAILED",
                "reason": "DESKTOP_ERROR_STEP",
                "stepType": step_type,
                "stepStatus": step_status,
                "stepCount": detail.get("stepCount", 0),
            }

        return {
            "ok": True,
            "cascadeId": cascade_id,
            "classification": "NOT_BLOCKED",
            "stepType": step_type,
            "stepStatus": step_status,
            "stepCount": detail.get("stepCount", 0),
        }
    def shutdown(self) -> None:
        process: Optional[subprocess.Popen[str]]

        with self._lock:
            process = self._process

            if process is None:
                return

            if process.poll() is None:
                if process.stdin is not None:
                    try:
                        process.stdin.write(
                            json.dumps({"action": "shutdown"}) + "\n"
                        )
                        process.stdin.flush()
                        process.stdout.readline() if process.stdout else None
                    except Exception:
                        pass

                if process.poll() is None:
                    try:
                        process.terminate()
                    except Exception:
                        pass

            self._process = None

        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                process.kill()
            except Exception:
                pass

            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass

    def __enter__(self) -> "AntigravityDesktopBridge":
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.shutdown()

