"""Conferência rápida antes de cada commit (AGENTS.md, seção 5.1).

Chamado pelo gancho `.githooks/pre-commit` (ativar uma vez por clone com
`git config core.hooksPath .githooks`) ou à mão. Roda em segundos:

1. as catracas e os testes de governança (linter, portabilidade para o Windows,
   README por pasta, acoplamento, idioma dos nomes, cores, leis do rio, camadas
   do motor, raiz, teto de linhas, versão, lock de dependências, ambiente);
2. se o commit toca `engine/`, `bridge/` ou `setup.py`: no Linux/macOS, a
   compilação para Windows com MinGW (`scripts/check_windows_build.py`); no
   Windows, lembra de recompilar o motor e rodar a suíte.

Confere a cópia de trabalho, não só o que está no índice. Não substitui a
suíte completa (`python -m pytest`), obrigatória antes do push.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FAST_TESTS = (
    "tests/test_python_lint.py",
    "tests/test_windows_portability.py",
    "tests/test_arccc_package_docs.py",
    "tests/test_arccc_coupling_ratchet.py",
    "tests/test_arccc_identifier_language_ratchet.py",
    "tests/test_hardcoded_colors_ratchet.py",
    "tests/test_river_ratchets.py",
    "tests/test_arccc_cxx_layers.py",
    "tests/test_arccc_root_layout.py",
    "tests/test_arccc_architecture_invariants.py",
    "tests/test_arccc_cpp_and_docs_governance.py",
    "tests/test_app_version.py",
    "tests/test_dependency_lock_contract.py",
    "tests/test_dev_environment.py",
)
NATIVE_PREFIXES = ("engine/", "bridge/", "setup.py")
MINGW = ("x86_64-w64-mingw32-g++-posix", "x86_64-w64-mingw32-g++")


def staged_files() -> list[str]:
    out = subprocess.run(["git", "diff", "--cached", "--name-only"], cwd=ROOT, capture_output=True,
                         text=True, encoding="utf-8", check=True).stdout
    return [line for line in out.splitlines() if line]


def touches_native(files: list[str]) -> bool:
    return any(name.startswith(NATIVE_PREFIXES) for name in files)


def main() -> int:
    files = staged_files()
    if not files:
        return 0
    env = dict(os.environ, QT_QPA_PLATFORM=os.environ.get("QT_QPA_PLATFORM", "offscreen"))
    tests = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *FAST_TESTS],
                           cwd=ROOT, env=env)
    if tests.returncode:
        print("\npre-commit: catraca ou teste de governança falhou (acima). Corrija ou use --no-verify.")
        return tests.returncode
    if touches_native(files):
        if os.name == "nt":
            print("pre-commit: o commit toca o motor. Antes do push: "
                  "python scripts/build_native.py --simd scalar e python -m pytest")
        elif any(shutil.which(name) for name in MINGW):
            build = subprocess.run([sys.executable, "scripts/check_windows_build.py"], cwd=ROOT)
            if build.returncode:
                print("\npre-commit: o motor não compila para Windows (acima).")
                return build.returncode
        else:
            print("pre-commit: sem MinGW-w64, a compilação para Windows ficou de fora "
                  "(apt-get install g++-mingw-w64-x86-64-posix).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
