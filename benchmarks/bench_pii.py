"""
Benchmark do detector de PII (CPF).

Execução:
    python benchmarks/bench_pii.py

1. O que este script mede?
   Mede o custo de execução de `PiiDetector.inspect()` em textos de
   diferentes tamanhos e com diferentes quantidades de candidatos a CPF.

2. Quais cenários são comparados?
   - Sem candidato: texto sem sequências que correspondam ao formato de CPF.
   - Candidato inválido: texto contendo CPFs que passam pela regex, mas
     são rejeitados pela validação determinística do módulo 11.
   - CPF válido: texto contendo CPFs que passam pela regex e pela
     validação, gerando um `Finding`.

   Os cenários com candidatos utilizam CPFs válidos e inválidos com o
   mesmo formato pontuado, permitindo comparar o custo adicional da
   validação e da criação do `Finding`.

3. Como o custo é medido?
   A normalização ocorre antes da medição e não faz parte do tempo medido.
   Cada entrada já normalizada é processada por `inspect()` N vezes usando
   `perf_counter_ns()`, após 500 iterações de aquecimento. São calculados
   P50, P95 e P99.

4. O que significa custo por caractere?
   É o P50 dividido pelo tamanho do texto de entrada. Representa o custo
   mediano por caractere da varredura naquele cenário, sendo usado
   principalmente para avaliar o custo fixo do detector quando não há
   candidatos.

5. O que são os custos marginais?
   O custo marginal de um candidato rejeitado é calculado pela diferença
   entre o P50 do cenário com candidatos inválidos e o P50 do cenário sem
   candidatos, dividida pela quantidade de candidatos.

   O custo marginal de um candidato aceito é calculado da mesma forma,
   usando o cenário com CPFs válidos. A diferença entre os custos dos
   cenários válido e inválido aproxima o custo adicional de
   `to_original_span` e da criação do `Finding`.

6. Quais cenários e parâmetros são utilizados?
   São avaliados textos de 100, 1.000 e 10.000 caracteres. Nos cenários
   adversariais, um CPF é inserido a cada 5 palavras. São utilizados três CPFs 
   válidos e três inválidos, alternados ciclicamente dentro de seus respectivos cenários.

7. Quais limitações existem?
   Os cenários são artificiais e não representam a distribuição de CPFs
   em prompts reais. A densidade fixa de um CPF a cada 5 palavras produz
   um cenário deliberadamente carregado para medir o custo por candidato.

   O custo por caractere é uma aproximação do custo da varredura e não
   deve ser interpretado como o custo de cada caractere individualmente,
   pois o custo total também depende da quantidade de candidatos
   encontrados e do caminho de validação executado.

   Os resultados são dependentes do ambiente de execução. Por isso,
   P50 é usado para caracterizar o custo do código, enquanto P95 e P99
   ajudam a observar a influência do ambiente.
"""

from datetime import datetime
from pathlib import Path
import platform
import time

from calcular_percentis import calcular_percentis

from prompt_validator.core.normalizer import normalize
from prompt_validator.core.contracts import GuardConfig, NormalizedText
from prompt_validator.core.detectors.pii import PiiDetector, _CPF_PATTERN

AQUECIMENTO = 500
N = 10_000

TEXTO = (
    "Preciso que voce reorganize essa tabela de excel com os dados "
    "de clientes, e-mails e telefones de forma que os dados sejam "
    "mostrados na primeira coluna e os telefones na segunda."
)

CPFS_INVALIDOS = (
    "529.982.247-26",
    "374.735.750-41",
    "779.302.530-08",
)

CPFS_VALIDOS = (
    "529.982.247-25",
    "374.735.750-40",
    "779.302.530-07",
)

TAMANHOS = (100, 1_000, 10_000)

A_CADA_N_PALAVRA = 5

GATILHO_NS_POR_CHAR = 30
GATILHO_ORIGINAL_NS_POR_CHAR = 155
NORMALIZER_NS_POR_CHAR = 310

CAMINHO = Path("benchmarks/resultados/dia_04_pii_N_10_000.txt")

config = GuardConfig()
detector = PiiDetector()

def criar_texto(base: str, tamanho: int) -> str:
    return (base * ((tamanho // len(base)) + 1))[:tamanho]

def criar_adversarial(texto: str, itens: tuple[str, ...], a_cada_n_palavra: int) -> str:
    palavras = texto.split()
    resultado = []

    for i,palavra in enumerate(palavras, start = 1):
        resultado.append(palavra)

        if i % a_cada_n_palavra == 0:
            item = itens[(i // a_cada_n_palavra - 1) % len(itens)]
            resultado.append(item)

    return " ".join(resultado)

def calcular_custo_marginal(p50_base: int, p50_cenario: int, quantidade_candidatos: int) -> float:
    return (p50_cenario - p50_base) / quantidade_candidatos

texto_invalido = criar_adversarial(
    TEXTO,
    CPFS_INVALIDOS,
    A_CADA_N_PALAVRA,
)

texto_valido = criar_adversarial(
    TEXTO,
    CPFS_VALIDOS,
    A_CADA_N_PALAVRA,
)

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

resultados = {}
for tamanho in TAMANHOS:
    textos = {
        "sem_candidato": criar_texto(TEXTO, tamanho),
        "candidato_invalido": criar_texto(texto_invalido, tamanho),
        "cpf_valido": criar_texto(texto_valido, tamanho),
    }

    for nome,texto in textos.items():
        candidatos = _CPF_PATTERN.findall(texto)

        normalized = normalize(texto,config)

        findings = detector.inspect(normalized, config)

        p50, p95, p99 = medir_inspect(normalized)

        resultados[tamanho, nome] = {
            "chars": len(texto),
            "candidatos": len(candidatos),
            "findings": len(findings),
            "p50": p50,
            "p95": p95,
            "p99": p99,
            "p50_custo_por_caractere": p50 / len(texto)
        }

    p50_sem_candidato = resultados[tamanho, "sem_candidato"]["p50"]
    p50_valido = resultados[tamanho, "cpf_valido"]["p50"]
    p50_invalido = resultados[tamanho, "candidato_invalido"]["p50"]

    candidatos_validos = resultados[tamanho, "cpf_valido"]["candidatos"]
    candidatos_invalidos = resultados[tamanho, "candidato_invalido"]["candidatos"]

    resultados[tamanho, "marginais"] = {
        "custo_marginal_invalido": calcular_custo_marginal(p50_sem_candidato, p50_invalido, candidatos_invalidos),
        "custo_marginal_valido": calcular_custo_marginal(p50_sem_candidato, p50_valido, candidatos_validos),
        "custo_marginal_valido_invalido":  calcular_custo_marginal(p50_invalido, p50_valido, candidatos_validos)
    }

linhas_relatorio = [
    f"Data e Hora: {datetime.now()}",
    f"Python: {platform.python_version()}",
    f"Plataforma: {platform.platform()}",
    f"Execuções (N): {N}",
    f"Aquecimento: {AQUECIMENTO}",
    f"Tamanhos: {TAMANHOS}",
    f"CPFs inválidos: {CPFS_INVALIDOS}",
    f"CPFs válidos: {CPFS_VALIDOS}",
    f"Injeção: 1 CPF a cada {A_CADA_N_PALAVRA} palavras",
    f"Gatilho ADR Original: {GATILHO_ORIGINAL_NS_POR_CHAR} ns/caractere",
    f"Gatilho ADR Atual: {GATILHO_NS_POR_CHAR} ns/caractere",
    f"Custo normalizer: {NORMALIZER_NS_POR_CHAR} ns/caractere",
    "",
    "Resultados:",
]

for tamanho in TAMANHOS:
    for nome in ("sem_candidato", "candidato_invalido", "cpf_valido"):
        resultado = resultados[tamanho, nome]

        linhas_relatorio.append(
            f"{tamanho} chars | {nome} | "
            f"P50: {resultado['p50']} ns | "
            f"P95: {resultado['p95']} ns | "
            f"P99: {resultado['p99']} ns | "
            f"Candidatos: {resultado['candidatos']} | "
            f"Findings: {resultado['findings']} | "
            f"P50/caractere: {resultado['p50_custo_por_caractere']:.2f} ns")

        if nome == "sem_candidato":    
            razao_gatilho = (
                  resultado["p50_custo_por_caractere"] / GATILHO_NS_POR_CHAR
              ) * 100
            razao_normalizer = (
                  resultado["p50_custo_por_caractere"] / NORMALIZER_NS_POR_CHAR
              ) * 100

            linhas_relatorio.append(
                f"Razão detector/gatilho atual: {razao_gatilho:.2f}% | "
                f"Razão detector/normalizador: {razao_normalizer:.2f}%")
    
    marginais = resultados[tamanho, "marginais"]

    linhas_relatorio.append(
        f"Marginais: "
        f"custo por candidato rejeitado: "
        f"{marginais['custo_marginal_invalido'] / 1000:.2f} µs | "
        f"custo por candidato aceito (Finding): "
        f"{marginais['custo_marginal_valido'] / 1000:.2f} µs | "
        f"custo de aceitar vs rejeitar: "
        f"{marginais['custo_marginal_valido_invalido'] / 1000:.2f} µs"
    )

relatorio = "\n".join(linhas_relatorio)

print(relatorio)

CAMINHO.parent.mkdir(parents = True, exist_ok = True)
CAMINHO.write_text(relatorio, encoding = "utf-8")