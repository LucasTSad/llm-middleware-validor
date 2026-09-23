import pytest

from prompt_validator.core.contracts import (
    Decision,
    Finding, 
    GuardConfig, 
    Action, 
    Category, 
    Severity,
    MaskMode
)
from prompt_validator.core.detectors.pii import PiiDetector
from prompt_validator.core.engine import decide_action, build_detectors, Engine
from prompt_validator.core.detectors.null import NullDetector

def finding(**kwargs) -> Finding:
    base = dict(
        rule_id = "pii.cpf.v2",
        category = Category.PII_DISCLOSURE,
        severity = Severity.MEDIUM,
        start = 0,
        end = 11,
        matched_type = "cpf",
    )
    return Finding(**(base | kwargs))


def test_sem_findings_allow():
    assert decide_action([], GuardConfig()) == Action.ALLOW

def test_finding_critical_block():
    f = finding(severity = Severity.CRITICAL)
    assert decide_action([f], GuardConfig()) == Action.BLOCK

def test_finding_pii_low_sanitize():
    f = finding(category = Category.PII_DISCLOSURE, 
                severity = Severity.LOW)
    assert decide_action([f], GuardConfig()) == Action.SANITIZE

def test_finding_injection_score09_block():
    f = finding(category = Category.PROMPT_INJECTION, 
                score = 0.9)
    assert decide_action([f], GuardConfig()) == Action.BLOCK

def test_injection_tem_precedencia_sobre_pii():
    pii = finding(
        category = Category.PII_DISCLOSURE,
        severity = Severity.LOW,
    )
    injection = finding(
        rule_id = "injection.ignore_previous.v1",
        category = Category.PROMPT_INJECTION,
        severity = Severity.LOW,
        matched_type = "ignore_previous",
        score = 0.9,
    )
    assert decide_action([pii, injection], GuardConfig()) == Action.BLOCK

def test_score03_not_block():
    f = finding(score = 0.3)
    assert decide_action([f], GuardConfig()) != Action.BLOCK

def test_builder_detectors_aceita_null():
    detect = build_detectors(GuardConfig(enabled_detectors = ("null",)))
    assert len(detect) == 1
    assert isinstance(detect[0], NullDetector)

def test_builder_detectors_rejeita_nome_desconhecido():
    with pytest.raises(ValueError):
        build_detectors(GuardConfig(enabled_detectors = ("pil",)))

def test_engine_libera_null():
    engine = Engine([NullDetector()], GuardConfig())
    decision = engine.analyze("meu cpf e 123.456.789-09")
    assert decision.action == Action.ALLOW

def test_engine_libera_findings_vazio():
    engine = Engine([NullDetector()], GuardConfig())
    decision = engine.analyze("")
    assert decision.findings == ()

def test_engine_caminho_limpa_nao_inventa_texto():
    engine = Engine([NullDetector()] , GuardConfig())
    decision = engine.analyze("meu cpf e 123.456.789-09")

    assert decision.sanitized_text is None
    assert decision.placeholders == {}
    assert decision.action == Action.ALLOW

def test_engine_pii_detector_fim_a_fim():
    engine = Engine([PiiDetector()], GuardConfig())
    decision = engine.analyze("Meu CPF é 529.982.247-25")

    assert decision.action == Action.SANITIZE
    assert decision.sanitized_text == "Meu CPF é [CPF_1]"
    assert decision.placeholders == {"[CPF_1]": "529.982.247-25"}

def test_engine_mask_mode_irreversible():
    engine = Engine([PiiDetector()], GuardConfig(mask_mode = MaskMode.IRREVERSIBLE))
    decision = engine.analyze("Meu CPF é 529.982.247-25")

    assert decision.action == Action.SANITIZE
    assert decision.sanitized_text == "Meu CPF é [CPF_1]"
    assert decision.placeholders == {}

def test_engine_finding_aponta_para_texto_original():  
    texto = "Meu CPF é 529.982\u200b.247-25"

    engine = Engine([PiiDetector()], GuardConfig())
    decision = engine.analyze(texto)

    finding = decision.findings[0]

    assert texto[finding.start:finding.end] == "529.982\u200b.247-25"

def test_engine_invisivel_dentro_da_pii_e_removido_com_ela():
    engine = Engine([PiiDetector()], GuardConfig())
    decision = engine.analyze("529.982\u200b.247-25")

    assert decision.action == Action.SANITIZE
    assert decision.sanitized_text == "[CPF_1]"

def test_engine_nao_expoe_dados_sensiveis_na_decision():
    engine = Engine([PiiDetector()], GuardConfig())
    decision = engine.analyze("Meu CPF é 529.982.247-25")

    dumped = decision.model_dump()

    assert "placeholders" not in dumped
    assert "529" not in str(dumped)
    assert "529" not in decision.model_dump_json()

def test_engine_elapsed_ns_maior_que_zero():
    engine = Engine([PiiDetector()], GuardConfig())
    decision = engine.analyze("meu cpf e 123.456.789-09")

    assert decision.elapsed_ns > 0

def test_engine_nao_detecta_pii_com_detector_desabilitado():
    config = GuardConfig(enabled_detectors=("null",))
    engine = Engine(build_detectors(config), config)

    decision = engine.analyze("Meu CPF é 529.982.247-25")

    assert decision.action == Action.ALLOW