import os

from dotenv import load_dotenv

from app.infrastructure.embeddings import _get_chroma, _get_model

load_dotenv()

CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "default")


def buscar_contexto(query: str, n_resultados: int = 5) -> list[dict]:

    chroma = _get_chroma()
    model = _get_model()

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

    documents = resultados["documents"]
    metadatas = resultados["metadatas"]
    distances = resultados["distances"]

    if documents is None or metadatas is None or distances is None:
        return []

    for i, doc in enumerate(documents[0]):
        meta = metadatas[0][i]
        distancia = distances[0][i]
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
