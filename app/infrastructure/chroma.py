import os

from chromadb import PersistentClient
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

load_dotenv()

_model = None
_chroma = None


def _get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def _get_chroma():
    global _chroma
    if _chroma is None:
        _chroma = PersistentClient(path="./chroma_db")
    return _chroma


CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "default")


def search_context(query: str, n_resultados: int = 5) -> list[dict]:

    model = _get_model()
    chroma = _get_chroma()

    query_embedding = model.encode(query).tolist()
    coleccion = chroma.get_or_create_collection(
        CHROMA_COLLECTION, metadata={"hnsw:space": "cosine"}
    )

    if coleccion.count() == 0:
        return []

    resultados = coleccion.query(
        query_embeddings=[query_embedding],
        n_results=min(n_resultados, coleccion.count()),
        include=["documents", "metadatas", "distances"],
    )

    chunks = []

    for i, doc in enumerate(resultados["documents"][0]):
        meta = resultados["metadatas"][0][i]
        distancia = resultados["distances"][0][i]
        chunks.append(
            {
                "text": doc,
                "path": meta["path"],
                "linea_inicio": meta["linea_inicio"],
                "linea_fin": meta["linea_fin"],
                "relevancia": round(1 - distancia, 3),
            }
        )

    return chunks
