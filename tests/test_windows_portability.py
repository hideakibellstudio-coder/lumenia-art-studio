"""Portabilidade para o Windows, conferida em qualquer sistema.

O Lumenia roda no Windows e o CI compila com MSVC, mas os agentes costumam
trabalhar em Linux, onde estes erros passam despercebidos e só aparecem na
máquina do dono ou no CI:

- dois arquivos cujo nome só difere na caixa (o Windows não distingue);
- nome inválido no Windows (`<>:"|?*`, CON/NUL/COM1..., ponto ou espaço no fim);
- caminho longo demais para o MAX_PATH (260) depois do prefixo do clone;
- texto lido/gravado sem `encoding`: no Windows o padrão é cp1252, e acento
  vira erro ou texto corrompido;
- texto já corrompido por isso (o "ó" de "módulo" gravado como "\u00c3\u00b3"):
  achado em 2026-09-25 no `setup.py`, gravado assim pelo commit d52783d.

O que só o compilador do Windows vê (`#ifdef _WIN32`, cabeçalhos) é conferido
por `scripts/check_windows_build.py` (MinGW-w64), que o agente em Linux roda
antes de cada commit (AGENTS.md, seção 5).
"""
from __future__ import annotations

import ast
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
# Clone em algo como C:\Users\<nome>\Documents\GitHub\lumenia-art-studio\ gasta
# ~70 caracteres; sobra folga para o build e para nomes de usuário longos.
MAX_REPO_PATH = 160
INVALID_CHARS = re.compile(r'[<>:"|?*\\]')
RESERVED = {"con", "prn", "aux", "nul", *(f"com{i}" for i in range(1, 10)), *(f"lpt{i}" for i in range(1, 10))}
BINARY_SUFFIXES = {".png", ".jpg", ".jpeg", ".ico", ".icns", ".pyd", ".so", ".lmn", ".ttf", ".otf", ".zip", ".gif", ".webp"}
# UTF-8 lido como cp1252: U+00C3 + byte de continuação, ou U+00E2 U+20AC (aspas e travessões).
MOJIBAKE = re.compile("\u00c3[\u00a0-\u00bf\u0152\u0153\u0160\u0161\u0178\u017d\u017e\u0192\u02c6\u02dc\u2013\u2014\u2018-\u201e\u2020-\u2022\u2026\u2030\u2039\u203a\u20ac\u2122]|\u00e2\u20ac")


def _tracked() -> list[str]:
    try:
        out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True,
                             encoding="utf-8", check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("git indisponível: a checagem usa os arquivos versionados")
    return [line for line in out.splitlines() if line and (ROOT / line).is_file()]


def test_no_two_paths_differ_only_by_case():
    seen: dict[str, str] = {}
    clashes = []
    for path in _tracked():
        other = seen.setdefault(path.lower(), path)
        if other != path:
            clashes.append((other, path))
    assert clashes == [], f"no Windows estes arquivos são o mesmo: {clashes}"


def test_file_names_are_valid_on_windows():
    invalid = [
        path for path in _tracked() for part in path.split("/")
        if INVALID_CHARS.search(part) or part != part.rstrip(". ") or part.split(".")[0].lower() in RESERVED
    ]
    assert invalid == [], f"nome inválido no Windows: {invalid}"


def test_paths_fit_the_windows_max_path():
    long_paths = [(len(path), path) for path in _tracked() if len(path) > MAX_REPO_PATH]
    assert long_paths == [], f"caminho com mais de {MAX_REPO_PATH} caracteres: {long_paths}"


def test_text_files_are_utf8_without_mojibake():
    problems = []
    for path in _tracked():
        if Path(path).suffix.lower() in BINARY_SUFFIXES:
            continue
        data = (ROOT / path).read_bytes()
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            problems.append(f"{path}: não é UTF-8")
            continue
        for number, line in enumerate(text.splitlines(), 1):
            if MOJIBAKE.search(line):
                problems.append(f"{path}:{number}: texto corrompido ({line.strip()[:60]})")
    assert problems == [], "\n".join(problems)


def _text_io_without_encoding(tree: ast.AST) -> list[int]:
    lines = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        keywords = {k.arg for k in node.keywords}
        if "encoding" in keywords:
            continue
        if isinstance(node.func, ast.Name) and node.func.id == "open":
            mode = node.args[1] if len(node.args) > 1 else next((k.value for k in node.keywords if k.arg == "mode"), None)
            if not (isinstance(mode, ast.Constant) and "b" in str(mode.value)):
                lines.append(node.lineno)
        elif isinstance(node.func, ast.Attribute) and node.func.attr in ("read_text", "write_text"):
            positional_encoding = len(node.args) > (0 if node.func.attr == "read_text" else 1)
            if not positional_encoding:
                lines.append(node.lineno)
    return lines


def test_python_text_io_declares_the_encoding():
    offenders = []
    for path in _tracked():
        if path.endswith(".py"):
            tree = ast.parse((ROOT / path).read_text(encoding="utf-8"), filename=path)
            offenders += [f"{path}:{line}" for line in _text_io_without_encoding(tree)]
    assert offenders == [], "open/read_text/write_text de texto sem encoding= (cp1252 no Windows):\n" + "\n".join(offenders)
