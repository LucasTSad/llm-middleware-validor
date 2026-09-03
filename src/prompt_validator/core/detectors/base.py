from __future__ import annotations
from typing import Protocol, runtime_checkable
from prompt_validator.core.contracts import Finding, GuardConfig

@runtime_checkable
class Detector(Protocol):
    name: str

    def inspect(self, text: str, config: GuardConfig) -> list[Finding]:
        ...