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
`.github/` (2), `plugins/system`, `plugins/ui`, os temas e os ícones do
plugin de geometria.

`tests/test_arccc_package_docs.py` agora exige, em toda pasta: README,
citação de cada arquivo de código ou documento, e — nas pastas de código dos
pilares — o bloco `arccc:deps` com as dependências medidas (`import` no
Python, `#include` no C++). Comando: `python -m tests.arccc_package_docs`.

## 2. O que ainda diverge do documento ARCcC

### 2.1 Arquivos essenciais por pasta (seção 3.3)

| Exigência | Situação |
|---|---|
| `index` (ponto de entrada) | Python: todo pacote tem `__init__.py` (desde a pendência 9). C++: não há cabeçalho agregador por pasta; o README de cada pasta nomeia o cabeçalho de entrada. |
| `manifest.json` | Nenhuma pasta tem. O projeto usa o bloco `arccc:deps` do README (medido pelo teste) no papel de manifesto de dependências. |
| `testes/` por pasta | A suíte é central (`tests/`, 115 arquivos). |

### 2.2 Raiz reservada aos pilares (seção 15.4, regra 1)

A raiz tem os três pilares (`ui/`, `bridge/`, `engine/`) e também:
`plugins/` (Python, fora de `ui/`), `assets/`, `docs/`, `tests/`,
`scripts/`, `benchmarks/`, `main.py`, `Iniciar_Lumenia.bat`,
`Iniciar_Lumenia_Silencioso.vbs`, `Enviar_Feedback.html` e
`TERMS_AND_LICENSE.txt`.

### 2.3 Estrutura interna de cada pilar (seção 15.3)

| Pilar | Tem | Falta ou sobra |
|---|---|---|
| `ui/` | `boundary/`, `core/`, `infrastructure/` | Sobra `engine_backends/` fora das quatro pastas (o ARCcC coloca o cliente da ponte em `ui/infrastructure/bridge-client/`); sobram `main.py` e `requirements.txt` de compatibilidade; não há `utils/`. |
| `engine/` | `boundary/`, `core/` | Faltam `infrastructure/` e `utils/`; `core/math` e `core/compression` são utilitários. `boundary/public-api/internal/` (27 arquivos) é implementação dentro da API pública. |
| `bridge/` | `boundary/`, `core/` | Falta `infrastructure/` (mapeamento de erros). |

### 2.4 Dependências entre pastas (seções 4.1 e 15.4)

| Medida | Python (`ui/`, `plugins/`) | C++ (`engine/`, `bridge/`) |
|---|---|---|
| Relações de dependência entre pastas | 254 | 66 |
| Entre pastas irmãs (regra 2: proibido) | 29 | 24 |
| Pares de pastas em ciclo | 9 (quase todos pai ↔ filha) | 9 |

- Python: os destinos irmãos mais usados são `ui/core/config`, `ui/core/engine`,
  `ui/core/i18n` e `ui/core/theme` — serviços transversais que, pelo ARCcC,
  morariam em `ui/infrastructure/` (e então deixariam de ser irmãs).
- C++: ciclos `canvas` ↔ `document`, `raster` ↔ `math`, `raster` ↔ `brush`,
  `raster` ↔ `canvas`, `raster` ↔ `color`. A maior parte vem de tipos básicos
  (`raster/Dab.hpp` com `ColorRGBA`) usados por todo mundo.
- A ponte inclui `engine/core/{canvas,color,math,raster}` e
  `engine/boundary/public-api/internal` diretamente, não só a API pública
  (seção 15.4, regra 2).

### 2.5 Idioma e nomenclatura (seção 14)

- Nomes de arquivo em português: `Iniciar_Lumenia.bat`,
  `Iniciar_Lumenia_Silencioso.vbs`, `Enviar_Feedback.html`,
  `scripts/monitor_sessao.ps1`, e as pastas/arquivos de `docs/`.
- Identificadores em português (contagem heurística por palavras comuns, piso
  e não teto): 27 em `ui/`, 5 em `plugins/`, 131 em `tests/`, 6 em `scripts/`;
  no C++, por exemplo `Homografia`, `pintarBaseDeDemonstracao`, `roiAoRedor`.
- Pastas Python usam `snake_case`, não `kebab-case`: é a convenção nativa do
  Python (pacote com hífen não é importável), permitida pela seção 14.3.

### 2.6 Arquivos sem consumidor ou gerados

- `assets/icons/`: 158 dos 160 SVG sem nenhum consumidor no código (os ícones
  vêm de `ui/core/icon_svg_catalog.py`); `assets/icons/geometry/` é cópia byte a
  byte de `plugins/ui/geometry_plugin/assets/`.
- `plugins/plugins_config.json.bak`: cópia de segurança gerada em execução,
  idêntica ao `plugins_config.json`, versionada.
- `scripts/github_project_dashboard.html`: saída gerada, versionada.
- `scripts/bisect_*.py` (5): diagnósticos pontuais de um crash de teardown.

## 3. Plano proposto (por risco, do menor para o maior)

1. **Limpeza sem mudança de comportamento:** remover os SVG sem consumidor, a
   cópia de ícones, o `.bak` e o HTML gerado (e ignorá-los no `.gitignore`);
   decidir se os `bisect_*` viram teste ou saem.
2. **Nomes em inglês:** lançadores e página de feedback da raiz, o script de
   monitoramento; catraca de identificadores em português (só pode cair) e
   renomeação progressiva.
3. **`ui/`:** `engine_backends/` → `ui/infrastructure/` (cliente da ponte) e os
   serviços transversais (`config`, `i18n`, `theme`, registro do motor, log,
   caminhos) → `ui/infrastructure/`, com as catracas e o Navigator conferindo.
4. **`engine/` e `bridge/`:** `engine/utils/` (tipos básicos, matemática,
   compressão) para quebrar os ciclos; orquestradores fora de `public-api/`;
   a ponte incluindo só a API pública.
5. **Raiz:** `plugins/` para dentro de `ui/`; `tests/`, `scripts/`, `docs/`,
   `assets/` e `benchmarks/` ficam na raiz como exceção declarada de monorepo
   (ferramentas e instalador esperam esses caminhos) ou migram para dentro dos
   pilares — decisão do dono do projeto.
