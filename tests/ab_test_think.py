"""
Test A/B: think=True vs think=False para code_analyzer.

Corre el mismo análisis N veces con cada modo y compara:
- Si llegó a producir contenido (content vacío = fallo de razonamiento)
- Tiempo de respuesta
- Tokens de thinking generados (si aplica)
- Si el JSON resultante es parseable
- Cantidad de issues encontrados

Uso:
    python ab_test_think.py path/al/archivo.py

Requiere las mismas variables de entorno que tu app (MODEL_NAME, etc.)
"""

import json
import os
import sys
import time
from dataclasses import dataclass

from dotenv import load_dotenv
from json_repair import repair_json
from ollama import Client

load_dotenv()

MODEL_NAME = os.getenv("MODEL_NAME", "qwen3.5:9b-q8_0")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", 180))  # un poco mas alto para el test
CONTEXT_WINDOW = int(os.getenv("CONTEXT_WINDOW", 16384))
OUTPUT_TOKENS = int(os.getenv("OUTPUT_TOKENS", 8192))
TEMPERATURE = float(os.getenv("TEMPERATURE", 0.6))
TOP_P = float(os.getenv("TOP_P", 0.95))
TOP_K = int(os.getenv("TOP_K", 20))

N_RUNS = int(os.getenv("AB_TEST_RUNS", 3))  # corridas por modo

client = Client(timeout=OLLAMA_TIMEOUT)

# Prompt minimo, sin RAG, para aislar la variable que nos interesa (think on/off)
SIMPLE_PROMPT = """
Analiza el siguiente código y retorna SOLO un objeto JSON con la clave "issues".
No incluyas texto antes ni después del JSON.

Archivo: {path}

Código a analizar:
El código viene con número de línea al inicio (N:).
Usa ÚNICAMENTE esta numeración para el campo line.
El N: es referencia, no parte del código.
{codigo}

IMPORTANTE:
- Antes de reportar un issue, verifica que el problema realmente esté presente en el código.
- No reportes como issue algo que ya está implementado correctamente.
- Si no encuentras ningún problema, retorna {{"issues": []}}.
- En code_example incluye únicamente el código, sin envolverlo en bloques markdown
ni usar comillas triples (```)

Retorna SOLO esto:
{{
    "issues": [
        {{
            "title": "...",
            "severity": "critical | warning | suggestion",
            "line": N,
            "description": "...",
            "solution": "...",
            "code_example": "..."
        }}
    ]
}}
"""


def _format_code(code: str) -> str:
    return "\n".join(f"{i}: {line}" for i, line in enumerate(code.splitlines(), 1))


@dataclass
class RunResult:
    mode: str
    run_idx: int
    elapsed_seconds: float = 0.0
    thinking_chars: int = 0
    content_chars: int = 0
    content_empty: bool = False
    json_valid: bool = False
    issues_count: int = 0
    error: str | None = None
    raw_content: str = ""


def run_once(path: str, codigo: str, think: bool, run_idx: int) -> RunResult:
    mode = "think=True" if think else "think=False"
    result = RunResult(mode=mode, run_idx=run_idx)

    prompt = SIMPLE_PROMPT.format(path=path, codigo=_format_code(codigo))
    messages = [{"role": "user", "content": prompt}]

    start = time.monotonic()
    try:
        response = client.chat(
            model=MODEL_NAME,
            messages=messages,
            think=think,
            options={
                "temperature": TEMPERATURE,
                "top_p": TOP_P,
                "top_k": TOP_K,
                "num_ctx": CONTEXT_WINDOW,
                "num_predict": OUTPUT_TOKENS,
            },
        )
    except Exception as e:  # noqa: BLE001 - queremos capturar cualquier fallo del test
        result.elapsed_seconds = time.monotonic() - start
        result.error = repr(e)
        return result

    result.elapsed_seconds = time.monotonic() - start

    thinking = getattr(response.message, "thinking", None) or ""
    content = response.message.content or ""

    result.thinking_chars = len(thinking)
    result.content_chars = len(content)
    result.content_empty = len(content.strip()) == 0
    result.raw_content = content

    if not result.content_empty:
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            try:
                parsed = json.loads(repair_json(content))
            except Exception:
                parsed = None

        if parsed is not None and "issues" in parsed:
            result.json_valid = True
            result.issues_count = len(parsed["issues"])

    return result


def print_summary(results: list[RunResult]) -> None:
    print("\n" + "=" * 70)
    print("RESUMEN")
    print("=" * 70)

    for mode in ("think=True", "think=False"):
        mode_results = [r for r in results if r.mode == mode]
        if not mode_results:
            continue

        print(f"\n--- {mode} ({len(mode_results)} corridas) ---")
        for r in mode_results:
            status = (
                "ERROR"
                if r.error
                else (
                    "VACIO" if r.content_empty else ("JSON_OK" if r.json_valid else "JSON_INVALIDO")
                )
            )
            print(
                f"  run {r.run_idx}: {status:14s} "
                f"tiempo={r.elapsed_seconds:6.1f}s "
                f"thinking_chars={r.thinking_chars:6d} "
                f"content_chars={r.content_chars:6d} "
                f"issues={r.issues_count}"
            )
            if r.error:
                print(f"           error: {r.error}")

        n_vacios = sum(1 for r in mode_results if r.content_empty and not r.error)
        n_errores = sum(1 for r in mode_results if r.error)
        n_ok = sum(1 for r in mode_results if r.json_valid)
        avg_time = sum(r.elapsed_seconds for r in mode_results) / len(mode_results)
        avg_thinking = sum(r.thinking_chars for r in mode_results) / len(mode_results)

        print(
            f"  -> OK: {n_ok}/{len(mode_results)} | VACIO: {n_vacios}/{len(mode_results)} | ERROR: {n_errores}/{len(mode_results)}"
        )
        print(
            f"  -> tiempo promedio: {avg_time:.1f}s | thinking promedio: {avg_thinking:.0f} chars"
        )


def main() -> None:
    if len(sys.argv) < 2:
        print("Uso: python ab_test_think.py path/al/archivo.py")
        sys.exit(1)

    path = sys.argv[1]
    with open(path, encoding="utf-8") as f:
        codigo = f.read()

    print(f"Modelo: {MODEL_NAME}")
    print(f"Archivo: {path} ({len(codigo.splitlines())} lineas)")
    print(f"Corridas por modo: {N_RUNS}")
    print(f"OUTPUT_TOKENS: {OUTPUT_TOKENS}")
    print()

    results: list[RunResult] = []

    for run_idx in range(1, N_RUNS + 1):
        print(f"[think=True]  corrida {run_idx}/{N_RUNS}...", flush=True)
        r = run_once(path, codigo, think=True, run_idx=run_idx)
        results.append(r)
        print(f"  -> {'VACIO' if r.content_empty else 'OK'} en {r.elapsed_seconds:.1f}s")

    for run_idx in range(1, N_RUNS + 1):
        print(f"[think=False] corrida {run_idx}/{N_RUNS}...", flush=True)
        r = run_once(path, codigo, think=False, run_idx=run_idx)
        results.append(r)
        print(f"  -> {'VACIO' if r.content_empty else 'OK'} en {r.elapsed_seconds:.1f}s")

    print_summary(results)

    # Guardar detalle completo para inspeccion manual
    out_path = "ab_test_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(
            [
                {
                    "mode": r.mode,
                    "run_idx": r.run_idx,
                    "elapsed_seconds": r.elapsed_seconds,
                    "thinking_chars": r.thinking_chars,
                    "content_chars": r.content_chars,
                    "content_empty": r.content_empty,
                    "json_valid": r.json_valid,
                    "issues_count": r.issues_count,
                    "error": r.error,
                    "raw_content": r.raw_content,
                }
                for r in results
            ],
            f,
            indent=2,
            ensure_ascii=False,
        )
    print(f"\nDetalle completo guardado en: {out_path}")


if __name__ == "__main__":
    main()
