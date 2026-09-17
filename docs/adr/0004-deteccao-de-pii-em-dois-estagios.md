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
* Cada novo tipo de PII acrescenta uma varredura sobre o texto. O custo específico do detector ainda será medido em `bench_pii.py`.
* O score de PII é atualmente informativo, enquanto o score de prompt injection participa da decisão em `decide_action`. Essa assimetria é intencional neste estágio, mas deve ser reavaliada caso scores de PII passem a influenciar decisões.

## Gatilhos para reavaliação

* A taxa de falsos positivos medida em um corpus representativo, especialmente envolvendo telefones, exceder o limite definido durante a avaliação dos dias 17–20.
* O custo do detector se aproximar ou ultrapassar 50% do custo da normalização (~155 ns/char), atualmente aproximadamente 310 ns/char.
* Surgir necessidade de detectar CPF com espaços, hífen alternativo ou outros formatos.
* Um novo tipo de PII, como CNPJ ou cartão, exigir validação determinística, indicando a necessidade de generalizar formalmente o padrão regex + validador.

## Alternativas consideradas e adiadas

* **Biblioteca externa de validação:** não adotada neste momento para evitar uma dependência adicional no `core`.
* **Presidio/NER:** adiado porque a estratégia atual da tese é baseada em detecção 100% determinística.
* **Emitir candidatos com DV inválido e score baixo:** adiado até que `decide_action` utilize score também para decisões de PII.