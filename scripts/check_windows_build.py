"""Compila o motor e a ponte para o alvo Windows a partir do Linux (MinGW-w64).

O Lumenia roda no Windows e o CI compila com MSVC, mas agentes costumam
trabalhar em Linux, onde g++ nunca passa pelos trechos `#ifdef _WIN32` nem pelos
cabeçalhos do Windows. Este script faz a checagem que falta antes do commit:
todos os `.cpp` de `setup.py` (a mesma lista do build oficial) compilados com
`x86_64-w64-mingw32-g++`, com os cabeçalhos do CPython para Windows, nas duas
variantes que o CI compila (escalar e AVX2). Só análise (`-fsyntax-only`):
nada é gravado no repositório. Aviso é erro (`-Wall -Wextra -Werror`): o motor
chegou a zero avisos em 2026-09-25 e aviso novo reprova; os cabeçalhos de
terceiros (CPython, pybind11) entram como `-isystem` e ficam de fora.

Uso:
    python scripts/check_windows_build.py                  # escalar e AVX2
    python scripts/check_windows_build.py --simd scalar
    python scripts/check_windows_build.py --python-include DIR

Pré-requisito (Debian/Ubuntu): `apt-get install g++-mingw-w64-x86-64-posix`.
Os cabeçalhos do Python para Windows são baixados uma vez para
`~/.cache/lumenia/windows-python/` (ou use `--python-include`, ou a variável
`LUMENIA_WIN_PYTHON_INCLUDE`). No Windows, o teste é o próprio build:
`python scripts/build_native.py`.
"""
from __future__ import annotations

import argparse
import ast
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPILERS = ("x86_64-w64-mingw32-g++-posix", "x86_64-w64-mingw32-g++")
PYTHON_TAG = "3.12.7+20241016"
PYTHON_URL = (
    "https://github.com/astral-sh/python-build-standalone/releases/download/20241016/"
    "cpython-3.12.7%2B20241016-x86_64-pc-windows-msvc-install_only.tar.gz"
)
CACHE = Path.home() / ".cache" / "lumenia" / "windows-python" / PYTHON_TAG
VARIANTS = {"scalar": [], "avx2": ["-mavx2", "-mfma"]}


def setup_sources() -> list[str]:
    """Lista `cpp_sources` do setup.py, lida sem executar o setup."""
    tree = ast.parse((ROOT / "setup.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "cpp_sources" for t in node.targets):
            return [elt.value for elt in node.value.elts]
    raise SystemExit("setup.py sem a lista cpp_sources")


def find_compiler() -> str:
    for name in COMPILERS:
        if shutil.which(name):
            return name
    raise SystemExit(
        "MinGW-w64 não encontrado. Instale com: apt-get install g++-mingw-w64-x86-64-posix"
    )


def python_include(explicit: str | None) -> Path:
    candidate = explicit or os.environ.get("LUMENIA_WIN_PYTHON_INCLUDE")
    if candidate:
        path = Path(candidate)
        if not (path / "Python.h").is_file():
            raise SystemExit(f"sem Python.h em {path}")
        return path
    include = CACHE / "python" / "include"
    if (include / "Python.h").is_file():
        return include
    print(f"Baixando os cabeçalhos do CPython {PYTHON_TAG} para Windows (uma vez)...", flush=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        archive = Path(tmp) / "python.tar.gz"
        try:
            urllib.request.urlretrieve(PYTHON_URL, archive)
        except OSError:
            subprocess.run(["curl", "-sSLf", "-o", str(archive), PYTHON_URL], check=True)
        with tarfile.open(archive) as tar:
            members = [m for m in tar.getmembers() if m.name.startswith("python/include/")]
            safe = {"filter": "data"} if hasattr(tarfile, "data_filter") else {}
            tar.extractall(CACHE, members=members, **safe)
    return include


def compile_one(compiler: str, flags: list[str], source: str) -> tuple[str, str]:
    result = subprocess.run([compiler, *flags, source], cwd=ROOT, capture_output=True,
                            text=True, encoding="utf-8", errors="replace")
    errors = "\n".join(line for line in result.stderr.splitlines() if "error" in line)
    return source, errors if result.returncode else ""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--simd", choices=("scalar", "avx2", "both"), default="both")
    parser.add_argument("--python-include")
    args = parser.parse_args(argv)

    import pybind11

    compiler = find_compiler()
    base = ["-std=c++20", "-fsyntax-only", "-fopenmp", "-Wall", "-Wextra", "-Werror",
            "-isystem", str(python_include(args.python_include)), "-isystem", pybind11.get_include()]
    sources = setup_sources()
    variants = list(VARIANTS) if args.simd == "both" else [args.simd]
    failed = 0
    for variant in variants:
        flags = base + VARIANTS[variant]
        with ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as pool:
            results = list(pool.map(lambda s: compile_one(compiler, flags, s), sources))
        broken = [(source, errors) for source, errors in results if errors]
        for source, errors in broken:
            print(f"[{variant}] {source}\n{errors}\n")
        print(f"[{variant}] {len(sources) - len(broken)}/{len(sources)} arquivos compilam para Windows")
        failed += len(broken)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
