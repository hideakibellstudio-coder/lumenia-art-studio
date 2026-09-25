"""Toda chave literal passada a tr(...) ou Text(...) em ui/ (plugins incluídos) existe nos 4 locales.

Sem isto, uma chave nova cai no texto padrão em português para TODOS os
idiomas -- foi o caso de 25 chaves em 2026-09-22 (menus de escala, telemetria,
máscara de recorte, botões Aplicar/Cancelar).
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCALES = ("pt_BR", "en_US", "es_ES", "ja_JP")


def _flat(d: dict, prefix: str = "") -> set[str]:
    out: set[str] = set()
    for k, v in d.items():
        if isinstance(v, dict):
            out |= _flat(v, f"{prefix}{k}.")
        else:
            out.add(f"{prefix}{k}")
    return out


def _chaves_usadas() -> dict[str, str]:
    usadas: dict[str, str] = {}
    for base in ("ui",):  # plugins embutidos em ui/plugins
        for path in (ROOT / base).rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if (isinstance(node, ast.Call) and getattr(node.func, "id", None) in ("tr", "Text")
                        and node.args and isinstance(node.args[0], ast.Constant)
                        and isinstance(node.args[0].value, str)):
                    usadas.setdefault(node.args[0].value, f"{path.relative_to(ROOT)}:{node.lineno}")
    return usadas


def test_toda_chave_usada_existe_em_todos_os_idiomas():
    usadas = _chaves_usadas()
    for loc in LOCALES:
        disponiveis = _flat(json.loads((ROOT / "assets" / "locales" / f"{loc}.json").read_text(encoding="utf-8")))
        faltando = {k: onde for k, onde in usadas.items() if k not in disponiveis}
        assert not faltando, f"{loc}.json sem {len(faltando)} chave(s): {faltando}"
