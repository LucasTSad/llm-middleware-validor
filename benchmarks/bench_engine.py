"""
Benchmark do Engine.

Execução:
    python benchmarks/bench_engine.py

1. O que este script mede?
    O overhead estrutural do pipeline: o custo de existir, sem nenhuma detecção real.

2. Por que medir isso agora?
    Para separar o custo do pipeline do custo das regex, que serão medidas depois.

3. O que cada medição inclui?
    A externa cobre a chamada completa, incluindo a construção e validação da Decision.
    A interna é o que o próprio engine cronometra: execução dos detectores e decisão de
    política, terminando antes da Decision ser construída.

4. Que limitações a medição tem?
    Relógio com granularidade de 100 ns no Windows: medições de poucos tiques têm erro
    relativo alto. Máquina local, processo único, não é o ambiente Lambda.

5. Por que percentis em vez de média?
    A distribuição de latência não é simétrica: a maioria das execuções se concentra em
    torno de um valor baixo e uma minoria se estende por uma cauda longa à direita,
    causada por eventos esporádicos do ambiente de execução.
    A média fica entre os dois grupos sem descrever nenhum deles.
    Percentis descrevem a distribuição diretamente: o p50 informa o comportamento
    típico, e o p95 e o p99 informam o comportamento da cauda, que é o que
    determina a experiência da fração pior atendida das requisições.
"""

import platform
import time
from datetime import UTC, datetime
from pathlib import Path

from calcular_percentis import calcular_percentis

from prompt_validator.core.contracts import GuardConfig
from prompt_validator.core.engine import Engine, build_detectors

AQUECIMENTO = 500
N = 10_000
TEXTO = (
    "Preciso que você reorganize essa tabela de excel com os cpf: 123.456.789-00,"
    " 321.654.987-00 e 987.654.321-00 e e-mails: sad@gmail.com , bem@gmail.com"
    " e joo@gmail.com e telefones: 11 1234-5678 , 22 9876-5432 e 33 5555-6666"
    " de forma que os cpf e e-mails sejam mostrados na primeira coluna e os"
    " telefones na segunda."
)
CAMINHO = Path("benchmarks/resultados/dia_02_null.txt")


config = GuardConfig(enabled_detectors=("null",))
detectores = build_detectors(config)
engine = Engine(detectores, config)

for _ in range(AQUECIMENTO):
    engine.analyze(TEXTO)

tempo_externo = []
tempo_interno = []
for _ in range(N):
    inicio = time.perf_counter_ns()
    decision = engine.analyze(TEXTO)
    fim = time.perf_counter_ns()
    tempo_externo.append(fim - inicio)
    tempo_interno.append(decision.elapsed_ns)


p50_int, p95_int, p99_int = calcular_percentis(tempo_interno)
p50_ext, p95_ext, p99_ext = calcular_percentis(tempo_externo)

diferenca_p95 = p95_ext - p95_int

linhas_relatorio = [
    f"Data e Hora: {datetime.now(UTC).isoformat()}",
    f"Python: {platform.python_version()}",
    f"Plataforma: {platform.platform()}",
    f"Execuções (N): {N}",
    f"Aquecimento: {AQUECIMENTO}",
    f"Detectores Ativos: {config.enabled_detectors}",
    f"Tamanho do Texto: {len(TEXTO)} caracteres",
    "",
    "Limitações: Granularidade de relógio (~100ns Windows) e ambiente local de",
    " processo único. Avaliação de Meta: A latência máxima aceitável é de 15 ms"
    " no P95.",
    "",
    f"Tempo Externo -> P50: {p50_ext} ns ({p50_ext / 1e6:.4f} ms) | ",
    f"P95: {p95_ext} ns ({p95_ext / 1e6:.4f} ms) | ",
    f"P99: {p99_ext} ns ({p99_ext / 1e6:.4f} ms)",
    f"Tempo Interno -> P50: {p50_int} ns ({p50_int / 1e6:.4f} ms) | ",
    f"P95: {p95_int} ns ({p95_int / 1e6:.4f} ms) | ",
    f"P99: {p99_int} ns ({p99_int / 1e6:.4f} ms)",
    f"Diferença no P95: {diferenca_p95} ns ({diferenca_p95 / 1e6:.4f} ms)",
    "",
    "Interpretação: A diferença no P95 reflete o custo de construir e validar o objeto "
    "Decision, representando a maior parte do overhead estrutural do pipeline.",
]

relatorio = "\n".join(linhas_relatorio)

print(relatorio)

CAMINHO.parent.mkdir(parents=True, exist_ok=True)
CAMINHO.write_text(relatorio, encoding="utf-8")
