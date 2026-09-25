# 🏛️ CONSTITUIÇÃO ARQUITETURAL & GUIA OPERACIONAL DE AGENTES
# Lumenia Art Studio & ALADYN ENGINE

> [!IMPORTANT]
> **LEITURA OBRIGATÓRIA PARA QUALQUER AGENTE DE IA OU DESENVOLVEDOR.**
> Este documento é a regra Always-On soberana do projeto. Qualquer agente (Antigravity, Claude, Codex, GPT, Gemini, etc.) que opere nesta base de código **DEVE** seguir integralmente estas diretrizes para manter o repositório 100% limpo, modular e funcional.

---

## 🧹 1. PROTOCOLO DE HIGIENE E ANTIPOLUIÇÃO (ZERO-DIRT POLICY)

O repositório foi totalmente saneado, reduzindo o tamanho de 3.4 GB para ~7 MB. Para impedir que a base volte a ser poluída:

### 🚫 NUNCA FAÇA (Ações Terminantemente Proibidas):
1. **NUNCA crie pastas temporárias dentro do repositório**:
   - É expressamente proibido criar pastas como `scratch/`, `temp/`, `tmp/`, `dumps/` ou `test_outputs/` dentro de `Lumenia/`.
2. **NUNCA gere ou salve imagens de teste na árvore de código**:
   - Imagens de depuração (`.png`, `.jpg`, `.raw`) geradas durante testes visuais devem ser descartadas imediatamente ou salvas em pastas temporárias do sistema (`%TEMP%`).
3. **NUNCA grave logs de depuração dentro do repositório**:
   - Nenhuma pasta `logs/` ou arquivos `*.log` devem ser criados na raiz. Mensagens de depuração vão exclusivamente para `stdout`/`stderr` do processo de teste.
4. **NUNCA compile ou gere artefatos dentro da árvore de fontes** (o único `.pyd` permitido é o `aladyn_engine_native.*.pyd` que o build copia para a raiz; cópias em outras pastas carregam binários velhos em silêncio — achado em 2026-09-22):
   - A compilação é **Out-of-Tree**. Todos os arquivos intermediários (`.obj`, `.ilk`, `.pdb`, `.clcache`, `Lumenia.build`) pertencem à pasta externa `../build`.
   - Distribuições finais compiladas pertencem à pasta externa `../dist`.
5. **NUNCA commite arquivos de despejo ou relatórios de crash**:
   - `.coverage`, `nuitka-crash-report.xml`, relatórios de profiling ou testes não pertencem ao repositório.

### ✅ ONDE ARMAZENAR ARTEFATOS TEMPORÁRIOS DURANTE A SESSÃO:
- Se precisar rodar um script pontual de teste/inspeção, crie-o na pasta de rascunho do seu próprio ambiente de agente (ex: `<appDataDir>/brain/<conversation-id>/scratch/`) ou em `%TEMP%`.
- Se um script for temporariamente colocado no repositório para uma checagem rápida, **DELETE-O antes de finalizar o turno**.

---

## 🏗️ 2. TOPOLOGIA DO AMBIENTE LIMPO (OUT-OF-TREE)

O ambiente é particionado em diretórios irmãos no nível superior:

```text
+ LUMENIA CLEAN/
├── Lumenia/                             # Repositório de código 100% puro + .git (sempre leve, ~7 MB)
│   ├── engine/                          # Motor C++20 em camadas: utils/ → infrastructure/ → core/ → boundary/ (orchestrator, public-api)
│   ├── bridge/                          # PyBind11 bindings e contratos .pyi (do motor, só inclui public-api/AladynEngine.hpp)
│   ├── ui/                              # Pilar Python/PySide6: boundary/ (casca), core/ (núcleo), infrastructure/ (ponte com o motor, config, idioma, tema, ícones, logging), plugins/ (workspace e painéis)
│   ├── assets/                          # Ícones e recursos visuais
│   ├── docs/                            # Documentação técnica reconstruída
│   ├── scripts/                         # Scripts oficiais de automação
│   └── tests/                           # Suíte automatizada (conte com `python -m pytest --collect-only -q`)
├── ARCcC-Navigator/                     # Ferramenta de auditoria arquitetural
├── build/                               # 📁 ARTEFATOS DE COMPILAÇÃO INTERMEDIÁRIOS (fora do código!)
│   ├── temp_native/                     # Objetos .obj, .lib, .pdb gerados pelo MSVC
│   └── portable/                        # Caches intermediários C do Nuitka (Lumenia.build)
└── dist/                                # 📁 DISTRIBUIÇÃO E ENTREGÁVEIS FINAIS
    ├── Lumenia_Setup_v0.2.0.exe         # Instalador oficial (55.6 MB)
    └── portable/Lumenia.dist/           # Executável portátil standalone
```

**Raiz do repositório (ARCcC 15.4, regra 1):** os três pilares (`ui/`, `bridge/`,
`engine/`) e arquivos de build/entrada do monorepo (`main.py`, `setup.py`,
`pyproject.toml`, `requirements-dev.*`, lançadores `Launch_Lumenia.*`,
`Send_Feedback.html`, `TERMS_AND_LICENSE.txt`, `README.md`, `AGENTS.md`,
configuração do git e `.github/`). **Exceção declarada** (decisão do dono do
projeto, 2026-09-25): `tests/`, `docs/`, `assets/`, `scripts/` e `benchmarks/`
ficam na raiz — atravessam os três pilares, e CI, instalador e build portátil
esperam esses caminhos. Até 2026-09-25 os plugins moravam em `plugins/`, na
raiz; hoje estão em `ui/plugins/`. Entrada nova na raiz fora dessa lista faz
`tests/test_arccc_root_layout.py` falhar.

---

## 📏 3. GOVERNANÇA DE CÓDIGO & TETOS DE LOC (ARCcC)

O projeto aplica estritamente a metodologia **ARCcC** (*Atomic Recursive Componentization by Contract*):

| Zona | Linhas de Código (LOC) | Ação Obrigatória para o Agente |
|---|:---:|---|
| 🟢 **Zona Verde** | $\le 299$ LOC | Ideal / Padrão esperado. |
| 🟡 **Zona Amarela** | $300$ a $449$ LOC | Aceitável para módulos coesos. Exige atenção para não crescer. |
| 🔴 **Zona Vermelha** | $\ge 450$ LOC | **VIOLAÇÃO GRAVE DE ENTREGA**. O agente é obrigado a dividir o arquivo antes de responder ao usuário. |

> Fonte única dos números: `tests/arccc_governance_rules.py` (espelhada no perfil
> `lumenia` do Navigator). Até 2026-09-22 esta tabela dizia "amarela a partir de
> 251" enquanto o teste e o Navigator usavam 300; alinhada ao que é de fato
> verificado.

### Censo Atual (medido em 2026-09-25 com `wc -l` em `ui/`, plugins incluídos):
- **0 arquivos na Zona Vermelha e nenhuma exceção de LOC declarada.** Nenhuma alteração pode criar ou expandir um arquivo para $\ge 450$ linhas.
- 314 verdes, 35 amarelos e **0 na parede** (430–449).
- **Parede dos 450:** arquivo entre 430 e 449 linhas não recebe código novo sem antes ser dividido — um teto usado como meta produz arquivos espremidos, não coesos.
- **Dividir é por responsabilidade, não por tamanho.** O diagnóstico de
  2026-09-24 achou o teto de LOC "cumprido" com mixins e funções soltas que
  recebem o dono e escrevem nos atributos privados dele: o arquivo encolhe e o
  acoplamento continua igual. Como dividir direito: seção 4.2.

---

## 🔒 4. AS 6 LEIS ARQUITETURAIS INVIOLÁVEIS

1. **Zero Cross-Plugin Imports**: Um plugin em `ui/plugins/` **NUNCA** importa outro plugin irmão diretamente. Comunicação entre plugins deve usar a API de plugins ou componentes compartilhados em `ui/core/`.
2. **Isolamento de Binário C++**: É expressamente proibido importar `aladyn_engine_native` fora de `ui/infrastructure/bridge_client/`. Exceção aceita: testes de caixa-branca do motor nativo (`tests/test_lowlevel_*.py` e afins) e scripts isolados de diagnóstico/benchmark na raiz do repositório (`diag_*.py`, `benchmarks/`) podem importar o módulo diretamente — não são código que a UI executa em produção. Auditado na Fase de panorama pós-C5 (2026-09-17): 20 ocorrências, todas nessa categoria (ver `claude/panorama-leis-do-rio-pos-c5.md` no Projects).
3. **Zero Acesso a Atributos Privados**: A UI nunca acessa `_facade` ou `_native`. Toda comunicação é mediada por métodos canônicos em `EngineBackend`.
4. **Fonte Única de Verdade (SSOT)**: O estado do documento reside em `Document` / `LocalLayerManager` (`ui/core/document/`). Painéis e widgets de UI são apenas **Views** reativas sincronizadas por sinais Qt.
5. **Zero Hardcode de Cores**: Sempre utilize `ThemeManager.instance().get_color(...)` ou classes de estilo QSS.
6. **Contratos e Mixins**: O `AladynBackend` é orquestrado por mixins especializados (`aladyn_color_mixin`, `aladyn_layer_mixin`, etc.) sobre `AladynBackendBase`, que declara todo o estado que eles compartilham (mixin não cria atributo que outro mixin lê). Fora do backend, prefira colaborador com estado próprio a mixin novo (seção 4.2). Nunca concentre código novo em uma classe monolítica.

---

## 🌊 4.1 AS 5 LEIS DO LEITO DO RIO (GOVERNANÇA DE FLUXO)

Registradas em 2026-09-17 a partir da "Análise Pós Solidificação" (2ª varredura
total, `Planos/Analise Pos Solidificacao Sem navigator.MD`) — a metáfora que dá
nome a esta seção: sem um leito bem definido, cada agente que passa pelo código
escava seu próprio curso (um `_flood_layers` aqui, um `findChild` ali), e o rio
transborda. Estas 5 leis complementam as 6 Leis da seção 4 (não substituem);
onde se sobrepõem, é porque detalham um caso concreto de violação já visto na
prática neste projeto.

1. **Proibição de Estado e Buffers Efêmeros em Widgets**: é expressamente
   proibido criar listas, dicionários de estado de réguas/guias ou buffers
   `QImage`/`QPixmap` dentro de um `QWidget`. O widget é uma lente descartável
   que apenas exibe o que `Document`/`LocalLayerManager` e `EngineBackend`
   fornecem — nunca um dono de estado. (Detalha a Lei nº4/SSOT da seção 4; caso
   real corrigido: `_flood_layers` no `CanvasWidget`, Fase C1.)
2. **Proibição de Mocks e Algoritmos Matemáticos Duplicados**: se uma
   funcionalidade já existe implementada em C++ (ex.: `snap_point`,
   `flood_fill`, `transform`), é estritamente proibido reimplementar uma
   versão alternativa em Python "para quebrar o galho". O agente DEVE ligar a
   UI ao método nativo correspondente, ou, se o método nativo existente for
   estruturalmente incompatível com o que a UI precisa (caso real: divergência
   entre `snapPoint()` nativo e `snap_ray_perspective()` Python, Fase C2b),
   expor um método nativo novo e correto — nunca duplicar a matemática em
   Python como solução definitiva.
3. **Desacoplamento via ServiceRegistry (Zero `findChild` entre Plugins)**:
   nenhum painel pode navegar pela árvore de widgets com
   `findChild`/`parent().parent()` para alcançar outro plugin ou o canvas.
   Toda comunicação entre plugins DEVE usar o contrato formal do workspace
   (`add_panel`/`set_render_widget`) ou sinais do `WorkspaceService`. (Caso
   real corrigido: hack `findChild(QtWidgets.QWidget, "CanvasWidget")` +
   `QTimer.singleShot` polling no `GeometryPanel`, Fase C2a.)
4. **Enums Canônicos Tipados (Fim dos Números Mágicos)**: parâmetros que
   cruzam a fronteira UI → Python → C++ (modos de simetria, tipos de guia,
   modos de mesclagem de camadas, etc.) devem ser representados por classes
   `Enum` únicas e canônicas, espelhando exatamente os enums nativos
   (`enum math::SymmetryType`, `enum math::GuideType`, etc.) — nunca
   strings soltas na UI mapeadas por dict ad-hoc (`m_map`, `gmap`) para
   inteiros no meio do caminho. ✅ Corrigido na Fase C5 (2026-09-17):
   `GuideType`/`SymmetryMode` em `ui/core/geometry/` e `LayerBlendMode`
   em `ui/core/document/` (não `ui/core/types/` — local ajustado durante
   a implementação). Ver `claude/verificacao-cruzada-planos-solidificacao.md`
   no Projects para o diagnóstico completo e os dois bugs de comportamento
   que essa consolidação corrigiu.
5. **Regra da Linha Única de Salvamento**: qualquer pixel desenhado na tela
   DEVE passar pelo `TileGrid` do motor C++ para que sua persistência pelo
   `DocumentSerializer` seja garantida. Se não está no `TileGrid`, não existe
   — não há caminho alternativo de composição/salvamento fora dele. (Mesmo
   caso do item 1: `_flood_layers` nunca era serializado, perdendo dados
   silenciosamente ao salvar/reabrir.)

---

## 🧭 4.2 CONTRATOS ENTRE COMPONENTES (COMO NÃO RECRIAR O ESPAGUETE)

Registradas em 2026-09-24, depois de desfazer o espaguete de pincel,
ferramentas, camadas, canvas e barra secundária. Guia completo, com os casos
reais de antes/depois: `docs/02-arquitetura/06-contratos-entre-componentes.md`.

**Quatro caminhos permitidos entre componentes** (qualquer outro é espaguete):

1. **Estado compartilhado** (`ui/core/state`): quem edita chama o estado
   (`BrushState.set_color`, `ToolState.update_options`); quem mostra escuta o
   sinal. Valor igual não emite — nenhuma view precisa de guarda de reentrância.
2. **Injeção pelo construtor**: o widget recebe o que usa
   (`BrushSettingsPanel(brush_state, tool_state)`); o plugin obtém com
   `require(context.service_registry, Tipo)`. Nenhum widget faz busca global.
3. **Sinal para fora + dono que liga**: a peça emite (`commandRequested`,
   `sizeChanged`) e quem a criou conecta. Nunca `self.parent().x`, nunca
   `findChild`, nunca `hasattr(pai, "metodo")`.
4. **Contrato do motor**: só `EngineRegistry.instance().get_backend()` e os
   métodos de `EngineBackend`; um único escritor por assunto
   (`BrushEngineSync`, `ToolEngineSync`, `layer_backend_sync`).

**Proibido** (a catraca de acoplamento conta e não deixa subir):

- `hasattr`/`getattr("literal")` em objeto que não é seu, para descobrir se ele
  "tem" algo. Se o contrato garante, chame; se não garante, mude o contrato.
- Ler ou escrever `obj._privado` de outra classe.
- Mixin que lê atributo criado por outro mixin, e função solta
  `montar_x(dono)` que pendura atributos no dono. Use um **colaborador com
  estado próprio** (classe com construtor que recebe o que usa), como
  `CanvasStrokePipeline`, `CanvasCursorController`, `LayerCommands`.
- Duas cópias de um estado sincronizadas à mão (ex.: `slider_h`/`slider_v`
  copiando um para o outro). Duas telas do mesmo dado são duas views do mesmo
  estado e não se conhecem.
- Publicar o dicionário inteiro de opções quando o usuário mexeu num campo:
  publique só o campo (`ToolOptionsView.publish(campo=valor)`).
- Regra entre estados implementada em cada tela que a conhece: ela mora num
  lugar só (`ui/core/state/state_links.py`).
- `except Exception: pass` (catraca `silent_except` está em 0).

**Toda pasta tem README** — todas mesmo: `ui/` (com `ui/plugins/`), o motor C++
(`engine/`), a ponte (`bridge/`), `tests/`, `scripts/`, `docs/`, `assets/` —
com responsabilidade, porta de entrada, tabela de arquivos, regras e, nas pastas
de código dos pilares, o bloco `arccc:deps` com as dependências medidas
(`import` no Python, `#include` no C++). Leia o README antes de mexer; pasta
nova, arquivo novo ou dependência nova entre pastas atualiza o README no mesmo
commit (o teste `tests/test_arccc_package_docs.py` falha se não). Até
2026-09-24 o teste só via as pastas Python e 51 das 111 pastas não tinham
README; divergências restantes da estrutura física em
`docs/02-arquitetura/07-auditoria-da-estrutura-fisica.md`.

---

## 🔄 5. FLUXO DE TRABALHO PADRONIZADO PARA AGENTES (5 PASSOS)

Qualquer agente que receba uma tarefa deve seguir este ciclo rigoroso:

```text
[1. Diagnóstico] ──> [2. Edição Limpa] ──> [3. Teste Unitário] ──> [4. Higiene/Limpeza] ──> [5. Validação Global]
```

1. **Passo 1: Diagnóstico e Leitura**:
   - **Leia o `README.md` da pasta que vai mexer** (e o da pasta mãe): ele diz
     a responsabilidade, a porta de entrada, as regras e a dívida conhecida.
   - **Consulte o ARCcC-Navigator ANTES de ler arquivos à mão.** `navigator_context`
     sobre o símbolo devolve contrato, consumidores e corpo relevante dentro de um
     orçamento de tokens. Se a mudança toca assinatura, contrato público ou `.pyi`,
     rode `navigator_impact` antes de escrever qualquer linha.
   - Só depois, e só para o que o pacote de contexto não cobriu, inspecione
     arquivos com `view_file` ou `grep_search`. Não crie arquivos de dump para ler código.
   - **Leia `docs/01-correcao-da-base/03-protocolo-do-navigator.md` antes de interpretar qualquer saída do Navigator.**
     As cinco categorias epistemológicas não são níveis de severidade e são
     rotineiramente mal lidas: `suspicious` é limitação da ferramenta, não defeito
     do código, e `declared_exception` é autorização deliberada que não se toca.
2. **Passo 2: Edição Limpa e Fatiamento**:
   - Ao criar ou editar arquivos, monitore a contagem de linhas. Se um arquivo
     estiver perto de 400 linhas, divida-o **por responsabilidade**: extraia um
     colaborador com estado próprio (seção 4.2). **Não** divida em mixins nem em
     funções soltas que recebem o dono — isso só move o espaguete de arquivo.
   - Arquivo novo: acrescente a linha dele no README da pasta. Import novo entre
     pastas: atualize o bloco `arccc:deps` do README
     (`python -m tests.arccc_package_docs --deps PASTA`).
3. **Passo 3: Execução de Testes Direcionados**:
   - Execute o teste automatizado do módulo afetado:
     ```powershell
     python -m pytest tests/test_color_management_cms.py
     ```
4. **Passo 4: Protocolo de Higiene e Limpeza**:
   - Execute `git status --short`.
   - Certifique-se de que **NENHUM** arquivo não-rastreado temporário, rascunho ou lixo foi deixado para trás.
5. **Passo 5: Validação Global**:
   - Execute a suíte de testes completa ou relevante para garantir que todos os testes permaneçam **100% GREEN**.
   - **Catracas locais (rodam dentro da suíte):**
     - acoplamento (`tests/test_arccc_coupling_ratchet.py`): `hasattr`,
       `getattr` literal, acesso privado alheio, `except` silencioso e núcleo
       importando plugin, contados por arquivo. Subiu → você acoplou; caiu →
       registre com `python -m tests.arccc_coupling_metrics --tighten`;
     - documentação por pasta (`tests/test_arccc_package_docs.py`);
     - idioma dos nomes (`tests/test_arccc_identifier_language_ratchet.py`):
       identificador com palavra em português não pode aumentar em nenhum
       arquivo (código em inglês; português só em comentário, doc e `tr`).
       Caiu → `python -m tests.arccc_identifier_language --tighten`;
     - camadas do motor C++ (`tests/test_arccc_cxx_layers.py`): sem ciclo de
       pasta, subpasta sem incluir a mãe, `#include` só para baixo e a ponte só
       pela API pública; módulo novo em `engine/core` entra em `CORE_ORDER`;
     - cores literais (`tests/test_hardcoded_colors_ratchet.py`) e varreduras
       cegas/leis do rio (`tests/test_river_ratchets.py`);
     - linter (`tests/test_python_lint.py`): `ruff check .` com as regras de
       `[tool.ruff]` do `pyproject.toml`, zero achados desde 2026-09-25.
       Import sem uso: `ruff check --fix .`; nome importado só para
       reexportar vai no `__all__` do pacote.
   - **Catraca arquitetural:** rode `navigator_verify` e compare a contagem de
     achados com a anterior. Ela pode cair ou ficar igual; **se subir, você
     introduziu algo** — investigue antes de entregar. Se a mudança tocou arquivos
     indexados, rode `index` no terminal antes (nunca via MCP: bloqueia o servidor).
   - **Números medidos, não adjetivos:** toda contagem escrita em doc, changelog ou
     commit ("N testes", "0 arquivos na Zona Vermelha") vem do comando rodado
     nesta sessão. Em 2026-09-21 o changelog afirmou "100% Zona Verde" e "zero
     vazamentos" sem medir, e as duas frases estavam erradas.
   - Antes de ler qualquer achado, confirme que o índice não está vazio: contagem
     de símbolos plausível, `insufficient_info` em 0, sem `cxx_empty_extraction`.
     **Relatório limpo sobre índice vazio parece perfeito e já escondeu um motor
     C++ inteiro fora da auditoria neste projeto.**

---

### 5.1 Agente em Linux, projeto em Windows (obrigatório antes de todo commit)

O dono do projeto usa **Windows** e o CI compila com **MSVC no Windows**; agentes
costumam rodar em **Linux**. O que passa no Linux pode quebrar lá (achados de
2026-09-25: acentos corrompidos no `setup.py` por arquivo UTF-8 salvo como
cp1252; trechos `#ifdef _WIN32` que o g++ do Linux nunca compila). Antes de
commitar, o agente em Linux roda:

1. a suíte completa (`python -m pytest`) com o `requirements-dev` instalado —
   sem o pytest-qt, exceção dentro de slot do Qt só é impressa e o teste passa
   no Linux enquanto falha no Windows (achado em 2026-09-25; o
   `tests/test_dev_environment.py` falha se ele faltar). A suíte inclui
   `tests/test_windows_portability.py`: nomes que colidem sem diferenciar
   maiúsculas, nomes inválidos no Windows, caminhos longos, texto que não é
   UTF-8 ou já corrompido, e `open`/`read_text`/`write_text` de texto sem
   `encoding=`;
2. `python scripts/check_windows_build.py` quando o commit toca `engine/`,
   `bridge/` ou `setup.py`: compila os `.cpp` do `setup.py` para o alvo Windows
   com MinGW-w64 (escalar e AVX2, como o CI), com aviso tratado como erro
   (`-Wall -Wextra -Werror`; o motor tem zero avisos desde 2026-09-25).
   Instalação no Debian/Ubuntu: `apt-get install g++-mingw-w64-x86-64-posix`.

Regras de código que valem pelo mesmo motivo:

- texto sempre com `encoding="utf-8"` (no Windows o padrão é cp1252);
- caminho com `pathlib`/`os.path` e comparação com `as_posix()` — nunca
  `relpath(...)` comparado com `"ui/"` (no Windows vem `ui\`);
- processo filho com `sys.executable`, nunca `"python3"`; nada de `/tmp` fixo;
- C++ que depende da plataforma fica atrás de `#ifdef _WIN32` e é conferido
  pelo script acima.

**CI só à mão (decisão do dono do projeto, 2026-09-25):** push e PR não
disparam o GitHub Actions — cada run são 5 jobs Windows e a cota do repositório
privado acabava, deixando todo commit com X vermelho. A conferência de cada
commit é a desta seção, feita pelo agente antes de commitar; o workflow
(`.github/workflows/ci.yml`) continua disponível em Actions → Lumenia CI → Run
workflow, útil antes de um release. Job que falha em 2 segundos, sem runner e
sem log, é cota esgotada (GitHub → Settings → Billing), não erro do código.

## 🛠️ 6. COMANDOS CANÔNICOS OFICIAIS

- **Rodar a Suíte Completa de Testes**:
  ```powershell
  python -m pytest
  ```
- **Conferir o build do Windows a partir do Linux (MinGW-w64)**:
  ```bash
  python scripts/check_windows_build.py            # escalar e AVX2
  ```
- **Linter Python (zero achados)**:
  ```powershell
  ruff check .            # --fix remove import sem uso
  ```
- **Recompilar a Extensão Nativa C++ (Out-of-Tree)**:
  ```powershell
  python scripts/build_native.py --simd scalar
  ```
  *(Os objetos intermediários irão automaticamente para `../build/temp_native`)*
- **Gerar a Distribuição Portátil Standalone (Out-of-Tree)**:
  ```powershell
  python scripts/build_portable.py
  ```
  *(A compilação irá automaticamente para `../build/portable`)*
- **Catraca de acoplamento (relatório e aperto)**:
  ```powershell
  python -m tests.arccc_coupling_metrics --top 20   # onde está o acoplamento
  python -m tests.arccc_coupling_metrics --tighten  # registra uma melhoria
  ```
- **Documentação por pacote**:
  ```powershell
  python -m tests.arccc_package_docs                   # pendências
  python -m tests.arccc_package_docs --deps PASTA      # dependências medidas
  python -m tests.arccc_package_docs --scaffold PASTA  # esqueleto de README
  ```
- **Auditoria de Conformidade com o ARCcC Navigator**:
  ```powershell
  cd ../ARCcC-Navigator
  python main.py index Lumenia
  python main.py verify Lumenia --profile lumenia
  ```\n