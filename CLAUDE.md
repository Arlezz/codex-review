# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**codex-review** is a local code review agent powered by Ollama (Qwen model) and RAG (Retrieval Augmented Generation) via ChromaDB. It analyzes code files, finds contextual information using vector search, and generates markdown reports with issues classified by severity.

## Commands

### Running

```bash
# Interactive agent mode (chat-based review)
python app/agente.py

# CLI pipeline mode — analyze a single file or directory
python -m app.cli.main analyze <path>

# Index files into ChromaDB for RAG context
python setup.py
```

### Testing

```bash
# Run all tests
pytest tests/ -v

# Run a single test file
pytest tests/test_indexer.py -v
```

### Linting & Formatting

```bash
black app/        # Format
ruff check app/   # Lint
```

### Package Manager

This project uses `uv`. Install dependencies with:

```bash
uv pip install -r requirements.txt
# or
pip install -e .
```

## Architecture

The project has two operating modes sharing the same domain layer:

### Mode 1: Interactive Agent (`app/agente.py`)

Streams Ollama chat with tool-calling. The LLM orchestrates 4 tools in a mandatory order: `leer_archivo` → `buscar_contexto` → `ejecutar_tests` → `guardar_reporte`. Reports are saved to `reports/`.

### Mode 2: Pipeline / CLI (`app/cli/main.py`)

Deterministic batch processing. The pipeline calls each step explicitly:

```
File path
  → filesystem.read_file()          # app/infrastructure/filesystem.py
  → InputModel (code + RAG context) # app/domain/models.py
  → llm.code_analyzer()             # app/infrastructure/llm.py  (Ollama call)
  → validators.issues_validator()   # app/domain/validators.py   (JSON parse + validate)
  → markdown.save_report()          # app/reports/markdown.py
  → PipelineResult
```

### Key Layers

| Layer   | Path                               | Responsibility                                                                                 |
| ------- | ---------------------------------- | ---------------------------------------------------------------------------------------------- |
| CLI     | `app/cli/main.py`                  | Typer entry point, glues pipeline                                                              |
| Core    | `app/core/pipeline.py`             | Orchestrates analysis steps                                                                    |
| Core    | `app/core/discovery.py`            | Recursive file discovery with extension/dir filters                                            |
| Domain  | `app/domain/models.py`             | `FileContent`, `Issue`, `InputModel`, `PipelineResult` data classes                            |
| Domain  | `app/domain/validators.py`         | Parses LLM JSON; maps Spanish severity names (`critico`/`advertencia`/`sugerencia`) to English |
| Infra   | `app/infrastructure/llm.py`        | Ollama integration; returns JSON array of issues                                               |
| Infra   | `app/infrastructure/filesystem.py` | File reading with encoding detection                                                           |
| Reports | `app/reports/markdown.py`          | Markdown report with summary table, grouped by severity                                        |
| Indexer | `app/indexer.py`                   | Chunks code (10 lines, 3-line overlap), embeds with `all-MiniLM-L6-v2`, stores in ChromaDB     |
| Tools   | `app/tools/`                       | Agent tool implementations (file read, vector search, pytest runner, report saver)             |

### Configuration

Key values come from `.env`:

- `MODEL_NAME` — Ollama model (default `qwen3.5:9b`)
- `CHROMA_COLLECTION` — ChromaDB collection name
- `HF_TOKEN` — HuggingFace token for sentence-transformers

Generated artifacts (`chroma_db/`, `generated_reports/`) are gitignored.

## User Stories and Roadmap

See `docs/historias_usuario.md` for full HU details, acceptance criteria and current status.

## Current Status

V1 complete. Working on V2 — precision improvements.
Next HUs: HU-004, HU-007, HU-009.

## Core Principle

The LLM only reasons about code. It does not control the flow.
Python controls the entire pipeline.

## Working Style

- Explain the concept before implementing
- Guiding questions before giving complete code
- Validate understanding of what was implemented before moving on
