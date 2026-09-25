from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import TypedDict

from prompt_validator.core.contracts import Action, Decision, GuardConfig
from prompt_validator.core.engine import Engine, build_detectors


class CorpusCase(TypedDict):
    id: str
    label: str
    families: list[str]
    text: str
    justification: str


ROOT_DIR = Path(__file__).resolve().parent.parent
CORPUS_PATH = ROOT_DIR / "datasets" / "prompt_injection_corpus.jsonl"
RESULT_PATH = ROOT_DIR / "benchmarks" / "resultados" / "prompt_injection_evaluation.txt"


def load_corpus() -> list[CorpusCase]:
    with CORPUS_PATH.open(encoding="utf-8") as file:
        return [json.loads(line) for line in file if line.strip()]


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(8192), b""):
            digest.update(chunk)

    return digest.hexdigest()


def rule_family(rule_id: str) -> str:
    parts = rule_id.split(".")

    if len(parts) < 2:
        return rule_id

    return parts[1]


def evaluate(cases: list[CorpusCase]) -> str:
    config = GuardConfig(enabled_detectors=("injection",))
    engine = Engine(build_detectors(config), config)

    attacks = [case for case in cases if case["label"] == "ataque"]
    legitimate = [case for case in cases if case["label"] == "legitimo"]

    results: list[tuple[CorpusCase, Decision]] = []

    for case in cases:
        decision = engine.analyze(case["text"])
        results.append((case, decision))

    blocked_attacks: list[tuple[CorpusCase, Decision]] = []
    missed_attacks: list[tuple[CorpusCase, Decision]] = []
    false_positives: list[tuple[CorpusCase, Decision]] = []

    family_results: dict[str, dict[str, int]] = {}
    rule_results: dict[str, dict[str, int]] = {}

    for case, decision in results:
        blocked = decision.action == Action.BLOCK

        if case["label"] == "ataque":
            if blocked:
                blocked_attacks.append((case, decision))
            else:
                missed_attacks.append((case, decision))

            for family in case["families"]:
                result = family_results.setdefault(
                    family,
                    {"total": 0, "blocked": 0},
                )

                result["total"] += 1
                result["blocked"] += int(blocked)

            detected_families = {
                rule_family(finding.rule_id) for finding in decision.findings
            }

            for family in detected_families:
                result = rule_results.setdefault(
                    family,
                    {"cases": 0, "blocked": 0},
                )
                result["cases"] += 1
                result["blocked"] += int(blocked)

        elif blocked:
            false_positives.append((case, decision))

    mitigation_rate = len(blocked_attacks) / len(attacks)
    false_positive_rate = len(false_positives) / len(legitimate)

    attack_family_counts: dict[str, int] = {}

    for case in attacks:
        for family in case["families"]:
            attack_family_counts[family] = attack_family_counts.get(family, 0) + 1

    lines: list[str] = []

    lines.append("AVALIAÇÃO DE PROMPT INJECTION")
    lines.append("=" * 40)
    lines.append("")
    lines.append(f"Corpus: {CORPUS_PATH.relative_to(ROOT_DIR).as_posix()}")
    lines.append(f"Corpus SHA-256: {file_sha256(CORPUS_PATH)}")
    lines.append(f"Casos: {len(cases)}")
    lines.append("Detector habilitado: injection")
    lines.append("")
    lines.append("COMPOSIÇÃO DO CORPUS")
    lines.append("-" * 40)
    lines.append(f"Total: {len(cases)}")
    lines.append(f"Ataques: {len(attacks)}")
    lines.append(f"Legítimos: {len(legitimate)}")
    lines.append("")
    lines.append("Ataques por família:")

    for family, count in sorted(attack_family_counts.items()):
        lines.append(f"  {family}: {count}")

    lines.append("")
    lines.append(
        "Observação: os casos de ataque são multi-label; "
        "a soma das famílias pode exceder o número total de ataques."
    )

    lines.append("")
    lines.append("RESULTADO GERAL")
    lines.append("-" * 40)

    lines.append(
        f"Ataques bloqueados: "
        f"{len(blocked_attacks)}/{len(attacks)} "
        f"({mitigation_rate:.1%})"
    )
    lines.append(
        f"Falsos positivos: "
        f"{len(false_positives)}/{len(legitimate)} "
        f"({false_positive_rate:.1%})"
    )

    lines.append("")
    lines.append("FALSOS NEGATIVOS")
    lines.append("-" * 40)

    if not missed_attacks:
        lines.append("Nenhum.")

    else:
        for case, decision in missed_attacks:
            lines.append(f"  {case['id']}")
            lines.append(f"    ação: {decision.action.value}")

            if decision.findings:
                for finding in decision.findings:
                    lines.append(f"    regra: {finding.rule_id}")
                    lines.append(f"    score: {finding.score:.2f}")

            else:
                lines.append("    findings: nenhum")

    lines.append("")
    lines.append("FALSOS POSITIVOS")
    lines.append("-" * 40)

    if not false_positives:
        lines.append("Nenhum.")

    else:
        for case, decision in false_positives:
            lines.append(f"  {case['id']}")
            lines.append(f"    ação: {decision.action.value}")

            if decision.findings:
                for finding in decision.findings:
                    lines.append(f"    regra: {finding.rule_id}")
                    lines.append(f"    score: {finding.score:.2f}")
            else:
                lines.append("    findings: nenhum")

    lines.append("")
    lines.append("COBERTURA POR FAMÍLIA DO CORPUS")
    lines.append("-" * 40)

    for family, result in sorted(family_results.items()):
        lines.append(
            f"  {family}: {result['blocked']}/{result['total']} casos bloqueados"
        )

    lines.append("")
    lines.append(
        "Esta seção mede cobertura dos casos rotulados com cada família, "
        "não atribuição causal da regra."
    )
    lines.append("")
    lines.append("BLOQUEIOS ATRIBUÍDOS ÀS REGRAS")
    lines.append("-" * 40)

    if not rule_results:
        lines.append("Nenhuma regra produziu findings em ataques.")

    else:
        for family, result in sorted(rule_results.items()):
            lines.append(
                f"  {family}: "
                f"{result['blocked']}/{result['cases']} "
                f"casos com finding da regra"
            )

    lines.append("")
    lines.append(
        "A família nesta seção é derivada do rule_id do Finding; "
        "portanto, representa a regra que efetivamente produziu o sinal."
    )

    return "\n".join(lines)


def main() -> None:
    cases = load_corpus()
    report = evaluate(cases)

    print(report)

    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(
        report + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
