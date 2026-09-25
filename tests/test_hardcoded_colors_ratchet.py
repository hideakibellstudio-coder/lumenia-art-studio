"""Catraca da Lei 5 (zero hardcode de cores).

Conta, por arquivo de ui/ (plugins incluídos), cores literais (hex "#rrggbb" e
QColor(r, g, b)) que NÃO são o fallback de `ThemeManager.get_color(TOKEN,
"#fallback")`. A linha de base de 2026-09-22 (228 em 54 arquivos, a maioria
cores de conteúdo: guias/réguas sobre o desenho, paletas de amostras) está em
tests/baselines/hardcoded_colors.json. A contagem pode cair; subir exige
decisão explícita (atualizar a linha de base com o motivo no commit).

Regerar a linha de base:  python tests/test_hardcoded_colors_ratchet.py --regerar
"""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASELINE = ROOT / "tests" / "baselines" / "hardcoded_colors.json"
_HEX = re.compile(r"^#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?$")


def contar() -> dict[str, int]:
    contagem: dict[str, int] = {}
    for base in ("ui",):  # plugins embutidos em ui/plugins
        for path in sorted((ROOT / base).rglob("*.py")):
            rel = path.relative_to(ROOT).as_posix()
            if "__pycache__" in rel or rel.startswith("ui/infrastructure/theme/"):
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            fallbacks = {
                id(a)
                for n in ast.walk(tree)
                if isinstance(n, ast.Call) and getattr(n.func, "attr", None) == "get_color"
                for a in n.args[1:]
            }
            n_lit = 0
            for n in ast.walk(tree):
                if isinstance(n, ast.Constant) and isinstance(n.value, str) and _HEX.match(n.value) and id(n) not in fallbacks:
                    n_lit += 1
                elif (isinstance(n, ast.Call)
                      and getattr(n.func, "attr", getattr(n.func, "id", None)) == "QColor"
                      and n.args and all(isinstance(a, ast.Constant) and isinstance(a.value, int) for a in n.args)):
                    n_lit += 1
            if n_lit:
                contagem[rel] = n_lit
    return contagem


def test_cores_literais_nao_aumentam():
    base = json.loads(BASELINE.read_text(encoding="utf-8"))
    atual = contar()
    piorou = {f: (base.get(f, 0), n) for f, n in atual.items() if n > base.get(f, 0)}
    assert not piorou, (
        "Cor literal nova fora do ThemeManager (antes, agora): "
        f"{piorou}. Use ThemeManager.instance().get_color(TOKEN, fallback)."
    )


if __name__ == "__main__" and "--regerar" in sys.argv:
    BASELINE.write_text(json.dumps(contar(), indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print("linha de base regravada:", BASELINE)
