# `tests/fixtures/` — entradas gravadas para os testes

**Responsabilidade:** guardar dados reais de entrada (não resultados esperados: esses ficam em `tests/golden/`) que os testes reproduzem contra o motor.

## Porta de entrada

Lidos por `tests/test_pen_pressure_calibration.py`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `pen_session_real.jsonl.gz` | Sessão gravada em 2026-10-02 com a caneta do dono no Windows (Windows Ink, 59,94 Hz, 105 traços em 9 passos: leve, média, forte, rampa, lento/rápido, hachura, contorno, inclinada, livre). Uma linha JSON por evento: `passo`, `traco`, `k` (press/move/release), `x`, `y`, `p` (pressão 0..1), `tx`/`ty` (inclinação), `ts` (milissegundos do Qt, repetido em rajadas de ~6 eventos), `ponta` (caneta/mouse). Só posição, pressão e tempo: nada de conteúdo do documento. |

## Regras

- Dado gravado nunca é editado à mão. Para trocar a fixture, grave outra sessão e substitua o arquivo inteiro, explicando no commit o que mudou nos testes que a leem.
- A fixture é entrada: o motor muda, ela não.
