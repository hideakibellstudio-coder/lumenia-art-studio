# `ui/core/document/` — documento (fonte única de verdade)

**Responsabilidade:** o estado de cada documento aberto: dimensões, câmera salva, pilha de camadas (`LocalLayerManager`), histórico, formato de arquivo `.lmn`, recuperação. É daqui, e só daqui, que alterações de camada chegam ao motor.

## Porta de entrada

`from ui.core.document import Document, DocumentManager`. Também usados:
`history.layer_transaction`, `layer_commands.LayerCommands`, `layer_blend_mode.LayerBlendMode`,
`serializer.DocumentSerializer`, `restore.restore_document`,
`recovery.RecoveryStore`, `geometry.change_geometry`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | Reexporta `Document` e `DocumentManager`. |
| `document.py` | Document — Representação de um documento aberto no Lumenia. |
| `geometry.py` | Atomic geometry changes: prepare all pixels before committing the new context. |
| `history.py` | One timeline for native pixels and the document's layer metadata. |
| `layer_backend_sync.py` | layer_backend_sync — Sincronizador de Estado e Projeção C++ para LocalLayerManager. |
| `layer_commands.py` | `LayerCommands`: comandos de camada iniciados pela interface (painel de camadas e menu Camada), cada um uma `layer_transaction`. |
| `layer_blend_mode.py` | LayerBlendMode -- enum canonico para o modo de mesclagem de camadas. |
| `layer_manager.py` | `LocalLayerManager`: pilha de camadas do documento; toda alteração passa por aqui e é espelhada no motor por `layer_backend_sync`. |
| `layer_manager_tree_ops.py` | Operações estruturais da pilha de camadas: achatar grupo/imagem, reordenar com reparentamento e substituir a lista inteira (restauração). |
| `local_layer.py` | ui.core.document.local_layer — Modelo de Camada Local do Lumenia. |
| `manager.py` | `DocumentManager` (singleton): documentos abertos, documento ativo e sinais de troca. |
| `paper_backend_sync.py` | `sync_paper_to_backend`: leva cor, visibilidade, textura e grão do papel do documento ao motor (único escritor fora da restauração). |
| `recovery.py` | Session-scoped recovery snapshots, independent of the user's saved file. |
| `restore.py` | Restore a validated document into a newly allocated backend context. |
| `schema.py` | Explicit migrations and portable document state for the LMN container. |
| `serializer.py` | Persistência do formato editável nativo do Lumenia. |

## Regras

- Lei nº 4 (SSOT): painéis são views do `LocalLayerManager`; nenhum painel
  sincroniza o motor por conta própria (ver `plugins/ui/layers_plugin`).
- Operação de camada iniciada pela interface roda dentro de
  `layer_transaction` (um passo de histórico, mensagem de status). Contrato
  do dono: `layer_manager` e `show_status(msg)` (sem descoberta por
  `hasattr`). Donos hoje: `LayerCommands`, `FilterLayerFlow`, `LayerModel`
  (arrastar e soltar) e `SelectionToolController.modify_selection`.
- Comando de camada novo entra em `LayerCommands`, não no painel nem no menu.
- `Document.modified(motivo)` avisa toda alteração que suja o documento.
- Papel: só `Document.set_paper(campo=valor)` altera (suja, sincroniza o
  motor, emite `paper_changed`); views do papel leem do documento.
- Lei nº 5 do rio: pixel que não está no `TileGrid` do motor não é salvo.
- Nada de aparência aqui: a miniatura da camada (`LocalLayer.thumb`) é a
  imagem que o motor devolve; quem desenha marcadores é o delegate do painel.

## Dívida conhecida (medida em 2026-09-24)

`layer_backend_sync.py` avisa o canvas pelo `ui.core.plugins.canvas_access`: o documento conhece o plugin de canvas por um atalho global.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
- `ui/core/engine`
- `ui/core/plugins`
<!-- /arccc:deps -->
