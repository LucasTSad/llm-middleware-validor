# ADR 0009 — Convenção de medição e escopo da afirmação de orçamento

* **Status:** Aceito
* **Data:** 27/10/2026
* **Decisões relacionadas:** ADR 0003 — Normalização com preservação de offsets; ADR 0004 — Detecção de PII em dois estágios; ADR 0007 — Detecção de prompt injection por famílias de regras; ADR 0008 — Modelo de ameaça do filtro de entrada e trilha de auditoria

## Contexto

O trabalho afirma um orçamento de 15 ms de latência adicionada, sem declarar duas coisas das quais a afirmação depende inteiramente: **qual estimador** a sustenta e **para qual tamanho de prompt** ela vale.

A primeira omissão produziu incoerência entre documentos do repositório. O artefato do dia 3 publica a coluna `P95/caractere`, conforme a definição da docstring do `bench_normalizer`, mas o número que circula como custo da normalização — cerca de 310 ns por caractere — é o P50 do mesmo artefato, e a razão entre os dois é de **2,67×**. Os dias 4 e 6 publicam `P50/caractere`. As três parcelas não concordam sobre o que "custo por caractere" significa, e nenhuma declarou a escolha.

A segunda omissão é mais básica: o custo é função do tamanho da entrada, e é por isso que os benchmarks medem três tamanhos. Um orçamento em milissegundos sem tamanho associado não é verificável — é verdadeiro para alguma faixa e falso fora dela, e a faixa nunca foi escrita.

## Decisão

**O estimador da afirmação de orçamento é o P95.** O P50 continua reportado, como latência típica; nenhum ocupa o lugar do outro.

**A afirmação passa a ser qualificada por tamanho:** o pipeline adiciona menos de 15 ms, no P95, para prompts de até **10.000 caracteres**. Acima disso a latência **não é afirmada**. Ela é estimável por uma razão de escala **sondada, não medida em artefato**: de 10.000 para 30.000 caracteres o P95 da normalização cresce 2,71× e o do `encode` 2,86×, escala praticamente linear dentro do ruído. Nenhum benchmark do repositório mede a normalização em 30.000 caracteres.

**Toda tabela de amostras descreve dispersão, nunca estrutura.** Uma tabela de medições autoriza afirmar a dispersão observada e a comparação entre valores medidos. Não autoriza afirmar extremos, ausências, agrupamentos nem constantes; cada uma dessas exige argumento próprio — analítico ou de amostragem declarada —, não a tabela. Esta cláusula não é uma segunda decisão: é o que explica por que as outras afirmações deste documento estão redigidas como estão, e vale para a medição final e para a monografia.

## Fundamento

### Por que o P95

Uma afirmação sem qualificador de estimador é lida como "quase sempre", não como "na metade dos casos". Declarar o P50 exigiria reescrever a frase com um "tipicamente" explícito, sob pena de trocar uma incoerência por outra. O P95 a torna forte e verdadeira ao mesmo tempo — o que só é possível porque ela passou a ser qualificada por tamanho. As duas primeiras cláusulas são interdependentes.

### O que sustenta os 10.000 caracteres

Soma dos P95 publicados, no pior cenário de conteúdo de cada parcela, em 10.000 caracteres. As três parcelas são lidas das execuções com **N = 10.000** — o dia 3 tem também uma execução com N = 100, cujo P95 é 10,6% maior para a mesma entrada, e é a de N maior que vale:

| Parcela | Cenário | P95 |
| --- | --- | --- |
| Normalização | NFKC em 20% dos caracteres | 8,24 ms |
| Detecção de PII | 223 candidatos válidos | 1,34 ms |
| Detecção de injection | colchete, 56 findings | 0,44 ms |
| **Soma** | | **10,02 ms (67% do orçamento)** |

No cenário limpo a soma é de 8,43 ms. A camada de orçamento de tokens, que exige duas passagens do tokenizador, acrescentaria cerca de 2,56 ms e levaria o pior caso a 12,58 ms — mas essa parcela é **sondagem, não benchmark**, e se confirma ou se corrige na medição final.

A soma é **duplamente conservadora**: cada parcela entra no pior cenário de conteúdo *e* no pior percentil, e o P95 de uma soma é menor que a soma dos P95 salvo caudas perfeitamente correlacionadas — não há razão para o pico da normalização coincidir com o do validador de CPF. É cota superior sobre cota superior, e é isso que permite declarar os 10.000 sem margem adicional. Para quem refizer a conta: a parcela de injection foi medida sobre 10.476 caracteres reais, porque o cenário de colchete acrescenta marcadores ao texto nominal; a diferença de 4,8% está na direção conservadora.

Escalando, o cruzamento dos 15 ms ficaria perto de 14.970 caracteres com as três parcelas commitadas, e de 11.900 com a camada de tokens incluída — este segundo número depende de uma parcela que é sondagem e de uma linearidade que também é. Declara-se o valor **medido**: os 10.000 existem nos três artefatos commitados.

Isso deixa 33% do orçamento sem uso hoje, ou 16% quando a camada de tokens entrar. É margem registrada em vez de consumida.

### Por que o escopo está em caracteres, e não em tokens

Converter o limite para tokens exigiria densidade constante de tokens por caractere, e ela não existe. Medido com `o200k_base`, o padrão de `GuardConfig.encoding_name`:

| Conteúdo | tokens por caractere |
| --- | --- |
| prosa acadêmica em inglês | 0,124 |
| prosa em português | 0,191 a 0,199 |
| português coloquial, frases curtas | 0,281 a 0,365 |
| texto misto — contrato com CPF, datas, e-mail e moeda | 0,398 |
| datas em sequência | 0,476 |
| siglas, códigos fiscais e números | 0,522 |
| CPF pontuado | 0,533 |

São **amostras**, não extremos: cada vez que se procurou um valor fora do que a tabela mostrava, ele apareceu na primeira tentativa, inclusive dentro de um intervalo que uma versão anterior deste documento declarava vazio. Os valores formam um gradiente contínuo, e o que varia é comprimento médio de palavra e densidade de pontuação e de dígitos — o gênero do texto é apenas correlacionado com isso.

Para esta decisão basta a dispersão: **o mesmo limite em tokens corresponde a tamanhos de entrada muito diferentes**, o oposto do que um escopo de afirmação precisa ser. O caractere é a unidade em que o custo foi medido e em que o escopo é declarado. Para *prever* o custo do tokenizador, a unidade é o token — o custo por token varia cerca de 1,4× entre conteúdos, contra 3,1× por caractere.

### `max_tokens` e o escopo são limites de finalidades diferentes

`GuardConfig.max_tokens`, de 8.000, é limite de **admissão**, para controlar custo e contexto da chamada à LLM. O escopo declarado é o alcance de uma afirmação de desempenho.

Pela densidade variável, 8.000 tokens correspondem a entre 15.000 e 64.257 caracteres nos conteúdos medidos — e o extremo superior não é cota. Não existe, portanto, valor de `max_tokens` que corresponda ao escopo, e baixá-lo faria o produto recusar prompts que processa corretamente, apenas porque a afirmação de latência não os cobre.

Uma afirmação de desempenho não precisa cobrir toda a faixa de admissão; precisa **dizer o que cobre**. Os dois limites coexistem, cada um na sua unidade.

### Por que a regra sobre tabelas de amostras

A terceira cláusula decorre de um modo de falha que se repetiu cinco vezes nesta semana — quatro na elaboração desta decisão, uma em documento de acompanhamento revisado junto com ela. Em cada caso uma medição foi usada para afirmar mais do que havia medido: um valor pontual tratado como constante, um último resultado chamado de final, dois números próximos chamados de idênticos, uma faixa de amostras tratada como cota, um agrupamento tratado como taxonomia.

Em todos, a correção veio de **uma** amostra adicional, obtida em uma única tentativa. Não é coincidência: a afirmação excedente é falsificável por construção, porque basta procurar fora do que a amostra mostrava.

## Consequências

### Para os artefatos já publicados

Os artefatos dos dias 3, 4 e 6 **não são reescritos**: esta convenção diz como lê-los. O P95 de cada tabela sustenta a afirmação de orçamento; o P50 é a latência típica.

As colunas de custo por caractere seguem divergentes entre eles. Benchmarks futuros, e a medição final, publicam **as duas colunas**, nomeadas pelo estimador. Regerar os antigos produziria números de outra máquina e destruiria a comparação histórica, que é o único motivo de eles existirem.

### Para o fast path do ADR 0003

**Permanece adiado — por medição, e não por omissão:** a soma dos P95 em 10.000 caracteres mostra que o orçamento não estoura.

Volta à pauta se o escopo precisar crescer. Em 30.000 caracteres a normalização sozinha custaria cerca de 22,2 ms no P95 pela razão de escala sondada, e aí ele deixaria de ser otimização e passaria a ser condição — mas esse número **não está medido em artefato**, e o gatilho 1 exige medi-lo antes de reverter o ADR 0003. Pela terceira cláusula desta decisão, uma sondagem não autoriza condicionar outra decisão.

### Para a densidade usada pelo ADR 0004

O ADR 0004 associa `max_tokens = 8.000` a 30.000 caracteres, o que corresponde a 0,267 tokens por caractere. O inverso é 3,75 caracteres por token, próximo da regra de bolso de "cerca de 4 caracteres por token" — hipótese sobre a origem, não fato verificado, que explica por que o número parece razoável.

O problema não é o valor, é o alcance que se lhe atribui:

| Conteúdo | Densidade | Quanto 0,267 subestima |
| --- | --- | --- |
| texto misto realista | 0,398 | 49% |
| datas em sequência | 0,476 | 78% |
| siglas, códigos fiscais e números | 0,522 | 96% |
| CPF pontuado | 0,533 | 100% |

**Estimativas de custo de token baseadas em 0,267 subestimam de 49% a 100% o tipo de prompt que o produto existe para tratar**, e não por acidente de amostragem: um prompt que chega a um middleware de mascaramento de PII contém, por construção, os identificadores que encarecem a tokenização.

**O ADR 0004 não é alterado.** A densidade variável decorre de uma medição que não existia quando ele foi escrito, e a estimativa de custo de PII que ele faz não depende dela — depende do tamanho em caracteres, que é dado diretamente.

### Para o que o trabalho afirma

A afirmação passa de "adiciona menos de 15 ms", sem escopo, para:

> O pipeline adiciona menos de 15 ms de latência, no P95, para prompts de até 10.000 caracteres. A latência típica, no P50, é de 4,84 ms no pior cenário de conteúdo medido e de 3,22 ms no cenário limpo.

Os três números vêm dos artefatos commitados. A afirmação **não inclui a camada de orçamento de tokens**, que ainda não existe: incluí-la exigiria apoiar a frase numa sondagem, e o ADR 0010 a mede antes de ela entrar aqui.

## Premissas assumidas

**O orçamento de 15 ms continua sem fundamentação própria.** Este ADR declara o estimador e o escopo, não a origem do número. Os 15 ms vieram da latência atribuída a um gateway serverless, arquitetura que o ADR 0008 abandonou. A justificativa local — 15 ms são imperceptíveis diante de uma ida e volta de LLM, da ordem de centenas de milissegundos — é provavelmente mais forte, e segue não escrita.

**Uma máquina, um sistema operacional.** Todos os artefatos foram produzidos em Windows 11 com Python 3.14.

**Soma de parcelas isoladas, não medição ponta a ponta.** O custo pelo pipeline completo não é a soma das parcelas, e a medição final deve verificá-lo.

## Trabalho futuro

**Medir o cruzamento diretamente.** O ponto em que a soma atinge 15 ms foi calculado por escala, não medido.

**Justificar o tamanho a partir de prompt real.** Os 10.000 caracteres são o maior tamanho medido, não uma afirmação sobre uso. O corpus de avaliação tem casos de 60 a 365 caracteres, mas é autoral e construído para avaliar injection — não é amostra de uso, e usá-lo para justificar o escopo seria viés de seleção. Uma referência externa sobre tamanho de prompt corporativo tornaria o número justificado, e não apenas declarado.

## Gatilhos de reavaliação

1. O escopo precisar crescer, por evidência de que prompts reais excedem 10.000 caracteres. **Dispara o ADR 0003**, depois de medir a normalização no tamanho novo: hoje o custo acima de 10.000 caracteres é sondagem.
2. A medição final contradizer a soma das parcelas, por efeito de pipeline não capturado pelos benchmarks isolados.
3. A camada de tokens se confirmar mais cara que a sondagem, consumindo a margem de 16%.
4. Surgir medição em outra plataforma.

## Relação com decisões anteriores

As consequências para os ADRs 0003 e 0004 estão nas seções acima, e nenhum dos dois é alterado. Resta um terceiro:

**ADR 0007** — introduziu a faixa de ±23% como régua de ambiente, observada em medianas. Se parte dessa variação for efeito de estimador, e não da máquina, a reprodutibilidade declarada é pessimista. Hipótese ainda não verificada no normalizador; fica registrada como verificação pendente, sem alterar o ADR 0007.
