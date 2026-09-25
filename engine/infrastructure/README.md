# `engine/infrastructure/` — infraestrutura do motor

**Responsabilidade:** serviços técnicos que o núcleo usa e que não têm regra de pintura: compressão de blocos, arquivo de rascunho em disco e medidas de telemetria.

## Porta de entrada

Cada subpasta tem a sua (ver o README dela).

## Conteúdo

| Pasta | Responsabilidade |
|---|---|
| `compression/` | Codec LZ4 próprio para tiles e histórico. |
| `storage/` | Disco de rascunho: paginação de blocos do histórico com checksum. |
| `telemetry/` | Métricas do traço em tempo real. |

## Regras

- Infraestrutura só inclui `engine/utils/` e a biblioteca padrão; as subpastas não se incluem entre si (`tests/test_arccc_cxx_layers.py`).
- Nada aqui conhece camadas, pincéis ou documento.
