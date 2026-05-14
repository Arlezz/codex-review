from app.indexer import indexar


def test_indexar_archivo():
    resultado = indexar("app/tools/leer_archivo.py")
    assert resultado > 0  # debe indexar al menos un chunk
