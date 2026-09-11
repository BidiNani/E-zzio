import pytest
from runtime.agent.loop import AgentLoop

def test_agent_loop_operational_execution_nominal():
    loop = AgentLoop()
    res = loop.run("Analyse standard en lecture seule")
    
    assert res is not None
    assert "state" in res
    assert res["state"] in ["COMPLETED", "HALTED", "EXECUTING", "VERIFYING"]
    assert "ledger_events" in res
    assert res["ledger_events"] > 0

def test_agent_loop_operational_constitution_blocking_immutable_path():
    loop = AgentLoop()
    # Action ciblant un scope protégé immuable
    res = loop.run("runtime/constitution/modify_rules.md")
    
    assert res["state"] == "HALTED"
    assert "Constitution violation" in res.get("reason", "")
    assert res["ledger_events"] > 0
