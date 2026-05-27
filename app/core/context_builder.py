import re
from pathlib import Path

EXTENSIONS = {
    ".py": "python",
    ".js": "javascript",
    ".mjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".go": "go",
    ".rs": "rust",
}


def get_language(path: Path):
    return EXTENSIONS.get(path.suffix.lower(), "unknown")


def extract(path: Path | str, content: str) -> dict:

    path = Path(path)
    language = get_language(path)

    extractor = _EXTRACTORS.get(language)

    return {
        "file": str(path),
        "language": language,
        **(extractor(content) if extractor else {}),
        "lines": len(content.splitlines()),
    }


def _py(code: str) -> dict:
    imports, functions, classes = [], [], []

    for m in re.finditer(r"^(?:import|from)\s+.+", code, re.M):
        imports.append(m.group().strip())

    for m in re.finditer(r"^(?:\s*)(?:async\s+)?def\s+(\w+)\s*\(([^)]*)\)", code, re.M):
        functions.append({"name": m.group(1), "args": _clean_args(m.group(2))})

    for m in re.finditer(r"^class\s+(\w+)(?:\(([^)]*)\))?", code, re.M):
        classes.append({"name": m.group(1), "bases": _split(m.group(2))})

    return {"imports": imports, "functions": functions, "classes": classes}


def _clean_args(raw: str) -> list[str]:
    return [a.strip() for a in raw.split(",") if a.strip()]


def _split(raw: str | None) -> list[str]:
    return [x.strip() for x in raw.split(",")] if raw else []


_EXTRACTORS = {
    "python": _py,
}
