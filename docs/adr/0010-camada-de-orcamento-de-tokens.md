# ADR 0010 — Camada de orçamento de tokens

* **Status:** Aceito
* **Data:** 28/10/2026
* **Decisões relacionadas:** ADR 0001 — Pipeline com núcleo isolado; ADR 0003 — Normalização com preservação de offsets; ADR 0005 — Mascaramento reversível; ADR 0006 — Precedência por máximo de ações; ADR 0009 — Convenção de medição e escopo da afirmação de orçamento

## Contexto

"Custos elevados com tokens" é o terceiro risco nomeado no aceite, e é o único sem nenhuma linha de código.

O `GuardConfig`, porém, já publica a interface inteira dessa camada. Dos oito campos, cinco têm leitor e três não:

```
com leitor:  block_severity, injection_threshold, enabled_detectors, mask_mode, normalize_input
sem leitor:  max_tokens, encoding_name, price_per_1k_tokens_usd
```

Os três sem leitor são exatamente os três da camada de tokens. A configuração foi escrita adiantada, e a consequência não é cosmética: **hoje alguém configura `max_tokens=100` e nada acontece.** Não é campo inerte — é limite configurável silenciosamente não aplicado, num trabalho cujo terceiro risco nomeado é custo.

Há ainda um nome quebrado. O default de `enabled_detectors` é `("budget", "pii", "injection")`, e `"budget"` não existe no `_REGISTRY`, de modo que `build_detectors(GuardConfig())` levanta `ValueError`. Esta decisão precisa dizer de que lado está o erro.

E a pergunta que a camada existe para responder — compensa mascarar antes de enviar? — não é respondida por um contador. Exige comparar duas contagens.

## Decisão

### 1. Contar é passo do `Engine`, não de um detector

A regra que esta cláusula torna explícita já é seguida pelo código: **detector produz `Finding`; `Engine` produz medição.** O `elapsed_ns` é campo da `Decision` que nenhum detector produz — o `Engine` mede e preenche. `token_count` é da mesma família.

O precedente basta: o `elapsed_ns` já é medição que o `Engine` produz e nenhum detector produz. O custo de fazer diferente está na cláusula 2.

### 2. Verificar também é passo do `Engine`, e `"budget"` sai de `enabled_detectors`

Se a verificação fosse um detector, teria de contar de novo: `inspect` recebe `NormalizedText` e `GuardConfig`, não a contagem. **Recontar dobra o custo da camada, em qualquer caminho** — a afirmação é relativa e não depende de qual caminho se considere. Para dar escala: duas passagens do tokenizador custam cerca de 2,56 ms em 10.000 caracteres (sondagem do ADR 0009), de modo que dobrar gasta um terço do orçamento para medir o orçamento.

Portanto a comparação `token_count > max_tokens` acontece no `analyze()`, e **`"budget"` é removido do default de `enabled_detectors`**.

Isso decide o erro do construtor na direção oposta à aparente: não falta registrar uma classe, **sobra um nome na tupla**. Registrar um detector de orçamento consertaria o sintoma e prenderia o desenho na alternativa que esta decisão rejeita.

Não há chave para desligar a verificação. `normalize_input` existe porque os benchmarks precisam medir sem normalizar — necessidade demonstrada; aqui não há equivalente, e `max_tokens` com `gt=0` já admite qualquer teto. Quem quiser teto praticamente inexistente declara um número grande.

### 3. O excesso continua sendo um `Finding`, emitido pelo `Engine`

Medir no `Engine` não retira o excesso da política de decisão. O contrato obriga:

```python
elif self.action is Action.BLOCK and not self.findings:
    raise ValueError("findings nao pode ser vazio quando action == BLOCK")
```

`BLOCK` exige `findings` não vazio. A alternativa — definir a ação fora de `decide_action` — quebraria o ponto único de decisão que o ADR 0006 estabeleceu, em troca de nada.

Portanto, quando `token_count > max_tokens`, o `Engine` constrói um `Finding` de `BUDGET_EXCEEDED` e o acrescenta a `all_findings` **antes** de `decide_action`. A precedência por máximo de ações resolve a combinação sem caso especial.

Duas propriedades desse `Finding` são arbitrárias e por isso ficam declaradas:

* **span `0` a `len(original)`.** Excesso de orçamento é propriedade do texto inteiro, não de uma posição. O `validate_span` exige `end > start`, então um span vazio não é representável, e o texto todo é a única escolha honesta. Na trilha de auditoria esse par será lido como localização: é o custo de o contrato não distinguir fato localizado de fato global.

  O sistema de coordenadas é o mesmo de todos os outros `Finding`: `pii.py` e `injection.py` chamam `to_original_span` antes de construir, de modo que nenhum `Finding` do sistema indexa o texto normalizado. É para isso que o ADR 0003 existe, e por isso `len(original)` não pode cair fora de nada — a expansão NFKC altera o comprimento do normalizado e não alcança esse span.

  A borda de `original` vazio — `end = 0`, que violaria o `gt=0` — é **inalcançável**: `max_tokens` tem `gt=0`, logo vale no mínimo 1, e texto vazio conta 0 tokens, que nunca é maior que 1. Fica registrado para que ninguém acrescente guarda defensiva depois contra estado que não ocorre;
* **`severity` é inerte.** Por `action_for_finding`, severidade alta bloqueia na primeira condição e qualquer outro valor cai no `return Action.BLOCK` final. Para a categoria `BUDGET_EXCEEDED` toda severidade bloqueia, e o valor escolhido não altera comportamento. Fica `MEDIUM`, por acompanhar `test_categoria_budget_exceeded_block`, com o registro de que a escolha é convencional.

Esse é o mesmo custo que um detector pagaria, e é por isso que ele não figura entre os motivos da cláusula 1.

### 4. O que a `Decision` passa a carregar

| Campo | Situação | Significado |
| --- | --- | --- |
| `token_count` | já existe, hoje sempre 0 | contagem do texto admitido |
| `estimated_cost_usd` | já existe, hoje sempre 0 | `float \| None`; `None` quando não há preço configurado |
| `token_delta` | **novo** | `int \| None`; economia de mascarar, negativa quando mascarar encarece |

A aritmética que liga os três fica declarada, para que a trilha não exija adivinhação: **contagem do texto enviado = `token_count` − `token_delta`** quando há mascaramento, e **igual a `token_count`** quando `token_delta` é `None`, porque aí não há segundo texto. Em ambos os casos `estimated_cost_usd` é calculado sobre essa contagem, não necessariamente sobre `token_count`.

`token_delta` é `None` quando não houve mascaramento, e a distinção tem critério: `placeholders` é **coleção**, e vazia significa "nada dentro", que é bem definido; `sanitized_text` e o delta são **valores**, e `None` significa "não existe". No caminho `ALLOW` não existe segundo texto para contar, logo a economia não é zero — é indefinida.

A regra vira invariante em `validate_coherence`, espelhando a que já existe para `sanitized_text`: **`token_delta` não é `None` se e somente se houve mascaramento.** Estado inválido deixa de ser representável.

### 5. O encoder é injetado na fronteira do `Engine`

`tiktoken.get_encoding()` lê o encoding de cache em disco na primeira chamada, e recorre à rede se o cache estiver ausente. Isso é I/O, que o ADR 0001 proíbe no núcleo.

O `Engine` já recebe os detectores construídos por `build_detectors`, fora dele. O encoder segue o mesmo caminho: construído na fronteira, injetado pronto. Não é exceção ao ADR 0001 — é o padrão dele.

Consequência a declarar: `encoding_name` passa a ser lido por **quem constrói o encoder**, não pelo núcleo.

### 6. O preço é opcional, e a ausência dele é dita

`price_per_1k_tokens_usd` tem default `0.0`, e `estimated_cost_usd` também. Como nada lê o preço, a trilha de auditoria do ADR 0008 grava `"estimated_cost_usd": 0.0` em todo registro — indistinguível de "configurado como gratuito".

É um número que afirma mais do que sabe, e o ADR 0009 proibiu isso para tabelas e prosa. Aqui o mesmo vício está no produto, no artefato que o trabalho oferece como evidência de método.

Portanto `estimated_cost_usd` passa a ser `float | None`, e `None` significa **preço não configurado**. O `audit.py` e o `RecordAudit` acompanham. A correção cabe nesta decisão porque nada chama `record` ainda: a trilha não tem um único registro em disco, e arquivo sem consumidor é o mais barato que existe para mudar.

### 7. Qual texto é contado

Existem **três** textos no `analyze()` — original, normalizado e mascarado — e as duas finalidades usam dois deles:

* **admissão** usa a contagem do texto **original**, o que o usuário enviou. É determinístico, independe de mascaramento e de normalização, e é o único número que o usuário consegue conferir;
* **custo estimado** usa a contagem do texto **efetivamente enviado à LLM** — o mascarado quando há mascaramento, o original quando não há. É o que o orçamento financeiro precisa;
* o texto **normalizado** não é contado para nenhuma das duas finalidades. Ele existe para a detecção preservando offsets (ADR 0003) e não é o que sai da máquina.

O fundamento está na seção seguinte.

## Fundamento — por que três textos, e não dois

A divisão entre admissão e contabilidade — no enquadramento do ADR 0009, duas finalidades distintas coexistindo — não bastaria se o texto normalizado fosse equivalente ao original. Ele não é: a normalização altera a tokenização, e nos dois sentidos.

| Entrada | tokens antes | depois | variação |
| --- | --- | --- | --- |
| zero-width entre sílabas | 18 | 11 | −39% |
| largura total (NFKC) | 16 | 14 | −12% |
| ligadura `ﬁ` e fração `½` | 15 | 17 | **+13%** |
| texto sem nada a normalizar | 13 | 13 | 0% |

Sondagem de uma execução, não benchmark; serve para mostrar que a pergunta existe e que a direção não é previsível. A expansão NFKC acrescenta caracteres, então o texto normalizado pode custar **mais** que o original. Contar o normalizado seria cobrar do usuário um número que ele não pode conferir, variável por motivo que não está no texto dele — o que exclui o terceiro texto das duas finalidades.

### Quantas contagens a camada custa

Duas finalidades não implicam duas passagens sempre. No caminho `ALLOW` não existe segundo texto, e as duas finalidades leem a **mesma** contagem: uma passagem do tokenizador. Só o caminho `SANITIZE` custa duas, porque a segunda conta o texto mascarado.

Essa segunda contagem acontece **depois** do mascaramento e, portanto, **dentro** da janela do `elapsed_ns` — o `Engine` fecha a medição na linha que antecede a construção da `Decision`. O custo aparece na medição, não fora dela.

### Mascarar pode encarecer

A alternativa de admitir pelo texto mascarado foi rejeitada. Medido com `o200k_base`: `529.982.247-25` são 7 tokens contra 5 de `[CPF_1]`, economia de 2; mas `52998224725` são 4 tokens contra os mesmos 5, custo de 1 a mais. O ADR 0004 implementa os dois formatos, de modo que o caso desfavorável é metade dos **formatos** reconhecidos — não metade dos casos, porque a distribuição dos dois formatos em prompt real não foi medida.

Admitir pelo mascarado não resolveria a assimetria: inverteria a direção dela, criando prompt que passa no original e estoura depois de mascarado. Uma decisão de ordem precisa valer nos dois sentidos.

### A forma do marcador virou parâmetro econômico

O parâmetro econômico é a **forma** `[TIPO_N]`, não o comprimento do índice. Medido com `o200k_base`: `[CPF_1]`, `[CPF_10]` e `[CPF_100]` custam 5 tokens cada; só em `[CPF_1000]` sobe para 6. O índice é quase gratuito; o preço está nos colchetes, no tipo e no sublinhado.

O ADR 0005 escolheu essa forma por risco de colisão — `[CPF_1]` casando dentro de `[CPF_10]` —, sem considerar custo. Os dois critérios agora competem, e esta decisão registra a tensão sem resolvê-la: encurtar a forma reduz o custo e reintroduz o risco que o ADR 0005 evitou.

## Consequências

### Para o mapa categoria → ação (ADR 0006)

O ADR 0006 decide precedência **por máximo de ações**, e isso não muda. O que esta decisão expõe é outra coisa: o mapa de categoria para ação. `BUDGET_EXCEEDED` bloqueia por queda no `return Action.BLOCK` final de `action_for_finding`, não por regra escrita, e `test_categoria_budget_exceeded_block` fixa esse comportamento incidental com `Severity.MEDIUM`.

PII e injection são ajustáveis por configuração; orçamento não é, e ninguém escreveu que não deveria ser. Fica como gatilho, não como alteração: bloquear por tamanho é diferente de bloquear por ameaça, e o aceite não usa a palavra "bloquear".

### Para a afirmação de latência (ADR 0009)

A camada acrescenta cerca de 2,56 ms em 10.000 caracteres no pior caso — duas passagens, isto é, o caminho `SANITIZE` —, levando a soma dos P95 a 12,58 ms, ou 84% do orçamento. No caminho `ALLOW` é a metade disso. Esse valor é **sondagem**: entra na afirmação do trabalho somente depois de medido em benchmark commitado.

### Para os três campos sem leitor

`max_tokens` passa a ser aplicado, `encoding_name` passa a ser lido na fronteira, e `price_per_1k_tokens_usd` passa a decidir entre custo estimado e `None`. O `GuardConfig` deixa de prometer controle que não exerce.

## Premissas assumidas

**Preço por mil tokens, uniforme e de entrada.** Modelos cobram preços diferentes para entrada e saída, e o campo é único. A estimativa cobre o custo de entrada, que é o que um filtro de entrada pode conhecer.

**O tokenizador é o do `encoding_name`, não o do modelo real.** `o200k_base` é o encoding de uma família de modelos; outra família tokeniza diferente. A estimativa vale para o encoding configurado.

**A razão de custo do `encode` é sondagem.** Medida sob o protocolo do ADR 0009, não publicada em artefato.

## Trabalho futuro

**Benchmark da camada**, para que o custo entre na afirmação de latência em vez de ficar como sondagem.

**Preço por modelo**, separando entrada e saída, caso a estimativa precise cobrir a resposta.

**Forma de marcador mais curta**, se o custo de `[TIPO_N]` se mostrar relevante no agregado — exige resolver a colisão que o ADR 0005 evitou.

## Gatilhos de reavaliação

1. A economia agregada sobre um corpus se mostrar negativa com frequência, caso em que mascarar para economizar deixa de ser justificativa e o delta passa a servir só de informação.
2. Surgir necessidade demonstrada de desligar a verificação de orçamento, caso em que a chave entra com justificativa.
3. O custo medido da camada em benchmark divergir da sondagem de 2,56 ms, consumindo a margem registrada no ADR 0009.
4. A saída da LLM passar a ser contabilizada, caso em que o preço único e de entrada deixa de bastar.

## Relação com decisões anteriores

**ADR 0001** — proibiu I/O no núcleo e estabeleceu injeção na fronteira do `Engine`. O encoder segue esse padrão; nenhuma exceção é aberta.

**ADR 0003** — produziu o texto normalizado, que preserva offsets para a detecção. Esta decisão declara que ele **não** é o texto contado, em nenhuma das duas finalidades.

**ADR 0005** — escolheu a forma `[TIPO_N]` por colisão. Esta decisão registra que a escolha passou a ter consequência econômica, sem alterá-la.

**ADR 0006** — decide precedência por máximo, o que não muda. O mapa categoria → ação fica como gatilho.

**ADR 0009** — fornece o enquadramento de finalidades distintas coexistindo, que aqui separa admissão de contabilidade, e a convenção de que número citável é número medido, que aqui obriga `None` no custo não configurado.
