"""
Point d'entrée principal et CLI unifiée pour E-ZzIO.
"""

import sys
from pathlib import Path

# Ajouter src au PYTHONPATH
SRC_DIR = Path(__file__).resolve().parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import argparse
import asyncio
import logging

import uvicorn
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ezzio.config import settings
from ezzio.graph.workflow import app
from ezzio.rag.engine import get_rag_engine
from ezzio.self_repair.auto_healer import AutoHealer
from ezzio.self_repair.codebase_catalog import get_codebase_catalog
from ezzio.tools.file_tools import list_project_files, read_project_file, verify_python_syntax
from ezzio.tools.system_tools import check_ollama_health

console = Console()
logging.basicConfig(level=logging.WARNING)


async def cmd_run(query: str, thread_id: str = "cli_session"):
    console.print(Panel(f"[bold cyan]Requête utilisateur :[/bold cyan] {query}\n[bold dim]Thread ID : {thread_id}[/bold dim]", title="E-ZzIO Input"))

    initial_state = {
        "query": query,
        "thread_id": thread_id,
        "route": "direct",
        "answer": "",
        "sources": [],
        "model_used": "",
    }

    config = {"configurable": {"thread_id": thread_id}}

    with console.status("[bold green]Traitement asynchrone par le graphe E-ZzIO (SQLite WAL)..."):
        final_state = await app.ainvoke(initial_state, config=config)

    route = final_state.get("route", "unknown")
    model = final_state.get("model_used", "unknown")
    answer = final_state.get("answer", "")
    sources = final_state.get("sources", [])

    console.print(f"[bold magenta]Route choisie :[/bold magenta] {route.upper()}  |  [bold yellow]Modèle :[/bold yellow] {model}")
    console.print(Panel(answer, title="[bold green]Réponse E-ZzIO[/bold green]"))

    if sources:
        table = Table(title="Sources documentaires / Contexte")
        table.add_column("#", style="dim")
        table.add_column("Source / Fichier", style="cyan")
        for i, src in enumerate(sources, 1):
            meta = src.get("metadata", {})
            src_name = meta.get("path") or meta.get("source", "contexte")
            table.add_row(str(i), str(src_name))
        console.print(table)


def cmd_api(host: str = settings.api_host, port: int = settings.api_port):
    console.print(f"[bold cyan]Démarrage de la passerelle API E-ZzIO sur http://{host}:{port} ...[/bold cyan]")
    uvicorn.run("ezzio.api:app", host=host, port=port, reload=False)


def cmd_ingest():
    console.print("[bold cyan]Lancement de l'ingestion vectorielle du codebase E-ZzIO...[/bold cyan]")
    engine = get_rag_engine()
    count = engine.ingest_codebase()
    console.print(f"[bold green]✔ Ingestion terminée avec succès : {count} fragments indexés dans ChromaDB.[/bold green]")


def cmd_catalog():
    console.print("[bold cyan]Génération du catalogue universel d'auto-connaissance du codebase...[/bold cyan]")
    catalog = get_codebase_catalog()
    data = catalog.scan_all()

    table = Table(title=f"Catalogue E-ZzIO ({data['files_count']} fichiers cartographiés)")
    table.add_column("Type", style="bold")
    table.add_column("Fichier", style="cyan")
    table.add_column("Taille", justify="right")
    table.add_column("Classes / Fonctions / Symboles", style="green")

    for rel_path, info in list(data["files"].items())[:35]:
        sym_count = len(info.get("symbols", []))
        sym_sample = ", ".join(info.get("symbols", [])[:3])
        if sym_count > 3:
            sym_sample += f" (+{sym_count - 3})"
        table.add_row(
            info.get("type", "other"),
            rel_path,
            f"{info.get('size_bytes', 0):,} B",
            sym_sample or "-"
        )

    console.print(table)
    console.print(f"[bold green]✔ Catalogue complet sauvegardé dans {catalog.catalog_path}[/bold green]")


def cmd_heal():
    console.print("[bold cyan]Diagnostic et auto-guérison du codebase E-ZzIO...[/bold cyan]")
    healer = AutoHealer()
    report = healer.diagnose_all()

    table = Table(title="Rapport de Santé AST & Auto-Guérison")
    table.add_column("Métrique", style="bold")
    table.add_column("Valeur", style="bold")

    table.add_row("Total Fichiers Surveillés", str(report["total_files"]))
    table.add_row("Modules Python", str(report["python_modules"]))
    table.add_row(
        "Validité Syntaxique AST",
        f"[green]{report['syntax_valid_count']} / {report['python_modules']} (100% OK)[/green]"
        if report["healthy"] else f"[red]{len(report['syntax_errors'])} Erreur(s)[/red]"
    )

    console.print(table)

    if not report["healthy"]:
        console.print("[bold red]Erreurs détectées nécessitant réparation :[/bold red]")
        for err in report["syntax_errors"]:
            console.print(f"- [red]{err['file']}[/red] : {err['error']}")
    else:
        console.print("[bold green]✔ Tous les fichiers Python sont intègres et prêts à l'exécution.[/bold green]")


async def cmd_check():
    console.print("[bold cyan]Exécution du diagnostic de santé E-ZzIO...[/bold cyan]")

    # 1. Vérification Ollama
    health = await check_ollama_health()
    table = Table(title="Statut des Composants")
    table.add_column("Composant", style="bold")
    table.add_column("Statut", style="bold")
    table.add_column("Détails")

    table.add_row(
        "Serveur Ollama",
        "[green]OK[/green]" if health.ollama_ok else "[red]ERREUR[/red]",
        settings.ollama_url
    )

    table.add_row(
        "Modèles Requis",
        "[green]OK[/green]" if len(health.models_available) > 0 else "[yellow]VIDE[/yellow]",
        ", ".join(health.models_available[:5]) + ("..." if len(health.models_available) > 5 else "")
    )

    table.add_row(
        "Base Vectorielle ChromaDB",
        "[green]OK[/green]" if health.vectorstore_ok else "[yellow]NON CRÉÉE[/yellow]",
        str(settings.chroma_db_dir)
    )

    # 2. Vérification syntaxique des fichiers Python du projet
    files = list_project_files()
    py_files = [f for f in files if f.endswith(".py")]
    syntax_errors = []

    for pf in py_files:
        try:
            content = read_project_file(pf)
            is_valid, err = verify_python_syntax(content)
            if not is_valid:
                syntax_errors.append((pf, err))
        except Exception as exc:
            syntax_errors.append((pf, str(exc)))

    table.add_row(
        "Codebase Python (Syntaxe AST)",
        "[green]100% VALIDE[/green]" if not syntax_errors else f"[red]{len(syntax_errors)} ERREUR(S)[/red]",
        f"{len(py_files)} fichiers vérifiés"
    )

    console.print(table)


def cmd_files():
    files = list_project_files()
    console.print(f"[bold cyan]Fichiers surveillés par E-ZzIO ({len(files)} au total) :[/bold cyan]")
    for f in files:
        console.print(f"  • {f}")


def main():
    parser = argparse.ArgumentParser(description="E-ZzIO Autonomous AI Orchestrator")
    subparsers = parser.add_subparsers(dest="command", help="Commande à exécuter")

    # Run
    run_parser = subparsers.add_parser("run", help="Poser une question ou demander une tâche à E-ZzIO")
    run_parser.add_argument("query", type=str, help="Requête / Prompt pour E-ZzIO")
    run_parser.add_argument("--thread-id", type=str, default="cli_session", help="ID de la session conversationnelle")

    # API
    api_parser = subparsers.add_parser("api", help="Démarrer le serveur API FastAPI (REST + SSE)")
    api_parser.add_argument("--host", type=str, default=settings.api_host, help="Hôte d'écoute")
    api_parser.add_argument("--port", type=int, default=settings.api_port, help="Port d'écoute")

    # Ingest
    subparsers.add_parser("ingest", help="Ingérer et indexer le codebase dans ChromaDB")

    # Catalog
    subparsers.add_parser("catalog", help="Construire le catalogue d'auto-connaissance du codebase")

    # Heal
    subparsers.add_parser("heal", help="Diagnostiquer et auto-guérir le codebase")

    # Check
    subparsers.add_parser("check", help="Lancer un diagnostic de santé et vérifier la syntaxe")

    # Files
    subparsers.add_parser("files", help="Lister tous les fichiers du projet")

    args = parser.parse_args()

    if args.command == "run":
        asyncio.run(cmd_run(args.query, thread_id=args.thread_id))
    elif args.command == "api":
        cmd_api(host=args.host, port=args.port)
    elif args.command == "ingest":
        cmd_ingest()
    elif args.command == "catalog":
        cmd_catalog()
    elif args.command == "heal":
        cmd_heal()
    elif args.command == "check":
        asyncio.run(cmd_check())
    elif args.command == "files":
        cmd_files()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
