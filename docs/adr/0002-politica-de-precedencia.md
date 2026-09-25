# ADR 0002 — A política de precedência de ações

* **Status:** Substituído por ADR 0006 — Precedência por máximo de ações
* **Data da substituição:** 25/09/2026
* **Data:** 08/09/2026

## Contexto
Detectores reportam achados de forma independente. O sistema precisa traduzir uma lista heterogênea de objetos `Finding` em uma única decisão final (`Action`). Como múltiplas regras podem disparar sobre o mesmo texto, é necessário estabelecer uma política clara de precedência para evitar ambiguidades no resultado.

## Decisão
Adotou-se uma **função pura** (`decide_action`), externa às classes do pipeline, para avaliar os achados e determinar a ação final. 

Optou-se por codificar explicitamente a seguinte **tabela de precedência** para a resolução de conflitos:

| Condição | Ação |
| :--- | :--- |
| Lista de achados vazia | `ALLOW` |
| Algum achado com severidade >= limiar de bloqueio | `BLOCK` |
| Achado do tipo *injection* com score >= limiar | `BLOCK` |
| Achado do tipo *PII* com severidade abaixo do limiar de bloqueio | `SANITIZE` |
| Nenhuma das anteriores | `BLOCK` |

**Premissas estruturais da decisão:**
* **Isolamento de escopo:** O campo `score` só é consultado para achados de *injection*, pois possui semânticas distintas dependendo da categoria (confiança do ataque vs. confiança da detecção).
* **Fail-safe padrão:** O retorno default do fluxo é `BLOCK`, garantindo segurança em casos não mapeados.

## Consequências

**Ganhos:**
* Política de decisão centralizada, isolada e testável sem dependências do pipeline.
* A adição de novos detectores não exige alterações no motor de decisão, desde que operem por severidade.
* A medição isolada do núcleo (execução dos detector "null" e avaliação da política) é de **0,6 µs no p95**. O custo total do pipeline, **de 4,1 µs**, é dominado pela construção e validação do objeto `Decision`, responsável por **3,5 µs**. A avaliação da política, portanto, não introduz custo computacional relevante.

**Custos e Riscos:**
* A precedência depende diretamente da ordem de avaliação imperativa (`if/elif`). Refatorações no código podem inverter a precedência caso os testes unitários específicos não sejam mantidos.

**Gatilho para Reavaliação:**
* Esta decisão deve ser reavaliada caso surja uma nova categoria de ameaça cujas regras de negócio não se encaixem no modelo baseado prioritariamente em severidade.

**Alternativas Consideradas e Adiadas:**
* Tornar o tipo `Action` ordenável e utilizar `max()` para determinar o resultado. A abordagem foi postergada por adicionar complexidade e não expressar com clareza as regras condicionais compostas (categoria + score).