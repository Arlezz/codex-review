import sys
from datetime import datetime
from pathlib import Path

import typer

from app.core.discovery import find_files
from app.core.pipeline import pipeline

app = typer.Typer()


@app.command()
def analyze(path: str):

    file_path = Path(path)

    issues_result = {}

    if file_path.is_file():
        result = pipeline(file_path)
        if result:
            for issue in result.issues:
                issues_result.setdefault(issue.severity, 0)
                issues_result[issue.severity] += 1

    elif file_path.is_dir():
        files = find_files(path)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_dir = f"generated_reports/{file_path.name}_{timestamp}"
        print(f"Archivos encontrados: {len(files)}")
        with typer.progressbar(files, label="Analizando archivos") as progress:
            for file in progress:
                print(f"Analizando: {file}")
                result = pipeline(
                    file,
                    output_dir=output_dir,
                )
                if result:
                    for issue in result.issues:
                        issues_result.setdefault(issue.severity, 0)
                        issues_result[issue.severity] += 1

    print("\nAnálisis completo.")
    if file_path.is_dir():
        print(f"Total de archivos analizados: {len(files)}")
        print("\nResumen de problemas encontrados:")
        for severity, count in issues_result.items():
            print(f"  {severity.capitalize()}: {count}")

    if issues_result.get("critical", 0) > 0:
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    app()
