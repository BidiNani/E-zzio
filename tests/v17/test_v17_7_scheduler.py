import pytest
from v17.concurrency.governor import resource_governor

def test_v17_7_resource_governor_bounds():
    assert resource_governor.capacity == 20
    assert resource_governor.active_tasks >= 0
