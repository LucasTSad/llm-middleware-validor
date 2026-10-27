import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import TypedDict

from prompt_validator.core.contracts import Decision


class RecordAudit(TypedDict):
    id: str
    time: str
    text_mode: str
    action: str
    token_count: int
    total_findings: int
    findings: list[dict[str, object]]
    estimated_cost_usd: float
    elapsed_ns: int


def record(decision: Decision, file: Path) -> RecordAudit:
    meta_data: RecordAudit = {
        "id": str(uuid.uuid4()),
        "time": datetime.now(UTC).isoformat(),
        "text_mode": "metadados",
        "action": decision.action.value,
        "token_count": decision.token_count,
        "total_findings": len(decision.findings),
        "findings": [
            {
                "rule_id": f.rule_id,
                "category": f.category.value,
                "severity": int(f.severity),
                "matched_type": f.matched_type,
                "start": f.start,
                "end": f.end,
                "score": f.score,
            }
            for f in decision.findings
        ],
        "estimated_cost_usd": decision.estimated_cost_usd,
        "elapsed_ns": decision.elapsed_ns,
    }

    with file.open("a", encoding="utf-8") as arq:
        arq.write(json.dumps(meta_data, ensure_ascii=False) + "\n")

    return meta_data
