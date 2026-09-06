# E-ZZIO V10.3 — COLLECTIVE INTELLIGENCE ARCHITECTURE

## 1. SOVEREIGN MASTER AUTHORITY
E-ZZIO Master (`master_ezzio`) creates, supervises, and arbitrates all swarms. No un-governed or parallel master swarms are permitted.

## 2. SWARM LIFECYCLE
```text
CREATED → ACTIVE → BRAINSTORMING → DEBATING → SYNTHESIZING → CONSENSUS_REACHED / ARBITRATED → COMPLETED
```

## 3. DISCUSSION BUS PROTOCOL
Agents communicate over a governed bus with formal message types:
- `QUESTION`
- `PROPOSAL`
- `OBJECTION` (triggers conflict detection)
- `COUNTER_ARGUMENT`
- `EVIDENCE`
- `CLARIFICATION`
- `ALTERNATIVE`
- `VOTE`
- `CONCESSION`
- `SUMMARY`
- `FINAL_POSITION`

## 4. CONFLICT RESOLUTION RULE
1. Conflicts automatically generated upon `OBJECTION`.
2. Resolution priority: `EVIDENCE > ASSUMPTION`.
3. Open conflicts prevent automatic consensus, triggering Master Arbitration.
4. Minority reports preserved if proposal score >= 0.50.
