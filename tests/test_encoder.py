from conftest import FakeEncoder

from prompt_validator.adapters.tiktoken_encoder import build_encoder
from prompt_validator.core.contracts import GuardConfig
from prompt_validator.core.encoder import Encoder


def test_fake_encoder_tem_o_metodo_encode():
    assert isinstance(FakeEncoder(), Encoder)


def test_encoder_real_tem_o_metodo_encode():
    assert isinstance(build_encoder(GuardConfig()), Encoder)


def test_encoder_real_conta_tokens_de_forma_estavel():
    encoder = build_encoder(GuardConfig())

    assert len(encoder.encode("529.982.247-25")) == 7


def test_encoding_name_escolhe_o_vocabulario():
    texto = "Meu CPF e 529.982.247-25"

    o200k = build_encoder(GuardConfig())
    cl100k = build_encoder(GuardConfig(encoding_name="cl100k_base"))

    assert len(o200k.encode(texto)) != len(cl100k.encode(texto))
