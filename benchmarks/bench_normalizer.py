"""
Benchmark do normalizador.

Execução:
    python benchmarks/bench_normalizer.py

1. O que este script mede?
   Mede o custo de execução de `normalize()` em textos de diferentes
   tamanhos e com diferentes características de entrada.

2. Quais cenários são comparados?
   - ASCII: texto sem caracteres que exigem transformação.
   - Invisíveis: texto contendo ~20% de caracteres removíveis.
   - NFKC: texto contendo caracteres que exigem normalização NFKC,
     incluindo casos de expansão.

3. Como o custo é medido?
   Cada entrada é normalizada N vezes usando `perf_counter_ns()`.
   São calculados P50, P95 e P99.

4. O que significa custo por caractere?
   É o P95 dividido pelo tamanho do texto de entrada.
   Portanto, representa o custo por caractere processado na entrada,
   e não por caractere produzido na saída.

5. Quais limitações existem?
   Os cenários artificiais não representam a distribuição de textos
   reais. A taxa de 20% é fixa e os casos de remoção e expansão NFKC
   possuem custos diferentes, por isso são medidos separadamente.
"""

from datetime import datetime
from pathlib import Path
import platform
import random
import time

from calcular_percentis import calcular_percentis

from prompt_validator.core.normalizer import normalize
from prompt_validator.core.contracts import GuardConfig

AQUECIMENTO = 500
N = 10_000

TEXTO =  ("Preciso que voce reorganize essa tabela de excel com os cpf: 123.456.789-00, 321.654.987-00 e 987.654.321-00" 
" e e-mails: sad@gmail.com , bem@gmail.com e joo@gmail.com e telefones: 11 1234-5678 , 22 9876-5432 e 33 5555-6666 de" 
" forma que os cpf e e-mails sejam mostrados na primeira coluna e os telefones na segunda.")

TAMANHOS = (100, 1_000, 10_000)

CAMINHO = Path("benchmarks/resultados/dia_03_normalizer.txt")

config = GuardConfig()

INVISIVEIS = ("\u200b", "\ufeff", "\u00ad", "\u202e", "\u2060")
NFKC_CARACTERES = ("Ａ","Ｂ","Ｃ","½","ﬁ")
TAXA_SUBSTITUICAO = 20

semente = 42
random.seed(semente)

def criar_texto(base: str, tamanho: int) -> str:
    return (base * ((tamanho // len(base)) + 1))[:tamanho]

def criar_adversarial(codigo : tuple[str, ...], taxa: int, texto: str) -> str:
    caracteres = []

    for caractere in texto:
        if random.randrange(100) < taxa:
            caracteres.append(random.choice(codigo))
        else:
            caracteres.append(caractere)

    return "".join(caracteres)

def medir_normalizacao(texto: str, config: GuardConfig) -> tuple[int, int, int]:

    for _ in range(AQUECIMENTO):
        normalize(texto, config)

    tempos = []

    for _ in range(N):
        inicio = time.perf_counter_ns()
        normalize(texto, config)
        fim = time.perf_counter_ns()

        tempos.append(fim - inicio)

    return calcular_percentis(tempos)

textos = {}
for tamanho in TAMANHOS:
    textos_ascii = criar_texto(TEXTO, tamanho)
    texto_invisiveis = criar_adversarial(INVISIVEIS, TAXA_SUBSTITUICAO, textos_ascii)
    texto_nfkc = criar_adversarial(NFKC_CARACTERES, TAXA_SUBSTITUICAO, textos_ascii)

    textos[tamanho] = {
        "ascii": textos_ascii,
        "invisiveis": texto_invisiveis,
        "nfkc": texto_nfkc
    }

resultados = {}
for tamanho, variantes in textos.items():
    resultados[tamanho] = {}

    for nome, texto in variantes.items():
        p50, p95, p99 = medir_normalizacao(texto, config)

        resultados[tamanho][nome] = {
            "p50": p50,
            "p95": p95,
            "p99": p99,
            "custo_por_caractere_por_entrada": p95 / len(texto)
        }

for tamanho in TAMANHOS:
    p95_ascii = resultados[tamanho]["ascii"]["p95"]
    p95_invisiveis = resultados[tamanho]["invisiveis"]["p95"]
    p95_nfkc = resultados[tamanho]["nfkc"]["p95"]

    resultados[tamanho]["razao_invisiveis"] = p95_invisiveis / p95_ascii
    resultados[tamanho]["razao_nfkc"] = p95_nfkc / p95_ascii

linhas_relatorio = [
    f"Data e Hora: {datetime.now()}",
    f"Python: {platform.python_version()}",
    f"Plataforma: {platform.platform()}",
    f"Execuções (N): {N}",
    f"Aquecimento: {AQUECIMENTO}",
    f"Taxa de substituição: {TAXA_SUBSTITUICAO}%",
    f"Semente aleatória: {semente}",
    "",
    "Resultados:",
]

for tamanho in TAMANHOS:
    for nome in ("ascii", "invisiveis", "nfkc"):
        resultado = resultados[tamanho][nome]

        linhas_relatorio.append(
            f"{tamanho} chars | {nome} | "
            f"P50: {resultado['p50']} ns | "
            f"P95: {resultado['p95']} ns | "
            f"P99: {resultado['p99']} ns | "
            f"P95/caractere: "
            f"{resultado['custo_por_caractere_por_entrada']:.2f} ns"
        )

    linhas_relatorio.append(
        f"Razão invisiveis/ASCII: "
        f"{resultados[tamanho]['razao_invisiveis']:.2f}x"
    )

    linhas_relatorio.append(
        f"Razão NFKC/ASCII: "
        f"{resultados[tamanho]['razao_nfkc']:.2f}x"
    )

p50_comparacao, p95_comparacao, p99_comparacao = medir_normalizacao(TEXTO, config)

linhas_relatorio.extend([
    "",
    "Comparação com o dia 2:",
    f"Tamanho do TEXTO: {len(TEXTO)} caracteres",
    "Dia 2 - P95 pipeline sem normalização: 4,1 µs",
    "(fonte: benchmarks/resultados/dia_02_null.txt, commit bca6ff8)",
    (
        f"Dia 3 - P95 normalização isolada: "
        f"{p95_comparacao} ns ({p95_comparacao / 1e3:.2f} µs)"
    ),
    (
        f"Estimativa P95 pipeline com normalização: "
        f"{4.1 + p95_comparacao / 1e3:.2f} µs"
    ),
])

relatorio = "\n".join(linhas_relatorio)

print(relatorio)

CAMINHO.parent.mkdir(parents = True, exist_ok = True)
CAMINHO.write_text(relatorio, encoding = "utf-8")