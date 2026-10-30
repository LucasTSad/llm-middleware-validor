import pytest


class FakeEncoder:
    # 1 Token por char, para a contagem ser previsivel no teste
    def encode(self, text: str) -> list[int]:
        return list(range(len(text)))


@pytest.fixture
def encoder() -> FakeEncoder:
    return FakeEncoder()
