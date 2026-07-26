from typing import Dict, Any, List, Optional
from runtime.memory import MemoryGateway
from runtime.knowledge.store import KnowledgeStore
from runtime.knowledge.models import KnowledgeItem, SourceType
from runtime.rss.cache import RSSCacheStore
from runtime.rss.collector import RSSCollector
from runtime.cognition.analyzer import TaskAnalyzer, TaskAnalysis
from runtime.reasoning.router import CognitiveRouter, ExecutionTarget

class EzzioBrain:
    """
    Unified Cognitive Core orchestrating Short-Term Memory, Long-Term Knowledge,
    Perception (RSS), and Local-First Reasoning.
    """
    def __init__(
        self,
        short_term_memory: Optional[MemoryGateway] = None,
        long_term_knowledge: Optional[KnowledgeStore] = None,
        rss_cache: Optional[RSSCacheStore] = None,
        collector: Optional[RSSCollector] = None
    ):
        self.short_term = short_term_memory or MemoryGateway()
        self.long_term = long_term_knowledge or KnowledgeStore()
        self.rss_cache = rss_cache or RSSCacheStore()
        self.collector = collector or RSSCollector(self.rss_cache)
        self.analyzer = TaskAnalyzer()
        self.router = CognitiveRouter()

    def process_task(self, prompt: str, session_id: str = "default", capability_id: Optional[str] = None) -> Dict[str, Any]:
        analysis = self.analyzer.analyze(prompt)
        target = self.router.route(task_type="prompt_eval", complexity_score=analysis.complexity_score)

        cap_id = capability_id or "ezzio_core"
        token_meta = {"id": cap_id, "state": "ACTIVE"}

        self.short_term.write_memory(
            session_id=session_id,
            content={"prompt": prompt, "complexity": analysis.complexity_score, "target": str(target)},
            capability_id=cap_id,
            token_meta=token_meta
        )

        keywords = self.analyzer.extract_keywords(prompt)
        relevant_knowledge = self.long_term.search_knowledge_by_keywords(keywords)

        return {
            "analysis": analysis,
            "target": target,
            "keywords": keywords,
            "recalled_knowledge": relevant_knowledge
        }

    def remember_fact(self, content: str, category: str = "general", importance: float = 0.5, source_type: SourceType = SourceType.USER, source: str = "user"):
        item = KnowledgeItem(
            category=category,
            content=content,
            importance=importance,
            source_type=source_type,
            source=source
        )
        self.long_term.save_item(item)

    def perceive_world(self, feed_url: str) -> List[Dict[str, Any]]:
        return self.collector.fetch_and_parse(feed_url)

    def consolidate_rss_to_knowledge(self, default_importance: float = 0.4) -> int:
        articles = self.rss_cache.get_recent_articles(limit=20)
        consolidated = 0
        for art in articles:
            fact_content = f"Article [{art['title']}]: {art['summary']}"
            item = KnowledgeItem(
                id=f"rss_{art['guid'][:16]}",
                category="news_feed",
                content=fact_content,
                importance=default_importance,
                source_type=SourceType.RSS,
                source=art['link'] or "rss_feed"
            )
            self.long_term.save_item(item)
            consolidated += 1
        return consolidated
