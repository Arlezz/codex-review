from ollama import chat
from tools.leer_archivo import leer_archivo
from tools.buscar_contexto import buscar_contexto
from tools.ejecutar_tests import ejecutar_tests
from tools.guardar_reporte import guardar_reporte
from dotenv import load_dotenv
import os

load_dotenv()

MODEL_NAME = os.getenv("MODEL_NAME", "qwen2.5:7b")

SYSTEM_PROMPT = """
Eres un agente de code review experto.

ORDEN OBLIGATORIO — sigue estos pasos en secuencia:
PASO 1: llama leer_archivo para obtener el código
PASO 2: llama buscar_contexto con términos en inglés del código que leíste
PASO 3: analiza el código y genera los issues
PASO 4: llama guardar_reporte con los issues

CRITERIOS DE ANÁLISIS:
- Lee el código completo antes de generar issues
- Solo reporta problemas que realmente existen en el código
- No reportes como issue algo que ya está correctamente implementado
- Verifica cada issue contra el código antes de incluirlo

ESTRUCTURA DE CADA ISSUE:
{
    "titulo": string,
    "severidad": "critico" | "advertencia" | "sugerencia",
    "linea": number,
    "descripcion": string,
    "solucion": string
}

Sé específico con líneas y soluciones concretas.
No inventes issues que no existen en el código.
"""

tools = [leer_archivo, buscar_contexto, ejecutar_tests, guardar_reporte]
tools_map = {
    "leer_archivo": leer_archivo,
    "buscar_contexto": buscar_contexto,
    "ejecutar_tests": ejecutar_tests,
    "guardar_reporte": guardar_reporte,
}
messages = []
messages.append({"role": "system", "content": SYSTEM_PROMPT})


while True:
    user_input = input("Tu: ")
    messages.append({"role": "user", "content": user_input})

    while True:
        response = chat(model=MODEL_NAME, messages=messages, tools=tools)
        messages.append(response.message)

        if response.message.tool_calls:
            for tc in response.message.tool_calls:
                if tc.function.name in tools_map.keys():
                    tool_name = tc.function.name
                    tool_input = tc.function.arguments

                    try:
                        tool_output = tools_map[tool_name](**tool_input)
                        messages.append(
                            {
                                "role": "tool",
                                "tool_name": tool_name,
                                "content": str(tool_output),
                            }
                        )
                    except Exception as e:
                        messages.append(
                            {
                                "role": "tool",
                                "tool_name": tool_name,
                                "content": str(e),
                            }
                        )
                else:
                    messages.append(
                        {
                            "role": "tool",
                            "tool_name": tc.function.name,
                            "content": f"Tool {tc.function.name} no encontrada.",
                        }
                    )
        else:
            print(response.message.content)
            break
