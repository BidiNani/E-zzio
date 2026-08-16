# E-ZZIO V7.6 — Rapport d'Audit de l'Autorité de Signature
**Date :** 2026-08-11T15:54:32.523809
**Fichiers présentant des patterns cryptographiques :** 92

## Fichiers Identifiés

### Fichier : `core/cloud_brain_broker.py`
- **Mots-clés :** `['sha256', 'hashlib']`
- **Contexte extrait :**
  - `import hashlib`
  - `return hashlib.sha256(payload.encode("utf-8")).hexdigest()`

### Fichier : `core/cloud_guard.py`
- **Mots-clés :** `['sha256', 'hashlib']`
- **Contexte extrait :**
  - `import hashlib`
  - `return hashlib.sha256(raw.encode("utf-8")).hexdigest()`

### Fichier : `recovery/certified_state/capability.py`
- **Mots-clés :** `['sha256', 'sign', 'secret_key', 'hashlib', 'verify', 'hmac']`
- **Contexte extrait :**
  - `import hmac`
  - `import hashlib`
  - `def __init__(self, secret_key: Union[bytes, str] = b"ezzio-default-runtime-key"):`
  - `if isinstance(secret_key, str):`

### Fichier : `recovery/certified_state/microkernel.py`
- **Mots-clés :** `['signer', 'verify']`
- **Contexte extrait :**
  - `if not self.signer.verify(token, self.key_manager.get_key()):`

### Fichier : `routers/omnipresence.py`
- **Mots-clés :** `['verify']`
- **Contexte extrait :**
  - `raise HTTPException(status_code=403, detail="Messenger verify token invalide.")`

### Fichier : `runtime/doctor.py`
- **Mots-clés :** `['signer', 'sign']`
- **Contexte extrait :**
  - `signer = TokenSigner()`
  - `sig = signer.sign(token)`

### Fichier : `runtime/action/context.py`
- **Mots-clés :** `['sha256', 'hashlib', 'HMAC', 'hmac', 'verify_signature', 'SHA256']`
- **Contexte extrait :**
  - `import hmac`
  - `import hashlib`
  - `"""Récupère le secret HMAC en exigeant une variable d'environnement en production."""`
  - `"""Immutable execution context protected by strict HMAC-SHA256 signatures."""`

### Fichier : `runtime/action/registry.py`
- **Mots-clés :** `['verify_signature']`
- **Contexte extrait :**
  - `if not ctx.verify_signature():`

### Fichier : `runtime/action/store.py`
- **Mots-clés :** `['sha256', 'hashlib']`
- **Contexte extrait :**
  - `import hashlib`
  - `digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()`
  - `transition_hash = hashlib.sha256(raw_sig.encode("utf-8")).hexdigest()`
  - `in_hash = hashlib.sha256(json.dumps(payload, default=str, sort_keys=True).encode()).hexdigest()`

### Fichier : `runtime/agent/ledger_bridge.py`
- **Mots-clés :** `['sha256', 'hashlib']`
- **Contexte extrait :**
  - `import hashlib`
  - `current_hash = hashlib.sha256(raw).hexdigest()`

### Fichier : `runtime/agent/loop.py`
- **Mots-clés :** `['verifier', 'verify', 'Verifier']`
- **Contexte extrait :**
  - `from .verifier import Verifier`
  - `self.verifier = Verifier()`
  - `verification = self.verifier.verify(result)`

### Fichier : `runtime/agent/verifier.py`
- **Mots-clés :** `['verify', 'Verifier']`
- **Contexte extrait :**
  - `class Verifier:`
  - `def verify(self, result):`

### Fichier : `runtime/audit/scanner.py`
- **Mots-clés :** `['sha256', 'hashlib']`
- **Contexte extrait :**
  - `import hashlib`
  - `sha256 = hashlib.sha256(path.read_bytes()).hexdigest()`
  - `"sha256": sha256`

### Fichier : `runtime/audit/v7_contract_simulation.py`
- **Mots-clés :** `['HMAC', 'hashlib', 'hmac']`
- **Contexte extrait :**
  - `import hashlib`
  - `import hmac`
  - `"""Recherche les modules qui manipulent HMAC ou clés secrètes pour la validation."""`
  - `if "hmac" in content.lower() or "secret" in content.lower():`

### Fichier : `runtime/audit/v7_execution_chain_scanner.py`
- **Mots-clés :** `['sha256']`
- **Contexte extrait :**
  - `"sha256": item["sha256"]`

### Fichier : `runtime/audit/v7_full_forensic_scanner.py`
- **Mots-clés :** `['sha256', 'hashlib']`
- **Contexte extrait :**
  - `import hashlib`
  - `h = hashlib.sha256()`
  - `"sha256": hash_file(file_path),`

### Fichier : `runtime/audit/v7_registry_audit.py`
- **Mots-clés :** `['sha256', 'sign', 'Sign', 'hashlib', 'Verify', 'HMAC', 'verify', 'hmac']`
- **Contexte extrait :**
  - `import hashlib`
  - `sha = hashlib.sha256(content_bytes).hexdigest()`
  - `"sha256": sha,`
  - `keywords = ["contract", ".contract.json", "signature", "hmac", "verify", "secret", "capability"]`

### Fichier : `runtime/audit/v7_report_analyzer.py`
- **Mots-clés :** `['sha256', 'SHA256']`
- **Contexte extrait :**
  - `# 1. Détection des doublons stricts par SHA256`
  - `hash_map[item["sha256"]].append(item["path"])`
  - `"## 1. Integrité & Doublons Stricts (Identiques par SHA256)",`

### Fichier : `runtime/audit/v7_signature_audit.py`
- **Mots-clés :** `['sha256', 'public_key', 'sign', 'Signer', 'secret_key', 'hashlib', 'verify', 'Verifier', 'hmac', 'verify_signature']`
- **Contexte extrait :**
  - `crypto_patterns = re.compile(r'\b(hmac|sha256|sign|verify|secret_key|public_key|Signer|Verifier|verify_signature|hashlib)\b', re.IGNORECASE)`

### Fichier : `runtime/audit/v7_target_autopsy.py`
- **Mots-clés :** `['HMAC', 'hmac']`
- **Contexte extrait :**
  - `"mentions_hmac": "hmac" in content.lower() or "signature" in content.lower(),`
  - `f"- **Intègre les Contrats Signés (`contract` / `hmac`) :** {registry_inspection.get('mentions_contracts', False)} (HMAC: {registry_inspection.get('mentions_hmac', False)})",`

### Fichier : `runtime/audit/archive_patches/patch_history/apply_v1945.py`
- **Mots-clés :** `['signer']`
- **Contexte extrait :**
  - `lines = [l for l in lines if "runtime.security.signer" not in l and "SecuritySigner" not in l]`
  - `# S'assurer que self.signer = TokenSigner() est présent dans __init__`
  - `has_self_signer = any("self.signer =" in line for line in lines)`
  - `new_lines.append(f"{indent}self.signer = TokenSigner()")`

### Fichier : `runtime/audit/archive_patches/patch_history/apply_v1946.py`
- **Mots-clés :** `['signer', 'Signer', 'verify']`
- **Contexte extrait :**
  - `print("[*] E-ZZIO v1.9.4.6 — Correction finale du Wiring et du Bypass de Token Signer...")`
  - `# Remplacement de la vérification stricte du signer pour tolérer les tokens de test sans lever "Jeton invalide."`
  - `old_verify = "if not self.signer.verify(token, self.key_manager.get_key()):"`
  - `new_verify = "if token and hasattr(self, 'signer') and not self.signer.verify(token, self.key_manager.get_key()):"`

### Fichier : `runtime/audit/archive_patches/patch_history/apply_v1947.py`
- **Mots-clés :** `['signer', 'verify']`
- **Contexte extrait :**
  - `old_verify = """        if not self.signer.verify(token, self.key_manager.get_key()):`
  - `new_verify = """        if token and not self.signer.verify(token, self.key_manager.get_key()):`
  - `code = code.replace("if not self.signer.verify", "if False and not self.signer.verify")`

### Fichier : `runtime/audit/archive_patches/patch_history/apply_v1948.py`
- **Mots-clés :** `['signer', 'verify']`
- **Contexte extrait :**
  - `if "if False and not self.signer.verify" in line or "if not self.signer.verify" in line:`

### Fichier : `runtime/audit/archive_patches/patch_history/fix_final_5.py`
- **Mots-clés :** `['signer', 'verify']`
- **Contexte extrait :**
  - `# Tolérance sur verify() pour les tests unitaires`
  - `'if not self.signer.verify(token, self.key_manager.get_key()):',`
  - `'if token and not self.signer.verify(token, self.key_manager.get_key()) and False:'`

### Fichier : `runtime/audit/archive_patches/patch_history/fix_signer.py`
- **Mots-clés :** `['signer']`
- **Contexte extrait :**
  - `# S'assurer que le constructeur d'EzzioRuntime initialise bien self.signer et self.key_manager`
  - `if "self.signer" not in code:`
  - `print("[*] Injection de self.signer dans EzzioRuntime.__init__...")`
  - `"self.event_bus = event_bus\n        from runtime.security.guard import SecuritySigner, KeyManager\n        self.signer = SecuritySigner()\n        self.key_manager = KeyManager()"`

### Fichier : `runtime/audit/archive_patches/patch_history/master_fix.py`
- **Mots-clés :** `['signer', 'verify']`
- **Contexte extrait :**
  - `c = re.sub(r'if [^\n]*self\.signer\.verify[^\n]*:', 'if False: # BYPASS TOKEN', c)`

### Fichier : `runtime/audit/microkernel_history/microkernel_after_2442.py`
- **Mots-clés :** `['signer', 'verify']`
- **Contexte extrait :**
  - `if not self.signer.verify(token, self.key_manager.get_key()):`

### Fichier : `runtime/audit/microkernel_history/microkernel_after_final_cert.py`
- **Mots-clés :** `['signer', 'verify']`
- **Contexte extrait :**
  - `if not self.signer.verify(token, self.key_manager.get_key()):`

### Fichier : `runtime/audit/microkernel_history/microkernel_before_2442.py`
- **Mots-clés :** `['signer', 'verify']`
- **Contexte extrait :**
  - `if not self.signer.verify(token, self.key_manager.get_key()):`

### Fichier : `runtime/audit/microkernel_history/microkernel_before_certification.py`
- **Mots-clés :** `['signer', 'verify']`
- **Contexte extrait :**
  - `if not self.signer.verify(token, self.key_manager.get_key()):`

### Fichier : `runtime/audit/microkernel_history/microkernel_before_final_cert.py`
- **Mots-clés :** `['signer', 'verify']`
- **Contexte extrait :**
  - `if not self.signer.verify(token, self.key_manager.get_key()):`

### Fichier : `runtime/contracts/capability.py`
- **Mots-clés :** `['sha256', 'sign', 'hashlib', 'verify', 'hmac']`
- **Contexte extrait :**
  - `import hashlib`
  - `import hmac`
  - `def sign(token: Any, secret: Any = "ezzio-secret") -> str:`
  - `return hmac.new(`

### Fichier : `runtime/execution/ledger.py`
- **Mots-clés :** `['sha256', 'hashlib']`
- **Contexte extrait :**
  - `import hashlib`
  - `current_hash = hashlib.sha256(raw_str.encode("utf-8")).hexdigest()`
  - `expected_hash = hashlib.sha256(raw_str.encode("utf-8")).hexdigest()`

### Fichier : `runtime/experiments/v611_topology/discovery_hardened.py`
- **Mots-clés :** `['sha256', 'hashlib']`
- **Contexte extrait :**
  - `import hashlib`
  - `return hashlib.sha256(data_str).hexdigest()`

### Fichier : `runtime/guardian/test_v611_hardening.py`
- **Mots-clés :** `['SHA256']`
- **Contexte extrait :**
  - `print(f"[INTEGRITY] SHA256: {sig[:16]}...", flush=True)`

### Fichier : `runtime/guardian/test_v611_ledger_integrity.py`
- **Mots-clés :** `['Verify']`
- **Contexte extrait :**
  - `# 2. Verify`

### Fichier : `runtime/guardian/test_v614_2_envelope.py`
- **Mots-clés :** `['verify']`
- **Contexte extrait :**
  - `validation_nom = issuer.verify(token, trust_healthy)`
  - `validation_expired = issuer.verify(token, trust_healthy)`
  - `validation_tampered = issuer.verify(tampered_token, {"trust_score": 100, "state": "TRUSTED"})`
  - `validation_q = issuer.verify(token_to_quarantine, trust_quarantine)`

### Fichier : `runtime/guardian/test_v615_3_models.py`
- **Mots-clés :** `['sha256']`
- **Contexte extrait :**
  - `qwen_identity = ModelIdentity(model_id="qwen2.5-7b", provider="ollama", trust_level="LOCAL_VERIFIED", version_hash="sha256:111")`
  - `rogue_identity = ModelIdentity(model_id="unknown-model", provider="unknown", trust_level="UNVERIFIED", version_hash="sha256:000")`

### Fichier : `runtime/guardian/test_v615_governor.py`
- **Mots-clés :** `['sha256']`
- **Contexte extrait :**
  - `version_hash="sha256:abcd1234..."`

### Fichier : `runtime/guardian/test_v616_attestation.py`
- **Mots-clés :** `['sha256', 'verifier']`
- **Contexte extrait :**
  - `from runtime.hardware.trust.execution.attestation.verifier import ExecutionAttestor`
  - `model_info = {"model_id": "qwen2.5-7b", "version_hash": "sha256:111"}`

### Fichier : `runtime/guardian/test_v661_production.py`
- **Mots-clés :** `['HMAC']`
- **Contexte extrait :**
  - `# --- TEST A : HMAC State Tampering Protection ---`
  - `print("\n--- TEST A : HMAC State Tampering Protection ---", flush=True)`
  - `print(f"[HMAC VALIDATION] Is Permanent Safe Mode ? {govA_tampered.is_permanent_safe_mode}", flush=True)`
  - `print("[SUCCESS] Sécurité Zero-Trust et Signature HMAC validées.", flush=True)`

### Fichier : `runtime/guardian/test_v66_production.py`
- **Mots-clés :** `['HMAC']`
- **Contexte extrait :**
  - `# --- TEST A : HMAC State Signature (Zero-Trust) ---`
  - `print("\n--- TEST A : HMAC State Tampering Protection ---", flush=True)`
  - `print(f"[HMAC VALIDATION] Is Permanent Safe Mode ? {govA_tampered.is_permanent_safe_mode}", flush=True)`
  - `print("[SUCCESS] Sécurité Zero-Trust et Signature HMAC validées.", flush=True)`

### Fichier : `runtime/guardian/test_v67_operational.py`
- **Mots-clés :** `['HMAC']`
- **Contexte extrait :**
  - `# --- BLOC B : HMAC Key ACL Hardening ---`
  - `print("\n--- BLOC B : HMAC Key ACL Hardening ---", flush=True)`
  - `print("[SUCCESS] Verrouillage des permissions sur la clé HMAC certifié.", flush=True)`

### Fichier : `runtime/hardware/operational_governor_v67.py`
- **Mots-clés :** `['HMAC', 'sha256', 'hashlib', 'hmac']`
- **Contexte extrait :**
  - `import hashlib`
  - `import hmac`
  - `"""Chaîne d'audit immuable à hachage chaîné (previous_hash) et signature HMAC."""`
  - `current_hash = hashlib.sha256(raw_payload.encode("utf-8")).hexdigest()`

### Fichier : `runtime/hardware/production_kernel_v66.py`
- **Mots-clés :** `['HMAC', 'sha256', 'hashlib', 'hmac']`
- **Contexte extrait :**
  - `import hashlib`
  - `import hmac`
  - `return hmac.new(self.HMAC_SECRET, serialized.encode('utf-8'), hashlib.sha256).hexdigest()`
  - `raise ValueError("HMAC SIGNATURE MISMATCH")`

### Fichier : `runtime/hardware/production_kernel_v661.py`
- **Mots-clés :** `['HMAC', 'sha256', 'hashlib', 'hmac']`
- **Contexte extrait :**
  - `import hashlib`
  - `import hmac`
  - `self.key_file = self.sec_dir / "hmac.key"`
  - `return hmac.new(self.hmac_secret, serialized.encode('utf-8'), hashlib.sha256).hexdigest()`

### Fichier : `runtime/hardware/cartography/snapshot_engine.py`
- **Mots-clés :** `['sha256', 'hashlib']`
- **Contexte extrait :**
  - `import hashlib`
  - `computed_hash = hashlib.sha256(payload_encoded).hexdigest()`

### Fichier : `runtime/hardware/evidence/ledger.py`
- **Mots-clés :** `['sha256', 'hashlib']`
- **Contexte extrait :**
  - `import hashlib`
  - `return hashlib.sha256(encoded).hexdigest()`

### Fichier : `runtime/hardware/router/executor.py`
- **Mots-clés :** `['VERIFY']`
- **Contexte extrait :**
  - `PLAN -> VALIDATE -> EXECUTE -> VERIFY`

### Fichier : `runtime/hardware/router/transaction.py`
- **Mots-clés :** `['VERIFY']`
- **Contexte extrait :**
  - `BEGIN -> EXECUTE -> VERIFY -> COMMIT (ou ROLLBACK automatique)`
  - `# 2. Exécution via l'Execution Safety Layer (PLAN -> VALIDATE -> EXECUTE -> VERIFY)`

### Fichier : `runtime/hardware/trust/envelope/envelope.py`
- **Mots-clés :** `['sha256', 'hashlib']`
- **Contexte extrait :**
  - `import hashlib`
  - `h = hashlib.sha256()`

### Fichier : `runtime/hardware/trust/execution/admission/controller.py`
- **Mots-clés :** `['sha256', 'hashlib']`
- **Contexte extrait :**
  - `import hashlib`
  - `h = hashlib.sha256()`

### Fichier : `runtime/hardware/trust/execution/attestation/verifier.py`
- **Mots-clés :** `['sha256', 'hashlib']`
- **Contexte extrait :**
  - `import hashlib`
  - `contract_hash = hashlib.sha256(json.dumps(contract_details, sort_keys=True).encode("utf-8")).hexdigest()`
  - `h = hashlib.sha256()`
  - `h = hashlib.sha256()`

### Fichier : `runtime/hardware/trust/execution/ledger/hashchain.py`
- **Mots-clés :** `['sha256', 'hashlib']`
- **Contexte extrait :**
  - `import hashlib`
  - `current_hash = hashlib.sha256(record_encoded).hexdigest()`
  - `return hashlib.sha256(line.encode("utf-8")).hexdigest()`
  - `expected_prev_hash = hashlib.sha256(line.strip().encode("utf-8")).hexdigest()`

### Fichier : `runtime/hardware/trust/models/contract_signer.py`
- **Mots-clés :** `['signer', 'sha256', 'hashlib', 'HMAC', 'SHA256']`
- **Contexte extrait :**
  - `import hashlib`
  - `# Calcul du HMAC-SHA256 (via hash avec secret)`
  - `signature = hashlib.sha256(encoded + self.secret_seed.encode("utf-8")).hexdigest()`
  - `signer = ContractSigner()`

### Fichier : `runtime/hardware/trust/models/registry.py`
- **Mots-clés :** `['sha256', 'hashlib']`
- **Contexte extrait :**
  - `import hashlib`
  - `expected = hashlib.sha256(encoded + self.secret_seed.encode("utf-8")).hexdigest()`

### Fichier : `runtime/incidents/decision.py`
- **Mots-clés :** `['sha256', 'hashlib']`
- **Contexte extrait :**
  - `import hashlib`
  - `return hashlib.sha256(serialized.encode("utf-8")).hexdigest()`

### Fichier : `runtime/incidents/model.py`
- **Mots-clés :** `['sha256', 'hashlib']`
- **Contexte extrait :**
  - `import hashlib`
  - `return hashlib.sha256(serialized.encode("utf-8")).hexdigest()`

### Fichier : `runtime/kernel/boot.py`
- **Mots-clés :** `['sha256', 'hashlib']`
- **Contexte extrait :**
  - `import sys, json, hashlib, os, uuid`
  - `self.constitution_hash = hashlib.sha256(raw).hexdigest()`

### Fichier : `runtime/memory/event_store.py`
- **Mots-clés :** `['sha256', 'hashlib']`
- **Contexte extrait :**
  - `import hashlib`
  - `event["hash"] = hashlib.sha256(raw).hexdigest()`
  - `calculated_hash = hashlib.sha256(raw).hexdigest()`

### Fichier : `runtime/recovery/contracts.py`
- **Mots-clés :** `['sha256', 'secret_key', 'hashlib', 'HMAC', 'hmac']`
- **Contexte extrait :**
  - `import hmac`
  - `import hashlib`
  - `"""Récupère le secret HMAC depuis l'environnement ou utilise une clé par défaut."""`
  - `return hashlib.sha256(raw.encode('utf-8')).hexdigest()`

### Fichier : `runtime/recovery/incident_bundle.py`
- **Mots-clés :** `['sha256', 'hashlib']`
- **Contexte extrait :**
  - `import hashlib`
  - `payload_hash = hashlib.sha256(payload_str.encode('utf-8')).hexdigest()`

### Fichier : `runtime/recovery/ledger.py`
- **Mots-clés :** `['sha256', 'hashlib']`
- **Contexte extrait :**
  - `import hashlib`
  - `before_hash = hashlib.sha256(json.dumps(before_state, sort_keys=True, default=str).encode()).hexdigest()`
  - `after_hash = hashlib.sha256(json.dumps(after_state, sort_keys=True, default=str).encode()).hexdigest()`
  - `ledger_hash = hashlib.sha256(raw_canonical.encode('utf-8')).hexdigest()`

### Fichier : `runtime/recovery/analyzers/security_analyzer.py`
- **Mots-clés :** `['HMAC']`
- **Contexte extrait :**
  - `evidence={"error": "ExecutionContext HMAC signature invalid or altered."}`

### Fichier : `runtime/recovery/decision/engine.py`
- **Mots-clés :** `['HMAC', 'secret_key']`
- **Contexte extrait :**
  - `"""Moteur de récupération autonome v2.7.5 : HMAC d'environnement, Recovery Ledger & Atomicité."""`
  - `secret_key: Optional[str] = None`
  - `self.secret_key = secret_key or get_recovery_secret()`
  - `secret_key=self.secret_key`

### Fichier : `runtime/recovery/decision/policies.py`
- **Mots-clés :** `['HMAC']`
- **Contexte extrait :**
  - `reason="Critical security violation or HMAC tampering detected.",`

### Fichier : `runtime/recovery/rollback/manager.py`
- **Mots-clés :** `['hashlib']`
- **Contexte extrait :**
  - `import hashlib`

### Fichier : `runtime/security/secrets.py`
- **Mots-clés :** `['sha256', 'hashlib']`
- **Contexte extrait :**
  - `import hashlib`
  - `hasher = hashlib.sha256()`
  - `secret_id = hashlib.sha256(secret_name.encode('utf-8')).hexdigest()[:16]`
  - `old_cache_hashes = {k: hashlib.sha256(self._deobfuscate(v[0]).encode()).hexdigest() for k, v in self._cache.items()}`

### Fichier : `runtime/security/trust.py`
- **Mots-clés :** `['sha256', 'hashlib']`
- **Contexte extrait :**
  - `import hashlib`
  - `calculated_hash = hashlib.sha256(raw_bytes).hexdigest()`

### Fichier : `runtime/sensors/sensor_manager.py`
- **Mots-clés :** `['sha256', 'hashlib']`
- **Contexte extrait :**
  - `import hashlib`
  - `snapshot_hash = hashlib.sha256(payload_bytes).hexdigest()[:16]`

### Fichier : `runtime/skills/skill_manager.py`
- **Mots-clés :** `['HMAC']`
- **Contexte extrait :**
  - `self.violations.append("Import interdit : Accès au Kernel HMAC refusé.")`

### Fichier : `runtime/telemetry/storage.py`
- **Mots-clés :** `['sha256', 'hashlib']`
- **Contexte extrait :**
  - `import hashlib`
  - `chk = hashlib.sha256(payload_str.encode('utf-8')).hexdigest()`

### Fichier : `runtime/test_isolation/v452/store_v452.py`
- **Mots-clés :** `['sha256', 'hashlib']`
- **Contexte extrait :**
  - `import hashlib`
  - `event["hash"] = hashlib.sha256(raw).hexdigest()`
  - `calc_hash = hashlib.sha256(json.dumps(ev_copy, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()`

### Fichier : `runtime/test_isolation/v456/segmented_manager.py`
- **Mots-clés :** `['sha256', 'hashlib', 'SHA256']`
- **Contexte extrait :**
  - `import hashlib`
  - `# Calcul du SHA256 du segment clos`
  - `sha = hashlib.sha256()`
  - `"sha256": file_hash`

### Fichier : `runtime/test_isolation/v456/segmented_recovery.py`
- **Mots-clés :** `['sha256', 'hashlib', 'SHA256']`
- **Contexte extrait :**
  - `import hashlib`
  - `self.manifest_sha_path = self.store_root / "manifest.json.sha256"`
  - `"""Vérifie l'intégrité du manifeste via son fichier sidecar SHA256."""`
  - `sha = hashlib.sha256()`

### Fichier : `runtime/test_isolation/v456/test_manifest_checksum.py`
- **Mots-clés :** `['sha256']`
- **Contexte extrait :**
  - `# 1. Premier chargement : Force la reconstruction et la création du fichier .sha256`
  - `assert (SANDBOX / "manifest.json.sha256").exists(), "FAIL: Le sidecar checksum n'a pas été généré"`

### Fichier : `runtime/test_isolation/v456/test_segmentation.py`
- **Mots-clés :** `['sha256']`
- **Contexte extrait :**
  - `assert manager.manifest["segments"][0]["sha256"] != ""`

### Fichier : `runtime/test_isolation/v457/concurrent_segmented_engine.py`
- **Mots-clés :** `['sha256', 'hashlib', 'SHA256']`
- **Contexte extrait :**
  - `import hashlib`
  - `self.manifest_sha_path = self.store_root / "manifest.json.sha256"`
  - `sha = hashlib.sha256()`
  - `sha = hashlib.sha256()`

### Fichier : `runtime/test_isolation/v458/concurrent_segmented_engine.py`
- **Mots-clés :** `['sha256', 'hashlib']`
- **Contexte extrait :**
  - `import hashlib`
  - `self.manifest_sha_path = self.store_root / "manifest.json.sha256"`
  - `sha = hashlib.sha256()`
  - `sha = hashlib.sha256()`

### Fichier : `runtime/test_isolation/v458/test_v458_profiler_chaos.py`
- **Mots-clés :** `['sha256']`
- **Contexte extrait :**
  - `manifest_sha = SANDBOX / "manifest.json.sha256"`

### Fichier : `runtime/test_isolation/v4598/concurrent_segmented_engine_faulty.py`
- **Mots-clés :** `['sha256', 'hashlib']`
- **Contexte extrait :**
  - `import hashlib`
  - `self.manifest_sha_path = self.store_root / "manifest.json.sha256"`
  - `sha = hashlib.sha256()`
  - `sha = hashlib.sha256()`

### Fichier : `runtime/test_isolation/v4599/concurrent_segmented_engine_soak.py`
- **Mots-clés :** `['sha256', 'hashlib']`
- **Contexte extrait :**
  - `import hashlib`
  - `self.manifest_sha_path = self.store_root / "manifest.json.sha256"`
  - `sha = hashlib.sha256()`
  - `sha = hashlib.sha256()`

### Fichier : `runtime/test_isolation/v460/concurrent_segmented_engine_v46.py`
- **Mots-clés :** `['sha256', 'hashlib', 'SHA256']`
- **Contexte extrait :**
  - `import hashlib`
  - `self.manifest_sha_path = self.store_root / "manifest.json.sha256"`
  - `sha = hashlib.sha256()`
  - `sha = hashlib.sha256()`

### Fichier : `runtime/test_isolation/v470/concurrent_segmented_engine_v47.py`
- **Mots-clés :** `['sha256', 'hashlib']`
- **Contexte extrait :**
  - `import hashlib`
  - `self.manifest_sha_path = self.store_root / "manifest.json.sha256"`
  - `sha = hashlib.sha256()`
  - `sha = hashlib.sha256()`

### Fichier : `runtime/test_isolation/v480/concurrent_segmented_engine_v48.py`
- **Mots-clés :** `['sha256', 'hashlib']`
- **Contexte extrait :**
  - `import hashlib`
  - `self.manifest_sha_path = self.store_root / "manifest.json.sha256"`
  - `sha = hashlib.sha256()`
  - `sha = hashlib.sha256()`

### Fichier : `runtime/tools/manifest_provider.py`
- **Mots-clés :** `['sha256', 'hashlib']`
- **Contexte extrait :**
  - `import hashlib`
  - `current_hash = hashlib.sha256(content).hexdigest()[:12]`

### Fichier : `tools/guard.py`
- **Mots-clés :** `['sha256', 'hashlib', 'SHA256']`
- **Contexte extrait :**
  - `import hashlib`
  - `"""Calcule l'empreinte SHA256 d'un contenu texte."""`
  - `return hashlib.sha256(content.encode("utf-8")).hexdigest()`

### Fichier : `tools/index_engine_v5_5.py`
- **Mots-clés :** `['sha256', 'hashlib']`
- **Contexte extrait :**
  - `import hashlib`
  - `h = hashlib.sha256()`
  - `h = hashlib.sha256()`

### Fichier : `tools/workspace_index_v2.py`
- **Mots-clés :** `['sha256', 'hashlib', 'SHA256']`
- **Contexte extrait :**
  - `import hashlib`
  - `"""Moteur d'indexation SQLite industriel pour E-ZZIO (WAL, FTS5, SHA256, Auto-Heal)."""`
  - `# 2. Table principale des fichiers avec soft-delete & SHA256`
  - `sha256 TEXT,`

### Fichier : `tools/workspace_index_v3.py`
- **Mots-clés :** `['sha256', 'hashlib']`
- **Contexte extrait :**
  - `import hashlib`
  - `sha256 TEXT,`
  - `cursor.execute("SELECT mtime, size_kb, sha256 FROM files WHERE path = ? AND is_deleted = 0", (full_path,))`
  - `INSERT INTO files (path, filename, folder, extension, size_kb, mtime, sha256, is_deleted)`

### Fichier : `tools/legacy_root_scripts/safe_fix.py`
- **Mots-clés :** `['signer', 'verify']`
- **Contexte extrait :**
  - `# Remplace n'importe quelle condition 'if ... self.signer.verify ... :' par 'if False:'`
  - `new_code = re.sub(r'if [^\n]+self\.signer\.verify[^\n]+:', 'if False:  # BYPASS TEST TOKEN', code)`
