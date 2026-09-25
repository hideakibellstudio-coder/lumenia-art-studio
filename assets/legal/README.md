# `assets/legal/` — avisos de licença de terceiros

**Responsabilidade:** o que a distribuição precisa levar para cumprir as
licenças dos componentes de terceiros (Qt/PySide6, Python, Pillow, NumPy,
SciPy, pybind11, runtime do MSVC, ícones).

## Porta de entrada

`THIRD_PARTY_NOTICES.txt` — o build portátil (`scripts/build_portable.py`)
copia este arquivo para a raiz da distribuição, ao lado da EULA; a pasta
inteira vai junto com `assets/`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `THIRD_PARTY_NOTICES.txt` | Lista dos componentes, licença, direitos autorais e onde está o texto completo de cada um. |
| `LGPL-3.0.txt` | Texto integral da LGPLv3 (Qt, PySide6, shiboken6). |
| `GPL-3.0.txt` | Texto integral da GPLv3, que a LGPLv3 complementa e exige junto. |

## Regras

- O PySide6 não traz o texto da licença no pacote instalado; por isso a LGPLv3
  e a GPLv3 estão aqui. Os pacotes que trazem (Pillow, NumPy, SciPy, pybind11)
  têm o texto copiado dos metadados instalados para `licenses/<pacote>/` da
  distribuição, na hora do build (`copy_third_party_licenses`), incluindo o das
  bibliotecas que cada um embute.
- Dependência nova distribuída (em `pyproject.toml` ou embutida no motor) entra
  em `THIRD_PARTY_NOTICES.txt` no mesmo commit, e, se o pacote traz o texto da
  licença, em `LICENSED_PACKAGES` do `scripts/build_portable.py`.
- Até 2026-09-25 a distribuição não levava nenhum aviso de terceiros.
  Este arquivo não é parecer jurídico: revisão do dono do projeto antes de
  vender.
