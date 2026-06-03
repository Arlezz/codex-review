from collections import Counter
from datetime import datetime
from pathlib import Path

from app.domain.models import Issue


def save_report(
    archivo_revisado: str, issues: list[Issue], output_dir: str | None = None
) -> dict:

    if output_dir is None:
        output_dir = "generated_reports"

    file_path = Path(archivo_revisado)

    reporte = Path(f"{output_dir}/reporte_{file_path.name}.md")
    reporte.parent.mkdir(parents=True, exist_ok=True)

    report_lines = []

    report_lines.append(f"# Code Review — {archivo_revisado}")
    report_lines.append(f"**Total de issues detectados:** {len(issues)}")
    report_lines.append(
        f"**Fecha del reporte:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    report_lines.append("")

    severity_order = {"critical": 0, "warning": 1, "suggestion": 2}

    sorted_issues = sorted(
        issues, key=lambda issue: severity_order.get(issue.severity, 99)
    )

    conteos = Counter(issue.severity for issue in issues)

    report_lines.append("## Resumen:")
    report_lines.append("| Severidad | Total |")
    report_lines.append("|-------------|-------|")
    report_lines.append(f"| Crítico | {conteos['critical']} |")
    report_lines.append(f"| Advertencia | {conteos['warning']} |")
    report_lines.append(f"| Sugerencia | {conteos['suggestion']} |")
    report_lines.append("")

    for i, issue in enumerate(sorted_issues, 1):
        report_lines.append(f"## {i}. {issue.title} (línea {issue.line})")
        report_lines.append(f"**Severidad:** {issue.severity}")
        report_lines.append("")
        report_lines.append("**Descripcion:**")
        report_lines.append(issue.description)
        report_lines.append("")
        report_lines.append("**Solucion:**")
        report_lines.append(issue.solution)
        report_lines.append("---")
        report_lines.append("")

    texto_markdown = "\n".join(report_lines)

    reporte.write_text(texto_markdown, encoding="utf-8")

    return {
        "path": str(reporte),
        "total_issues": len(issues),
    }
