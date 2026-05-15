def leer_archivo(file):
    try:
        with open(file, "r") as f:
            file_content = f.read()
            return {"content": file_content}
    except FileNotFoundError:
        return {"error": f"El archivo {file} no se encuentra en el directorio actual."}
    except PermissionError:
        return {"error": f"No tienes permiso para leer el archivo {file}."}
