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

- Modelo: Qwen2.5:32b via Ollama (local)
- Embeddings: all-MiniLM-L6-v2 (sentence-transformers)
- Vector store: ChromaDB con similitud coseno
- CLI: entrada principal del sistema
- Tests: pytest

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

**Estado:** Pendiente

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

**Estado:** Implementado ✅ — pendiente agregar límite de tamaño

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

**Estado:** Parcialmente implementado — pendiente migrar a pipeline determinístico

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

**Estado:** Pendiente

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

**Estado:** Parcialmente implementado ✅ — pendiente agrupación por severidad y reporte consolidado

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

**Estado:** Pendiente

---

### HU-015 — Visualización resumida

**Descripción**
Como usuario, quiero ver un resumen rápido al finalizar el análisis.

**Criterios de aceptación**

- Total de archivos analizados
- Total de issues por severidad
- Archivos con más issues listados primero
- Tiempo total de análisis

**Estado:** Pendiente

---

## Roadmap

### V1 — MVP funcional

- HU-001 Escaneo de directorios
- HU-003 Lectura segura ✅
- HU-005 Generación de issues (migrar a pipeline)
- HU-010 Reporte Markdown ✅ parcial
- HU-014 CLI básico

**Objetivo:** Analizar un directorio completo y generar reportes desde terminal.

---

### V2 — Mejora de precisión

- HU-004 Context Builder
- HU-006 Severidad ✅
- HU-007 Prevención de falsos positivos
- HU-008 Validación estructural

**Objetivo:** Reportes confiables sin falsos positivos.

---

### V3 — Integraciones

- HU-009 Deduplicación
- HU-011 Export JSON
- HU-012 Git Diff
- HU-013 Linters

**Objetivo:** Integración con herramientas externas.

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
