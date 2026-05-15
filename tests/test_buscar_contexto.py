from app.tools.buscar_contexto import buscar_contexto
from app.indexer import indexar


def test_buscar_retorna_resultados():
    indexar("app/tools/leer_archivo.py")
    resultados = buscar_contexto("leer archivo")
    assert len(resultados) > 0


def test_buscar_tiene_metadatos():
    indexar("app/tools/leer_archivo.py")
    resultados = buscar_contexto("leer archivo")
    assert "path" in resultados[0]
    assert "relevancia" in resultados[0]
