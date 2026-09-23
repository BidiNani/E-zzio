# Couverture de tests — E-ZZIO

**Derniere mise a jour** : 2026-09-23 17:10 UTC

## Resume

- **Fichiers a 100%** : 93
- **Fichiers < 100%** : 171
- **Couverture globale** : 59.8%
- **Statements totaux** : 22060
- **Statements non couverts** : 8870

## Fichiers a 100%

| Fichier | Statements |
|---|---|
| `core\__init__.py` | 0 |
| `core\actions.py` | 28 |
| `core\agents\__init__.py` | 4 |
| `core\agents\schemas.py` | 23 |
| `core\agents\swarm\__init__.py` | 5 |
| `core\api\__init__.py` | 2 |
| `core\app_config.py` | 30 |
| `core\artifacts\__init__.py` | 2 |
| `core\autonomy.py` | 17 |
| `core\capabilities\capability_policy.py` | 22 |
| `core\capabilities\capability_qualification.py` | 30 |
| `core\capabilities\discovery.py` | 74 |
| `core\capabilities\external_qualification.py` | 48 |
| `core\capabilities\trust.py` | 51 |
| `core\capabilities\workspace_decisions.py` | 93 |
| `core\coding\__init__.py` | 2 |
| `core\coding\model_registry.py` | 181 |
| `core\coding\policy.py` | 24 |
| `core\coding\protocol.py` | 44 |
| `core\coding\providers.py` | 139 |
| `core\cognition\__init__.py` | 6 |
| `core\cognition\model_router.py` | 38 |
| `core\config\__init__.py` | 3 |
| `core\config\active_model.py` | 26 |
| `core\config\config_provider.py` | 26 |
| `core\config\iconfig_provider.py` | 9 |
| `core\decision_router.py` | 35 |
| `core\ezzio_identity.py` | 12 |
| `core\frozen_core\__init__.py` | 2 |
| `core\generators\__init__.py` | 9 |
| `core\generators\media_engine.py` | 47 |
| `core\governance\approval\__init__.py` | 3 |
| `core\governance\approval\models.py` | 58 |
| `core\identity\identity_context.py` | 62 |
| `core\integrations\discord\hitl_bridge.py` | 44 |
| `core\integrations\discord\routing_rules.py` | 23 |
| `core\intents\__init__.py` | 0 |
| `core\kernel\__init__.py` | 1 |
| `core\knowledge\__init__.py` | 3 |
| `core\memory\__init__.py` | 4 |
| `core\memory\instance.py` | 2 |
| `core\models\__init__.py` | 0 |
| `core\models\discovery\__init__.py` | 0 |
| `core\models\discovery\base.py` | 7 |
| `core\models\discovery\litellm.py` | 24 |
| `core\models\errors.py` | 8 |
| `core\models\ezzio_router.py` | 10 |
| `core\models\lifecycle.py` | 31 |
| `core\models\provider_health.py` | 20 |
| `core\models\qualification\__init__.py` | 3 |
| `core\models\qualification\policies.py` | 26 |
| `core\models\telemetry.py` | 27 |
| `core\observability\tracer.py` | 31 |
| `core\orchestration\__init__.py` | 3 |
| `core\orchestrator.py` | 35 |
| `core\providers\google_calendar_provider.py` | 14 |
| `core\providers\google_docs_provider.py` | 14 |
| `core\providers\google_drive_provider.py` | 14 |
| `core\providers\google_gateway.py` | 18 |
| `core\providers\google_gmail_provider.py` | 14 |
| `core\providers\igoogle_provider.py` | 5 |
| `core\providers\iresearch_provider.py` | 5 |
| `core\providers\jina_provider.py` | 21 |
| `core\providers\searxng_provider.py` | 23 |
| `core\providers\tavily_provider.py` | 22 |
| `core\sandbox.py` | 45 |
| `core\schemas.py` | 53 |
| `core\secrets.py` | 12 |
| `core\security\__init__.py` | 2 |
| `core\security\archive_validator.py` | 40 |
| `core\security\guardrail.py` | 17 |
| `core\security\immutable_audit.py` | 50 |
| `core\security\quota_manager.py` | 30 |
| `core\security\secret_redactor.py` | 20 |
| `core\security\untrusted.py` | 8 |
| `core\storage.py` | 25 |
| `core\system\__init__.py` | 2 |
| `core\talents\analyser.py` | 9 |
| `core\talents\base_talent.py` | 4 |
| `core\tasks\__init__.py` | 4 |
| `core\tasks\models.py` | 35 |
| `core\tasks\store.py` | 35 |
| `core\telemetry\__init__.py` | 2 |
| `core\telemetry\tracer.py` | 39 |
| `core\tools\base.py` | 8 |
| `core\tools\registry.py` | 13 |
| `core\url_reader.py` | 28 |
| `core\utils\http_pool.py` | 12 |
| `core\vision_bridge.py` | 97 |
| `core\voice\__init__.py` | 2 |
| `core\voice\voice_duplex_engine.py` | 93 |
| `core\voice\voice_gateway.py` | 120 |
| `core\world\__init__.py` | 2 |

## Fichiers < 100%

| Couverture | Miss | Statements | Fichier |
|---|---|---|---|
| 0.0% | 2 | 2 | `core\agents\swarm.py` |
| 0.0% | 34 | 34 | `core\models\discovery\ollama.py` |
| 0.0% | 39 | 39 | `core\ezzio_truth_guard.py` |
| 0.0% | 40 | 40 | `core\governor.py` |
| 0.0% | 40 | 40 | `core\sdk.py` |
| 0.0% | 41 | 41 | `core\human_chat_guard.py` |
| 0.0% | 42 | 42 | `core\cognition\self_healing_engine.py` |
| 0.0% | 42 | 42 | `core\model_registry.py` |
| 0.0% | 58 | 58 | `core\cloud_connectors.py` |
| 0.0% | 59 | 59 | `core\knowledge_connectors.py` |
| 0.0% | 63 | 63 | `core\agents\token_frugality.py` |
| 0.0% | 65 | 65 | `core\agents\blackboard.py` |
| 0.0% | 66 | 66 | `core\cognition\ecol_runtime_interceptor.py` |
| 0.0% | 68 | 68 | `core\hd_forge.py` |
| 0.0% | 71 | 71 | `core\agents\orchestrator.py` |
| 0.0% | 76 | 76 | `core\cognition\ecol_runtime_contract.py` |
| 0.0% | 90 | 90 | `core\ezzio_message_brain.py` |
| 0.0% | 92 | 92 | `core\cloud_brain_broker.py` |
| 0.0% | 93 | 93 | `core\comfy_api.py` |
| 0.0% | 98 | 98 | `core\cognition\ecol_universal_enforcement.py` |
| 0.0% | 113 | 113 | `core\omnipresence.py` |
| 0.0% | 134 | 134 | `core\dependency_graph_v49.py` |
| 0.0% | 142 | 142 | `core\pc_optimizer.py` |
| 0.0% | 145 | 145 | `core\cloud_guard.py` |
| 0.0% | 172 | 172 | `core\human_chat.py` |
| 0.0% | 176 | 176 | `core\pc_commander.py` |
| 0.0% | 177 | 177 | `core\cognition\cognitive_governor.py` |
| 0.0% | 340 | 340 | `core\cognition\decision_ledger.py` |
| 4.1% | 190 | 201 | `core\pc_model_router.py` |
| 4.9% | 49 | 53 | `core\response_guard.py` |
| 9.8% | 89 | 102 | `core\models\qualification\probes.py` |
| 10.4% | 61 | 72 | `core\agents\swarm\watcher.py` |
| 10.5% | 211 | 245 | `core\models\fabric.py` |
| 10.8% | 49 | 59 | `core\models\qualification\gate.py` |
| 11.2% | 55 | 66 | `core\agents\swarm\inspector.py` |
| 11.6% | 161 | 195 | `core\knowledge\self_awareness.py` |
| 13.3% | 237 | 287 | `core\knowledge\drift_detector.py` |
| 13.8% | 204 | 243 | `core\research_router.py` |
| 13.8% | 46 | 55 | `core\security\file_lock.py` |
| 14.9% | 52 | 65 | `core\accounts\oauth_flow.py` |
| 16.4% | 155 | 196 | `core\models\provider_http.py` |
| 16.7% | 34 | 44 | `core\models\discovery\groq.py` |
| 17.0% | 127 | 163 | `core\models\capability_registry_source.py` |
| 17.5% | 163 | 213 | `core\agent\input_access_manager.py` |
| 18.4% | 28 | 37 | `core\accounts\oauth_registry.py` |
| 19.3% | 38 | 49 | `core\agents\swarm\sentinel.py` |
| 20.2% | 73 | 98 | `core\accounts\store.py` |
| 21.5% | 67 | 93 | `core\agents\factory.py` |
| 21.6% | 210 | 294 | `core\memory\tiers.py` |
| 23.3% | 57 | 78 | `core\security\archive_engine.py` |
| 24.5% | 32 | 45 | `core\api\state_store.py` |
| 25.0% | 24 | 34 | `core\models\discovery\openrouter.py` |
| 25.0% | 43 | 62 | `core\llm_engine.py` |
| 26.7% | 23 | 35 | `core\models\discovery\gemini.py` |
| 27.8% | 63 | 96 | `core\agent\agent_provider.py` |
| 29.1% | 30 | 45 | `core\memory\legacy_manager.py` |
| 29.7% | 133 | 211 | `core\api\endpoints.py` |
| 30.4% | 72 | 113 | `core\models\key_pool.py` |
| 32.4% | 63 | 97 | `core\models\registry_refresh_service.py` |
| 32.8% | 34 | 55 | `core\routing\circuit_breaker.py` |
| 35.1% | 172 | 286 | `core\safe_actions.py` |
| 35.4% | 156 | 255 | `core\agent\complex_task_orchestrator.py` |
| 40.0% | 48 | 94 | `core\agent\data_source_manager.py` |
| 42.3% | 27 | 52 | `core\agent\codebase_indexer.py` |
| 42.7% | 51 | 94 | `core\capabilities\google_workspace_provider.py` |
| 43.0% | 43 | 83 | `core\agent\coding_agent_loop.py` |
| 43.2% | 44 | 80 | `core\creative_forge.py` |
| 43.3% | 39 | 75 | `core\perception\youtube_adapter.py` |
| 43.4% | 110 | 212 | `core\omni_brain.py` |
| 43.8% | 22 | 46 | `core\capabilities\slack_provider.py` |
| 44.4% | 26 | 54 | `core\perception\unified_perception.py` |
| 45.3% | 41 | 82 | `core\capabilities\github_provider.py` |
| 45.9% | 32 | 66 | `core\governance\diff_viewer.py` |
| 46.3% | 78 | 155 | `core\providers\ollama_provider.py` |
| 46.4% | 23 | 48 | `core\identity\canonical_identity.py` |
| 47.7% | 41 | 83 | `core\perception\rss_adapter.py` |
| 47.7% | 54 | 111 | `core\config\secrets_loader.py` |
| 48.2% | 38 | 75 | `core\runtime\backend_supervisor.py` |
| 48.8% | 80 | 185 | `core\agents\swarm\engine.py` |
| 50.3% | 59 | 123 | `core\supervisor.py` |
| 51.5% | 65 | 152 | `core\coding\coder_worker.py` |
| 52.4% | 26 | 59 | `core\intents\fabric_connector.py` |
| 52.5% | 80 | 180 | `core\agent\tools_registry.py` |
| 53.8% | 29 | 65 | `core\frozen_core\manifest.py` |
| 54.0% | 68 | 155 | `core\cognitive_router.py` |
| 54.1% | 166 | 375 | `core\perception\universal_reader.py` |
| 54.9% | 34 | 87 | `core\perception\safe_fetcher.py` |
| 55.0% | 43 | 114 | `core\cognition\providers\key_pool.py` |
| 55.1% | 44 | 113 | `core\models\qualification\free_only.py` |
| 58.1% | 29 | 77 | `core\studio\builder.py` |
| 59.2% | 50 | 127 | `core\models\registry_refresh.py` |
| 59.5% | 42 | 111 | `core\security\guardian.py` |
| 59.8% | 26 | 76 | `core\agent\capability_manager.py` |
| 60.7% | 58 | 168 | `core\capabilities\registry.py` |
| 60.9% | 30 | 102 | `core\health\evolution_decision.py` |
| 62.0% | 23 | 68 | `core\capabilities\composio_provider.py` |
| 62.0% | 35 | 105 | `core\perception\social_media_extractor.py` |
| 63.8% | 20 | 75 | `core\studio\studio_agent.py` |
| 64.9% | 29 | 85 | `core\agent\web_access_manager.py` |
| 65.1% | 39 | 144 | `core\agents\registry.py` |
| 66.9% | 118 | 421 | `core\observability\metrics.py` |
| 69.1% | 32 | 109 | `core\orchestration\engine.py` |
| 69.6% | 19 | 80 | `core\security\audit_ledger.py` |
| 69.7% | 53 | 192 | `core\human_loop.py` |
| 69.8% | 20 | 88 | `core\routing\registry.py` |
| 71.1% | 23 | 84 | `core\integrations\discord\publisher.py` |
| 71.1% | 24 | 92 | `core\system\cpu_tuning.py` |
| 71.1% | 13 | 61 | `core\generators\archive_engine.py` |
| 71.8% | 48 | 207 | `core\providers\groq_provider.py` |
| 71.9% | 38 | 139 | `core\project_janitor.py` |
| 72.3% | 27 | 109 | `core\agent\agent_guard.py` |
| 72.9% | 24 | 101 | `core\capabilities\web_provider.py` |
| 73.1% | 13 | 55 | `core\perception\vision_engine.py` |
| 73.8% | 19 | 116 | `core\studio\scaffolder.py` |
| 74.3% | 19 | 93 | `core\agent\mission_controller.py` |
| 74.6% | 10 | 51 | `core\agent\skill_manager.py` |
| 75.2% | 26 | 115 | `core\agent\command_executor.py` |
| 75.4% | 24 | 112 | `core\artifacts\provenance.py` |
| 75.4% | 26 | 131 | `core\generators\image_engine.py` |
| 76.4% | 40 | 184 | `core\governance\approval\manager.py` |
| 76.6% | 26 | 115 | `core\coding\bridge.py` |
| 77.0% | 29 | 141 | `core\security\secrets_vault.py` |
| 77.8% | 8 | 56 | `core\capabilities\hermes_mcp_gateway.py` |
| 78.4% | 82 | 509 | `core\models\_dormant_litellm_types.py` |
| 78.8% | 16 | 86 | `core\integrations\discord\ui_components.py` |
| 79.6% | 44 | 230 | `core\ezzio_master.py` |
| 79.7% | 22 | 131 | `core\kernel\native_harness.py` |
| 79.8% | 41 | 240 | `core\providers\gemini_provider.py` |
| 80.8% | 14 | 106 | `core\models\registry.py` |
| 81.1% | 13 | 97 | `core\authority\user_preservation.py` |
| 81.3% | 11 | 69 | `core\token_compressor.py` |
| 81.5% | 19 | 117 | `core\memory\unified_gateway.py` |
| 82.1% | 23 | 136 | `core\capabilities\semantic_evidence.py` |
| 82.2% | 11 | 81 | `core\perception\audio_engine.py` |
| 82.4% | 29 | 266 | `core\operations\multi_mission_arbitrator.py` |
| 82.4% | 14 | 137 | `core\models\gemini_pool.py` |
| 82.6% | 31 | 233 | `core\agent\autonomous_e2e_engine.py` |
| 83.3% | 7 | 62 | `core\agent\patch_engine.py` |
| 83.3% | 8 | 58 | `core\perception\qr_engine.py` |
| 83.4% | 34 | 288 | `core\world\world_model.py` |
| 84.3% | 10 | 77 | `core\agent\coder_federation.py` |
| 84.6% | 17 | 166 | `core\memory\strategic_memory.py` |
| 84.8% | 17 | 120 | `core\governance\approval\store.py` |
| 85.5% | 27 | 168 | `core\telemetry\agent_tracer.py` |
| 86.4% | 10 | 159 | `core\agent\strategic_master.py` |
| 86.5% | 10 | 89 | `core\security\backup_engine.py` |
| 87.5% | 13 | 172 | `core\agent\self_awareness.py` |
| 88.6% | 8 | 70 | `core\providers\base_provider.py` |
| 89.5% | 4 | 49 | `core\evidence_store.py` |
| 90.0% | 5 | 64 | `core\bus.py` |
| 90.4% | 8 | 88 | `core\generators\sheet_engine.py` |
| 90.5% | 6 | 79 | `core\routing\model_registry.py` |
| 90.6% | 13 | 142 | `core\generators\generation_router.py` |
| 90.8% | 5 | 82 | `core\rag\simple_rag.py` |
| 91.2% | 6 | 118 | `core\orchestration\dag.py` |
| 91.4% | 4 | 84 | `core\generators\doc_engine.py` |
| 91.5% | 6 | 49 | `core\system_cleanup.py` |
| 91.8% | 3 | 71 | `core\agent\evidence_logger.py` |
| 92.1% | 7 | 111 | `core\agent\nothing_impossible.py` |
| 92.5% | 4 | 71 | `core\agent\interaction_control.py` |
| 93.7% | 1 | 59 | `core\generators\pdf_engine.py` |
| 94.4% | 3 | 75 | `core\security\ledger_engine.py` |
| 94.9% | 3 | 66 | `core\security\unified_vault.py` |
| 94.9% | 2 | 73 | `core\signals\signal_bus.py` |
| 95.0% | 3 | 86 | `core\cognition\cognitive_gateway.py` |
| 95.1% | 2 | 59 | `core\tasks\manager.py` |
| 95.1% | 2 | 70 | `core\capabilities\factory.py` |
| 99.1% | 0 | 87 | `core\generators\slide_engine.py` |
| 99.1% | 0 | 87 | `core\smart_vision.py` |
| 99.1% | 2 | 171 | `core\capabilities\research_fabric.py` |
| 99.2% | 0 | 110 | `core\operations\continuous_operations_loop.py` |

## Note sur les pragmas `no cover`

Certaines branches sont marquees `# pragma: no cover` :

- `core/generators/slide_engine.py` L82 : branche defensive `if subtitle_shape:`
  (python-pptx fournit toujours un placeholder pour le layout de titre standard).
- `core/tasks/store.py` classe `ITaskStore` : Protocol stub sans logique metier
  (fins implicites des methodes `save`, `get_by_id`, `list_by_state`).
