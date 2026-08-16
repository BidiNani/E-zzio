import ast
from collections import deque
from pathlib import Path

root = Path(r"G:\AI\E-zzio")

entrypoints = [
    Path("web_server.py"),
    Path("routers/master.py"),
    Path("core/ezzio_master.py"),
    Path("core/dispatcher.py"),
    Path("core/llm_engine.py"),
]

def module_to_path(module_name: str):
    candidate = root / (module_name.replace(".", "/") + ".py")
    if candidate.exists():
        return candidate

    package_init = root / module_name.replace(".", "/") / "__init__.py"
    if package_init.exists():
        return package_init

    return None

def local_imports(file_path: Path):
    try:
        tree = ast.parse(file_path.read_text(encoding="utf-8-sig"))
    except SyntaxError as exc:
        return [], [f"SyntaxError line {exc.lineno}: {exc.msg}"]

    imports = []
    errors = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)

        elif isinstance(node, ast.ImportFrom):
            if node.level != 0:
                continue
            if node.module:
                imports.append(node.module)

    return imports, errors

queue = deque()
seen = set()
edges = []
errors = []

for entrypoint in entrypoints:
    full = root / entrypoint
    if full.exists():
        queue.append(full)
    else:
        errors.append(f"Entrypoint absent : {entrypoint}")

while queue:
    file_path = queue.popleft()
    relative = str(file_path.relative_to(root)).replace("\\", "/")

    if relative in seen:
        continue

    seen.add(relative)

    imports, parse_errors = local_imports(file_path)

    for error in parse_errors:
        errors.append(f"{relative}: {error}")

    for imported in imports:
        target = module_to_path(imported)
        if target is None:
            continue

        target_relative = str(target.relative_to(root)).replace("\\", "/")
        edges.append((relative, imported, target_relative))

        if target_relative not in seen:
            queue.append(target)

report = root / "runtime" / "audit" / "boot_path_map.md"
report.parent.mkdir(parents=True, exist_ok=True)

lines = [
    "# E-ZZIO — Carte du chemin de démarrage",
    "",
    "Analyse AST des imports locaux statiques depuis les entrypoints actifs.",
    "",
    "## Entrypoints",
    "",
]

for entrypoint in entrypoints:
    lines.append(f"- `{entrypoint.as_posix()}`")

lines.extend([
    "",
    f"## Modules locaux atteignables ({len(seen)})",
    "",
])

for item in sorted(seen):
    lines.append(f"- `{item}`")

lines.extend([
    "",
    f"## Arêtes d'import locales ({len(edges)})",
    "",
])

for source, imported, target in sorted(edges):
    lines.append(f"- `{source}` → `{imported}` → `{target}`")

lines.extend([
    "",
    "## Erreurs / limites",
    "",
])

if errors:
    lines.extend(f"- {error}" for error in errors)
else:
    lines.append("- Aucune erreur de parsing dans les modules analysés.")

report.write_text("\n".join(lines), encoding="utf-8")

print(f"Modules locaux atteignables : {len(seen)}")
print(f"Imports locaux cartographiés : {len(edges)}")
print(f"Rapport : {report}")
