import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)

from app.core.discovery import find_files
from app.core.pipeline import pipeline
from app.domain.models import PipelineResult
from app.indexer import index_project
from app.infrastructure.chroma import get_documents_count, reset_collection
from app.reports.json_report import save_json_report
from app.reports.markdown import save_report

console = Console()
app = typer.Typer()


@app.callback()
def main():
    """Code review agent"""
    pass


def make_progress_bar() -> Progress:
    return Progress(
        TextColumn("[progress.description]{task.description}"),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        BarColumn(),
        MofNCompleteColumn(),
        TextColumn("•"),
        TimeElapsedColumn(),
        TextColumn("•"),
        TimeRemainingColumn(),
    )


def _ensure_indexed(project: str, root: Path, reindex: bool) -> None:

    files = find_files(str(root))
    files_count = len(files)

    if files_count == 0:
        typer.echo(f"No se encontraron archivos en {root}")
        raise typer.Exit(code=1)

    if not reindex and get_documents_count(project) > 0:
        print("Proyecto ya indexado, saltando indexación...")
        return

    if reindex:
        reset_collection(project)

    if files_count > 1:
        with make_progress_bar() as progress:
            task = progress.add_task("Indexando...", total=None)

            def callback(actual, total, nombre):
                progress.update(
                    task, completed=actual, total=total, description=f"Indexando... {nombre}"
                )

            result = index_project(
                str(root),
                project,
                on_progress=callback,
            )

        print(f"Indexado completo - {result[0]} archivos, {result[1]} chunks")
        return

    print("Indexando archivo...")
    result = index_project(str(root), project, on_progress=None)
    print(f"Indexado completo - {result[0]} archivos, {result[1]} chunks")
    return


def emit(result: PipelineResult, stdout: bool, output_dir: str):

    severity_colors = {
        "critical": "red",
        "warning": "yellow",
        "suggestion": "cyan",
    }

    if not stdout:
        language = result.meta["language"] if result.meta else "unknown"
        save_report(result.file, result.issues, output_dir, language)
        save_json_report(result.file, result.issues, output_dir)
        return

    console.print(f"\n[bold]{result.file}[/bold]")
    if not result.issues:
        console.print("[green]Sin issues detectados.[/green]")
        return

    for issue in result.issues:
        color = severity_colors.get(issue.severity, "white")
        console.print(f"[{color}]{issue.severity}[/{color}] línea {issue.line}: {issue.title}")
        console.print(issue.description)
        console.print("")


@app.command()
def analyze(
    path: str = typer.Argument(..., help="Ruta al proyecto o al archivo"),
    project: str = typer.Option(..., "--project", help="Nombre del proyecto"),
    reindex: bool = typer.Option(
        False, "--reindex", help="Reindexar el proyecto antes de analizar"
    ),
    output: str = typer.Option(None, "--output", help="Directorio de salida de reportes"),
    stdout: bool = typer.Option(
        False, "--stdout", help="Salida por consola, no guardar en archivos"
    ),
):

    if output and stdout:
        typer.echo("La opción --output no puede ser usada con --stdout")
        raise typer.Exit(code=1)

    file_path = Path(path)

    if not file_path.exists():
        typer.echo(f"El archivo o directorio {path} no existe")
        raise typer.Exit(code=1)

    typer.echo(f"Analizando proyecto: {project}")

    project_root = file_path if file_path.is_dir() else file_path.parent

    start = time.perf_counter()

    _ensure_indexed(project, project_root, reindex)

    failed: list[tuple[Path, str]] = []

    output_dir = (
        output
        if output
        else f"generated_reports/{file_path.name}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
    )

    results: list[PipelineResult] = []

    if file_path.is_file():
        try:
            result = pipeline(file_path, project)
            if result:
                results.append(result)
            else:
                failed.append((file_path, "Sin resultados, no se pudo analizar."))
        except Exception as e:
            failed.append((file_path, str(e)))

    elif file_path.is_dir():
        files = find_files(path)
        print(f"Archivos encontrados: {len(files)}")
        with make_progress_bar() as progress:
            task = progress.add_task("Analizando archivos", total=len(files))
            for file in files:
                progress.console.print(f"Analizando: {file}")
                try:
                    result = pipeline(file, project)
                    if result:
                        results.append(result)
                    else:
                        failed.append((file, "Sin resultados, no se pudo analizar."))
                except Exception as e:
                    failed.append((file, str(e)))
                finally:
                    progress.update(task, advance=1)

    for r in results:
        emit(r, stdout, output_dir)

    issues_result = {r.file: Counter(issue.severity for issue in r.issues) for r in results}

    totals = sum(issues_result.values(), Counter())

    print("\nAnálisis completo.")
    print(f"Total de archivos analizados: {len(results)}")
    print("\nResumen de problemas encontrados:")
    for severity, count in totals.items():
        print(f"  {severity.capitalize()}: {count}")

    top = sorted(issues_result.items(), key=lambda kv: sum(kv[1].values()), reverse=True)
    print("\nArchivos con más issues:")
    for file, counter in top:
        if sum(counter.values()) == 0:
            continue
        print(f"  {file}: {sum(counter.values())}")

    if failed:
        print("\nErrores encontrados:")
        for file, error in failed:
            print(f"  {file}: {error}")

    print(f"\nTiempo total: {time.perf_counter() - start:.2f}s")

    if totals.get("critical", 0) > 0 or failed:
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    app()
