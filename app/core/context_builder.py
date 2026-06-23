import re
from pathlib import Path

EXTENSIONS = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".go": "go",
    ".rs": "rust",
}


def _split(raw: str | None) -> list[str]:
    return [x.strip() for x in raw.split(",")] if raw else []


def _split_args(raw: str) -> list[str]:
    """Divide args respetando generics anidados: dict[str, Any] no se parte."""
    args, current, depth = [], [], 0
    for ch in raw:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if ch == "," and depth == 0:
            a = "".join(current).strip()
            if a:
                args.append(a)
            current = []
        else:
            current.append(ch)
    a = "".join(current).strip()
    if a:
        args.append(a)
    return args


def _collapse_parens(code: str) -> str:
    """Reemplaza newlines dentro de paréntesis por espacios (para args multilínea)."""
    result, depth = [], 0
    for ch in code:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "\n" and depth > 0:
            result.append(" ")
        else:
            result.append(ch)
    return "".join(result)


def _py(code: str) -> dict:
    imports, functions, classes = [], [], []
    flat = _collapse_parens(code)

    # imports — incluye from x import (\n  a,\n  b\n) multilínea
    for m in re.finditer(r"^(?:import|from)\s+.+", flat, re.M):
        cleaned = re.sub(r"\s+", " ", m.group().strip())
        cleaned = re.sub(r"\(\s*(.*?)\s*,?\s*\)$", r"(\1)", cleaned)
        imports.append(cleaned)

    # funciones con decoradores y args multilínea
    _DECS = r"((?:^[ \t]*@[\w.]+(?:\([^)]*\))?[ \t]*\n)+)?"
    _FUNC = r"^[ \t]*(?:async\s+)?def\s+(\w+)\s*\(([^)]*)\)"
    func_pat = re.compile(_DECS + _FUNC, re.M)

    for m in func_pat.finditer(flat):
        raw_decs = m.group(1) or ""
        decorators = re.findall(r"@[\w.]+(?:\([^)]*\))?", raw_decs)
        functions.append(
            {
                "name": m.group(2),
                "args": _split_args(m.group(3)),
                "decorators": decorators,
            }
        )

    # clases con decoradores
    class_pat = re.compile(
        r"((?:^[ \t]*@[\w.]+(?:\([^)]*\))?[ \t]*\n)+)?^[ \t]*class\s+(\w+)(?:\(([^)]*)\))?",
        re.M,
    )
    for m in class_pat.finditer(flat):
        raw_decs = m.group(1) or ""
        decorators = re.findall(r"@[\w.]+(?:\([^)]*\))?", raw_decs)
        classes.append(
            {
                "name": m.group(2),
                "bases": _split(m.group(3)),
                "decorators": decorators,
            }
        )

    return {"imports": imports, "functions": functions, "classes": classes}


def _js_ts(code: str) -> dict:
    imports, functions, classes, interfaces = [], [], [], []

    # imports multilínea: colapsar el bloque { ... } antes de extraer
    collapsed = re.sub(r"import\s*\{[^}]*\}", lambda m: m.group().replace("\n", " "), code)
    for m in re.finditer(r"^import\s+.+", collapsed, re.M):
        imports.append(re.sub(r"\s+", " ", m.group().strip()))
    for m in re.finditer(r"\brequire\s*\(\s*['\"]([^'\"]+)['\"]\s*\)", code):
        imports.append(f"require('{m.group(1)}')")

    # function foo(...) / async function foo(...)
    for m in re.finditer(r"(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)", code, re.S):
        functions.append({"name": m.group(1), "args": _split_args(m.group(2))})

    # const/let/var foo = x => / foo = (x, y) => (con o sin paréntesis)
    for m in re.finditer(
        r"(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?(\w+|\([^)]*\))\s*(?::[^=]*(?:<[^>]*>)?[^=]*)?\s*=>",
        code,
    ):
        raw_args = m.group(2)
        args = _split_args(raw_args.strip("()")) if raw_args else []
        functions.append({"name": m.group(1), "args": args})

    # class Foo / class Foo extends Bar
    for m in re.finditer(r"class\s+(\w+)(?:\s+extends\s+(\w+))?", code):
        classes.append({"name": m.group(1), "bases": [m.group(2)] if m.group(2) else []})

    # interface (TS)
    for m in re.finditer(r"(?:export\s+)?interface\s+(\w+)(?:\s+extends\s+([\w,\s]+))?", code):
        interfaces.append(
            {
                "name": m.group(1),
                "extends": _split(m.group(2)) if m.group(2) else [],
            }
        )

    result = {"imports": imports, "functions": functions, "classes": classes}
    if interfaces:
        result["interfaces"] = interfaces
    return result


def _go(code: str) -> dict:
    imports, functions, structs = [], [], []

    block = re.search(r"import\s*\(([^)]+)\)", code, re.S)
    if block:
        for m in re.finditer(r'"([^"]+)"', block.group(1)):
            imports.append(m.group(1))
    for m in re.finditer(r'^import\s+"([^"]+)"', code, re.M):
        imports.append(m.group(1))

    for m in re.finditer(r"^func\s+(?:\(\w+\s+\*?\w+\)\s+)?(\w+)\s*\(([^)]*)\)", code, re.M):
        functions.append({"name": m.group(1), "args": _split_args(m.group(2))})

    for m in re.finditer(r"^type\s+(\w+)\s+struct", code, re.M):
        structs.append({"name": m.group(1)})

    return {"imports": imports, "functions": functions, "structs": structs}


def _rs(code: str) -> dict:
    imports, functions, structs = [], [], []

    for m in re.finditer(r"^use\s+.+;", code, re.M):
        imports.append(m.group().strip())

    for m in re.finditer(r"(?:pub\s+)?(?:async\s+)?fn\s+(\w+)\s*\(([^)]*)\)", code):
        functions.append({"name": m.group(1), "args": _split_args(m.group(2))})

    for m in re.finditer(r"(?:pub\s+)?(?:struct|enum|trait)\s+(\w+)", code):
        structs.append({"name": m.group(1)})

    return {"imports": imports, "functions": functions, "structs": structs}


_EXTRACTORS = {
    "python": _py,
    "javascript": _js_ts,
    "typescript": _js_ts,
    "go": _go,
    "rust": _rs,
}


def get_language(path: Path) -> str:
    return EXTENSIONS.get(path.suffix.lower(), "unknown")


def extract_file_metadata(path: Path | str, content: str) -> dict:
    path = Path(path)
    language = get_language(path)
    if language == "unknown":
        return {
            "file": str(path),
            "language": "unknown",
            "error": f"Extension no soportada {path.suffix}",
        }

    return {
        "file": str(path),
        "language": language,
        **_EXTRACTORS[language](content),
        "lines": len(content.splitlines()),
    }


def query_context(file_metadata: dict) -> str | None:
    context_query = ""

    for imp in file_metadata.get("imports", []):
        context_query += f"Import: {imp}\n"

    for func in file_metadata.get("functions", []):
        args = ", ".join(func["args"])
        decs = "  # " + ", ".join(func["decorators"]) if func.get("decorators") else ""
        context_query += f"Function: {func['name']}({args}){decs}\n"

    for cls in file_metadata.get("classes", []):
        bases = ", ".join(cls["bases"])
        decs = "  # " + ", ".join(cls["decorators"]) if cls.get("decorators") else ""
        context_query += f"Class: {cls['name']}({bases}){decs}\n"

    for iface in file_metadata.get("interfaces", []):
        ext = ", ".join(iface["extends"])
        context_query += f"Interface: {iface['name']}({ext})\n"

    for s in file_metadata.get("structs", []):
        context_query += f"Struct: {s['name']}\n"

    return context_query if context_query else None
