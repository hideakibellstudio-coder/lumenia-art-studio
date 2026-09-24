# `tests/golden/` — resultados de referência (golden)

**Responsabilidade:** guardar os hashes do resultado atual de composição e de traço, para detectar mudança não intencional no motor.

## Porta de entrada

Lidos por `tests/test_compositing_characterization.py` e `tests/test_stroke_characterization.py`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `compositing_golden.json` | Hash dos pixels compostos por cenário (modos, filtros, grupos). |
| `stroke_golden.json` | Hash dos pixels do traço por combinação de latência e estabilizador. |

## Regras

- Mudança de pixel intencional: apague o golden correspondente, rode o teste para regravar e explique no commit por que o resultado mudou.
