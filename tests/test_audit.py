import json

import pytest

from prompt_validator.adapters.audit import record
from prompt_validator.core.contracts import GuardConfig
from prompt_validator.core.engine import Engine, build_detectors


def valores_de_texto(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for valor in obj.values():
            yield from valores_de_texto(valor)
    elif isinstance(obj, list):
        for valor in obj:
            yield from valores_de_texto(valor)


def carregar(caminho):
    linhas = caminho.read_text(encoding="utf-8").splitlines()
    return [json.loads(linha) for linha in linhas]


VOLATEIS = {"id", "time", "elapsed_ns"}


@pytest.fixture
def engine():
    config = GuardConfig(enabled_detectors=("pii",))
    return Engine(build_detectors(config), config)


@pytest.fixture
def caminho(tmp_path):
    return tmp_path / "audit.jsonl"


def test_diretorio_inexistente_falha(tmp_path, engine):
    caminho = tmp_path / "inexistente" / "audit.jsonl"

    with pytest.raises(FileNotFoundError):
        record(engine.analyze("A"), caminho)


def test_cpf_nao_aparece_na_linha_gravada(caminho, engine):
    texto = "Meu CPF e 529.982.247-25."
    record(engine.analyze(texto), caminho)

    linha = caminho.read_text(encoding="utf-8")
    assert "529.982.247-25" not in linha
    assert "52998224725" not in linha


def test_placeholders_nao_aparece_na_linha(caminho, engine):
    texto = "Meu CPF e 529.982.247-25."

    decision = engine.analyze(texto)
    assert decision.placeholders

    record(decision, caminho)
    linha = caminho.read_text(encoding="utf-8")

    assert "placeholders" not in linha


def test_gravacoes_sucessivas_acumulam(caminho, engine):
    record(engine.analyze("A"), caminho)
    record(engine.analyze("B"), caminho)

    linha = caminho.read_text(encoding="utf-8")

    assert len(linha.splitlines()) == 2


def sem_volateis(registro):
    return {k: v for k, v in registro.items() if k not in VOLATEIS}


def test_mesma_entrada_mesmos_campos_de_decisao(caminho, engine):
    texto = "529.982.247-25"
    record(engine.analyze(texto), caminho)
    record(engine.analyze(texto), caminho)

    primeiro, segundo = carregar(caminho)

    assert sem_volateis(primeiro) == sem_volateis(segundo)
    assert primeiro["total_findings"] == 1
    assert primeiro["id"] != segundo["id"]
    assert primeiro["time"] != segundo["time"]


def test_conteudo_do_prompt_nao_aparece(caminho, engine):
    record(engine.analyze("Banana comeu minha pera"), caminho)

    (registro,) = carregar(caminho)
    linha = caminho.read_text(encoding="utf-8")

    assert "banana" not in linha.casefold()
    assert all("banana" not in valor.casefold() for valor in valores_de_texto(registro))


def test_modo_declarado_corresponde_ao_conteudo(caminho, engine):
    record(engine.analyze("Banana 529.982.247-25"), caminho)

    (registro,) = carregar(caminho)
    linha = caminho.read_text(encoding="utf-8")

    assert "banana" not in linha.casefold()
    assert registro["text_mode"] == "metadados"
    assert all("banana" not in valor.casefold() for valor in valores_de_texto(registro))


def test_regressao_ramo_de_sanitizacao_nao_vaza_conteudo(caminho, engine):
    # regressao: o sanitized_text era gravado e vazava PII não detectada.
    # CPF passava, porque o CPF é o tipo mascarado
    texto = "CPF: 529.982.247-25, telefone: (11) 91234-5678, e-mail: test@example.com"
    record(engine.analyze(texto), caminho)

    (registro,) = carregar(caminho)
    linha = caminho.read_text(encoding="utf-8")

    assert "(11) 91234-5678" not in linha
    assert "test@example.com" not in linha
    assert registro["action"] == "sanitize"
