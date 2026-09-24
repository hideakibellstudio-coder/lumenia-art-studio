# Contratos entre componentes — como as peças do Lumenia conversam

> Leitura obrigatória antes de ligar um componente a outro (um painel ao
> canvas, um plugin ao workspace, uma tela ao motor). Criado em 2026-09-24 a
> partir da análise de acoplamento que originou
> `tests/test_arccc_coupling_ratchet.py`.

## O diagnóstico em uma frase

**O teto de linhas foi cumprido fatiando arquivos, não responsabilidades.**
Por meses o projeto teve 0 arquivos na Zona Vermelha e mesmo assim virou
espaguete: um arquivo de 450 linhas virava três de 150 que continuavam sendo
um objeto só — funções livres que recebem `panel` e mexem em
`panel._preview_filter_idx`, mixins que perguntam `hasattr(self, "_mark_document_dirty")`
porque não sabem com quem vão ser combinados, e um workspace que tateava os
painéis dos outros plugins com `hasattr(dock, "qs_size")`.

Medido em 2026-09-24 (ui/ + plugins/, `python -m tests.arccc_coupling_metrics`):

| Padrão | Ocorrências | O que significa |
|---|---:|---|
| `hasattr(obj, "x")` | 781 | o chamador não sabe o tipo do objeto e tateia |
| `getattr(obj, "x", padrão)` | 408 | idem, com valor padrão escondendo a ausência |
| `outro._privado` | 349 | um objeto mexendo no estado interno de outro |
| `except Exception: pass` | 15 | erro engolido sem rastro |
| `ui/` importando `plugins/` | 2 | núcleo dependendo das folhas |

A catraca `tests/test_arccc_coupling_ratchet.py` impede que qualquer arquivo
piore e obriga a registrar cada melhoria. Os números atuais estão em
`tests/arccc_coupling_baseline.json`.

Evolução no mesmo dia, depois das correções (cada linha é um commit com a
medição na mensagem):

| Padrão | Início | Depois de estado/camadas | Depois do canvas | Hoje (barra secundária + limpeza) |
|---|---:|---:|---:|---:|
| `hasattr` | 781 | 637 | 572 | 465 |
| `getattr` literal | 408 | 363 | 303 | 265 |
| privado alheio | 349 | 236 | 166 | 71 |
| `except` silencioso | 15 | 0 | 0 | 0 |
| núcleo → plugin | 2 | 0 | 0 | 0 |

## Os quatro caminhos permitidos

Todo fluxo de informação entre duas peças diferentes usa **um** destes:

### 1. Estado compartilhado (fonte única) — `ui/core/state/`, `ui/core/document/`

Para dado que mais de uma tela mostra ou edita. O estado é um `QObject` com
setters que validam e sinais que avisam. Quem edita chama o setter; quem
mostra escuta o sinal. Valor igual não emite, então não há laço.

- Documento, camadas, histórico: `Document` / `LocalLayerManager`.
- Cor e parâmetros do pincel: `BrushState` (ver `ui/core/state/README.md`).

### 2. Serviço registrado — `ServiceRegistry` + contrato ABC

Para um plugin pedir algo que outro oferece. O provedor registra a
implementação de um contrato (`WorkspaceService`, `BrushState`...); o
consumidor pede pelo tipo, no `activate()`, via `self.context.service_registry`,
e **injeta pelo construtor** nos seus widgets. Widget nenhum faz busca global.

### 3. Sinal público do dono

Para avisar "aconteceu X" sem saber quem se importa (`strokeFinished`,
`toolActivated`). O sinal é declarado na classe, com tipos, e documentado.
Quem conecta é quem se importa.

### 4. Contrato do motor — `EngineBackend`

Para qualquer coisa que toque pixels ou o perfil nativo. Só por métodos do
`EngineBackend` (`ui/core/engine/backend.py`); nunca `_facade`/`_native`,
nunca `aladyn_engine_native` fora de `ui/engine_backends/`.

## Padrões proibidos, com o caso real e a correção

### ✗ Tatear objeto de outro componente

```python
# antes — workspace_brush_adapter.py
if hasattr(dock, "sizeChanged"):
    self._bind_panel_signal(panel_id, dock.sizeChanged, self._on_brush_size)
...
if hasattr(d, "_adv_panel") and d._adv_panel and hasattr(d._adv_panel, "slider_size"):
    d._adv_panel.slider_size.blockSignals(True)
    d._adv_panel.slider_size.setValue(val)
```

O workspace (plugin de sistema) conhecia os widgets internos do plugin de
pincel. **Correção (2026-09-24):** o painel escreve no `BrushState` e se
atualiza pelo sinal dele; o workspace nem sabe que o painel existe para isso.

### ✗ Mesmo dado em vários donos sincronizados à mão

`_saved_color` no workspace, `active_color` no canvas, a cor da roda, a cor do
painel de pincel, a cor da barra secundária e a do motor — cada um atualizado
por um caminho diferente. **Correção:** `BrushState.color` é a única; os
outros são views.

### ✗ Dois caminhos até o motor para o mesmo valor

O painel avançado chamava `backend.set_brush_size(v)` **e** emitia
`sizeChanged`, que o workspace transformava em outro `backend.set_brush_size(v)`.
Carregar textura aplicava duas vezes (via `BridgeClient` e direto).
**Correção:** `BrushEngineSync` é o único escritor desses valores no motor.

### ✗ Decomposição falsa (fatiar por linhas)

```python
# plugins/ui/layers_plugin/panel_actions.py — função livre dona do estado alheio
def add_filter_layer(panel, filter_type=None):
    panel._preview_filter_idx = -1
    ...
    panel._filter_transaction_cancelled = True
```

**Correção:** ao dividir uma classe, extraia um **colaborador**: uma classe
que possui o estado que usa, recebe as dependências no construtor e expõe
métodos públicos. O dono antigo guarda uma referência a ele. Exemplo aplicado:
`CanvasBrushBinding` (recebe estado, canvas e barra no construtor; não lê nada
do `WorkspaceContainer`).

### ✗ Mixin que pergunta por si mesmo

`hasattr(self, "_mark_document_dirty")` repetido 30 vezes nos mixins do
backend: o mixin não sabe se a classe final terá o método. **Correção:** o
método pertence a uma base comum que todos os mixins herdam, ou o mixin vira
colaborador que recebe a função pelo construtor.

### ✗ Teste que fixa o espaguete

`test_brush_texture_io.py` "provava" que a miniatura era atualizada chamando
`dock.update_thumbnail(...)` num `MagicMock` — método que não existia em lugar
nenhum. `MagicMock` aceita qualquer atributo, então o teste passava e a
miniatura nunca mudava. **Regra:** teste o contrato público com objetos reais
(ou um fake com os métodos do contrato), nunca `MagicMock` genérico no lugar
de um componente do próprio projeto.

### ✗ Duas cópias da mesma tela sincronizadas à mão

A barra secundária tinha cada controle duas vezes (`slider_bkt_tol_h` e
`slider_bkt_tol_v`, para as orientações horizontal e vertical) e cada handler
copiava o valor de uma para a outra com `getattr`. O painel de pincel tinha uma
terceira cópia que nunca acompanhava as outras. **Correção:** cada tela é uma
view do `ToolState` (`ToolOptionsView`): mostra em `show_options`, publica em
`publish`. As três ficam iguais porque mostram o mesmo estado, sem se conhecer.

### ✗ Publicar o dicionário inteiro

A página de transformação do painel publicava todas as opções a cada clique:
mudar o "Modo" reescrevia a interpolação com o valor velho da página (o
usuário escolhia "Mais Próximo" na barra, mexia no modo no painel, e voltava a
ser bicúbica). **Correção:** `publish(campo=valor)` só com o campo editado.

### ✗ Regra entre estados em cada tela que a conhece

"As formas usam a cor do pincel" estava implementada três vezes (canvas,
barra, painel), e uma cópia zerava a transparência do fundo. **Correção:** uma
regra, num lugar: `ui/core/state/state_links.py` (`ShapeColorLink`).

### ✗ Botão que alcança o canvas pelo pai

`self.parent().canvas_widget.commit_transform()` com `hasattr` para saber se o
pai era o workspace. **Correção:** o botão emite um `ToolCommand` (enum
canônico em `ui/core/tools.py`) e o workspace liga o sinal em
`RenderWidget.run_tool_command`.

### ✗ Vários caminhos para a mesma coisa

A câmera era empurrada ao motor por cinco cópias de
`bridge_client.update_view(...)`, e o zoom pelo menu nunca chegava ao
Navigator. **Correção:** um método, `RenderWidget.publish_view()`, que atualiza
motor, editor de texto, repintura e sinais — quem muda zoom/pan/rotação chama
ele.

### ✗ Janela Qt coletada pelo GC no meio de outra operação (testes)

Criar diálogos sem pai e deixá-los para o coletor de lixo do Python derruba o
PySide 6.11.1 se a coleta acontecer enquanto outra janela está sendo embrulhada
(achado com gdb e valgrind). **Regra nos testes:** enumerar e apagar janelas
com o GC desligado (`tests/qt_windows.py`); na aplicação, diálogo sempre com
pai.

## Como dividir um arquivo que ficou grande (o jeito certo)

1. Liste as **responsabilidades** do arquivo em frases ("mostra X", "valida
   Y", "sincroniza Z com o motor"). Se não cabe em uma frase, são várias.
2. Para cada responsabilidade que sai, pergunte **quem é dono do estado que
   ela usa**. O estado vai junto com ela.
3. Crie um colaborador (classe) com esse estado, dependências pelo construtor
   e API pública pequena. O dono antigo cria e guarda o colaborador.
4. Nada de `def funcao(owner, ...)` que lê/escreve `owner._x`. Nada de mixin
   novo.
5. Rode `python -m tests.arccc_coupling_metrics` antes e depois: os números do
   arquivo devem cair, nunca subir.

## Checklist antes de commitar

- [ ] `python -m pytest tests/test_arccc_coupling_ratchet.py` verde (e, se
      algo melhorou, `python -m tests.arccc_coupling_metrics --tighten`).
- [ ] Nenhum `hasattr`/`getattr("literal")` novo sobre objeto de outro
      componente.
- [ ] Nenhum `outro._privado` novo.
- [ ] Estado novo que duas telas mostram → está num estado compartilhado,
      não duplicado nos widgets.
- [ ] Widget novo recebe suas dependências pelo construtor.
- [ ] O `README.md` da pasta tocada continua verdadeiro: arquivo novo na
      tabela, import novo entre pastas no bloco `arccc:deps`
      (`python -m pytest tests/test_arccc_package_docs.py`).
- [ ] Duas telas do mesmo dado são views do mesmo estado; nenhuma copia valor
      para a outra.
