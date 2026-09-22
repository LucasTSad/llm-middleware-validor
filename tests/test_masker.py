import pytest

from prompt_validator.core.contracts import Category, Finding, GuardConfig, MaskMode, Severity
from prompt_validator.core.detectors.pii import PiiDetector
from prompt_validator.core.normalizer import normalize
from prompt_validator.core.masker import mask, rehydrate

def mascarado(texto, findings=None, config=None):
    if config is None:
        config = GuardConfig()

    detector = PiiDetector()

    normalized = normalize(texto, config)

    if findings is None:
        findings = detector.inspect(normalized, config)

    masked_text, replacements = mask(texto, findings, config)

    return masked_text, replacements

def criar_finding(start, end, matched_type):
    return Finding(
        rule_id="test.rule.v1",
        category=Category.PII_DISCLOSURE,
        severity=Severity.MEDIUM,
        start=start,
        end=end,
        matched_type=matched_type,
    )

@pytest.mark.parametrize(
    ("texto", "cpfs"),
    [
        (
            "Meu CPF é 529.982.247-25.",
            ["529.982.247-25"],
        ),
        (
            "CPFs: 529.982.247-25 e 374.735.750-40.",
            ["529.982.247-25", "374.735.750-40"],
        ),
        (
            "Meu CPF 529.982.247-25 aparece novamente: 529.982.247-25.",
            ["529.982.247-25"],
        ),
        (
            "529.982.247-25 está no início.",
            ["529.982.247-25"],
        ),
        (
            "CPF no fim: 529.982.247-25",
            ["529.982.247-25"],
        ),
        (
            "Não existe PII neste texto.",
            [],
        ),
        (
            "João tem café ☕\u200b antes do CPF 529.982.247-25.",
            ["529.982.247-25"],
        ),
    ],
)
def test_mask_rehydrate_round_trip(texto,cpfs):
    masked_text, replacements = mascarado(texto)

    rehydrated = rehydrate(masked_text, replacements)

    assert rehydrated == texto

    for cpf in cpfs:
        assert cpf not in masked_text

    if cpfs:
        assert masked_text != texto
        assert replacements
    else:
        assert masked_text == texto
        assert replacements == {}

def test_mask_reutiliza_placeholder_para_mesmo_valor():
    masked_text, replacements = mascarado("Meu CPF é 529.982.247-25 e é 529.982.247-25.")

    assert masked_text.count("[CPF_1]") == 2
    assert len(replacements) == 1
    assert replacements["[CPF_1]"] == "529.982.247-25"

def test_mask_dois_cpfs_distintos():
    masked_text, replacements = mascarado("Meu CPF é 529.982.247-25 e do meu amigo é 374.735.750-40.")

    assert "[CPF_1]" in masked_text
    assert "[CPF_2]" in masked_text
    assert len(replacements) == 2
    assert replacements["[CPF_1]"] == "529.982.247-25"
    assert replacements["[CPF_2]"] == "374.735.750-40"

def test_mask_irreversivel():
    texto = ("Meu CPF é 529.982.247-25 e do meu amigo é 374.735.750-40.")
    config=GuardConfig(mask_mode=MaskMode.IRREVERSIBLE)

    masked_text, replacements = mascarado(texto, config=config)

    assert masked_text == "Meu CPF é [CPF_1] e do meu amigo é [CPF_2]."
    assert replacements == {}

def test_mask_findings_adjacentes():
    texto = "CPFEMAIL"

    findings = (
        criar_finding(0, 3, "cpf"),
        criar_finding(3, 8, "email"),
    )

    masked_text, replacements = mascarado(texto, findings)

    assert masked_text == "[CPF_1][EMAIL_1]"
    assert replacements["[CPF_1]"] == "CPF"
    assert replacements["[EMAIL_1]"] == "EMAIL"

def test_mask_findings_nos_limites_do_texto():
    texto = "CPF meio EMAIL"

    findings = (
        criar_finding(0, 3, "cpf"),
        criar_finding(9, 14, "email"),
    )

    masked_text, replacements = mascarado(texto, findings)

    assert masked_text == "[CPF_1] meio [EMAIL_1]"
    assert replacements["[CPF_1]"] == "CPF"
    assert replacements["[EMAIL_1]"] == "EMAIL"

def test_mask_preserva_acento_e_zero_width_space():
    texto = "João tem café \u200b antes do CPF 529.982.247-25"

    masked_text, replacements = mascarado(texto)

    assert "João" in masked_text
    assert "café" in masked_text
    assert "\u200b" in masked_text
    assert masked_text == "João tem café \u200b antes do CPF [CPF_1]"

def test_rehydrate_sem_replacements():
    texto = "Meu CPF é [CPF_1]."

    assert rehydrate(texto, {}) == texto

def test_rehydrate_ignora_placeholder_ausente():
    texto = "Meu CPF é [CPF_1]."

    replacements = {"[CPF_2]": "529.982.247-25"}

    assert rehydrate(texto, replacements) == texto

def test_rehydrate_distingue_placeholders_com_numeros_parecidos():

    assert rehydrate("[CPF_10]", {"[CPF_1]": "X", "[CPF_10]": "Y"}) == "Y"

def test_rehydrate_colisao_com_placeholder_escrito_pelo_usuario():
    texto = "O usuário escreveu [CPF_1] e informou o CPF 529.982.247-25."

    masked_text, replacements = mascarado(texto)

    rehydrated = rehydrate(masked_text, replacements)

    assert masked_text == "O usuário escreveu [CPF_1] e informou o CPF [CPF_1]."
    # Limitação conhecida: não é possível distinguir
    # um placeholder gerado pelo masker de um placeholder
    # originalmente escrito pelo usuário.
    assert rehydrated == "O usuário escreveu 529.982.247-25 e informou o CPF 529.982.247-25."