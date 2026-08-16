# V7.11.0.5 — Isolation Refactoring Map

### 🔴 Violation HIGH : `core\memory_core.py`
- **Import interdit :** `runtime.memory.sqlite.store` (core -> runtime)
- **Suggestion :** `Replace direct import with runtime.contracts.runtime_contract`

### 🔴 Violation HIGH : `runtime\kernel_legacy_v2.py`
- **Import interdit :** `runtime.core.message` (runtime -> core)
- **Suggestion :** `Replace direct import with runtime.contracts.core_contract`

### 🔴 Violation HIGH : `runtime\agent\controller.py`
- **Import interdit :** `runtime.core.microkernel` (runtime -> core)
- **Suggestion :** `Replace direct import with runtime.contracts.core_contract`

### 🔴 Violation HIGH : `runtime\agent\executor.py`
- **Import interdit :** `runtime.core.microkernel` (runtime -> core)
- **Suggestion :** `Replace direct import with runtime.contracts.core_contract`

### 🔴 Violation HIGH : `runtime\cognition\__init__.py`
- **Import interdit :** `runtime.cognition.core` (runtime -> core)
- **Suggestion :** `Replace direct import with runtime.contracts.core_contract`

### 🔴 Violation HIGH : `runtime\core\context.py`
- **Import interdit :** `runtime.contracts.execution_context` (core -> runtime)
- **Suggestion :** `Replace direct import with runtime.contracts.runtime_contract`

### 🔴 Violation HIGH : `runtime\core\context.py`
- **Import interdit :** `runtime.contracts.capability` (core -> runtime)
- **Suggestion :** `Replace direct import with runtime.contracts.runtime_contract`

### 🔴 Violation HIGH : `runtime\core\ezzio_core.py`
- **Import interdit :** `runtime.identity.persona` (core -> runtime)
- **Suggestion :** `Replace direct import with runtime.contracts.runtime_contract`

### 🔴 Violation HIGH : `runtime\core\ezzio_core.py`
- **Import interdit :** `runtime.cognition.router` (core -> runtime)
- **Suggestion :** `Replace direct import with runtime.contracts.runtime_contract`

### 🔴 Violation HIGH : `runtime\core\ezzio_core.py`
- **Import interdit :** `runtime.telemetry.collector` (core -> runtime)
- **Suggestion :** `Replace direct import with runtime.contracts.runtime_contract`

### 🔴 Violation HIGH : `runtime\core\ezzio_core.py`
- **Import interdit :** `runtime.recovery.queue.bus` (core -> runtime)
- **Suggestion :** `Replace direct import with runtime.contracts.runtime_contract`

### 🔴 Violation HIGH : `runtime\gateway\adapter.py`
- **Import interdit :** `runtime.core.ezzio_core` (runtime -> core)
- **Suggestion :** `Replace direct import with runtime.contracts.core_contract`

### 🔴 Violation MEDIUM : `runtime\guardian\test_v615_3_models.py`
- **Import interdit :** `runtime.hardware.trust.models_governance.model_registry` (runtime -> governance)
- **Suggestion :** `Replace direct import with runtime.contracts.governance_contract`

### 🔴 Violation MEDIUM : `runtime\guardian\test_v615_3_models.py`
- **Import interdit :** `runtime.hardware.trust.models_governance.budget` (runtime -> governance)
- **Suggestion :** `Replace direct import with runtime.contracts.governance_contract`

### 🔴 Violation MEDIUM : `runtime\hardware\trust\execution\admission\controller.py`
- **Import interdit :** `runtime.hardware.trust.models_governance.budget` (runtime -> governance)
- **Suggestion :** `Replace direct import with runtime.contracts.governance_contract`

### 🔴 Violation MEDIUM : `runtime\hardware\trust\models_governance\budget.py`
- **Import interdit :** `runtime.hardware.trust.models_governance.model_registry` (runtime -> governance)
- **Suggestion :** `Replace direct import with runtime.contracts.governance_contract`

### 🔴 Violation HIGH : `runtime\memory\session.py`
- **Import interdit :** `runtime.core.message` (runtime -> core)
- **Suggestion :** `Replace direct import with runtime.contracts.core_contract`

### 🔴 Violation HIGH : `runtime\memory\cortex\episodic.py`
- **Import interdit :** `runtime.core.events` (runtime -> core)
- **Suggestion :** `Replace direct import with runtime.contracts.core_contract`

### 🔴 Violation HIGH : `runtime\memory\dream\engine.py`
- **Import interdit :** `runtime.core.events` (runtime -> core)
- **Suggestion :** `Replace direct import with runtime.contracts.core_contract`

### 🔴 Violation HIGH : `runtime\memory\reflection\store.py`
- **Import interdit :** `runtime.core.events` (runtime -> core)
- **Suggestion :** `Replace direct import with runtime.contracts.core_contract`

### 🔴 Violation HIGH : `runtime\memory\reflection\validator.py`
- **Import interdit :** `runtime.core.events` (runtime -> core)
- **Suggestion :** `Replace direct import with runtime.contracts.core_contract`

### 🔴 Violation HIGH : `runtime\memory\semantic\contracts.py`
- **Import interdit :** `core.memory_core` (runtime -> core)
- **Suggestion :** `Replace direct import with runtime.contracts.core_contract`

### 🔴 Violation HIGH : `runtime\memory\sleep\scheduler.py`
- **Import interdit :** `runtime.core.events` (runtime -> core)
- **Suggestion :** `Replace direct import with runtime.contracts.core_contract`
