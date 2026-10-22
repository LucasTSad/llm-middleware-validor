import re
from typing import NamedTuple

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


class RuleSpec(NamedTuple):
    family: str
    rule_id: str
    pattern: re.Pattern[str]
    score: float
    severity: Severity


_SPECS: tuple[RuleSpec, ...] = (
    RuleSpec(
        family="delimiter",
        rule_id="injection.delimiter.v1",
        pattern=DELIMITER_PATTERN,
        score=0.9,
        severity=Severity.MEDIUM,
    ),
)


class InjectionDetector:
    name = "injection"

    def inspect(
        self, normalized_text: NormalizedText, config: GuardConfig
    ) -> list[Finding]:
        findings: list[Finding] = []
        for spec in _SPECS:
            for match in spec.pattern.finditer(normalized_text.normalized):
                start, end = normalized_text.to_original_span(
                    match.start(), match.end()
                )

                findings.append(
                    Finding(
                        rule_id=spec.rule_id,
                        category=Category.PROMPT_INJECTION,
                        severity=spec.severity,
                        start=start,
                        end=end,
                        matched_type=spec.family,
                        score=spec.score,
                    )
                )
        findings.sort(key=lambda finding: finding.start)

        return findings
