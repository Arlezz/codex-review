from dataclasses import dataclass
from datetime import datetime
from typing import Literal


@dataclass
class FileContent:
    content: str
    warning: str | None = None
    error: str | None = None


@dataclass
class Issue:
    title: str
    severity: Literal["critical", "warning", "suggestion"]
    description: str
    solution: str
    line: int = 0
    code_example: str = ""


@dataclass
class IssuesResult:
    issues: list[Issue]


@dataclass
class PipelineResult:
    file: str
    issues: list[Issue]
    timestamp: datetime
    meta: dict[str, str] | None = None


@dataclass
class InputModel:
    file: str
    language: str
    imports: list[str]
    functions: list[dict[str, list[str]]]
    clases: list[dict[str, list[str]]]
    rag: list[dict[str, str | int | float]]
    code: str
