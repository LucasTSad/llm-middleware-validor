# ADR 0014 — Critério de aprovação da taxa de falso positivo de PII

* **Status:** Aceito em 11/11/2026
* **Data:** 11/11/2026
* **Decisões relacionadas:** ADR 0004 — Detecção de PII em dois estágios; ADR 0007 — Detecção de prompt injection; ADR 0008 — Modelo de ameaça do filtro de entrada e trilha de auditoria; ADR 0012 — Cobertura de PII e o critério de admissão de tipos
* **ADR 0009 — Convenção de medição:** relacionado por **dois** motivos, e nenhum deles é a disciplina de previsão cega, que ele não contém — a convenção de reporte de medições, que vale aqui, e a correção da atribuição falsa feita em `0012:191`, registrada no fim deste documento

## Contexto

A cobertura de PII vai de um tipo para cinco, e a medição que a avalia ainda não tem critério de aprovação. **Medição sem critério não reprova, e medição que não pode reprovar não é verificação — é ilustração.**

O projeto já tentou resolver isso duas vezes, e as duas falharam do mesmo jeito. O gatilho 1 do ADR 0004 manda comparar a taxa medida contra "o limite definido durante a avaliação dos dias 17–20"; aquela avaliação nunca aconteceu, nenhum número foi fixado, e o gatilho ficou inacionável desde setembro. O gatilho 2 do ADR 0005 compara a taxa de placeholders órfãos contra "o limite definido na avaliação", e é inacionável **por construção**, porque o órfão é propriedade da **resposta** da LLM (`0005:76`), que o produto nunca observa — o ADR 0011 o encerra na `Decision`, e obter a resposta o tornaria cliente da LLM, o que `0013:41` já recusou por este mesmo motivo.

O ADR 0012 aponta a obrigação — `0012:207` fala do "limiar que o M2 tiver de definir" — e apontar para uma obrigação é o que torna um gatilho inacionável, não o que o satisfaz.

### O que define a espécie, e por que "nomear um prazo" não basta

É tentador descrever a falha como vagueza. **Não é:** o ADR 0004 nomeou um quando, "os dias 17–20", com precisão de calendário. Os dias passaram, nenhum artefato apareceu, e **nada falhou**. O gatilho ficou silencioso por dois meses, até ser encontrado por acidente.

Portanto a propriedade que define a espécie é outra: **a ausência do número não produz falha que alguém perceba.** Um agendamento verificável não conserta isso — ele torna o compromisso conferível e deixa a omissão tão silenciosa quanto antes. Quem rodar a medição com limiares faltando obtém um relatório com cara de completo.

### O momento

Este registro precede a existência do primeiro detector novo, e isso é condição e não conveniência. Assim que um detector existe ele roda, e qualquer critério escrito depois disso está contaminado pelo que já se viu. A disciplina é a do `0008:95` — "a previsão correspondente será registrada antes da medição, de modo que a sequência permaneça verificável no histórico do repositório" — e a anterioridade se confere por **ancestralidade**, não por data: dois commits do mesmo dia empatam no `git log --date=short` e são decididos por `git merge-base --is-ancestor`.

## Decisão

**O critério de aprovação da taxa de falso positivo é declarado por padrão de reconhecimento, e padrão sem limiar registrado conta como reprovado.**

### A unidade é aplicada, não decidida aqui

A unidade já está fixada em `0012:149`: "a unidade é o **padrão de reconhecimento, não o tipo** — e-mail é um tipo com um padrão, telefone é um tipo com vários". Aquele registro também já conta quantos padrões não têm segundo estágio: **três** — e-mail, telefone nu sem DDD e telefone hifenizado sem DDD — e afirma que nenhum outro dos cinco tipos está nessa situação.

Este registro **aplica** essa unidade ao critério. Escrevê-la como decisão nova criaria segundo registro da mesma decisão, e decisão existe para remover liberdade do implementador — essa já foi removida.

**E a proporção importa para ler o resto:** são três padrões sem segundo estágio contra **todos os demais com**, e não três contra um. O telefone sozinho tem cinco formas (`0012:141`), e somados e-mail, CPF, CNPJ e cartão a enumeração por padrão passa de meia dúzia. O "a fixar" das seções seguintes é a exceção enumerada, não a regra.

### A cláusula da ausência, que é o que torna este registro diferente dos dois anteriores

**Padrão cujo limiar não esteja registrado não pode ser aprovado: a ausência conta como reprovação, e não como "não avaliado".**

O efeito é mecânico. Rodar a medição com três limiares faltando produz **três reprovações**, e um resultado com três reprovações é alto o bastante para não ser publicado. O número passa a ser escrito porque a alternativa dói, e não porque alguém lembrou.

**É a mesma inversão que o projeto acabou de aplicar aos produtores de artefato.** Sobrescrever evidência era silencioso e virou erro: a escrita no caminho commitado recusa se o arquivo existir, de modo que a ausência de decisão sobre sobrescrever passou a ser ruído em vez de omissão. Limiar faltando é silencioso pelo mesmo motivo, e recebe o mesmo tratamento. **Padrão invertido protege de quem não pensou; a falha ruidosa protege de quem não lembrou.**

Isso também é o que torna verdadeira a afirmação do `0012:155`, de que o limite é "agendado e não limiar por procuração". Sem esta cláusula aquela frase seria otimismo sobre o próprio mecanismo.

### A obrigação sobre o `rule_id`, sem a qual o critério é inverificável

**Cada padrão de reconhecimento emite o seu próprio `rule_id`. Não é permitido um `rule_id` servir a vários padrões.**

O motivo é de atribuição, e é conferível no código de hoje. O detector emite `rule_id="pii.cpf.v1"` (`pii.py:77`) e `matched_type="cpf"` (`pii.py:82`), e a trilha grava os dois (`audit.py:32` e `:35`). Com o telefone, `matched_type` valerá `"telefone"` para a forma nua sem DDD e para a hifenizada sem DDD — **os dois padrões de que o critério fala separadamente**. Se o `rule_id` também não os separar, a medição produz um número que não é atribuível a nenhum dos dois, e o critério por padrão deixa de ser verificável por construção.

Nesse estado, nem a cláusula da ausência salva: três reprovações que ninguém consegue atribuir a um ramo não são mais úteis que três silêncios.

O mecanismo já existe — a trilha carrega `rule_id` desde o ADR 0008. O que falta, e é o que esta decisão acrescenta, é a obrigação de que ele seja por padrão.

### O número que pode ser fixado hoje, e por quê

**Só o ramo de onze dígitos com dígito verificador recebe número agora.** O ADR 0004 publica que aproximadamente **1 em 100** sequências aleatórias de onze dígitos passa pelos dois dígitos verificadores.

**Esse 1 em 100 não é uma taxa de falso positivo, e a ressalva é da própria fonte.** O `0004:57` já declara, na mesma linha em que publica o número: "Isso não representa a taxa real de falso positivo do detector, que depende do corpus analisado; telefones e outros números estruturados ainda podem ser confundidos com CPF."

Ele é um **resíduo condicional**: a fração dos *candidatos* que o segundo estágio deixa passar. A taxa de falso positivo é o produto de dois fatores — a **frequência** da forma em texto real, e a **fração que atravessa o segundo estágio**. O resíduo é o segundo fator; o primeiro só existe sobre um corpus.

#### O denominador são os candidatos que não são CPF real

Separando os candidatos de onze dígitos em CPFs reais `R` e não-CPFs `M`, uma implementação correta produz `FP ≈ M × r`, com `r` o resíduo. Então:

```
FP / (R + M)  =  r × M/(R+M)  ≤  r
```

**Dividir pelo total de candidatos produz critério inalcançável:** a razão fica estritamente abaixo do resíduo sempre que o corpus contiver um CPF real, e qualquer teto igual ou acima do resíduo nessa forma é vazio. O denominador correto é `M` — **os candidatos que não são CPF real** —, e aí o medido é a taxa condicional, diretamente comparável ao resíduo.

#### O fator é uma regra derivada, e não um número escolhido

> **O fator é o menor que mantenha a probabilidade de falso alarme abaixo de 5%, dado o número de candidatos não-CPF do corpus.**

Com `p = 1%` e a razão medida sobre `n` candidatos não-CPF, a probabilidade de uma implementação **correta** exceder o teto por acaso é:

| Fator | n = 100 | n = 200 | n = 500 | n = 1000 |
| --- | --- | --- | --- | --- |
| 1 | 26,4% | 32,3% | 38,4% | 41,7% |
| 2 | 7,9% | 5,2% | 1,3% | 0,15% |
| 3 | 1,8% | 0,43% | 0,01% | 0,00% |

**Isso responde com número por que o fator 1 está fora:** o resíduo puro como teto reprovaria implementação correta entre 26% e 42% das vezes. Fator maior que 1 é obrigatório, não folga generosa.

**A regra devolve fator bem definido apenas de `n ≈ 300` em diante**, e o motivo está na seção de dimensionamento adiante: abaixo disso o falso alarme é **dente de serra** e não função decrescente de `n`, de modo que não existe corte do tipo "acima de tanto, fator 2". Na banda irregular o fator tem de ser calculado para o `n` exato do corpus, nunca lido de regra de bolso. O valor 2 é o que a regra devolve para o regime limpo, e é o que vale enquanto o corpus não existir.

#### O resíduo não é constante: ele é função da frequência do dígito zero

A largura acima está orçada **só** para ruído de amostragem. Existe um segundo consumidor dela, e é o que o `0004:57` chama de "números estruturados": corrida de onze dígitos em texto real não tem dígitos uniformes, e o resíduo muda com a distribuição.

**O mecanismo está no cálculo do dígito verificador, e tem forma fechada.** Em `_calculate_dv`, o resto da divisão por 11 menor que 2 devolve DV igual a zero (`pii.py:33-36`), de modo que **dois dos onze resíduos colapsam em DV = 0**. Logo DV = 0 ocorre com probabilidade 2/11 e cada um dos outros nove com 1/11, e a fração que passa por uma posição verificadora é

```
P(casar) = (1/11) × (2·P(d=0) + P(d≠0)) = (1 + P(d=0)) / 11

resíduo  = ((1 + P(d=0)) / 11)²
```

A simplificação vale porque `P(d≠0) = 1 − P(d=0)`, e ela dá de imediato **toda a amplitude analítica do resíduo**: de `0,83%` com nenhum zero a `3,31%` com só zeros — fator quatro de ponta a ponta. **O resíduo é monótono em P(0)** — não em "viés" —, e o modelo confere contra o `is_cpf` do projeto, 400.000 amostras por linha e duas sementes:

| P(dígito zero) | Medido | Modelo |
| --- | --- | --- |
| 0,100 — uniforme | 0,97% e 1,03% | 1,00% |
| 0,200 | 1,22% e 1,22% | 1,19% |
| 0,429 | 1,70% e 1,67% | 1,69% |
| 0,500 | 1,84% e 1,87% | 1,86% |

**O que isso fixa.** O piso de 1% vale para a classe dominante de onze dígitos em texto brasileiro — celular com DDD —, porque os dois últimos dígitos de um telefone são livres; e prefixo fixo não o altera. Essa é a razão de a escada do ADR 0012 existir.

**E dá a classe de risco com nome em vez de magnitude.** O perigo não é "número estruturado" em geral: é **identificador com muitos zeros** — identificador com zero à esquerda, `00012345678`, código no começo de uma faixa. Conferível contando zeros, sem detector nenhum.

**O teto de 3,31% é analítico e inalcançável**, e o motivo é que o modelo supõe o DV independente dos dígitos quando o DV é calculado **a partir** deles: na concentração extrema o DV torna-se previsível, as posições verificadoras forçadas a zero deixam de casar, e `is_cpf` ainda descarta a sequência de dígito único. O efeito, portanto, não cresce sem limite, e o topo observável na faixa plausível é da ordem de 1,7× com P(0) ≈ 0,43 — já extremo para texto real.

**A consequência é de método, e melhora o critério em vez de o enfraquecer: o resíduo entra na regra como parâmetro medido, não como constante herdada.** E ele é **previsível no congelamento, antes de qualquer detector existir** — conta-se a frequência de zero nas corridas não-CPF e a forma fechada devolve o resíduo esperado.

**A contagem é sobre as corridas que não são CPF real, e não sobre todas.** É a mesma população do denominador: CPF real tem distribuição de dígitos própria, então contar todas as corridas preveria o resíduo de uma população que não é a medida. Com a verdade de campo por ocorrência que a seção de restrições exige, a separação sai da mesma rotulagem e não custa trabalho novo — mas escrever "do corpus" faria quem executasse contar tudo.

#### O que este critério não detecta

**Âncora, varredura e precedência não são detectáveis por esta razão, e dizer o contrário seria falso.** Os três são defeitos que **multiplicam candidatos**: um candidato espúrio entra no numerador e no denominador juntos, e a razão fica quase invariante. O caso é concreto — pelo mecanismo descrito em `0012:123`, janelas deslizantes de onze dígitos dentro de uma corrida maior são todas candidatas, e cerca de 1% delas passa no verificador, mantendo a razão em 1%.

O único defeito que move a razão é **o verificador não rodar**, e aí ela vai a `M/(R+M) ≈ 1`. Isso é falha catastrófica que teste unitário pega de graça.

**Logo o instrumento daqueles três defeitos não é taxa, é invariante.** Ela já está escrita em `0012:157`: `\b` nas duas pontas, nenhum casamento dentro de corrida maior. Propriedade se verifica por teste, e esse teste tem implementação errada nomeada que o faria acender — a expressão de telefone escrita sem `\b`.

E uma precisão sobre o que "dentro do fator" significa: a taxa é irredutível **dado o dígito verificador como único filtro**. Um terceiro estágio por contexto a reduziria, e nada aqui afirma que ele seja impossível — apenas que não existe.

**Os três padrões sem segundo estágio não recebem número**, e o motivo é que para eles **os dois fatores** dependem do corpus: não há segundo estágio de onde derivar o resíduo. O `0012:155` já registra que ali "a taxa não é 1%, é desconhecida e maior". Eles entram na medição sob a cláusula da ausência — reprovados até que o número exista.

### A margem, que é o que se confere quando a previsão existir

Critério e previsão são coisas diferentes: critério é tolerância de produto e se decide sem corpus; previsão é previsão de taxa, e taxa é propriedade de um corpus. Por isso **a previsão não está aqui** — nenhum ADR deste repositório carrega previsão, e o `0007:47` apenas cita uma, pelo par de commits. Ela pertence ao documento do corpus de PII, amarrada ao SHA-256 dele, como o precedente do `datasets/README.md` faz.

**O que precisa ser conferido quando ela existir é a margem entre as duas, e não cada número isolado.** Critério de 50% contra expectativa de 1% é critério que não pode reprovar; 1,1% contra 1% é cara ou coroa. Os dois estão acoplados pela margem mesmo que alterar um não altere o valor do outro — e um critério inofensivo passa sem que nada acuse, porque ele *parece* um critério.

Fica declarado, portanto, que a emissão da previsão obriga a reler este registro e a verificar a margem, e que essa verificação é parte da previsão e não deste documento.

## Consequências

**Este registro precede o código**, como o ADR 0012. Hoje existe um único `rule_id` de PII, e os três padrões sem segundo estágio não existem em implementação.

**O que o trabalho poderá afirmar.** Que a taxa de falso positivo foi avaliada contra critério registrado antes de a observação ser possível, por padrão de reconhecimento, com a anterioridade verificável por ancestralidade no histórico.

**O que o trabalho não poderá afirmar.** Que a taxa é aceitável para os padrões cujo limiar não tiver sido fixado. Para eles o resultado é reprovação declarada, e reprovação declarada é resultado — não é ausência de resultado.

**Restrição de implementação.** Um `rule_id` por padrão de reconhecimento, com o padrão identificável no nome. A suíte precisa de um teste que recuse `rule_id` repetido entre padrões distintos, porque a obrigação é verificável e, sem teste, vale o mesmo que o gatilho do ADR 0004 valia.

**Sobre o corpus de PII.** Ele não existe: `datasets/` contém o `README.md` e o `prompt_injection_corpus.jsonl` do corpus de injection. Congelá-lo com SHA-256 declarado é pré-requisito da previsão, e não deste registro.

### Duas restrições que este critério impõe ao corpus, e que precisam ser ditas antes de ele existir

**Verdade de campo por ocorrência, com o span.** O denominador são os candidatos que **não** são CPF real, de modo que computar o critério exige saber, por ocorrência, quais corridas de onze dígitos são CPF e quais não. O corpus de injection rotula por **caso**, no campo `label`; este precisa rotular por **ocorrência**, com as posições. Sem isso o critério é incomputável — e descobrir isso depois de o corpus estar congelado custaria congelá-lo de novo, com hash novo, invalidando a previsão que dependia do primeiro.

**Dimensionamento derivado do critério: o requisito é 10³, e 10² é piso com irregularidade declarada.** Recalculando o falso alarme do fator 2 com o resíduo como parâmetro, e não fixado em 1%:

| Resíduo | n = 100 | n = 200 | n = 500 | n = 1000 |
| --- | --- | --- | --- | --- |
| 1,0% | 7,9% | 5,2% | 1,3% | 0,15% |
| 1,2% | **12,0%** | **9,5%** | 0,84% | 0,06% |
| 1,7% | 9,2% | 5,6% | 0,27% | 0,01% |
| 2,5% | 4,0% | 1,3% | 0,05% | 0,00% |

**A irregularidade é aritmética e não estatística, e aparece nos dois eixos.** O limiar efetivo é `int(n × resíduo × fator)`, de modo que ele **salta em inteiros** enquanto a média cresce continuamente. No resíduo isso dá 7,9% a 1,0% e **12,0%** a 1,2%; em `n` dá dente de serra, com o limiar parado entre saltos:

| n | Limiar | Falso alarme |
| --- | --- | --- |
| 200 | 4 | 5,17% |
| 210 | 4 | 6,12% |
| 220 | 4 | **7,15%** |
| 250 | 5 | 4,12% |
| 290 | 5 | **7,32%** |
| 300 | 6 | 3,28% |
| 500 | 10 | 1,32% |

**Duas consequências, e a segunda é contraintuitiva.** A primeira: já em `n = 200` o valor é 5,17%, **acima dos 5% que a regra promete**, e a violação se repete em 210, 220, 270, 280 e 290 — não existe corte em duzentos. A segunda: **na banda irregular, mais candidatos pioram a garantia** — `n = 290` é pior que `n = 200`. Quem dimensionasse um corpus parando em 290 degradaria o critério de propósito sem saber.

O dente de serra morre por volta de `n = 300`, e dali em diante a ordenação é limpa. **Daí o requisito: ordem de 10³ candidatos não-CPF de onze dígitos.** A ordem de 10² fica declarada como **piso** — abaixo dele o critério não opera —, e entre 10² e o fim da banda irregular o fator tem de ser calculado para o `n` exato, com a garantia obtida declarada no relatório.

**E resíduo maior melhora o dimensionamento, não piora:** em `n = 500`, o falso alarme cai de 1,3% a 1,0% de resíduo para 0,27% a 1,7%, porque resíduo maior concentra relativamente mais. Então a classe de risco dos muitos zeros encarece o critério pelo lado do número e o barateia pelo lado da amostra. **Isso vale no regime limpo, e não na banda irregular**, onde nenhuma monotonia pode ser invocada em eixo nenhum.

Requisito de tamanho é consequência aritmética deste critério, e por isso pertence a este registro e não ao do corpus. **E é conferível antes de o corpus ser aceito**, porque tanto a contagem de candidatos não-CPF quanto a frequência de zero neles se medem sem detector.

## Uma atribuição falsa, corrigida aqui

O `0012:191` afirma que o limiar precede a medição "pela mesma disciplina de previsão cega que o ADR 0009 exige". **O ADR 0009 não exige isso:** ele é o registro de convenção de medição, sobre estimador, escopo por tamanho e o que uma tabela de amostras autoriza afirmar, e não contém as palavras "cega", "cego" nem "previsão".

A disciplina existe e mora em três lugares: a obrigação em **`0008:95`**; a prática em **`datasets/README.md`**, com hash do corpus, rótulo de regime item por item e cláusula de falsificação; e o precedente em **`0007:47`**, citado pelo par de commits.

**O ADR 0012 não é corrigido.** Registro commitado descreve o que era afirmado quando foi escrito, e reescrevê-lo destruiria a procedência — é o movimento do `0011:70-78`, que refutou dentro do registro novo e deixou o antigo intacto. A anotação fica aqui.

## Gatilhos de reavaliação

* **A medição do M2 reprovar um padrão por exceder o fator.** Não dispara revisão de âncora, varredura ou precedência, que esta razão não mede, e **não** dispara revisão do critério, escrito antes justamente para não ser ajustado ao resultado.

  **Restam duas causas possíveis, e a mais provável não é defeito do padrão:** o verificador não estar rodando, ou **o resíduo previsto estar errado**. As duas se separam **sem medição nova** — recontar os zeros nas corridas não-CPF e comparar com a forma fechada. Se o previsto bate com o medido, a causa é o padrão e o gatilho dispara a revisão do segundo estágio; se não bate, a causa é a previsão, e o que se revisa é o resíduo. Sem esta distinção, uma reprovação por resíduo subestimado viraria revisão de segundo estágio que não tem o que consertar;
* **A frequência do dígito zero nas corridas de onze dígitos que não são CPF real indicar resíduo acima de 1%.** Nesse caso o fator é recalculado sobre o resíduo previsto pela forma fechada, e não sobre a constante herdada do ADR 0004. Verifica-se **contando zeros nessas corridas** — as mesmas do denominador, nunca todas as do corpus —, sem detector e antes do congelamento;
* **O corpus trazer menos de 10³ candidatos não-CPF de onze dígitos.** Entre 10² e 10³ o critério opera com garantia degradada e irregular, e isso tem de ser declarado no relatório em vez de silenciado; abaixo de 10² ele não opera, e o padrão cai na cláusula da ausência;
* **Um padrão de reconhecimento passar a existir sem `rule_id` próprio.** Verifica-se por inspeção do detector, e é o que a restrição de implementação acima proíbe;
* **A previsão ser emitida.** Obriga a conferência da margem descrita acima. É o único gatilho deste registro que depende de trabalho futuro, e ele nomeia o que conferir em vez de nomear uma data.

## Relação com decisões anteriores

**Satisfaz o que o gatilho 1 do ADR 0004 pedia e nunca recebeu.** Aquele gatilho permanece como está, inalterado e inacionável na sua própria redação; o número que ele manda comparar passa a existir aqui, para o ramo que ele nomeia.

**Não conserta o gatilho 2 do ADR 0005**, e é preciso dizer. Aquele é inacionável por construção, porque o placeholder órfão só existe na resposta da LLM, que está fora da fronteira que o ADR 0011 fechou. Nenhum critério o torna acionável — não é limiar que falta, é observação — e este registro não o tenta.

**Aplica a unidade de contagem do ADR 0012** e não a redecide.

**Usa o resíduo publicado no ADR 0004** como parâmetro, sem o confundir com taxa medida — e a distinção não é acréscimo deste registro: ela está na mesma linha `0004:57` que publica o número, que já declara não representar a taxa real do detector.
