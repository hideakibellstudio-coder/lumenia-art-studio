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
| `document_saver.py` | `DocumentSaver`: a segunda metade de salvar numa thread própria (uma gravação por vez, na ordem pedida); o resultado volta na thread da interface por callback; `wait_idle` espera a fila ao sair. |
| `background_queue.py` | `BackgroundQueue`: uma fila de trabalhos numa thread só, na ordem pedida, com resultado e erro de volta na thread do dono por sinal. Base do `DocumentSaver` e do `DocumentLoader`. |
| `document_loader.py` | `DocumentLoader` e `load_document`: a primeira metade de abrir (ler o arquivo e decodificar os blocos de tiles em objetos do motor sem documento) numa thread de fundo; `restore_document` adota o resultado na thread da interface. |
| `document.py` | Document — Representação de um documento aberto no Lumenia. |
| `geometry.py` | Atomic geometry changes: prepare all pixels before committing the new context (pede ao motor o RGBA de cada camada; não passa mais por um arquivo temporário). |
| `history.py` | One timeline for native pixels and the document's layer metadata. |
| `layer_backend_sync.py` | layer_backend_sync — Sincronizador de Estado e Projeção C++ para LocalLayerManager. |
| `layer_commands.py` | `LayerCommands`: comandos de camada iniciados pela interface (painel de camadas e menu Camada), cada um uma `layer_transaction`. |
| `layer_blend_mode.py` | LayerBlendMode -- enum canonico para o modo de mesclagem de camadas. |
| `layer_manager.py` | `LocalLayerManager`: pilha de camadas do documento; toda alteração passa por aqui e é espelhada no motor por `layer_backend_sync`. |
| `layer_manager_tree_ops.py` | Operações estruturais da pilha de camadas: achatar grupo/imagem, reordenar com reparentamento e substituir a lista inteira (restauração). |
| `local_layer.py` | `LocalLayer` (camada, grupo ou filtro) e `default_layer_name`, o nome padrão de camada no idioma atual — o mesmo que a ponte dá à camada inicial do motor. |
| `manager.py` | `DocumentManager` (singleton): documentos abertos, documento ativo e sinais de troca. |
| `paper_backend_sync.py` | `sync_paper_to_backend`: leva cor, visibilidade, textura e grão do papel do documento ao motor (único escritor fora da restauração). |
| `recovery.py` | Session-scoped recovery snapshots, independent of the user's saved file. |
| `restore.py` | Restore a validated document into a newly allocated backend context, num lote do motor (compõe uma vez no fim). |
| `save_capture.py` | `SaveCapture` e `capture_document`: a primeira metade de salvar, que precisa da thread do documento (conferências, manifesto, instantâneo das camadas em poucos ms). A segunda, `DocumentSerializer.write`, roda em qualquer thread. |
| `schema.py` | Explicit migrations and portable document state for the LMN container (versão atual: 3). |
| `serializer.py` | Persistência do formato editável nativo do Lumenia: `write` (comprime e grava), `read` (valida) e `save` (as duas metades de uma vez). Camada = bloco de tiles desde a v3; v1 e v2 (RGBA do canvas inteiro) seguem abrindo. |

## Regras

- Lei nº 4 (SSOT): painéis são views do `LocalLayerManager`; nenhum painel
  sincroniza o motor por conta própria (ver `ui/plugins/panels/layers_plugin`).
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
- `Document.dpi` guarda a resolução de impressão e vai no `.lmn` (campo
  opcional `dpi`; arquivo antigo abre com 300). O id do perfil de cor não é
  campo do documento: é estado do motor por contexto
  (`EngineBackend.get_color_profile` no documento ativo); o documento guarda
  só os bytes ICC embutidos no arquivo.
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
- `ui/infrastructure/i18n`
<!-- /arccc:deps -->
