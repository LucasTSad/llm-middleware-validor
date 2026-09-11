# ADR 0003 — Normalizacao com preservacao de offsets

**Status:** Aceito  
**Data:** 11/09/2026

## Contexto
A normalização é necessária para reduzir vetores de obfuscação Unicode que podem escapar
de regex, buscas e comparações simples. O Unicode Technical Report #36 documenta riscos
relacionados à segurança e à confusibilidade de texto Unicode.

Uma alternativa seria ampliar regexes para cobrir diferentes formas de texto ofuscado,
mas isso aumenta a complexidade dos detectores e pode ampliar a superfície para ataques
de ReDoS.

Os detectores precisam trabalhar sobre uma representação normalizada sem perder a
capacidade de apontar a posição correspondente no texto original.

## Decisão
O sistema manterá duas visões do texto:

- **Texto original:** preservado sem alterações.
- **Texto normalizado:** utilizado pelos detectores.

A normalização produzirá também um **mapa de offsets**, permitindo traduzir posições
encontradas no texto normalizado para os respectivos intervalos no texto original.

A política de caracteres invisíveis será explícita. Serão removidos por padrão:

- `U+200B ZERO WIDTH SPACE` —  ocultação, quebra buscas/regex/comparações.
- `U+FEFF ZERO WIDTH NO-BREAK SPACE` — no meio do texto, pode quebrar tokens e interferir em buscas, regex e comparações. 
- `U+00AD SOFT HYPHEN` — caractere invisível que pode afetar segmentação e comparação.
- `U+202E RIGHT-TO-LEFT OVERRIDE` — risco de Bidi spoofing e Trojan Source.
- `U+2060 WORD JOINER` — divergência em tokenização, busca e comparação.

Os caracteres `U+200C ZERO WIDTH NON-JOINER` e `U+200D ZERO WIDTH JOINER` não serão
removidos por padrão, pois possuem funções legítimas em determinados sistemas de
escrita e na composição de emojis.

A normalização NFKC será aplicada após a remoção dos caracteres invisíveis.

## Subdecisões
| Decisão | Alternativa descartada | Motivo |
|---|---|---|
| Lista explícita de caracteres invisíveis | Remover todos os caracteres `Cf` | Maior auditabilidade e menor risco de remover caracteres legítimos |
| Preservar ZWNJ/ZWJ | Remover ZWNJ e ZWJ também | Possuem funções semânticas legítimas |
| NFKC caractere a caractere | NFKC aplicada somente à string inteira | O mapa de offsets exige acompanhar a expansão de cada caractere de entrada |
| Invisíveis antes de NFKC | NFKC antes da remoção | Os caracteres definidos na política não são removidos de forma adequada pela NFKC |
| Detectores recebem `NormalizedText` | Cada detector manipular sua própria normalização | Centraliza a política e a tradução de offsets |
| Pipeline mede a normalização em `elapsed_ns` | Medir somente o detector | O custo relevante para o cliente é o custo total do pipeline; a decomposição é feita pelo benchmark isolado |
| `normalize_input` como flag | Ausência de configuração | Permite comparar experimentalmente o caminho normalizado e o caminho identidade; o padrão permanece ligado |
| `normalize_input=False` retorna objeto nulo em vez de `None` | Retornar `None` | Mantém o contrato de retorno e evita tratamento especial nos consumidores |

## Consequências
**Ganhos:**

- Detectores trabalham sobre uma representação mais resistente à obfuscação Unicode.
- O texto original permanece disponível para apresentação e auditoria.
- Offsets encontrados na representação normalizada podem ser relacionados ao texto original.
- A política de caracteres removidos fica explícita e revisável.
- O custo da normalização pode ser medido separadamente do restante do pipeline.
- `normalize_input` permite comparar experimentalmente o comportamento com e sem normalização.

**Custos e Riscos:**
- O experimento com `e\u0301` confirmou que NFKC caractere a caractere diverge da
  NFKC aplicada à sequência inteira: a normalização da string produz `é`, enquanto a
  normalização individual preserva `e\u0301`. Portanto, a implementação não é
  semanticamente equivalente à NFKC completa.
- O mapa de offsets aumenta a complexidade e o consumo de memória da normalização.
- A lista explícita de caracteres pode deixar de cobrir novos vetores Unicode descobertos
  posteriormente.
- A preservação de ZWNJ/ZWJ significa que esses caracteres não são mitigados como vetores
  de obfuscação quando utilizados de forma maliciosa.
- A normalização apresentou P50 de aproximadamente **306–331 ns por caractere** nas
  entradas avaliadas, tornando seu custo relevante para entradas próximas ao limite de
  `max_tokens = 8.000`

**Resultado do Benchmark:**
O benchmark do Dia 3 foi executado em Windows 11, Python 3.14.3, com 10.000 execuções
e 500 iterações de aquecimento.

Considerando o P50, o custo por caractere permaneceu estável nas três escalas avaliadas:

- 100 caracteres: **319 ns/caractere**.
- 1.000 caracteres: **331 ns/caractere**.
- 10.000 caracteres: **306 ns/caractere**.

Essa estabilidade em duas ordens de grandeza sustenta a conclusão de que o custo da
normalização cresce aproximadamente de forma linear com o tamanho da entrada.

O P95 deve ser interpretado de forma diferente: ele é utilizado para avaliar a meta de
latência, mas apresenta maior influência do ambiente de execução. Nos textos de 10.000
caracteres, os valores observados foram:

- ASCII: **8,18 ms** — **817,78 ns/caractere**.
- Invisíveis: **6,17 ms** — **616,99 ns/caractere**.
- NFKC: **8,24 ms** — **824,06 ns/caractere**.

A diferença entre os cenários é explicada pelo caminho de processamento: caracteres
invisíveis são removidos antes da normalização NFKC, evitando a chamada a `unicodedata.normalize()`
e as operações de `extend` para esses caracteres, enquanto o cenário ASCII percorre o
caminho completo.

A comparação entre os benchmarks com `N=100` e `N=10.000` reforça a diferença entre p50 e p95:
para a mesma entrada de 100 caracteres, o P50 permaneceu próximo de **31,4–31,9 µs**,
enquanto o P95 variou de **33,7 µs para 94,9 µs**. Os resultados estão registrados em
`benchmarks/resultados/dia_03_normalizer_N_100.txt` e
`benchmarks/resultados/dia_03_normalizer_N_10_000.txt`.

Assim, o P50 é utilizado para caracterizar o custo da função e avaliar sua linearidade,
enquanto o P95 é utilizado para avaliar a meta de latência, preferencialmente em
ambiente controlado para reduzir a influência do ambiente de execução.

A principal evidência aponta, portanto, para o custo do **laço de processamento e das**
**operações realizadas por caractere**, e não simplesmente para o fato de a entrada
conter Unicode.

Para o limite configurado de `max_tokens = 8.000`, considerando aproximadamente 30.000
caracteres e o custo observado de ~310 ns/caractere no P50, a extrapolação resulta em
aproximadamente **9,3 ms** de normalização:

`30.000 × 310 ns ≈ 9,3 ms`

Esse valor representa cerca de **62% do orçamento de 15 ms**, antes da execução dos
detectores. Considerando o fator de aproximadamente **2,7×** observado entre P95 e P50
nas medições, o P95 extrapolado ultrapassaria **25 ms**, excedendo sozinho o orçamento
total de 15 ms.

Portanto, o custo da normalização já é relevante no pior caso configurado e justifica
a manutenção da flag `normalize_input` e a investigação futura de um fast path para 
entradas que a normalização não alteraria.

A comparação com o Dia 2 reforça o impacto. O pipeline sem normalização apresentou
P95 de **4,1 µs** no Dia 2. Para a entrada de 313 caracteres utilizada na comparação,
a normalização isolada apresentou P95 de **224,30 µs** no benchmark com 10.000
execuções. A soma desses valores resulta em aproximadamente **228,40 µs**, mas deve
ser tratada como estimativa, não como medição direta do pipeline completo.

**Fonte dos resultados:** `benchmarks/resultados/dia_03_normalizer_N_100.txt` e `benchmarks/resultados/dia_03_normalizer_N_10_000.txt`, commit
`ed7d02aae43faa7b15ce1c0559a2cb7e0672f4da`.

**Fonte do baseline:** `benchmarks/resultados/dia_02_null.txt`, commit 
`bca6ff870235436720d92975ed6b1cadea9f6ce7`.

**Gatilho para Reavaliação:**
- O tamanho típico dos prompts ultrapassar significativamente os tamanhos utilizados
  no benchmark.
- Surgir um novo vetor Unicode não coberto pela política atual.
- A divergência entre NFKC caractere a caractere e NFKC sobre sequências inteiras
  produzir impacto funcional relevante.
- Houver necessidade de normalizar quebras de linha ou outros elementos atualmente
  fora do MVP.

**Alternativas Consideradas e Adiadas:**
- Regexes abrangentes cobrindo variantes Unicode ofuscadas — descartadas por aumentar
  a complexidade dos detectores e a superfície potencial para ReDoS.
- Remoção genérica de todos os caracteres da categoria Unicode `Cf`.
- NFKC aplicada exclusivamente sobre a string inteira.
- Normalização de quebras de linha (`\r\n` → `\n`).
- Expansão da política para ZWNJ e ZWJ mediante configuração explícita.
- Fast path baseado em `str.isascii()` adiado — Para textos em português,
  caracteres como `ç`, `ã`, `é` e `õ` tornam o caminho ASCII pouco representativo.
  Um fast path futuro deve verificar se a entrada contém caracteres que a
  normalização efetivamente alteraria, em vez de depender apenas de
  `str.isascii()`.