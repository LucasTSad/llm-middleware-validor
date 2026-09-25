# ADR 0001 — Pipeline de detectores com núcleo isolado

* **Status:** Aceito
* **Data:** 03/09/2026

## Contexto
O middleware precisa inspecionar cada *prompt* em três dimensões distintas (PII, *injection* e orçamento) sob um limite rigoroso de 15 ms de latência adicionada. A validação experimental exige executar essa lógica milhares de vezes para mensurar percentis de desempenho, o que se torna inviável se a execução depender diretamente do ambiente em nuvem ou de *frameworks* de infraestrutura.

## Decisão
Isolou-se o pacote `core/` de qualquer dependência externa de infraestrutura. Ficou decidido que:

* **Isolamento de dependências:** O núcleo não importa `fastapi`, `boto3` nem `httpx`. Essas bibliotecas foram movidas para grupos opcionais no `pyproject.toml`.
* **Contrato via Protocolo:** Optou-se por fazer com que cada detector implemente a interface pura `inspect(text, config) -> list[Finding]`.
* **Separação de responsabilidades:** Os detectores apenas reportam ocorrências. A tradução dessas ocorrências em uma ação final (`ALLOW`, `SANITIZE`, `BLOCK`) foi delegada exclusivamente ao orquestrador.
* **Avaliação por pontuação contínua:** Adotou-se o uso de pontuação contínua comparada a limiares externalizados em vez de regras booleanas rígidas.

**Alternativas Descartadas:**
* **Classificação por LLM secundária:** Descartada por apresentar custos e latência incompatíveis com a meta de < 15 ms.
* **Modelo de ML local:** Descartado devido ao não determinismo e à perda de explicabilidade sobre o motivo dos bloqueios.

## Consequências

**Ganhos:**
* O núcleo tornou-se mensurável de forma isolada, permitindo que cada camada seja desligada individualmente para atribuir o custo exato de latência a cada detector.
* Os limiares de detecção podem ser varridos experimentalmente via configuração, sem necessidade de alterar o código-fonte.
* Testes de contrato automatizados garantem a conformidade da interface sem acoplamento a serviços externos.

**Custos e Limitações:**
* A instalação do projeto passa a exigir o gerenciamento explícito de extras (`pip install -e .` vs `.[api]` vs `.[aws]`), aumentando o risco de acionar `ImportError` em tempo de execução se dependências forem omitidas.
* Exige a criação e manutenção de uma camada adicional de adaptadores para conectar o núcleo isolado aos serviços e frameworks de infraestrutura.
* O núcleo não pode utilizar recursos convenientes oferecidos por bibliotecas como `FastAPI` ou `boto3`, exigindo reimplementação ou abstração manual.
* A detecção baseada em regras e limiares não generaliza para ataques inéditos (zero-day).

