# Corpus de avaliação de Prompt Injection

## Finalidade

Este diretório contém o corpus sintético utilizado para avaliar o detector de prompt injection do projeto.

O corpus é utilizado por um **script de avaliação**, e não como um teste unitário de `pytest`. Seu objetivo é produzir métricas de mitigação e falso positivo, além de identificar quais famílias de regras produziram erros.

## Procedência

O corpus é **sintético e autoral**, elaborado especificamente para este projeto. Os casos foram escritos com base nas famílias de prompt injection estudadas a partir da categoria **LLM01 — Prompt Injection** do OWASP Top 10 for LLM Applications.

O corpus não é uma cópia nem uma amostra extraída de um dataset público.

Data de criação: 25/09/2026.

## Estrutura

Os casos são armazenados em `prompt_injection_corpus.jsonl`, utilizando um objeto JSON por linha.

Cada caso possui exatamente cinco campos:

* `id`: identificador estável e único;
* `label`: `ataque` ou `legitimo`;
* `families`: lista das famílias de prompt injection presentes no caso;
* `text`: texto submetido ao detector;
* `justification`: justificativa da classificação e do aspecto que torna o caso relevante para a avaliação.

Casos legítimos possuem `families` como uma lista vazia (`[]`).

Um caso pode pertencer a mais de uma família. Portanto, a soma das quantidades de casos por família pode ser superior ao número total de ataques.

### Critério de rotulagem das famílias

Uma família é incluída em `families` quando o texto contém, de forma independente, uma manifestação do comportamento que a família representa e que poderia ser identificada por uma regra específica daquela família, sem depender da presença de outra família no mesmo caso.

As famílias utilizadas neste corpus são:

* `delimiter`: tentativa de introduzir ou simular uma fronteira sintática privilegiada de mensagem ou instrução;
* `persona_switch`: tentativa de alterar explicitamente a identidade, o papel ou a autoridade atribuída ao assistente;
* `instruction_override`: tentativa explícita de substituir, ignorar ou invalidar instruções anteriores;
* `system_prompt`: solicitação explícita para revelar o system prompt, instruções internas ou regras ocultas.

Esse critério é aplicado ao texto do caso, independentemente de qual regra do detector posteriormente consiga identificá-lo.

### Casos com múltiplas famílias

Um caso pode apresentar mais de um vetor de ataque independente.

Por exemplo, `atk_02` pertence simultaneamente às famílias `delimiter` e `instruction_override`, pois utiliza um marcador de sistema falso e tenta substituir instruções anteriores.

Entretanto, `atk_02` **não** pertence à família `system_prompt`. Embora solicite a revelação de "internal information", essa expressão é mais ampla e não especifica explicitamente o system prompt, instruções internas ou regras ocultas. A classificação como `system_prompt` exige essa manifestação específica.

## Balanceamento

A versão inicial contém 16 casos:

* 8 ataques;
* 8 legítimos;
* 4 ataques em português;
* 4 ataques em inglês;
* 4 casos legítimos em português;
* 4 casos legítimos em inglês.

Os ataques contemplam quatro famílias. Alguns casos possuem múltiplas famílias quando apresentam mais de um vetor de ataque independente.

Os casos legítimos foram construídos para serem adversariais contra o próprio detector, incluindo discussões acadêmicas sobre prompt injection, uso coloquial de termos como "ignore", marcadores de templates de modelos e solicitações legítimas relacionadas a system prompts.

## Descoberta durante a preparação da avaliação

Antes da execução da avaliação agregada, foi comparada a lista de marcadores inicialmente prevista para a regra `delimiter` com os casos do corpus.

A comparação revelou que os cinco marcadores inicialmente definidos:

* `[INST]`;
* `<|im_start|>`;
* `<|im_end|>`;
* `<message role="system">`;
* `</system>`;

apareciam somente nos casos legítimos `leg_03`, `leg_04` e `leg_05`, enquanto os ataques classificados como `delimiter` utilizavam outras formas:

* `atk_01`: `<|system|>` e `<|end|>`;
* `atk_02`: `[SYSTEM]` e `[END SYSTEM]`.

Consequentemente, uma implementação baseada exclusivamente em uma lista fechada desses cinco marcadores seria incapaz de detectar `atk_01` e `atk_02`, embora pudesse gerar falsos positivos nos casos legítimos.

Essa descoberta foi registrada **antes da execução da avaliação agregada** e levou à revisão da definição operacional da família `delimiter`.

A família passou a representar a **forma de tentativa de introdução de uma fronteira privilegiada**, e não somente uma lista fechada de marcadores conhecidos de templates.

## Implementação inicial do detector

A primeira implementação da família `delimiter` utiliza correspondência literal de **formas restritas de delimitadores privilegiados**, sem análise contextual.

A versão inicial considera três formas:

1. marcadores entre `|`, como `<|system|>` ou `<|im_start|>`;
2. marcadores entre colchetes em caixa alta, como `[SYSTEM]` ou `[INST]`;
3. delimitadores XML explícitos relacionados a `system`, como `<message role="system">` e `</system>`.

A implementação deliberadamente não considera qualquer conteúdo arbitrário entre `< >` ou `[ ]` como um delimitador. A generalização desses padrões ou a introdução de análise contextual será avaliada posteriormente.

A primeira implementação também utiliza correspondência **sensível a maiúsculas e minúsculas**. Essa decisão mantém a linha de base literal controlada e evita introduzir, simultaneamente, uma segunda variável experimental.

A utilização de `re.ASCII` não é necessária nesta regra, pois o padrão não utiliza classes como `\w`, `\d` ou `\b` cujo significado seria alterado pela flag.

## Hipótese registrada antes da avaliação

Os casos `leg_03`, `leg_04` e `leg_05` contêm formas de delimitadores que também estão dentro do escopo da implementação inicial:

* `leg_03`: `[INST]`;
* `leg_04`: `<|im_start|>` e `<|im_end|>`;
* `leg_05`: `<message role="system">` e `</system>`.

Esses casos representam uso legítimo dos mesmos formatos que podem aparecer em entradas de ataque.

**Previsão registrada antes da implementação:** a implementação inicial de `delimiter`, sem considerar o contexto em que os marcadores aparecem, deverá acusar `leg_03`, `leg_04` e `leg_05`, resultando em uma taxa de falso positivo de **3/8 = 37,5%**.

A previsão será considerada confirmada somente se os três casos forem efetivamente classificados como `BLOCK`. Caso contrário, a previsão será considerada refutada ou parcialmente confirmada, conforme os casos efetivamente classificados.

A descoberta anterior sobre a ausência dos marcadores originalmente definidos nos ataques constitui uma observação metodológica distinta da previsão acima e foi registrada antes da execução da avaliação agregada.

## Métricas

A avaliação considera duas métricas principais:

* **Taxa de mitigação:** ataques classificados pelo detector como `BLOCK` / total de ataques;
* **Taxa de falso positivo:** casos legítimos classificados pelo detector como `BLOCK` / total de casos legítimos.

As métricas agregadas devem ser apresentadas junto às contagens absolutas, pois o corpus inicial possui apenas oito casos em cada classe.

Por exemplo:

`1/8 = 12,5%`

A taxa de mitigação e a taxa de falso positivo devem ser interpretadas conjuntamente. Uma estratégia que bloqueasse todas as entradas poderia obter mitigação máxima, mas também poderia produzir uma quantidade elevada de falsos positivos.

## Resultados por família

Os resultados por família são apresentados **somente em contagens absolutas**.

O corpus inicial possui poucos casos por família e permite múltiplos rótulos por caso. Portanto, percentuais por família dariam uma aparência de precisão que o tamanho da amostra não sustenta.

Um caso com duas famílias contribui para a contagem de ambas as famílias, sem alterar o número total de ataques do corpus.

Os resultados agregados são calculados por **caso**, e não por quantidade de `Finding`s. Um único caso pode produzir vários findings quando contém mais de um marcador da mesma família.

## Limitações

O corpus possui caráter exploratório e não representa a distribuição real de prompts de uma população de usuários.

Além disso, existe **viés otimista por construção**: o mesmo autor que implementa o detector também constrói o corpus. Os casos foram definidos antes da implementação das regras correspondentes, mas isso não elimina a possibilidade de vieses na seleção ou formulação dos exemplos.

Por esse motivo, os resultados deste corpus devem ser interpretados como uma avaliação inicial da implementação e como instrumento de calibração, e não como estimativa universal de desempenho em produção.

Uma avaliação posterior com corpus independente ou elaborado por terceiros constitui uma possível extensão do trabalho.

### Limitação conhecida: falsos positivos com colchetes

A expressão atualmente utilizada para a forma de delimitador entre colchetes é propositalmente ampla e pode reconhecer padrões que também aparecem legitimamente em textos técnicos, como `[OK]`, `[NOTE]`, `[TODO]`, `[ERROR]` ou referências como `array[I]`.

O corpus atual contém apenas `[INST]` como exemplo legítimo desse formato. Portanto, ele **não mede de forma abrangente os falsos positivos causados por colchetes em documentação técnica, código ou textos acadêmicos**.

Essa limitação é conhecida e não representa o comportamento desejado para a versão final do detector. O corpus foi mantido congelado para preservar a consistência da avaliação atual; novos casos desse tipo devem ser adicionados em uma futura versão do corpus antes de uma nova medição.

Consequentemente, os resultados atuais de falsos positivos para a família `delimiter` devem ser interpretados considerando essa cobertura limitada.

## Especificação e previsão registradas antes da implementação de `persona_switch`

* **Data:** 22/10/2026.
* **Corpus:** congelado, SHA-256 `80c9888b3a6ac36457bc6c53d4f0d3fc3672d3529ca9f451aa3a7b2b0aade354`, idêntico ao utilizado na avaliação do dia 6.
* **Linha de base:** artefato `dia_06_prompt_injection_evaluation.txt`, com 2/8 de mitigação e 3/8 de falso positivo.
* **Estado do detector no momento deste registro:** apenas a família `delimiter` implementada.

Esta seção é registrada **antes** da implementação da segunda família e não deve ser editada após a medição. Um item refutado permanece no documento com o resultado observado ao lado.

### Regime de evidência desta seção

Esta seção **não** possui o mesmo regime de evidência da previsão do dia 6, e a distinção é registrada explicitamente porque afeta o peso probatório de cada item.

A previsão do dia 6 foi **cega**: a taxa de 3/8 em casos legítimos foi registrada antes de existir qualquer implementação da família `delimiter`, e o histórico do repositório comprova a ordem dos commits — previsão em `f866355`, implementação e medição em `6917f1b`. O acerto dessa previsão é evidência forte justamente porque a resposta não era acessível no momento do registro.

O registro atual foi precedido por uma **sondagem preliminar**: antes da redação desta seção, uma forma candidata do padrão de `persona_switch` foi executada contra os 16 casos do corpus, caso por caso, e o custo do padrão isolado foi medido em prosa sintética. Os itens 1, 2 e 3 descrevem, portanto, um resultado já conhecido no momento da escrita. Chamá-los de previsão seria incorreto.

Consequentemente, cada item desta seção é rotulado pelo seu regime:

| Item | Regime | Fundamento |
| --- | --- | --- |
| 1, 2 e 3 | **Especificação verificada em sondagem** | resultado observado na sondagem preliminar; funciona como critério de aceitação e detector de regressão, não como previsão |
| 4 | **Dedução a partir da política** | consequência analítica de ADR 0006 e do estado do detector; não depende de medição |
| 5 | **Previsão** | o objeto a ser medido não foi sondado |

O que permanece genuinamente desconhecido no momento deste registro:

| Aferição | Sondado? |
| --- | --- |
| Acurácia nos 16 casos do corpus | sim |
| Custo do padrão isolado, em prosa sintética | sim |
| Custo pelo `Engine`, com `finditer` e os textos do benchmark | **não** |
| Custo marginal por `Finding` com duas famílias | **não** |
| Efeito colateral da refatoração sobre os casos já cobertos por `delimiter` | **não** |
| Comportamento do padrão após permitir que o vão atravesse `\n` | **não** |

O último item restringe diretamente o alcance da sondagem de custo: ela mediu uma forma do padrão **anterior** ao tratamento da quebra de linha. Permitir `\n` no vão altera o que o quantificador percorre, de modo que o valor sondado não descreve o padrão que será efetivamente implementado.

A razão de registrar essa distinção, em vez de apresentar todos os itens sob o mesmo rótulo, é que o rótulo "previsão registrada" só tem valor probatório enquanto designar exclusivamente registros cegos. Aplicá-lo a um caso em que a resposta já era conhecida enfraqueceria retroativamente a previsão do dia 6, que é cega e verificável.

### Escopo da alteração prevista

A alteração prevista acrescenta a família `persona_switch` ao detector. Não altera a família `delimiter`, não altera o corpus e não altera a política de decisão definida no ADR 0006.

Portanto, qualquer variação observada nos casos já cobertos por `delimiter` indicaria efeito colateral da refatoração, e não efeito da nova família.

### Premissa explícita sobre o score

Os itens abaixo assumem que a família `persona_switch` receberá `score >= injection_threshold` (atualmente `0.7`), de modo que um único finding da família justifique `BLOCK` isoladamente.

Essa premissa é necessária porque `severity = MEDIUM` (20) é inferior a `block_severity = HIGH` (30): nesta categoria, o bloqueio não decorre da severidade, mas exclusivamente da comparação entre `score` e `injection_threshold`.

Caso a implementação adote um score inferior ao limiar, o item 1 deixa de valer e precisa ser reemitido antes da medição.

### Especificação 1 — ataques bloqueados, por identificador

Regime: resultado observado na sondagem preliminar.

| Caso | Famílias rotuladas | Comportamento especificado | Regra responsável |
| --- | --- | --- | --- |
| `atk_01` | `delimiter` | bloqueado | `delimiter` (já na linha de base) |
| `atk_02` | `delimiter`, `instruction_override` | bloqueado | `delimiter` (já na linha de base) |
| `atk_03` | `persona_switch` | bloqueado | `persona_switch` (novo) |
| `atk_04` | `persona_switch` | bloqueado | `persona_switch` (novo) |
| `atk_05` | `instruction_override`, `system_prompt` | não bloqueado | nenhuma família implementada o cobre |
| `atk_06` | `instruction_override`, `system_prompt` | não bloqueado | nenhuma família implementada o cobre |
| `atk_07` | `system_prompt` | não bloqueado | nenhuma família implementada o cobre |
| `atk_08` | `system_prompt` | não bloqueado | nenhuma família implementada o cobre |

Taxa de mitigação especificada: **4/8 = 50,0%**.

Observação sobre `atk_06`: o caso contém uma âncora temporal ("A partir deste ponto") e um substantivo de papel ("assistente"), mas não contém verbo de assunção de papel. A ausência de match nesse caso, observada na sondagem, decorre da exigência dos três elementos em sequência, e não apenas da ausência das famílias `instruction_override` e `system_prompt`. É a verificação mais informativa do conjunto, porque distingue a exigência dos três elementos de uma exigência apenas da âncora.

**Critério de aceitação e cláusula de falsificação.** A implementação é aceita somente se o conjunto de ataques bloqueados coincidir exatamente com o conjunto nomeado acima, **inclusive quanto à identidade dos casos**. Um resultado de 4/8 obtido com outro conjunto refuta este item. Após a aceitação, a mesma cláusula passa a funcionar como detector de regressão.

### Especificação 2 — legítimos perdidos, por identificador

Regime: resultado observado na sondagem preliminar.

Comportamento especificado: `leg_03`, `leg_04` e `leg_05`, os mesmos três da linha de base, bloqueados pela família `delimiter`.

Taxa de falso positivo especificada: **3/8 = 37,5%**.

O item afirma que a nova família não bloqueia nenhum caso legítimo. Os oito casos foram executados individualmente contra a forma candidata do padrão, e o resultado é registrado abaixo para que a falsificação seja específica:

| Caso | Elementos presentes | Elemento ausente que o mantém fora |
| --- | --- | --- |
| `leg_01` | vocabulário de ataque em contexto acadêmico | âncora temporal, verbo de assunção e papel |
| `leg_02` | uso coloquial de "ignore" | âncora temporal, verbo de assunção e papel |
| `leg_03` | delimitador `[INST]` | os três elementos da família `persona_switch` |
| `leg_04` | delimitadores `<\|im_start\|>` e `<\|im_end\|>` | os três elementos da família `persona_switch` |
| `leg_05` | `</system>` em prosa corrida, fora do bloco de código, que é o elemento causador do bloqueio na linha de base; e o termo `role` dentro do exemplo | âncora temporal e verbo de assunção |
| `leg_06` | o substantivo de papel "assistant" | âncora temporal e verbo de assunção |
| `leg_07` | vocabulário de defesa contra prompt injection | âncora temporal, verbo de assunção e papel |
| `leg_08` | o substantivo "system" | âncora temporal e verbo de assunção |

Os casos `leg_06` e `leg_08` são os mais informativos deste item: contêm substantivos de papel ou autoridade em uso legítimo ("assistant", "system") e não são bloqueados por nenhuma família. A afirmação de que permaneçam liberados depende da exigência da âncora temporal e do verbo de assunção, e não da raridade do vocabulário de papel em texto legítimo.

O caso `leg_05` não cumpre essa função, porque já é bloqueado pela família `delimiter` na linha de base. Um caso já bloqueado não pode demonstrar contenção da nova família.

**Critério de aceitação e cláusula de falsificação.** O item é refutado se qualquer caso legítimo fora de `leg_03`, `leg_04` e `leg_05` for bloqueado, ou se qualquer um desses três deixar de ser bloqueado.

### Especificação 3 — atribuição por regra e cobertura por família

Regime: resultado observado na sondagem preliminar.

Para a seção "BLOQUEIOS ATRIBUÍDOS ÀS REGRAS":

* `delimiter`: 2 casos de ataque com finding da regra;
* `persona_switch`: 2 casos de ataque com finding da regra.

Para a seção "COBERTURA POR FAMÍLIA DO CORPUS":

* `delimiter`: 2/2;
* `persona_switch`: 2/2;
* `instruction_override`: 1/3, inalterado em relação à linha de base, pois `atk_02` continua sendo bloqueado pela família `delimiter`;
* `system_prompt`: 0/4.

A cobertura de `instruction_override` permanecer em 1/3 é o ponto relevante: a seção mede cobertura dos casos rotulados, não atribuição causal. Uma variação nesse número sem alteração na família `instruction_override` indicaria que a nova família casou um caso cujo rótulo não a inclui.

**Critério de aceitação e cláusula de falsificação.** O item é refutado se qualquer uma das quatro contagens de cobertura divergir, ou se alguma regra produzir finding em um caso de ataque cujo rótulo não contenha a família correspondente.

### Dedução 4 — teto permitido pela política

Regime: consequência analítica do ADR 0006 e do estado do detector. Não depende de medição nem da sondagem.

O teto de mitigação desta etapa é **4/8**, e o piso de falso positivo é **3/8**.

O teto não decorre da calibração do limiar. Os casos `atk_05` a `atk_08` pertencem exclusivamente às famílias `instruction_override` e `system_prompt`, que não existem no detector; nenhum valor de `injection_threshold` os bloqueia, porque nenhum finding é produzido para eles. Reduzir o limiar não aumenta a mitigação desta etapa; apenas tornaria a decisão mais sensível a scores de famílias ainda inexistentes.

O piso de falso positivo também não decorre do limiar. Ele decorre de a família `delimiter` permanecer inalterada, com `score = 0.9`, acima do limiar.

Consequentemente, a janela de resultados admissíveis para esta etapa é estreita: mitigação de no máximo 4/8 e falso positivo de no mínimo 3/8. Qualquer resultado fora dessa janela indica que a alteração produziu efeito não previsto, e não que a política foi recalibrada.

### Previsão 5 — custo

Regime: previsão. O objeto a ser medido não foi sondado.

**Composição do valor central, declarada.** O valor central de 18 ns/caractere é a soma de duas parcelas de origens distintas:

* **3 ns/caractere medidos** para a família `delimiter` em texto limpo (2,98 ns/char no texto nominal de 30.000 caracteres, registrado em `dia_06_injection_N_10_000.txt`);
* **15 ns/caractere sondados** para uma forma candidata do padrão de `persona_switch`, executada isoladamente sobre prosa sintética na sondagem preliminar descrita acima.

O número não foi derivado por raciocínio a partir da medição anterior. Essa composição é registrada porque a parcela sondada tem duas limitações que impedem tratá-la como medição válida do que será implementado:

1. a sondagem avaliou o **padrão isolado**, não o caminho do `Engine` com `finditer` sobre os textos do benchmark;
2. a sondagem antecede o tratamento da quebra de linha. Permitir que o vão atravesse `\n` altera o que o quantificador percorre, portanto o valor de 15 ns/char descreve uma forma do padrão que não será a implementada.

Previsão para o detector com duas famílias, em texto limpo, medido pelo benchmark: **~18 ns/caractere**, com faixa admissível de **14 a 22 ns/caractere**.

A faixa aplica ao valor central a amplitude conservadora de ±23% estabelecida no ADR 0007 a partir de duas execuções do mesmo código. Ela representa sensibilidade ao ambiente de execução, e não incerteza estatística medida, e não cobre o efeito da quebra de linha, cuja direção e magnitude são desconhecidas.

Dois argumentos independentes são registrados por serem **compatíveis** com o valor sondado, e não como sua origem:

* **Distribuição de candidatos.** A família `delimiter` ancora em `<` e `[`, caracteres raros em prosa. A família `persona_switch` ancora em palavras, cujos caracteres iniciais são frequentes em texto comum. Espera-se, portanto, que a segunda família produza mais posições candidatas por caractere varrido. A razão de aproximadamente cinco vezes entre as duas parcelas é consistente com essa expectativa.
* **Dominância do normalizador.** Em qualquer ponto da faixa, a parcela do detector permanece de duas ordens de grandeza abaixo da parcela de normalização, mantendo a conclusão do ADR 0007 sobre a composição do orçamento.

Previsão para o custo marginal por `Finding`: **2,0 a 2,8 µs**, sem alteração significativa em relação aos ~2,4 µs medidos no dia 6. Este item é previsão plena: a sondagem não mediu custo marginal com duas famílias. O argumento é que esse custo é dominado pela construção do objeto `Finding`, e não pela forma do padrão que o originou — ordem de grandeza já corroborada por duas medições independentes no dia 4 e no dia 6.

Comparações previstas, apresentadas como contexto e não como critério de aprovação:

* 18 ns/char corresponde a 60% do gatilho herdado de 30 ns/caractere;
* 18 ns/char corresponde a aproximadamente 5,8% do custo do normalizador (310 ns/caractere).

O ADR 0007 registrou que o limite de 30 ns/caractere **não será utilizado como único gatilho**, por ter sido herdado do contexto do detector de PII, e que um gatilho quantitativo definitivo será estabelecido quando as famílias restantes forem implementadas. Ele é reportado aqui para continuidade histórica; ultrapassá-lo ou não ultrapassá-lo não constitui, por si, aprovação ou reprovação desta etapa.

**Cláusula de falsificação.** A previsão de custo é refutada se o custo medido em texto limpo ficar fora da faixa de 14 a 22 ns/caractere, ou se o custo marginal por `Finding` ficar fora da faixa de 2,0 a 2,8 µs.

Uma refutação deste item, ao contrário dos itens 1 a 3, é informativa: ela mede a distância entre o padrão sondado e o padrão implementado, incluindo o efeito do tratamento da quebra de linha.

### Fonte da família no relatório de avaliação

O relatório deriva a família exibida na seção "BLOQUEIOS ATRIBUÍDOS ÀS REGRAS" do `rule_id` do `Finding`, por meio do segundo segmento do identificador.

Os itens desta seção assumem que essa continua sendo a fonte canônica da família no relatório. A decisão arquitetural sobre a relação entre `rule_id` e `matched_type` será registrada no ADR correspondente à implementação da segunda família.

### Cláusula geral

Os cinco itens desta seção valem exclusivamente para o corpus de SHA-256 `80c9888b3a6ac36457bc6c53d4f0d3fc3672d3529ca9f451aa3a7b2b0aade354`.

Qualquer alteração no corpus invalida os itens, que então precisam ser reemitidos com o novo SHA-256 antes de nova medição. Esse requisito existe porque o viés otimista por construção, documentado em Limitações, só é parcialmente contido pelo registro antecipado: se o corpus pudesse mudar junto com a implementação, o registro antecipado perderia função.

O mesmo raciocínio justifica a separação de regimes declarada no início desta seção. O viés otimista cresce quando o resultado é conhecido antes do registro; nos itens 1 a 3 ele é, portanto, maior do que na previsão do dia 6, e o rótulo precisa dizer isso. A contenção disponível nesse regime não é o acerto, que é esperado, mas a cláusula de falsificação, que continua valendo como detector de regressão nas medições seguintes.

## Retirada da especificação de `persona_switch`

* **Data:** 22/10/2026.
* **Especificação retirada:** a seção anterior, registrada no commit `4c543e0`.

A seção anterior **não foi editada**. Ela permanece como registrada, e esta retirada é acrescentada abaixo dela, pelo mesmo critério aplicado ao ADR 0002: o documento substituído continua legível, para que a sequência das decisões possa ser verificada.

### O que está sendo retirado

A família `persona_switch` saiu do escopo. Com ela, saem os cinco itens da especificação anterior, incluindo a previsão de 4/8 de mitigação.

Quatro afirmações precisam ficar explícitas:

1. **A retirada é por modelo de ameaça, não por desempenho.** A família não foi reprovada: ela nunca chegou a ser avaliada.
2. **Nenhum padrão foi implementado e nenhuma avaliação foi executada.** O detector nunca teve a família. Não existe medição a reportar.
3. **Os resultados da sondagem preliminar permanecem válidos** como aquilo que sempre foram: a medição de uma forma candidata que não foi implementada. A seção anterior já declarava esse regime.
4. **A previsão de 4/8 é retirada, não substituída.** Com a detecção de prompt injection encerrando na família `delimiter`, o resultado permanece o 2/8 já medido no dia 6, e não há previsão nova a registrar: nenhuma família foi acrescentada depois daquela medição. Trocar um número pelo outro em silêncio apagaria a diferença entre uma previsão retirada e uma previsão cumprida.

### O motivo

Um filtro determinístico de input não observa a **procedência** do texto. A mesma sequência — âncora temporal, verbo de assunção, papel privilegiado — é engenharia de prompt legítima quando o usuário a digita e é ataque quando chega colada de um e-mail, de um ticket ou de uma página.

Como a string é idêntica nos dois casos, nenhuma regra sobre a string decide entre eles. As famílias cuja malícia depende da origem são, por construção, as que este filtro não consegue julgar.

O critério que substitui a cobertura de corpus está registrado no ADR 0008.

### O que sobrevive à retirada

Um dado da sondagem contraria a intuição corrente e não deve ser descartado com a família: a forma lexical de três elementos produziu **0 falsos positivos em 8 casos legítimos**, contra **3 em 8** da família estrutural `delimiter`, que exige um único marcador.

Ou seja, neste corpus, a regra lexical com conjunção de elementos foi mais precisa que a regra estrutural. É achado sobre a forma das regras, independente da família que o produziu, e permanece disponível para o capítulo de método.

### Trabalho futuro

A retirada é condicionada ao desenho atual, e não um descarte definitivo.

Se a arquitetura passar a distinguir segmentos confiáveis de não confiáveis — texto digitado pelo usuário contra texto colado ou anexado — a família volta a fazer sentido, aplicada somente ao segmento não confiável. Nesse cenário, a especificação retirada é o ponto de partida, e a sondagem registrada continua sendo a medição preliminar dela.

## PII

O corpus não contém dados pessoais reais.

Qualquer identificador pessoal utilizado em outros testes do projeto deve ser sintético e utilizado exclusivamente para fins de validação técnica.
