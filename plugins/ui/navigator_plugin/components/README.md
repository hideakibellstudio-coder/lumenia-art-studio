# `plugins/ui/navigator_plugin/components/` — peças do navegador

**Responsabilidade:** a prévia em miniatura com o retângulo arrastável da área visível.

## Porta de entrada

Importar por módulo: `navigator_preview.NavigatorPreview`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | Marca o pacote. |
| `navigator_preview.py` | `NavigatorPreview`: miniatura do documento com o retângulo da área visível, arrastável. |

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
- `ui/infrastructure/icons`
- `ui/infrastructure/theme`
<!-- /arccc:deps -->
