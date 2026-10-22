# Índice das decisões de arquitetura (ADRs)

Este arquivo resume, em linguagem direta, as sete decisões registradas até agora. Cada entrada responde quatro perguntas: o que foi decidido, por que, o que isso obriga daqui para frente e onde está no código.

Os documentos completos ficam nesta mesma pasta. Este índice não os substitui: serve para localizar a decisão certa e para retomar o contexto depois de um intervalo sem mexer no projeto.

As capturas de tela em `evidencias/` registram execuções de teste usadas como evidência em ADRs específicos.

**Os números medidos não são repetidos aqui, de propósito.** Eles ficam em dois lugares apenas: o ADR correspondente, que guarda a medição original com seu contexto e sua procedência, e a seção 2 do [`STATUS.md`](../../STATUS.md), que consolida os valores atuais. Uma terceira cópia divergiria na primeira remedição, e uma medição final consolidada já está planejada.

## Visão geral

| ADR | Assunto | Data | Status |
| --- | --- | --- | --- |
| [0001](0001-arquitetura-do-pipeline.md) | Núcleo isolado de infraestrutura | 03/09/2026 | Aceito |
| [0002](0002-politica-de-precedencia.md) | Primeira política de precedência | 08/09/2026 | **Substituído pelo 0006** |
| [0003](0003-normalizacao-com-preservacao-de-offsets.md) | Normalização preservando posições | 11/09/2026 | Aceito |
| [0004](0004-deteccao-de-pii-em-dois-estagios.md) | Detecção de CPF em dois estágios | 17/09/2026 | Aceito |
| [0005](0005-mascaramento-reversivel-de-pii.md) | Mascaramento reversível | 23/09/2026 | Aceito |
| [0006](0006-precedencia-por-maximo-de-acoes.md) | Precedência por máximo de ações | 25/09/2026 | Aceito |
| [0007](0007-deteccao-de-prompt-injection.md) | Prompt injection por famílias de regras | 06/10/2026 | Aceito |

---

## ADR 0001 — Núcleo isolado de infraestrutura

**O que foi decidido.** O pacote `core/` não importa `fastapi`, `boto3` nem `httpx`. Cada detector implementa a mesma interface: recebe o texto e a configuração, devolve uma lista de ocorrências (`Finding`). Quem decide o que fazer com essas ocorrências é o orquestrador, não o detector.

**Por quê.** Para medir o custo de cada camada sem depender da nuvem. Rodar o pipeline dez mil vezes é viável porque nada nele chama rede.

**O que isso obriga.** Nenhum detector pode decidir bloquear ou sanitizar: ele só relata. E qualquer ligação com FastAPI ou AWS precisa de uma camada de adaptadores separada — que hoje não existe e saiu do escopo.

**Onde está.** `src/prompt_validator/core/`, `pyproject.toml` (extras `api` e `aws`).

**Alternativas recusadas.** Usar uma segunda LLM para classificar (custo e latência incompatíveis com 15 ms) e um modelo de ML local (não determinístico, sem explicabilidade do bloqueio).

---

## ADR 0002 — Primeira política de precedência (substituído)

**O que foi decidido.** Uma função pura `decide_action` traduzia a lista de ocorrências em uma ação única, usando uma escada de condições na ordem: lista vazia, severidade alta, injection acima do limiar, PII.

**Por que foi substituído.** A escada era "primeira condição vence". Quando entrou prompt injection, apareceu um caso em que uma injeção fraca impedia que um CPF no mesmo texto fosse sanitizado — e o CPF ficava em claro. O ADR 0006 resolveu isso.

**Por que o arquivo continua aqui.** O próprio ADR 0002 havia registrado em que situação ele deveria ser reavaliado, e essa situação aconteceu. Manter os dois documentos prova que a reavaliação foi prevista, e não improvisada. Isso é material de defesa, não lixo.

---

## ADR 0003 — Normalização preservando posições

**O que foi decidido.** O texto passa a existir em duas versões: a original, intocada, e a normalizada, que os detectores leem. Junto vem um **mapa de posições**, que permite converter uma posição encontrada no texto normalizado para a posição equivalente no texto original.

A normalização faz duas coisas: remove cinco caracteres invisíveis escolhidos um a um (`U+200B`, `U+FEFF`, `U+00AD`, `U+202E`, `U+2060`) e depois aplica NFKC caractere a caractere.

**Por quê.** Sem isso, um atacante esconde um caractere invisível no meio de `<|system|>` e escapa do regex. Com isso, o detector enxerga o texto limpo e ainda sabe apontar o lugar certo no texto que o usuário escreveu.

**O que isso obriga.** Todo detector recebe `NormalizedText` e converte suas posições com `to_original_span` antes de criar um `Finding`. Nenhum detector normaliza por conta própria.

**O que a medição mostrou.** **A normalização é o gargalo do pipeline**, não os detectores: sozinha, consome a maior parte do orçamento de latência. Números na seção "Resultado do Benchmark" do ADR.

**Limitação assumida.** NFKC caractere a caractere não é igual a NFKC na string inteira: `e` + acento combinante continua separado em vez de virar `é`. Está registrado como divergência conhecida.

**Onde está.** `src/prompt_validator/core/normalizer.py`.

---

## ADR 0004 — Detecção de CPF em dois estágios

**O que foi decidido.** Primeiro um regex encontra candidatos (dois formatos: `999.999.999-99` e onze dígitos nus). Depois cada candidato é validado pelo algoritmo de módulo 11, rejeitando também sequências de um dígito repetido. Só quem passa nos dois estágios gera `Finding`.

**Por quê.** Onze dígitos não são um CPF. Telefone com DDD também tem onze. O segundo estágio é o que separa formato de validade — e é por isso que o `score` do CPF é 1.0: existe verificação determinística, não uma estimativa.

**O que isso obriga.** O `Finding` **não carrega o valor detectado**, só o tipo e a posição. É o que permite mandar o `Finding` para auditoria sem vazar a PII.

A severidade é `MEDIUM`, de propósito: `HIGH` alcançaria o limiar de bloqueio, e CPF deve ser sanitizado, não bloqueado.

**O que a medição mostrou.** O custo está concentrado no validador em Python, não na expressão regular — e a detecção de PII não é o gargalo do pipeline. Números na seção "Resultado do Benchmark" do ADR.

**Onde está.** `src/prompt_validator/core/detectors/pii.py`. Só CPF está implementado; e-mail e telefone não.

---

## ADR 0005 — Mascaramento reversível

**O que foi decidido.** A PII é substituída no **texto original** por marcadores da forma `[CPF_1]`. No modo reversível, um mapa `marcador → valor` fica em memória para reconstruir a resposta depois. No modo irreversível o mascaramento é o mesmo, mas o mapa fica vazio.

**Por quê.** Mascarar o original preserva acentos e formatação do que o usuário escreveu. Os colchetes evitam que `[CPF_1]` seja encontrado dentro de `[CPF_10]`.

**O que isso obriga.** O masker **assume** que recebe findings ordenados por posição, sem sobreposição, e não verifica isso. Quem chama precisa garantir — e foi justamente onde apareceu um bug, corrigido no ADR 0006.

O mapa contém PII, então o campo é marcado com `exclude=True` e o objeto `Decision` inteiro nunca deve ir para log.

**Riscos assumidos.** Se o usuário escrever `[CPF_1]` no próprio prompt, a re-hidratação pode inserir uma PII onde ela não existia. E se a LLM reformular o marcador, ele fica órfão e o usuário recebe `[CPF_1]` em vez do valor.

**Onde está.** `src/prompt_validator/core/masker.py`.

---

## ADR 0006 — Precedência por máximo de ações

**O que foi decidido.** Cada ocorrência é avaliada isoladamente e diz qual ação ela justifica. A decisão final é o **máximo** dessas ações, na ordem `ALLOW < SANITIZE < BLOCK`.

**Por quê.** A escada do ADR 0002 deixava uma injeção fraca impedir a sanitização de um CPF no mesmo texto. Com o máximo, cada categoria decide o que quer sem precisar saber da posição das outras.

**O que isso obriga.** `ALLOW` deixou de significar "nada foi encontrado". Agora significa "nada ultrapassou o limiar". Quem precisa de auditoria tem que olhar `Decision.findings`, não só a ação.

Uma `Action` nova sem prioridade registrada causa erro na hora, de propósito: é melhor estourar do que receber uma prioridade arbitrária em silêncio.

**Limitação assumida.** A política não soma sinais fracos. Três indícios fracos não viram um bloqueio, porque cada ocorrência é avaliada sozinha. Essa é a limitação que a regra de coocorrência resolveria, e ela está adiada.

**Onde está.** `src/prompt_validator/core/engine.py`, funções `action_for_finding` e `decide_action`.

---

## ADR 0007 — Prompt injection por famílias de regras

**O que foi decidido.** O detector de injection é organizado em **famílias** de regras, não numa regra única. A primeira implementada é `delimiter`, que procura formas de fronteira privilegiada: marcadores entre barras (`<|system|>`), entre colchetes em maiúsculas (`[SYSTEM]`) e XML de sistema (`</system>`). Cada ocorrência gera um `Finding` com severidade `MEDIUM` e score 0.9.

**Por quê.** Prompt injection não tem validador determinístico como o CPF. "ignore previous instructions" é só uma frase: não existe cálculo que confirme a intenção. Então cada família carrega sua própria confiança no campo `score`, e o bloqueio sai da comparação com `injection_threshold` (0.7) — **não** da severidade.

**O que isso obriga.** Como a severidade é `MEDIUM` (20) e o limiar de bloqueio é `HIGH` (30), uma família só bloqueia se o score dela alcançar 0.7. Toda família nova precisa declarar esse score de propósito.

**O resultado, sem suavizar.** No corpus de 16 casos, a regra isolada bloqueou **mais texto legítimo do que ataque** — contribuição líquida negativa. É esse resultado que justifica implementar as famílias restantes, e ele é o ponto de partida honesto da avaliação. Contagens na seção 3 do [`STATUS.md`](../../STATUS.md).

**Limitação assumida.** A forma de colchetes é ampla e casa `[OK]`, `[TODO]`, `[ERROR]`. Num texto técnico longo ela produz ocorrências às dezenas. Custo e falso positivo são o mesmo fenômeno: um padrão que casa demais bloqueia demais.

**Onde está.** `src/prompt_validator/core/detectors/injection.py`, corpus em `datasets/`, avaliação em `scripts/evaluate_prompt_injection.py`.

---

## Como ler isso antes de uma apresentação

Se precisar retomar o projeto rápido, a sequência mínima é:

1. **0001** — por que o núcleo é isolado (explica a arquitetura em uma frase);
2. **0003** — por que existe texto normalizado e mapa de posições (explica o gargalo de latência);
3. **0006** — como a decisão final é tomada (explica `ALLOW`, `SANITIZE`, `BLOCK`);
4. **0007** — o resultado de injection e por que ele ainda é negativo (explica o que falta fazer).

O 0004 e o 0005 são o caminho de PII, e o 0002 é histórico.

O estado atual do projeto, com o que falta e o que foi cortado, está em [`STATUS.md`](../../STATUS.md) na raiz do repositório.
