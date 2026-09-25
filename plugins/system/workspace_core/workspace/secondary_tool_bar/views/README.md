# `plugins/system/workspace_core/workspace/secondary_tool_bar/views/` — views de opções da barra secundária

**Responsabilidade:** uma view por ferramenta e orientação (horizontal/vertical), cada uma ligada ao `ToolState` pela base `ToolOptionsView`.

## Porta de entrada

`build_option_views(tool_state, brush_state, orientação)` → `{chave de opções: view}`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | `build_option_views`: cria as views de todas as ferramentas numa orientação. |
| `base.py` | OrientedOptionsView — view de opções da barra secundária numa orientação. |
| `eyedrop_transform_views.py` | Conta-gotas (amostragem + cor capturada) e transformação (comandos + interpolação). |
| `fill_views.py` | Balde de tinta e varinha mágica: tolerância e amostragem por região de cor. |
| `selection_view.py` | Seleção retangular, elíptica e laço: suavização da borda, anti-alias e modo de combinação. |
| `shapes_view.py` | Formas vetoriais: tipo, modo de desenho, espessura, cores e o parâmetro extra do tipo. |
| `smudge_view.py` | Smudge: arrasto, coleta de cor e mistura (0–100% na tela, 0–1 no estado). |
| `text_view.py` | Texto tipográfico: fonte, tamanho, estilo, alinhamento, cor; Inserir e Cancelar. |

## Regras

Ver o README da pasta mãe (`secondary_tool_bar/`). Publicar só o campo editado; botões emitem `ToolCommand`.

Texto fixo (título, rótulo de slider) nasce traduzível: `Text(chave, padrão)` passado a
`header_row`, `add_slider`, `view.label` ou `view.translate`, que o reaplicam quando o idioma
muda. `retranslate_ui` fica para o que depende de estado (itens de combo, rótulo que muda com a
ferramenta). Nunca literal em português: `tests/test_i18n_keys_exist.py` confere as chaves de
`tr(...)` e `Text(...)` nos 4 idiomas.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
- `ui/core`
- `ui/core/state`
- `ui/core/widgets`
- `ui/core/widgets/tool_options`
- `ui/infrastructure/i18n`
- `ui/infrastructure/icons`
- `ui/infrastructure/theme`
<!-- /arccc:deps -->
