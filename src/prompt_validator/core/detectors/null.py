from __future__ import annotations
from prompt_validator.core.contracts import Finding, GuardConfig


class NullDetector:

    name: str = "null"

    def inspect(self, text: str, config: GuardConfig) -> list[Finding]:
        return []