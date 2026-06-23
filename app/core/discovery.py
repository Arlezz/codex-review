from pathlib import Path


def find_files(
    path: str,
    path_to_ignore: set[str] | None = None,
    file_to_ignore: set[str] | None = None,
    extensions: set[str] | None = None,
) -> list[Path]:

    if path_to_ignore is None:
        path_to_ignore = {
            "__pycache__",
            ".venv",
            ".git",
            "tests",
            "node_modules",
        }

    if file_to_ignore is None:
        file_to_ignore = {"__init__.py", "setup.py"}

    if extensions is None:
        extensions = {".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs"}

    try:
        ruta = Path(path)
        archivos_encontrados: list[Path] = []

        for archivo in ruta.rglob("*"):
            if not archivo.is_file():
                continue

            if any(parte in path_to_ignore for parte in archivo.parts):
                continue

            if not any(archivo.suffix == extension for extension in extensions):
                continue

            if archivo.name in file_to_ignore:
                continue

            if archivo.stat().st_size == 0:
                continue

            archivos_encontrados.append(archivo)

        return sorted(archivos_encontrados)

    except Exception as e:
        print(f"Error al descubrir archivos: {e}")
        return []
