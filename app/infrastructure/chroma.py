import os

from dotenv import load_dotenv

from app.infrastructure.embeddings import _get_chroma, _get_chroma_metadata, _get_model

load_dotenv()

RAG_MIN_RELEVANCE = float(os.getenv("RAG_MIN_RELEVANCE", 0.5))
RAG_MAX_CHUNKS = int(os.getenv("RAG_MAX_CHUNKS", 3))


def search_context(
    query: str, collection: str, n_resultados: int = 5, exclude_path: str | None = None
) -> list[dict]:

    model = _get_model()
    chroma = _get_chroma()

    query_embedding = model.encode(query).tolist()
    coleccion = chroma.get_or_create_collection(collection, metadata=_get_chroma_metadata())

    if coleccion.count() == 0:
        return []

    resultados = coleccion.query(
        query_embeddings=[query_embedding],
        n_results=min(n_resultados, coleccion.count()),
        include=["documents", "metadatas", "distances"],
    )

    documents = resultados.get("documents")
    if not documents or not documents[0]:
        return []

    metadatas = resultados.get("metadatas", [])
    distances = resultados.get("distances", [])

    chunks = []

    for i, doc in enumerate(documents[0]):
        meta = metadatas[0][i] if metadatas and metadatas[0] else {}
        distancia = distances[0][i] if distances and distances[0] else 0
        relevancia = round(1 - distancia, 3)

        if exclude_path and meta.get("path") == exclude_path:
            continue

        if relevancia < RAG_MIN_RELEVANCE:
            continue

        chunks.append(
            {
                "text": doc,
                "path": meta.get("path"),
                "linea_inicio": meta.get("linea_inicio"),
                "linea_fin": meta.get("linea_fin"),
                "relevancia": relevancia,
            }
        )

    chunks.sort(key=lambda c: c["relevancia"], reverse=True)
    return chunks[:RAG_MAX_CHUNKS]


def get_documents_count(collection: str) -> int:
    chroma = _get_chroma()
    if collection in [c.name for c in chroma.list_collections()]:
        return chroma.get_collection(collection).count()
    return 0


def reset_collection(collection: str) -> None:
    chroma = _get_chroma()
    if collection in [c.name for c in chroma.list_collections()]:
        chroma.delete_collection(collection)
