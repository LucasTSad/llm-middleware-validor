import pytest

from prompt_validator.core.contracts import Category, GuardConfig, Severity
from prompt_validator.core.detectors.injection import InjectionDetector
from prompt_validator.core.normalizer import normalize


def test_texto_legitimo_sem_delimitador_nao_gera_finding():
    normalized = normalize("bom dia", GuardConfig())
    detector = InjectionDetector()

    findings = detector.inspect(normalized, GuardConfig())

    assert findings == []


@pytest.mark.parametrize(
    "texto",
    [
        "<|system|>",
        "<|end|>",
        "[SYSTEM]",
        "[END SYSTEM]",
        '<message role="system">',
        "</system>",
    ],
)
def test_delimitadores_sao_detectados(texto):
    normalized = normalize(texto, GuardConfig())
    detector = InjectionDetector()

    findings = detector.inspect(normalized, GuardConfig())

    assert len(findings) == 1

    finding = findings[0]

    assert finding.matched_type == "delimiter"
    assert finding.category == Category.PROMPT_INJECTION
    assert finding.severity == Severity.MEDIUM
    assert finding.rule_id == "injection.delimiter.v1"
    assert finding.score == 0.9


@pytest.mark.parametrize(
    "texto",
    [
        "<html>",
        "<Fulano>",
        "[Fulano 2023]",
        "bom dia",
    ],
)
def test_conteudo_arbitrario_nao_e_delimitador(texto):
    normalized = normalize(texto, GuardConfig())
    detector = InjectionDetector()

    findings = detector.inspect(normalized, GuardConfig())

    assert findings == []


def test_delimitador_preserva_span_original():
    texto = "antes <|system|> depois"

    normalized = normalize(texto, GuardConfig())
    findings = InjectionDetector().inspect(normalized, GuardConfig())

    assert len(findings) == 1

    finding = findings[0]
    assert texto[finding.start : finding.end] == "<|system|>"


def test_delimitador_com_invisivel_antes_preserva_span_original():
    texto = "\u200bantes <|system|> depois"

    normalized = normalize(texto, GuardConfig())
    findings = InjectionDetector().inspect(normalized, GuardConfig())

    assert len(findings) == 1

    finding = findings[0]
    assert texto[finding.start : finding.end] == "<|system|>"

def test_delimitador_com_invisivel_dentro_preserva_span_original():
    texto = "antes <|sys\u200btem|> depois"

    normalized = normalize(texto, GuardConfig())
    findings = InjectionDetector().inspect(normalized, GuardConfig())

    assert len(findings) == 1

    finding = findings[0]
    assert texto[finding.start:finding.end] == "<|sys\u200btem|>"

def test_dois_delimitadores_geram_dois_findings():
    texto = "<|system|> texto <|end|>"

    normalized = normalize(texto, GuardConfig())
    findings = InjectionDetector().inspect(normalized, GuardConfig())

    assert len(findings) == 2
    assert [texto[f.start : f.end] for f in findings] == [
        "<|system|>",
        "<|end|>",
    ]
