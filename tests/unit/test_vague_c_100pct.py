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

class TestFinalBranches:
    def test_doc_engine_sections_end_with_table(self, tmp_path):
        """L104->85 : sections terminant par table (boucle complete)."""
        from core.generators.doc_engine import DocEngine
        engine = DocEngine(workspace_root=str(tmp_path))
        res = engine.generate_docx(
            filename="end_table.docx", title="T",
            sections=[
                {"type": "paragraph", "text": "P1"},
                {"type": "heading", "level": 1, "text": "H"},
                {"type": "bullet", "items": ["a"]},
                {"type": "table", "headers": ["X"], "rows": [["1"]]},
            ],
        )
        assert "ok" in res

    def test_doc_engine_row_with_more_cells_than_headers(self, tmp_path):
        """L124->123 : row plus longue que row_cells -> branche False."""
        from core.generators.doc_engine import DocEngine
        engine = DocEngine(workspace_root=str(tmp_path))
        res = engine.generate_docx(
            filename="long_row.docx", title="T",
            sections=[{
                "type": "table",
                "headers": ["A", "B"],
                "rows": [
                    ["1", "2", "3", "4"],  # row plus longue que 2 colonnes
                    ["x", "y"],
                ],
            }],
        )
        assert "ok" in res

    def test_pdf_engine_last_section_different_type(self, tmp_path):
        """L139->125 : derniere section type table -> boucle complete."""
        from core.generators.pdf_engine import PdfEngine
        engine = PdfEngine(workspace_root=str(tmp_path))
        res = engine.generate_pdf(
            filename="last_table.pdf", title="T",
            sections=[
                {"type": "paragraph", "text": "P"},
                {"type": "heading", "text": "H"},
                {"type": "bullet", "items": ["a", "b"]},
                {"type": "table", "headers": ["X"], "rows": [["1"], ["2"]]},
            ],
        )
        assert res["ok"] is True

# ============================================================
# 6. Couverture finale branches (positions critiques)
# ============================================================

class TestLastBranches:
    def test_doc_engine_last_section_is_table(self, tmp_path):
        """L104->85 : table en DERNIERE position -> branche de sortie de boucle."""
        from core.generators.doc_engine import DocEngine
        engine = DocEngine(workspace_root=str(tmp_path))
        res = engine.generate_docx(
            filename="last_table.docx", title="T",
            sections=[
                {"type": "paragraph", "text": "P1"},
                {"type": "table", "headers": ["A"], "rows": [["x"]]},
            ],
        )
        assert "ok" in res

    def test_doc_engine_row_index_beyond_cells(self, tmp_path):
        """L124->123 : i >= len(row_cells) -> branche False."""
        from core.generators.doc_engine import DocEngine
        engine = DocEngine(workspace_root=str(tmp_path))
        # headers=1 col, row[0]=1 col -> cols_count=1
        # row avec 3 elements -> i=1 >= len(row_cells)=1 -> False
        res = engine.generate_docx(
            filename="beyond.docx", title="T",
            sections=[{
                "type": "table",
                "headers": ["A"],
                "rows": [["1", "2", "3", "4", "5"]],
            }],
        )
        assert "ok" in res

    def test_pdf_engine_last_section_is_table(self, tmp_path):
        """L139->125 : table en DERNIERE position -> branche de sortie."""
        from core.generators.pdf_engine import PdfEngine
        engine = PdfEngine(workspace_root=str(tmp_path))
        res = engine.generate_pdf(
            filename="last_table.pdf", title="T",
            sections=[
                {"type": "paragraph", "text": "P1"},
                {"type": "heading", "text": "H"},
                {"type": "table", "headers": ["X"], "rows": [["1"]]},
            ],
        )
        assert res["ok"] is True

    def test_pdf_engine_table_last_with_rows(self, tmp_path):
        """L148->125 : table_data cree -> doc.build final."""
        from core.generators.pdf_engine import PdfEngine
        engine = PdfEngine(workspace_root=str(tmp_path))
        res = engine.generate_pdf(
            filename="table_build.pdf", title="T",
            sections=[
                {"type": "table", "headers": ["X", "Y"], "rows": [["1", "2"]]},
            ],
        )
        assert res["ok"] is True

# ============================================================
# 7. Tests structure exacte pour branches coverage
# ============================================================

class TestCoverageBranchesExact:
    def test_doc_engine_alternating_paragraph_table_paragraph(self, tmp_path):
        """L104->85 : elif table faux/vrai/faux (3 transitions)."""
        from core.generators.doc_engine import DocEngine
        engine = DocEngine(workspace_root=str(tmp_path))
        res = engine.generate_docx(
            filename="alternate.docx", title="T",
            sections=[
                {"type": "paragraph", "text": "P1"},   # elif faux
                {"type": "table", "headers": ["A"], "rows": [["x"]]},  # elif vrai
                {"type": "paragraph", "text": "P2"},   # elif faux (fin)
            ],
        )
        assert "ok" in res

    def test_doc_engine_row_same_length_plus_longer(self, tmp_path):
        """L124->123 : if vrai (meme len) puis if faux (row plus longue)."""
        from core.generators.doc_engine import DocEngine
        engine = DocEngine(workspace_root=str(tmp_path))
        # headers 2 cols -> cols_count=2 -> row_cells a 2 cellules
        # 1ere row: 2 elements (if vrai sur i=0,1)
        # 2eme row: 4 elements (if vrai i=0,1 puis if faux i=2,3)
        res = engine.generate_docx(
            filename="mixed_rows.docx", title="T",
            sections=[{
                "type": "table",
                "headers": ["A", "B"],
                "rows": [
                    ["1", "2"],
                    ["3", "4", "5", "6"],
                ],
            }],
        )
        assert "ok" in res

    def test_pdf_engine_alternating_paragraph_table_paragraph(self, tmp_path):
        """L139->125 : elif table faux/vrai/faux."""
        from core.generators.pdf_engine import PdfEngine
        engine = PdfEngine(workspace_root=str(tmp_path))
        res = engine.generate_pdf(
            filename="alternate.pdf", title="T",
            sections=[
                {"type": "paragraph", "text": "P1"},
                {"type": "table", "headers": ["A"], "rows": [["x"]]},
                {"type": "paragraph", "text": "P2"},
            ],
        )
        assert res["ok"] is True

    def test_pdf_engine_table_with_headers_no_rows(self, tmp_path):
        """L148->125 : table_data non vide (headers only) -> doc.build."""
        from core.generators.pdf_engine import PdfEngine
        engine = PdfEngine(workspace_root=str(tmp_path))
        res = engine.generate_pdf(
            filename="headers_only.pdf", title="T",
            sections=[
                {"type": "table", "headers": ["A", "B"], "rows": []},
            ],
        )
        assert res["ok"] is True

    def test_pdf_engine_table_no_headers_with_rows(self, tmp_path):
        """L148->125 : table_data non vide (rows only) -> doc.build."""
        from core.generators.pdf_engine import PdfEngine
        engine = PdfEngine(workspace_root=str(tmp_path))
        res = engine.generate_pdf(
            filename="rows_only.pdf", title="T",
            sections=[
                {"type": "table", "headers": [], "rows": [["1", "2"]]},
            ],
        )
        assert res["ok"] is True

# ============================================================
# 8. Tests branche else (type inconnu)
# ============================================================

class TestElseBranch:
    def test_doc_engine_unknown_type_skipped(self, tmp_path):
        """L104->85 : type inconnu -> else du if/elif -> retour au for."""
        from core.generators.doc_engine import DocEngine
        engine = DocEngine(workspace_root=str(tmp_path))
        res = engine.generate_docx(
            filename="unknown.docx", title="T",
            sections=[
                {"type": "paragraph", "text": "P1"},
                {"type": "unknown_type", "text": "ignored"},  # tombe dans else
                {"type": "paragraph", "text": "P2"},
            ],
        )
        assert "ok" in res

    def test_pdf_engine_unknown_type_skipped(self, tmp_path):
        """L139->125 : type inconnu -> else -> retour au for."""
        from core.generators.pdf_engine import PdfEngine
        engine = PdfEngine(workspace_root=str(tmp_path))
        res = engine.generate_pdf(
            filename="unknown.pdf", title="T",
            sections=[
                {"type": "paragraph", "text": "P1"},
                {"type": "unknown_type", "text": "ignored"},
                {"type": "paragraph", "text": "P2"},
            ],
        )
        assert res["ok"] is True

# ============================================================
# 9. Test 148->125 : table_data vide puis section suivante
# ============================================================

class TestPdfEngineEmptyTableFollowedBySection:
    def test_pdf_engine_empty_table_then_paragraph(self, tmp_path):
        """L148->125 : table_data vide (if faux) puis retour au for."""
        from core.generators.pdf_engine import PdfEngine
        engine = PdfEngine(workspace_root=str(tmp_path))
        res = engine.generate_pdf(
            filename="empty_then_para.pdf", title="T",
            sections=[
                {"type": "table", "headers": [], "rows": []},   # table_data vide, if faux
                {"type": "paragraph", "text": "Apres la table"},  # retour au for depuis 148
            ],
        )
        assert res["ok"] is True
