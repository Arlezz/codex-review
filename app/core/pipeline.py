from app.domain.models import InputModel, PipelineResult
from app.infrastructure.filesystem import read_file
from app.infrastructure.llm import code_analyzer
from app.domain.validators import issues_validator
from app.reports.markdown import save_report
from pathlib import Path
from datetime import datetime


def pipeline(file: Path, output_dir: str | None = None) -> PipelineResult | None:

    print("Pipeline executed")

    file_content = read_file(str(file))

    if file_content.error:
        print(file_content.error)
        return

    if file_content.warning:
        print(file_content.warning)

    payload = InputModel(
        file=file,
        language="python",
        imports=[],
        functions=[],
        rag="",
        code=file_content.content,
    )

    issues_raw = code_analyzer(payload)

    issues = issues_validator(
        issues_raw, total_lines=len(file_content.content.splitlines())
    )

    save_report(str(file), issues, output_dir=output_dir)

    return PipelineResult(
        file=str(file),
        issues=issues,
        timestamp=datetime.now(),
        # meta={"issues": issues},
    )
