import pytest
from pydantic import ValidationError

from prompt_validator.core.contracts import (
    Action,
    Category,
    Decision,
    Finding,
    NormalizedText,
    Severity,
)


def finding(
    *,
    rule_id: str = "pii.cpf.v1",
    category: Category = Category.PII_DISCLOSURE,
    severity: Severity = Severity.HIGH,
    start: int = 0,
    end: int = 11,
    matched_type: str = "cpf",
    score: float = 1.0,
) -> Finding:
    return Finding(
        rule_id=rule_id,
        category=category,
        severity=severity,
        start=start,
        end=end,
        matched_type=matched_type,
        score=score,
    )


def normalized_text(**kwargs) -> NormalizedText:
    base = {
        "original": "ignore",
        "normalized": "ignore",
        "offset_map": (0, 1, 2, 3, 4, 5),
    }
    return NormalizedText(**(base | kwargs))


def test_severidade_ordenavel():
    assert Severity.LOW < Severity.MEDIUM < Severity.HIGH < Severity.CRITICAL


def test_finding_rejeita_span_invertido():
    with pytest.raises(ValidationError):
        finding(start=10, end=5)


def test_finding_imutavel():
    f = finding()
    with pytest.raises(ValidationError):
        f.severity = Severity.LOW


def test_block_exige_justificativa():
    with pytest.raises(ValidationError):
        Decision(action=Action.BLOCK)


def test_block_nao_carrega_texto_sanitizado():
    with pytest.raises(ValidationError):
        Decision(action=Action.BLOCK, findings=(finding(),), sanitized_text="teste")


def test_sanitize_exige_texto():
    with pytest.raises(ValidationError):
        Decision(action=Action.SANITIZE, findings=(finding(),))


def test_placeholders_nao_vazam_na_serializacao():
    d = Decision(
        action=Action.SANITIZE,
        findings=(finding(),),
        sanitized_text="meu cpf e [[PII_CPF_1]]",
        placeholders={"[[PII_CPF_1]]": "123.456.789-10"},
    )
    assert "123.456.789-10" not in d.model_dump_json()


def test_conversao_para_milisegundos():
    d = Decision(action=Action.ALLOW, elapsed_ns=3_500_000)
    assert d.elapsed_ms == pytest.approx(3.5)


def test_normalized_text_rejeitada_offset_map_com_tamanho_diferente():
    with pytest.raises(ValidationError, match=r"Offset_map tem tamanho"):
        normalized_text(offset_map=(0, 1, 2))


def test_normalized_text_rejeitada_offset_map_com_indice_fora_do_original():
    with pytest.raises(ValidationError, match=r"Offset_map tem valores invalidos"):
        normalized_text(original="oi", normalized="oi", offset_map=(0, 2))


def test_normalized_text_rejeitada_offset_map_nao_crescente():
    with pytest.raises(ValidationError, match=r"Offset_map nao eh crescente"):
        normalized_text(offset_map=(1, 0, 2, 3, 4, 5))


def test_normalized_text_to_original_span_com_expansao():
    texto = "a\u00bdb"

    n = NormalizedText(
        original=texto,
        normalized="a1\u20442b",
        offset_map=(0, 1, 1, 1, 2),
    )

    start, end = n.to_original_span(1, 4)

    assert n.original[start:end] == "\u00bd"


def test_normalized_text_to_original_span_com_remocao():
    texto = "ig\u200bnore"

    normalized_text = NormalizedText(
        original=texto,
        normalized="ignore",
        offset_map=(0, 1, 3, 4, 5, 6),
    )

    start, end = normalized_text.to_original_span(2, 5)

    assert normalized_text.original[start:end] == "nor"


def test_normalized_text_to_original_span_rejeita_span_invalido():
    n = normalized_text()

    with pytest.raises(ValueError, match=r"span invalido"):
        n.to_original_span(2, 2)


def test_normalized_text_to_original_span_rejeitada_start_negativo():
    n = normalized_text()

    with pytest.raises(ValueError, match=r"start nao pode ser negativo"):
        n.to_original_span(-1, 2)


def test_normalized_text_to_original_span_rejeitada_end_fora_do_mapa():
    n = normalized_text()

    with pytest.raises(ValueError, match=r"end fora dos limites do texto normalizado"):
        n.to_original_span(2, 7)
