# ADR 0012 — Cobertura de PII e o critério de admissão de tipos

* **Status:** Aceito em 04/11/2026
* **Data:** 04/11/2026
* **Decisões relacionadas:** ADR 0001 — Pipeline de detectores com núcleo isolado; ADR 0004 — Detecção de PII em dois estágios; ADR 0005 — Mascaramento reversível; ADR 0006 — Precedência por máximo de ações; ADR 0008 — Modelo de ameaça do filtro de entrada e trilha de auditoria
* **Decisão irmã:** ADR 0011 — A interceptação se realiza como fronteira de chamada

## Contexto

O aceite nomeia "vazamento de dados sensíveis" entre os três riscos. O detector reconhece **CPF, e nada mais**.

Esse recorte nunca foi decidido. O ADR 0004 decide **como** detectar CPF e não decide parar nele; o ADR 0008 apenas constata a consequência, numa frase: o `sanitized_text` carrega em claro toda a PII que o detector não reconheceu. Dos três riscos do aceite, dois foram recortados com justificativa registrada — injection no ADR 0008, tokens no ADR 0010 — e este foi recortado **por omissão**.

A pergunta que faltava responder não era "por que parar no CPF", e sim **qual é o critério para um tipo entrar**. Sem ele, cada tipo novo é discussão do zero e a ausência de qualquer um é indefensável.

### Uma confusão a desfazer antes

Uma versão anterior deste registro propunha manter apenas o CPF, com o argumento de que os demais tipos não têm validador determinístico. O argumento confunde duas coisas:

* **determinístico** — mesma entrada, mesma saída, sem modelo estatístico e sem rede. É o que o ADR 0001 exigiu ao descartar LLM secundária e aprendizado de máquina;
* **validável** — existe verificação que decide se o dado é *real*, e não apenas se tem a forma certa.

Uma expressão regular de e-mail é **inteiramente determinística**. Ela não valida existência, o que é outra propriedade. A exigência do ADR 0001 é a primeira, e o e-mail a cumpre.

A regra dos dois estágios do ADR 0004 também não era universal: era **remédio para um primeiro estágio fraco**. Onze dígitos é sinal fraco — telefone, número de pedido e código de rastreio têm onze dígitos —, e o dígito verificador existe para consertar isso. Um tipo cujo primeiro estágio já é forte não precisa do mesmo remédio.

## Decisão

**A cobertura de PII se estende a cinco tipos: CPF, e-mail, telefone, CNPJ e cartão.**

### Antes do critério: o que esta decisão cobre, e o que ela estreita

O aceite nomeia **"vazamento de dados sensíveis"**. Este registro decide sobre **PII** — dado pessoal identificável. As duas categorias não coincidem, e o estreitamento precisa ser declarado aqui, porque um registro escrito para acabar com recorte por omissão não pode se apoiar em um.

**Credencial é o caso que a diferença expõe**: chave de API, token e senha são sensíveis sem serem pessoais. O ADR 0008 já observa que chave de API não existe no detector.

Credencial **passa** no critério de admissão abaixo — prefixos como `sk-`, `ghp_` e `AKIA` são primeiros estágios mais específicos que o de e-mail, e a detecção é determinística. Ela fica fora por outro motivo, de natureza e não de viabilidade: **a ação correta para ela não está decidida.**

Todo o mecanismo deste registro pressupõe a ação resolvida. Os cinco tipos são PII, e para PII a resposta é a mesma e já está no ADR 0006: achado vai para `SANITIZE`, o dado não chega à LLM, a tarefa continua.

E a pressuposição é estrutural, não só editorial: **ação por tipo não é representável.** `action_for_finding` despacha por `Category`, e `matched_type` não entra em nenhum dos seus ramos — ele é lido depois, por `mask`, via `matched_type.upper()`, para formar o rótulo, e por `record`, na chave `"matched_type"` de cada finding da trilha. O tipo decide o rótulo; a categoria decide a ação.

E esse despacho é **decidido, não incidental** — o código diz o que acontece, não se é de propósito, e quem afirma o propósito é o ADR 0006: "o `score` participa da decisão somente nas categorias cuja política o utiliza". Sem essa oração, um leitor pode tomar o despacho por categoria como acidente de implementação, e aí o que aqui é razão para excluir um tipo vira bug a consertar.

A consequência é que **acrescentar credencial como tipo de PII a manda para `SANITIZE` por construção**, sem que ninguém tenha decidido isso — e é por isso que ela não é "um sexto tipo numa lista".

Cuidado com o passo seguinte, que seria falso: **isto não diz que a arquitetura não possa bloquear credencial.** A primeira verificação de `action_for_finding` avalia `severity >= block_severity` antes de olhar a categoria, então um achado com severidade alta bloqueia hoje, sem nenhuma lógica por tipo. O que não existe é escolha **por tipo**. A ação está indecidida, não inexpressável.

Para credencial, `SANITIZE` não é obviamente certo. Pode ser que mascarar e seguir baste, pode ser que o envio deva ser recusado, pode ser que o ponto seja avisar quem precisa rotacionar a chave — e nada disso está decidido. **Um tipo cuja ação correta está em aberto não pode entrar num registro construído sobre a pressuposição de que ela está resolvida.** Decidir qual é essa ação é trabalho próprio, sobre a política do ADR 0006, e não cabe de passagem num registro de cobertura.

Note-se o que esta razão **não** afirma: que credencial seja `BLOCK`. Afirmar isso aqui seria decidir a política do ADR 0006 numa linha de outro registro, e seria pior fundamentado do que parece — `[APIKEY_1]` impede o vazamento tanto quanto `[CPF_1]`, de modo que "credencial é capacidade ativa" não leva, por si, a recusar o envio. A exclusão não precisa que `BLOCK` esteja certo; basta que a ação esteja indecidida.

É essa formulação que mantém **cartão** dentro sem contradição. Cartão também é capacidade, em algum grau, e se a exclusão dependesse de um eixo de capacidade seria preciso dizer onde nesse eixo a linha cai — o que este registro não faz e não precisa fazer. Cartão entra porque é PII e porque sua ação **está** decidida: `SANITIZE`, como os outros quatro.

**Fica registrado como não-cobertura declarada, por categoria.** Dados sensíveis que não sejam PII — credenciais em primeiro lugar — estão fora deste trabalho, e entram, se entrarem, por ADR que decida a ação antes de decidir o detector.

### O critério de admissão

Um tipo entra quando sua detecção é **determinística** e seu primeiro estágio é **específico o bastante para que o falso positivo seja raro ou barato**. Não se exige validação de existência, que nenhum filtro local pode fazer para e-mail ou telefone.

**E o que este registro fixa são formas e comprimentos, nunca expressões.** O teste é direto: se o M2 escrever expressões diferentes das sondadas aqui e elas pegarem as mesmas formas, este registro **não precisa mudar** — logo ele declara o que o produto promete reconhecer, e não como. Nomear expressões faria de qualquer troca de regex uma edição de ADR, e aí o registro seria especificação de detector em vez de decisão de cobertura. As sondagens citadas adiante usam padrões hipotéticos, de propósito: servem para demonstrar um efeito, não para prescrever uma implementação. Condição de correção — Luhn sobre os dígitos, separador consistente, âncora nas duas pontas — não é exceção a esta regra: sem ela a cobertura declarada não é alcançável por nenhuma expressão.

### A tese: recall sobre precisão, e o que a sustenta

A escolha entre errar para mais e errar para menos não é simétrica neste produto, e a assimetria **não** vem do mascaramento ser reversível. Vem de duas propriedades mais básicas:

* **transmissão é irreversível.** O falso negativo manda o dado para fora da máquina, e depois disso nada no produto o alcança. É o risco inteiro que o aceite nomeia;
* **inspeção não destrói.** `analyze(text) -> Decision` recebe uma string e devolve um objeto novo: não consome, não substitui, não apaga. O chamador continua com o texto original que ele mesmo passou, independentemente do que o detector achou.

**Porque transmitir é irreversível e inspecionar não é, favorecer recall é a escolha correta, e não uma concessão.**

O mapa de `placeholders` do ADR 0005 é conveniência e não sustentação: ele serve para restaurar a **resposta** da LLM, que é outra necessidade. A tese vale mesmo sem ele.

### Os três custos do falso positivo, e só um é desprezível

| Custo | Estado |
| --- | --- |
| O dado em si | **neutro** — o original nunca saiu das mãos do chamador |
| A tarefa do usuário | **não medido, e não mensurável nesta arquitetura** |
| A trilha e a medição | **real, e é o que obriga declarar onde falta segundo estágio** |

**Sobre o segundo, que é o mais incômodo.** Quem recebe o texto mascarado é a LLM, e um prompt com marcadores espúrios pode ficar pior de responder. Esse custo existe, não é limitado, e **este produto não consegue medi-lo por construção**: aferir degradação de resposta exigiria uma LLM, e o ADR 0001 descartou LLM secundária. Fica declarado como não medido e não mensurável aqui — e não como "pequeno", que seria afirmação de grandeza sem artefato.

**Sobre o terceiro.** A trilha é artefato de evidência pelo ADR 0008, e um achado espúrio corrompe a contagem que ela registra. Mascarar errado é inofensivo para o dado; **contar errado não é**. O que torna esse custo real é a **função** da trilha, não quem a lê: artefato de evidência com contagem errada é defeito do artefato, independente de haver leitor.

Isso **não** se transforma em exigência de segundo estágio para toda a classe plausível, e dizê-lo seria falso neste próprio registro: **e-mail não tem segundo estágio** — a classe é definida por forma específica sem verificação de existência —, e a forma de telefone sem DDD também não. O que o custo da trilha obriga é **declarar onde o segundo estágio falta**, caso por caso, em vez de deixar a ausência implícita: é o que a escada faz para o telefone e o que a tabela de classes faz para o e-mail. Ausência declarada é mensurável pela medição do M2; ausência implícita vira número que ninguém sabe ler.

### Duas classes de tipo, e é isso que o `score` passa a significar

| Classe | Tipos | Segundo estágio | `score` |
| --- | --- | --- | --- |
| Validado | CPF, CNPJ, cartão | dígito verificador: módulo 11 para CPF e CNPJ, algoritmo de Luhn para cartão | 1.0 |
| Plausível | e-mail, telefone | forma específica, sem verificação de existência | abaixo de 1.0 |

Os algoritmos são nomeados de propósito: são definições públicas e verificáveis, não medições, e omiti-las deixaria dois implementadores escreverem coisas diferentes a partir deste registro.

O campo `score` já existia no `Finding`, com `1.0` de padrão, e passa a carregar a classe do achado.

**São duas classes, e dentro da plausível há duas intensidades.** Classe é **espécie** de evidência; score é **força**. O telefone com DDD consulta a tabela de códigos de área, isto é, tem segundo estágio; o telefone sem DDD não tem nenhum, como a subseção da escada registra. São evidências de forças diferentes dentro da mesma espécie, e dar a elas o mesmo score faria o campo não informar nada — o que contradiria o título desta seção. Não se cria terceira classe para isso: o score existe exatamente para graduar dentro da classe, já é informativo e já vai para a trilha. Se ele não distinguir as duas, volta a ser campo sem leitor com valor diferente de 1.0.

**Isto não destrava o item adiado do ADR 0004, e é preciso dizer, porque a semelhança engana.** Aquele item é:

> "**Emitir candidatos com DV inválido** e score baixo: adiado **até que `decide_action` utilize score também para decisões de PII**."

São dois casos diferentes: lá, um tipo que **tem** dígito verificador e **falhou** nele; aqui, um tipo que **não tem** dígito verificador. E a condição de desbloqueio daquele item é `decide_action` passar a usar score para PII — que é exatamente o contrário do que esta decisão faz logo abaixo. **O item do ADR 0004 continua adiado**, e este registro não se apoia nele.

**O `score` não altera a ação.** `decide_action` manda todo `PII_DISCLOSURE` para `SANITIZE`, qualquer que seja o score, e isso é consequência direta da tese acima: um achado plausível é mascarado como um validado. O score é registrado na trilha e não consumido pela decisão — o que é declarado aqui de propósito, para não repetir o defeito do `max_tokens`, que era configurável e silenciosamente não aplicado.

### A escada do telefone

Telefone e CPF colidem: ambos podem aparecer como onze dígitos nus. A discriminação se faz por ordem de teste, e **não** pela ausência de CPF — "não é um CPF" não implica "é um telefone", porque número de pedido, código de rastreio e matrícula também falham no dígito verificador.

Para onze dígitos nus:

1. passa no validador de CPF → **cpf**, classe validada;
2. falha no validador de CPF, **e** tem DDD pertencente à lista de códigos de área em vigor seguido do 9 obrigatório de celular → **telefone**, classe plausível. A lista é finita e precisa ser citada por **fonte** na implementação, porque é dado externo ao projeto: a quantidade de DDDs não é afirmada aqui, já que não foi medida nem verificada contra fonte;
3. nenhum dos dois → nenhum achado.

**Fixo com DDD tem dez dígitos, e por isso não passa pela escada.** O passo 2 exige o nono dígito de celular, de modo que `1134567890` falharia nele; e dez dígitos não colidem com CPF, que tem onze. A forma é coberta por ramo próprio, com o mesmo segundo estágio: **DDD na lista, seguido de oito dígitos cujo primeiro não é 9** — a condição que a distingue do celular sem precisar de comprimento mágico. Vale nua e pontuada, `1134567890` e `(11) 3456-7890`, pela regra de que a consulta não depende da pontuação.

**São dois dados externos, e cada um exige a sua citação.** A lista de códigos de área e a regra do dígito inicial vêm da mesma autoridade e de **artefatos diferentes** — tabela de códigos nacionais e plano de numeração —, que mudam em cronogramas independentes: o nono dígito de celular já mudou uma vez sem que a lista de DDD mudasse junto. Dizer "a fonte é a mesma" seria verdade sobre a autoridade e falso sobre o artefato, e o efeito prático é que quem atualizasse um suporia ter atualizado o outro. A implementação cita **duas** fontes, uma por discriminante.

**E este ramo é o que mais depende da âncora**, por efeito do próprio discriminante. Sondagem com padrão hipotético que o implementa — DDD, depois oito dígitos cujo primeiro está em `[2-8]`, sem `\b`: em `11987654321` a varredura **não casa na posição 0**, porque ali o nono caractere é `9` e o discriminante o recusa; o primeiro casamento possível começa no índice 1, e é `1987654321`, com DDD `19` inventado pelo deslocamento e cauda `87654321` que passa no discriminante. O resultado é achado de fixo aninhado num de celular.

O mecanismo é a varredura leftmost comum, não uma retentativa especial: é **o discriminante falhar na posição certa que empurra o casamento para a errada**. Um padrão de dez dígitos sem discriminante casaria em `(0,10)` e não exibiria o efeito — de modo que a demonstração depende de o padrão sondado implementar a regra deste ramo. Com `\b` nas duas pontas não há casamento algum, porque não existe fronteira de palavra no índice 1. É o caso mais concreto de por que a âncora foi declarada parte da decisão.

A enumeração de formas com DDD é, portanto: **onze dígitos para celular, dez para fixo**, cada um com a sua condição de primeiro dígito. Declarar o comprimento de cada ramo é o que impede que "nua com DDD" fique sem alcance definido, que foi como o fixo ficou fora até esta redação.

O telefone ganha assim o seu próprio segundo estágio — consulta a tabela, da mesma natureza determinística do dígito verificador —, em vez de herdar o do CPF pela negativa. Telefone escrito com formatação não colide com o padrão de CPF e é reconhecido por expressão própria.

**E a conferência da lista não depende da pontuação.** Toda forma que traz o DDD — nua ou formatada, `11987654321` ou `(11) 98765-4321` — passa pela mesma consulta à tabela de códigos de área, porque a evidência é a mesma e deixar de usá-la por causa de um parêntese seria arbitrário. O segundo estágio pertence ao **DDD presente**, não ao formato: a escada acima descreve a ordem de teste para o caso que colide com CPF, e a consulta vale para todas as formas com DDD.

**A regra companheira, que decide span e não tipo: em casamentos aninhados, vence o que inclui o DDD, e o contido fica suprimido.** Ela decorre da frase acima — se a evidência está no DDD presente, o casamento que o contém carrega mais evidência — e é obrigatória, porque sem ela a escada decide qual tipo e não decide qual trecho. O caso é concreto: em `(11) 98765-4321`, o padrão com DDD casa o texto inteiro e o padrão sem DDD casa `98765-4321` no interior; os dois achados **não são o mesmo span**, são aninhados, e a restrição de implementação registrada nas Consequências proíbe emitir ambos. A mesma regra resolve `99 987654321`, onde o DDD separado por espaço ficaria fora do span do achado contido.

**A supressão vale contra achado, não contra candidato.** Um casamento com DDD que a lista reprova **não é achado**, e portanto não suprime nada: o padrão contido segue valendo por si. Sem essa oração a regra se choca com a assimetria do parágrafo seguinte, porque um implementador poderia suprimir o contido em favor de um candidato que foi rejeitado — e aí nada seria emitido, contra o que esta decisão declara.

**Uma assimetria desta escolha, declarada.** Em dígitos nus a consulta à tabela **reprova** de fato: `11987654321` não tem fronteira interna, então nenhum padrão mais curto casa dentro dele, e DDD fora da lista significa nenhum achado. Em forma pontuada ela **não reprova**: se o código de área falha na lista, o padrão sem DDD ainda casa o miolo e o achado sai, com o prefixo rejeitado em claro fora do span. Isso é consequência aceita pela tese — erra-se para mais —, e fica escrito para não ser descoberto como surpresa na medição do M2.

#### Todas as formas de telefone são cobertas, e a forma sem DDD entra pela tese

**A cobertura vale para cinco formas: nua com DDD de celular, onze dígitos; nua com DDD de fixo, dez; nua sem DDD, oito ou nove; hifenizada sem DDD; e qualquer das duas com DDD escrita com pontuação.** A escada acima decide apenas o caso de onze dígitos nus, onde há colisão com CPF; os demais comprimentos não colidem com nada deste registro e precisavam de decisão própria, que sem esta subseção ficaria por omissão — o recorte que este documento foi escrito para acabar.

**O instrumento aqui não é o critério de admissão.** O critério decide **entre tipos candidatos**, e telefone foi admitido como tipo quando entrou na lista dos cinco. Forma sem DDD não é tipo novo: é outra forma de um tipo já admitido, e a pergunta em aberto era de **cobertura dentro do tipo** — todas as formas, ou só as discrimináveis. Quem responde isso é a **tese**: recall sobre precisão, porque transmitir é irreversível e inspecionar não destrói. Entre registrar um achado que não era nada e deixar passar um telefone, a tese escolhe o primeiro, e é por isso que a forma entra.

Dizer que ela entra por ser "barata" seria apoio errado, e vale registrar por quê: custo unitário limitado vezes taxa ilimitada dá total ilimitado, de modo que "barato" sozinho não autoriza admissão alguma. **"Barato" descreve o custo; não é ele que autoriza.**

**O custo, declarado.** A forma sem DDD **não tem segundo estágio** — sem DDD não há tabela de códigos a consultar, e o nono dígito de celular só discrimina quando se sabe onde o número começa. O que ela custa é ruído na trilha, que é o terceiro custo da tabela acima: mensurável, local e reversível. Nada sai da máquina, e o chamador segue com o texto original.

**Quantos padrões estão nessa situação, e por que a contagem é conferível.** A unidade é o **padrão de reconhecimento, não o tipo** — e-mail é um tipo com um padrão, telefone é um tipo com vários —, e sem essa definição a exaustividade não seria conferível: quem contasse tipos acharia um, quem contasse padrões acharia três. Contados por padrão, são **três** os que não têm estágio seguinte: e-mail, telefone nu sem DDD e telefone hifenizado sem DDD. Nenhum outro padrão dos cinco tipos está nessa situação, porque CPF, CNPJ e cartão têm dígito verificador e toda forma com DDD — de celular ou de fixo — consulta a tabela.

**O falso positivo esperado, nomeado por classe — e quatro delas são conjectura, uma é medida.** Número de pedido, código de rastreio, matrícula e protocolo vêm de raciocínio sobre o que costuma ter oito ou nove dígitos. **Data escrita sem separador foi demonstrada por sondagem**, nos dois sentidos de escrita: com `re.ASCII`, `pedido 20261104` e `nasc 04112026` casam ambos em oito dígitos. A distinção tem consequência, e ela é de piso e não de ordem: **a classe medida é obrigatória no corpus do M2**, porque omitir um verdadeiro positivo já demonstrado seria lacuna conhecida; as conjecturadas entram por frequência esperada em prompt real, que é outra pergunta e não foi medida. A sondagem mostrou que o padrão **casa** a data, não que ela seja frequente — e frequência é o que ordenaria cobertura. Para a forma hifenizada, `\d{4}-\d{4}` casa **intervalo de anos**, como `2024-2025`; CEP escapa, por ser 5–3 e não 4–4.

**A forma hifenizada exige expressão própria**, porque a âncora quebra no hífen e ela não casa com o padrão de oito dígitos nus. Seu conjunto de falso positivo é o do parágrafo acima, diferente do dos nus, e a implementação a trata como padrão separado.

**Nenhum limite conhecido substitui o 1 em 100 aqui.** Aquele número é o resíduo do filtro mais forte disponível, e vale **somente** para o ramo de onze dígitos com dígito verificador. Para os ramos sem segundo estágio não há limite conhecido: a taxa não é 1%, é desconhecida e maior. A única fonte será o limiar de falso positivo do M2 — que o gatilho desta decisão já aponta, e que é limite agendado e não limiar por procuração.

**Os ramos não se sobrepõem, e isso é consequência da âncora, não da ordem.** O `_CPF_PATTERN` delimita com `\b` nas duas pontas, e dígito é caractere de palavra: `\b\d{9}\b` não casa dentro de um CPF de onze dígitos nem de um cartão de treze a dezenove, porque entre dígitos consecutivos não existe fronteira de palavra. Cada comprimento nu casa como token inteiro ou não casa. **A âncora é parte da decisão**: uma expressão de telefone escrita sem `\b` passaria a casar dentro dos outros tipos, e aí a disputa por trecho sobreposto seria real.

### Precedência entre tipos, e as formas que o cartão cobre

As regras acima resolvem colisão **dentro** do telefone. Falta a colisão **entre tipos**, e ela tem instância concreta: um cartão escrito em grupos separados por hífen produz **dois** casamentos em forma de telefone 4–4, não um, e eles são adjacentes entre si — `4111-1111-1111-1111` dá `(0,9)` e `(10,19)`. A regra do DDD não decide, porque nenhum dos dois tem DDD; a escada não decide, porque não são onze dígitos nus; e a precondição de sobreposição não vê conflito entre eles, porque adjacente não é sobreposto.

**A regra é precedência por classe: na sobreposição, achado de classe validada vence achado de classe plausível.** Ela não é nova, é a generalização do que a escada já faz para CPF contra telefone — e decorre do critério de evidência deste registro: o cartão passa por Luhn, e o telefone sem segundo estágio não passa por nada. Na sobreposição entre achados da mesma classe, vence o span mais longo, do qual a regra do DDD é o caso particular.

**Isso só resolve se houver competidor, e por isso as formas do cartão ficam declaradas: o padrão cobre o número nu e o agrupado, com espaço ou hífen entre grupos, de treze a dezenove dígitos no total.** O agrupamento **não** é quatro grupos de quatro: isso cobriria apenas o cartão de dezesseis, e o intervalo declarado inclui o de quinze, cujo agrupamento usual é 4-6-5. O que o padrão exige é o total de dígitos dentro do intervalo e um separador consistente entre grupos, não um gabarito de grupos fixo — e a validação de Luhn se faz sobre os dígitos, depois de removidos os separadores. Sem a forma agrupada não haveria casamento de cartão nenhum — `4111111111111111` nu não casa padrão agrupado, e o agrupado não casa padrão nu —, e o cartão simplesmente não seria detectado: a trilha registraria `matched_type="telefone"` duas vezes para um cartão. O dado estaria mascarado de todo modo, mas a contagem da trilha estaria errada, que é o terceiro custo da tabela acima com instância nomeada.

### O limite que nenhuma ordem de testes conserta

O ADR 0004 publica que **aproximadamente 1 em cada 100 sequências aleatórias de onze dígitos passa pelos dois dígitos verificadores**. Um telefone real tem, portanto, cerca de 1% de chance de ser rotulado CPF, e isso não é consertável por ordenação: o dígito verificador é o sinal mais forte disponível e erra nessa taxa.

Fica declarado como limite conhecido do método, e não como defeito a corrigir.

## Consequências

**Este registro precede o código, e os dois parágrafos de afirmação abaixo são escritos no futuro por isso.** Hoje o detector emite um único `matched_type`, `"cpf"`; quatro dos cinco tipos não existem em implementação, e a taxa de falso positivo de nenhum deles foi medida. Diferente do ADR 0010, que foi escrito junto da implementação, este decide à frente dela — o que é legítimo e obriga o tempo verbal a dizer isso. Os demais itens desta seção valem desde já.

**O que o trabalho poderá afirmar, quando os cinco detectores existirem e a medição do M2 estiver feita.** Que detecta e mascara cinco tipos de PII por método determinístico, com as duas classes de confiança declaradas e registradas na trilha, e com a taxa de falso positivo caracterizada por medição.

**O que o trabalho não poderá afirmar, nem depois disso.** Que todo achado corresponde a um dado real. Para e-mail e telefone não existe verificação de existência, e o trabalho declara isso em vez de contorná-lo.

**Restrição de implementação.** O masker exige achados sem sobreposição e ordenados por posição — precondição do ADR 0005, que o próprio ADR 0005 declara não validar, e cujo rompimento o ADR 0006 registra como bug ocorrido, com saída sanitizada deixando telefone e CPF em claro. O detector deve emitir **um único achado por trecho**: a escada escolhe qual.

**E a proibição vale para span aninhado, não só para span idêntico.** Esta decisão multiplica os padrões que podem casar dentro um do outro — cinco tipos, e o telefone com uma forma por pontuação —, enquanto a precondição é a mesma de setembro. Aninhado é sobreposto: dois achados em `(0,15)` e `(5,15)` violam o contrato do masker tanto quanto dois em `(5,15)`. Vale a regra da escada: em casamentos aninhados vence o que inclui o DDD, e o contido é suprimido antes de a lista de achados chegar ao masker.

**O gatilho de setembro dispara, e está quebrado.** O ADR 0004 registra como gatilho de reavaliação:

> "A taxa de falsos positivos medida em um corpus representativo, especialmente envolvendo telefones, exceder **o limite definido durante a avaliação dos dias 17–20**."

Esse limite **não existe**. Não há artefato dos dias 17–20 em `benchmarks/resultados/`, que vai do dia 2 ao dia 6 e para; a avaliação nunca aconteceu, e nenhum número foi fixado. O gatilho é, portanto, inacionável desde setembro: ele manda comparar contra um limiar que nunca foi escrito.

**Consequência para o M2:** definir o limiar precede medir. Medição sem critério de aprovação não pode reprovar, e medição que não pode reprovar não é verificação — é ilustração. O limiar tem de ser registrado **antes** da medição, pela mesma disciplina de previsão cega que o ADR 0009 exige, sob pena de ser escolhido depois para caber no resultado obtido.

**Custo de escopo.** Cada tipo acrescenta detector, testes, casos de corpus e avaliação própria sob a convenção do ADR 0009. Isso é trabalho do M2 e não do M1.

## Trabalho futuro

**Seleção do mascaramento pelo usuário.** Apresentar os achados e deixar a pessoa escolher quais mascarar. O `placeholders` do ADR 0005 já é o que torna isso possível, porque guarda o original de cada marcador.

Isso transforma o falso positivo de defeito em decisão de quem usa, e é o complemento natural da tese: o produto erra para mais, e a pessoa corrige para menos com informação à vista.

**Por que fica fora do escopo, e o motivo não é a fronteira do ADR 0011.** Escolher o que mascarar já é representável hoje, por detector, através de `enabled_detectors` — campo com leitor em `engine.py`, aplicado **antes** da `Decision`. É configuração, não consequência de fronteira. O que não existe é granularidade **por tipo**.

Acrescentá-la é escolha de escopo com custo próprio: cinco tipos selecionáveis individualmente multiplicam as combinações que a suíte teria de cobrir, e nada no aceite pede seleção fina. Fica fora por isso, e não por posição no pipeline.

## Gatilhos de reavaliação

* **Falso positivo medido** exceder o limiar que o M2 tiver de definir, em corpus representativo, especialmente para telefone. Dispara a revisão da escada, não da tese — e depende do limiar ser registrado antes da medição, porque o do ADR 0004 nunca existiu;
* **A ação para credencial ser decidida em qualquer registro**, inclusive sem acrescentar o tipo — convenção de severidade, revisão da política do ADR 0006, detector de segredo chegando por outro caminho. A exclusão desta decisão repousa sobre a ação estar em aberto, e no instante em que ela for decidida essa razão expira: a exclusão precisa ser refeita com razão nova ou levantada. O gatilho é o inverso da regra de admissão acima, que só pega quem entra *através* dela, e por isso não pegaria a decisão tomada por fora. Verifica-se por inspeção dos registros, e não depende de medição alguma;
* **Um tipo novo não cumprir o critério** — detecção não determinística, ou primeiro estágio cujo falso positivo não seja raro nem barato. Esse tipo não entra, e a recusa passa a ter critério em vez de omissão;
* **O texto mascarado passar a ser a única cópia.** É o que derrubaria a tese, porque ela se apoia em o original nunca sair das mãos do chamador. Três formas plausíveis, nenhuma hipotética: redação em repouso; gravar o `sanitized_text` na trilha, hoje proibido pelo ADR 0008 — cuja justificativa esta decisão acabou de enfraquecer, ver abaixo; e o proxy do ADR 0011, se o chamador delegar o envio sem reter o prompt.

## Relação com decisões anteriores

**Complementa o ADR 0004**, que decidiu o método para um tipo e deixou o critério de admissão implícito. O ADR 0004 permanece Aceito e inalterado.

**Nota sobre a escada do telefone, caso algum dia se mova.** Ela é conteúdo de **método** dentro de um registro de **cobertura**, da mesma natureza do que o ADR 0004 carrega — e não se move agora: deslocar especificação antes de o código existir produziria registro sobre código inexistente. Não é candidata a registro próprio, porque a dependência é de mão única: mudar a escada deixa a cobertura intacta, e tirar telefone da cobertura mata a escada junto. Esse é o teste que separou o ADR 0011 deste, e a escada não passa nele. Se algo se mover, move para a linhagem do ADR 0004.

**Confirma o ADR 0005**, que foi desenhado para vários tipos desde setembro: o masker monta o marcador a partir do `matched_type` do achado, e a tabela de decisão daquele registro já usa `[EMAIL_1]` como exemplo. Esta decisão exerce um desenho que já existia.

**Fecha uma constatação do ADR 0008.** Aquele registro observou que PII não reconhecida sai em claro, sem que houvesse decisão à qual a consequência se referisse. Agora há, e a consequência fica reduzida aos tipos fora das cinco.

**E dispara o gatilho 3 da Parte II do ADR 0008**, que foi escrito para este momento:

> "O detector passar a cobrir os tipos de PII hoje ausentes. Este item não reverte a decisão — a redação da subdecisão correspondente já afirma que o argumento muda sem ser eliminado —, e serve para que a justificativa seja reescrita quando a cobertura mudar."

A subdecisão em questão é a que mantém o `sanitized_text` fora da trilha, e o argumento dela **decorre da cobertura parcial declarada no ADR 0004**: arquivá-lo criaria repositório durável do resíduo não identificado, que cresceria na proporção da limitação do detector. Ir de um tipo para cinco **encolhe esse resíduo** e, portanto, enfraquece o argumento sem eliminá-lo — resíduo menor continua sendo resíduo, e os tipos fora das cinco continuam saindo em claro.

**A decisão do ADR 0008 não muda; a justificativa dela precisa ser reescrita.** Isso é trabalho que esta decisão cria, e fica nomeado aqui para não depender de alguém lembrar — que é exatamente a função que aquele gatilho tinha.
