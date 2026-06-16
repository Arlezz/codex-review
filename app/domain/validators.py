from app.domain.models import Issue


def issues_validator(issues: list[Issue], total_lines: int) -> list[Issue]:
    unique: list[Issue] = []
    seen: set[tuple[int, str]] = set()

    for issue in issues:
        if issue.line > total_lines or issue.line < 0:
            issue.line = 0
        key = (issue.line, issue.title)
        if key not in seen:
            seen.add(key)
            unique.append(issue)

    return unique
