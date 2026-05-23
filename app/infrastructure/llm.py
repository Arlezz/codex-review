from ollama import chat
from app.domain.models import InputModel
from dotenv import load_dotenv
import os

load_dotenv()

MODEL_NAME = os.getenv("MODEL_NAME", "qwen2.5:7b")


TEMPLATE_PROMPT = """
Analiza el siguiente código y retorna SOLO un JSON array de issues.
No incluyas texto antes ni después del JSON.

Archivo: {path}
Lenguaje: {lenguaje}
Imports detectados: {imports}
Funciones detectadas: {funciones}
Contexto relacionado del proyecto: {rag}

Código:
{codigo}

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
        funciones=", ".join(input_model.functions),
        rag=input_model.rag,
        codigo=input_model.code,
    )

    messages = [{"role": "user", "content": prompt}]

    response = chat(
        model=MODEL_NAME,
        messages=messages,
    )

    return response.message.content
