from __future__ import annotations

import time

from prompt_validator.core.contracts import (
    Action,
    Category,
    Decision,
    Finding,
    GuardConfig,
)
from prompt_validator.core.detectors.base import Detector
from prompt_validator.core.detectors.injection import InjectionDetector
from prompt_validator.core.detectors.null import NullDetector
from prompt_validator.core.detectors.pii import PiiDetector
from prompt_validator.core.masker import mask
from prompt_validator.core.normalizer import normalize

ACTION_PRIORITY = {
    Action.ALLOW: 0,
    Action.SANITIZE: 1,
    Action.BLOCK: 2,
}


def action_for_finding(finding: Finding, config: GuardConfig) -> Action:
    if finding.severity >= config.block_severity:
        return Action.BLOCK

    if finding.category == Category.PROMPT_INJECTION:
        if finding.score >= config.injection_threshold:
            return Action.BLOCK

        return Action.ALLOW

    if finding.category == Category.PII_DISCLOSURE:
        return Action.SANITIZE

    return Action.BLOCK


def decide_action(findings: list[Finding], config: GuardConfig) -> Action:
    if not findings:
        return Action.ALLOW

    return max(
        (action_for_finding(finding, config) for finding in findings),
        key=ACTION_PRIORITY.__getitem__,
    )


_REGISTRY: dict[str, type[Detector]] = {
    "null": NullDetector,
    "pii": PiiDetector,
    "injection": InjectionDetector,
}


def build_detectors(config: GuardConfig) -> list[Detector]:
    detectors: list[Detector] = []

    for name in config.enabled_detectors:
        if name not in _REGISTRY:
            raise ValueError(
                f"Detector {name} nao encontrado \n",
                f"Detectors disponiveis: {list(_REGISTRY)}"
            )

        classe = _REGISTRY[name]
        detectors.append(classe())

    return detectors


class Engine:
    def __init__(self, detectors: list[Detector], config: GuardConfig) -> None:
        self._config = config
        self._detectors = detectors

    def analyze(self, text: str) -> Decision:
        start = time.perf_counter_ns()

        normalized = normalize(text, self._config)

        all_findings: list[Finding] = []
        for d in self._detectors:
            findings = d.inspect(normalized, self._config)
            all_findings.extend(findings)

        action = decide_action(all_findings, self._config)

        masked_text: str | None = None
        placeholders: dict[str, str] = {}

        if action == Action.SANITIZE:
            maskable_findings = sorted(
                (
                    finding
                    for finding in all_findings
                    if finding.category == Category.PII_DISCLOSURE
                ),
                key=lambda finding: finding.start,
            )

            masked_text, placeholders = mask(
                text, tuple(maskable_findings), self._config
            )

        end = time.perf_counter_ns()
        elapsed_ns = end - start

        return Decision(
            action=action,
            findings=tuple(all_findings),
            elapsed_ns=elapsed_ns,
            sanitized_text=masked_text,
            placeholders=placeholders,
        )
