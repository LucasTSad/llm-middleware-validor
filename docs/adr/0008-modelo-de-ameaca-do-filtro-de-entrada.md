# ADR 0008 — Modelo de ameaça do filtro de entrada e trilha de auditoria

* **Status:** Aceito
* **Data:** 23/10/2026
* **Decisões relacionadas:** ADR 0001 — Pipeline com núcleo isolado; ADR 0004 — Detecção de PII em dois estágios; ADR 0005 — Mascaramento reversível; ADR 0007 — Detecção de prompt injection por famílias de regras

Este documento registra duas decisões tomadas em sequência. A primeira define qual ameaça o filtro de entrada considera e, como consequência, encerra a detecção de prompt injection em uma família. A segunda define como cada decisão do pipeline é registrada em disco.

Cada parte possui status próprio. Uma delas pode ser substituída sem que a outra seja afetada: a substituição é registrada em um ADR novo, que declara qual parte substitui, e o status da parte correspondente passa a indicá-lo.

O conteúdo técnico deste documento não é reestruturado depois de commitado, pelo mesmo motivo que preserva o ADR 0002 — um ADR publicado é registro, e alterar sua estrutura mudaria o significado de citações já feitas.

Isso não impede correções. Corrigir erro factual e esclarecer redação são permitidos, com o motivo na mensagem do commit; foi o que fez o commit `6d9d46b` ao esclarecer o método da faixa de orçamento no ADR 0007. Alterar, retirar ou inverter uma decisão exige ADR novo.

---

# Parte I — Modelo de ameaça do filtro de entrada

* **Status:** Aceito em 22/10/2026

## Contexto

Até aqui, o escopo das famílias de prompt injection foi determinado pelo corpus, que por sua vez foi construído a partir das categorias da LLM01 — Prompt Injection do OWASP Top 10 for LLM Applications.

Um catálogo de categorias serve para não esquecer fenômenos. Não serve para decidir escopo: ele enumera o que existe no mundo, não o que ameaça um produto específico. A consequência foi que a avaliação passou a tratar o corpus como se fosse a especificação.

A lacuna apareceu com uma pergunta que o repositório não sabia responder: qual o sentido de validar prompt injection numa LLM corporativa, se quem escreve o prompt é o próprio funcionário autorizado?

Não havia resposta registrada porque nunca houve modelo de ameaça.

## Decisão

A ameaça considerada é a injeção indireta: o atacante não é quem usa o middleware, mas quem produziu o conteúdo que o usuário cola ou anexa ao prompt. O usuário é a vítima.

A injeção direta — o funcionário atacando a própria LLM corporativa — não é considerada. Ele já possui acesso autorizado, e o pior resultado é burlar o system prompt da empresa, em um produto cuja finalidade é apoiá-lo.

## O critério de admissão de famílias

Uma família entra no escopo quando satisfaz os três testes abaixo.

1. **Julgável.** A forma não possui uso legítimo em nenhuma procedência. Um filtro determinístico lê a string e não observa de onde ela veio; quando a mesma sequência é legítima vinda do usuário e maliciosa vinda de conteúdo colado, nenhuma regra sobre a string decide entre as duas.
2. **Dano real sob a arquitetura escolhida.** Não basta haver dano em abstrato. O produto é local e a saída vai para a tela do próprio usuário, sem renderização de conteúdo remoto e sem encaminhamento automático. Não existe canal de exfiltração.
3. **Observável na entrada.** A forma precisa estar no texto que o middleware vê. Ataques cujo efeito só aparece na saída estão fora do alcance de um filtro de entrada por construção — e é também por isso que não existe camada de validação de saída neste trabalho.

O segundo teste é o que torna o critério verificável: `system_prompt` tem dano real num gateway corporativo e dano nulo num aplicativo local. A mesma família recebe decisões diferentes sob arquiteturas diferentes, e é a arquitetura registrada que decide.

Desse teste decorre um princípio que separa as famílias por **tipo de dano**, e não caso a caso. Numa arquitetura local, as famílias cujo dano é de **confidencialidade** falham no segundo teste, porque a saída não sai do laço fechado: não há para quem exfiltrar. As famílias cujo dano é de **integridade** sobrevivem, porque a manipulação acontece dentro do laço — a vítima e a destinatária da resposta são a mesma pessoa, e é exatamente isso que faz o ataque funcionar.

### Aplicação

`delimiter` **entra**. Não há uso legítimo para escrever `<|system|>` ou `[SYSTEM]` com intenção de fronteira; o uso legítimo observado é citacional — documentação discutindo o marcador — e é a origem do falso positivo já medido.

O seu dano é de integridade, e por isso ela passa no segundo teste apesar de não haver canal de exfiltração. Um marcador oculto num contrato de quarenta páginas faz a LLM tratar o conteúdo seguinte como instrução privilegiada, e o usuário recebe uma resposta manipulada sobre a qual vai agir. Nada precisa sair da máquina: o prejuízo se realiza na decisão que a pessoa toma a partir da resposta.

`system_prompt` **fica de fora**. Passa no primeiro teste, porque pedir instruções internas não é técnica de produtividade, e falha no segundo: quem lê a resposta é o próprio usuário, de modo que a extração recai na injeção direta, que não é considerada.

`instruction_override` **fica de fora**. Falha no primeiro teste: "ignore o que eu disse antes" é fala corrente de correção, representada no corpus por `leg_02`.

`persona_switch` **fica de fora**. Falha no primeiro teste de forma ainda mais clara: atribuir papel é a técnica que extrai mais de uma LLM, e a string é idêntica quando digitada e quando colada. A retirada da especificação está registrada em `datasets/README.md`, abaixo da original, que não foi editada.

Com isso, a detecção de prompt injection se encerra com uma família.

## O que o canal de entrada preserva

A justificativa de `delimiter` depende de existirem formas que o usuário não consegue ver. Isso é propriedade do canal, e o canal deste produto é a colagem.

O que sobrevive a uma colagem em texto puro:

* **caracteres Unicode não renderizados** — sobrevivem, e são removidos pela normalização do ADR 0003, que preserva o span no texto original;
* **volume** — sobrevive sempre; ninguém lê um contrato de quarenta páginas antes de colar;
* **texto branco sobre branco** — não sobrevive, salvo se o caminho de colagem preservar formatação. Numa caixa de texto puro ele reaparece visível.

As duas primeiras são as formas que este filtro pode alcançar, e são as que a avaliação precisa conter.

## Evidência externa, e seus limites

Um levantamento empírico de injeção indireta em páginas web (arXiv 2604.27202, 1,2 bilhão de URLs em 24,8 milhões de hosts, 15,3 mil instâncias validadas) encontrou que cerca de 70% das instruções aparecem em HTML não renderizado, como cabeçalhos, comentários e metadados.

Esse número **não é transferido** para este trabalho como quantidade. A população medida são páginas web e respostas HTTP consumidas por máquina; comentários e `<meta>` não entram na seleção quando um usuário copia texto renderizado. O canal que torna esses 70% exploráveis é a recuperação automática de HTML bruto por um agente, que não é o caso aqui.

Do levantamento aproveita-se apenas a conclusão qualitativa: quando o consumidor do texto é uma máquina, a ocultação é a técnica dominante.

O mesmo resumo reporta que a conformidade dos modelos é limitada, chegando a até 8% nos modelos menores com entradas em texto puro. Prevalência alta e obediência baixa precisam ser citadas juntas; separá-las seria seleção favorável de evidência.

As referências que descrevem o canal deste produto são outras: prompts ocultos em documentos estruturados, incluindo texto branco em currículos submetidos a triagem automática (arXiv 2508.17884), e instruções embutidas em arquivos enviados por upload (arXiv 2508.19287).

## Consequências

O resultado de prompt injection permanece em 2 de 8 de mitigação contra 3 de 8 de falso positivo. É negativo e continua negativo.

`atk_03` a `atk_08`, seis dos oito ataques, passam a ser falso negativo conhecido atribuído a famílias fora de escopo. O corpus mantém os quatro rótulos: alterá-lo destruiria a procedência — ele foi commitado antes de o detector existir — e o relatório de avaliação já separa cobertura por família do corpus de bloqueios atribuídos às regras, de modo que as famílias fora de escopo aparecem como 0/N na primeira seção e ausentes na segunda, sem alteração de código.

A tese que este modelo de ameaça sugere — a defesa determinística num filtro de entrada local só se justifica para formas que o usuário não consegue ver — **ainda não foi medida**. O corpus não contém nenhum caso de invisibilidade nem de volume: os dois verdadeiros positivos de `delimiter` são marcadores curtos, visíveis e digitados em texto claro, isto é, casos do modelo direto, que esta decisão não considera. A tese é, hoje, hipótese derivada do modelo de ameaça, com apoio externo apenas quanto à prevalência.

Para que a avaliação final meça o modelo adotado, o corpus precisa de ao menos dois casos novos: um com marcador contendo caractere de largura zero e um documento longo com marcador enterrado. A ampliação é consequência da mudança de modelo de ameaça, e não do resultado desfavorável; esta decisão é anterior à nova versão do corpus, e a previsão correspondente será registrada antes da medição, de modo que a sequência permaneça verificável no histórico do repositório.

O ADR 0007 se intitula "por famílias de regras" e o detector passa a ter uma só. A estrutura de specs criada para o plural permanece: ela é exercitada pelos testes de caracterização e por `inspect` em todos os casos do corpus, e é a costura natural caso `delimiter` venha a precisar de um segundo `rule_id` para formas de invisibilidade. O plural é, portanto, projetado e não realizado.

## Trabalho futuro

**Segmentação por procedência.** Se a arquitetura passar a distinguir texto digitado de texto colado ou anexado, as famílias excluídas pelo primeiro teste voltam a ser julgáveis, aplicadas somente ao segmento não confiável.

**Canal de exfiltração.** Se a saída passar a alimentar outro sistema — log, ticket, automação a jusante — o canal passa a existir e `system_prompt` volta ao escopo pelo segundo teste.

## Gatilhos de reavaliação

1. A arquitetura passar a marcar a procedência dos segmentos do prompt. **Dispara também a Parte II**, gatilho 4: havendo procedência, a trilha precisa decidir se a registra por finding.
2. A saída deixar de terminar na tela do usuário. **Dispara também a Parte II**, gatilho 2: é o mesmo evento — o sistema deixa de ser um laço local fechado —, e ele derruba ao mesmo tempo a ausência de canal de exfiltração e a premissa de arquivo local.
3. Surgir uma família que satisfaça os três testes e não esteja contemplada.

## Relação com decisões anteriores

O ADR 0007 estabeleceu a arquitetura de famílias e implementou a primeira. Esta parte não a altera: define o critério que decide quais famílias entram nela.

O ADR 0001 estabeleceu que os detectores apenas relatam ocorrências, deixando a tradução em ação para o orquestrador. Esse isolamento é o que permite aplicar o critério de admissão por família sem tocar na política de decisão.

---

# Parte II — Trilha de auditoria local

* **Status:** Aceito em 23/10/2026

## Contexto

"Auditoria" está no tema da proposta aceita e "auditar" é um dos três verbos de entrega. Até aqui não havia nenhuma implementação: a `Decision` era produzida, consumida em memória e descartada.

O produto é local, de modo que o destino do registro é o disco da própria máquina, e não o DynamoDB previsto originalmente. O ADR 0001 proíbe I/O no `core`, portanto a gravação pertence à camada de adaptadores.

## Decisão

Um adaptador em `adapters/` grava uma linha por `Decision` em um arquivo JSONL, em modo append.

O registro contém **apenas metadados**. Nenhum conteúdo do prompt é persistido.

Vão para o registro: a ação decidida; os findings, com `rule_id`, `category`, `severity`, `matched_type`, `start`, `end` e `score`; a quantidade de findings; `elapsed_ns`; `token_count` e `estimated_cost_usd`, quando a camada de orçamento existir; um identificador aleatório; o carimbo de tempo; e o modo de redação aplicado.

Não vão: o texto original, o mapa `placeholders` e o `sanitized_text`.

## Subdecisões

### Por que o `sanitized_text` também fica de fora

Ele é seguro quanto à PII **detectada**, e o advérbio é o problema. O ADR 0004 implementa somente CPF: e-mail, telefone e chave de API não existem no detector. O `sanitized_text` carrega, portanto, em claro, toda a PII que o detector não reconheceu.

Arquivá-lo criaria um repositório durável exatamente do resíduo que a ferramenta não soube identificar, e esse repositório cresceria na proporção da limitação do detector. O argumento não depende de preferência sobre privacidade de conteúdo: decorre da cobertura parcial declarada no ADR 0004.

Os campos `start` e `end` dos findings permitem auditar **onde** havia PII sem guardar o texto.

### Identificador aleatório, e não hash do texto de entrada

A alternativa considerada era identificar o registro pelo hash do texto de entrada, o que permitiria correlacionar registros do mesmo prompt.

Foi rejeitada por viabilizar recuperação da PII protegida. O espaço de busca de um CPF válido é da ordem de **10⁹ valores**, enumerável em minutos em um computador pessoal. Com um molde provável — "Meu CPF é X" — e um prompt curto, quem possuir o arquivo de auditoria não confirma uma suspeita: recupera o valor exato por força bruta, offline, sem acesso ao texto original.

Uma trilha que viabiliza recuperação por força bruta contraria a finalidade do produto de forma mais direta do que guardar o `sanitized_text` contrariaria.

O instrumento correto para correlação, caso ela venha a ser necessária, é HMAC com segredo local. Isso introduz gestão de chave, cujo custo não se justifica no escopo atual.

### O carimbo de tempo fica no registro, não na `Decision`

Um relógio dentro da `Decision` destruiria a afirmação de determinismo do núcleo: "mesma entrada, mesmo resultado" só é demonstrável enquanto o relógio estiver fora dele.

A decisão decorre da tese do trabalho, e não de preferência arquitetural.

### O registro declara o próprio modo de redação

Sem esse campo, um leitor não distingue "sem conteúdo porque a política omite" de "sem conteúdo porque não havia conteúdo a registrar".

Uma trilha precisa ser autodescritiva quanto ao que ela própria omitiu. Caso contrário a ausência não é auditável, e não há como demonstrar que o modo padrão estava ativo quando o registro foi gravado.

### Formato

JSONL com append, uma decisão por linha. Não acrescenta dependência, é legível sem ferramenta, e permite comparar execuções com utilitários de texto.

SQLite foi considerado e descartado: traz peso de esquema e migração sem acrescentar nada ao que se pretende afirmar.

## Consequências

### Determinismo

A afirmação verificável por terceiro passa a ser sobre os **campos de decisão**, e não sobre a linha inteira: mesma entrada produz os mesmos campos, descontados o identificador, o carimbo de tempo e `elapsed_ns`.

O recorte é consequência da escolha do identificador aleatório, e não uma concessão: foi a privacidade que tornou a linha não reproduzível, enquanto a decisão permanece reproduzível.

### Verificação

Dois testes sustentam esta decisão, e ambos devem afirmar sobre **a linha efetivamente gravada**, não sobre `model_dump()`. O `exclude=True` do ADR 0005 protege a serialização do pydantic; um adaptador que monte o dicionário à mão fura essa proteção. Testar `model_dump()` testaria o pydantic; testar o arquivo testa o adaptador.

1. Uma `Decision` em modo reversível é gravada e a linha não contém o campo `placeholders`.
2. **Controle negativo:** uma decisão produzida a partir de um texto com CPF conhecido é gravada, e aquela string literal não aparece em nenhuma posição da linha.

O segundo teste pega vazamento por qualquer campo, inclusive campos que ainda não existem, e sobrevive a refatorações do registro.

Esta camada é o primeiro consumidor real da regra de privacidade do ADR 0005, que até aqui era exercitada apenas por testes de unidade.

### Premissas assumidas

**Sem política de retenção ou rotação.** Um arquivo em append que cresce indefinidamente é, na prática, retenção infinita — o que contraria a finalidade de uma ferramenta de privacidade mesmo guardando apenas metadados. A ausência de política é escolha de escopo, declarada aqui para não ser lida como descuido.

**Processo único.** O append concorrente de dois processos não é atômico para linhas longas. O desenho pressupõe um único processo gravando.

**Permissões do sistema de arquivos.** O arquivo herda as permissões do diretório onde é criado; o adaptador não as ajusta.

## Trabalho futuro

**Correlação de registros.** Caso seja necessário correlacionar registros do mesmo prompt, o instrumento é HMAC com segredo local, com a gestão de chave que isso implica.

**Retenção.** Uma política de retenção e rotação, hoje ausente por escopo.

## Gatilhos de reavaliação

1. Surgir necessidade de correlacionar registros do mesmo prompt.
2. A trilha passar a ser consumida por mais de um processo, ou precisar sair da máquina local. **Dispara também a Parte I**, gatilho 2: sair da máquina é a mesma mudança que cria canal de exfiltração e devolve `system_prompt` ao escopo.
3. O detector passar a cobrir os tipos de PII hoje ausentes. Este item não reverte a decisão — a redação da subdecisão correspondente já afirma que o argumento muda sem ser eliminado —, e serve para que a justificativa seja reescrita quando a cobertura mudar.
4. A arquitetura passar a marcar a procedência dos segmentos, caso em que a trilha precisa decidir se registra essa informação por finding. É o gatilho 1 da Parte I, visto do lado do registro.

## Relação com decisões anteriores

O ADR 0001 proibiu I/O no núcleo. É isso que coloca a trilha de auditoria em `adapters/`, e não no `core`.

O ADR 0005 estabeleceu que o mapa `placeholders` contém PII e não deve ser serializado. Esta parte é o primeiro consumidor real dessa regra.
