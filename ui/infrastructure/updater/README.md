# `ui/infrastructure/updater/` — atualização pelo Velopack

**Responsabilidade:** o único lugar que conversa com o Velopack: procurar uma versão nova no feed (GitHub Releases), baixar só o que mudou (pacote delta) numa thread própria e aplicar ao fechar ou reiniciando. Não decide se a versão pode ser instalada (licença, canal): isso é do `ui/core/updates/`.

## Porta de entrada

`from ui.infrastructure.updater import VelopackUpdater, UpdateThread, FoundUpdate`

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | Porta do pacote. |
| `velopack_updater.py` | `VelopackUpdater`: `available` (falso em desenvolvimento ou numa cópia que o Velopack não instalou), `check`, `download`, `apply_on_exit` (o atualizador do Velopack espera o programa fechar, troca `current\` e, se pedido, abre a versão nova). |
| `update_worker.py` | `UpdateWorker` (roda na thread) e `UpdateThread` (dona da thread; `check` e `download` voltam na hora, as respostas chegam por sinal). |

## Regras

- Falha de rede ou do feed nunca derruba o programa: vira o sinal `failed` e uma linha no log.
- O `velopack` só é importado aqui. A partida (`velopack.App().run()`) fica em `main.py`, antes de qualquer import da interface.
- Nada aqui importa `ui/core`.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
(nenhuma dependência interna)
<!-- /arccc:deps -->
