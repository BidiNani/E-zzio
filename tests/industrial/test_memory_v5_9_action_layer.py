from runtime.memory.semantic.memory_action import MemoryAction
from runtime.memory.semantic.memory_executor import MemoryExecutor
from runtime.memory.semantic.memory_recovery import MemoryRecovery



def test_reinforce():

    assert (
        MemoryAction.apply(
            "REINFORCE"
        )
        ==
        "INCREASE_WEIGHT"
    )



def test_forget():

    assert (
        MemoryAction.apply(
            "FORGET"
        )
        ==
        "DECREASE_WEIGHT"
    )



def test_executor():

    result=MemoryExecutor().execute(
        "REINFORCE",
        {}
    )


    assert (
        result["status"]
        ==
        "EXECUTED"
    )



def test_quarantine():

    assert (
        MemoryAction.apply(
            "REVIEW"
        )
        ==
        "QUARANTINE"
    )



def test_recovery():

    result=MemoryRecovery().restore()


    assert (
        result["status"]
        ==
        "ROLLBACK"
    )



def test_unknown():

    assert (
        MemoryAction.apply(
            "UNKNOWN"
        )
        ==
        "NO_ACTION"
    )



def test_memory_update():

    result=MemoryExecutor().execute(
        "CONSOLIDATE",
        {}
    )


    assert (
        result["memory"]["last_action"]
        ==
        "LOCK_MEMORY"
    )



def test_safe_execution():

    result=MemoryExecutor().execute(
        "FORGET",
        {
            "id":1
        }
    )


    assert (
        result["action"]
        ==
        "DECREASE_WEIGHT"
    )
