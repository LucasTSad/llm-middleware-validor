import re

from prompt_validator.core.contracts import (
    Category,
    Finding,
    GuardConfig,
    NormalizedText,
    Severity,
)


def is_cpf(cpf: str) -> bool:
    if len(cpf) != 11:
        return False

    if not cpf.isascii() or not cpf.isdecimal():
        return False

    if len(set(cpf)) == 1:
        return False

    return _dv_validator(cpf)


def _calculate_dv(digits: str, initial_weight: int) -> int:
    total = 0

    for digit, weight in zip(digits, range(initial_weight, 1, -1)):
        total += int(digit) * weight

    total = total % 11

    if total < 2:
        return 0

    return 11 - total


def _dv_validator(cpf: str) -> bool:
    nine_digits = cpf[0:9]
    two_digits = cpf[-2:]

    dv1 = _calculate_dv(nine_digits, 10)

    cpf_ten = nine_digits + str(dv1)

    dv2 = _calculate_dv(cpf_ten, 11)

    return dv1 == int(two_digits[0]) and dv2 == int(two_digits[1])


_CPF_PATTERN = re.compile(
    r"\b(?:\d{3}\.\d{3}\.\d{3}-\d{2}|\d{11})\b",
    re.ASCII,
)


class PiiDetector:
    name: str = "pii"

    def inspect(
        self, normalized_text: NormalizedText, config: GuardConfig
    ) -> list[Finding]:
        findings: list[Finding] = []

        for match in _CPF_PATTERN.finditer(normalized_text.normalized):
            candidate = match.group()
            cpf = candidate.replace(".", "").replace("-", "")

            if is_cpf(cpf):
                start, end = normalized_text.to_original_span(
                    match.start(), match.end()
                )

                findings.append(
                    Finding(
                        rule_id="pii.cpf.v1",
                        category=Category.PII_DISCLOSURE,
                        severity=Severity.MEDIUM,
                        start=start,
                        end=end,
                        matched_type="cpf",
                        score=1.0,
                    )
                )

        return findings
