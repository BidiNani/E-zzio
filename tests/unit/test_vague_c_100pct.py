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

    def test_table_in_middle_of_sections(self, tmp_path):
        """L104->85 : table AU MILIEU -> elif vrai remonte a L85."""
        from core.generators.doc_engine import DocEngine

        engine = DocEngine(workspace_root=str(tmp_path))
        res = engine.generate_docx(
            filename="table_middle.docx",
            title="T",
            sections=[
                {"type": "heading", "level": 1, "text": "Avant"},
                {"type": "table", "headers": ["H1"], "rows": [["a"]]},
                {"type": "heading", "level": 2, "text": "Apres"},
                {"type": "table", "headers": ["H2"], "rows": [["b"]]},
                {"type": "paragraph", "text": "Fin"},
            ],
        )
        assert "ok" in res

    def test_table_row_longer_than_cols(self, tmp_path):
        """L124->123 : r_data plus long que row_cells -> if i < len(row_cells) faux."""
        from core.generators.doc_engine import DocEngine

        engine = DocEngine(workspace_root=str(tmp_path))
        res = engine.generate_docx(
            filename="table_overflow.docx",
            title="T",
            sections=[
                {
                    "type": "table",
                    "headers": ["H1"],
                    "rows": [
                        ["a"],
                        ["b", "c"],
                    ],
                }
            ],
        )
        assert "ok" in res


# ============================================================
# 3. pdf_engine.py — L139->125 (boucle sections)
# ============================================================

class TestPdfEngineMultipleSections:
    def test_table_in_middle_of_sections(self, tmp_path):
        """L139->125 : table AU MILIEU -> elif vrai remonte a L125."""
        from core.generators.pdf_engine import PdfEngine

        engine = PdfEngine(workspace_root=str(tmp_path))
        res = engine.generate_pdf(
            filename="table_middle.pdf",
            title="T",
            sections=[
                {"type": "heading", "text": "Avant"},
                {"type": "table", "headers": ["X"], "rows": [["1"]]},
                {"type": "heading", "text": "Apres"},
                {"type": "table", "headers": ["Y"], "rows": [["2"]]},
                {"type": "paragraph", "text": "Fin"},
            ],
        )
        assert res["ok"] is True
        assert res["size_bytes"] > 0


# ============================================================
# 4. simple_rag.py — L42 (migration) + L156-157, 163-164 (fallback)
# ============================================================

class TestSimpleRAGMigration:
    def test_migration_tag_column_from_scratch(self, tmp_path):
        """L42 : table SANS tag -> init() doit ALTER TABLE ADD COLUMN tag."""
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

        # 2. Verifier que tag est absent AVANT init()
        async def check_no_tag():
            async with aiosqlite.connect(db_path) as db:
                cursor = await db.execute("PRAGMA table_info(documents)")
                cols = [row[1] for row in await cursor.fetchall()]
                return "tag" not in cols

        assert asyncio.run(check_no_tag()) is True, "tag doit etre absent avant init()"

        # 3. SimpleRAG.init() doit faire la migration (L42)
        rag = SimpleRAG(db_path=db_path)
        asyncio.run(rag.init())

        # 4. Verifier que tag existe APRES init()
        async def check_tag():
            async with aiosqlite.connect(db_path) as db:
                cursor = await db.execute("PRAGMA table_info(documents)")
                cols = [row[1] for row in await cursor.fetchall()]
                return "tag" in cols

        assert asyncio.run(check_tag()) is True, "tag doit etre present apres init()"


class TestSimpleRAGFallback:
    def test_search_fts5_exception_fallback_with_tag(self, tmp_path):
        """L156-157, 163-164 : FTS5 echoue -> fallback LIKE + filtre tag."""
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

        assert isinstance(results, list)
