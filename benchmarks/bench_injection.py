"""
Benchmark do detector de prompt injection.

Execução:
    python benchmarks/bench_injection.py

1. O que este script mede?
   Mede o custo de execução de `InjectionDetector.inspect()` em textos
   de diferentes tamanhos e com diferentes quantidades de marcadores
   de prompt injection.

2. Quais cenários são comparados?
   - Limpo: texto sem marcadores detectáveis.
   - Marcadores: texto contendo aproximadamente 10 delimitadores
     distribuídos ao longo do texto.
   - Colchete: marcadores entre colchetes em densidade aproximada
     de um marcador a cada 30 palavras.

3. Como o custo é medido?
   A normalização ocorre antes da medição e não faz parte do tempo medido.
   Cada entrada já normalizada é processada por `inspect()` N vezes usando
   `perf_counter_ns()`, após 500 iterações de aquecimento. São calculados
   P50, P95 e P99.

4. O que significa custo por caractere?
   É o P50 dividido pelo comprimento REAL do texto medido.
   Representa o custo mediano por caractere da varredura naquele cenário.

5. O que são os custos marginais?
   O custo marginal dos marcadores é calculado pela diferença entre o P50
   do cenário com marcadores e o P50 de um texto limpo com o MESMO tamanho
   real em caracteres, dividida pela quantidade de Findings.

   Dessa forma, a estimativa reduz a contaminação causada pelo aumento
   de tamanho produzido pela inserção dos marcadores.

6. Quais cenários e parâmetros são utilizados?
   São avaliados textos nominais de 100, 1.000, 5.000, 10.000 e 30.000
   caracteres.

   O cenário de marcadores tenta inserir exatamente 10 marcadores,
   respeitando a quantidade de palavras disponível.

   O cenário de colchetes insere um marcador a cada 30 palavras.
   Nos tamanhos que não comportam essa densidade, nenhum marcador é
   inserido e o cenário é mantido apenas para medir o custo da varredura.

7. Quais limitações existem?
   Os cenários são artificiais e não representam a distribuição de
   delimitadores em prompts reais.

   A densidade de um marcador a cada 30 palavras produz um cenário
   deliberadamente carregado, útil para avaliar o custo quando há muitos
   Findings.

   O custo por caractere é uma aproximação do custo da varredura e não
   deve ser interpretado como o custo individual de cada caractere,
   pois o custo total também depende da quantidade de correspondências
   encontradas.

   Os resultados são dependentes do ambiente de execução. Por isso,
   P50 é usado para caracterizar o custo central, enquanto P95 e P99
   ajudam a observar a influência do ambiente.

8. O que as previsões representam?
   As previsões foram registradas antes da execução do benchmark e são
   comparadas explicitamente com os valores medidos no relatório.
"""

import platform
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import TypedDict

from calcular_percentis import calcular_percentis

from prompt_validator.core.contracts import GuardConfig, NormalizedText
from prompt_validator.core.detectors.injection import InjectionDetector
from prompt_validator.core.normalizer import normalize
from prompt_validator.provenance import obter_commit

AQUECIMENTO = 500
N = 10_000

TAMANHOS = (100, 1_000, 5_000, 10_000, 30_000)

TEXTO = (
    "Preciso que voce reorganize essa tabela de excel com os dados "
    "de clientes, e-mails e telefones de forma que os dados sejam "
    "mostrados na primeira coluna e os telefones na segunda."
)

INJECTIONS_MARCADORES = (
    '<message role="system">',
    "</system>",
    "<|system|>",
    "<|end|>",
)

INJECTIONS_COLCHETE = (
    "[OK]",
    "[TODO]",
    "[SYSTEM]",
    "[END SYSTEM]",
)

QUANTIDADE_MARCADORES = 10
A_CADA_N_PALAVRA_LOG = 30

GATILHO_NS_POR_CHAR = 30
NORMALIZER_NS_POR_CHAR = 310

PREVISAO_NS_POR_CHAR = 14
PREVISAO_CUSTO_MARGINAL_US_MIN = 2.0
PREVISAO_CUSTO_MARGINAL_US_MAX = 2.5
PREVISAO_30K_10_MS = 0.44
PREVISAO_30K_LOG_MS = 0.90

CAMINHO = (
    Path(__file__).resolve().parent / "resultados" / "dia_06_injection_N_10_000.txt"
)


class Resultado(TypedDict):
    chars: int
    findings: int
    p50: int
    p95: int
    p99: int
    p50_custo_por_caractere: float


config = GuardConfig()
detector = InjectionDetector()


def criar_texto(base: str, tamanho: int) -> str:
    return (base * ((tamanho // len(base)) + 1))[:tamanho]


def criar_com_quantidade_exata(
    texto: str, itens: tuple[str, ...], quantidade: int
) -> str:
    palavras = texto.split()

    if quantidade <= 0 or not palavras:
        return texto

    quantidade = min(quantidade, len(palavras))

    if quantidade == 1:
        posicoes: set[int] = {max(1, len(palavras) // 2)}
    else:
        posicoes = {
            1 + (i * (len(palavras) - 1)) // (quantidade - 1) for i in range(quantidade)
        }

    resultado = []
    marcador = 0

    for i, palavra in enumerate(palavras, start=1):
        resultado.append(palavra)

        if i in posicoes:
            resultado.append(itens[marcador % len(itens)])
            marcador += 1

    return " ".join(resultado)


def criar_adversarial(texto: str, itens: tuple[str, ...], a_cada_n_palavra: int) -> str:
    palavras = texto.split()
    resultado = []

    for i, palavra in enumerate(palavras, start=1):
        resultado.append(palavra)

        if i % a_cada_n_palavra == 0:
            item = itens[(i // a_cada_n_palavra - 1) % len(itens)]
            resultado.append(item)

    return " ".join(resultado)


def calcular_custo_marginal(
    p50_base: int, p50_cenario: int, quantidade_candidatos: int
) -> float:
    if quantidade_candidatos == 0:
        return 0.0

    return (p50_cenario - p50_base) / quantidade_candidatos


def medir_inspect(normalized: NormalizedText) -> tuple[int, int, int]:
    for _ in range(AQUECIMENTO):
        detector.inspect(normalized, config)

    tempos = []

    for _ in range(N):
        inicio = time.perf_counter_ns()

        detector.inspect(normalized, config)

        fim = time.perf_counter_ns()

        tempos.append(fim - inicio)

    return calcular_percentis(tempos)


resultados: dict[tuple[int, str], Resultado] = {}
marginais = {}

for tamanho in TAMANHOS:
    texto_limpo = criar_texto(TEXTO, tamanho)

    texto_marcadores = criar_com_quantidade_exata(
        texto_limpo, INJECTIONS_MARCADORES, QUANTIDADE_MARCADORES
    )

    texto_colchete = criar_adversarial(
        texto_limpo, INJECTIONS_COLCHETE, A_CADA_N_PALAVRA_LOG
    )

    textos = {
        "limpo": texto_limpo,
        "marcadores": texto_marcadores,
        "colchete": texto_colchete,
    }

    for nome, texto in textos.items():
        normalized = normalize(texto, config)

        findings = detector.inspect(normalized, config)

        p50, p95, p99 = medir_inspect(normalized)

        resultados[tamanho, nome] = {
            "chars": len(texto),
            "findings": len(findings),
            "p50": p50,
            "p95": p95,
            "p99": p99,
            "p50_custo_por_caractere": p50 / len(texto),
        }

        if nome == "limpo":
            assert len(findings) == 0
        elif nome == "marcadores":
            esperado = min(QUANTIDADE_MARCADORES, len(texto_limpo.split()))
            assert len(findings) == esperado
        elif nome == "colchete":
            esperado = len(texto_limpo.split()) // A_CADA_N_PALAVRA_LOG
            assert len(findings) == esperado

    texto_base_marcadores = criar_texto(TEXTO, len(texto_marcadores))
    texto_base_colchete = criar_texto(TEXTO, len(texto_colchete))

    normalized_base_marcadores = normalize(texto_base_marcadores, config)
    normalized_base_colchete = normalize(texto_base_colchete, config)

    findings_base_marcadores = detector.inspect(normalized_base_marcadores, config)
    findings_base_colchete = detector.inspect(normalized_base_colchete, config)

    assert len(findings_base_marcadores) == 0
    assert len(findings_base_colchete) == 0

    p50_base_marcadores, _, _ = medir_inspect(normalized_base_marcadores)
    p50_base_colchete, _, _ = medir_inspect(normalized_base_colchete)

    p50_marcadores = resultados[tamanho, "marcadores"]["p50"]
    p50_colchete = resultados[tamanho, "colchete"]["p50"]

    quantidade_marcadores = resultados[tamanho, "marcadores"]["findings"]
    quantidade_colchete = resultados[tamanho, "colchete"]["findings"]

    custo_marginal_marcadores = calcular_custo_marginal(
        p50_base_marcadores,
        p50_marcadores,
        quantidade_marcadores,
    )
    custo_marginal_colchete = calcular_custo_marginal(
        p50_base_colchete,
        p50_colchete,
        quantidade_colchete,
    )

    marginais[tamanho] = {
        "chars_base_marcadores": len(texto_base_marcadores),
        "chars_base_colchete": len(texto_base_colchete),
        "p50_base_marcadores": p50_base_marcadores,
        "p50_base_colchete": p50_base_colchete,
        "custo_marginal_marcadores": custo_marginal_marcadores,
        "custo_marginal_colchete": custo_marginal_colchete,
    }

commit = obter_commit(Path(__file__).resolve().parent)

linhas_relatorio = [
    "BENCHMARK — DETECTOR DE PROMPT INJECTION",
    "=" * 72,
    "",
    f"Data e Hora: {datetime.now(UTC).isoformat()}",
    f"Commit: {commit}",
    f"Python: {platform.python_version()}",
    f"Plataforma: {platform.platform()}",
    f"Execuções (N): {N}",
    f"Aquecimento: {AQUECIMENTO}",
    f"Tamanhos nominais: {TAMANHOS}",
    f"Gatilho atual: {GATILHO_NS_POR_CHAR} ns/caractere",
    f"Custo normalizer: {NORMALIZER_NS_POR_CHAR} ns/caractere",
    "",
    "PREVISÕES REGISTRADAS ANTES DA MEDIÇÃO:",
    f"- Texto limpo: ~{PREVISAO_NS_POR_CHAR} ns/char",
    "- Custo marginal por marcador: "
    f"~{PREVISAO_CUSTO_MARGINAL_US_MIN:.1f}–"
    f"{PREVISAO_CUSTO_MARGINAL_US_MAX:.1f} µs",
    f"- 30.000 chars + 10 marcadores: ~{PREVISAO_30K_10_MS:.2f} ms",
    f"- 30.000 chars + densidade de log: ~{PREVISAO_30K_LOG_MS:.2f} ms",
    "",
    "RESULTADOS:",
    "",
    "Tamanho | Cenário       | Chars reais | P50 (ns) | "
    "P95 (ns) | P99 (ns) | Findings | P50/char",
    "--------|---------------|-------------|----------|----------|----------|----------|----------",
]

for tamanho in TAMANHOS:
    for nome in ("limpo", "marcadores", "colchete"):
        resultado = resultados[tamanho, nome]

        linhas_relatorio.append(
            f"{tamanho:7d} | "
            f"{nome:13s} | "
            f"{resultado['chars']:11d} | "
            f"{resultado['p50']:8d} | "
            f"{resultado['p95']:8d} | "
            f"{resultado['p99']:8d} | "
            f"{resultado['findings']:8d} | "
            f"{resultado['p50_custo_por_caractere']:8.2f}"
        )

    linhas_relatorio.append("")

linhas_relatorio.extend(
    [
        "COMPARAÇÃO COM O GATILHO",
        "-" * 72,
    ]
)

for tamanho in TAMANHOS:
    resultado = resultados[tamanho, "limpo"]

    razao_gatilho = (resultado["p50_custo_por_caractere"] / GATILHO_NS_POR_CHAR) * 100

    razao_normalizer = (
        resultado["p50_custo_por_caractere"] / NORMALIZER_NS_POR_CHAR
    ) * 100

    linhas_relatorio.append(
        f"{tamanho} chars | "
        f"Detector/gatilho: {razao_gatilho:.2f}% | "
        f"Detector/normalizer: {razao_normalizer:.2f}%"
    )

linhas_relatorio.extend(
    [
        "",
        "CUSTOS MARGINAIS",
        "-" * 72,
        "O baseline utilizado no cálculo marginal possui o mesmo",
        "comprimento real do cenário adversarial.",
        "",
    ]
)

for tamanho in TAMANHOS:
    marginal = marginais[tamanho]

    quantidade_marcadores = resultados[tamanho, "marcadores"]["findings"]
    quantidade_colchete = resultados[tamanho, "colchete"]["findings"]

    linhas_relatorio.append(
        f"{tamanho} chars nominais | "
        f"Marcadores: {quantidade_marcadores} findings | "
        f"Base pareada: {marginal['chars_base_marcadores']} chars | "
        f"Custo marginal: "
        f"{marginal['custo_marginal_marcadores'] / 1000:.2f} µs/marcador"
    )

    if quantidade_colchete > 0:
        linhas_relatorio.append(
            f"{tamanho} chars nominais | "
            f"Colchete: {quantidade_colchete} findings | "
            f"Base pareada: {marginal['chars_base_colchete']} chars | "
            f"Custo marginal: "
            f"{marginal['custo_marginal_colchete'] / 1000:.2f} µs/marcador"
        )
    else:
        linhas_relatorio.append(
            f"{tamanho} chars nominais | "
            "Colchete: nenhum marcador comportado pela densidade "
            "de 1 marcador a cada 30 palavras."
        )

p50_limpo_30k = resultados[30_000, "limpo"]["p50"]
p50_marcadores_30k = resultados[30_000, "marcadores"]["p50"]
p50_colchete_30k = resultados[30_000, "colchete"]["p50"]

ns_por_char_limpo_30k = resultados[30_000, "limpo"]["p50_custo_por_caractere"]

custo_marginal_30k = marginais[30_000]["custo_marginal_marcadores"]

chars_marcadores_30k = resultados[30_000, "marcadores"]["chars"]
chars_colchete_30k = resultados[30_000, "colchete"]["chars"]

linhas_relatorio.extend(
    [
        "",
        "COMPARAÇÃO COM AS PREVISÕES",
        "-" * 72,
        "",
        "1. Texto limpo",
        f"   Previsto: ~{PREVISAO_NS_POR_CHAR} ns/char",
        f"   Medido:   {ns_por_char_limpo_30k:.2f} ns/char",
        "",
        "2. Custo marginal por marcador",
        "   Previsto: "
        f"~{PREVISAO_CUSTO_MARGINAL_US_MIN:.1f}–"
        f"{PREVISAO_CUSTO_MARGINAL_US_MAX:.1f} µs/marcador",
        f"   Medido:   {custo_marginal_30k / 1000:.2f} µs/marcador",
        "",
        "3. Texto nominal de 30.000 chars com 10 marcadores",
        f"   Previsto: ~{PREVISAO_30K_10_MS:.2f} ms",
        f"   Medido:   {p50_marcadores_30k / 1_000_000:.3f} ms",
        f"   Tamanho real medido: {chars_marcadores_30k} chars",
        "",
        "4. Texto nominal de 30.000 chars com densidade de log",
        f"   Previsto: ~{PREVISAO_30K_LOG_MS:.2f} ms",
        f"   Medido:   {p50_colchete_30k / 1_000_000:.3f} ms",
        f"   Tamanho real medido: {chars_colchete_30k} chars",
        "",
    ]
)

linhas_relatorio.extend(
    [
        "OBSERVAÇÕES",
        "-" * 72,
        "A normalização não faz parte da região cronometrada.",
        "O benchmark mede exclusivamente InjectionDetector.inspect().",
        "",
        "O custo por caractere utiliza o comprimento real do texto",
        "cronometado, e não o tamanho nominal solicitado na criação.",
        "",
        "Para o custo marginal, o texto limpo de referência possui",
        "o mesmo número de caracteres do cenário que contém marcadores.",
        "Isso reduz a influência do custo adicional da varredura causada",
        "pelo crescimento do texto durante a inserção dos marcadores.",
        "",
        "No cenário de colchetes, tamanhos pequenos podem não possuir",
        "palavras suficientes para comportar a densidade de um marcador",
        "a cada 30 palavras. Nesses casos, o cenário apresenta zero",
        "Findings e não é utilizado para inferir custo marginal.",
        "",
        "CONCLUSÃO",
        "-" * 72,
        "O benchmark mede separadamente o custo da varredura do detector",
        "e o custo adicional associado à presença de múltiplos Findings.",
        "",
        "Os resultados devem ser combinados com as medições anteriores",
        "do normalizador e dos demais componentes para estimar a latência",
        "total do Engine.",
        "",
    ]
)

relatorio = "\n".join(linhas_relatorio)

print(relatorio)

CAMINHO.parent.mkdir(parents=True, exist_ok=True)
CAMINHO.write_text(relatorio, encoding="utf-8")
