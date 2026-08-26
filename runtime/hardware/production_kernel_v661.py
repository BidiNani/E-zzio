# ==============================================================================
# E-ZZIO Runtime — Industrial Production Kernel V6.6.1 (Hardened & Signed)
# ==============================================================================
VERSION = "6.6.1"

import os
import time
import json
import threading
import hashlib
import hmac
from pathlib import Path
from dataclasses import dataclass
from collections import deque


class KernelFatalError(Exception):
    """Exception dédiée aux pannes fatales du noyau."""

    pass


@dataclass
class VectorHeartbeat:
    timestamp: float = 0.0
    generation_id: int = 1
    tick_count: int = 0
    last_ttc: float = 999.0
    latency_ms: float = 0.0


@dataclass
class DecisionPolicy:
    state: str
    tier: str
    confidence: float
    ttc_seconds: float
    polling_interval: float
    max_batch_size: int
    max_batch_delay: float
    reason: str
    is_safe_mode: bool = False


class DeepLearningEngine:
    def __init__(self, incident_log_path: Path):
        self.incident_log_path = incident_log_path

    def calibrate_profile(self, base_profile: dict) -> dict:
        calibrated = base_profile.copy()
        if not self.incident_log_path.exists():
            return calibrated

        try:
            with open(self.incident_log_path, "r", encoding="utf-8") as f:
                incidents = [json.loads(line) for line in f.read().strip().split("\n") if line]

            now = time.time()
            recent_incidents = [i for i in incidents if (now - i.get("timestamp", 0)) < 86400]

            penalty = 0.0
            for inc in recent_incidents:
                recovery_time = inc.get("recovery_sec", 0.0)
                weight = 2.0 if recovery_time > 10.0 else 1.0
                penalty += 0.01 * weight

            if penalty > 0.0:
                penalty = min(0.15, penalty)
                calibrated["entry"] = round(base_profile["entry"] - penalty, 3)
                calibrated["pre_entry"] = round(base_profile["pre_entry"] - penalty, 3)
        except Exception:
            pass

        return calibrated


class PredictiveDecisionEngine:
    WORKLOAD_PROFILES = {
        "INGESTION_BURST": {"entry": 0.80, "pre_entry": 0.65, "exit": 0.50, "hold": 3.0},
        "FULL_INDEXING": {"entry": 0.70, "pre_entry": 0.55, "exit": 0.40, "hold": 4.0},
        "GUARDIAN_SCAN": {"entry": 0.85, "pre_entry": 0.70, "exit": 0.55, "hold": 2.0},
        "IDLE_MAINTENANCE": {"entry": 0.90, "pre_entry": 0.75, "exit": 0.60, "hold": 1.0},
    }

    def __init__(self, learning_engine: DeepLearningEngine):
        self.learning_engine = learning_engine

    @staticmethod
    def calculate_confidence(oom: float, d_rss: float, ttc: float, incident_count: int) -> float:
        c_oom = min(1.0, oom / 0.80) * 0.40
        c_vel = min(1.0, max(0.0, d_rss) / 500.0) * 0.30
        c_ttc = 0.20 if ttc < 15.0 else (0.10 if ttc < 30.0 else 0.0)
        c_hist = min(1.0, incident_count / 3.0) * 0.10
        return round(c_oom + c_vel + c_ttc + c_hist, 2)

    def evaluate(self, metrics: dict, context: dict) -> DecisionPolicy:
        oom, d_rss, rss = metrics.get("oom_index", 0.0), metrics.get("d_rss_dt_mbs", 0.0), metrics.get("rss_mb", 2048.0)
        budget = metrics.get("budget_mb", 10240.0)
        ttc = (budget - rss) / d_rss if d_rss > 0.1 else 999.0

        base_p = self.WORKLOAD_PROFILES[context["workload"]]
        p = self.learning_engine.calibrate_profile(base_p)

        prev, now = context["current_state"], time.time()
        nxt, reason = prev, "STABLE"

        if prev in ["THROTTLING_ACTIVE", "PRE_CRITICAL"]:
            if (now - context["last_transition"]) < p["hold"]:
                nxt, reason = prev, "HOLD_TIME_ACTIVE"
            elif oom <= p["exit"]:
                nxt, reason = "RECOVERY_CONFIRMED", "SAFE_WATERMARK_REACHED"

        if nxt == prev and nxt not in ["THROTTLING_ACTIVE", "PRE_CRITICAL"]:
            if ttc <= 12.0 or oom >= p["entry"]:
                nxt, reason = "THROTTLING_ACTIVE", f"CRITICAL_TRIGGER (TTC={ttc:.1f}s)"
            elif oom >= p["pre_entry"] or (0.0 < ttc <= 25.0):
                nxt, reason = "PRE_CRITICAL", "PREEMPTIVE_WARNING"
            elif oom >= (p["entry"] * 0.60):
                nxt, reason = "PRESSURE_DETECTED", "ELEVATED_PRESSURE"
            else:
                nxt, reason = "NORMAL_OPERATION", "NOMINAL"

        confidence = self.calculate_confidence(oom, d_rss, ttc, context["incident_count"])

        if nxt == "THROTTLING_ACTIVE":
            batch, delay, tier, poll = 250, 0.05, "CRITICAL", 0.025
        elif nxt == "PRE_CRITICAL":
            batch, delay, tier, poll = 1500, 0.02, "MODERATE", 0.100
        elif nxt == "PRESSURE_DETECTED":
            batch, delay, tier, poll = 2200, 0.015, "MODERATE", 0.250
        elif nxt in ["RECOVERY_PENDING", "RECOVERY_CONFIRMED"]:
            batch, delay, tier, poll = 2000, 0.012, "NOMINAL", 0.200
        else:
            batch, delay, tier, poll = 3000, 0.01, "NOMINAL", 0.500

        return DecisionPolicy(nxt, tier, confidence, round(ttc, 1), poll, batch, delay, reason)


class ActionExecutor:
    def __init__(self, engine_ref):
        self.engine = engine_ref

    def apply(self, policy: DecisionPolicy):
        self.engine.max_batch_size = policy.max_batch_size
        self.engine.max_batch_delay = policy.max_batch_delay


class ProductionKernelV661:
    def __init__(self, engine_ref, memory_engine_ref, state_dir: str = None, safe_cooldown: float = 60.0):
        self.memory_engine = memory_engine_ref
        self.executor = ActionExecutor(engine_ref)

        self.base_dir = Path(state_dir) if state_dir else Path(__file__).resolve().parent
        self.state_dir = self.base_dir / "state"
        self.state_dir.mkdir(parents=True, exist_ok=True)

        self.sec_dir = self.base_dir.parent / "security"
        self.sec_dir.mkdir(parents=True, exist_ok=True)
        self.key_file = self.sec_dir / "hmac.key"
        self.hmac_secret = self._get_or_create_hmac_key()

        self.state_file = self.state_dir / "production_v661_state.json"
        self.incident_log = self.state_dir / "rich_incidents.jsonl"

        self.learning_engine = DeepLearningEngine(self.incident_log)
        self.decision_engine = PredictiveDecisionEngine(self.learning_engine)

        self.safe_cooldown = safe_cooldown
        self.context = {
            "workload": "INGESTION_BURST",
            "current_state": "NORMAL_OPERATION",
            "last_transition": time.time(),
            "incident_count": 0,
            "current_polling": 2.0,
        }

        self.is_safe_mode = False
        self.is_permanent_safe_mode = False
        self.permanent_reason = ""
        self.safe_mode_start = 0.0
        self.safe_mode_step = 0

        self.heartbeat = VectorHeartbeat()
        self.crash_history = deque(maxlen=10)

        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._fatal_simulate = False
        self._stall_simulate = False

        self.load_persisted_state_safely()
        self._start_threads()

    def _get_or_create_hmac_key(self) -> bytes:
        if not self.key_file.exists():
            key = os.urandom(32)
            with open(self.key_file, "wb") as f:
                f.write(key)
            return key
        with open(self.key_file, "rb") as f:
            return f.read()

    def _generate_hmac(self, payload: dict) -> str:
        clean_payload = {k: v for k, v in payload.items() if k != "signature"}
        serialized = json.dumps(clean_payload, sort_keys=True, separators=(",", ":"))
        return hmac.new(self.hmac_secret, serialized.encode("utf-8"), hashlib.sha256).hexdigest()

    def _start_threads(self):
        self.governor_thread = threading.Thread(target=self._governor_loop, daemon=True)
        self.watchdog_thread = threading.Thread(target=self._watchdog_loop, daemon=True)
        self.governor_thread.start()
        self.watchdog_thread.start()

    def load_persisted_state_safely(self):
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                expected_sig = self._generate_hmac(data)
                if data.get("signature") != expected_sig:
                    raise ValueError("HMAC SIGNATURE MISMATCH")

                self.context["current_state"] = data.get("current_state", "NORMAL_OPERATION")
                self.context["workload"] = data.get("workload", "INGESTION_BURST")

                if data.get("is_permanent_safe_mode", False):
                    reason = data.get("permanent_reason", "PERSISTED_PERMANENT_SAFE_MODE")
                    self.trigger_permanent_safe_mode(reason)
            except Exception as e:
                self.trigger_permanent_safe_mode(f"STATE_TAMPERING_DETECTED: {e}")
                try:
                    self.state_file.unlink()
                except:
                    pass

    def save_persisted_state_atomic(self):
        tmp = self.state_file.with_suffix(".tmp")
        payload = {
            "version": VERSION,
            "current_state": self.context["current_state"],
            "workload": self.context["workload"],
            "is_permanent_safe_mode": self.is_permanent_safe_mode,
            "permanent_reason": self.permanent_reason,
            "timestamp": time.time(),
        }
        payload["signature"] = self._generate_hmac(payload)
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(payload, f)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, self.state_file)
        except:
            pass

    def trigger_safe_mode(self, reason: str):
        with self._lock:
            if not self.is_safe_mode and not self.is_permanent_safe_mode:
                self.is_safe_mode = True
                self.safe_mode_start = time.time()
                self.safe_mode_step = 0
                self.context["current_state"] = "SAFE_MODE_ACTIVE"
                safe_policy = DecisionPolicy("SAFE_MODE_ACTIVE", "CRITICAL", 1.0, 0.0, 2.0, 100, 0.1, reason, True)
                self.executor.apply(safe_policy)
                self.save_persisted_state_atomic()

    def trigger_permanent_safe_mode(self, reason: str):
        with self._lock:
            self.is_permanent_safe_mode = True
            self.is_safe_mode = True
            self.permanent_reason = reason
            self.context["current_state"] = "PERMANENT_SAFE_MODE"
            safe_policy = DecisionPolicy("PERMANENT_SAFE_MODE", "CRITICAL", 1.0, 0.0, 2.0, 50, 0.5, reason, True)
            self.executor.apply(safe_policy)
            self.save_persisted_state_atomic()

    def _watchdog_loop(self):
        while not self._stop_event.is_set():
            now = time.time()

            if not self.governor_thread.is_alive() and not self.is_permanent_safe_mode:
                self.crash_history.append(now)
                recent_crashes = [t for t in self.crash_history if (now - t) < 60.0]
                if len(recent_crashes) >= 3:
                    self.trigger_permanent_safe_mode("CRASH_LOOP_CIRCUIT_BREAKER_TRIPPED")
                else:
                    self.trigger_safe_mode("THREAD_DEATH_RECOVERY")
                    self.heartbeat.generation_id += 1
                    self.governor_thread = threading.Thread(target=self._governor_loop, daemon=True)
                    self.governor_thread.start()

            if not self.is_permanent_safe_mode and self.governor_thread.is_alive():
                if (now - self.heartbeat.timestamp) > 3.0:
                    self.trigger_safe_mode("VECTOR_HEARTBEAT_TIMEOUT")

            if self.is_safe_mode and not self.is_permanent_safe_mode:
                if (now - self.safe_mode_start) > self.safe_cooldown:
                    self._execute_gradual_recovery()

            time.sleep(1.0)

    def _execute_gradual_recovery(self):
        with self._lock:
            recovery_steps = [500, 1500, 3000]
            if self.safe_mode_step < len(recovery_steps):
                batch = recovery_steps[self.safe_mode_step]
                self.executor.apply(
                    DecisionPolicy("SAFE_MODE_RECOVERING", "MODERATE", 1.0, 99.0, 1.0, batch, 0.02, "GRADUAL_RECOVERY", True)
                )
                self.safe_mode_step += 1
                self.safe_mode_start = time.time() - (self.safe_cooldown / 2)
            else:
                self.is_safe_mode = False
                self.context["current_state"] = "NORMAL_OPERATION"
                self.save_persisted_state_atomic()

    def _governor_loop(self):
        while not self._stop_event.is_set():
            if getattr(self, "_stall_simulate", False):
                time.sleep(0.1)
                continue

            if getattr(self, "_fatal_simulate", False):
                self._fatal_simulate = False
                raise KernelFatalError("FATAL KERNEL EXCEPTION")

            if not self.is_safe_mode:
                try:
                    t_start = time.perf_counter()
                    self.evaluate_tick()

                    with self._lock:
                        self.heartbeat.tick_count += 1
                        self.heartbeat.timestamp = time.time()
                        self.heartbeat.latency_ms = (time.perf_counter() - t_start) * 1000.0
                except Exception as e:
                    self.trigger_safe_mode(f"UNHANDLED_EVAL_EXCEPTION: {e}")
            else:
                with self._lock:
                    self.heartbeat.timestamp = time.time()

            time.sleep(self.context["current_polling"])

    def evaluate_tick(self) -> dict:
        with self._lock:
            metrics = self.memory_engine.evaluate_state()
            metrics["budget_mb"] = getattr(self.memory_engine, "budget_mb", 10240.0)

            policy = self.decision_engine.evaluate(metrics, self.context)
            if policy.state != self.context["current_state"]:
                self.context["last_transition"] = time.time()
                self.context["current_state"] = policy.state
                self.save_persisted_state_atomic()

            self.context["current_polling"] = policy.polling_interval
            self.heartbeat.last_ttc = policy.ttc_seconds
            self.executor.apply(policy)
            return {"state": policy.state, "batch": policy.max_batch_size, "polling": policy.polling_interval}

    def simulate_fatal_crash(self):
        self._fatal_simulate = True

    def simulate_thread_stall(self):
        self._stall_simulate = True

    def restore_thread_stall(self):
        self._stall_simulate = False

    def stop(self):
        self._stop_event.set()
        if self.governor_thread.is_alive():
            self.governor_thread.join(timeout=1.0)
        if self.watchdog_thread.is_alive():
            self.watchdog_thread.join(timeout=1.0)
