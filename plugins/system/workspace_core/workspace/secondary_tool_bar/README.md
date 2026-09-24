# `secondary_tool_bar/` — barra de opções da ferramenta ativa

**Em uma frase:** mostra, flutuando junto da barra de ferramentas, as opções
da ferramenta ativa (tolerância do balde, fonte do texto, tipo de forma...) e
deixa editá-las; as opções moram no `ToolState`, não aqui.

## Porta de entrada

`from .secondary_tool_bar import SecondaryToolBar` (o `__init__.py`).

```python
bar = SecondaryToolBar(tool_state, brush_state, parent=workspace)
bar.commandRequested.connect(canvas.run_tool_command)   # ToolCommand
bar.sizeChanged.connect(workspace.update_toolbar_position)
bar.set_orientation(QtCore.Qt.Vertical)                 # chamado pelo workspace
bar.option_view("bucket", QtCore.Qt.Horizontal)          # para testes/inspeção
```

## Estrutura

| Arquivo | Responsabilidade |
|---|---|
| `toolbar.py` | Moldura (cápsula, sombra), orientação, pilha de views, mostrar/esconder conforme a ferramenta, reajuste de tamanho. Não guarda opção nenhuma. |
| `dynamic_stacked_widget.py` | Pilha que mede pela página visível. |
| `views/__init__.py` | `build_option_views(tool_state, brush_state, orientação)` → `{chave de opções: view}`. |
| `views/base.py` | `OrientedOptionsView` (layout horizontal/vertical) e fábricas de widgets (slider, toggle, combo, amostra de cor...). |
| `views/*_view(s).py` | Uma view por ferramenta: monta os widgets, `show_options` (estado → tela), `publish` (tela → estado), `retranslate_ui`. |

O vínculo com o estado (`bind`, `publish`, `show_options`, `commandRequested`)
vem de `ui/core/widgets/tool_options/bound_view.py` (`ToolOptionsView`), a
mesma base das páginas de opções do painel de pincel.

## Regras

1. **Uma view por ferramenta e orientação, e elas não se conhecem.** A
   horizontal e a vertical ficam iguais porque mostram o mesmo `ToolState`.
   Nunca copie valor de uma para a outra.
2. **Publique só o campo editado** (`self.publish(tolerance=v)`), nunca o
   dicionário inteiro: publicar tudo sobrescreve com valores velhos o que outra
   tela (painel de pincel) acabou de mudar.
3. **Botão de ação emite `ToolCommand`** (`ui.core.tools`). Nada de
   `self.parent().canvas_widget...`.
4. **Regras entre estados não moram aqui.** "As formas usam a cor do pincel"
   é o `ShapeColorLink`; "o Smudge vai ao motor" é o `ToolEngineSync`
   (`ui/core/state/state_links.py`).
5. Ferramenta nova com opções: acrescente as opções em
   `ui/core/tool_settings.py`, escreva a view em `views/`, registre em
   `build_option_views`. A barra não muda.

## Histórico

Até 2026-09-24: `toolbar.py` com 366 linhas, três mixins de handlers e nove
funções `build_*_panels(toolbar)` que penduravam ~200 atributos na barra
(`slider_bkt_tol_h`, `slider_bkt_tol_v`...); cada handler copiava o valor da
versão horizontal para a vertical com `getattr`/`hasattr`; o botão Desmarcar
não parava a animação da seleção; o painel de pincel não acompanhava o que se
mudava aqui; a barra não encolhia ao trocar estrela por elipse.

## Dependências permitidas

`ui.core.state`, `ui.core.tools`, `ui.core.widgets.*`, `ui.core.i18n`,
`ui.core.icons`, `ui.core.theme`, `ui.core.dialogs.floating_tool_window`.
Nada de canvas, workspace ou outros plugins.

## Testes

`tests/test_secondary_toolbar_structure.py` (contrato),
`tests/test_toolbars_geometry_i18n.py` (tradução).
