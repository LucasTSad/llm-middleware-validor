from __future__ import annotations

from prompt_validator.core.contracts import (Decision, Finding, GuardConfig, Action)
from prompt_validator.core.contracts import Category
from prompt_validator.core.detectors.null import NullDetector
from prompt_validator.core.detectors.base import Detector
from prompt_validator.core.normalizer import normalize

import time

def decide_action(findings: list[Finding], config: GuardConfig) -> Action:
    if findings == []:
        return Action.ALLOW
    
    elif any(f.severity >= config.block_severity
              for f in findings):
        return Action.BLOCK 

    elif any(f.score >= config.injection_threshold and
              f.category == Category.PROMPT_INJECTION
              for f in findings):
            return Action.BLOCK 
    
    elif any(f.category == Category.PII_DISCLOSURE and 
              f.severity < config.block_severity 
              for f in findings ):
            return Action.SANITIZE
    
    return Action.BLOCK


_REGISTRY = {"null" : NullDetector}
def build_detectors(config: GuardConfig) -> list[Detector]:
    detectors: list[Detector] = []

    for name in config.enabled_detectors:
        if name not in _REGISTRY:
            raise ValueError(f"Detector {name} nao encontrado \n Detectors disponiveis: {list(_REGISTRY)}")
        
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

        if action == Action.SANITIZE:
            raise NotImplementedError("mascaramento ainda não implementado")

        end = time.perf_counter_ns()
        elapsed_ns = end - start

        return Decision(action = action, findings = tuple(all_findings), elapsed_ns = elapsed_ns)