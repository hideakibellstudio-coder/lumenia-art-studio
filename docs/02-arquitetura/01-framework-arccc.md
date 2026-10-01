# Como o ARCcC se aplica ao Lumenia

O Lumenia é construído sob o **ARCcC** (*Atomic Recursive Componentization by
Contract*). O método, universal e independente de projeto, está em
`08-arccc-metodologia-universal.md` (v1.1.0). **Este documento diz só o que é
específico daqui:** os pilares, os números verificados, as exceções declaradas
e onde cada regra do método é feita cumprir. Em caso de dúvida sobre o método,
vale o universal; sobre o projeto, vale este.

Reescrito em 2026-10-01. A versão anterior (zonas de 250 linhas, `plugins/` na
raiz, "a UI não pinta pixels", "mixins de estado") contradizia o código; o
Apêndice E de `../01-correcao-da-base/07-analise-arccc-decomposta.md` lista o que
estava errado.

---

## 1. Os pilares (ARCcC 15)

| Pilar | Linguagem | Papel | Porta de entrada |
|---|---|---|---|
| `engine/` | C++20 | Núcleo de pintura. Sem Python nem Qt; só STL e OpenMP. Camadas `utils` → `infrastructure` → `core` → `boundary`, com `#include` só para baixo | `engine/boundary/public-api/PaintEngineFacade.hpp` |
| `bridge/` | C++ / PyBind11 | Traduz a facade para o Python, valida buffers, mapeia erros. Sem regra de negócio | `bridge/boundary/contracts/*.pyi` |
| `ui/` | Python / PySide6 | Apresentação e orquestração. Plugins moram em `ui/plugins/` | `ui/infrastructure/bridge_client/` (único lugar que importa o binário) |

**Exceção declarada** (decisão do dono, 2026-09-25): `tests/`, `docs/`,
`assets/`, `scripts/` e `benchmarks/` ficam na raiz, porque atravessam os três
pilares e o CI, o instalador e o build portátil esperam esses caminhos.
`tests/test_arccc_root_layout.py` barra qualquer outra entrada na raiz.

Não é verdade que "a UI nunca pinta pixel": forma e texto são rasterizados com
`QPainter` na interface e coladas no motor (D12 do relatório 07). A Lei do Rio 5
(todo pixel passa pelo `TileGrid`) vale para o que fica no documento, e esse
caminho cumpre.

## 2. Números que o projeto verifica

| Regra | Valor | Fonte única (teste) |
|---|---|---|
| Zona verde | até 299 linhas | `tests/arccc_governance_rules.py` |
| Zona amarela | 300 a 449 | idem |
| Parede (sem código novo) | 430 a 449 | idem (`MAX_LINES_WALL`) |
| Zona vermelha | 450 ou mais: violação | idem; vale para `ui/`, `tests/`, `engine/`, `bridge/` |
| Complexidade (barreira) | McCabe até 20 | `[tool.ruff.lint.mccabe]` no `pyproject.toml`; `tests/test_python_lint.py` |
| Complexidade (alerta) | `lizard`, acima de 10 | só relatório; não barra (ver abaixo) |
| Idioma dos identificadores | inglês | `tests/test_arccc_identifier_language_ratchet.py` |
| Camadas do motor | sem ciclo; `#include` só para baixo | `tests/test_arccc_cxx_layers.py` |
| Acoplamento | `hasattr`, `getattr` literal, acesso privado alheio, `except` silencioso | `tests/test_arccc_coupling_ratchet.py` |
| README e dependências por pasta | verdadeiros | `tests/test_arccc_package_docs.py` |

**Por que 20 e não 10 (o método universal pede 10).** O McCabe do `ruff` não
conta operadores booleanos; o `lizard` conta, e acha bem mais funções acima de
10. O custo de baixar a barreira está nos 9 motores de pincel, que repetem a
rasterização; ele cai de uma vez quando o núcleo comum de dab existir. Até lá, o
`lizard` serve de alerta: `python -m lizard engine -l cpp` e
`python -m lizard ui -l python`.

## 3. Desvios declarados do método universal

| O método universal | No Lumenia | Por quê |
|---|---|---|
| Pasta com `manifest.json` | README com bloco `arccc:deps` **medido** (`python -m tests.arccc_package_docs --deps PASTA`) | Dependência escrita à mão envelhece; a medida é conferida por teste |
| Pasta `testes/` em cada pasta | `tests/` na raiz | Exceção declarada acima |
| `public/` e `private/` como pastas | `__init__.py` (a porta) e o README ("Porta de entrada") | Pacote Python não precisa de pasta para esconder módulo; vale a convenção |
| Pastas em `kebab-case` | `snake_case` nos pacotes Python | Pacote Python só se importa em `snake_case`; o motor C++ usa `kebab-case` onde cabe (`public-api`) |
| Complexidade 10, 5 métodos públicos por classe | 20, e a regra dos métodos públicos só vale para classes de **contrato** | Interface Qt tem muitos métodos públicos por natureza |
| Assunto de commit em inglês (14.1) | Vale **a partir de 2026-10-01**; o histórico anterior não se reescreve | Decisão do dono |
| Mixin como unidade de decomposição | Só no `AladynBackend` sobre `AladynBackendBase`; fora dele, colaborador com estado próprio | `AGENTS.md`, seções 4 (lei 6) e 4.2 |

## 4. Onde cada regra é feita cumprir

- **Leis arquiteturais e Leis do Leito do Rio:** `AGENTS.md`, seções 4 e 4.1.
- **Contratos entre componentes (os quatro caminhos permitidos):**
  `06-contratos-entre-componentes.md` e `AGENTS.md`, seção 4.2.
- **Ciclo de construção (ARCcC 4.4) e regras de parada:** `AGENTS.md`, seção 5.0.
- **Estrutura física contra o método:** `07-auditoria-da-estrutura-fisica.md`.
- **Análise sob a v1.1.0, com as portas de validação medidas:**
  `../01-correcao-da-base/08-analise-arccc-v1-1-e-forma-de-trabalho.md`.
