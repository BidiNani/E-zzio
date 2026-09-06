# E-ZZIO V10.2 — AUTONOMY & HIERARCHY ARCHITECTURE SPECIFICATION

## 1. SOVEREIGN MONO-AUTHORITY
E-ZZIO Master (`master_ezzio`) remains the sole governing authority at depth 0. No parallel master or ungoverned sub-tree escalation is permitted.

## 2. HIERARCHICAL STRUCTURE
```text
MASTER (depth 0)
 ├── AGENT (depth 1)
 │    ├── SUB-AGENT (depth 2)
 │    │    └── SUB-SUB-AGENT (depth 3) [MAX_AGENT_DEPTH]
```

## 3. GOVERNANCE INVARIANTS
1. **Depth Boundary**: `MAX_AGENT_DEPTH = 3`. Any attempt to spawn at depth 4 raises `HierarchicalLimitError`.
2. **Budget Boundary**: `child.budget <= (parent.budget - parent.budget_used)`. Any over-allocation raises `BudgetExceededError`.
3. **Capability Boundary**: `child.capabilities <= parent.capabilities`. Any privilege escalation attempt raises `SecurityViolationError`.
4. **Sandboxing**: Forbidden tools (`SecretsVault`, `FrozenCoreWriter`) are stripped from sub-agents automatically.
5. **Rate Limiting**: `MAX_SPAWNS_PER_MINUTE = 20`.
6. **Kill Switch**: `agent_factory.cancel_subtree(root_agent_id)` recursively terminates a target sub-tree.
