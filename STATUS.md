# Estado do projeto

Última atualização: **22/10/2026**. Branch de trabalho: `prompt_injection`.

---

## 1. O que já existe e funciona

| Componente | Estado | Onde | Verificação |
| --- | --- | --- | --- |
| Contratos tipados (`Finding`, `Decision`, `NormalizedText`, `GuardConfig`) | pronto | `core/contracts.py` | `tests/test_contracts.py` |
| Normalização com mapa de posições | pronto | `core/normalizer.py` | `tests/test_normalizer.py` + benchmark do dia 3 |
| Detecção de CPF em dois estágios | pronto | `core/detectors/pii.py` | `tests/test_pii.py` + benchmark do dia 4 |
| Mascaramento reversível | pronto | `core/masker.py` | `tests/test_masker.py` |
| Orquestrador e política de decisão | pronto | `core/engine.py` | `tests/test_engine.py` |
| Injection, família `delimiter` | pronto | `core/detectors/injection.py` | `tests/test_injection.py` + benchmark e avaliação do dia 6 |
| Corpus de avaliação, 16 casos | congelado | `datasets/` | SHA-256 `80c9888b…` |
| Injection, família `persona_switch` | **em andamento** | — | especificação registrada em `datasets/README.md` |

Suíte completa: **135 testes passando + 1 `xfail`**, 136 coletados. `ruff` e `mypy` limpos.

## 2. Os números medidos

Orçamento alvo: **15 ms** de latência adicionada.

| Parcela | Custo em 30.000 caracteres |
| --- | --- |
| Normalização | ~9,30 ms |
| Detecção de PII | ~0,42 ms |
| Detecção de injection | ~0,09 ms |
| **Total estimado** | **~9,8 ms (65% do orçamento)** |

Faixa de sensibilidade ao ambiente: 7,7 a 11,9 ms, ou 51% a 79% do orçamento. A normalização responde por ~95% do total — **é ela o gargalo, não os detectores**.

Custos unitários: normalização ~310 ns/caractere; PII 14 ns/caractere mais 4,5 µs por CPF válido; injection ~3 ns/caractere mais ~2,4 µs por ocorrência.

## 3. O resultado atual de injection

Com apenas a família `delimiter`, no corpus de 16 casos:

* ataques bloqueados: **2 de 8 (25%)**;
* legítimos bloqueados: **3 de 8 (37,5%)** — `leg_03`, `leg_04`, `leg_05`.

A regra isolada bloqueia mais texto legítimo do que ataque. Esse resultado é a linha de base do trabalho e não deve ser escondido: é ele que justifica as famílias seguintes.

Com `persona_switch`, o esperado é 4 de 8 ataques, mantendo 3 de 8 legítimos.

## 4. Escopo: o que entra e o que saiu

Decidido em **22/10/2026**, para caber no prazo de um TCC de graduação. O registro formal desta redução em ADR está pendente.

### Fica no escopo

* família `persona_switch` (padrão já definido e sondado);
* família `system_prompt` — cobre 4 dos 8 ataques do corpus e é insubstituível;
* uma ampliação do corpus, focada apenas no buraco conhecido dos colchetes em texto técnico;
* uma medição final consolidada: uma avaliação e um benchmark, no fim;
* **camada de orçamento de tokens (`tiktoken`)** — decidida em 22/10/2026. Além de ser uma das métricas declaradas do trabalho, ela é o que permite ao usuário saber se compensa mascarar a mensagem: sem contagem de tokens e custo estimado, a decisão de sanitizar não tem como ser avaliada economicamente. É também a camada mais barata que resta — uma biblioteca, sem nuvem e sem rede.

### Saiu do escopo (vira Trabalhos Futuros)

| Item | Motivo |
| --- | --- |
| Família `instruction_override` | **Ganho zero de mitigação neste corpus.** Ver a justificativa abaixo. |
| Regra de coocorrência no `Engine` | Já estava adiada; nenhum caso do corpus a exercita. |
| Subtipos em `matched_type` (`pipe`, `bracket`, `xml`) | Cosmético. |
| Leetspeak | Dependia de `instruction_override`. |
| API FastAPI, AWS, `infra/`, camada `adapters/` | Decidido em 22/10/2026. O ADR 0001 já mede o núcleo isoladamente; a contribuição está no núcleo. **Ver a ressalva de título abaixo.** |

### O produto passa a ser local

Decidido em 22/10/2026: o middleware deixa de ser serverless e passa a ser uma **aplicação local**. O usuário aponta a ferramenta para a LLM que já usa, e o pipeline roda na máquina dele.

Consequências:

* o título precisa perder *serverless* — a revisão fica para conversar com o orientador, mas a direção já está decidida;
* a trilha de auditoria continua existindo, em forma local: persistir a `Decision` sem o campo `placeholders`, exercitando a regra de privacidade do ADR 0005;
* o ADR 0001 ganha reforço em vez de perder validade: o núcleo já era isolado de infraestrutura, e agora não há infraestrutura nenhuma para isolar;
* a camada de tokens faz ainda mais sentido localmente — é o que permite ao usuário decidir se compensa mascarar antes de enviar.

Com isso, o repositório deixa de prometer mais do que entrega.

**O orçamento de 15 ms precisa de justificativa nova.** O número foi escolhido como latência adicionada por um gateway serverless. Sem API Gateway e sem Lambda, o orçamento fica mais fácil de cumprir, mas a fundamentação dele desaparece — e "por que 15 ms?" é pergunta óbvia de banca. A justificativa local é provavelmente mais forte: 15 ms são imperceptíveis diante de uma ida e volta de LLM, que custa centenas de milissegundos. Precisa estar escrita, junto com o retítulo.

### Por que `instruction_override` sai

Os três casos rotulados com essa família já são cobertos por outra:

| Caso | Famílias rotuladas | Quem cobre |
| --- | --- | --- |
| `atk_02` | `delimiter`, `instruction_override` | `delimiter` |
| `atk_05` | `instruction_override`, `system_prompt` | `system_prompt` |
| `atk_06` | `instruction_override`, `system_prompt` | `system_prompt` |

`delimiter` + `persona_switch` + `system_prompt` alcançam **8 de 8 ataques** sem ela. Implementá-la acrescentaria risco de falso positivo e nenhum ganho de mitigação mensurável neste corpus.

Isso é um resultado, não uma omissão, e deve ser escrito assim: *a quarta família não é avaliável quanto à mitigação neste corpus, pois todos os casos que ela rotula são cobertos por outras famílias*. A conclusão vale para este corpus, que é pequeno e autoral.

**O corpus continua livre.** Uma versão anterior deste arquivo trazia a regra de não acrescentar, na ampliação futura, um caso que só `instruction_override` cobrisse. Essa regra foi removida: moldar o corpus para não expor uma família não implementada é viés de seleção escrito na metodologia, e atingiria justamente o ativo mais forte do trabalho — o corpus foi commitado antes do detector (`f866355` precede `6917f1b`) e a previsão do dia 6 foi cega.

Se um caso desses aparecer na ampliação, ele entra, e o registro honesto é um falso negativo conhecido, atribuído à família que ficou fora do escopo.

**Custo do corte, registrado.** O corte transfere risco para `system_prompt` em vez de eliminá-lo. `atk_05` e `atk_06` passam a depender dela casar "disclose the internal rules" e "revele as regras internas" — formulações que não contêm o termo *system prompt*. Para alcançar 8 de 8, a família precisa cobrir duas formulações distintas, ficando mais larga do que o nome sugere, com risco de falso positivo contra `leg_06` ("create a system prompt") e `leg_08` ("The system receives user requests"). **A previsão de 8/8 é condicional a isso** e deve ser verificada, não assumida.

## 5. Próximo passo imediato

**Etapa 1 — refatorar o detector de injection para a estrutura de famílias, sem mudar comportamento.**

1. Escrever dois testes de caracterização, que passam de imediato:
   * estrutural: o contêiner de specs é uma tupla e a ordem declarada é a esperada (é o que denuncia a troca por `set`, cuja ordem de iteração muda entre processos);
   * concordância: o segundo segmento do `rule_id` é igual à família declarada na spec.
2. Mover `delimiter` para a estrutura de specs. `rule_id`, `score` e `severity` passam a vir da spec. Ordenar os findings por posição antes de devolver.
3. Rodar as quatro verificações da seção 7.
4. Conferir a impressão digital: se o `git diff` do relatório de avaliação mostrar **somente** a linha `Commit:`, a refatoração não mudou comportamento.
5. Restaurar o relatório antes de commitar.

**Não mudam nesta etapa:** o conteúdo do regex de `delimiter` e o score de 0.9.

Depois vem a etapa 2 (`persona_switch`, com os testes vermelhos primeiro) e a etapa 3 (ADR novo e atualização do resultado no `datasets/README.md`).

## 6. O que falta até a entrega

| Marco | Conteúdo | Quando |
| --- | --- | --- |
| M1 | Etapas 1 a 3 — `persona_switch` implementada, medida e registrada | até dezembro de 2026 |
| M2 | Família `system_prompt`, corpus ampliado uma vez, medição final única | até março de 2027 |
| M3 | Monografia, convertendo os ADRs em capítulo de metodologia | março a junho de 2027 |

A camada de orçamento de tokens entra em M2, junto com a família `system_prompt`.

**Para o checkpoint de dezembro**, o que se apresenta já existe: a arquitetura, o orçamento de latência fechado em ~9,8 ms, o caminho de PII completo, a linha de base de injection com previsão registrada antes da medição, e o plano das famílias restantes. Não é "o sistema pronto" — é o método e a linha de base, que é o que um checkpoint parcial deve mostrar.

Os sete ADRs e os artefatos de benchmark são o rascunho do capítulo de metodologia. Encarar isso como texto a converter, e não como trabalho acessório, é o que torna M3 viável.

## 7. Comandos

Testes do detector de injection:

```bash
./.venv/Scripts/python.exe -m pytest tests/test_injection.py -q
```

Suíte completa:

```bash
./.venv/Scripts/python.exe -m pytest -q
```

Lint e tipos:

```bash
./.venv/Scripts/python.exe -m ruff check .
```

```bash
./.venv/Scripts/python.exe -m mypy src
```

Avaliação sobre o corpus — **atenção: este comando reescreve o relatório do dia 6**:

```bash
./.venv/Scripts/python.exe scripts/evaluate_prompt_injection.py
```

Conferir se algo mudou além da linha do commit:

```bash
git diff -- benchmarks/resultados/dia_06_prompt_injection_evaluation.txt
```

Restaurar o relatório (obrigatório antes de commitar):

```bash
git checkout -- benchmarks/resultados/dia_06_prompt_injection_evaluation.txt
```

Benchmark de injection — gera artefato novo, verificar o nome do arquivo de saída antes de rodar:

```bash
./.venv/Scripts/python.exe benchmarks/bench_injection.py
```

## 8. Pendências conhecidas

* **`GuardConfig()` padrão não constrói detectores.** O padrão de `enabled_detectors` inclui `"budget"`, que não existe no registro do `Engine`, então `build_detectors(GuardConfig())` levanta erro. **É bug vivo, não dívida de estilo.** Com a camada de tokens mantida no escopo, a correção é registrar o detector de orçamento — a pendência se fecha junto com a implementação dessa camada. Vale um teste do caminho padrão para que ela não se feche em silêncio.
* **Mensagens de erro construídas com dois argumentos** em vez de uma f-string única, em `contracts.py` e `engine.py`. A mensagem sai como tupla. Não quebra nada, mas não é o texto esperado.
* **Fonte da família.** Decidido que o `rule_id` é a fonte canônica e o `matched_type` seria o subtipo — mas a troca do `matched_type` ficou fora do escopo, então os dois continuam carregando a família e precisam concordar por teste.
* **Falso positivo de colchetes.** A forma `[MAIÚSCULAS]` casa `[OK]`, `[TODO]`, `[ERROR]`. O corpus atual mede isso de forma limitada, com um único caso legítimo. É o buraco que a ampliação do corpus deve cobrir.
* **A economia de tokens pode ser negativa, e isso muda o desenho da camada.** Medido com `o200k_base`, o encoding padrão do `GuardConfig`: `529.982.247-25` são 7 tokens contra 5 de `[CPF_1]` — economiza 2; mas `52998224725` são 4 tokens contra os mesmos 5 — **custa 1 a mais mascarado**. O ADR 0004 implementa exatamente esses dois formatos, então o caso negativo é metade do que o detector reconhece. Três consequências para o ADR da camada: a métrica precisa prever resultado negativo para uma classe definida de entrada; medir exige contar tokens **duas vezes**, no original e no mascarado, porque o que interessa é o delta; e o comprimento do marcador vira parâmetro econômico, não cosmético — o que interage com o ADR 0005, que escolheu a forma `[TIPO_N]` por razões de colisão, sem considerar custo.
* **Diretórios que o repositório promete e não cumpre.** `infra/` e `src/prompt_validator/core/patterns/` estão vazios; `api/` e `adapters/` têm apenas `__init__.py`. Com API e AWS fora do escopo, os quatro podem ser removidos — exceto `adapters/`, se a fatia local de auditoria da ressalva de título for adotada.
* **`docs/adr/evidencias/`** guarda quatro capturas de tela de execução de testes. É a evidência mais fraca do repositório: um screenshot prova menos que um teste commitado, e os testes estão versionados. Candidato a remoção.
