# ADR 0005 — Mascaramento reversível de PII

* **Status:** Aceito
* **Data:** 2026-09-23

## Contexto

A ação `SANITIZE` precisava de uma implementação que removesse PII do prompt antes do envio à LLM, mantendo o texto legível para a tarefa e permitindo que a resposta pudesse ser re-hidratada posteriormente.

O `Finding` já fornece as posições `start` e `end` no **texto original**, conforme os ADRs 0003 e 0004. Portanto, o mascaramento pode ser realizado diretamente sobre o texto escrito pelo usuário, preservando acentos, formatação e demais caracteres fora da PII.

## Decisão

A PII será substituída no texto original por placeholders nomeados no formato `[TIPO_N]`.

Em modo `REVERSIBLE`, o masker mantém em memória um mapa `placeholder → valor original`, permitindo a re-hidratação posterior. Em modo `IRREVERSIBLE`, o mesmo mascaramento é realizado, mas o mapa permanece vazio.

Exemplo:

```text
Original:
"Meu CPF é 529.982.247-25."

Mascarado:
"Meu CPF é [CPF_1]."

Mapa:
{"[CPF_1]": "529.982.247-25"}
```

O `mask()` recebe a `GuardConfig` e decide o modo de mascaramento. O `Engine` só chama `mask()` quando a decisão é `SANITIZE`.

O campo `placeholders` possui `exclude=True`, pois contém os valores originais da PII e não deve aparecer na serialização pública de `Decision`.

O masker assume que os `Finding`s recebidos estão **ordenados por `start`**, possuem spans válidos e **não possuem sobreposição**. O masker não valida essas condições; a responsabilidade por produzir findings consistentes permanece nas etapas anteriores do pipeline.

## Subdecisões

| Decisão                                   | Alternativa                                     | Motivo                                                                                                             |
| ----------------------------------------- | ----------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| Mascarar o **original**                   | Mascarar o normalizado                          | Preserva o texto que o usuário realmente escreveu, incluindo acentos e formatação.                                 |
| Construção por fatias, esquerda → direita | `replace()` ou substituição de trás para frente | Permite uma única passada sem deslocar os offsets dos próximos findings.                                           |
| `[TIPO_N]` com colchetes                  | `<<...>>`, `{{...}}`, sem delimitador           | O `]` impede que `[CPF_1]` seja encontrado como substring dentro de `[CPF_10]`; comportamento verificado em teste. |
| Um placeholder por valor distinto         | Um por ocorrência                               | Reduz o mapa e preserva a informação de que ocorrências representam o mesmo valor.                                 |
| Contador por tipo                         | Contador global                                 | `[EMAIL_1]` representa o primeiro e-mail, independentemente de outros tipos de PII.                                |
| `matched_type.upper()`                    | Tabela de nomes                                 | Mantém uma única fonte de verdade e permite tipos futuros.                                                         |
| `mask()` recebe `config`                  | `Engine` descartar o mapa                       | Mantém a responsabilidade pelo modo de mascaramento no próprio masker.                                             |
| `mask()` somente em `SANITIZE`            | Sempre                                          | Evita trabalho desnecessário em `ALLOW` e `BLOCK`.                                                                 |
| Mascaramento dentro de `elapsed_ns`       | Medir somente detecção                          | O tempo representa o pipeline efetivamente executado, incluindo a sanitização.                                     |
| `placeholders` com `exclude=True`         | Campo normal                                    | O mapa contém PII e não deve ser serializado.                                                                      |

## Consequências

### Ganhos

* A PII detectada não chega à LLM.
* O texto fora da PII permanece intacto.
* O prompt continua legível.
* O round-trip pode restaurar os valores originais.
* Valores repetidos reutilizam o mesmo placeholder.
* `IRREVERSIBLE` reutiliza a mesma implementação.
* Caracteres invisíveis inseridos dentro da PII são removidos junto com ela, reduzindo uma forma de ofuscação.

### Custos e riscos

#### 1. Colisão com placeholder escrito pelo usuário

Se o prompt já contiver `[CPF_1]`, esse texto pode ser confundido com um placeholder gerado pelo masker. Durante a re-hidratação, o literal escrito pelo usuário será substituído pelo valor armazenado no mapa.

Isso pode fazer uma PII aparecer em uma posição onde ela não existia originalmente, caracterizando **potencial vazamento**, e não apenas perda de texto.

Mitigações futuras: delimitador menos provável ou verificação de colisão antes de escolher o placeholder.

#### 2. Placeholder órfão

Se a LLM omitir, reformular ou traduzir um placeholder, a re-hidratação atual não encontra o marcador correspondente. O valor permanece no mapa e o usuário pode receber o placeholder em vez do valor original.

A taxa de placeholders órfãos deverá ser monitorada posteriormente.

#### 3. Mapa reversível em memória

`exclude=True` protege a serialização de `Decision`, mas não impede exposição por `print` ou logging inadequado.

Durante uma requisição reversível, o `Decision` inteiro não deve ser registrado em logs.

#### 4. Invisíveis dentro da PII

Caracteres invisíveis dentro do span da PII são removidos junto com ela. Por exemplo, `529.982\u200b.247-25` é substituído integralmente pelo placeholder.

Essa alteração além dos caracteres visíveis da PII é aceita porque o objetivo do `SANITIZE` é impedir que a informação sensível, inclusive quando ofuscada, chegue à LLM.

## Resultado do Benchmark

O mascaramento não foi medido isoladamente.

O custo é considerado secundário em relação às etapas já medidas nos ADRs anteriores: aproximadamente **3,5 µs para a construção da `Decision` (ADR 0002)** e **2 µs por `Finding` (ADR 0004)**. Além disso, o mascaramento só é executado no caminho `SANITIZE`.

O custo do mascaramento permanece incluído em `elapsed_ns`, pois esse valor deve representar o pipeline efetivamente executado.

## Gatilhos

Este ADR deverá ser revisado caso:

1. uma colisão de placeholder seja observada em uso real;
2. a taxa de placeholders órfãos ultrapasse o limite definido na avaliação;
3. surja necessidade de placeholders que sobrevivam de forma confiável a tradução ou reformulação;
4. múltiplos detectores passem a produzir findings sobrepostos;
5. seja necessário representar uma PII com semântica contextual mais rica;
6. seja necessário eliminar o armazenamento direto dos valores originais.

## Alternativas adiadas

* **Hashing/tokenização criptográfica:** reversibilidade sem armazenar diretamente o valor.
* **Mascaramento parcial:** como `529.***.**-25`.
* **Placeholder semanticamente rico:** como `[CPF_DO_TITULAR]`.
* **Validação de sobreposição no masker:** atualmente tratada como pré-condição do contrato de entrada.

## Cobertura

O comportamento deste ADR é coberto por `tests/test_masker.py` e `tests/test_engine.py`.
