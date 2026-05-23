import json
from app.domain.models import Issue


def issues_validator(issues_raw: str, total_lines: int) -> list[Issue]:

    try:
        parsed_data = json.loads(issues_raw)

        if not isinstance(parsed_data, list):
            print("Error: El JSON de issues no es una lista.")
            return []

        issues: list[Issue] = []

        severity_levels = {
            "critico": "critical",
            "advertencia": "warning",
            "sugerencia": "suggestion",
        }

        for issue in parsed_data:
            if not isinstance(issue, dict):
                print("Error: Cada issue debe ser un diccionario.")
                return []

            try:
                line = int(issue.get("linea", 0))
            except Exception:
                print(
                    f"Advertencia: Línea no válida para el issue '{issue.get('titulo', '')}'. Se asignará línea 0."
                )
                line = 0

            issues.append(
                Issue(
                    title=issue.get("titulo", ""),
                    severity=severity_levels.get(
                        issue.get("severidad", "sugerencia").lower(), "suggestion"
                    ),
                    description=issue.get("descripcion", ""),
                    solution=issue.get("solucion", ""),
                    line=line if line <= total_lines else 0,
                )
            )

        return issues

    except json.JSONDecodeError:
        print("Error: No se pudo parsear el JSON de issues.")
        return []
