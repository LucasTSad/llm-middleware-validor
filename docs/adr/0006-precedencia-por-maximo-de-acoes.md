# ADR 0006 — Precedência por máximo de ações

* **Status:** Aceito
* **Data:** 25/09/2026
* **Substitui:** ADR 0002 — Política de decisão e precedência
* **Decisão relacionada:** ADR 0007 — Detector de prompt injection por famílias de regras

## Contexto

O ADR 0002 definia a decisão final do Engine por uma escada de `if/elif`,
avaliando condições sobre a lista completa de `Finding`s. A abordagem
funcionava enquanto as categorias existentes podiam ser tratadas como uma
escalada simples de severidade.

A introdução de `PROMPT_INJECTION` revelou uma limitação estrutural. Uma
injeção abaixo do limiar deve resultar em `ALLOW`, mas a existência de outra
categoria, como `PII_DISCLOSURE`, ainda deve poder elevar a decisão para
`SANITIZE`. Uma condição global como "existe uma injeção abaixo do limiar"
representa a ausência de uma condição de bloqueio, e não uma ação de
escalada. Em uma escada de primeira-condição-vence, isso pode impedir que
outras categorias sejam avaliadas corretamente.

O próprio ADR 0002 havia registrado este gatilho para reavaliar a decisão:

> "caso surja uma nova categoria de ameaça cujas regras de negócio não se
> encaixem no modelo baseado prioritariamente em severidade"

O mesmo ADR também havia registrado como alternativa adiada tornar `Action`
ordenável e utilizar `max()` para determinar o resultado. A combinação de
`PROMPT_INJECTION` com `PII_DISCLOSURE` confirmou esse gatilho e levou à
adoção daquela alternativa.

## Decisão

A decisão final não será mais determinada por uma escada global de
primeira-condição-vence. Cada `Finding` será avaliado individualmente por uma
política `action_for_finding`, que determina a ação que aquele finding,
isoladamente, justifica. A decisão final será o máximo das ações produzidas
pelos findings, segundo uma ordem de precedência explícita:
`ALLOW < SANITIZE < BLOCK`.

A ordem representa a prioridade operacional das ações quando múltiplos
findings estão presentes. Ela não altera a identidade ou a representação
textual de `Action`.

## Subdecisões

- A precedência será mantida em uma estrutura explícita, e não dependerá da
  ordem alfabética ou textual de `StrEnum`.
- A consulta à precedência utilizará `__getitem__`, em vez de `.get`, para
  que uma nova `Action` sem prioridade registrada produza erro imediatamente.
- `severity >= block_severity` continua sendo avaliada antes do `score`.
- O `score` participa da decisão somente nas categorias cuja política o
  utiliza, atualmente `PROMPT_INJECTION`.
- Categorias não mapeadas mantêm comportamento *fail-safe*: `BLOCK`.

## Alternativas consideradas

### Tornar `Action` um `IntEnum`

Essa alternativa permitiria representar a precedência diretamente no enum e
usar `max()` sem uma estrutura auxiliar.

Foi rejeitada porque `Action` atualmente é um `StrEnum` e sua representação
textual faz parte da trilha de auditoria. A mudança para `IntEnum` alteraria
o valor serializado de ações como `"block"` para um valor numérico, como `2`,
modificando o contrato do payload destinado à persistência e tornando os
registros menos legíveis sem consultar o código.

O dicionário de prioridades preserva a representação textual existente e
separa a ordem operacional da identidade da ação.

## Semântica de ALLOW

A mudança altera o significado de `ALLOW`.

Antes, a interpretação prática era:

> `ALLOW` = nenhum finding foi encontrado.

Agora:

> `ALLOW` = nenhum finding foi encontrado **ou** todos os findings encontrados
> estão abaixo das condições que justificam uma ação mais restritiva.

Portanto, `ALLOW` não significa necessariamente que a entrada está limpa.

Consumidores da decisão que precisem de informações de auditoria devem
examinar também `Decision.findings`, e não interpretar `Action.ALLOW`
isoladamente como ausência de detecção.

Essa distinção é particularmente relevante para a futura persistência da
trilha de auditoria no DynamoDB.

## Consequências

### Ganhos

Categorias diferentes passam a expressar regras de decisão independentes
sem precisar conhecer a posição das demais categorias na escada.

Um finding de `PROMPT_INJECTION` abaixo do limiar pode resultar em `ALLOW`
sem impedir que um finding de `PII_DISCLOSURE` resulte em `SANITIZE`.
Qualquer finding que justifique `BLOCK` prevalece sobre ações menos
restritivas produzidas pelos demais findings.

A política também fornece uma extensão previsível para novas categorias:
cada categoria define a ação que seu finding justifica, enquanto a
precedência global permanece centralizada.

### Custos e riscos

A ordem de precedência passou a existir em uma estrutura separada da função
que define as ações.

Adicionar um novo membro a `Action` sem registrá-lo na precedência causa
`KeyError` em tempo de execução. Esse comportamento é intencional: uma ação
sem precedência definida não deve receber silenciosamente uma prioridade
arbitrária.

A solução também não representa políticas nas quais múltiplos sinais fracos
precisam ser acumulados para produzir uma ação mais forte. Cada finding é
avaliado independentemente.

## Evidência

A necessidade da mudança foi demonstrada pelo caso em que uma entrada
contendo uma injeção com score `0.5` e um CPF válido era classificada como
`ALLOW`. A regra de injeção abaixo do limiar podia impedir que a presença da
PII elevasse a decisão para `SANITIZE`, permitindo que a informação sensível
permanecesse em claro.

A alteração também revelou um problema independente no fluxo de
sanitização: o Engine encaminhava todos os findings para o masker, embora
nem todos fossem findings de PII. Em um caso com findings fora de ordem, a
saída sanitizada foi:

```text
'Telefone: 11987654321. Meu CPF e [CPF_1][TELEFONE_1]. Meu CPF e 529.982.247-25'
```

O resultado demonstra que tanto o telefone quanto o CPF permaneceram em
claro na saída que deveria estar sanitizada. O Engine passou a filtrar os
findings por `PII_DISCLOSURE` e ordená-los por posição antes de chamar o
masker, preservando as precondições documentadas no ADR 0005.

## Relação com decisões anteriores

O ADR 0002 permanece como registro histórico da decisão anterior e não é
editado para remover a abordagem substituída.

Seu status passa a ser:

**Substituído por ADR 0006.**

A manutenção dos dois documentos preserva a evolução arquitetural e permite
verificar que a condição prevista para reavaliação no ADR 0002 realmente
ocorreu.

## Gatilho de reavaliação

Esta decisão deverá ser reavaliada caso uma nova categoria ou regra precise
combinar múltiplos findings para produzir uma ação que não possa ser
representada por uma ação independente para cada finding.

Um exemplo é uma política na qual três sinais individualmente fracos devam
ser acumulados para ultrapassar um limiar e produzir `BLOCK`.

O máximo por finding não expressa esse tipo de acumulação. Essa é uma
limitação conhecida da decisão atual e está relacionada à escolha de manter
um `Finding` por padrão detectado.
