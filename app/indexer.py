from sentence_transformers import SentenceTransformer
from pathlib import Path
from dotenv import load_dotenv
from chromadb import PersistentClient
import hashlib
import os

load_dotenv()

model = SentenceTransformer("all-MiniLM-L6-v2")
chroma = PersistentClient(path="./chroma_db")

CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION")


def chunk_texto(texto: str, chunk_size: int = 5, overlap: int = 2) -> list[str]:
    lineas = texto.splitlines()
    chunks = []
    i = 0

    while i < len(lineas):
        lineas_chunk = lineas[i : i + chunk_size]
        texto_chunk = "\n".join(lineas_chunk)
        chunks.append(texto_chunk)

        i += chunk_size - overlap

    return chunks


def indexar(path: str) -> int:
    content_file = Path(path).read_text(encoding="utf-8")

    chunk_size = 10
    overlap = 3

    chunks = chunk_texto(content_file, chunk_size, overlap)

    chunks_embeddings = model.encode(chunks)

    coleccion = chroma.get_or_create_collection(
        CHROMA_COLLECTION, metadata={"hnsw:space": "cosine"}
    )

    metadatas = []

    for i in range(len(chunks)):
        linea_inicio = i * (chunk_size - overlap) + 1
        metadatas.append(
            {
                "path": path,
                "linea_inicio": linea_inicio,
                "linea_fin": linea_inicio + chunk_size - 1,
            }
        )

    coleccion.add(
        ids=[
            hashlib.md5(f"{path}:chunks_{i}".encode()).hexdigest()
            for i in range(len(chunks))
        ],
        documents=chunks,
        embeddings=chunks_embeddings.tolist(),
        metadatas=metadatas,
    )

    return len(chunks)
