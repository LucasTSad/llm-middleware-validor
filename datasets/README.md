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

* `delimiter`: uso de marcadores que tentam simular ou introduzir uma fronteira privilegiada de mensagem ou instrução;
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

## Implementação inicial do detector

A primeira implementação da família `delimiter` será feita por **correspondência literal dos marcadores definidos pela regra**, sem análise do contexto em que o marcador aparece.

Essa decisão é intencional para que a primeira avaliação estabeleça uma linha de base mensurável. A necessidade de introduzir análise contextual será decidida posteriormente com base nos resultados observados no corpus.

A família `delimiter` inclui, entre outros, marcadores como:

* `[INST]`;
* `<|im_start|>`;
* `<|im_end|>`;
* `<message role="system">`;
* `</system>`.

## Hipótese registrada antes da avaliação

Os casos `leg_03`, `leg_04` e `leg_05` contêm literalmente marcadores associados a delimitadores de mensagens de modelos:

* `leg_03`: `[INST]`;
* `leg_04`: `<|im_start|>` e `<|im_end|>`;
* `leg_05`: `<message role="system">` e `</system>`.

Esses marcadores estão dentro do escopo da família `delimiter`.

**Previsão registrada antes da implementação:** a primeira implementação literal de `delimiter`, sem considerar o contexto em que os marcadores aparecem, acusará `leg_03`, `leg_04` e `leg_05`, resultando em uma taxa de falso positivo de **3/8 = 37,5%**.

A previsão será considerada confirmada somente se os três casos forem efetivamente classificados como `BLOCK`. Caso contrário, a previsão será considerada refutada ou parcialmente confirmada, conforme os casos efetivamente classificados.

Essa previsão é registrada antes da implementação da regra correspondente para evitar que o resultado observado seja utilizado para formular retroativamente a hipótese.

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

## Limitações

O corpus possui caráter exploratório e não representa a distribuição real de prompts de uma população de usuários.

Além disso, existe **viés otimista por construção**: o mesmo autor que implementa o detector também constrói o corpus. Os casos foram definidos antes da implementação das regras correspondentes, mas isso não elimina a possibilidade de vieses na seleção ou formulação dos exemplos.

Por esse motivo, os resultados deste corpus devem ser interpretados como uma avaliação inicial da implementação e como instrumento de calibração, e não como estimativa universal de desempenho em produção.

Uma avaliação posterior com corpus independente ou elaborado por terceiros constitui uma possível extensão do trabalho.

## PII

O corpus não contém dados pessoais reais.

Qualquer identificador pessoal utilizado em outros testes do projeto deve ser sintético e utilizado exclusivamente para fins de validação técnica.
