import bootstrap

def test_brain_contract_exports():
    import runtime.realtime.brain as brain
    expected_symbols = ["BrainRequest", "BrainResponseChunk", "IBrainWorker", "MockBrainWorker"]
    missing = [sym for sym in expected_symbols if not hasattr(brain, sym)]
    assert not missing, f"Symboles manquants dans runtime.realtime.brain: {missing}"

if __name__ == "__main__":
    test_brain_contract_exports()
