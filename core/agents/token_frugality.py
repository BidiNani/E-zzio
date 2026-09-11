"""E-ZZIO — frugalité tokens : squelettes AST + élagage délibération.

Règle : jamais de fichier entier réémis — diffs unifiés uniquement.
"""
from __future__ import annotations

import ast
from typing import Any


def skeletonize_code(code: str) -> str:
    """AST : conserve signatures/types/docstrings, corps -> `...`."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        lines = code.splitlines()
        return "\n".join(l for l in lines if l.strip().startswith(("def ", "class ", "async def ", "@", '"""', "'''")) or not l.strip())[:4000]

    out: list[str] = []

    def _sig(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
        pos = list(node.args.args)
        defs = [ast.unparse(d) for d in node.args.defaults]
        no_def = len(pos) - len(defs)
        parts = []
        for i, a in enumerate(pos):
            s = a.arg
            if a.annotation:
                s += f": {ast.unparse(a.annotation)}"
            if i >= no_def:
                s += f"={defs[i - no_def]}"
            parts.append(s)
        if node.args.vararg:
            parts.append("*" + node.args.vararg.arg)
        if node.args.kwarg:
            parts.append("**" + node.args.kwarg.arg)
        ret = f" -> {ast.unparse(node.returns)}" if node.returns else ""
        kind = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
        doc = ast.get_docstring(node)
        head = f"{kind} {node.name}({', '.join(parts)}){ret}: ..."
        return f"{head}  # {doc.splitlines()[0][:80]}" if doc else head

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out.append(_sig(node))
        elif isinstance(node, ast.ClassDef):
            doc = ast.get_docstring(node)
            out.append(f"class {node.name}:  # {(doc or '').splitlines()[0][:80] if doc else ''}".rstrip())
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    out.append("    " + _sig(sub))
                elif isinstance(sub, ast.AnnAssign) and isinstance(sub.target, ast.Name):
                    ann = ast.unparse(sub.annotation) if sub.annotation else "?"
                    out.append(f"    {sub.target.id}: {ann}")
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            out.append(ast.unparse(node))
        elif isinstance(node, ast.Assign):
            tgt = ", ".join(ast.unparse(t) for t in node.targets)[:60]
            out.append(f"{tgt} = ...")
    return "\n".join(out)


def prune_deliberation_context(history: list) -> list:
    """Ne garde : énoncé initial + squelette minimal + diff du tour précédent."""
    if not history:
        return []
    pruned = [history[0]]
    skeletons = [h for h in history[1:] if isinstance(h, dict) and h.get("kind") == "skeleton"]
    if skeletons:
        pruned.append(skeletons[-1])
    diffs = [h for h in history[1:] if isinstance(h, dict) and h.get("kind") == "diff"]
    if diffs:
        pruned.append(diffs[-1])
    return pruned


def enforce_unified_diff(text: str) -> dict[str, Any]:
    """Valide qu'une contribution code est un diff unifié, pas un fichier entier."""
    has_hunk = "@@" in text and ("--- " in text or "+++ " in text or text.strip().startswith("@@"))
    return {"is_unified_diff": bool(has_hunk), "chars": len(text)}
