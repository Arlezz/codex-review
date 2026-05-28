import argparse
from pathlib import Path

from app.indexer import indexar

parser = argparse.ArgumentParser()

parser.add_argument("--path", required=True)
parser.add_argument("--project", required=True)

args = parser.parse_args()

project_path = Path(args.path)
project_name = args.project

if not project_path.exists():
    raise Exception(f"El proyecto {project_path} no existe")

exclusiones = {"__pycache__", ".venv", ".git", "tests"}
archivos_excluidos = {"__init__.py", "setup.py"}


for archivo in project_path.rglob("*.py"):
    # filtro de exclusiones
    if any(parte in exclusiones for parte in archivo.parts):
        continue

    if archivo.name in archivos_excluidos:
        continue

    # llamar indexar
    chunks = indexar(str(archivo), project_name)

    # imprimir resultado
    print(f"✓ {archivo} — {chunks} chunks")
