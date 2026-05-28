from app.domain.validators import issues_validator


def test_retorna_issues_validos():
    raw = '[{"titulo": "Error", "severidad": "critico", "linea": 1, "descripcion": "desc", "solucion": "sol"}]'
    issues = issues_validator(raw, total_lines=10)
    assert len(issues) == 1
    assert issues[0].title == "Error"
    assert issues[0].severity == "critical"
    assert issues[0].line == 1


def test_json_invalido_retorna_lista_vacia():
    issues = issues_validator("esto no es json", total_lines=10)
    assert issues == []


def test_json_no_lista_retorna_lista_vacia():
    issues = issues_validator('{"titulo": "Error"}', total_lines=10)
    assert issues == []


def test_linea_fuera_de_rango_se_asigna_cero():
    raw = '[{"titulo": "Error", "severidad": "critico", "linea": 999, "descripcion": "desc", "solucion": "sol"}]'
    issues = issues_validator(raw, total_lines=10)
    assert issues[0].line == 0


def test_duplicados_se_eliminan():
    raw = '[{"titulo": "Error", "severidad": "critico", "linea": 1, "descripcion": "desc", "solucion": "sol"}, {"titulo": "Error", "severidad": "critico", "linea": 1, "descripcion": "desc", "solucion": "sol"}]'
    issues = issues_validator(raw, total_lines=10)
    assert len(issues) == 1


def test_mismo_titulo_distinta_linea_no_es_duplicado():
    raw = '[{"titulo": "Error", "severidad": "critico", "linea": 1, "descripcion": "desc", "solucion": "sol"}, {"titulo": "Error", "severidad": "critico", "linea": 2, "descripcion": "desc", "solucion": "sol"}]'
    issues = issues_validator(raw, total_lines=10)
    assert len(issues) == 2


def test_issue_malformado_se_salta():
    raw = '["no soy dict", {"titulo": "Error", "severidad": "sugerencia", "linea": 1, "descripcion": "desc", "solucion": "sol"}]'
    issues = issues_validator(raw, total_lines=10)
    assert len(issues) == 1


def test_severidad_desconocida_mapea_a_suggestion():
    raw = '[{"titulo": "X", "severidad": "desconocida", "linea": 1, "descripcion": "d", "solucion": "s"}]'
    issues = issues_validator(raw, total_lines=10)
    assert issues[0].severity == "suggestion"
