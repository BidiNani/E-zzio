from typing import Dict, Any


def get_system_health(telemetry_collector, recovery_bus) -> Dict[str, Any]:
    """Agrège l'état des sous-systèmes critiques du Kernel E-zzio."""
    is_telemetry_active = telemetry_collector is not None
    is_recovery_armed = recovery_bus is not None

    return {
        "status": "ONLINE",
        "runtime": "READY",
        "memory": "ACTIVE",
        "telemetry": "RUNNING" if is_telemetry_active else "OFFLINE",
        "recovery": "ARMED" if is_recovery_armed else "OFFLINE",
        "hardware_mode": "CPU_ONLY",  # Préparation pour Ollama/GPU router
    }
