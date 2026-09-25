# `ui/plugins/panels/geometry_plugin/` — plugin de réguas, simetria e perspectiva

**Responsabilidade:** o painel de guias (réguas, simetria, perspectiva) e seus ajustes avançados.

## Porta de entrada

`GeometryPlugin` (em `plugin.py`, reexportado pelo `__init__.py`); o painel conversa com o canvas pelo `WorkspaceService`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | Reexporta `GeometryPlugin` e `GeometryPanel`. |
| `panel.py` | `GeometryPanel`: escolha e ajuste de guia e simetria da doca; view do `GeometryState`. |
| `plugin.py` | GeometryPlugin — Plugin UI de Réguas, Simetrias e Perspectiva (Lumenia V2). |

## Regras

Lei do rio nº 3: nada de `findChild` para achar o canvas (caso real corrigido na Fase C2a); tipos de guia e simetria pelos enums de `ui/core/geometry`.

O painel não conhece o canvas: recebe o `GeometryState` pelo construtor
(`require(registry, GeometryState)` no plugin), escreve nele e mostra o que
ele tem — o canvas edita o mesmo objeto. O diálogo avançado publica só o
campo editado (`settingsChanged`), que vai para `GeometryState.apply_advanced`.
Até 2026-09-24 o painel guardava uma cópia própria e a empurrava inteira para o
canvas (`set_render_widget` + `rw.geometry_ctrl`), com 4 defeitos medidos em
`tests/test_geometry_state.py`.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
- `ui/plugins/panels/geometry_plugin/components`
- `ui/core/plugins`
- `ui/core/state`
- `ui/infrastructure/i18n`
- `ui/infrastructure/icons`
- `ui/infrastructure/theme`
<!-- /arccc:deps -->
