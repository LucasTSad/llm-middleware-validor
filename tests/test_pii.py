import pytest 

from prompt_validator.core.detectors.pii import is_cpf

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
    ],
)
def test_is_cpf_resto_zero(cpf):
    assert is_cpf(cpf) is True

@pytest.mark.parametrize(
    "cpf",
    [
        "10000000108", # DV1: resto == 1
        "10000002810", # DV2: resto == 1
    ],
)
def test_is_cpf_resto_um(cpf):
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