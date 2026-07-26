import unittest
from runtime.memory.semantic.contracts import SemanticQuery, SemanticFilters, SemanticResultItem, SemanticQueryResult, SemanticSource, SemanticIntent, MemoryType

class TestSemanticContractsFinal(unittest.TestCase):
    def test_semantic_query_contract_version(self):
        """Vérifie la séparation propre du contract_version et des enums."""
        filters = SemanticFilters(memory_type=[MemoryType.EPISODE], confidence_min=0.8)
        query = SemanticQuery(
            query_id="qry_final_01",
            source=SemanticSource.AGENT,
            intent=SemanticIntent.REASON,
            text="Analyser l'historique des échecs d'exécution.",
            filters=filters,
            top_k=5
        )
        
        payload = query.to_dict()
        self.assertEqual(payload["source"], "agent")
        self.assertEqual(payload["intent"], "reason")
        self.assertEqual(payload["contract_version"], "1.0")

    def test_semantic_result_vector_spec(self):
        """Vérifie la présence de l'embedding_version, de la dimension et du content_hash."""
        item = SemanticResultItem(
            memory_id="ep_final_01",
            type=MemoryType.EPISODE,
            score=0.96,
            content="Résolution d'erreur d'encodage UTF-8 sous Windows.",
            embedding_version="2.0",
            embedding_dimension=768,
            content_hash="sha256_deadbeef",
            metadata={"retriever": "test"}
        )
        result = SemanticQueryResult(
            query_id="qry_final_01",
            results=[item],
            contract_version="1.0"
        )

        payload = result.to_dict()
        res_item = payload["results"][0]
        self.assertEqual(res_item["embedding_version"], "2.0")
        self.assertEqual(res_item["embedding_dimension"], 768)
        self.assertEqual(res_item["content_hash"], "sha256_deadbeef")
        print(f"\n[PHASE 8.0 GELÉE & VALIDÉE] Spécifications vectorielles et contrats validés : {res_item}")

if __name__ == "__main__":
    unittest.main()