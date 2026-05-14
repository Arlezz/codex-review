import subprocess
import sys


def ejecutar_tests(ruta_proyecto: str) -> dict:
    resultado = subprocess.run(
        [sys.executable, "-m", "pytest", "--tb=short", "-q"],
        capture_output=True,
        text=True,
        cwd=ruta_proyecto,
    )

    return {
        "exitoso": resultado.returncode == 0,
        "output": resultado.stdout,
        "resumen": [linea for linea in resultado.stdout.splitlines() if linea.strip()][
            -1
        ],
    }
