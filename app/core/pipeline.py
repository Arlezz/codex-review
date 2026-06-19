from datetime import datetime
from pathlib import Path

from app.core.context_builder import extract_file_metadata, query_context
from app.domain.models import InputModel, PipelineResult
from app.domain.validators import issues_validator
from app.infrastructure.chroma import search_context
from app.infrastructure.filesystem import read_file
from app.infrastructure.llm import code_analyzer
from app.reports.markdown import save_report


def pipeline(file: Path, collection: str, output_dir: str | None = None) -> PipelineResult | None:

    print("Pipeline executed")

    file_content = read_file(str(file))

    if file_content.error:
        print(file_content.error)
        return

    if file_content.warning:
        print(file_content.warning)

    file_metadata = extract_file_metadata(file, file_content.content)
    query = query_context(file_metadata)

    context = search_context(query, collection) if query else []

    payload = InputModel(
        file=str(file),
        language=file_metadata["language"],
        imports=file_metadata.get("imports", []),
        functions=file_metadata.get("functions", []),
        clases=file_metadata.get("classes", []),
        rag=context,
        code=file_content.content,
    )

    issues = code_analyzer(payload)

    for i in issues:
        print(f"RAW line={i.line} title={i.title}")

    issues_validated = issues_validator(issues, total_lines=len(file_content.content.splitlines()))

    save_report(str(file), issues_validated, output_dir=output_dir, language=payload.language)

    return PipelineResult(
        file=str(file),
        issues=issues_validated,
        timestamp=datetime.now(),
        # meta={"issues": issues},
    )
