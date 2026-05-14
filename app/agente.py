from ollama import chat
from tools.leer_archivo import leer_archivo
from tools.buscar_contexto import buscar_contexto
from tools.ejecutar_tests import ejecutar_tests
from tools.guardar_reporte import guardar_reporte

SYSTEM_PROMPT = """
Eres un agente de code review experto .

ORDEN OBLIGATORIO — sigue estos pasos en secuencia:
PASO 1: llama leer_archivo para obtener el código
PASO 2: llama buscar_contexto con términos del código que leíste
PASO 3: analiza y genera los issues
PASO 4: llama guardar_reporte con los issues

Cuando el usuario pida revisar un archivo tienes que utilizar las siguientes herramientas:
1. Lee el archivo con 'leer_archivo'
2. Busca el contexto relevante con 'buscar_contexto'
3. Analiza el código y genera una lista de issues siguiendo la siguiente estructura:
    {
        "titulo": string,
        "severidad": string,
        "linea": number,
        "descripcion": string,
        "solucion": string
    }
4. Guarda el reporte con 'guardar_reporte'

Se especifico con lineas y soluciones concretas
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
        response = chat(model="qwen2.5:32b", messages=messages, tools=tools)
        messages.append(response.message)

        if response.message.tool_calls:
            for tc in response.message.tool_calls:
                if tc.function.name in tools_map.keys():
                    tool_name = tc.function.name
                    tool_input = tc.function.arguments
                    tool_output = tools_map[tool_name](**tool_input)
                    messages.append(
                        {
                            "role": "tool",
                            "tool_name": tool_name,
                            "content": str(tool_output),
                        }
                    )
        else:
            print(response.message.content)
            break
