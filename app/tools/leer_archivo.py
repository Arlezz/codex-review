def leer_archivo(file):
    try:
        with open(file) as f:
            return {"content": f.read()}
    except FileNotFoundError:
        return {"error": f"El archivo {file} no se encuentra en el directorio actual."}
    except PermissionError:
        return {"error": f"No tienes permiso para leer el archivo {file}."}
    except Exception as e:
        return {"error": f"Error al leer el archivo {file}: {str(e)}"}
