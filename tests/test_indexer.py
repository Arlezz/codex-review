from app.indexer import indexar


def test_indexar_archivo():
    resultado = indexar("app/infrastructure/filesystem.py", "test_project")
    assert resultado > 0
