"""Archivo de prueba con bugs reales plantados.
Identificadores en español a propósito (NO son bugs)."""


def calcular_promedio(numeros):
    total = 0
    for numero in numeros:
        total += numero
    return total / len(numeros)


def guardar_opciones(opciones=[]):
    opciones.append("default")
    return opciones


def leer_archivo(ruta):
    archivo = open(ruta)
    contenido = archivo.read()
    return contenido


def dividir(dividendo, divisor):
    resultado = dividendo / divisor
    return resultdo


def contar_palabras(texto):
    palabras = texto.split(" ")
    return len(palabras) - 1


""
