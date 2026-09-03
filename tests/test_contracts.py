import pytest
from pydantic import ValidationError

from prompt_validator.core.contracts import (
    Action,
    Category,
    Decision,
    Finding,
    Severity,
)

def finding(**kwargs) -> Finding:
    base = dict(
        rule_id = "pii.cpf.v1",
        category = Category.PII_DISCLOSURE,
        severity = Severity.HIGH,
        start = 0,
        end = 11,
        matched_type = "cpf",
    )
    return Finding(**(base | kwargs))

def test_severidade_ordenavel():
    assert Severity.LOW < Severity.MEDIUM < Severity.HIGH < Severity.CRITICAL

def test_finding_rejeita_span_invertido():
    with pytest.raises(ValidationError):
        finding(start = 10, end = 5)

def test_finding_imutavel():
    f = finding()
    with pytest.raises(ValidationError):
        f.severity = Severity.LOW

def test_block_exige_justificativa():
    with pytest.raises(ValidationError):
        Decision(action = Action.BLOCK)

def test_block_nao_carrega_texto_sanitizado():
    with pytest.raises(ValidationError):
        Decision(
            action = Action.BLOCK, 
            findings = (finding(),), 
            sanitized_text = "teste"
        )

def test_sanitize_exige_texto():
    with pytest.raises(ValidationError):
        Decision(action=Action.SANITIZE, findings=(finding(),))

def test_placeholders_nao_vazam_na_serializacao():
    d = Decision(
        action = Action.SANITIZE,
        findings = (finding(),),
        sanitized_text = "meu cpf e [[PII_CPF_1]]",
        placeholders = {"[[PII_CPF_1]]": "123.456.789-10"},
    )
    assert "123.456.789-10" not in d.model_dump_json()

def test_conversao_para_milisegundos():
    d = Decision(action = Action.ALLOW, elapsed_ns = 3_500_000)
    assert d.elapsed_ms == pytest.approx(3.5)