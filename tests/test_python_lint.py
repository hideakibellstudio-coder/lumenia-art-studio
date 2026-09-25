"""Linter Python: zero achados do ruff com as regras de `pyproject.toml`.

Até 2026-09-25 o projeto não tinha linter; `ruff check --select F` achava 237
problemas: 215 imports sem uso, 17 variáveis sem uso (umas escondiam cor do
tema calculada e nunca aplicada) e um `__init__` duplicado no contrato `.pyi`
do `BrushProfile`. As regras ficam em `[tool.ruff]` do `pyproject.toml`.
"""
from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _ruff() -> list[str]:
    if importlib.util.find_spec("ruff") is not None:
        return [sys.executable, "-m", "ruff"]
    executable = shutil.which("ruff")
    if executable:
        return [executable]
    pytest.skip("ruff não instalado: python -m pip install -r requirements-dev.txt")


def test_python_code_has_no_lint_findings():
    result = subprocess.run([*_ruff(), "check", "--no-cache", "--output-format", "concise", "."],
                            cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert result.returncode == 0, result.stdout + result.stderr
