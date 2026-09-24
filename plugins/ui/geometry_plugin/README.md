# `plugins/ui/geometry_plugin/` — plugin de réguas, simetria e perspectiva

**Responsabilidade:** o painel de guias (réguas, simetria, perspectiva) e seus ajustes avançados.

## Porta de entrada

`GeometryPlugin` (em `plugin.py`, reexportado pelo `__init__.py`); o painel conversa com o canvas pelo `WorkspaceService`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | Reexporta `GeometryPlugin` e `GeometryPanel`. |
| `panel.py` | `GeometryPanel`: escolha e ajuste de guia e simetria da doca. |
| `plugin.py` | GeometryPlugin — Plugin UI de Réguas, Simetrias e Perspectiva (Lumenia V2). |

## Regras

Lei do rio nº 3: nada de `findChild` para achar o canvas (caso real corrigido na Fase C2a); tipos de guia e simetria pelos enums de `ui/core/geometry`.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
- `plugins/ui/geometry_plugin/components`
- `ui/core`
- `ui/core/i18n`
- `ui/core/plugins`
- `ui/core/theme`
<!-- /arccc:deps -->
