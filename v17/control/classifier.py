from v17.control.models import RiskLevel

def classify_action_risk(action_type: str, target: str) -> tuple[RiskLevel, bool]:
    # Read-only inquiries and conversational tasks
    if (
        action_type.startswith("GET_") or 
        action_type.startswith("SEARCH_") or 
        action_type in [
            "INSPECT_EVIDENCE", "TASK_CHAT", "TASK_FAST_REPLY", 
            "TASK_GENERAL", "TASK_REASONING", "TASK_RESEARCH", 
            "TASK_FORENSIC", "TASK_POWERSHELL", "TASK_PYTHON", 
            "TASK_CODE", "TASK_STRUCTURED_JSON"
        ]
    ):
        return RiskLevel.READ_ONLY, False

    # Low risk tasks
    if action_type in ["REQUEST_TASK_RESUME", "PING_SERVICE"]:
        return RiskLevel.LOW, False

    # Medium risk tasks
    if action_type in ["REQUEST_TASK_EXECUTION", "RUN_HEALTH_CHECK"]:
        return RiskLevel.MEDIUM, False

    # High risk tasks requiring explicit confirmation
    if action_type in ["REQUEST_TASK_CANCEL", "RESTART_SUBCOMPONENT", "TRIGGER_BACKUP_ROTATION"]:
        return RiskLevel.HIGH, True

    # Critical destructive tasks
    if action_type in ["PURGE_CACHE", "EMERGENCY_SHUTDOWN", "RESET_SESSION", "TASK_CRITICAL_OPERATION"]:
        return RiskLevel.CRITICAL, True

    # Default fallback: fail-closed HIGH risk
    return RiskLevel.HIGH, True
