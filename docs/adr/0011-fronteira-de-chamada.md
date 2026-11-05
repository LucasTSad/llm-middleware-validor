# ADR 0011 — A interceptação se realiza como fronteira de chamada

* **Status:** Aceito em 31/10/2026
* **Data:** 04/11/2026
* **Decisões relacionadas:** ADR 0001 — Pipeline de detectores com núcleo isolado; ADR 0008 — Modelo de ameaça do filtro de entrada e trilha de auditoria
* **Decisão irmã:** ADR 0012 — Cobertura de PII e critério de admissão de tipos

## Contexto

O aceite nomeia três verbos: interceptar, sanitizar e auditar. **Sanitizar** está entregue e exercido — o mascaramento acontece dentro de `analyze`. **Auditar** está implementado e sem chamador: `record` existe em `adapters/audit.py` e é invocado apenas por teste, como o ADR 0010 já registra ao dizer que a trilha não tem um único registro em disco. **Interceptar** nunca foi definido, e é o que falta.

"Interceptar" sugere algo posicionado *entre* o cliente e a LLM e essa leitura admite duas realizações materialmente diferentes:

* **proxy de rede** — um processo que recebe a requisição, filtra e encaminha. O chamador aponta para o middleware em vez de apontar para o provedor;
* **fronteira de chamada em processo** — uma função que o chamador invoca antes de enviar. O chamador continua apontando para o provedor e passa a ter um passo a mais.

O código implementa a segunda desde o ADR 0001, sem que nenhum registro diga que essa é a decisão. O `Engine.analyze(text) -> Decision` é o ponto de interceptação, e sempre foi.

A ambiguidade tem custo concreto. Enquanto ela existe, "falta a API" é lido como pendência de implementação, e a pergunta reaparece a cada planejamento.

## Decisão

**A interceptação se realiza como fronteira de chamada em processo.** `Engine.analyze` é o ponto de interceptação do produto, e a **interceptação** termina na `Decision` que ele devolve.

### O que vem depois da `Decision`

A trilha de auditoria **consome** a `Decision` e portanto fica depois desse ponto. Isso exige dizer o que `adapters/` é, porque sem essa frase o registro e o ADR 0008 Parte II discordam. Um encerra o produto na `Decision`, o outro chama "auditar" de verbo entregue por código que a recebe.

**`adapters/` é produto.** O que termina na `Decision` é a interceptação e não o pacote. O produto oferece **duas** funções ao chamador — `analyze` que decide e `record` que registra, o ADR 0001 as separa por isolamento de I/O, não por fronteira de produto.

**A consequência é que a ressalva desta decisão vale duas vezes.** Ninguém é obrigado a chamar `analyze` e ninguém é obrigado a chamar `record` depois. Hoje, de fato, ninguém chama: `record` é exercido apenas por teste. A trilha é capacidade oferecida e não exercida em produção, e dizer "auditar está entregue" sem essa qualificação é afirmação de estado que o histórico contradiz.

O proxy HTTP é **trabalho futuro**.

O motivo é a arquitetura local do ADR 0008. Um ponto de entrada HTTP acrescentaria FastAPI, um modelo de concorrência e testes de integração, e **o que ele muda é o transporte, não a detecção**: o mesmo texto, com o mesmo detector e o mesmo mascaramento, produz a mesma `Decision` atravessando um socket ou uma chamada de função. O que mudaria é quem hospeda o processo — e o aceite pede middleware **local**.

A afirmação limita-se, de propósito, à detecção. O proxy **alteraria** outra coisa, tratada na seção seguinte: a alcançabilidade da fronteira. Dizer que ele "não tocaria nenhum dos três riscos" seria forte demais, porque um filtro que pode ser contornado não mitiga nada no caminho que o contorna.

## A ressalva, que é parte da decisão

**Nada obriga a chamada.** Um chamador que não invocar `analyze` envia o prompt sem filtro algum, e o produto não percebe. A fronteira é convenção, não imposição.

**Garantir que essa fronteira não seja contornada está fora do produto.** Não há hook de import, não há wrapper do cliente da LLM, não há verificação em tempo de execução, e não haverá: qualquer um deles seria imposição de política dentro do processo do chamador, que é outro trabalho.

**Registrar a ressalva é obrigatório**, porque sem ela o registro prometeria contenção que o código não entrega — e a pergunta "o que impede alguém de simplesmente não chamar?" não teria resposta escrita.

A resposta é o modelo de ameaça já registrado: sob o ADR 0008, **o chamador é a vítima, não o adversário**. O produto protege a organização que o adota contra o que seus próprios usuários colam num prompt, não contra um desenvolvedor que decide burlá-lo. Interceptação voluntária basta exatamente nesse modelo, e em nenhum outro.

É também o único eixo em que o proxy seria superior: ele centraliza o ponto de passagem e torna o contorno uma ação deliberada de rede, em vez de uma omissão. Esse ganho é real e não é suficiente para incluí-lo no escopo, porque ele endereça um adversário que o ADR 0008 declarou fora do modelo.

## Consequências

**O que o trabalho pode afirmar.** Que filtra, sanitiza e audita prompts em processo, com latência medida, sobre a fronteira de chamada declarada.

**O que o trabalho não pode afirmar.** Que garante que todo prompt da organização passa pelo filtro. Essa afirmação exigiria controle sobre o chamador, que o produto não tem e não pretende ter.

**Sobre os extras do `pyproject.toml`.** O extra `api` permanece declarado, como dependência do trabalho futuro que esta decisão nomeia. O extra `aws` foi removido, por aplicar o abandono do serverless decidido no ADR 0008.

Isso torna obsoleta uma frase do ADR 0001, em Custos e Limitações, que cita `pip install -e .` contra `.[api]` contra `.[aws]`. O ADR 0001 **não** é corrigido por isso: registro antigo descreve o que era verdade quando foi escrito, e reescrevê-lo destruiria a procedência. Fica a anotação aqui.

## Gatilhos de reavaliação

* **O produto precisar ser alcançável por HTTP por chamador fora do processo.** Nesse caso o extra `api` deixa de ser trabalho futuro e este registro é substituído;
* **O produto precisar garantir a passagem pelo filtro, e não apenas oferecê-la.** Isso invalidaria a premissa do chamador-vítima do ADR 0008, e exigiria ADR novo em vez de emenda a este.

Os dois são condições sobre o produto, conferíveis por inspeção do que ele faz. Enunciá-los como evento externo — "surgir requisito de…" — os tornaria inverificáveis pelo próprio registro, porque quem o relê não tem como responder se o evento ocorreu olhando o projeto.

## Relação com decisões anteriores

**Este registro complementa o ADR 0001 e não o substitui.** É preciso dizer por quê, porque documentos de trabalho deste projeto afirmaram o contrário antes desta data.

A afirmação em circulação era que o ADR 0001 teria tirado a API do escopo sob a premissa serverless, e que este registro substituiria essa parte. A leitura do ADR 0001 não a sustenta, e a inverte: o documento tem 33 linhas, a palavra "escopo" não aparece nenhuma vez, e ele move `fastapi`, `boto3` e `httpx` para grupos opcionais — extra instalável é o oposto de exclusão. Mais que isso, a linha 30, em Custos e Limitações, lista como custo assumido da decisão:

> "Exige a criação e manutenção de uma camada adicional de adaptadores para conectar o núcleo isolado aos serviços e frameworks de infraestrutura."

Ou seja, o ADR 0001 **obriga** a camada de adaptadores em vez de dispensá-la. Não há decisão anterior a substituir: aquele isolou o núcleo e previu os adaptadores, este declara onde o produto termina. O ADR 0001 permanece Aceito, sem linha de substituição.

**Nota de método.** A afirmação falsa circulou em documento de trabalho e em discussão, e não chegou a nenhum arquivo versionado — `git grep` por ela não encontra ocorrência fora deste registro, que a refuta. Ela sobreviveu por ser relato sobre o conteúdo de um documento, repetido sem releitura do documento. A verificação que o projeto já aplica a número e a estado passa a valer também para afirmação sobre o que um registro diz.
