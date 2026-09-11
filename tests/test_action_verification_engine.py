import pytest
from dataclasses import dataclass
from typing import Any, Dict

@dataclass
class ActionVerification:
    action: str
    target: str
    result_data: Any
    verified: bool
    evidence: Dict[str, Any]
    status: str

def verify_read_action(file_path: str, read_output: str) -> ActionVerification:
    import os
    if not os.path.exists(file_path):
        return ActionVerification(
            action="filesystem.read",
            target=file_path,
            result_data=read_output,
            verified=False,
            evidence={"reason": "File does not exist physically"},
            status="FAILED"
        )
    return ActionVerification(
        action="filesystem.read",
        target=file_path,
        result_data=read_output,
        verified=len(read_output) > 0,
        evidence={"bytes_verified": len(read_output.encode("utf-8"))},
        status="VERIFIED" if len(read_output) > 0 else "EMPTY"
    )

def test_action_verification_read_nominal(tmp_path):
    test_f = tmp_path / "verified_test.txt"
    test_f.write_text("Données vérifiées E-ZZIO", encoding="utf-8")
    
    verif = verify_read_action(str(test_f), "Données vérifiées E-ZZIO")
    assert verif.verified is True
    assert verif.status == "VERIFIED"
    assert verif.evidence["bytes_verified"] > 0

def test_action_verification_nonexistent_fails():
    verif = verify_read_action("ghost_file_xyz_123.txt", "")
    assert verif.verified is False
    assert verif.status == "FAILED"
