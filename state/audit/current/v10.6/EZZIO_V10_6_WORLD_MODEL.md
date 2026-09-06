# E-ZZIO V10.6 — WORLD MODEL & PROACTIVE MASTER ARCHITECTURE

## 1. WORLD REPRESENTATION & STATE PIPELINE
- **Entities**: 19 entity types (`SYSTEM`, `GOAL`, `PROGRAM`, `PROJECT`, `MISSION`, `TASK`, `AGENT`, `SUB_AGENT`, `SWARM`, `WORKER`, `MODEL`, `PROVIDER`, `RESOURCE`, `ARTIFACT`, `DEPENDENCY`, `SCHEDULE`, `RISK`, `OPPORTUNITY`, `EVENT`).
- **State Sourcing**: `OBSERVED`, `MEASURED`, `DERIVED`, `PREDICTED`, `INFERRED`, `USER_PROVIDED`, `UNKNOWN`.
- **Freshness Lifecycle**: `FRESH` (< 30s), `AGING` (30-120s), `STALE` (>= 120s). Automatic revalidation trigger when critical state is stale.
- **Drift Reconciliation**: Continuous comparison of `CURRENT_STATE` vs `EXPECTED_STATE` (`DETECT -> RECONCILE -> VERIFY -> AUDIT`).

## 2. PROACTIVE ENGINE & SAFETY GOVERNANCE
- **Pipeline**: `OBSERVE -> UNDERSTAND -> FORECAST -> EVALUATE -> POLICY CHECK -> DECIDE -> ACT/INFORM/RECOMMEND -> VERIFY -> AUDIT -> LEARN`.
- **Action Classification**:
  - `AUTO_EXECUTE_SAFE`: Low risk (R0/R1), reversible, authorized capability, no secrets/protected scope.
  - `REQUIRE_APPROVAL`: High risk (R3/R4) or policy restriction.
- **Proactive Loop Protection**: Hard limits (`MAX_PROACTIVE_ACTIONS = 5`, `MAX_TRIGGER_CHAIN = 3`) preventing `ACTION -> EVENT -> ACTION` cycles.
- **Duplicate Prevention**: Signature locking preventing duplicate proactive mission spawning.

## 3. SMART ROUTING & GRACEFUL DEGRADATION
- **Priority Chain**: `POLICY > SECURITY > LOCAL_ONLY > CAPABILITY > RELIABILITY > TASK FIT > LATENCY > COST`.
- **Graceful Fallback**: Direct state & static policy passthrough if World Model layer becomes degraded or unavailable.
