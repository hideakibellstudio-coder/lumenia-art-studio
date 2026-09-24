# `plugins/ui/navigator_plugin/components/` — peças do navegador

**Responsabilidade:** a prévia em miniatura com o retângulo arrastável da área visível.

## Porta de entrada

Importar por módulo: `navigator_preview.NavigatorPreview`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `navigator_preview.py` | `NavigatorPreview`: miniatura do documento com o retângulo da área visível, arrastável. |

## Dívida conhecida (medida em 2026-09-24)

Pasta sem `__init__.py`.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
- `ui/core`
- `ui/core/theme`
<!-- /arccc:deps -->
