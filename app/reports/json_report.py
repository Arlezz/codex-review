import json
from dataclasses import asdict
from pathlib import Path

from app.domain.models import Issue
from app.reports.naming import SEVERITY_LABELS, SEVERITY_ORDER


def save_json_report(file: str, issues: list[Issue], output_dir: str | None = None) -> dict:

    output_dir = output_dir or "generated_reports"
    file_path = Path(file)
    reporte = Path(output_dir) / f"reporte_{file_path.name}.json"
    reporte.parent.mkdir(parents=True, exist_ok=True)

    sorted_issues = sorted(issues, key=lambda issue: SEVERITY_ORDER.get(issue.severity, 99))

    issues_json = [asdict(issue) for issue in sorted_issues]

    summary = {
        severity: sum(1 for issue in issues if issue.severity == severity)
        for severity in SEVERITY_LABELS
    }

    output = {
        "file": file,
        "summary": summary,
        "issues": issues_json,
    }

    reporte.write_text(json.dumps(output, indent=4), encoding="utf-8")

    return {
        "path": str(reporte),
        "total_issues": len(issues),
    }
