# Audit Python final - 20260919_115641

Genere apres lot 8a (fix requests). Non destructif.

## pyflakes - 107 erreurs restantes

```
core/cloud_connectors.py:69:12: undefined name 'requests'
core/cloud_connectors.py:70:16: undefined name 'requests'
core/cloud_connectors.py:132:16: undefined name 'requests'
core/cognitive_router.py:64:19: undefined name 'RoutingIntegrityError'
core/cognitive_router.py:74:19: undefined name 'RoutingIntegrityError'
core/creative_forge.py:51:13: undefined name 'requests'
core/omnipresence.py:166:9: undefined name 'requests'
core/pc_model_router.py:218:20: undefined name 'requests'
core/pc_model_router.py:235:20: undefined name 'requests'
core/pc_model_router.py:239:12: undefined name 'requests'
core/pc_model_router.py:241:12: undefined name 'requests'
core/pc_model_router.py:257:24: undefined name 'requests'
core/pc_model_router.py:259:24: undefined name 'requests'
core/pc_optimizer.py:257:20: undefined name 'requests'
core/safe_actions.py:506:1: redefinition of unused 'augment_queue_items' from line 161
core/safe_actions.py:554:1: redefinition of unused 'ledger' from line 190
core/safe_actions.py:585:1: redefinition of unused 'status' from line 218
core/safe_actions.py:683:1: redefinition of unused 'run_proposal' from line 385
core/agent\coding_agent_loop.py:151:23: undefined name 'List'
core/agent\coding_agent_loop.py:152:24: undefined name 'List'
core/agent\complex_task_orchestrator.py:320:9: local variable 'validation_state' is assigned to but never used
core/artifacts\provenance.py:13:1: 'dataclasses.field' imported but unused
core/cognition\model_federation\antigravity_provider.py:97:31: undefined name 'datetime'
core/cognition\model_federation\antigravity_provider.py:97:44: undefined name 'timezone'
core/cognition\orchestration\arbiter.py:93:9: local variable 'constitutional_rules' is assigned to but never used
core/cognition\providers\key_pool.py:68:13: local variable 'start_idx' is assigned to but never used
core/cognition\providers\key_pool.py:127:41: undefined name 'Any'
core/cognition\providers\key_pool.py:147:51: undefined name 'Any'
core/generators\doc_engine.py:16:5: 'docx.shared.Inches' imported but unused
core/generators\sheet_engine.py:26:13: 'openpyxl' imported but unused
core/identity\canonical_identity.py:52:9: local variable 'hash_path' is assigned to but never used
core/integrations\discord\discord_client.py:278:5: `global _http_client` is unused: name is never assigned in scope
core/integrations\discord\publisher.py:27:9: `nonlocal in_fence` is unused: name is never assigned in scope
core/kernel\__init__.py:2:1: 'core.kernel.native_harness.HarnessState' imported but unused
core/kernel\__init__.py:2:1: 'core.kernel.native_harness.InvalidTransitionError' imported but unused
core/kernel\__init__.py:2:1: 'core.kernel.native_harness.NativeHarness' imported but unused
core/kernel\__init__.py:2:1: 'core.kernel.native_harness.TaskSession' imported but unused
core/kernel\__init__.py:2:1: 'core.kernel.native_harness.TerminationReason' imported but unused
core/models\fabric.py:485:5: redefinition of unused 'quarantine_runtime_violation' from line 380
core/models\fabric.py:503:5: redefinition of unused 'rehabilitate_model' from line 398
core/models\provider_health.py:13:5: `global _ollama_status_cache` is unused: name is never assigned in scope
core/models\registry_refresh.py:197:5: local variable 'transition_cb' is assigned to but never used
core/models\registry_refresh.py:220:5: local variable 'new_records' is assigned to but never used
core/models\qualification\__init__.py:2:1: '.free_only.FREE_POLICY_NAME' imported but unused
core/models\qualification\__init__.py:2:1: '.free_only.FREE_POLICY_VERSION' imported but unused
core/models\qualification\__init__.py:2:1: '.free_only.accept_free_only' imported but unused
core/models\qualification\__init__.py:2:1: '.free_only.annotate_free_status' imported but unused
core/models\qualification\__init__.py:2:1: '.free_only.classify_free_status' imported but unused
core/models\qualification\__init__.py:2:1: '.free_only.filter_free_only' imported but unused
core/models\qualification\__init__.py:10:1: '.gate.QualificationGate' imported but unused
core/models\qualification\__init__.py:11:1: '.policies.QUALIFICATION_POLICY' imported but unused
core/models\qualification\__init__.py:11:1: '.policies.policy_allows' imported but unused
core/observability\metrics.py:713:1: redefinition of unused 'latency_snapshot' from line 249
core/operations\adaptive_model_optimizer.py:125:9: local variable 'res' is assigned to but never used
core/operations\continuous_operations_loop.py:78:9: local variable 'total_missions' is assigned to but never used
core/perception\audio_engine.py:64:9: local variable 'model' is assigned to but never used
core/perception\audio_engine.py:80:9: local variable 'chunk_len_ms' is assigned to but never used
core/perception\safe_fetcher.py:140:25: undefined name 'Path'
core/perception\vision_engine.py:49:13: undefined name 'logger'
core/providers\gemini_provider.py:22:1: 'core.models.gemini_pool.gemini_pool' imported but unused
core/providers\ollama_provider.py:278:9: local variable 'timeout' is assigned to but never used
core/providers\ollama_provider.py:315:9: local variable 'timeout' is assigned to but never used
core/recovery\sovereign_recovery_engine.py:12:1: 'os' imported but unused
core/recovery\sovereign_recovery_engine.py:17:1: 'typing.Any' imported but unused
core/recovery\sovereign_recovery_engine.py:17:1: 'typing.Dict' imported but unused
core/recovery\sovereign_recovery_engine.py:17:1: 'typing.List' imported but unused
core/recovery\sovereign_recovery_engine.py:17:1: 'typing.Optional' imported but unused
core/recovery\sovereign_recovery_engine.py:17:1: 'typing.Tuple' imported but unused
core/recovery\sovereign_recovery_engine.py:86:13: local variable 'e' is assigned to but never used
core/signals\signal_bus.py:93:46: undefined name 'Optional'
runtime/regen_manifest.py:3:1: 'sys' imported but unused
runtime/adapters\config\dotenv_provider.py:4:1: 'dotenv.load_dotenv' imported but unused
runtime/agent\__init__.py:1:1: '.loop.AgentLoop' imported but unused
runtime/archive_cleanup_20260918_220329\guardian.py:20:1: 'os' imported but unused
runtime/archive_cleanup_20260918_220329\guardian.py:30:1: 'core.app_config.REQUEST_TIMEOUT_S' imported but unused
runtime/archive_cleanup_20260918_220329\guardian.py:203:14: f-string is missing placeholders
runtime/archive_cleanup_20260918_220329\web_server.py:12:1: 'fastapi.middleware.cors.CORSMiddleware' imported but unused
runtime/archive_cleanup_20260918_220329\web_server.py:149:1: redefinition of unused 'health_check' from line 75
runtime/archive_cleanup_20260918_220329\web_server.py:159:5: redefinition of unused 'uvicorn' from line 7
runtime/archive_cleanup_20260918_220329\web_server.py:167:1: 'core.config.active_model.get_active_model' imported but unused
runtime/archive_cleanup_20260918_220329\web_server.py:168:1: 'httpx' imported but unused
runtime/archive_cleanup_20260918_220329\web_server.py:186:5: redefinition of unused 'get_active_model' from line 167
runtime/archive_cleanup_20260918_220329\web_server.py:405:9: redefinition of unused 'httpx' from line 168
runtime/bidi\ezzio_interface.py:90:9: undefined name 'CanonicalIdentity'
runtime/external\ezzio_app.py:3:1: 'logging' imported but unused
runtime/model_router\providers\gemini.py:1:1: 'os' imported but unused
runtime/model_router\providers\gemini.py:2:1: 'time' imported but unused
runtime/model_router\providers\gemini.py:3:1: 'requests' imported but unused
runtime/obsolete_tests_20260918_182439\test_agent_data_capability_mission.py:17:1: 'asyncio' imported but unused
runtime/obsolete_tests_20260918_182439\test_agent_data_capability_mission.py:20:1: 'time' imported but unused
runtime/obsolete_tests_20260918_182439\test_agent_end_to_end_pipeline.py:17:1: 'asyncio' imported but unused
runtime/obsolete_tests_20260918_182439\test_agent_end_to_end_pipeline.py:18:1: 'tempfile' imported but unused
runtime/obsolete_tests_20260918_182439\test_agent_mission_autonomy.py:17:1: 'asyncio' imported but unused
runtime/obsolete_tests_20260918_182439\test_agent_mission_autonomy.py:21:1: 'unittest.mock.MagicMock' imported but unused
runtime/obsolete_tests_20260918_182439\test_agent_mission_autonomy.py:82:9: local variable 'elapsed_ms' is assigned to but never used
runtime/obsolete_tests_20260918_182439\test_agent_test_repair_loop_mission.py:17:1: 'asyncio' imported but unused
runtime/obsolete_tests_20260918_182439\test_agent_test_repair_loop_mission.py:18:1: 'tempfile' imported but unused
runtime/obsolete_tests_20260918_182439\test_agent_web_capability_mission.py:17:1: 'asyncio' imported but unused
runtime/obsolete_tests_20260918_182439\test_agent_web_capability_mission.py:18:1: 'unittest.mock.MagicMock' imported but unused
runtime/obsolete_tests_20260918_182439\test_agent_web_capability_mission.py:20:1: 'core.agent.input_access_manager.InputDocument' imported but unused
runtime/obsolete_tests_20260918_182439\test_agent_web_capability_mission.py:20:1: 'core.agent.input_access_manager.InputType' imported but unused
runtime/temp\pytest_final\test_impact_analyzer_finds_tes0\src\analytics.py:2:1: 'os.path' imported but unused
runtime/temp\pytest_final\test_scaffolder_godot_and_pyga0\projects\pong_retro\src\game.py:4:1: 'sys' imported but unused
runtime/temp\pytest_final\test_scaffolder_godot_and_pyga0\projects\pong_retro\src\game.py:11:27: undefined name 'name'
runtime/tools\executors\filesystem.py:18:13: local variable 'e' is assigned to but never used
runtime/tools\executors\reflector.py:3:1: redefinition of unused 'ToolResult' from line 1
web_server.py:189:5: redefinition of unused 'uvicorn' from line 10
```

## vulture (min-confidence 80)

```
Traceback (most recent call last):
  File "<frozen runpy>", line 198, in _run_module_as_main
  File "<frozen runpy>", line 88, in _run_code
  File "G:\AI\E-zzio\.venv\Lib\site-packages\vulture\__main__.py", line 3, in <module>
    main()
  File "G:\AI\E-zzio\.venv\Lib\site-packages\vulture\core.py", line 666, in main
    config = make_config()
             ^^^^^^^^^^^^^
  File "G:\AI\E-zzio\.venv\Lib\site-packages\vulture\config.py", line 209, in make_config
    config = _parse_toml(fconfig)
             ^^^^^^^^^^^^^^^^^^^^
  File "G:\AI\E-zzio\.venv\Lib\site-packages\vulture\config.py", line 84, in _parse_toml
    data = tomllib.load(infile)
           ^^^^^^^^^^^^^^^^^^^^
  File "G:\Python312\Lib\tomllib\_parser.py", line 66, in load
    return loads(s, parse_float=parse_float)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "G:\Python312\Lib\tomllib\_parser.py", line 116, in loads
    raise suffixed_err(src, pos, "Invalid statement")
tomllib.TOMLDecodeError: Invalid statement (at line 52, column 1)
```

## Prochaines etapes

1. Traiter les imports inutilises (pyflakes - imported but unused)
2. Traiter les redefinitions (pyflakes - redefinition of unused)
3. Traiter les variables locales non utilisees
4. Trancher les 3 REF-PY restants
