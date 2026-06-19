import os

from dotenv import load_dotenv
from json_repair import repair_json
from ollama import Client
from pydantic import TypeAdapter, ValidationError

from app.domain.models import InputModel, Issue, IssuesResult

load_dotenv()

MODEL_NAME = os.getenv("MODEL_NAME", "qwen3.5:9b-q8_0")
THINK_ENABLED = os.getenv("THINK_ENABLED", "true").lower() == "true"
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", 120))
CONTEXT_WINDOW = int(os.getenv("CONTEXT_WINDOW", 16384))
OUTPUT_TOKENS = int(os.getenv("OUTPUT_TOKENS", 8192))
TEMPERATURE = float(os.getenv("TEMPERATURE", 0.6))
TOP_P = float(os.getenv("TOP_P", 0.95))
TOP_K = int(os.getenv("TOP_K", 20))


adapter = TypeAdapter(IssuesResult)
schema = adapter.json_schema()

client = Client(timeout=OLLAMA_TIMEOUT)

TEMPLATE_PROMPT = """
Analiza el siguiente código y retorna SOLO un objeto JSON con la clave "issues".
No incluyas texto antes ni después del JSON.

Archivo: {path}
Lenguaje: {lenguaje}
Imports detectados: {imports}
Funciones detectadas: {funciones}
Clases detectadas: {clases}

Contexto relacionado del proyecto (puede incluir fragmentos de OTRAS partes 
del archivo o de OTROS archivos, recuperados por similitud semántica).
Estos fragmentos son solo referencia de contexto general: pueden solaparse 
entre sí y NO debes usar su numeración de líneas para nada relacionado 
al bloque "Código" de abajo.
{rag}

Código a analizar:
El código viene con número de línea al inicio (N:).
Usa ÚNICAMENTE esta numeración (la del bloque "Código a analizar") para 
el campo line. Ignora cualquier número de línea mencionado en el contexto 
del proyecto de arriba: pertenece a otros fragmentos y puede no coincidir 
con este bloque.
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


def code_analyzer(
    input_model: InputModel, temperature: float = TEMPERATURE, _attempt: int = 0
) -> list[Issue]:

    prompt = TEMPLATE_PROMPT.format(
        path=input_model.file,
        lenguaje=input_model.language,
        imports=", ".join(input_model.imports),
        funciones=", ".join(
            [f"{f['name']}({', '.join(f['args'])})" for f in input_model.functions]
        ),
        clases=", ".join([f"{c['name']}({', '.join(c['bases'])})" for c in input_model.clases]),
        rag=_format_rag(input_model.rag),
        codigo=_format_code(input_model.code),
    )

    messages = [{"role": "user", "content": prompt}]

    response = client.chat(
        model=MODEL_NAME,
        messages=messages,
        think=THINK_ENABLED,
        format=schema,
        options={
            "temperature": temperature,
            "top_p": TOP_P,
            "top_k": TOP_K,
            "num_ctx": CONTEXT_WINDOW,
            "num_predict": OUTPUT_TOKENS,
        },
    )

    content = response.message.content or '{"issues": []}'

    try:
        result = adapter.validate_json(content)
        return result.issues
    except ValidationError:
        repaired = repair_json(content)

        try:
            result = adapter.validate_json(repaired)
            return result.issues
        except ValidationError as e:
            if _attempt < 1:
                return code_analyzer(input_model, _attempt=_attempt + 1)
            else:
                print(f"[PARSE FAILED] {e!r}\nContent: {content}")
                raise ValueError(f"No se pudo parsear la respuesta del modelo: {e}") from e


def _format_rag(chunks: list[dict[str, str | int | float]]) -> str:

    if not chunks:
        return "Sin contexto disponible."

    rag_formatted = ""

    for chunk in chunks:
        rag_formatted += (
            f"--- Fragmento de contexto (no autoritativo para numeración) "
            f"de {chunk['path']} "
            f"[rango aproximado original: {chunk['linea_inicio']}-{chunk['linea_fin']}, "
            f"relevancia {chunk['relevancia']}] ---\n"
        )
        rag_formatted += str(chunk["text"]) + "\n"

    return rag_formatted


def _format_code(code: str) -> str:
    return "\n".join(f"{i}: {line}" for i, line in enumerate(code.splitlines(), 1))
