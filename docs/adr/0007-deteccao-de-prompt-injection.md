# ADR 0007 — Detecção de prompt injection por famílias de regras

* **Status:** Aceito
* **Data:** 06/10/2026
* **Decisão relacionada:** ADR 0006 — Precedência por máximo de ações

## Contexto

O detector de prompt injection não dispõe de um validador determinístico equivalente ao usado no CPF. No CPF, a própria string contém evidência verificável de validade: formato, dígitos verificadores e algoritmo módulo 11 permitem rejeitar candidatos inválidos e atribuir score = 1.0 quando a validação passa. Em prompt injection, uma expressão como “ignore previous instructions” é apenas uma frase. Não existe uma propriedade estrutural ou operação determinística que confirme, isoladamente, a intenção de ataque.

O custo do erro também é diferente. Um falso positivo de PII pode ser mascarado e o processamento pode continuar; um falso positivo de prompt injection resulta em BLOCK e impede o processamento de conteúdo legítimo. Portanto, a família precisa ser avaliada tanto pela capacidade de mitigação quanto pelo custo de falsos positivos.

## Decisão

O detector será organizado por famílias de regras. Cada ocorrência de um padrão casado produzirá um `Finding` independente, com `severity = MEDIUM` e `score` representando a confiança da regra. Esse score participa da decisão por meio de `injection_threshold`, conforme a política definida no ADR 0006.

A primeira família implementada será `delimiter`, por apresentar baixa variabilidade linguística e permitir uma regra predominantemente estrutural. As demais famílias serão implementadas separadamente, evitando que uma única regra tente representar fenômenos distintos de prompt injection.

## Subdecisões

**Formas restritas, não lista fechada.** A família utiliza formas restritas dos delimitadores observados, mas não uma lista fechada de marcadores conhecidos. A avaliação preliminar mostrou que os cinco marcadores inicialmente previstos apareciam apenas nos casos legítimos, enquanto os ataques utilizavam formas como `<|system|>` e `[SYSTEM]`. Uma lista fechada baseada apenas nos marcadores previstos produziria mitigação de 0/2 nos ataques com delimitadores observados.

**Fragmentos literais com `re.escape`.** Os elementos literais do padrão são construídos com `re.escape`, evitando escape manual e reduzindo a possibilidade de erro na composição da expressão regular.

**Uma única expressão compilada com alternação.** As formas da família são reunidas em um único padrão compilado, permitindo uma única passada de busca sobre o texto em vez de executar uma busca separada para cada variante.

**Sensibilidade a caixa nesta versão.** A regra permanece case-sensitive para não introduzir simultaneamente uma segunda variável experimental. Isso permite atribuir os resultados observados ao conjunto de formas efetivamente especificado.

**Sem `re.ASCII`.** O padrão não utiliza `\w`, `\d` ou `\b`, portanto `re.ASCII` não altera o comportamento relevante dessa família. A decisão de usar `re.ASCII` no CPF pertence ao escopo local do ADR 0004 e não constitui uma prática global.

**Score fixo em 0.9.** O score da família permanece em `0.9` e não será calculado por expressão composta, evitando efeitos de representação de ponto flutuante em um valor que representa uma decisão deliberada de confiança.

## Consequências — Ganhos

A expressão da família `delimiter` é resistente a ReDoS por construção: utiliza alternação de literais e classes simples, sem quantificadores aninhados ou estruturas com retrocesso combinatório. Essa propriedade decorre da forma do padrão, e não de comportamento acidental observado no ambiente de execução.

A regra também se beneficia diretamente da normalização definida no ADR 0003. Caracteres invisíveis selecionados são removidos antes da inspeção, enquanto o mapeamento preserva a correspondência com o texto original. Assim, uma forma como `<|sys\u200btem|>` pode ser normalizada para `<|system|>`, ser detectada pela família `delimiter` e ainda produzir um span correspondente à região no texto original.

Esse ganho possui escopo específico: trata-se de resistência a determinados caracteres invisíveis, e não de resistência geral a ofuscação. Em particular, leetspeak não faz parte da capacidade desta família.

## Consequências — Resultado da avaliação

A avaliação foi registrada no artefato `dia_06_prompt_injection_evaluation.txt` (commit `90aa208`), utilizando o corpus com SHA-256 `80c9888b3a6ac36457bc6c53d4f0d3fc3672d3529ca9f451aa3a7b2b0aade354`.

Foram bloqueados 2 de 8 ataques, correspondendo a 25,0% de mitigação. Foram bloqueados 3 de 8 casos legítimos, correspondendo a 37,5% de falso positivo. Os falsos positivos foram `leg_03`, `leg_04` e `leg_05`. A família `delimiter` bloqueou 2/2 ataques aos quais foi atribuída e foi responsável pelos dois bloqueios observados nessa família.

A previsão registrada no commit `f866355`, antes da implementação e medição registrada no commit `6917f1b`, foi confirmada: ocorreram 3 falsos positivos em 8 casos legítimos, exatamente nos três casos nomeados anteriormente.

A leitura do resultado não deve ser suavizada: neste corpus, a regra isolada bloqueou mais casos legítimos do que ataques. Sua contribuição líquida é, portanto, negativa no conjunto avaliado. Esse resultado estabelece a linha de base que justifica a implementação das três famílias restantes.

## Consequências — Resultado do benchmark

O resultado de desempenho está registrado no artefato `dia_06_injection_N_10_000.txt` (commit `1503020`). A varredura apresentou custo aproximado de 3 ns/char. O custo marginal foi de aproximadamente 2,4 µs por `Finding`, calculado como a mediana de nove estimativas, com intervalo observado de 2,04 a 2,76 µs. A razão entre o detector e o normalizador foi de 0,96%.

A reprodutibilidade foi avaliada com duas execuções do mesmo código que resultaram em 2,43 ns/char `2,03 µs por Finding` e 2,98 ns/char `2,38 µs por Finding`, ancorando as medições da taxa de varredura e do custo marginal (reportado acima como ~2,4 µs) nos mesmos dois ensaios. Para a taxa de varredura, tomar a primeira execução como referência indica uma diferença de +22,6% (ou −18,5% tomando a segunda); para o `custo marginal por Finding`, a variação correspondente é de +17,2% (ou −14,7%). O valor de 23% é utilizado adiante como aproximação conservadora abrangendo ambas as métricas, e não como incerteza simétrica diretamente medida. Essa variação também encontra paralelo em medições anteriores, como a observada no dia 4, indicando que parte da diferença pode estar associada ao ambiente de execução, embora sua contribuição específica para cada componente não tenha sido isolada. Essa variação não sustenta precisão de dois algarismos significativos; por isso, os valores deste ADR são apresentados com apenas um algarismo significativo quando resumidos.

A ordem de grandeza do custo por `Finding` também concorda com a medição independente realizada com `timeit` no dia 4 para a construção de um `Finding`. Dois métodos distintos chegaram à mesma ordem de grandeza.

O orçamento de 15 ms pode ser fechado apenas como estimativa, pois as três parcelas foram medidas em execuções distintas. A estimativa central é composta por aproximadamente 9,30 ms de normalização, 0,42 ms de PII e 0,09 ms de injection, totalizando cerca de 9,8 ms, ou 65% do orçamento. A reprodutibilidade do normalizador não foi medida novamente neste benchmark; como análise de sensibilidade, aplica-se à parcela de 9,30 ms a amplitude relativa observada nas duas execuções do detector de injection, mantendo PII e injection constantes. Com a aproximação conservadora de ±23%, a faixa do subtotal fica entre 7,7 e 11,9 ms, ou 51% a 79% do orçamento de 15 ms. Essa faixa não representa uma incerteza estatística do pipeline, mas um cenário de sensibilidade baseado na variabilidade observada do ambiente. Em qualquer ponto da faixa, o normalizador permanece como a principal parcela, respondendo por aproximadamente 95% do subtotal medido.

## Consequências — Custos e riscos

A forma de colchete utilizada pela família é deliberadamente ampla e pode casar construções como `[OK]`, `[NOTE]`, `[TODO]`, `[ERROR]` e `array[I]`. A composição e as limitações do corpus estão documentadas em `datasets/README.md`.

No cenário de densidade de log, um texto legítimo de 30.000 caracteres produziu 168 `Finding`s. Custo computacional e falso positivo são manifestações do mesmo fenômeno: um padrão que casa demais bloqueia demais e também produz mais resultados para processar.

Existe uma lacuna para marcadores entre colchetes cujo primeiro caractere é um dígito. `[5Y5T3M]` escapa da âncora atual, que exige uma letra maiúscula no primeiro caractere. Esse comportamento é rastreado por um teste `xfail(strict=True)` e não é considerado prioritário nesta versão, pois um atacante que utilize esse marcador também depende de o modelo reconhecer a sequência como uma fronteira semântica útil.

Leetspeak não é tratado pela implementação atual. Sua avaliação exige a família `instruction_override`, portanto não é testável de forma isolada neste estágio.

O custo de aproximadamente 3 ns/char também não deve ser extrapolado para famílias baseadas em palavras. Na família atual, `<` e `[` são raros em prosa; termos como `ignore`, `disregard` e `forget` terão distribuição de candidatos e comportamento estrutural diferentes.

## Gatilho de reavaliação

A reavaliação deverá considerar simultaneamente custo em µs por `Finding`, quantidade de `Findings` por texto e taxa de falsos positivos em corpus ampliado. O limite de 30 ns/char não será utilizado como único gatilho, pois foi herdado do contexto do detector de PII e atualmente corresponde a aproximadamente dez vezes o custo observado para esta família, tornando-o pouco sensível para regressões relevantes.

Um gatilho quantitativo definitivo será estabelecido quando as três famílias restantes forem implementadas e o comportamento agregado puder ser medido em corpus ampliado. Até então, os resultados deste benchmark constituem a linha de base registrada para `delimiter`.

## Relação com decisões anteriores

O ADR 0006 define a precedência que permite que o score específico de prompt injection participe da decisão por categoria, enquanto este ADR define a estratégia e o primeiro conjunto de regras do detector. O ADR 0003 fornece a normalização e o mapeamento necessário para a resistência a determinados caracteres invisíveis. O ADR 0004 permanece como referência específica para o detector de CPF e seus critérios locais de validação e desempenho.
