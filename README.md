# codex-review

Agente local de code review impulsado por Qwen y RAG.
Analiza tu código, busca contexto relevante en el proyecto y genera reportes con issues clasificados por severidad.

## Stack

- **Modelo**: Qwen2.5:32b via Ollama
- **Embeddings**: all-MiniLM-L6-v2 (sentence-transformers)
- **Vector store**: ChromaDB
- **Tests**: pytest

## Uso

### 1. Indexar un archivo

```python
from app.indexer import indexar
indexar("ruta/al/archivo.py")
```

### 2. Correr el agente

```bash
python app/agente.py
```

### 3. Correr los tests

```bash
python -m pytest tests/ -v
```

## Estructura

```
codex-review/
├── app/
│   ├── agente.py
│   ├── indexer.py
│   └── tools/
├── tests/
├── reports/
└── .env
```
