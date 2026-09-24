# `tests/baselines/` — linhas de base das catracas

**Responsabilidade:** guardar a contagem aceita, por arquivo, das catracas que não podem subir.

## Porta de entrada

Lido por `tests/test_hardcoded_colors_ratchet.py`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `hardcoded_colors.json` | Cores literais aceitas por arquivo (Lei 5); regenerar com `python tests/test_hardcoded_colors_ratchet.py --regerar` só quando a contagem cair. |

## Regras

- A linha de base só é regravada quando a contagem cai (registro de melhoria), nunca para aceitar piora.
