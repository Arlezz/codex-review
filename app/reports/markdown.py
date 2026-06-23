from collections import Counter
from datetime import datetime
from pathlib import Path

from app.domain.models import Issue, PipelineResult
from app.reports.naming import SEVERITY_LABELS, SEVERITY_ORDER


def _render_issues(issues: list[Issue], fence_lang: str) -> list[str]:

    issues_render: list[str] = []

    for i, issue in enumerate(issues, 1):
        issues_render.append(f"## {i}. {issue.title} (línea {issue.line})")
        issues_render.append(
            f"**Severidad:** {SEVERITY_LABELS.get(issue.severity, issue.severity)}"
        )
        issues_render.append("")
        issues_render.append("**Descripción:**")
        issues_render.append(issue.description)
        issues_render.append("")
        issues_render.append("**Solución:**")
        issues_render.append(issue.solution)
        if issue.code_example:
            issues_render.append("")
            issues_render.append("**Ejemplo:**")
            issues_render.append(f"```{fence_lang}")
            issues_render.append(issue.code_example)
            issues_render.append("```")
        issues_render.append("---")
        issues_render.append("")

    return issues_render


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

    report_lines += _render_issues(sorted_issues, fence_lang)

    texto_markdown = "\n".join(report_lines)
    reporte.write_text(texto_markdown, encoding="utf-8")

    return {
        "path": str(reporte),
        "total_issues": len(issues),
    }


def save_consolidated_report(result: list[PipelineResult], output_dir=None) -> dict | None:
    pass
