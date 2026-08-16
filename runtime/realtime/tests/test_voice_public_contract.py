import bootstrap

def test_public_contract_exports():
    import runtime.realtime.voice as voice

    expected_symbols = [
        "VoiceRequest",
        "VoiceMetrics",
        "CancellationToken",
        "KokoroEngine",
        "VoiceGateway",
        "VoiceTelemetry",
        "AdaptiveStreamChunker",
        "BargeInController",
        "BargeInEvent",
        "AudioStreamWorker",
    ]

    missing = [sym for sym in expected_symbols if not hasattr(voice, sym)]
    assert not missing, f"Symboles manquants dans runtime.realtime.voice: {missing}"

if __name__ == "__main__":
    test_public_contract_exports()
