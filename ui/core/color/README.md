# `ui/core/color/` — gestão de cor (perfis ICC)

**Responsabilidade:** perfis de cor ICC (nativos, do sistema e do usuário), transformações com LittleCMS (via Pillow `ImageCms`) e a configuração de prova de impressão.

## Porta de entrada

`from ui.core.color import ...` (reexporta o pacote). Consumidores diretos: `proofing.SoftProofConfig`, `proofing.RenderingIntent`, `catalog.get_color_catalog`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | Porta de entrada do subsistema de cor. |
| `catalog.py` | ColorProfileCatalog — Catálogo Canônico Unificado de Perfis de Cor. |
| `cms_engine.py` | ColorManagementEngine — Motor de Gestão de Cor baseado em LittleCMS 2.x (Pillow ImageCms). |
| `icc_profile.py` | ICCProfileInfo — Representação canônica de metadados e bytes de um perfil ICC. |
| `proofing.py` | SoftProofConfig & RenderingIntent — Configuração e contratos de Prova de Cor. |

## Regras

Sem widgets aqui; os diálogos que mostram perfis estão em `ui/core/dialogs`. O motor recebe o perfil pelo `EngineBackend` (`ui/engine_backends/aladyn_color_mixin.py`).

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
(nenhuma dependência interna)
<!-- /arccc:deps -->
