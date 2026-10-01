# `ui/infrastructure/bridge_client/` — adaptador do motor Aladyn

**Responsabilidade:** o único lugar que conhece o motor nativo: `AladynBackend` implementa o `EngineBackend` sobre o `aladyn_engine_native` (C++/pybind11), repartido em mixins por assunto.

## Porta de entrada

`from ui.infrastructure.bridge_client import create_backends` — chamado no boot para registrar o backend no `EngineRegistry`. Ninguém mais importa daqui.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | `create_backends()`: fábrica dos backends disponíveis para o `EngineRegistry`. |
| `aladyn.py` | AladynBackend — Adaptador do ALADYN ENGINE (C++ PyBind11 / aladyn_engine_native). |
| `aladyn_base.py` | AladynBackendBase — estado e serviços compartilhados por todos os mixins do AladynBackend. |
| `contract_version.py` | `EXPECTED_CONTRACT_VERSION`: a versão do contrato que esta interface espera; o `AladynBackend` recusa um binário de outra versão ao carregar. |
| `aladyn_brush_mixin.py` | AladynBrushMixin — Mapeamento Atômico de Perfis, Presets e Parâmetros de Pincéis para o AladynBackend. |
| `aladyn_brush_profiles.py` | AladynBrushProfiles — Serialização e Mapeamento de Parâmetros de Pincel. |
| `aladyn_buffers.py` | Pixel format conversion at the canonical RGBA / native intensity boundary. |
| `aladyn_capabilities_mixin.py` | Capacidades efetivas publicadas pelo backend nativo Aladyn. |
| `aladyn_color_mixin.py` | AladynColorMixin — Gerenciamento Atômico de Amostragem de Cor e Perfis ICC para o AladynBackend. |
| `aladyn_geometry_mixin.py` | AladynGeometryMixin — Integração com Guias, Réguas e Simetria C++ do ALADYN ENGINE. |
| `aladyn_layer_mixin.py` | AladynLayerMixin — Gerenciador Atômico de Camadas, Grupos e Filtros para o AladynBackend. |
| `aladyn_mdi_mixin.py` | AladynMdiMixin — Gerenciador de Contextos MDI Multi-Documento para o AladynBackend. |
| `aladyn_persistence_mixin.py` | Persistência do documento ativo (S1.2): instantâneo das camadas, restauração de uma camada por bloco de tiles e o lote que compõe uma vez. |
| `aladyn_resources_mixin.py` | Document-owned canvas assets crossing the canonical backend boundary. |
| `aladyn_selection_mixin.py` | Selection operations mixin for AladynBackend. |
| `aladyn_stroke_mixin.py` | AladynStrokeMixin — Gerenciador Atômico de Traços, Fast-Path e Telemetria para o AladynBackend. |
| `aladyn_transform_mixin.py` | Transform and raster manipulation operations mixin for AladynBackend. |
| `brush_param_table.py` | Tabela Única de Parâmetros de Pincel — o motor define, a interface exibe. |
| `native_fallback.py` | Plano B para binário nativo desatualizado -- nunca em silêncio. |

## Regras

- Lei nº 2: só esta pasta importa `aladyn_engine_native`.
- Estado compartilhado pelos mixins é declarado em `AladynBackendBase`
  (`aladyn_base.py`); mixin não cria atributo que outro mixin lê.
- Método ausente num binário antigo: `native_fallback.nativo_tem(...)`, que
  avisa no log — nunca `hasattr` calado.
- Parâmetro de pincel novo: uma linha em `brush_param_table.TABELA`
  (chave, onde mora no motor, conversão).
- Estado que é de cada documento fica por contexto e volta na troca
  (`set_active_document_context`): o perfil de cor mora em `_doc_profiles`.
  Até 2026-09-24 era um valor só para todos os documentos.

## Dívida conhecida (medida em 2026-09-24)

O backend importa `ui.core.document.layer_blend_mode` (o enum canônico `LayerBlendMode`). Marcar o documento modificado já passa pelo `EngineRegistry.notify_document_modified`, sem importar o modelo.
A Prova de Cores (`set_soft_proofing`) é uma só para todos os documentos e suja o documento ativo, mas não vai no arquivo.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
- `aladyn_engine_native`
- `ui/core/color`
- `ui/core/document`
- `ui/core/engine`
- `ui/infrastructure/config`
<!-- /arccc:deps -->
