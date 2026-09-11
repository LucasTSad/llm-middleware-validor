from __future__ import annotations
from prompt_validator.core.contracts import Finding, GuardConfig, NormalizedText


class NullDetector:

    name: str = "null"

    def inspect(self, normalized_text: NormalizedText, config: GuardConfig) -> list[Finding]:
        return []