import pathlib


def guardar_reporte(archivo_revisado: str, issues: list[dict[str, str]]) -> dict:

    reporte = pathlib.Path(f"reports/reporte_{archivo_revisado}.md")
    reporte.parent.mkdir(parents=True, exist_ok=True)

    lineas = []

    lineas.append(f"# Code Review — {archivo_revisado}")
    lineas.append("")

    for i, issue in enumerate(issues, 1):
        lineas.append(f"## {i}. {issue['titulo']} (línea {issue['linea']})")
        lineas.append(f"**Severidad:** {issue['severidad']}")
        lineas.append("")
        lineas.append("**Descripcion:**")
        lineas.append(issue["descripcion"])
        lineas.append("")
        lineas.append("**Solucion:**")
        lineas.append(issue["solucion"])
        lineas.append("---")
        lineas.append("")

    texto_markdown = "\n".join(lineas)

    reporte.write_text(texto_markdown, encoding="utf-8")

    return {
        "path": str(reporte),
        "total_issues": len(issues),
    }
