import pytest

def test_task_analyzer_and_keyword_extraction():
    from runtime.cognition.analyzer import TaskAnalyzer

    simple = TaskAnalyzer.analyze("Bonjour comment vas tu ?")
    assert simple.complexity_score < 0.4

    complex_task = TaskAnalyzer.analyze("Réalise une architecture complète et une synthèse d'optimisation cloud security refactor.")
    assert complex_task.complexity_score > 0.4
    assert "architecture" in complex_task.keywords_detected

    keywords = TaskAnalyzer.extract_keywords("Utilisateur préfère l'environnement Python pour son projet")
    assert "utilisateur" in keywords
    assert "environnement" in keywords
    assert "python" in keywords

def test_knowledge_store_keyword_search(tmp_path):
    from runtime.knowledge.store import KnowledgeStore
    from runtime.knowledge.models import KnowledgeItem, SourceType

    db_file = str(tmp_path / "test_ezzio.db")
    store = KnowledgeStore(db_path=db_file)

    item1 = KnowledgeItem(content="Note temporaire sur Linux", importance=0.2, source_type=SourceType.RSS)
    item2 = KnowledgeItem(content="Directive fondamentale d'E-ZZIO en Python", importance=0.9, source_type=SourceType.USER)

    store.save_item(item1)
    store.save_item(item2)

    results = store.search_knowledge_by_keywords(["python"])
    assert len(results) == 1
    assert results[0]["content"] == "Directive fondamentale d'E-ZZIO en Python"

def test_ezzio_brain_full_pipeline(tmp_path):
    from runtime.cognition import EzzioBrain
    from runtime.knowledge.store import KnowledgeStore
    from runtime.rss.cache import RSSCacheStore
    from runtime.memory import MemoryGateway
    from runtime.reasoning import ExecutionTarget

    rss_cache = RSSCacheStore(str(tmp_path / "brain_rss.db"))
    rss_cache.save_article("guid_abc", "AI News", "http://ai.org", "New local model released in Python", "2026-07-27")

    brain = EzzioBrain(
        short_term_memory=MemoryGateway(),
        long_term_knowledge=KnowledgeStore(str(tmp_path / "brain_ezzio.db")),
        rss_cache=rss_cache
    )

    # Consolidation RSS -> Knowledge
    count = brain.consolidate_rss_to_knowledge(default_importance=0.6)
    assert count == 1

    # Traitement tâche complexe -> Doit router vers CLOUD_API et rappeler la connaissance
    complex_prompt = "Réalise une architecture complète et une synthèse d'optimisation cloud security refactor en Python."
    result = brain.process_task(complex_prompt, session_id="session_01")

    assert result["target"] == ExecutionTarget.CLOUD_API
    assert len(result["recalled_knowledge"]) > 0
    assert "Python" in result["recalled_knowledge"][0]["content"]
