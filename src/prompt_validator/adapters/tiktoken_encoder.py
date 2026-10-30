import tiktoken

from prompt_validator.core.contracts import GuardConfig
from prompt_validator.core.encoder import Encoder


def build_encoder(config: GuardConfig) -> Encoder:
    return tiktoken.get_encoding(config.encoding_name)
