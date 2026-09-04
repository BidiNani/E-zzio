# E-ZZIO LOCAL LLM BENCHMARK V2 - RAPPORT FINAL (PHASE A)
**Campaign V1:** ABORTED / INVALIDATED - no V1 values reused.
**Standard:** EVIDENCE RULE v1.1 - NO CLAIM WITHOUT OBSERVABLE PROOF
**Host:** AMD Ryzen 9 5900X / 32 GB DDR4 / CPU-only (num_gpu=0) / Ollama 0.33.2
**Config:** 4T | ctx=4096 | timeout=180.0s | seed=42

## Matrice Comparative - Phase A

| Model | TTFT P50 | TTFT P95 | Gen tok/s | RAM Delta | Reasoning | Coding | Tools | Agent | LongCtx |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **hermes3:8b** | 164.09 ms | 164.09 ms | 7.54 tok/s | +4.98 GB | 2/5 | 4/4 | 3/3 | 3/3 | 3/3 |
| **qwen3.5:9b** | 252.96 ms | 252.96 ms | 5.82 tok/s | +6.47 GB | 0/5 | 1/4 | 0/3 | 0/3 | 0/3 |
| **nemotron-3-nano:4b** | 230.23 ms | 230.23 ms | 10.04 tok/s | +3.01 GB | 0/5 | 2/4 | 3/3 | 1/3 | 0/3 |
| **phi4-mini:latest** | 78.83 ms | 78.83 ms | 12.49 tok/s | +2.91 GB | 2/5 | 4/4 | 3/3 | 3/3 | 3/3 |


## Reconciliation
`

============================================================
E-ZZIO - OLLAMA LOCAL BENCHMARK V2
============================================================
CAMPAIGN_V1_STATUS     : ABORTED / INVALIDATED
CAMPAIGN_V2_STATUS     : COMPLETED
PHASE_A_EXPECTED       : 96
PHASE_A_EXECUTED       : 96
PHASE_A_COMPLETED      : 96
PHASE_A_TIMEOUTS       : 0
PHASE_A_FAILURES       : 0
PHASE_A_SKIPPED        : 0
EXECUTION_ORDER        : hermes3:8b -> qwen3.5:9b -> nemotron-3-nano:4b -> phi4-mini:latest
CPU_ONLY               : TRUE
GPU_USED               : 0
CUDA_USED              : FALSE
PRODUCTION_ROUTING_CHANGED : FALSE
PRODUCTION_CODE_CHANGED    : FALSE
============================================================

`
