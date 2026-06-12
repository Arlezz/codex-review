# codex-review

Pipeline local de code review impulsado por Qwen y RAG.
Analiza tu código, busca contexto relevante en el proyecto y genera reportes con issues clasificados por severidad. El backend determinístico controla el flujo; el LLM solo razona sobre el código.

## Stack

- **Modelo**: Qwen2.5:7b via Ollama (`think=False`)
- **Embeddings**: all-MiniLM-L6-v2 (sentence-transformers)
- **Vector store**: ChromaDB
- **CLI**: Typer
- **Tests**: pytest

## Uso

### 1. Indexar un proyecto (RAG)

```bash
python setup.py --path ruta/al/proyecto --project nombre_proyecto
```

### 2. Analizar un archivo o directorio

```bash
python -m app.cli.main analyze ruta --project nombre_proyecto
```

### 3. Correr los tests

```bash
python -m pytest tests/ -v
```

## Estructura

```
codex-review/
├── app/
│   ├── cli/main.py            # entry point CLI
│   ├── core/                  # pipeline, discovery, context_builder
│   ├── domain/                # models, validators
│   ├── infrastructure/        # filesystem, llm, chroma, embeddings
│   ├── reports/markdown.py    # generación de reportes
│   └── indexer.py             # chunking + embeddings → ChromaDB
├── tests/
├── setup.py                   # indexado RAG
└── .env
```
