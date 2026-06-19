# Historias de Usuario — Codex Reviewer v2

## Descripción General

Codex Reviewer es un pipeline determinístico de revisión automática de código fuente.
El sistema controla el flujo completo — el LLM solo actúa como motor de razonamiento
para detectar issues. No hay agente conversacional en el núcleo del sistema.

### Principio arquitectural clave

```
Backend determinístico → controla el flujo, valida outputs, persiste resultados
LLM probabilístico     → solo razona sobre el código, no controla nada
```

### Stack actual

- Modelo: Qwen2.5:7b via Ollama (local, `think=False`)
- Embeddings: all-MiniLM-L6-v2 (sentence-transformers)
- Vector store: ChromaDB con similitud coseno
- CLI: entrada principal del sistema
- Tests: pytest

---

## Estado actual (2026-06-12)

- **V1 MVP** ✅ completo
- **V2 Precisión** ✅ completo (+ multi-proyecto via `--project`)
- **V3 Experiencia** ✅ completo — HU-016 auto-indexado, HU-017 progreso indexado (limpieza `setup.py` → HU-021)
- **V4 Integraciones** — HU-009 dedup ✅ ya hecho; HU-011/012/013 pendientes
- **V5 Calidad y robustez** 🆕 — HU-018→024 de la auditoría 2026-06-12 (HU-018/019 alta prioridad)
- Bug parseo JSON resuelto: `.env` → `qwen2.5:7b` + `chat(..., think=False)`

**Pendientes sueltos:** HU-002 `.codexignore`, reporte consolidado de directorio (HU-010), flags CLI `--output`/`--stdout` (HU-014), resumen avanzado HU-015.

---

## EPIC — Pipeline de revisión automática de código

### Objetivo

Construir un pipeline que analice archivos o proyectos completos, detecte problemas
reales en el código y genere reportes accionables para desarrolladores.

### Alcance

- Análisis de archivos individuales y directorios completos
- Soporte multilenguaje: Python, TypeScript, JavaScript, TSX, JSX
- Generación de issues con severidad y solución concreta
- Reportes en Markdown y JSON
- Interfaz CLI
- RAG para contexto del proyecto

---

## MÓDULO 1 — Descubrimiento de archivos

### HU-001 — Escaneo de directorios

**Descripción**
Como usuario, quiero entregar una carpeta raíz al sistema para que descubra
automáticamente todos los archivos analizables del proyecto.

**Contexto técnico**
El sistema ya tiene un `indexer.py` que acepta archivos individuales.
Esta HU extiende esa lógica para recorrer directorios recursivamente
usando `pathlib.Path.rglob()`.

**Alcance**

- Recorrer directorios recursivamente
- Detectar archivos por extensión
- Ignorar directorios irrelevantes
- Retornar lista ordenada de paths

**Criterios de aceptación**

- Ignora: `.git`, `node_modules`, `.venv`, `__pycache__`, `dist`, `build`
- Detecta: `.py`, `.ts`, `.tsx`, `.js`, `.jsx`
- Retorna lista de `pathlib.Path` ordenada
- Archivos vacíos son ignorados

**Implementación sugerida**

```python
# app/core/discovery.py
def descubrir_archivos(ruta: str, extensiones: set = None) -> list[Path]:
    ...
```

**Estado:** Implementado ✅ — `app/core/discovery.py::find_files` (rglob, exclusiones, extensiones, ignora vacíos, ordenado)

---

### HU-002 — Configuración de exclusiones

**Descripción**
Como usuario, quiero definir carpetas o patrones excluidos via `.codexignore`
para evitar analizar archivos innecesarios.

**Contexto técnico**
Similar a `.gitignore` — el sistema lee el archivo y aplica las exclusiones
antes del escaneo.

**Alcance**

- Leer `.codexignore` desde la raíz del proyecto
- Soportar exclusión por nombre de carpeta
- Soportar exclusión por patrón glob (`*.generated.ts`)
- Exclusiones por defecto si no existe el archivo

**Criterios de aceptación**

- Si no existe `.codexignore`, aplica exclusiones por defecto
- Soporta wildcards (`*.min.js`, `**/__generated__/**`)
- Evita archivos binarios automáticamente

**Estado:** Pendiente

---

## MÓDULO 2 — Lectura y preparación de código

### HU-003 — Lectura segura de archivos

**Descripción**
Como sistema, necesito leer archivos fuente correctamente para entregar
contenido íntegro al analizador.

**Contexto técnico**
Ya existe `app/tools/leer_archivo.py` con manejo de `FileNotFoundError`,
`PermissionError` y `Exception`. Esta HU formaliza y extiende esa lógica
como parte del pipeline determinístico.

**Alcance**

- Lectura en UTF-8 con fallback a latin-1
- Manejo de errores sin crash
- Validación de tamaño máximo
- Retorno estructurado `{"content": ...}` o `{"error": ...}`

**Criterios de aceptación**

- Maneja encoding inválido sin crash
- Evita crash por permisos
- Archivos mayores a 500KB retornan warning y se truncan
- Retorna dict consistente en todos los casos

**Implementación actual**

```python
# app/tools/leer_archivo.py — ya implementado
def leer_archivo(file: str) -> dict:
    try:
        with open(file, "r") as f:
            return {"content": f.read()}
    except FileNotFoundError:
        return {"error": f"Archivo no encontrado: {file}"}
    except PermissionError:
        return {"error": f"Sin permisos: {file}"}
    except Exception as e:
        return {"error": f"Error inesperado: {str(e)}"}
```

**Estado:** Implementado ✅ — `app/infrastructure/filesystem.py::read_file` incluye límite de tamaño (500KB, trunca + warning) y fallback utf-8→latin-1

---

### HU-004 — Construcción de contexto (Context Builder)

**Descripción**
Como sistema, necesito extraer metadata del archivo para enriquecer
el prompt del LLM antes del análisis.

**Contexto técnico**
Actualmente el sistema usa RAG (ChromaDB) para buscar contexto relacionado.
Esta HU agrega extracción estática de metadata del archivo actual — sin LLM,
determinística.

**Alcance**

- Extraer imports/dependencias
- Extraer nombres de funciones y clases
- Contar líneas totales
- Detectar lenguaje por extensión
- Buscar contexto relacionado via RAG (ChromaDB)

**Criterios de aceptación**

- Funciona sin LLM (solo análisis de texto)
- Para Python: detecta `import`, `def`, `class`
- Para TypeScript/JavaScript: detecta `import`, `function`, `class`, `interface`
- El contexto RAG retorna máximo 5 chunks relevantes con relevancia > 0.3
- Si ChromaDB está vacío, retorna contexto vacío sin error

**Implementación sugerida**

```python
# app/core/context_builder.py
def construir_contexto(path: str, contenido: str) -> dict:
    return {
        "lenguaje":  detectar_lenguaje(path),
        "imports":   extraer_imports(contenido),
        "funciones": extraer_funciones(contenido),
        "clases":    extraer_clases(contenido),
        "lineas":    len(contenido.splitlines()),
        "rag":       buscar_contexto_rag(contenido[:200]),
    }
```

**Estado:** Implementado ✅

---

## MÓDULO 3 — Análisis LLM

### HU-005 — Generación de issues

**Descripción**
Como usuario, quiero que el sistema detecte problemas reales en el código.

**Contexto técnico**
Actualmente el LLM actúa como agente y controla el flujo. En la nueva
arquitectura el LLM recibe un prompt estructurado y retorna JSON.
El orquestador llama al LLM directamente, sin tool calling.

**Alcance**

- Bugs y errores potenciales
- Problemas de seguridad
- Performance
- Legibilidad y mantenibilidad

**Criterios de aceptación**

- Issues contienen: `titulo`, `severidad`, `linea`, `descripcion`, `solucion`
- El LLM retorna JSON puro, sin texto adicional
- Si no hay issues, retorna lista vacía `[]`
- El número de línea referenciado existe en el archivo

**Prompt estructurado**

```
Analiza el siguiente código y retorna SOLO un JSON array de issues.
No incluyas texto antes ni después del JSON.

Archivo: {path}
Lenguaje: {lenguaje}
Imports detectados: {imports}
Funciones detectadas: {funciones}
Contexto relacionado del proyecto: {rag}

Código:
{codigo}

Retorna SOLO esto:
[{"titulo": "...", "severidad": "critico|advertencia|sugerencia",
  "linea": N, "descripcion": "...", "solucion": "..."}]
```

**Estado:** Implementado ✅ — migrado a pipeline determinístico (`app/core/pipeline.py` llama `code_analyzer` directo, sin tool calling)

---

### HU-006 — Clasificación de severidad

**Descripción**
Como usuario, quiero que los issues tengan severidad estandarizada.

**Criterios de aceptación**

- Solo acepta: `critico`, `advertencia`, `sugerencia`
- Valores inválidos se normalizan a `sugerencia`
- Toda issue tiene severidad

**Estado:** Implementado ✅

---

### HU-007 — Prevención de issues falsos

**Descripción**
Como usuario, quiero minimizar issues incorrectos o inventados.

**Contexto técnico**
El problema actual es que el LLM genera falsos positivos (ej: reporta
"falta gestor de contexto" cuando sí existe `with open(...)`).
Se resuelve con validación post-LLM y prompt más restrictivo.

**Criterios de aceptación**

- El número de línea del issue existe en el archivo
- No reporta como issue algo que ya está en el código
- Issues duplicados se eliminan
- Si el LLM retorna JSON inválido, el pipeline continúa sin crash

**Estado:** Implementado ✅

---

## MÓDULO 4 — Validación y normalización

### HU-008 — Validación estructural de resultados

**Descripción**
Como sistema, necesito validar los outputs del LLM antes de persistirlos.

**Contexto técnico**
El LLM puede retornar JSON malformado, campos faltantes o valores inválidos.
Esta capa valida y normaliza antes de pasar al reporte.

**Alcance**

- Parsear JSON del LLM con manejo de errores
- Validar campos obligatorios
- Normalizar severidades
- Validar que las líneas referenciadas existan

**Criterios de aceptación**

- JSON inválido no crashea el pipeline
- Campos faltantes tienen valores por defecto
- Severidades inválidas se corrigen a `sugerencia`
- Líneas fuera de rango se marcan como `linea: 0`

**Estado:** Implementado ✅

---

### HU-009 — Deduplicación de issues

**Descripción**
Como usuario, quiero evitar issues repetidos en el reporte.

**Criterios de aceptación**

- Issues con mismo título y línea se consolidan
- No existen duplicados exactos

**Estado:** Implementado ✅ — `app/domain/validators.py` deduplica por `(line, title)`

---

## MÓDULO 5 — Reporting

### HU-010 — Generación de reporte Markdown

**Descripción**
Como usuario, quiero obtener un reporte legible en Markdown.

**Contexto técnico**
Ya existe `app/tools/guardar_reporte.py`. Esta HU lo extiende para
soportar múltiples archivos en un solo reporte cuando se analiza
un directorio completo.

**Criterios de aceptación**

- Reporte contiene metadata (fecha, archivo, total issues)
- Issues agrupados por severidad (críticos primero)
- Tabla resumen con estadísticas al inicio
- Un reporte por archivo analizado
- Reporte consolidado cuando se analiza un directorio

**Estado:** Parcialmente implementado ✅ — `app/reports/markdown.py` tiene tabla resumen + agrupación por severidad (críticos primero) + metadata. Pendiente: **reporte consolidado** de directorio (hoy genera un .md por archivo)

---

### HU-011 — Exportación JSON

**Descripción**
Como usuario, quiero exportar resultados en JSON para integrarlos con otras herramientas.

**Criterios de aceptación**

- JSON válido con estructura estable
- Mismo schema que los issues internos
- Se genera junto al Markdown automáticamente

**Estado:** Pendiente

---

## MÓDULO 6 — Integraciones futuras

### HU-012 — Integración con Git Diff

**Descripción**
Como usuario, quiero analizar solo archivos modificados para acelerar revisiones.

**Estado:** Pendiente (V3)

---

### HU-013 — Integración con linters

**Descripción**
Como usuario, quiero combinar análisis estático con reasoning LLM.

**Alcance**

- Python: Ruff, MyPy, pytest
- TypeScript/JavaScript: ESLint

**Criterios de aceptación**

- Resultados del linter se incluyen en el contexto del LLM
- Issues del linter y del LLM se unifican sin duplicados

**Estado:** Pendiente (V3)

---

## MÓDULO 7 — CLI

### HU-014 — CLI de análisis

**Descripción**
Como usuario, quiero ejecutar revisiones desde terminal con comandos simples.

**Alcance**

- Analizar archivo individual
- Analizar directorio completo
- Mostrar progreso por archivo
- Output configurable

**Comandos esperados**

```bash
# Archivo individual
codex-review analyze app/tools/leer_archivo.py

# Directorio completo
codex-review analyze ./app

# Con output específico
codex-review analyze ./app --output reports/

# Solo mostrar en terminal sin guardar
codex-review analyze ./app --stdout
```

**Criterios de aceptación**

- Soporta archivo y directorio
- Muestra barra de progreso por archivo
- Muestra resumen al finalizar
- Exit code 0 si no hay críticos, 1 si hay críticos

**Estado:** Implementado ✅ — `app/cli/main.py` soporta archivo y directorio, `typer.progressbar`, resumen por severidad, exit codes 0/1. Requiere `--project`. Pendiente: flags `--output` y `--stdout`

---

### HU-015 — Visualización resumida

**Descripción**
Como usuario, quiero ver un resumen rápido al finalizar el análisis.

**Criterios de aceptación**

- Total de archivos analizados
- Total de issues por severidad
- Archivos con más issues listados primero
- Tiempo total de análisis

**Estado:** Parcialmente implementado — `app/cli/main.py` muestra total de archivos + issues por severidad. Pendiente: archivos con más issues primero, tiempo total

---

## MÓDULO 8 — Experiencia de uso

### HU-016 — Auto-indexado del proyecto

**Descripción**
Como usuario, quiero ejecutar `analyze` sin tener que indexar manualmente el proyecto primero.

**Contexto técnico**
Actualmente el usuario debe ejecutar `python setup.py` antes de usar el pipeline.
Esta HU elimina ese paso — el CLI detecta si ChromaDB está vacío y lo indexa automáticamente.

**Alcance**

- Detectar si ChromaDB está vacío antes de analizar
- Si está vacío, indexar el proyecto automáticamente
- Si ya está indexado, saltar el paso
- Opción `--reindex` para forzar re-indexado

**Criterios de aceptación**

- Primera ejecución indexa automáticamente sin intervención del usuario
- Ejecuciones posteriores no re-indexan si ChromaDB ya tiene datos
- `analyze --reindex` fuerza un nuevo indexado completo
- Si el directorio raíz no puede inferirse, se muestra error claro

**Estado:** Implementado ✅ — `cli/main.py::_ensure_indexed` (ramas `--reindex` / `count==0` / skip), `chroma.get_documents_count` + `reset_collection`, `indexer.index_project` (reúsa `find_files`). Raíz = `path` si es dir, carpeta padre si es archivo. Path inválido → error + exit 1.

---

### HU-017 — Progreso de indexado

**Descripción**
Como usuario, quiero ver el progreso del indexado para saber que el sistema está trabajando.

**Contexto técnico**
El indexado puede tardar varios segundos en proyectos grandes. Sin feedback visual,
el usuario no sabe si el sistema está colgado o procesando.

**Alcance**

- Barra de progreso por archivo indexado
- Mostrar archivo actual siendo procesado
- Mostrar total de archivos y tiempo transcurrido
- Mensaje de confirmación al finalizar

**Criterios de aceptación**

- Barra de progreso visible durante el indexado
- Muestra `archivo X de Y — nombre_archivo.py`
- Al finalizar: `Indexado completo — N archivos, X chunks`
- Sin progreso si solo hay 1 archivo (no es necesario)

**Implementación sugerida**

Usar `rich.progress` (ya disponible via Typer) o `tqdm`.

**Estado:** ✅ Completo (2026-06-19) en el flujo CLI — `cli/main.py::_ensure_indexed` muestra barra rich con `on_progress` callback: `archivo X de Y` (`MofNCompleteColumn` + descripción), tiempo transcurrido (`TimeElapsedColumn`), final `Indexado completo - N archivos, X chunks` (fuera del `with`, no corrompe el render), y sin barra si hay 1 solo archivo (`files_count > 1`). El script legacy `setup.py` sigue con `print [OK]` plano, pero duplica `find_files` + llama `indexar` en vez de `index_project` → su limpieza queda en HU-021 (dedup de infraestructura), no acá.

---

## MÓDULO 9 — Calidad y robustez (V5)

> Hallazgos de la auditoría de calidad/flujo (2026-06-12). Priorizan corregir
> degradaciones silenciosas del producto antes de seguir sumando features.

### HU-018 — Parseo robusto de la salida del LLM

**Descripción**
Como sistema, necesito interpretar la salida del LLM aunque venga envuelta en
fences de código o con texto adicional, para no perder issues silenciosamente.

**Contexto técnico**
`validators.py` hace `json.loads(issues_raw)` directo. Qwen suele envolver el
JSON en ```` ```json ... ``` ```` o agregar texto antes/después →
`JSONDecodeError` → `return []`. Resultado: 0 issues sin aviso, el reporte
aparenta que el código está perfecto. Es el bug de mayor impacto del producto.

**Alcance**

- Forzar salida JSON desde Ollama (`chat(..., format="json")`) en `llm.py`
- Como respaldo: strip de fences + extracción del primer array `[...]`
- Diferenciar "sin issues" (`[]` real) de "fallo de parseo"

**Criterios de aceptación**

- JSON envuelto en fences se parsea correctamente
- JSON con texto antes/después se extrae correctamente
- Un fallo real de parseo se registra/marca, no se confunde con "sin issues"
- `[]` legítimo sigue significando "sin issues"

**Estado:** ✅ Completo (2026-06-17). `format=schema` ya cubría fences/texto extra/`[]`.
Cascada en `llm.py::code_analyzer`: validate → `json_repair` → retry temp 0.3 (cap 1) →
log `[PARSE FAILED]` + `return []`. Falta solo propagar el fallo al reporte → HU-019.

---

### HU-019 — Resiliencia del pipeline

**Descripción**
Como usuario, quiero que un archivo problemático o una caída de Ollama no aborte
el análisis del directorio completo.

**Contexto técnico**
`pipeline.py` llama `code_analyzer` sin try/except. Un fallo (Ollama caído,
archivo raro) propaga la excepción y mata el batch (`cli/main.py`). Además, un
path inexistente cae sin rama → "Análisis completo", exit 0 (no-op silencioso).
La llamada a Ollama no tiene timeout ni reintento.

**Alcance**

- try/except por archivo en el pipeline; acumular fallos y continuar
- Validar que el path exista; error claro + exit 1 si no
- Timeout y manejo de error en la llamada a Ollama (`llm.py`)
- Resumen final lista archivos que fallaron

**Criterios de aceptación**

- Un archivo que falla no detiene el resto del directorio
- Path inválido produce error claro y exit code distinto de 0
- Caída de Ollama se reporta como error, no como crash
- El resumen indica cuántos archivos fallaron

**Estado:** Pendiente — prioridad alta

---

### HU-020 — Soporte multilenguaje real (JS/TS)

**Descripción**
Como usuario, quiero que los archivos JS/TS se indexen y se les extraiga metadata,
no solo Python.

**Contexto técnico**
`discovery.py` descubre `.js/.ts/.jsx/.tsx`, pero `setup.py` solo indexa `*.py`
y `context_builder._EXTRACTORS` solo tiene extractor de Python. Para archivos
JS/TS: sin RAG, sin imports/funciones/clases. Incumple el alcance de HU-004.

**Alcance**

- Indexar también `.js/.ts/.jsx/.tsx` (reusar `find_files`)
- Extractor para JS/TS: `import`, `function`, `class`, `interface`
- Detección de lenguaje ya soportada en `EXTENSIONS`

**Criterios de aceptación**

- Un proyecto JS/TS se indexa completo
- Para TS/JS se detectan import/function/class/interface
- El contexto RAG funciona en proyectos JS/TS

**Estado:** Pendiente

---

### HU-021 — Deduplicación de infraestructura

**Descripción**
Como mantenedor, quiero eliminar lógica duplicada y costos de import innecesarios
para reducir divergencias y acelerar el arranque.

**Contexto técnico**
Varios duplicados detectados:
- `setup.py` reimplementa rglob + exclusiones que ya están en `find_files`
- `indexer.py` lee solo utf-8 (sin fallback); `filesystem.read_file` ya resuelve encoding + límite
- `infrastructure/__init__.py` importa `embeddings` de forma ansiosa → carga `sentence_transformers`/`torch` aunque solo se use `filesystem`
- Parámetros de chunking duplicados: `chunk_texto(5,2)` vs `indexar(10,3)`
- Literal `{"hnsw:space": "cosine"}` repetido en `chroma.py` e `indexer.py`

**Alcance**

- `setup.py` reusa `find_files`
- `indexer.py` reusa `read_file`
- Vaciar `infrastructure/__init__.py` (imports lazy)
- Una sola fuente para parámetros de chunking
- Constante compartida para metadata de colección

**Criterios de aceptación**

- No hay dos lugares con reglas de descubrimiento de archivos
- Indexado no crashea con archivos no-utf8
- Importar `read_file` no carga torch
- Chunking tiene una sola configuración

**Estado:** Pendiente

---

### HU-022 — Logging y configuración central

**Descripción**
Como mantenedor, quiero logging con niveles y un único punto de configuración,
en vez de `print` dispersos y `os.getenv` repartido.

**Contexto técnico**
Hay `print` de debug (`pipeline.py` → `"Pipeline executed"`) y prints dispersos
en cli/pipeline/discovery/validators. Las env vars se leen sueltas en `llm.py`,
`embeddings.py`, `setup.py`.

**Alcance**

- Módulo `logging` con niveles (info/warning/error)
- Quitar prints de debug
- Módulo `settings`/`config` central que centralice env vars

**Criterios de aceptación**

- No quedan `print` de debug en el código
- Nivel de log configurable
- Las env vars se leen en un solo módulo

**Estado:** Pendiente

---

### HU-023 — Consistencia de modelos y naming

**Descripción**
Como mantenedor, quiero nombres y type hints consistentes para evitar confusión.

**Contexto técnico**
- `InputModel.clases` (español) junto a `functions`/`imports` (inglés)
- Type hint mentiroso: `functions: list[dict[str, list[str]]]` pero `name` es `str`
- Literal de metadata de colección duplicado
- UX CLI: resumen solo en rama directorio, no en archivo único; `print` dentro del loop pisa el `typer.progressbar`

**Alcance**

- Unificar naming (preferir inglés en el dominio)
- Corregir type hints de `InputModel`
- Mostrar resumen también para archivo único
- Evitar prints dentro del progressbar

**Criterios de aceptación**

- Naming consistente en `models.py`
- Type hints reflejan la estructura real
- Resumen visible en archivo y directorio
- La barra de progreso no se corrompe con prints

**Estado:** Pendiente

---

### HU-024 — Suite de tests del camino crítico

**Descripción**
Como mantenedor, quiero tests sobre el flujo central para detectar regresiones.

**Contexto técnico**
Hoy solo hay tests de `validators`, `context_builder`, `indexer`. Cero cobertura
en `pipeline`, `cli`, `llm`, `chroma`, `markdown`. No hay test que cubra el bug
de parseo de fences (HU-018).

**Alcance**

- Test de `pipeline` con LLM mockeado
- Test de parseo robusto (fences, texto extra) — cubre HU-018
- Test de `cli` (path válido/inválido, exit codes)
- Test de `markdown` (estructura del reporte)

**Criterios de aceptación**

- El camino crítico tiene cobertura de tests
- Existe test que falla si reaparece el bug de fences
- Los exit codes del CLI están testeados

**Estado:** Pendiente

---

## Roadmap

### V1 — MVP funcional ✅ COMPLETO

- HU-001 Escaneo de directorios ✅
- HU-003 Lectura segura ✅
- HU-005 Generación de issues ✅ (pipeline determinístico)
- HU-010 Reporte Markdown ✅ (parcial — falta consolidado de directorio)
- HU-014 CLI básico ✅

**Objetivo:** Analizar un directorio completo y generar reportes desde terminal.

---

### V2 — Mejora de precisión ✅ COMPLETO

- HU-004 Context Builder ✅
- HU-006 Severidad ✅
- HU-007 Prevención de falsos positivos ✅
- HU-008 Validación estructural ✅

**Objetivo:** Reportes confiables sin falsos positivos.

**Extra completado:** Soporte multi-proyecto via `--project` (embeddings.py lazy loaders, collection requerido).

---

### V3 — Experiencia de uso ✅ COMPLETO

- HU-016 Auto-indexado del proyecto ✅
- HU-017 Progreso de indexado ✅ (flujo CLI; limpieza de `setup.py` → HU-021)

**Objetivo:** El usuario no necesita saber que ChromaDB existe. El sistema se configura solo.

---

### V4 — Integraciones

- HU-009 Deduplicación ✅ (ya en validators.py)
- HU-011 Export JSON — pendiente
- HU-012 Git Diff — pendiente
- HU-013 Linters — pendiente

**Objetivo:** Integración con herramientas externas.

---

### V5 — Calidad y robustez

- HU-018 Parseo robusto de salida LLM — ✅ **completo**
- HU-019 Resiliencia del pipeline — **alta prioridad**
- HU-020 Soporte multilenguaje real (JS/TS)
- HU-021 Deduplicación de infraestructura
- HU-022 Logging y configuración central
- HU-023 Consistencia de modelos y naming
- HU-024 Suite de tests del camino crítico

**Objetivo:** Eliminar degradaciones silenciosas del producto y reducir deuda
técnica antes de seguir sumando integraciones.

---

## Nueva estructura del proyecto

```
codex-review/
├── app/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── orchestrator.py    ← controla el pipeline
│   │   ├── pipeline.py        ← flujo por archivo
│   │   └── discovery.py       ← escaneo de directorios
│   ├── domain/
│   │   ├── __init__.py
│   │   ├── models.py          ← Issue, Report (dataclasses)
│   │   └── validators.py      ← validación de outputs LLM
│   ├── infrastructure/
│   │   ├── __init__.py
│   │   ├── filesystem.py      ← leer_archivo mejorado
│   │   ├── llm.py             ← llamadas a Ollama
│   │   └── rag.py             ← ChromaDB (buscar_contexto + indexer)
│   ├── reports/
│   │   ├── __init__.py
│   │   ├── markdown.py        ← guardar_reporte mejorado
│   │   └── json_report.py     ← export JSON
│   └── cli/
│       ├── __init__.py
│       └── main.py            ← entry point CLI
├── tests/
│   ├── __init__.py
│   ├── test_discovery.py
│   ├── test_pipeline.py
│   ├── test_validators.py
│   └── test_reports.py
├── .codexignore
├── .env
├── .gitignore
├── pyproject.toml
└── README.md
```

---

## Mapeo de código existente → nueva estructura

| Archivo actual                 | Nueva ubicación                    | Cambios                          |
| ------------------------------ | ---------------------------------- | -------------------------------- |
| `app/tools/leer_archivo.py`    | `app/infrastructure/filesystem.py` | Agregar límite de tamaño         |
| `app/tools/buscar_contexto.py` | `app/infrastructure/rag.py`        | Unificar con indexer             |
| `app/indexer.py`               | `app/infrastructure/rag.py`        | Unificar con buscar_contexto     |
| `app/tools/guardar_reporte.py` | `app/reports/markdown.py`          | Soporte multi-archivo            |
| `app/tools/ejecutar_tests.py`  | `app/infrastructure/llm.py`        | Mover a integraciones V3         |
| `app/agente.py`                | `app/core/orchestrator.py`         | Migrar a pipeline determinístico |
