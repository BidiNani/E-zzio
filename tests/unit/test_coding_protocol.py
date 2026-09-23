from __future__ import annotations

import pytest

from core.coding.policy import CodingPolicy
from core.coding.protocol import CodingPolicyViolationError, CodingRequest


def test_empty_task_description_rejected() -> None:
    """Vérifie qu'une CodingRequest avec task_description='' est rejetée."""
    policy = CodingPolicy(root_dir=".")
    request = CodingRequest(task_description="")

    with pytest.raises(CodingPolicyViolationError, match="task_description est vide"):
        policy.evaluate_request(request)
