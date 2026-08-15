from core.talents.analyser import Analyser


def test_analyser_exposes_async_run():
    analyser = Analyser()

    assert analyser.name == "analyser"
    assert callable(analyser.run)
