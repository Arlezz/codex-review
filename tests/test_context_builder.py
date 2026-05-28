from pathlib import Path
from app.core.context_builder import get_language, extract_file_metadata, query_context

SAMPLE_PY = """\
import os
from pathlib import Path

class MyClass(Path):
    pass

def my_func(a, b):
    return a + b

async def async_func(x):
    pass
"""


def test_get_language_python():
    assert get_language(Path("app/core/pipeline.py")) == "python"


def test_get_language_javascript():
    assert get_language(Path("index.js")) == "javascript"


def test_get_language_unknown():
    assert get_language(Path("file.xyz")) == "unknown"


def test_extract_detecta_imports():
    meta = extract_file_metadata("file.py", SAMPLE_PY)
    assert "import os" in meta["imports"]
    assert "from pathlib import Path" in meta["imports"]


def test_extract_detecta_funciones():
    meta = extract_file_metadata("file.py", SAMPLE_PY)
    nombres = [f["name"] for f in meta["functions"]]
    assert "my_func" in nombres
    assert "async_func" in nombres


def test_extract_detecta_clases():
    meta = extract_file_metadata("file.py", SAMPLE_PY)
    nombres = [c["name"] for c in meta["classes"]]
    assert "MyClass" in nombres


def test_extract_cuenta_lineas():
    meta = extract_file_metadata("file.py", SAMPLE_PY)
    assert meta["lines"] == len(SAMPLE_PY.splitlines())


def test_extract_lenguaje_no_soportado_no_crashea():
    meta = extract_file_metadata("file.go", SAMPLE_PY)
    assert meta["language"] == "go"
    assert "imports" not in meta


def test_query_context_retorna_string():
    meta = extract_file_metadata("file.py", SAMPLE_PY)
    query = query_context(meta)
    assert query is not None
    assert "my_func" in query
    assert "import os" in query


def test_query_context_retorna_none_sin_metadata():
    meta = {"language": "go", "file": "file.go", "lines": 5}
    assert query_context(meta) is None
