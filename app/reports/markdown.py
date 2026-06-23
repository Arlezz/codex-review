from collections import Counter
from datetime import datetime
from pathlib import Path

from app.domain.models import Issue
from app.reports.naming import SEVERITY_LABELS, SEVERITY_ORDER


def save_report(
    archivo_revisado: str,
    issues: list[Issue],
    output_dir: str | None = None,
    language: str = "unknown",
) -> dict:

    output_dir = output_dir or "generated_reports"
    file_path = Path(archivo_revisado)
    reporte = Path(output_dir) / f"reporte_{file_path.name}.md"
    reporte.parent.mkdir(parents=True, exist_ok=True)

    sorted_issues = sorted(issues, key=lambda issue: SEVERITY_ORDER.get(issue.severity, 99))
    conteos = Counter(issue.severity for issue in issues)
    fence_lang = "" if language == "unknown" else language

    report_lines = [
        f"# Code Review — {archivo_revisado}",
        f"**Total de issues detectados:** {len(issues)}",
        f"**Fecha del reporte:** {datetime.now():%Y-%m-%d %H:%M:%S}",
        "",
        "## Resumen",
        "| Severidad | Total |",
        "|-----------|-------|",
    ]
    for severity, label in SEVERITY_LABELS.items():
        report_lines.append(f"| {label} | {conteos.get(severity, 0)} |")
    report_lines.append("")

    for i, issue in enumerate(sorted_issues, 1):
        report_lines.append(f"## {i}. {issue.title} (línea {issue.line})")
        report_lines.append(f"**Severidad:** {SEVERITY_LABELS.get(issue.severity, issue.severity)}")
        report_lines.append("")
        report_lines.append("**Descripción:**")
        report_lines.append(issue.description)
        report_lines.append("")
        report_lines.append("**Solución:**")
        report_lines.append(issue.solution)
        if issue.code_example:
            report_lines.append("")
            report_lines.append("**Ejemplo:**")
            report_lines.append(f"```{fence_lang}")
            report_lines.append(issue.code_example)
            report_lines.append("```")
        report_lines.append("---")
        report_lines.append("")

    texto_markdown = "\n".join(report_lines)
    reporte.write_text(texto_markdown, encoding="utf-8")

    return {
        "path": str(reporte),
        "total_issues": len(issues),
    }
