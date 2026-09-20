# ADR 0004 — Detecção de PII em dois estágios

**Status:** Aceito

**Data:** 17/09/2026

## Contexto

A detecção de CPF não pode depender exclusivamente de uma expressão regular. Uma regex que procure 11 dígitos identifica apenas uma sequência numérica com esse tamanho, e não necessariamente um CPF. Telefones com DDD, números de pedidos e outros identificadores também podem possuir 11 dígitos, aumentando a possibilidade de falsos positivos quando somente o formato é considerado.

A normalização definida no ADR 0003 reduz parte dos vetores de obfuscação Unicode. A normalização NFKC converte caracteres fullwidth, como `５`, para `5`, mas não converte dígitos árabe-índicos, como `٥`. Como o `\d` do Python pode reconhecer diferentes categorias de dígitos Unicode, a normalização isoladamente não é suficiente para definir quais caracteres devem ser considerados candidatos a CPF.

O resultado da detecção será representado por um `Finding`, que pode ser enviado para o DynamoDB para fins de auditoria. O `Finding` não deve carregar o valor do CPF detectado, mas apenas informações necessárias para identificar o tipo de ocorrência e sua posição no texto original.

A normalização já representa um custo mensurável no pipeline, conforme os resultados do ADR 0003. A detecção deve, portanto, evitar trabalho desnecessário, mantendo a expressão regular compilada e realizando a validação determinística somente sobre os candidatos encontrados.

## Decisão

A detecção de CPF será realizada em dois estágios:

1. **Detecção de candidatos por expressão regular:** identifica sequências que possuem um dos formatos de CPF suportados.
2. **Validação determinística:** cada candidato encontrado é normalizado para apenas dígitos e validado pelo algoritmo de módulo 11, com rejeição adicional de sequências formadas por um único dígito repetido.

Somente candidatos aprovados pelos dois estágios gerarão um `Finding`.

A expressão regular será compilada no carregamento do módulo e utilizará `re.ASCII`. A implementação está em `src/prompt_validator/core/detectors/pii.py`.

Os offsets encontrados no texto normalizado serão convertidos para posições do texto original por meio de `to_original_span`, conforme o contrato definido no ADR 0003.

## Subdecisões

| Decisão                                                             | Alternativa descartada                             | Motivo                                                                                                                    |
| ------------------------------------------------------------------- | -------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| Regex compilada no import com `re.ASCII`                            | `\d` padrão / compilar por chamada                 | Dígitos árabe-índicos não são convertidos pelo NFKC; a compilação por chamada adicionaria custo desnecessário             |
| Dois formatos: `999.999.999-99` e 11 dígitos nus                    | Suportar apenas um formato ou formatos com espaços | Representam os formatos atualmente suportados; espaços são adiados até existir necessidade                                |
| `\b` aplicado às duas alternativas por meio de grupo não capturante | `\b` somente na primeira alternativa               | A precedência de `\|` poderia permitir que a alternativa de 11 dígitos casasse dentro de outro número                     |
| Validação por módulo 11 + rejeição de dígitos repetidos             | Somente módulo 11                                  | Sequências como `11111111111` passam pelo cálculo de módulo 11                                                            |
| Candidato com DV inválido é descartado                              | Emitir `Finding` com score baixo                   | Evita tratar números que apenas possuem formato semelhante a CPF; atualmente `decide_action` não utiliza `score` para decisões de PII |
| `score = 1.0`                                                       | `score = 0.5`                                      | O candidato passou pelo formato e pela validação determinística; o score é informativo para PII no estado atual                    |
| `Severity.MEDIUM`                                                   | `Severity.HIGH`                                    | `HIGH` atingiria `block_severity` e resultaria em bloqueio; CPF deve seguir o fluxo de sanitização                        |
| `Finding` contém posições, tipo e `rule_id`, sem o valor detectado  | Incluir o CPF no `Finding`                         | Evita que o mecanismo de auditoria carregue ou exponha a própria PII detectada                                            |
| Posições traduzidas com `to_original_span`                          | Utilizar posições do texto normalizado             | O contrato do `Finding` utiliza posições no texto original                                                                |
| `rule_id = "pii.cpf.v1"`                                            | Identificador sem versão                           | Permite alterar posteriormente a regra sem confundir ocorrências produzidas por versões diferentes                        |
| Limpeza de pontuação realizada no `inspect`                         | Remover `.` e `-` no normalizer                    | Mantém a normalização geral fiel ao texto e deixa a interpretação específica do CPF no detector                           |

## Consequências

### Ganhos

* A validação determinística reduz falsos positivos em relação à identificação baseada somente em formato.
* A política `re.ASCII`, combinada à normalização do ADR 0003, cobre a diferença entre dígitos ASCII e Unicode.
* Os offsets continuam sendo relacionados ao texto original, permitindo futura sanitização sem perder a localização correta.
* O `Finding` não expõe o valor detectado, reduzindo o risco de vazamento da PII na camada de auditoria.
* A arquitetura de dois estágios pode ser reutilizada por outros identificadores que possuam uma regra determinística de validação.

### Custos e riscos

* Aproximadamente 1 em cada 100 sequências aleatórias de 11 dígitos pode passar pelos dois dígitos verificadores: intuitivamente, cada DV possui aproximadamente 10 valores possíveis, resultando em uma chance de cerca de `1/10 × 1/10`. Isso não representa a taxa real de falso positivo do detector, que depende do corpus analisado; telefones e outros números estruturados ainda podem ser confundidos com CPF.
* O MVP reconhece somente os dois formatos definidos. CPF com espaços ou outras variações não será detectado.
* Cada novo tipo de PII acrescenta uma varredura sobre o texto. O custo específico do detector é `14 ns/char fixo` + `4,5 µs/candidato`.
* O score de PII é atualmente informativo, enquanto o score de prompt injection participa da decisão em `decide_action`. Essa assimetria é intencional neste estágio, mas deve ser reavaliada caso scores de PII passem a influenciar decisões.

### Resultado do Benchmark

O benchmark foi executado em Windows 11, Python 3.14.3, com `N = 10.000` medições e 500 iterações de aquecimento. Foram avaliados três cenários (`sem_candidato`, `candidato_invalido` e `cpf_valido`) em textos de 100, 1.000 e 10.000 caracteres. Foi inserido um CPF a cada 5 palavras, utilizando CPFs válidos e inválidos com o mesmo formato pontuado. A verificação dos cenários encontrou 2, 22 e 223 candidatos nos três tamanhos; candidatos inválidos produziram zero `Finding`, enquanto candidatos válidos produziram um `Finding` por candidato.

No cenário sem candidato, o custo P50 por caractere foi de **17,0 → 14,4 → 13,96 ns/char** para 100 → 1.000 → 10.000 caracteres, mantendo comportamento linear. No maior tamanho, isso corresponde a aproximadamente **9,0% do gatilho inicial de 155 ns/char**. Após o benchmark, esse limite foi reancorado para **30 ns/char**, equivalente a aproximadamente **46,5% do novo gatilho**, mantendo uma margem de aproximadamente 2× sobre o custo medido. O valor também corresponde a aproximadamente **4,5% do custo de 310 ns/char da normalização medido** no ADR 0003.

Em execuções repetidas, o cenário de 100 caracteres apresentou maior variação relativa: uma execução posterior mediu **27,0 ns/char, contra 17,0 ns/char no registro oficial**. Como o tempo absoluto nesse caso é de aproximadamente 2 µs, a influência do ruído do ambiente é proporcionalmente maior. Por isso, os tamanhos de 1.000 e 10.000 caracteres são referências mais estáveis para caracterizar o custo do detector.

O custo marginal permaneceu estável entre os tamanhos: **2,39–2,45 µs por candidato rejeitado**, **4,40–4,49 µs por candidato aceito** e **1,95–2,10 µs adicionais para aceitar em relação a rejeitar**, correspondendo aproximadamente ao custo de `to_original_span` e criação do `Finding`. A estabilidade confirma que esses custos são predominantemente proporcionais à quantidade de candidatos, e não ao tamanho total do texto.

Uma decomposição adicional com `timeit` mostrou `is_cpf` em aproximadamente **2,21 µs (≈92%)**, contra **96 ns (≈4%)** para os dois `replace` e **195 ns (≈8%)** para `_CPF_PATTERN.search`. A principal oportunidade de otimização está, portanto, no validador Python, e não na expressão regular.

O modelo aproximado de custo é **14 ns × caracteres + 4,5 µs × candidatos válidos + 2,4 µs × candidatos rejeitados**. Para 30.000 caracteres, aproximadamente o tamanho associado a `max_tokens = 8.000`, o custo fixo estimado é de **0,42 ms**; com 100 CPFs válidos, o custo total estimado seria de **0,87 ms**, cerca de 5,8% de um orçamento de 15 ms. No mesmo tamanho, a normalização do ADR 0003 custa aproximadamente 9,3 ms, indicando que a detecção de PII não é o gargalo do pipeline.

No cenário denso de CPF válido, com 10.000 caracteres, o custo chegou a aproximadamente **114 ns/char**. Esse valor ultrapassa o gatilho de **30 ns/char**, mas o gatilho de varredura é aplicado ao custo fixo observado no cenário sem candidatos. Nesse cenário denso, o custo por caractere incorpora principalmente o custo variável da validação dos candidatos, que possui o gatilho independente de **10 µs por candidato**. A densidade de um CPF a cada 5 palavras representa um cenário de planilha colada, e não necessariamente um prompt típico.

O benchmark também evidenciou a necessidade de `N` suficiente para estabilizar os percentis. Com `N = 100`, o marginal de aceitar em relação a rejeitar chegou a valores negativos em dois tamanhos (−0,85 µs em 100 caracteres e −0,28 µs em 1.000), apesar de o caminho válido executar todas as operações do caminho inválido e mais. Com `N = 10.000`, os três marginais ficaram positivos e consistentes, entre 1,95 e 2,10 µs.

Fontes: `benchmarks/resultados/dia_04_pii_N_100.txt` e `benchmarks/resultados/dia_04_pii_N_10_000.txt`, commit `443b8e1`. O baseline da normalização é o ADR 0003, commit `ed7d02a`.

## Gatilhos para reavaliação

* A taxa de falsos positivos medida em um corpus representativo, especialmente envolvendo telefones, exceder o limite definido durante a avaliação dos dias 17–20.
* A varredura sem candidatos ultrapassar **30 ns/char**, aproximadamente 2× o custo medido, ou o custo marginal por candidato ultrapassar **10 µs**.
* Surgir necessidade de detectar CPF com espaços, hífen alternativo ou outros formatos.
* Um novo tipo de PII, como CNPJ ou cartão, exigir validação determinística, indicando a necessidade de generalizar formalmente o padrão regex + validador.

## Alternativas consideradas e adiadas

* **Biblioteca externa de validação:** não adotada neste momento para evitar uma dependência adicional no `core`.
* **Presidio/NER:** adiado porque a estratégia atual da tese é baseada em detecção 100% determinística.
* **Emitir candidatos com DV inválido e score baixo:** adiado até que `decide_action` utilize score também para decisões de PII.
* **Otimização de `is_cpf`:** adiada a pré-conversão dos dígitos para evitar reconversão durante DV1/DV2. O benchmark indica que `is_cpf` concentra aproximadamente 92% do custo de rejeição, mas o ganho estimado seria inferior a 2× e não se justifica diante do custo total estimado de aproximadamente 0,87 ms em 30.000 caracteres.