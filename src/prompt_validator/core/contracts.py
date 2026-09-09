from __future__ import annotations

from enum import IntEnum, StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

class Severity(IntEnum):

    LOW = 10
    MEDIUM = 20
    HIGH = 30
    CRITICAL = 40

class Category(StrEnum): 

    PII_DISCLOSURE = "LLM06_SENSITIVE_INFORMATION_DISCLOSURE"
    PROMPT_INJECTION = "LLM01_PROMPT_INJECTION"
    BUDGET_EXCEEDED = "COST_BUDGET_EXCEEDED"

class Action(StrEnum):

    ALLOW = "allow"
    SANITIZE = "sanitize"
    BLOCK = "block"

class MaskMode(StrEnum):

    IRREVERSIBLE = "irreversible"
    REVERSIBLE = "reversible"

class Finding(BaseModel):

    model_config = ConfigDict(frozen=True)

    rule_id: str = Field(description = "Identificador estavel da regra, ex: 'pii.cpf.v1'")
    category: Category
    severity: Severity
    start: int = Field(ge = 0, description = "Indice inicial no texto original")
    end: int = Field(gt = 0, description = "Indice final, exclusivo")
    matched_type: str = Field(description = "Tipo concreto, ex: 'cpf', 'api_key'")
    score: float = Field(default = 1.0, ge = 0.0, le = 1.0)

    @model_validator(mode = "after")
    def validate_span(self) -> Self:
        if self.end <= self.start:
            raise ValueError (f"span invalido: end ({self.end}) deve ser maior que start ({self.start})")
        return self

class NormalizedText(BaseModel):

    model_config = ConfigDict(frozen=True)

    original: str
    normalized: str
    offset_map: tuple[int, ...]

    @model_validator(mode = "after")
    def validate_offset_map(self) -> Self:
        if len(self.offset_map) != len(self.normalized):
            raise ValueError(f"Offset_map tem tamanho ({len(self.offset_map)}), porem o normalized tem ({len(self.normalized)})")
        
        if self.offset_map:
            limit = len(self.original)
            out = [x for x in self.offset_map if not 0 <= x < limit]
            if out:
                raise ValueError(f"Offset_map tem valores invalidos: {out[:5]}, enquanto o original tem {limit} caracteres, indices invalidos: 0 .. {limit - 1}")

        for i in range(len(self.offset_map) - 1):
            if self.offset_map[i] > self.offset_map[i + 1]:
                raise ValueError(f"Offset_map nao eh crescente na posicao {i}: {self.offset_map[i]} > {self.offset_map[i + 1]}")
            
        return self

class Decision(BaseModel):

    action: Action
    findings: tuple[Finding, ...] = ()

    sanitized_text: str | None = Field(
        default = None,
        description = "Texto ja mascarado. Preenchido apenas quando action == SANITIZE"
    )
    
    placeholders: dict[str, str] = Field(
        default_factory = dict,
        description = (
            "Mapa placeholder -> valor original, usado para re-hidratar a resposta "
            "da LLM no modo reversivel. CONTEM DADO SENSIVEL: vive apenas em "
            "memoria, durante a requisicao. Nunca serializar, logar ou persistir."
        ),
        exclude = True
    )

    token_count: int = Field(default = 0, ge = 0)
    estimated_cost_usd: float = Field(default = 0.0, ge = 0.0)
    elapsed_ns: int = Field(default = 0, ge = 0)

    @model_validator(mode = "after")
    def validate_coherence(self) -> Self:
        if self.action is Action.SANITIZE and self.sanitized_text is None:
            raise ValueError("sanitized_text deve ser preenchido quando action == SANITIZE")
        elif self.action is Action.BLOCK and self.sanitized_text is not None:
            raise ValueError("sanitized_text deve ser None quando action == BLOCK")
        elif self.action is Action.BLOCK and not self.findings:
            raise ValueError("findings nao pode ser vazio quando action == BLOCK")
        return self

    @property
    def elapsed_ms(self) -> float:
        return self.elapsed_ns / 1_000_000

class GuardConfig(BaseModel):

    model_config = ConfigDict(frozen = True)

    injection_threshold: float = Field(default = 0.7, ge = 0.0, le = 1.0)
    block_severity: Severity = Severity.HIGH
    max_tokens: int = Field(default = 8_000, gt = 0)
    mask_mode: MaskMode = MaskMode.REVERSIBLE

    encoding_name: str = Field(default = "o200k_base")
    price_per_1k_tokens_usd: float = Field(default = 0.0, ge = 0.0)

    enabled_detectors: tuple[str, ...] = ("budget", "pii", "injection")