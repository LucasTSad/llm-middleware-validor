import pytest

from prompt_validator.core.contracts import GuardConfig
from prompt_validator.core.normalizer import normalize


def test_normalizer_ascii_puro():
    texto = "abc123"
    resultado = normalize(texto, GuardConfig())

    assert resultado.original == texto
    assert resultado.normalized == "abc123"
    assert resultado.offset_map == (0,1,2,3,4,5)

def test_normalizer_flag_desligada_preserva_invisiveis():
    texto = "ig\u200bnore"
    resultado = normalize(texto, GuardConfig(normalize_input = False))

    assert resultado.original == texto
    assert resultado.normalized == texto
    assert "\u200b" in resultado.normalized
    assert resultado.offset_map == (0,1,2,3,4,5,6)

def test_normalizer_texto_vazio():
    resultado = normalize("", GuardConfig())

    assert resultado.original == ""
    assert resultado.normalized == ""
    assert resultado.offset_map == ()


def test_normalizer_texto_invisivel_no_meio():
    texto = "ig\u200bnore"
    resultado = normalize(texto, GuardConfig())

    assert resultado.original == texto
    assert resultado.normalized == "ignore"
    assert "\u200b" not in resultado.normalized
    assert resultado.offset_map == (0,1,3,4,5,6)

@pytest.mark.parametrize(
    "code_point", 
    [
        "\u200b",  # ZERO WIDTH SPACE
        "\ufeff",  # ZERO WIDTH NO-BREAK SPACE
        "\u00ad",  # SOFT HYPHEN
        "\u202e",  # RIGHT-TO-LEFT OVERRIDE
        "\u2060",  # WORD JOINER
    ]
)
def test_normalizer_remove_code_points(code_point):
    texto = f"ig{code_point}nore"
    resultado = normalize(texto, GuardConfig())

    assert resultado.original == texto
    assert resultado.normalized == "ignore"
    assert code_point not in resultado.normalized
    assert resultado.offset_map == (0,1,3,4,5,6)

def test_normalizer_invisivel_no_fim():
    texto = "ignore\u200b"
    resultado = normalize(texto, GuardConfig())

    assert resultado.original == texto
    assert resultado.normalized == "ignore"
    assert "\u200b" not in resultado.normalized
    assert resultado.offset_map == (0,1,2,3,4,5)
    assert 6 not in resultado.offset_map

def test_normalizer_com_caracteres_especiais(): #'a½b'
    texto = "a" + "\u00bd" + "b"
    resultado = normalize(texto, GuardConfig())

    assert resultado.original == texto
    assert resultado.normalized == "a1\u20442b"
    assert resultado.offset_map == (0,1,1,1,2)

def test_normalizer_fullwidth():
    texto = "\uff49\uff47\uff4e\uff4f\uff52\uff45"
    resultado = normalize(texto, GuardConfig())

    assert resultado.original == texto
    assert resultado.normalized == "ignore"
    assert resultado.offset_map == (0,1,2,3,4,5)

@pytest.mark.parametrize(
    "entradas", 
    [
        "",
        "abc123",
        "ig\u200bnore",
        "a\u00bd" + "b",
        "\uff49\uff47\uff4e\uff4f\uff52\uff45",
    ]
)

def test_normalizer_idempotencia(entradas):
    primeira = normalize(entradas, GuardConfig())
    segunda = normalize(primeira.normalized, GuardConfig())

    assert segunda.normalized == primeira.normalized
    assert segunda.offset_map == tuple(range(len(primeira.normalized)))

@pytest.mark.parametrize(
    "texto",
    [
        "",
        "abc123",
        "ig\u200bnore",
        "ignore\u200b",
        "a\u00bd" + "b",
        "\uff49\uff47\uff4e\uff4f\uff52\uff45",
    ],
)
def test_normalizer_tamanho_mapa(texto):
    resultado = normalize(texto, GuardConfig())

    assert len(resultado.offset_map) == len(resultado.normalized)


def test_normalizer_mapeia_expansao_e_remocao():
    texto = "a\u00bd\u200bb"

    resultado = normalize(texto, GuardConfig())

    assert resultado.original == texto
    assert resultado.normalized == "a1\u20442b"
    assert resultado.offset_map == (0, 1, 1, 1, 3)