from pathlib import Path

from app.domain.models import FileContent


def read_file(file: str, max_size: int = 500_000) -> FileContent:
    encodings = ("utf-8", "latin-1")

    try:
        file_path = Path(file)
        size_bytes = file_path.stat().st_size
        if size_bytes > max_size:
            with file_path.open("rb") as f:
                content = f.read(max_size)
            text = content.decode("utf-8", errors="ignore")
            return FileContent(
                content=text,
                warning=(
                    f"El archivo {file} excede el tamaño máximo permitido. "
                    "Se ha truncado a este tamaño para su lectura."
                ),
            )

        for encoding in encodings:
            try:
                content = file_path.read_text(encoding=encoding)
                return FileContent(content=content)
            except UnicodeDecodeError:
                continue

        return FileContent(
            content="",
            error=(
                f"El archivo {file} no se pudo decodificar "
                "con ninguno de los encodings probados."
            ),
        )
    except FileNotFoundError:
        return FileContent(
            content="",
            error=f"El archivo {file} no se encuentra en el directorio actual.",
        )
    except PermissionError:
        return FileContent(
            content="", error=f"No tienes permiso para leer el archivo {file}."
        )
    except Exception as e:
        return FileContent(
            content="", error=f"Error al leer el archivo {file}: {str(e)}"
        )
