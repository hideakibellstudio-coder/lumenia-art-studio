# `benchmarks/` — medidas de desempenho do motor

**Responsabilidade:** medir linhas de base do motor nativo sem impor limites que dependem do hardware.

## Porta de entrada

`python benchmarks/run_engine_benchmarks.py`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `run_engine_benchmarks.py` | Mede e exporta a linha de base (formato conferido por `tests/test_engine_benchmark_runner.py`). |

## Regras

- Pode importar `aladyn_engine_native` diretamente (exceção da Lei nº 2 para benchmarks).
