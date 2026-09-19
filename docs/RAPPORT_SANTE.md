# E-ZZIO — Rapport de santé

Généré : 2026-09-18 21:40:10

## Volumétrie

| Zone | Fichiers | Lignes |
|---|---|---|
| Backend (.py) | 1609 | 144114 |
| Frontend (.ts/.tsx) | 47 | 4694 |

## Marqueurs TODO/FIXME/HACK (backend)

```
core\cognition\compression\compressor_fabric.py:154  filtered = [l for l in lines if not (l.strip().startswith("#") and len(l.strip()) > 1 and "TODO" not in l and "CRITICAL" not in l)]
core\config\secrets_loader.py:145  "DISCORD_OWNER_ID": f"[PRESENT] (ID: {str(owner)[:5]}...XXXX)"
core\health\diagnostic.py:183  Mémoire d'évolution (XXXVII) : anomalies, diagnostics, traitements,
core\providers\google_calendar_provider.py:19  # TODO: Implémenter l'appel à l'API Google Calendar
core\providers\google_docs_provider.py:19  # TODO: Implémenter l'appel à l'API Google Docs
core\providers\google_drive_provider.py:19  # TODO: Implémenter l'appel à l'API Google Drive
core\providers\google_gmail_provider.py:19  # TODO: Implémenter l'appel à l'API Gmail
routers\self.py:30  # TODO: exposer cette info depuis le router chat
scripts\run_master_final_certification.py:183  dec = policy.evaluate_intent("hacker", "modify", "core/constitution/axioms.json", ["modify"])
tests\test_capability_registry_and_qualifications.py:53  <script>alert("hack");</script>
tests\test_fabric_runtime.py:146  fabric.transition(provider=prov, model_id=mid, new_state="ACTIVE", actor="hack", reason="hack")
tests\test_hitl_api.py:252  json={"decision": "CONSUMED", "decided_by": "hacker"},
tests\test_hitl_discord.py:217  user_id="hacker",
tests\test_hitl_discord.py:218  username="hacker",
tests\test_metrics.py:149  {"worker_type": "A", "status": "HACKED into COMPLETED"}),
tests\test_phase7_adversarial_real.py:22  actor="hacker",
```

## Fichiers volumineux (backend, > 300 lignes)

| Fichier | Lignes |
|---|---|
| core\models\router.py | 801 |
| core\observability\metrics.py | 646 |
| core\safe_actions.py | 634 |
| routers\office.py | 610 |
| backups\registry_integration\20260902_131946\model_router_before_import_repair.py | 572 |
| backups\registry_integration\20260902_131946\model_router.py | 569 |
| core\perception\universal_reader.py | 568 |
| tools\run_nemotron_vs_baseline_benchmark.py | 560 |
| state\audit\current\capability_registry\generate_registry.py | 547 |
| legacy_archive\_forensic\phase_2_13R2_backup_20260828_000732\core_models_fabric.py | 539 |
| legacy_archive\_forensic\phase_2_13_backup_20260828_000642\core_models_fabric.py | 539 |
| legacy_archive\snapshot\fabric.py | 536 |
| core\omni_brain.py | 533 |
| scripts\cleanup_engine.py | 532 |
| core\models\fabric.py | 497 |
| core\agents\registry.py | 494 |
| core\knowledge\drift_detector.py | 483 |
| tools\index_engine_v5_5.py | 480 |
| core\knowledge\self_awareness.py | 476 |
| core\cognition\decision_ledger.py | 463 |
| core\human_loop.py | 456 |
| core\providers\nvidia_nim_provider.py | 446 |
| core\memory\tiers.py | 432 |
| tools\run_master_lab_v13.py | 431 |
| core\integrations\discord\discord_client.py | 431 |
| core\providers\gemini_provider.py | 428 |
| core\human_chat.py | 424 |
| core\pc_commander.py | 423 |
| tests\test_hitl_approval.py | 422 |
| core\pc_model_router.py | 419 |
| state\quarantine\quarantine_20260829_1600\pc_model_router.py | 419 |
| tools\run_v21_1_certification.py | 418 |
| state\audit\current\ollama_local_benchmark_v2\benchmark_v2_phase_a.py | 410 |
| core\research_router.py | 408 |
| tools\run_master_real_benchmark_lab_v11.py | 406 |
| core\models\capability_registry_source.py | 405 |
| core\world\world_model.py | 403 |
| state\quarantine\quarantine_20260829_222000\core\pc_optimizer.py | 402 |
| core\pc_optimizer.py | 402 |
| core\agent\complex_task_orchestrator.py | 399 |
| core\providers\groq_provider.py | 380 |
| tools\run_context_benchmark_lab_v17.py | 378 |
| core\ezzio_master.py | 374 |
| tools\run_master_top_benchmark_lab_v8.py | 369 |
| core\operations\multi_mission_arbitrator.py | 364 |
| tests\test_web_ui_e2e.py | 363 |
| core\governance\approval\manager.py | 362 |
| web_server.py | 358 |
| tools\run_physical_benchmark_lab_v16.py | 355 |
| tools\run_v21_lab.py | 353 |
| tools\run_hardware_real_benchmark_lab_v9.py | 348 |
| core\capabilities\registry.py | 345 |
| scripts\AG_Forensic_Verifier_V3.py | 334 |
| core\operations\adaptive_model_optimizer.py | 332 |
| core\constitution\hardware_resource_governor.py | 331 |
| tools\run_master_full_model_gate_v4.py | 327 |
| tools\run_benchmark_v2.py | 320 |
| core\cognition\antigravity\client.py | 320 |
| ezzio_kernel.py | 317 |
| core\providers\ollama_provider.py | 314 |
| tools\run_ultimate_double_pass_lab_v15.py | 309 |
| core\api\endpoints.py | 308 |
| scripts\cleanup_v2_engine.py | 307 |
| core\agent\autonomous_e2e_engine.py | 307 |
| tools\run_v20_lab.py | 307 |
| runtime\hardware\production_kernel_v661.py | 305 |
| tools\run_master_forensic_lab_v12.py | 305 |
| tools\run_deep_llm_behavior_lab_v6.py | 303 |
| core\agents\swarm\engine.py | 303 |

## Duplication de noms de fichiers (backend)

### __init__.py (57 occurrences)
- core\accounts\__init__.py
- core\agents\swarm\__init__.py
- core\agents\__init__.py
- core\api\__init__.py
- core\artifacts\__init__.py
- core\cognition\__init__.py
- core\cognitive_engine\__init__.py
- core\config\__init__.py
- core\evidence\__init__.py
- core\generators\__init__.py
- core\governance\approval\__init__.py
- core\intents\__init__.py
- core\kernel\__init__.py
- core\knowledge\__init__.py
- core\memory\__init__.py
- core\models\discovery\__init__.py
- core\models\qualification\__init__.py
- core\models\__init__.py
- core\orchestration\__init__.py
- core\security\__init__.py
- core\system\__init__.py
- core\tasks\__init__.py
- core\telemetry\__init__.py
- core\voice\__init__.py
- core\world\__init__.py
- core\__init__.py
- legacy_archive\v17\__init__.py
- runtime\action\__init__.py
- runtime\agent\__init__.py
- runtime\bidi\__init__.py
- runtime\cognition\__init__.py
- runtime\contracts\__init__.py
- runtime\gateway\__init__.py
- runtime\hardware\__init__.py
- runtime\knowledge\__init__.py
- runtime\memory\__init__.py
- runtime\model_router\__init__.py
- runtime\observability\__init__.py
- runtime\reasoning\__init__.py
- runtime\recovery\analyzers\__init__.py
- runtime\recovery\decision\__init__.py
- runtime\recovery\queue\__init__.py
- runtime\recovery\rollback\__init__.py
- runtime\recovery\__init__.py
- runtime\rss\__init__.py
- runtime\security\__init__.py
- runtime\telemetry\__init__.py
- src\ezzio\connectors\__init__.py
- src\ezzio\graph\__init__.py
- src\ezzio\llm\__init__.py
- src\ezzio\memory\__init__.py
- src\ezzio\rag\__init__.py
- src\ezzio\self_repair\__init__.py
- src\ezzio\tools\__init__.py
- src\ezzio\__init__.py
- state\quarantine\quarantine_20260829_194121\graph\__init__.py
- v17\__init__.py

### actions.py (3 occurrences)
- core\actions.py
- routers\actions.py
- runtime\recovery\actions.py

### api.py (2 occurrences)
- src\ezzio\api.py
- state\quarantine\quarantine_20260829_194121\api.py

### app_config.py (2 occurrences)
- _backup_refonte_20260918_210557\app_config.py
- core\app_config.py

### archive_engine.py (2 occurrences)
- core\generators\archive_engine.py
- core\security\archive_engine.py

### autonomy.py (2 occurrences)
- core\autonomy.py
- routers\autonomy.py

### base_provider.py (3 occurrences)
- core\cognition\model_federation\base_provider.py
- core\providers\base_provider.py
- providers\base_provider.py

### base.py (5 occurrences)
- core\models\discovery\base.py
- core\tools\base.py
- runtime\agent\capability\base.py
- runtime\recovery\analyzers\base.py
- runtime\recovery\executor\base.py

### boot.py (2 occurrences)
- core\runtime\boot.py
- runtime\kernel\boot.py

### buffer.py (2 occurrences)
- legacy_archive\v17\events\buffer.py
- v17\events\buffer.py

### builder.py (8 occurrences)
- audit\identity_repair_20260826_192405\runtime\context\builder.py
- audit\snapshot_consumers_reconcile_20260826_190027\builder.py
- audit\snapshot_phase1_identity_20260826_190043\builder.py
- core\studio\builder.py
- legacy_archive\audit\identity_repair_20260826_192405\runtime\context\builder.py
- legacy_archive\audit\snapshot_consumers_reconcile_20260826_190027\builder.py
- legacy_archive\audit\snapshot_phase1_identity_20260826_190043\builder.py
- runtime\context\builder.py

### bus.py (3 occurrences)
- core\bus.py
- runtime\events\bus.py
- runtime\recovery\queue\bus.py

### canonical_identity.py (5 occurrences)
- audit\FINAL_CANONICAL_REPAIR_20260826_192805\core\identity\canonical_identity.py
- audit\identity_repair_20260826_192405\core\identity\canonical_identity.py
- core\identity\canonical_identity.py
- legacy_archive\audit\FINAL_CANONICAL_REPAIR_20260826_192805\core\identity\canonical_identity.py
- legacy_archive\audit\identity_repair_20260826_192405\core\identity\canonical_identity.py

### capabilities.py (2 occurrences)
- core\cognition\antigravity\capabilities.py
- routers\capabilities.py

### capability_registry_source.py (2 occurrences)
- backups\registry_integration\loader_repair_20260902_154636\capability_registry_source.py
- core\models\capability_registry_source.py

### capability.py (3 occurrences)
- legacy_archive\recovery\certified_state\capability.py
- recovery\certified_state\capability.py
- runtime\contracts\capability.py

### catalog.py (2 occurrences)
- legacy_archive\v17\models\catalog.py
- v17\models\catalog.py

### circuit_breaker.py (3 occurrences)
- core\routing\circuit_breaker.py
- core\runtime\circuit_breaker.py
- src\ezzio\llm\circuit_breaker.py

### classifier.py (5 occurrences)
- legacy_archive\v17\control\classifier.py
- legacy_archive\v17\orchestration\classifier.py
- runtime\incidents\classifier.py
- v17\control\classifier.py
- v17\orchestration\classifier.py

### client.py (2 occurrences)
- core\cognition\antigravity\client.py
- src\ezzio\llm\client.py

### cloud_brain_broker.py (15 occurrences)
- audit\canonical_sealed_20260826_194741\cloud_brain_broker.py
- audit\canonical_sealed_20260826_194835\cloud_brain_broker.py
- audit\contract_repair_backup_20260826_025737\cloud_brain_broker.py
- audit\FINAL_CANONICAL_REPAIR_20260826_192805\core\cloud_brain_broker.py
- audit\identity_repair_20260826_192405\core\cloud_brain_broker.py
- audit\snapshot_identity_v2_20260826_184954\cloud_brain_broker.py
- audit\snapshot_identity_v2_20260826_185024\cloud_brain_broker.py
- core\cloud_brain_broker.py
- legacy_archive\audit\canonical_sealed_20260826_194741\cloud_brain_broker.py
- legacy_archive\audit\canonical_sealed_20260826_194835\cloud_brain_broker.py
- legacy_archive\audit\contract_repair_backup_20260826_025737\cloud_brain_broker.py
- legacy_archive\audit\FINAL_CANONICAL_REPAIR_20260826_192805\core\cloud_brain_broker.py
- legacy_archive\audit\identity_repair_20260826_192405\core\cloud_brain_broker.py
- legacy_archive\audit\snapshot_identity_v2_20260826_184954\cloud_brain_broker.py
- legacy_archive\audit\snapshot_identity_v2_20260826_185024\cloud_brain_broker.py

### cloud_connectors.py (2 occurrences)
- core\cloud_connectors.py
- state\quarantine\quarantine_20260829_222000\core\cloud_connectors.py

### cloud_guard.py (2 occurrences)
- core\cloud_guard.py
- state\quarantine\quarantine_20260829_222000\core\cloud_guard.py

### codebase_indexer.py (2 occurrences)
- core\agent\codebase_indexer.py
- core\codebase_indexer.py

### cognitive_router.py (2 occurrences)
- core\cognition\cognitive_router.py
- core\cognitive_router.py

### collector.py (4 occurrences)
- runtime\hardware\trust\execution\attestation\collector.py
- runtime\incidents\collector.py
- runtime\rss\collector.py
- runtime\telemetry\collector.py

### comfy_api.py (2 occurrences)
- core\comfy_api.py
- state\quarantine\quarantine_20260829_222000\core\comfy_api.py

### config_port.py (2 occurrences)
- contracts\config_port.py
- legacy_archive\contracts\config_port.py

### context.py (8 occurrences)
- audit\identity_repair_20260826_192405\runtime\model_router\context.py
- audit\snapshot_phase1_identity_20260826_190043\context.py
- legacy_archive\audit\identity_repair_20260826_192405\runtime\model_router\context.py
- legacy_archive\audit\snapshot_phase1_identity_20260826_190043\context.py
- runtime\action\context.py
- runtime\execution\context.py
- runtime\kernel\context.py
- runtime\model_router\context.py

### contracts.py (5 occurrences)
- core\routing\contracts.py
- runtime\action\contracts.py
- runtime\agent\contracts.py
- runtime\memory\semantic\contracts.py
- runtime\recovery\contracts.py

### controller.py (4 occurrences)
- runtime\agent\controller.py
- runtime\governor\controller.py
- runtime\hardware\trust\execution\admission\controller.py
- runtime\recovery\controller.py

### coordinator.py (2 occurrences)
- legacy_archive\v18\agents\coordinator.py
- v18\agents\coordinator.py

### core_cloud_brain_broker.py (4 occurrences)
- audit\snapshot_pre_forensic_restore_20260826_180311\core_cloud_brain_broker.py
- audit\snapshot_pre_forensic_restore_20260826_180408\core_cloud_brain_broker.py
- legacy_archive\audit\snapshot_pre_forensic_restore_20260826_180311\core_cloud_brain_broker.py
- legacy_archive\audit\snapshot_pre_forensic_restore_20260826_180408\core_cloud_brain_broker.py

### core_dispatcher.py (8 occurrences)
- audit\snapshot_pre_forensic_restore_20260826_180311\core_dispatcher.py
- audit\snapshot_pre_forensic_restore_20260826_180408\core_dispatcher.py
- audit\snapshot_pre_restore_20260826_180137\core_dispatcher.py
- audit\snapshot_pre_restore_20260826_180233\core_dispatcher.py
- legacy_archive\audit\snapshot_pre_forensic_restore_20260826_180311\core_dispatcher.py
- legacy_archive\audit\snapshot_pre_forensic_restore_20260826_180408\core_dispatcher.py
- legacy_archive\audit\snapshot_pre_restore_20260826_180137\core_dispatcher.py
- legacy_archive\audit\snapshot_pre_restore_20260826_180233\core_dispatcher.py

### core_ezzio_master.py (10 occurrences)
- audit\snapshot_pre_fabric_connect_20260826_181659\core_ezzio_master.py
- audit\snapshot_pre_forensic_restore_20260826_180311\core_ezzio_master.py
- audit\snapshot_pre_forensic_restore_20260826_180408\core_ezzio_master.py
- audit\snapshot_pre_restore_20260826_180137\core_ezzio_master.py
- audit\snapshot_pre_restore_20260826_180233\core_ezzio_master.py
- legacy_archive\audit\snapshot_pre_fabric_connect_20260826_181659\core_ezzio_master.py
- legacy_archive\audit\snapshot_pre_forensic_restore_20260826_180311\core_ezzio_master.py
- legacy_archive\audit\snapshot_pre_forensic_restore_20260826_180408\core_ezzio_master.py
- legacy_archive\audit\snapshot_pre_restore_20260826_180137\core_ezzio_master.py
- legacy_archive\audit\snapshot_pre_restore_20260826_180233\core_ezzio_master.py

### core_integrations_discord_discord_client.py (8 occurrences)
- audit\snapshot_pre_forensic_restore_20260826_180311\core_integrations_discord_discord_client.py
- audit\snapshot_pre_forensic_restore_20260826_180408\core_integrations_discord_discord_client.py
- audit\snapshot_pre_restore_20260826_180137\core_integrations_discord_discord_client.py
- audit\snapshot_pre_restore_20260826_180233\core_integrations_discord_discord_client.py
- legacy_archive\audit\snapshot_pre_forensic_restore_20260826_180311\core_integrations_discord_discord_client.py
- legacy_archive\audit\snapshot_pre_forensic_restore_20260826_180408\core_integrations_discord_discord_client.py
- legacy_archive\audit\snapshot_pre_restore_20260826_180137\core_integrations_discord_discord_client.py
- legacy_archive\audit\snapshot_pre_restore_20260826_180233\core_integrations_discord_discord_client.py

### core_models_discovery_ollama.py (2 occurrences)
- legacy_archive\_forensic\phase_2_13_backup_20260828_000642\core_models_discovery_ollama.py
- legacy_archive\_forensic\phase_2_13R2_backup_20260828_000732\core_models_discovery_ollama.py

### core_models_fabric.py (2 occurrences)
- legacy_archive\_forensic\phase_2_13_backup_20260828_000642\core_models_fabric.py
- legacy_archive\_forensic\phase_2_13R2_backup_20260828_000732\core_models_fabric.py

### core_models_lifecycle.py (2 occurrences)
- legacy_archive\_forensic\phase_2_13_backup_20260828_000642\core_models_lifecycle.py
- legacy_archive\_forensic\phase_2_13R2_backup_20260828_000732\core_models_lifecycle.py

### core_models_registry.py (2 occurrences)
- legacy_archive\_forensic\phase_2_13_backup_20260828_000642\core_models_registry.py
- legacy_archive\_forensic\phase_2_13R2_backup_20260828_000732\core_models_registry.py

### creative_forge.py (2 occurrences)
- core\creative_forge.py
- state\quarantine\quarantine_20260829_222000\core\creative_forge.py

### decision.py (2 occurrences)
- runtime\governance\decision.py
- runtime\incidents\decision.py

### deploy_model_router_v1.py (2 occurrences)
- scripts\deploy_model_router_v1.py
- state\quarantine\quarantine_20260829_224200\scripts\deploy_model_router_v1.py

### discord_adapter.py (2 occurrences)
- legacy_archive\v17\channels\discord_adapter.py
- v17\channels\discord_adapter.py

### discovery.py (2 occurrences)
- core\capabilities\discovery.py
- runtime\hardware\topology\discovery.py

### dispatcher.py (17 occurrences)
- audit\canonical_sealed_20260826_194741\dispatcher.py
- audit\canonical_sealed_20260826_194835\dispatcher.py
- audit\contract_repair_backup_20260826_025737\dispatcher.py
- audit\FINAL_CANONICAL_REPAIR_20260826_192805\core\dispatcher.py
- audit\identity_repair_20260826_192405\core\dispatcher.py
- audit\snapshot_consumers_reconcile_20260826_190027\dispatcher.py
- audit\snapshot_phase2_signatures_20260826_190159\dispatcher.py
- audit\snapshot_phase2_signatures_20260826_190230\dispatcher.py
- core\dispatcher.py
- legacy_archive\audit\canonical_sealed_20260826_194741\dispatcher.py
- legacy_archive\audit\canonical_sealed_20260826_194835\dispatcher.py
- legacy_archive\audit\contract_repair_backup_20260826_025737\dispatcher.py
- legacy_archive\audit\FINAL_CANONICAL_REPAIR_20260826_192805\core\dispatcher.py
- legacy_archive\audit\identity_repair_20260826_192405\core\dispatcher.py
- legacy_archive\audit\snapshot_consumers_reconcile_20260826_190027\dispatcher.py
- legacy_archive\audit\snapshot_phase2_signatures_20260826_190159\dispatcher.py
- legacy_archive\audit\snapshot_phase2_signatures_20260826_190230\dispatcher.py

### drift_detector.py (2 occurrences)
- core\knowledge\drift_detector.py
- runtime\capabilities\security\drift_detector.py

### engine.py (10 occurrences)
- core\agents\swarm\engine.py
- core\orchestration\engine.py
- legacy_archive\v18\evidence\engine.py
- runtime\confidence\engine.py
- runtime\hardware\trust\engine.py
- runtime\memory\dream\engine.py
- runtime\policy\engine.py
- runtime\recovery\decision\engine.py
- src\ezzio\rag\engine.py
- v18\evidence\engine.py

### envelope.py (2 occurrences)
- core\cognition\evidence\envelope.py
- runtime\hardware\trust\envelope\envelope.py

### evaluator.py (2 occurrences)
- runtime\capabilities\evaluator.py
- runtime\hardware\trust\policy\evaluator.py

### events.py (4 occurrences)
- runtime\cognition\events.py
- runtime\core\events.py
- runtime\memory\events.py
- runtime\telemetry\events.py

### executor.py (3 occurrences)
- runtime\action\executor.py
- runtime\agent\executor.py
- runtime\hardware\router\executor.py

### experience_ledger.py (2 occurrences)
- core\evolution_experience\experience_ledger.py
- runtime\experience\experience_ledger.py

### experience.py (2 occurrences)
- legacy_archive\v19\product\experience.py
- v19\product\experience.py

### ezzio_app.py (2 occurrences)
- backups\cognitive_gateway_lifecycle_fix\20260902_174157\ezzio_app.py
- runtime\external\ezzio_app.py

### ezzio_identity.py (8 occurrences)
- audit\identity_repair_20260826_192405\core\ezzio_identity.py
- audit\snapshot_identity_v2_20260826_184954\ezzio_identity.py
- audit\snapshot_identity_v2_20260826_185024\ezzio_identity.py
- core\ezzio_identity.py
- legacy_archive\audit\identity_repair_20260826_192405\core\ezzio_identity.py
- legacy_archive\audit\snapshot_identity_v2_20260826_184954\ezzio_identity.py
- legacy_archive\audit\snapshot_identity_v2_20260826_185024\ezzio_identity.py
- routers\ezzio_identity.py

### ezzio_master.py (15 occurrences)
- audit\canonical_sealed_20260826_194741\ezzio_master.py
- audit\canonical_sealed_20260826_194835\ezzio_master.py
- audit\contract_repair_backup_20260826_025737\ezzio_master.py
- audit\FINAL_CANONICAL_REPAIR_20260826_192805\core\ezzio_master.py
- audit\identity_repair_20260826_192405\core\ezzio_master.py
- audit\snapshot_phase2_signatures_20260826_190159\ezzio_master.py
- audit\snapshot_phase2_signatures_20260826_190230\ezzio_master.py
- core\ezzio_master.py
- legacy_archive\audit\canonical_sealed_20260826_194741\ezzio_master.py
- legacy_archive\audit\canonical_sealed_20260826_194835\ezzio_master.py
- legacy_archive\audit\contract_repair_backup_20260826_025737\ezzio_master.py
- legacy_archive\audit\FINAL_CANONICAL_REPAIR_20260826_192805\core\ezzio_master.py
- legacy_archive\audit\identity_repair_20260826_192405\core\ezzio_master.py
- legacy_archive\audit\snapshot_phase2_signatures_20260826_190159\ezzio_master.py
- legacy_archive\audit\snapshot_phase2_signatures_20260826_190230\ezzio_master.py

### fabric.py (2 occurrences)
- core\models\fabric.py
- legacy_archive\snapshot\fabric.py

### factory.py (2 occurrences)
- core\agents\factory.py
- core\capabilities\factory.py

### gate.py (3 occurrences)
- core\models\qualification\gate.py
- legacy_archive\snapshot\gate.py
- runtime\governance\gate.py

### gemini_pool.py (3 occurrences)
- backups\gemini_key_loader_repair\20260902_165323\gemini_pool.py
- backups\registry_integration\20260902_131946\gemini_pool.py
- core\models\gemini_pool.py

### gemini_provider.py (7 occurrences)
- backups\gemini_provider_hardening\20260902_163501\gemini_provider.py
- backups\gemini_provider_hardening\20260902_164456\gemini_provider.py
- backups\gemini_provider_hardening\20260902_164533\gemini_provider.py
- backups\gemini_provider_hardening\20260902_164734\gemini_provider.py
- core\providers\gemini_provider.py
- providers\gemini_provider.py
- state\quarantine\quarantine_20260829_1715\gemini_provider.py

### gemini.py (3 occurrences)
- core\models\discovery\gemini.py
- runtime\model_router\providers\gemini.py
- state\quarantine\quarantine_20260829_223700\runtime\model_router\providers\gemini.py

### governor.py (6 occurrences)
- core\governor.py
- legacy_archive\v17\concurrency\governor.py
- runtime\execution\governor.py
- runtime\hardware\ryzen_optimizer\governor.py
- runtime\recovery\decision\governor.py
- v17\concurrency\governor.py

### groq_provider.py (4 occurrences)
- core\cognition\model_federation\groq_provider.py
- core\providers\groq_provider.py
- providers\groq_provider.py
- state\quarantine\quarantine_20260829_1715\groq_provider.py

### guard.py (2 occurrences)
- runtime\security\guard.py
- tools\guard.py

### health_monitor.py (2 occurrences)
- runtime\capabilities\health\health_monitor.py
- tools\health_monitor.py

### health.py (6 occurrences)
- routers\health.py
- runtime\gateway\health.py
- runtime\model_router\health.py
- runtime\sensors\health.py
- runtime\telemetry\health.py
- state\quarantine\quarantine_20260829_223700\runtime\model_router\health.py

### human_chat.py (2 occurrences)
- core\human_chat.py
- routers\human_chat.py

### human_loop.py (2 occurrences)
- core\human_loop.py
- routers\human_loop.py

### intelligence_router.py (3 occurrences)
- core\intelligence_router.py
- legacy_archive\v17\models\intelligence_router.py
- v17\models\intelligence_router.py

### intent.py (2 occurrences)
- legacy_archive\v17\orchestration\intent.py
- v17\orchestration\intent.py

### key_pool.py (2 occurrences)
- core\cognition\providers\key_pool.py
- core\models\key_pool.py

### key_scheduler.py (2 occurrences)
- providers\key_scheduler.py
- state\quarantine\quarantine_20260829_1715\key_scheduler.py

### ledger.py (3 occurrences)
- runtime\execution\ledger.py
- runtime\hardware\evidence\ledger.py
- runtime\recovery\ledger.py

### lifecycle.py (4 occurrences)
- core\models\lifecycle.py
- legacy_archive\snapshot\lifecycle.py
- runtime\capabilities\lifecycle.py
- runtime\execution\lifecycle.py

### llm.py (7 occurrences)
- backups\deterministic_certification\20260902_180917\llm.py
- backups\explicit_backend_contract\20260902_171204\llm.py
- backups\explicit_backend_http_fix\20260902_171525\llm.py
- backups\explicit_backend_http_fix2\20260902_171606\llm.py
- backups\explicit_backend_scope_fix\20260902_171411\llm.py
- backups\llm_endpoint_router_20260902_161249\llm.py
- runtime\routers\llm.py

### loader.py (2 occurrences)
- runtime\skills\loader.py
- src\ezzio\rag\loader.py

### loop.py (2 occurrences)
- runtime\agent\loop.py
- runtime\cognition\loop.py

### main.py (7 occurrences)
- runtime\temp\pytest_final\test_builder_run_python_and_te0\projects\calc_test_proj\src\main.py
- runtime\temp\pytest_final\test_dev_studio_end_to_end_pip0\projects\calculatrice_tva_cli\src\main.py
- runtime\temp\pytest_final\test_phase7_project_scaffoldin0\projects\demo_app\src\main.py
- runtime\temp\pytest_final\test_phase7_python_project_exe0\projects\calc_app\src\main.py
- runtime\temp\pytest_final\test_scaffolder_python_cli0\projects\calculatrice_cli\src\main.py
- runtime\temp\pytest_final\test_universal_routing_dev_stu0\projects\snake_game\src\main.py
- main.py

### manager.py (6 occurrences)
- core\governance\approval\manager.py
- core\tasks\manager.py
- legacy_archive\v17\concurrency\manager.py
- runtime\budget\manager.py
- runtime\recovery\rollback\manager.py
- v17\concurrency\manager.py

### master.py (5 occurrences)
- audit\FINAL_CANONICAL_REPAIR_20260826_192805\routers\master.py
- audit\identity_repair_20260826_192405\routers\master.py
- legacy_archive\audit\FINAL_CANONICAL_REPAIR_20260826_192805\routers\master.py
- legacy_archive\audit\identity_repair_20260826_192405\routers\master.py
- routers\master.py

### metrics.py (2 occurrences)
- core\observability\metrics.py
- runtime\telemetry\metrics.py

### model_registry.py (3 occurrences)
- core\routing\model_registry.py
- core\model_registry.py
- runtime\hardware\trust\models_governance\model_registry.py

### model_router.py (3 occurrences)
- backups\registry_integration\20260902_131946\model_router.py
- core\cognition\model_router.py
- state\quarantine\quarantine_20260829_223700\core\tool_gateway\model_router.py

### models.py (21 occurrences)
- core\governance\approval\models.py
- core\tasks\models.py
- legacy_archive\v17\concurrency\models.py
- legacy_archive\v17\control\models.py
- legacy_archive\v17\events\models.py
- legacy_archive\v17\read_model\models.py
- legacy_archive\v17\state\models.py
- legacy_archive\v18\fabric\models.py
- routers\models.py
- runtime\capabilities\models.py
- runtime\hardware\trust\execution\admission\models.py
- runtime\hardware\trust\execution\attestation\models.py
- runtime\hardware\trust\policy\models.py
- runtime\knowledge\models.py
- runtime\memory\models.py
- v17\concurrency\models.py
- v17\control\models.py
- v17\events\models.py
- v17\read_model\models.py
- v17\state\models.py
- v18\fabric\models.py

### nodes.py (2 occurrences)
- src\ezzio\graph\nodes.py
- state\quarantine\quarantine_20260829_194121\graph\nodes.py

### ollama_provider.py (4 occurrences)
- backups\deterministic_certification\20260902_180917\ollama_provider.py
- backups\ollama_default_model_fix\20260902_173040\ollama_provider.py
- core\providers\ollama_provider.py
- providers\ollama_provider.py

### ollama_sync.py (2 occurrences)
- legacy_archive\snapshot\ollama_sync.py
- runtime\models\ollama_sync.py

### ollama.py (3 occurrences)
- core\models\discovery\ollama.py
- runtime\model_router\providers\ollama.py
- state\quarantine\quarantine_20260829_223700\runtime\model_router\providers\ollama.py

### omnipresence.py (3 occurrences)
- core\omnipresence.py
- routers\omnipresence.py
- state\quarantine\quarantine_20260829_222000\core\omnipresence.py

### orchestrator.py (3 occurrences)
- core\agents\orchestrator.py
- core\cognition\orchestration\orchestrator.py
- core\orchestrator.py

### patch_engine.py (2 occurrences)
- core\agent\patch_engine.py
- tools\patch_engine.py

### pc_commander.py (2 occurrences)
- core\pc_commander.py
- routers\pc_commander.py

### pc_model_router.py (2 occurrences)
- core\pc_model_router.py
- state\quarantine\quarantine_20260829_1600\pc_model_router.py

### pc_optimizer.py (2 occurrences)
- core\pc_optimizer.py
- state\quarantine\quarantine_20260829_222000\core\pc_optimizer.py

### performance_store.py (2 occurrences)
- legacy_archive\v17\models\performance_store.py
- v17\models\performance_store.py

### planner.py (4 occurrences)
- legacy_archive\v17\orchestration\planner.py
- runtime\agent\planner.py
- runtime\reasoning\planner.py
- v17\orchestration\planner.py

### policies.py (2 occurrences)
- core\models\qualification\policies.py
- runtime\recovery\decision\policies.py

### policy.py (2 occurrences)
- core\cognition\antigravity\policy.py
- runtime\agent\policy.py

### probes.py (2 occurrences)
- core\models\qualification\probes.py
- core\models\probes.py

### provider_health.py (2 occurrences)
- core\models\provider_health.py
- providers\provider_health.py

### quality_gate.py (2 occurrences)
- core\quality_gate\quality_gate.py
- scripts\quality_gate.py

### registry.py (16 occurrences)
- core\agents\registry.py
- core\capabilities\registry.py
- core\models\registry.py
- core\tools\registry.py
- legacy_archive\snapshot\registry.py
- routers\registry.py
- runtime\action\registry.py
- runtime\agent\capability\registry.py
- runtime\capabilities\registry.py
- runtime\execution\registry.py
- runtime\hardware\cartography\registry\registry.py
- runtime\hardware\trust\models\registry.py
- runtime\hardware\trust\policy\registry.py
- runtime\hardware\trust\revocation\registry.py
- runtime\incidents\registry.py
- runtime\skills\registry.py

### resource.py (2 occurrences)
- runtime\execution\resource.py
- runtime\hardware\trust\execution\governor\resource.py

### retry.py (2 occurrences)
- runtime\agent\retry.py
- runtime\recovery\executor\retry.py

### router.py (22 occurrences)
- audit\identity_repair_20260826_192405\runtime\cognition\router.py
- audit\snapshot_phase2_signatures_20260826_190159\router.py
- backups\cloud_capability_exact\20260902_162934\router.py
- backups\deterministic_certification\20260902_180917\router.py
- backups\explicit_backend_contract\20260902_171204\router.py
- backups\explicit_backend_scope_fix\20260902_171411\router.py
- backups\llm_cloud_routing\20260902_162753\router.py
- backups\llm_endpoint_repair_20260902_161159\router.py
- backups\llm_primary_operational\20260902_162128\router.py
- backups\ollama_router_scope\20260902_173354\router.py
- backups\ollama_router_scope_fix\20260902_173519\router.py
- backups\ollama_router_scope_fix\20260902_173551\router.py
- core\models\router.py
- legacy_archive\audit\identity_repair_20260826_192405\runtime\cognition\router.py
- legacy_archive\audit\snapshot_phase2_signatures_20260826_190159\router.py
- legacy_archive\v17\api\router.py
- runtime\cognition\router.py
- runtime\execution\router.py
- runtime\hardware\router\router.py
- runtime\model_router\router.py
- runtime\reasoning\router.py
- v17\api\router.py

### run_capcap_tests.py (2 occurrences)
- capcap\tests\run_capcap_tests.py
- projects\capcap\tests\run_capcap_tests.py

### safe_actions.py (2 occurrences)
- core\safe_actions.py
- state\quarantine\quarantine_20260829_223700\routers\safe_actions.py

### sandbox.py (2 occurrences)
- core\sandbox.py
- runtime\execution\sandbox.py

### sanitizer.py (2 occurrences)
- legacy_archive\v17\sanitization\sanitizer.py
- v17\sanitization\sanitizer.py

### scheduler.py (2 occurrences)
- runtime\execution\scheduler.py
- runtime\memory\sleep\scheduler.py

### schemas.py (8 occurrences)
- backups\deterministic_certification\modelrequest_20260902_181512\schemas.py
- backups\deterministic_certification\modelrequest_final\schemas.py
- backups\explicit_backend_http_fix\20260902_171525\schemas.py
- backups\explicit_backend_http_fix2\20260902_171606\schemas.py
- core\agents\schemas.py
- core\schemas.py
- runtime\model_router\schemas.py
- src\ezzio\schemas.py

### scoring.py (2 occurrences)
- core\models\scoring.py
- legacy_archive\snapshot\scoring.py

### secrets_loader.py (2 occurrences)
- core\config\secrets_loader.py
- providers\secrets_loader.py

### secrets.py (2 occurrences)
- core\secrets.py
- runtime\security\secrets.py

### self_awareness.py (2 occurrences)
- core\agent\self_awareness.py
- core\knowledge\self_awareness.py

### service.py (9 occurrences)
- legacy_archive\v17\control\service.py
- legacy_archive\v17\read_model\service.py
- legacy_archive\v17\state\service.py
- runtime\capabilities\service.py
- runtime\temp\pytest_final\test_autonomous_rollback_on_fa0\rollback_test\service.py
- runtime\temp\pytest_final\test_harness_integration_run_c0\service.py
- v17\control\service.py
- v17\read_model\service.py
- v17\state\service.py

### session.py (2 occurrences)
- runtime\gateway\session.py
- runtime\memory\session.py

### skill_manager.py (2 occurrences)
- core\agent\skill_manager.py
- runtime\skills\skill_manager.py

### skill.py (5 occurrences)
- core\agent\skills\code_analyzer\skill.py
- runtime\skills\active\filesystem_search\skill.py
- runtime\skills\active\git_manager\skill.py
- runtime\skills\active\python_analyzer\skill.py
- runtime\temp\pytest_final\test_skill_timeout_bounded0\core\agent\skills\slow\skill.py

### snapshot_engine.py (2 occurrences)
- core\constitution\snapshot_engine.py
- runtime\hardware\cartography\snapshot_engine.py

### state.py (5 occurrences)
- runtime\action\state.py
- runtime\cognition\state.py
- runtime\execution\state.py
- runtime\kernel\state.py
- runtime\memory\sleep\state.py

### storage.py (2 occurrences)
- core\storage.py
- runtime\telemetry\storage.py

### store.py (9 occurrences)
- core\accounts\store.py
- core\cognition\evidence\store.py
- core\governance\approval\store.py
- core\tasks\store.py
- runtime\action\store.py
- runtime\knowledge\store.py
- runtime\memory\reflection\store.py
- runtime\memory\sqlite\store.py
- runtime\recovery\store.py

### supervisor.py (4 occurrences)
- core\supervisor.py
- routers\supervisor.py
- runtime\execution\supervisor.py
- runtime\external\supervisor.py

### system_sensor.py (2 occurrences)
- core\agent\sensors\system_sensor.py
- runtime\sensors\system_sensor.py

### target.py (2 occurrences)
- runtime\temp\pytest_final\test_practice_2_diff_search_re0\target.py
- runtime\temp\pytest_final\test_real_agent_task_execution0\task_workspace\target.py

### telemetry.py (4 occurrences)
- core\models\telemetry.py
- core\telemetry.py
- routers\telemetry.py
- runtime\model_router\telemetry.py

### test_main.py (6 occurrences)
- runtime\temp\pytest_final\test_builder_run_python_and_te0\projects\calc_test_proj\tests\test_main.py
- runtime\temp\pytest_final\test_dev_studio_end_to_end_pip0\projects\calculatrice_tva_cli\tests\test_main.py
- runtime\temp\pytest_final\test_phase7_project_scaffoldin0\projects\demo_app\tests\test_main.py
- runtime\temp\pytest_final\test_phase7_python_project_exe0\projects\calc_app\tests\test_main.py
- runtime\temp\pytest_final\test_scaffolder_python_cli0\projects\calculatrice_cli\tests\test_main.py
- runtime\temp\pytest_final\test_universal_routing_dev_stu0\projects\snake_game\tests\test_main.py

### token_compressor.py (3 occurrences)
- core\token_compressor.py
- runtime\optimization\token_compressor.py
- src\ezzio\memory\token_compressor.py

### tracer.py (2 occurrences)
- core\observability\tracer.py
- core\telemetry\tracer.py

### validator.py (4 occurrences)
- runtime\capabilities\validator.py
- runtime\hardware\evidence\validator.py
- runtime\memory\reflection\validator.py
- runtime\skills\validator.py

### vector_store.py (2 occurrences)
- runtime\agent\ledger\vector_store.py
- runtime\memory\semantic\vector_store.py

### verifier.py (2 occurrences)
- runtime\agent\verifier.py
- runtime\hardware\trust\execution\attestation\verifier.py

### web_server.py (2 occurrences)
- backups\boot_secrets_preload\20260902_170033\web_server.py
- web_server.py

### workflow.py (2 occurrences)
- src\ezzio\graph\workflow.py
- state\quarantine\quarantine_20260829_194121\graph\workflow.py

## Tests (backend)

- Fichiers de test : **295**
- Fichiers source : **1314**
- Ratio : **22.5%**

## Secrets potentiels dans l'historique git

**Attention : à vérifier manuellement.**

```
p = GeminiProvider(api_key="K0")
p = GeminiProvider(api_key="K0")
-            p = mod.GeminiProvider(api_key="K0")
+    p = GeminiProvider(api_key="K0")
+    mock_tavily = TavilyProvider(api_key="mock_key")
+    mock_p1 = TavilyProvider(api_key="mock_key")
+    mock_gemini = GeminiProvider(api_key="mock_key")
+    provider = GeminiProvider(api_key="test_key", model="gemini-1.5-pro")
+    p_gemini = GeminiProvider(api_key="mock_key")
+    p_gemini = GeminiProvider(api_key="mock_key")
+    p_gemini = GeminiProvider(api_key="mock_key")
+    mock_tavily = TavilyProvider(api_key="mock_key")
+    provider = TavilyProvider(api_key="test")
+    provider = GeminiProvider(api_key="test")
-    provider = OpenRouterProvider(api_key="test-key-mock")
-    return NvidiaNimProvider(api_key="nvapi-mock-qualification-key")
-    provider = NvidiaNimProvider(api_key="nvapi-valid-mock-key-12345")
-    provider = NvidiaNimProvider(api_key="nvapi-invalid-key")
-    provider = NvidiaNimProvider(api_key="mock-key")
-    provider = NvidiaNimProvider(api_key="mock-key")
```

## Dépendances obsolètes

### Python

| Paquet | Actuel | Dernier |
|---|---|---|
| anyio | 4.14.2 | 4.15.1 |
| azure-storage-blob | 12.30.0 | 12.30.2 |
| boto3 | 1.43.79 | 1.43.97 |
| botocore | 1.43.79 | 1.43.97 |
| click | 8.4.2 | 8.5.0 |
| cryptography | 50.0.0 | 50.0.1 |
| discord.py | 2.4.0 | 2.7.1 |
| fastapi-sso | 0.21.1 | 0.22.0 |
| filelock | 3.32.4 | 4.0.0 |
| fsspec | 2026.7.0 | 2026.9.0 |
| google-auth | 2.57.0 | 2.58.0 |
| google-genai | 2.22.0 | 2.24.0 |
| granian | 2.8.2 | 2.8.3 |
| gunicorn | 23.0.0 | 26.2.0 |
| huggingface_hub | 1.28.0 | 1.32.0 |
| idna | 3.19 | 3.20 |
| importlib_metadata | 8.9.0 | 9.0.1 |
| jiter | 0.16.0 | 0.17.0 |
| litellm | 1.98.0 | 1.101.0 |
| litellm-enterprise | 0.1.56 | 0.1.68 |



---

## Note de coherence (20260919_115334)

Les dossiers `core/evolution`, `core/evolution_experience`, `core/evolution_intelligence` et `core/evolution_simulation` ont ete **archives** dans `_archive/core_evolution/` lors du lot 1 (commit `235b251`). Les references a ces dossiers dans ce rapport sont **historiques**.


---

## Note de coherence (20260919_115458)

Les dossiers `core/evolution`, `core/evolution_experience`, `core/evolution_intelligence` et `core/evolution_simulation` ont ete **archives** dans `_archive/core_evolution/` lors du lot 1 (commit `235b251`).

Les references a ces dossiers dans ce rapport sont **historiques**.

Raison : cluster auto-referme ferme, non importe par le code actif dans `core/routers/runtime/scripts`.
