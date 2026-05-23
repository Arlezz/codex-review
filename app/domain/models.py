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
    functions: list[str]
    rag: str
    code: str
