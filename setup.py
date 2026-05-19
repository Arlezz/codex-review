from pathlib import Path
from app.indexer import indexar

exclusiones = {"__pycache__", ".venv", ".git", "tests"}
archivos_excluidos = {"__init__.py", "setup.py"}

directorio_actual = Path(".")

for archivo in directorio_actual.rglob("*.py"):
    # filtro de exclusiones
    if any(parte in exclusiones for parte in archivo.parts):
        continue

    if archivo.name in archivos_excluidos:
        continue

    # llamar indexar
    chunks = indexar(str(archivo))

    # imprimir resultado
    print(f"✓ {archivo} — {chunks} chunks")
