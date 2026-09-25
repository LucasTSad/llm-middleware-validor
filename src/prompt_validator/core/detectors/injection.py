import re

from prompt_validator.core.contracts import (
    Category,
    Finding,
    GuardConfig,
    NormalizedText,
    Severity,
)

_SYSTEM_OPEN = re.escape("<|")
_SYSTEM_CLOSE = re.escape("|>")
_SYSTEM_CONTENT = r"[A-Za-z0-9_-]+"

_SYSTEM_PATTERN = _SYSTEM_OPEN + _SYSTEM_CONTENT + _SYSTEM_CLOSE

_BRACKET_OPEN = re.escape("[")
_BRACKET_CLOSE = re.escape("]")
_BRACKET_CONTENT = r"[A-Z][A-Z0-9 _-]*"

_BRACKET_PATTERN = _BRACKET_OPEN + _BRACKET_CONTENT + _BRACKET_CLOSE

_MESSAGE_SYSTEM_PATTERN = re.escape('<message role="system">')
_CLOSING_SYSTEM_PATTERN = re.escape("</system>")

DELIMITER_PATTERN = re.compile(
    _SYSTEM_PATTERN
    + "|"
    + _BRACKET_PATTERN
    + "|"
    + _MESSAGE_SYSTEM_PATTERN
    + "|"
    + _CLOSING_SYSTEM_PATTERN
)


class InjectionDetector:
    name = "injection"

    def inspect(
        self, normalized_text: NormalizedText, config: GuardConfig
    ) -> list[Finding]:
        findings: list[Finding] = []
        for match in DELIMITER_PATTERN.finditer(normalized_text.normalized):
            start, end = normalized_text.to_original_span(match.start(), match.end())

            findings.append(
                Finding(
                    rule_id="injection.delimiter.v1",
                    category=Category.PROMPT_INJECTION,
                    severity=Severity.MEDIUM,
                    start=start,
                    end=end,
                    matched_type="delimiter",
                    score=0.9,
                )
            )

        return findings
