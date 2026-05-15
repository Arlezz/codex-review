# from app.indexer import indexar
# import sys

# ruta = sys.argv[1] if len(sys.argv) > 1 else "."
# indexar(ruta)


from app.indexer import indexar

archivos = [
    "app/tools/leer_archivo.py",
    "app/tools/buscar_contexto.py",
    "app/tools/ejecutar_tests.py",
    "app/tools/guardar_reporte.py",
    "app/agente.py",
    "app/indexer.py",
]

for archivo in archivos:
    chunks = indexar(archivo)
    print(f"✓ {archivo} — {chunks} chunks")
