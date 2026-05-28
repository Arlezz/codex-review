import os

from dotenv import load_dotenv
from ollama import chat

from app.domain.models import InputModel

load_dotenv()

MODEL_NAME = os.getenv("MODEL_NAME", "qwen2.5:7b")


TEMPLATE_PROMPT = """
Analiza el siguiente código y retorna SOLO un JSON array de issues.
No incluyas texto antes ni después del JSON.

Archivo: {path}
Lenguaje: {lenguaje}
Imports detectados: {imports}
Funciones detectadas: {funciones}
Clases detectadas: {clases}
Contexto relacionado del proyecto: {rag}

Código:
{codigo}

IMPORTANTE:
Antes de reportar un issue, verifica que el problema realmente esté presente en el código. 
No reportes como issue algo que ya está implementado correctamente.

Retorna SOLO esto:
[
    {{
        "titulo": "...", 
        "severidad": "critico | advertencia | sugerencia",
        "linea": N, 
        "descripcion": "...", 
        "solucion": "..."
    }}
]
"""


def code_analyzer(input_model: InputModel) -> str:

    prompt = TEMPLATE_PROMPT.format(
        path=input_model.file,
        lenguaje=input_model.language,
        imports=", ".join(input_model.imports),
        funciones=", ".join(
            [f"{f['name']}({', '.join(f['args'])})" for f in input_model.functions]
        ),
        clases=", ".join(
            [f"{c['name']}({', '.join(c['bases'])})" for c in input_model.clases]
        ),
        rag=_format_rag(input_model.rag),
        codigo=input_model.code,
    )

    messages = [{"role": "user", "content": prompt}]

    response = chat(
        model=MODEL_NAME,
        messages=messages,
    )

    return response.message.content


def _format_rag(chunks: list[dict[str, str | int | float]]) -> str:

    rag_formatted = ""

    if not chunks:
        return "Sin contexto disponible."

    for chunk in chunks:
        rag_formatted += f"--- {chunk['path']} (lineas {chunk['linea_inicio']} - {chunk['linea_fin']}, relevancia {chunk['relevancia']}) ---\n"
        rag_formatted += chunk["text"] + "\n"

    return rag_formatted
