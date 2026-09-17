import pytest 

from prompt_validator.core.detectors.pii import is_cpf, PiiDetector
from prompt_validator.core.contracts import Finding, GuardConfig
from prompt_validator.core.normalizer import normalize

@pytest.mark.parametrize(
    "cpf",
    [
        "52998224725",
        "37473575040",
        "77930253007",
    ],
)
def test_is_cpf_true(cpf):
    assert is_cpf(cpf) is True

@pytest.mark.parametrize(
    "cpf",
    [
        "52998224715", # DV1 errado
        "52998224726", # DV2 errado
    ],
)
def test_is_cpf_calculate_dv_errado(cpf):
    assert is_cpf(cpf) is False

@pytest.mark.parametrize(
    "cpf",
    [
        "10000000604", # DV1: resto == 0
        "10000000280", # DV2: resto == 0
        "10000000108", # DV1: resto == 1
        "10000002810", # DV2: resto == 1
    ],
)
def test_is_cpf_resto_zero_e_um(cpf):
    assert is_cpf(cpf) is True

@pytest.mark.parametrize(
    "cpf",
    [
        "11111111111",
        "00000000000",
    ],
)
def test_is_cpf_digitos_repetidos(cpf):
    assert is_cpf(cpf) is False

@pytest.mark.parametrize(
    "cpf",
    [
        "5299822472",       # 10 dígitos
        "529982247250",     # 12 dígitos
        "",                 # vazio
        "529.982.247-25",   # separadores
        "5299822472a",      # letra
        "\uff15" * 11,      # fullwidth: NFKC converte, isascii rejeita
        "\u0665" * 11,      # árabe-índico: isdecimal aceita, isascii rejeita
        "\u00bd" * 11,      # ½: isnumeric aceita, isdecimal rejeita
        "\u00b2" * 11,      # ²: isdigit aceita, isdecimal rejeita
        " 5299822472",      # espaço
    ],
)
def test_is_cpf_invalid_guard(cpf):
    assert is_cpf(cpf) is False

def _inspect(texto: str) -> list[Finding]:
    detector = PiiDetector()
    config = GuardConfig()

    normalized = normalize(texto, config)

    return detector.inspect(normalized, config)

@pytest.mark.parametrize(
    "texto",
    [
        "sem pii",              # sem pii
        "cpf 529.982.247-26",   # dv inválido
        "07290264000176",       # cnpj sem pontuação
        "06.050.842/0001-34",   # cnpj com pontuação
        "1529.982.247-251",     # cpf entre numeros
        "\u0665" * 11,          # árabe índico
    ],
)
def test_inspect_sem_finding(texto):
    assert _inspect(texto) == []

def test_inspect_cpf_com_pontuacao():
    findings = _inspect("cpf 529.982.247-25")

    assert len(findings) == 1

    finding = findings[0]

    assert finding.start == 4
    assert finding.end == 18
    assert finding.matched_type == "cpf"

def test_inspect_cpf_formato_nu():
    findings = _inspect("cpf 52998224725")

    assert len(findings) == 1

    finding = findings[0]

    assert finding.start == 4
    assert finding.end == 15

def test_inspect_cpf_dois_findings():
    findings = _inspect("a 529.982.247-25 b 52998224725")

    assert len(findings) == 2

    assert findings[0].start == 2
    assert findings[0].end == 16
    assert findings[0].matched_type == "cpf"

    assert findings[1].start == 19
    assert findings[1].end == 30
    assert findings[1].matched_type == "cpf"

def test_inspect_cpf_fullwidth_nfkc():
    texto = "\uff15\uff12\uff19.\uff19\uff18\uff12.\uff12\uff14\uff17-\uff12\uff15"
    findings = _inspect(texto)

    assert len(findings) == 1
    
    finding = findings[0]

    assert finding.start == 0
    assert finding.end == 14
    assert finding.matched_type == "cpf"

def test_inspect_cpf_com_invisivel():
    texto = "cpf 529.982\u200b.247-25"
    findings = _inspect(texto)

    assert len(findings) == 1

    finding = findings[0]

    assert finding.start == 4
    assert finding.end == 19

def test_inspect_finding_nao_expoe_cpf_e_com_score():
    findings = _inspect("cpf 529.982.247-25")

    assert len(findings) == 1
    assert findings[0].score == 1.0
    assert "529.982.247-25" not in repr(findings[0])
    assert "52998224725" not in str(findings[0])