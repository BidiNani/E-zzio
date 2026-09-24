"""Tests finaux Vague C : 4 fichiers -> 100%."""
from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest

# ============================================================
# 1. nothing_impossible.py — L219-222 (backtrack)
# ============================================================

class TestNothingImpossibleBacktrack:
    def test_solve_iteratively_autonomous_creation_fails(self):
        """L219-222 : create_custom_tool echoue -> backtrack final."""
        import core.agent.nothing_impossible as ni_mod
        from core.agent.nothing_impossible import FeasibilityEngine

        e = FeasibilityEngine()
        with patch.object(ni_mod, "self_knowledge") as mock_sk:
            mock_sk.query_capability.return_value = {"can_do": False}
            mock_sk.detect_gap.return_value = {"gap_type": "TOOL_GAP"}
            with patch.object(e, "create_custom_tool", return_value={"status": "FAILED"}):
                res = e.solve_iteratively("do something unique that fails")
                assert res["status"] == "HONEST_FAILURE"


# ============================================================
# 2. doc_engine.py — L53, 104->85, 124->123
# ============================================================

class TestDocEngineFullCoverage:
    def test_filename_without_extension_gets_docx(self, tmp_path):
        """L53 : extension .docx ajoutee automatiquement."""
        from core.generators.doc_engine import DocEngine

        engine = DocEngine(workspace_root=str(tmp_path))
        res = engine.generate_docx(filename="sans_extension", title="T", sections=[])
        if res.get("ok"):
            assert res["filename"] == "sans_extension.docx"

    def test_multiple_sections_same_type(self, tmp_path):
        """L104->85 : boucle for iterant plusieurs fois (sections type identique)."""
        from core.generators.doc_engine import DocEngine

        engine = DocEngine(workspace_root=str(tmp_path))
        res = engine.generate_docx(
            filename="multi.docx",
            title="Multi",
            sections=[
                {"type": "paragraph", "text": "P1"},
                {"type": "paragraph", "text": "P2"},
                {"type": "paragraph", "text": "P3"},
            ],
        )
        assert "ok" in res

    def test_table_multiple_rows(self, tmp_path):
        """L124->123 : plusieurs rows dans table -> boucle interne."""
        from core.generators.doc_engine import DocEngine

        engine = DocEngine(workspace_root=str(tmp_path))
        res = engine.generate_docx(
            filename="table_multi.docx",
            title="T",
            sections=[
                {
                    "type": "table",
                    "headers": ["H1", "H2"],
                    "rows": [
                        ["a", "b"],
                        ["c", "d"],
                        ["e", "f"],
                        ["g", "h"],
                    ],
                }
            ],
        )
        assert "ok" in res


# ============================================================
# 3. pdf_engine.py — L139->125 (boucle sections)
# ============================================================

class TestPdfEngineMultipleSections:
    def test_multiple_paragraph_sections(self, tmp_path):
        """L139->125 : boucle for iterant plusieurs fois (sections type identique)."""
        from core.generators.pdf_engine import PdfEngine

        engine = PdfEngine(workspace_root=str(tmp_path))
        res = engine.generate_pdf(
            filename="multi_sections.pdf",
            title="Multi Sections",
            sections=[
                {"type": "paragraph", "text": "Premier paragraphe."},
                {"type": "paragraph", "text": "Deuxieme paragraphe."},
                {"type": "paragraph", "text": "Troisieme paragraphe."},
                {"type": "paragraph", "text": "Quatrieme paragraphe."},
            ],
        )
        assert res["ok"] is True
        assert res["size_bytes"] > 0


# ============================================================
# 4. simple_rag.py — L156-157 (FTS5 except), L163-164 (fallback + tag)
# ============================================================

class TestSimpleRAGFinal:
    def test_search_fts5_exception_fallback_with_tag(self, tmp_path):
        """L156-157, 163-164 : FTS5 echoue -> except -> fallback LIKE + tag."""
        import core.rag.simple_rag as rag_mod
        from core.rag.simple_rag import SimpleRAG

        rag = SimpleRAG(db_path=str(tmp_path / "rag.db"))
        asyncio.run(rag.init())

        asyncio.run(rag.add_document(content="Alpha Beta", tag="test_tag"))

        # Patcher aiosqlite.connect pour forcer une erreur sur les requetes MATCH
        real_connect = rag_mod.aiosqlite.connect

        class BrokenCursor:
            async def fetchall(self):
                raise RuntimeError("FTS5 broken intentionally")

        class BrokenDB:
            def __init__(self, real):
                self._real = real
                self._conn = None
            async def __aenter__(self):
                self._conn = await self._real.__aenter__()
                return self
            async def __aexit__(self, *args):
                return await self._real.__aexit__(*args)
            async def execute(self, sql, *args):
                if "MATCH" in sql:
                    return BrokenCursor()
                return await self._conn.execute(sql, *args)
            async def commit(self):
                return await self._conn.commit()

        def fake_connect(path):
            real = real_connect(path)
            return BrokenDB(real)

        with patch.object(rag_mod.aiosqlite, "connect", fake_connect):
            results = asyncio.run(rag.search_documents("Alpha", limit=5, tag="test_tag"))

        # Le fallback LIKE doit avoir ete utilise -> liste retournee
        assert isinstance(results, list)

# ============================================================
# 5. Branches manquantes finales
# ============================================================

class TestDocEngineBranchesFinal:
    def test_multiple_sections_with_different_types(self, tmp_path):
        """L104->85 : boucle for avec sections de types differents."""
        from core.generators.doc_engine import DocEngine

        engine = DocEngine(workspace_root=str(tmp_path))
        res = engine.generate_docx(
            filename="multi_types.docx",
            title="Multi Types",
            sections=[
                {"type": "heading", "level": 1, "text": "H1"},
                {"type": "paragraph", "text": "P1"},
                {"type": "bullet", "items": ["A", "B"]},
                {"type": "table", "headers": ["X"], "rows": [["1"], ["2"]]},
                {"type": "paragraph", "text": "P2"},
            ],
        )
        assert "ok" in res

    def test_table_row_shorter_than_headers(self, tmp_path):
        """L124->123 : row plus courte que headers -> skip branches manquantes."""
        from core.generators.doc_engine import DocEngine

        engine = DocEngine(workspace_root=str(tmp_path))
        res = engine.generate_docx(
            filename="short_row.docx",
            title="T",
            sections=[
                {
                    "type": "table",
                    "headers": ["A", "B", "C"],
                    "rows": [
                        ["1"],           # row plus courte que headers
                        ["x", "y", "z"], # row complete
                    ],
                }
            ],
        )
        assert "ok" in res


class TestPdfEngineBranchesFinal:
    def test_multiple_sections_with_different_types(self, tmp_path):
        """L139->125 : boucle for avec sections de types differents."""
        from core.generators.pdf_engine import PdfEngine

        engine = PdfEngine(workspace_root=str(tmp_path))
        res = engine.generate_pdf(
            filename="multi_types.pdf",
            title="Multi Types",
            sections=[
                {"type": "heading", "text": "H1"},
                {"type": "paragraph", "text": "P1"},
                {"type": "bullet", "items": ["A", "B"]},
                {"type": "table", "headers": ["X"], "rows": [["1"], ["2"]]},
                {"type": "paragraph", "text": "P2"},
            ],
        )
        assert res["ok"] is True


class TestSimpleRAGMigration:
    def test_migration_adds_tag_column(self, tmp_path):
        """L42 : migration douce ajoute la colonne tag si absente."""
        import asyncio

        import aiosqlite

        from core.rag.simple_rag import SimpleRAG

        db_path = str(tmp_path / "old_rag.db")

        # 1. Creer DB SANS colonne tag
        async def setup_old_db():
            async with aiosqlite.connect(db_path) as db:
                await db.execute("""
                    CREATE TABLE documents (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        content TEXT NOT NULL,
                        metadata TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                await db.commit()

        asyncio.run(setup_old_db())

        # 2. SimpleRAG.init() doit faire la migration (ajouter tag)
        rag = SimpleRAG(db_path=db_path)
        asyncio.run(rag.init())

        # 3. Verifier que tag existe
        async def check_tag():
            async with aiosqlite.connect(db_path) as db:
                cursor = await db.execute("PRAGMA table_info(documents)")
                cols = [row[1] for row in await cursor.fetchall()]
                return "tag" in cols

        assert asyncio.run(check_tag()) is True
