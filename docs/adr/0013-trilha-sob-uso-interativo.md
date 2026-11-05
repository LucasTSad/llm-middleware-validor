# ADR 0013  O custo em dólar sai e a trilha registra o que saiu em claro

* **Status:** Aceito em 05/11/2026
* **Data:** 05/11/2026
* **Decisões relacionadas:** ADR 0005  Mascaramento reversível; ADR 0006  Precedência por máximo de ações; ADR 0008  Modelo de ameaça do filtro de entrada e trilha de auditoria; ADR 0010  Camada de orçamento de tokens; ADR 0011  A interceptação se realiza como fronteira de chamada; ADR 0012  Cobertura de PII e o critério de admissão de tipos

## Contexto

A trilha de auditoria nunca teve chamador. O ADR 0010 registra isso ao dizer que ela não tem um único registro em disco e o ADR 0011 o declara como ressalva: `record` é capacidade oferecida e não exercida exercida apenas por teste.

Isso está prestes a mudar. O produto passa a ter uma forma de uso interativa ,a pessoa submete o texto, vê os achados e decide o que fazer antes de enviar e com ela `record` ganha o primeiro chamador real. **O formato da trilha deixa de ser hipótese e passa a ser dado em disco.**

É a última janela em que o formato se altera de graça. Depois da primeira linha gravada, mudar a enumeração mistura dois formatos no mesmo arquivo e o torna incomparável sem que nada acuse o problema  é o argumento que o ADR 0010 usou para declarar `rule_id` e `matched_type` antes da implementação e aqui ele é mais forte, porque lá não havia arquivo e aqui vai haver.

Duas mudanças de formato estão pendentes e nenhuma delas cabe nos registros que as originaram, porque os dois estão commitados: a enumeração da **Parte II do ADR 0008** e a subdecisão de custo do **ADR 0010**.

### Por que um registro com duas partes e não dois registros

O teste deste projeto é a revertibilidade: um registro, uma decisão, revertível sozinha. Aplicado ingenuamente, ele mandaria separar  tirar o custo não depende de registrar o envio em claro e vice-versa.

**O que as une não é o tema, é o artefato.** As duas alteram a mesma enumeração do mesmo arquivo de saída e a razão de urgência das duas é a mesma linha ainda não gravada. Separá-las autorizaria uma a entrar sem a outra e o resultado seria um terceiro formato  sem custo e sem o campo novo, ou com os dois  que ninguém decidiu e que existiria apenas pelo intervalo entre dois commits. **Formato de registro muda uma vez, ou cria versão intermediária que alguém vai ler depois sem saber que ela existiu.**

É o mesmo motivo que deu duas partes ao ADR 0008 e a forma vem dele como precedente. O que faria disto dois registros seria uma das duas mudanças não tocar a trilha  e as duas tocam.

## Parte I  O custo em dólar sai do produto

### Decisão

**O custo estimado em dólar é removido do produto.** Saem o campo `price_per_1k_tokens_usd` do `GuardConfig`, o campo `estimated_cost_usd` da `Decision` e a chave `estimated_cost_usd` da trilha.

O motivo é de escopo e é verificável no aceite: ele nomeia **"custos elevados com tokens"**. Token é a unidade que o aceite pede e o produto a conta. O dinheiro foi acréscimo do ADR 0010, que o justificou como "o que o orçamento financeiro precisa" (`0010:109`)  necessidade real de quem administra orçamento e que o aceite não pediu.

### O que a remoção derruba junto e é por isso que ela compensa

Um preço configurado por quem usa arrasta cinco obrigações que nada no aceite exige:

* **a unidade implícita**  "por 1k tokens" é convenção e de qual modelo não se diz;
* **a validade no tempo**  preço de provedora muda e registro antigo passa a mentir sobre um valor que já estava gravado;
* **a licença da tabela**  distribuir preços de terceiro é problema próprio e evitá-lo significava exigir que a pessoa digitasse o seu;
* **o CRUD de preços salvos**  guardar editar e versionar o que a pessoa digitou;
* **o tamanho da saída**  custo real inclui os tokens que a LLM devolve e o produto não os conhece. Estimá-los seria chute; medi-los exigiria fazer a requisição, o que tornaria o produto o cliente da LLM.

Nenhuma das cinco mede economia de token, que é o que o risco do aceite nomeia. **O que sai é a conversão para moeda; a medição de economia fica inteira**  `token_count` e `token_delta` permanecem e é neles que o terceiro risco se verifica.

### Onde o código é tocado

| Arquivo | Linhas |
| --- | --- |
| `core/contracts.py` | 136 (`estimated_cost_usd` na `Decision`), 176 (`price_per_1k_tokens_usd` no `GuardConfig`) |
| `core/engine.py` | 131, 132, 140, 150 |
| `adapters/audit.py` | 18 (campo do `RecordAudit`), 42 (chave do registro) |
| `tests/test_contracts.py` | 189, 205 |
| `tests/test_engine.py` | 457, 462, 469, 486, 490, 494 |

A enumeração é a lista de exclusões: o que não está nela não sai. A `test_engine.py:490` entra por aritmética e não por nome  é a linha que calcula o valor esperado  de modo que procurar o identificador não a encontra.

### O que isto reverte em registro já commitado

**Do ADR 0010, uma subdecisão inteira e não uma menção.** A subdecisão do `float | None` se apoia no campo: a tabela de contratos (`0010:75`), a aritmética que liga as três contagens (`0010:78`), o diagnóstico de que `0.0` é indistinguível de "configurado como gratuito" (`0010:98`), a passagem para `None` com `audit.py` e `RecordAudit` acompanhando (`0010:102`) e o fecho que afirma que "`price_per_1k_tokens_usd` passa a decidir entre custo estimado e `None`" (`0010:159`).

Aquele fecho tem três campos  `max_tokens`, `encoding_name` e `price_per_1k_tokens_usd`  e dizia que o `GuardConfig` deixa de prometer controle que não exerce. **Um terço dele cai e o resto continua verdadeiro**: `max_tokens` é aplicado e `encoding_name` é lido na fronteira. A frase não fica falsa por inteiro; fica falsa na terceira parte, o que é pior de notar e é por isso que está escrito aqui.

**Do ADR 0008, uma chave da enumeração da Parte II** (`0008:135`): "`token_count` e `estimated_cost_usd`, quando a camada de orçamento existir". A camada existe e a chave não.

Os dois registros permanecem Aceitos e inalterados. Quem declara a reversão é este.

### A autorização e a assimetria que é fácil de errar

Há duas intervenções pendentes na **mesma Parte II do ADR 0008**, por caminhos opostos:

* **a reescrita da justificativa do `sanitized_text`**, que o gatilho 3 daquela parte pede e que o ADR 0012 acionou, é **correção dentro** do 0008. Cabe sem registro novo pelo precedente `6d9d46b`  a regra do próprio 0008 exige ADR novo para **alterar, retirar ou inverter** uma decisão e reescrever justificativa sem mexer na decisão não faz nenhuma das três;
* **a remoção do custo** retira uma chave e inverte a subdecisão do `float | None`. Faz duas das três e por isso exige este registro.

**Mesma seção atingida, autorizações opostas.** Quem fizer as duas na mesma sessão de trabalho vai querer um commit só e o commit único apagaria a distinção: um pedaço autorizado por precedente de correção, outro por decisão nova. Vão em commits separados e a mensagem de cada um diz qual autorização usa.

### O que o trabalho deixa de poder afirmar

Que estima o custo financeiro do prompt. Nunca pôde afirmar o custo **total**, porque a saída da LLM não é conhecida e agora não afirma nem a parcela de entrada.

O que continua afirmável é o que o aceite pede: que conta os tokens do texto, aplica um teto e **mede** quantos tokens o mascaramento economiza.

## Parte II  A trilha registra o que saiu em claro

### O problema: dois eventos diferentes, um registro idêntico

A forma de uso interativa permite que a pessoa desfaça o mascaramento de um achado  é o trabalho futuro que o ADR 0012 declara, viabilizado pelo mapa de `placeholders` do ADR 0005 e acontece **depois** da `Decision`.

Com o formato atual, dois eventos materialmente opostos produzem registro **idêntico**:

* o dado foi detectado, mascarado e o texto mascarado foi enviado;
* o dado foi detectado, mascarado, a pessoa desfez o mascaramento e o dado foi enviado **em claro**.

Os dois gravam `action: "sanitize"`, um finding, `matched_type: "cpf"`, as mesmas posições e o mesmo `score`. Nada no registro os separa.

**Isso é pior que ausência de registro.** A trilha é artefato de evidência pelo ADR 0008 e aqui ela não deixaria de informar: ela afirmaria proteção onde não houve. É a mesma classe de defeito que o ADR 0012 nomeia no terceiro custo do falso positivo  contar errado não é inofensivo  e a mesma regra que o projeto já aplicou ao ampliar o aviso de sobrescrita: **registro parcial é pior que registro ausente, porque o ausente faz perguntar e o parcial responde errado.**

E a forma de uso agrava em vez de atenuar: a trilha é exibida a quem usa. A pessoa leria "CPF protegido" numa linha que ela sabe ter enviado em claro e a primeira coisa que ela aprenderia sobre a trilha é que ela não é confiável.

### Decisão

**Cada finding da trilha passa a registrar se o dado correspondente saiu em claro.** A chave é `sent_in_clear`, do tipo `bool | None`, presente em todo finding de todo registro.

| Valor | Significado |
| --- | --- |
| `false` | o dado foi mascarado e o texto enviado traz o marcador no lugar dele |
| `true` | o dado saiu em claro no texto enviado |
| `null` | nada foi enviado  a ação foi `BLOCK` |

### O campo não responde sozinho "houve escolha" e a derivação fica escrita

Só achado de PII vai ao masker: `Engine.analyze` filtra `Category.PII_DISCLOSURE` antes de ordenar por posição (`engine.py:116`). A consequência é que `true` cobre **dois eventos diferentes**  alguém desfez uma proteção e isto nunca foi mascarável. Um achado de injection sai em claro porque mascarar injection não é o que o produto faz.

A pergunta que motivou este campo continua respondida, mas por derivação e não pelo campo isolado:

> houve escolha de quem usa quando `category == PII_DISCLOSURE` **e** `action == SANITIZE` **e** `sent_in_clear == true`.

**A derivação é exata e é o filtro do masker que a torna exata:** na ação `SANITIZE` todo achado de PII vai ao mascaramento, de modo que um achado de PII em claro ali só pode ter saído assim por decisão de alguém.

Está escrito porque a conta errada é fácil e silenciosa: **quem contar `true` como "desfeitos" superconta**, somando todo achado de injection de todo registro. Seria registro parcial respondendo errado um nível acima do defeito que esta parte conserta  não mais no campo e sim em quem o lê.

### Dois estados que o espaço admite e o código não produz

**PII com `ALLOW` é inalcançável.** `action_for_finding` manda todo `PII_DISCLOSURE` para `SANITIZE` e `decide_action` toma o máximo por prioridade  então um achado de PII força a ação para `SANITIZE` no mínimo e para `BLOCK` se a severidade alcançar o teto.

**Para `BUDGET_EXCEEDED` o campo é constante.** Achado de orçamento cai no `return Action.BLOCK` final de `action_for_finding` e `BLOCK` é a prioridade máxima  então todo registro com achado de orçamento tem ação `BLOCK` e o campo vale `null`, sempre. Campo que admite um único valor para uma categoria não informa nada ali e dizê-lo evita que alguém procure significado na variação que não existe.

**As duas inalcançabilidades são consequência de comportamento testado e estes são os testes que as sustentam** em `tests/test_engine.py`:

| Teste | O que fixa |
| --- | --- |
| `test_finding_pii_low_sanitize` | achado de PII decide `SANITIZE` |
| `test_pii_score_nao_influencia_decisao` | o score de PII não muda a ação |
| `test_pii_score_alto_nao_bloqueia` | score alto de PII não escala para `BLOCK` |
| `test_injection_fraca_com_pii_sanitize` | com injection fraca, que decidiria `ALLOW`, o PII puxa para `SANITIZE` |
| `test_categoria_budget_exceeded_block` | achado de orçamento decide `BLOCK` |

**Nenhum deles fabrica o estado inalcançável** e é por isso que não há teste a escrever aqui: eles fixam a invariante que torna o estado impossível e um teste do estado em si precisaria construí-lo à mão para afirmar que ele não se constrói. O quarto é o que fecha o caso do `ALLOW`, porque é o único em que `ALLOW` concorre de verdade.

**O efeito prático é que a declaração não pode ficar falsa em silêncio.** Se alguém tornar PII sensível a score  espelhando o ramo de injection, que é a implementação errada plausível  o `test_pii_score_nao_influencia_decisao` acende e com ele esta seção. É a diferença exata com o caso do `max_tokens`, cuja declaração não tinha nada atrás: o campo era configurável e nada o exercitava.

### Por que não é um booleano de override

A formulação óbvia seria um booleano dizendo "a pessoa desfez o mascaramento deste achado", com `false` por padrão. Ela está errada e o modo de errar é exatamente o que esta parte foi escrita para evitar.

`false` nesse campo significaria "não desfeito" e um achado de um registro `ALLOW` nunca foi mascarado  não havia o que desfazer. Ele gravaria `false` e um leitor contando achados protegidos contaria esse também. **O campo descreveria a interação e a pergunta da trilha é sobre o dado.** A versão que erra é a que nomeia o gesto; a que serve é a que nomeia o destino do dado.

Daí decorre o terceiro estado. Em `BLOCK` nada foi enviado e os dois valores de um booleano afirmariam algo falso: `true` diria que o dado saiu, `false` diria que ele saiu protegido. **Os três estados são irredutíveis porque há três destinos possíveis, não porque o tipo seja conveniente.**

**Esta decisão remove um campo `X | None` na Parte I e acrescenta outro aqui e os dois casos são opostos.** A diferença não é ter leitor, que seria critério fraco: é o que o `None` significa e se algum caminho o produz.

No `estimated_cost_usd`, `None` significava **"o produto não sabe"** e sem preço configurado era o **único** valor que se produzia  o outro lado existia no contrato e não no uso. É o vício que o ADR 0010 consertou e que agora se resolve por remoção.

No `sent_in_clear`, `None` significa **"não aconteceu"** e um caminho real e comum o produz: todo registro de ação `BLOCK`. **`None` nunca produzido é defeito; `None` produzido por caminho real é modelagem.**

### Onde o dado entra e por que `record` muda de assinatura

`record(decision, file)` recebe hoje só a `Decision` e `Decision` e `Finding` são `frozen=True`. A escolha da pessoa acontece **depois** de `analyze` devolver a `Decision`, de modo que o dado não pode vir de dentro dela: não há como mutar e reconstruir a `Decision` faria o chamador fabricar um objeto que o núcleo deveria ser o único a produzir.

**`record` passa a receber as escolhas como segundo dado de entrada.** O que o núcleo produz continua sendo só o que ele observou; o que a pessoa decidiu chega pelo chamador, que é quem sabe. Isso é coerente com o ADR 0011: `record` é função que o produto oferece ao chamador e não etapa que a `Decision` dispara.

**O caso sem escolha alguma precisa ser decidido, não deixado em branco.** Um chamador que importe o núcleo e chame `record` sem passar escolhas  biblioteca, teste, script  está no caso em que nada foi desfeito. Aí `sent_in_clear` é `false` para os findings mascarados e `null` quando a ação foi `BLOCK` e isso é afirmação verdadeira e não valor padrão de conveniência: ninguém desfez nada porque não havia interface para desfazer.

### A identidade do finding, que não pode ser a posição na lista

As escolhas precisam ser atribuídas aos findings certos e **índice na lista não serve**. `Engine.analyze` monta `all_findings` na ordem dos detectores enquanto o que vai ao masker é uma cópia ordenada por `start` (`engine.py:116`). São duas ordens diferentes do mesmo conjunto e um índice colhido de uma delas aponta para outro achado na outra  com dois tipos de PII no mesmo texto, o erro é de atribuir o desmascaramento de um ao outro.

**A chave é o par `(start end)`**, que é o que identifica o trecho e o que o ADR 0012 já usa como unidade de precedência. Ele é único por construção dentro de um registro: o masker exige achados sem sobreposição e dois achados não podem compartilhar o mesmo par sem violar essa precondição.

### O que isto não decide

Não decide a aparência da tela, nem como a escolha é apresentada. Decide o que a trilha grava, que é o que fica em disco depois de a tela fechar.

Também **não** cria granularidade de mascaramento por tipo no `GuardConfig`. A exclusão registrada no ADR 0012 continua valendo e não é tocada: lá a questão é configurar, antes da `Decision`, quais tipos o produto mascara; aqui a questão é registrar, depois da `Decision`, o que de fato foi enviado. São momentos diferentes do mesmo pipeline.

## Consequências

**O formato da trilha muda uma vez e antes da primeira linha.** Depois disto, mudança de enumeração só com registro novo e com decisão explícita sobre o que fazer com as linhas antigas  que é problema que este registro existe para não criar.

**A suíte de testes da trilha cresce.** Três estados de `sent_in_clear` vezes a presença ou ausência de escolhas, mais o caso de atribuição com dois achados no mesmo texto, que é o que prova que a chave por span funciona. O caso que não pode faltar é o par de registros que o problema desta parte descreve: mesmo texto, mesmo achado, uma vez com o mascaramento mantido e uma vez desfeito e os dois registros têm de **diferir**.

**Dois commits, não um**, pelo motivo da assimetria de autorização descrita na Parte I.

**A ressalva do ADR 0011 estreita.** "Auditar" deixa de ser capacidade oferecida e não exercida assim que a forma de uso interativa chamar `record`. A outra metade da ressalva continua: nada obriga a chamada.

## Trabalho futuro

**O que a trilha ainda não registra é o texto enviado** e isso não muda aqui. O `sanitized_text` continua fora, pelo ADR 0008 e `sent_in_clear` é o que permite reconstruir o que aconteceu com cada dado sem arquivar o dado  que é a razão daquela decisão.

**A justificativa dessa subdecisão continua pendente de reescrita**, pelo gatilho 3 da Parte II do ADR 0008, acionado pelo ADR 0012. Este registro não a faz e nomeá-la aqui é o que impede que ela dependa de alguém lembrar.

## Gatilhos de reavaliação

* **O produto precisar afirmar custo financeiro.** Isso reverte a Parte I e exige decidir antes as cinco obrigações que ela derruba  em particular de onde vem o preço e o que acontece com registro antigo quando ele muda;
* **A trilha ganhar um segundo chamador com outro modelo de interação.** Se um chamador puder desfazer mascaramento por outro caminho, `sent_in_clear` continua respondendo a mesma pergunta, mas a atribuição por `(start end)` precisa ser conferida contra o novo caminho;
* **A precondição de não sobreposição do masker ser relaxada.** Ela é o que torna o par `(start end)` único e sem ela a chave de atribuição deixa de ser chave. É gatilho sobre o ADR 0005, verificável por inspeção do contrato.

## Relação com decisões anteriores

**Reverte parcialmente o ADR 0010**, na subdecisão de custo e o deixa inalterado no restante: o teto de `max_tokens`, a contagem com encoder injetado e o `token_delta` seguem como decididos.

**Retira uma chave da enumeração do ADR 0008 Parte II e acrescenta outra**, sem tocar a decisão de não arquivar o texto.

**Realiza o trabalho futuro declarado no ADR 0012**  seleção do mascaramento por quem usa  na forma que aquele registro previu: depois da `Decision`, pelo mapa de `placeholders`, sem granularidade no `GuardConfig`. A exclusão registrada lá não é acionada.

**Exerce a fronteira do ADR 0011.** O chamador que decide é o mesmo que invoca `analyze` e depois `record`, no mesmo processo, sem transporte entre os dois.
