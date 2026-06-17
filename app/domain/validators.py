from app.domain.models import Issue


def _strip_code_fence(text: str) -> str:
    text = text.strip()

    if not text:
        return text

    text_lines = text.splitlines()

    if text_lines[0].startswith("```"):
        text_lines = text_lines[1:]

    if text_lines and text_lines[-1].startswith("```"):
        text_lines = text_lines[:-1]

    return "\n".join(text_lines)


def issues_validator(issues: list[Issue], total_lines: int) -> list[Issue]:
    unique: list[Issue] = []
    seen: set[tuple[int, str]] = set()

    for issue in issues:
        if issue.line > total_lines or issue.line < 0:
            issue.line = 0

        issue.code_example = _strip_code_fence(issue.code_example)

        key = (issue.line, issue.title)
        if key not in seen:
            seen.add(key)
            unique.append(issue)

    return unique
