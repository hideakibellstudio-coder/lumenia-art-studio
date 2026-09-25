# Auditoria da estrutura física contra o ARCcC (2026-09-24)

Pedido: "a estrutura física do projeto também deve seguir ARCcC; notei que
ainda não está 100%, principalmente os README de módulos". Referência: o
documento *ARCcC — Atomic Recursive Componentization by Contract* v1.0.0
(seções 2, 3, 4, 14 e 15). Todos os números abaixo foram medidos nesta data
com os comandos indicados.

## 1. README por pasta — corrigido

| Medida | Antes | Depois |
|---|---|---|
| Pastas versionadas com README | 60 de 111 | 111 de 111 |
| Pastas conferidas pelo teste | só as com `.py` de `ui/` e `plugins/` | todas (motor, ponte, testes, scripts, docs, assets, CI) |

Faltavam: o motor C++ inteiro (20 de 20 pastas), a ponte (5 de 5),
`tests/` (4), `scripts/`, `benchmarks/`, `assets/` (7), 6 pastas de `docs/`,
`.github/` (2), `ui/plugins/system`, `ui/plugins/panels`, os temas e os ícones do
plugin de geometria.

`tests/test_arccc_package_docs.py` agora exige, em toda pasta: README,
citação de cada arquivo de código ou documento, e — nas pastas de código dos
pilares — o bloco `arccc:deps` com as dependências medidas (`import` no
Python, `#include` no C++). Comando: `python -m tests.arccc_package_docs`.

## 2. O que ainda diverge do documento ARCcC

### 2.1 Arquivos essenciais por pasta (seção 3.3)

| Exigência | Situação |
|---|---|
| `index` (ponto de entrada) | Python: todo pacote tem `__init__.py` (desde a pendência 9). C++: o motor tem uma porta única para a ponte (`engine/boundary/public-api/AladynEngine.hpp`, passo 4); dentro do motor não há cabeçalho agregador por pasta e o README de cada pasta nomeia o cabeçalho de entrada. |
| `manifest.json` | Nenhuma pasta tem. O projeto usa o bloco `arccc:deps` do README (medido pelo teste) no papel de manifesto de dependências. |
| `testes/` por pasta | A suíte é central (`tests/`, exceção declarada da raiz). |

### 2.2 Raiz reservada aos pilares (seção 15.4, regra 1)

Antes: a raiz tinha os três pilares (`ui/`, `bridge/`, `engine/`) e também
`plugins/` (Python, fora de `ui/`), `assets/`, `docs/`, `tests/`, `scripts/`,
`benchmarks/`, `main.py`, `Iniciar_Lumenia.bat`,
`Iniciar_Lumenia_Silencioso.vbs`, `Enviar_Feedback.html` e
`TERMS_AND_LICENSE.txt`.

Resolvido no passo 5: `plugins/` virou `ui/plugins/` (`plugins/ui/` →
`ui/plugins/panels/`, para não haver `ui.plugins.ui` nem uma pasta `ui` dos
plugins no `sys.path` sombreando o pacote `ui`). Por decisão do dono do
projeto, `tests/`, `docs/`, `assets/`, `scripts/` e `benchmarks/` ficam na raiz
como **exceção declarada** (atravessam os pilares; CI, instalador e build
portátil esperam esses caminhos), ao lado dos arquivos de build/entrada
(`main.py`, `setup.py`, `pyproject.toml`, lançadores, termos). A lista está no
AGENTS.md (seção 2) e em `tests/test_arccc_root_layout.py`, que falha com
entrada nova na raiz.

### 2.3 Estrutura interna de cada pilar (seção 15.3)

| Pilar | Tem | Falta ou sobra |
|---|---|---|
| `ui/` | `boundary/`, `core/`, `infrastructure/`, `plugins/` | Passo 5: os plugins embutidos entraram como `ui/plugins/` (as funcionalidades do pilar; o carregador fica em `ui/core/plugins`). Passo 3: `engine_backends/` virou `ui/infrastructure/bridge_client/` (o cliente da ponte, seção 15.3); configuração, idioma, tema, ícones e caminhos saíram de `ui/core/` para `ui/infrastructure/`; `ui/main.py` e `ui/requirements.txt` (sem uso) saíram. Não há `utils/` (nada genérico o bastante). |
| `engine/` | `boundary/`, `core/`, `infrastructure/`, `utils/` | Resolvido no passo 4: tipos de valor (`Point2D`, `Rect2D`, `MathUtils`, `ColorRGBA`, `Dab`) em `utils/`; compressão, disco de rascunho e telemetria em `infrastructure/`; os orquestradores saíram de `public-api/internal/` para `boundary/orchestrator/`. |
| `bridge/` | `boundary/`, `core/` | Falta `infrastructure/` (mapeamento de erros). |

### 2.4 Dependências entre pastas (seções 4.1 e 15.4)

| Medida | Python (`ui/`, com os plugins) | C++ (`engine/`, `bridge/`) |
|---|---|---|
| Relações de dependência entre pastas | 254 → 262 (passo 3) → 260 (passo 5) | 66 → 69 depois do passo 4 |
| Entre pastas irmãs (regra 2: proibido) | 29 → 21 (passo 3) → 20 (passo 5) | 24 → 20 depois do passo 4 |
| Pares de pastas em ciclo | 9 → 5 (passo 3) → 2 (passo 5) | 9 → 0 depois do passo 4 |
| Subpasta incluindo a pasta-mãe | — | 5 → 0 depois do passo 4 |

- Python, antes: os destinos irmãos mais usados eram `ui/core/config`,
  `ui/core/engine`, `ui/core/i18n` e `ui/core/theme`. No passo 3 os serviços
  transversais foram para `ui/infrastructure/`; saíram os ciclos
  `ui/core` ↔ `i18n`/`theme`/`logging`, `icons` ↔ `theme` (o tema registra as
  cores nos ícones) e `ui/core/dialogs` ↔ `ui/core/widgets` (a cor da sombra
  virou `ThemeManager.shadow_color`).
- Python, depois do passo 3: as 21 relações entre irmãs que sobravam eram, na
  maioria, o contrato do motor (`ui/core/engine`, 5) e a configuração dentro
  de `ui/infrastructure` (3); 5 ciclos, pai ↔ filha dentro dos plugins.
- Python, passo 5: `dock_system.py` foi para `workspace/dock/` (só dependia das
  peças da doca, que o importavam da pasta-mãe), `text_overlay_editor.py` para
  `canvas/tools/` (só a ferramenta de texto usa) e os auxiliares do painel
  avançado (`brush_engine_writer`, `texture_file`, `non_scroll_combo_box`,
  `panel_thumbnails`) para `advanced_panel/sections/`, que os usa. Sobram 2
  ciclos, `canvas` ↔ `tools` e `canvas` ↔ `viewport`, só por anotação de tipo
  do `RenderWidget` (`TYPE_CHECKING`); dívida registrada no README do canvas
  (o `input_router.py` usa 37 membros do widget: dividir o widget vem antes do
  contrato).
- C++, antes: ciclos `canvas` ↔ `document` (o histórico em `canvas/` incluía a
  pilha de camadas), `raster` ↔ `math`/`brush`/`canvas`/`color` (tipos básicos
  em `raster/Dab.hpp` e a seleção dentro de `raster/`) e quatro subpastas que
  incluíam a pasta-mãe (`document/blending`, `document/blending/filters`,
  `document/internal`, `raster/transform`).
- C++, passo 4: tipos de valor para `engine/utils/`; `TileUndoManager` para o
  módulo novo `core/history/`; seleção para `core/selection/`; o enum de
  mesclagem para `document/blending/LayerBlendMode.hpp` e o dos filtros para
  `document/filters/FilterSettings.hpp` (o documento os reexporta); HSV para
  `core/color/`; `document/internal/` voltou para `document/`. O motor ficou em
  camadas — `utils` → `infrastructure` → `core` (`math` → `texture` → `color` →
  `stroke` → `canvas` → `selection` → `brush` → `document` → `history` →
  `raster` → `engines`) → `orchestrator` → `public-api` → ponte — conferidas
  por `tests/test_arccc_cxx_layers.py`. As 20 relações entre irmãs que sobram
  (19 entre módulos de `core/`, e `public-api` → `orchestrator`, que é o par
  da seção 3.1) vão todas para baixo nessa ordem: decisão registrada em
  `engine/core/README.md`.
- A ponte incluía `engine/core/{canvas,color,math,raster}` e
  `engine/boundary/public-api/internal`; desde o passo 4 inclui só
  `engine/boundary/public-api/AladynEngine.hpp`, e a máscara da ponta redonda,
  que era calculada na ponte, passou para o motor (`boundary::renderRoundTipMask`).

### 2.5 Idioma e nomenclatura (seção 14) — resolvido no código de produção (passo 2)

- Arquivos renomeados: `Iniciar_Lumenia.bat` → `Launch_Lumenia.bat`,
  `Iniciar_Lumenia_Silencioso.vbs` → `Launch_Lumenia_Silent.vbs`,
  `Enviar_Feedback.html` → `Send_Feedback.html`, `scripts/monitor_sessao.ps1` →
  `scripts/monitor_session.ps1` (parâmetros `-IntervalSeconds`, `-Analyze`;
  lê CSV antigo com colunas em português).
- Identificadores: catraca nova (`tests/test_arccc_identifier_language_ratchet.py`)
  conta, por arquivo, nomes com palavra portuguesa de uma lista (piso, não
  teto). Medido: 0 em `ui/`, `plugins/`, `scripts/`, `engine/` e `bridge/` depois
  das renomeações (tabela de parâmetros do pincel, fallback nativo, distorção,
  harmonias, scripts de sessão longa, morfologia da seleção, homografia...);
  132 em 25 arquivos de `tests/`, que só podem cair.
- Pastas Python seguem `snake_case` (convenção nativa, seção 14.3). As pastas e
  arquivos de `docs/` ficam em português: `docs/` é exceção declarada da raiz e
  documentação pode ser em português (seção 14.1).

### 2.6 Arquivos sem consumidor ou gerados — resolvido (passo 1)

Saíram: 158 SVG de `assets/icons/` sem consumidor (os ícones vêm de
`ui/infrastructure/icons/svg_catalog.py`; ficaram `close.svg` e `maximize.svg`, fallback
do QSS), a cópia `assets/icons/geometry/` dos ícones do plugin de geometria,
o índice `icon_index.json`, `ui/plugins/plugins_config.json.bak` (cópia de
segurança gerada em execução), `scripts/github_project_dashboard.html` (saída
gerada, agora no `.gitignore`) e os cinco `scripts/bisect_*.py` (diagnósticos
de um crash de encerramento, do primeiro commit, sem referência).

## 3. Plano proposto (por risco, do menor para o maior)

1. **Limpeza sem mudança de comportamento:** remover os SVG sem consumidor, a
   cópia de ícones, o `.bak` e o HTML gerado (e ignorá-los no `.gitignore`);
   decidir se os `bisect_*` viram teste ou saem. **Feito (passo 1).**
2. **Nomes em inglês:** lançadores e página de feedback da raiz, o script de
   monitoramento; catraca de identificadores em português (só pode cair) e
   renomeação progressiva. **Feito (passo 2; `tests/` só pode cair).**
3. **`ui/`:** `engine_backends/` → `ui/infrastructure/` (cliente da ponte) e os
   serviços transversais (`config`, `i18n`, `theme`, registro do motor, log,
   caminhos) → `ui/infrastructure/`, com as catracas e o Navigator conferindo.
   **Feito (passo 3).**
4. **`engine/` e `bridge/`:** `engine/utils/` (tipos básicos, matemática,
   compressão) para quebrar os ciclos; orquestradores fora de `public-api/`;
   a ponte incluindo só a API pública. **Feito (passo 4).**
5. **Raiz:** `plugins/` para dentro de `ui/`; `tests/`, `scripts/`, `docs/`,
   `assets/` e `benchmarks/` ficam na raiz como exceção declarada de monorepo
   (ferramentas e instalador esperam esses caminhos) ou migram para dentro dos
   pilares — decisão do dono do projeto: `plugins/` entra em `ui/`; `tests/`,
   `docs/` e `assets/` (com `scripts/` e `benchmarks/`) ficam na raiz como
   exceção declarada. **Feito (passo 5).**
