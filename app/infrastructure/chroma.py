from app.infrastructure.embeddings import _get_chroma, _get_model


def search_context(query: str, collection: str, n_resultados: int = 5) -> list[dict]:

    model = _get_model()
    chroma = _get_chroma()

    query_embedding = model.encode(query).tolist()
    coleccion = chroma.get_or_create_collection(collection, metadata={"hnsw:space": "cosine"})

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
        chunks.append(
            {
                "text": doc,
                "path": meta.get("path"),
                "linea_inicio": meta.get("linea_inicio"),
                "linea_fin": meta.get("linea_fin"),
                "relevancia": round(1 - distancia, 3),
            }
        )

    return chunks
