import sys
from datetime import datetime
from pathlib import Path

import typer
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
from app.indexer import index_project
from app.infrastructure.chroma import get_documents_count, reset_collection

app = typer.Typer()


@app.callback()
def main():
    """Code review agent"""
    pass


progress_bar = Progress(
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
        with progress_bar as progress:
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


@app.command()
def analyze(
    path: str = typer.Argument(..., help="Ruta al proyecto o al archivo"),
    project: str = typer.Option(..., "--project", help="Nombre del proyecto"),
    reindex: bool = typer.Option(
        False, "--reindex", help="Reindexar el proyecto antes de analizar"
    ),
):
    file_path = Path(path)

    if not file_path.exists():
        typer.echo(f"El archivo o directorio {path} no existe")
        raise typer.Exit(code=1)

    typer.echo(f"Analizando proyecto: {project}")

    project_root = file_path if file_path.is_dir() else file_path.parent

    _ensure_indexed(project, project_root, reindex)

    failed: list[tuple[Path, str]] = []
    issues_result = {}

    if file_path.is_file():
        try:
            result = pipeline(file_path, project)
            if result:
                for issue in result.issues:
                    issues_result.setdefault(issue.severity, 0)
                    issues_result[issue.severity] += 1
            else:
                failed.append((file_path, "Sin resultados, no se pudo analizar."))
        except Exception as e:
            failed.append((file_path, str(e)))

    elif file_path.is_dir():
        files = find_files(path)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_dir = f"generated_reports/{file_path.name}_{timestamp}"
        print(f"Archivos encontrados: {len(files)}")
        with typer.progressbar(files, label="Analizando archivos") as progress:
            for file in progress:
                print(f"Analizando: {file}")

                try:
                    result = pipeline(
                        file,
                        project,
                        output_dir=output_dir,
                    )
                    if result:
                        for issue in result.issues:
                            issues_result.setdefault(issue.severity, 0)
                            issues_result[issue.severity] += 1
                    else:
                        failed.append((file, "Sin resultados, no se pudo analizar."))
                except Exception as e:
                    failed.append((file, str(e)))

    print("\nAnálisis completo.")
    if file_path.is_dir():
        print(f"Total de archivos analizados: {len(files) - len(failed)}")
        print("\nResumen de problemas encontrados:")
        for severity, count in issues_result.items():
            print(f"  {severity.capitalize()}: {count}")

    if failed:
        print("\nErrores encontrados:")
        for file, error in failed:
            print(f"  {file}: {error}")

    if issues_result.get("critical", 0) > 0 or failed:
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    app()
