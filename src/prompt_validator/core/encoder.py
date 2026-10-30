from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class Encoder(Protocol):
    def encode(self, text: str) -> list[int]: ...
