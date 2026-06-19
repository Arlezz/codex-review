import enum
import hashlib
from collections.abc import Callable
from pathlib import Path

from app.core.discovery import find_files
from app.infrastructure.embeddings import _get_chroma, _get_chroma_metadata, _get_model


def chunk_texto(texto: str, chunk_size: int = 10, overlap: int = 3) -> list[str]:
    lineas = texto.splitlines()
    chunks = []
    i = 0

    while i < len(lineas):
        lineas_chunk = lineas[i : i + chunk_size]
        texto_chunk = "\n".join(lineas_chunk)
        chunks.append(texto_chunk)

        i += chunk_size - overlap

    return chunks


def indexar(path: str, project_name: str) -> int:

    model = _get_model()
    chroma = _get_chroma()

    content_file = Path(path).read_text(encoding="utf-8")

    chunks = chunk_texto(content_file)

    chunks_embeddings = model.encode(chunks)

    coleccion = chroma.get_or_create_collection(project_name, metadata=_get_chroma_metadata())

    metadatas = []
    chunk_size = 10
    overlap = 3

    for i, chunk in enumerate(chunks):
        linea_inicio = i * (chunk_size - overlap) + 1
        num_lineas_chunk = len(chunk.splitlines())
        metadatas.append(
            {
                "path": path,
                "linea_inicio": linea_inicio,
                "linea_fin": linea_inicio + num_lineas_chunk - 1,
            }
        )

    coleccion.add(
        ids=[hashlib.md5(f"{path}:chunks_{i}".encode()).hexdigest() for i in range(len(chunks))],
        documents=chunks,
        embeddings=chunks_embeddings.tolist(),
        metadatas=metadatas,
    )

    return len(chunks)


def index_project(
    root: str, project_name: str, on_progress: Callable[[int, int, str], None] | None = None
) -> tuple[int, int]:
    files = find_files(root)
    total_files = len(files)

    total_chunks = 0

    if not files:
        return (0, 0)

    for i, file in enumerate(files, 1):
        chunks = indexar(str(file), project_name)
        total_chunks += chunks
        if on_progress:
            on_progress(i, total_files, file.name)

    return (total_files, total_chunks)
