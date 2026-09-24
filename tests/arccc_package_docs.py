"""Documentação por pasta (ARCcC): TODA pasta do repositório tem README.md.

"Toda pasta" é toda pasta com arquivos (própria ou de subpastas), fora as de
ferramenta e de build (`.git`, `__pycache__`, `build`, caches...): ui/,
plugins/, engine/, bridge/, tests/, scripts/, docs/, assets/, .github/...
Até 2026-09-24 só as pastas com .py de ui/ e plugins/ eram conferidas, e 51
das 111 pastas (o motor C++ inteiro, a ponte, os testes) não tinham README.

O README de cada pasta tem que:
1. existir;
2. citar cada arquivo de código ou documento da pasta (entre crases, ex.:
   `toolbar.py`, `TileGrid.hpp`, `01-pendencias-atuais.md`) — arquivo novo sem
   explicação no README faz o teste falhar. Arquivos de dados (ícones, temas,
   locales) não precisam ser citados um a um;
3. nas pastas de código dos pilares (Python em ui/ e plugins/, C++ em engine/
   e bridge/), declarar entre os marcadores abaixo exatamente as pastas que o
   código importa/inclui (dependências internas):

       <!-- arccc:deps -->
       - `ui/core/state`
       - `aladyn_engine_native`
       <!-- /arccc:deps -->

   Import novo entre jurisdições aparece no diff do README: é uma decisão, não
   um acidente. Dependência que some também tem que sair da lista.
4. não conter marcadores de rascunho (`A PREENCHER`).

Linha de comando:
    python -m tests.arccc_package_docs                 # relatório de pendências
    python -m tests.arccc_package_docs --deps PASTA    # dependências medidas de uma pasta
    python -m tests.arccc_package_docs --scaffold PASTA  # esqueleto de README (não sobrescreve)
"""
from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASES = ("ui", "plugins")          # pilares Python: dependências por import
CXX_BASES = ("engine", "bridge")   # pilares C++: dependências por #include
NATIVE = "aladyn_engine_native"
CXX_SUFFIXES = (".hpp", ".cpp", ".h")
# Arquivos que o README cita um a um (código e documentos). Dados não.
CITED_SUFFIXES = (".py", ".pyi", *CXX_SUFFIXES, ".md", ".ps1", ".iss", ".yml", ".bat", ".vbs")
SKIPPED_DIRS = {".git", "__pycache__", "build", "dist", ".pytest_cache", ".mypy_cache",
                ".ruff_cache", ".venv", "venv", "env", "node_modules"}
_INCLUDE = re.compile(r'#include\s+"([^"]+)"')
DEPS_BLOCK = re.compile(r"<!--\s*arccc:deps\s*-->(.*?)<!--\s*/arccc:deps\s*-->", re.S)
DRAFT_MARK = "A PREENCHER"


def _skipped(folder: Path) -> bool:
    parts = folder.relative_to(ROOT).parts
    return any(part in SKIPPED_DIRS or part.endswith(".egg-info")
               or (part.startswith(".") and part != ".github") for part in parts)


def packages() -> list[Path]:
    """Toda pasta documentável do repositório (com arquivos nela ou abaixo)."""
    found = []
    for folder in sorted(ROOT.rglob("*")):
        if folder.is_dir() and not _skipped(folder) and any(
                f.is_file() and not _skipped(f.parent) for f in folder.rglob("*")):
            found.append(folder)
    return found


def _pillar(folder: Path) -> str:
    parts = folder.relative_to(ROOT).parts
    return parts[0] if parts else ""


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _module_to_package(module: str) -> str | None:
    """'ui.core.state.brush_state' -> 'ui/core/state' (a pasta que contém o módulo)."""
    if module == NATIVE or module.startswith(NATIVE + "."):
        return NATIVE
    parts = module.split(".")
    if parts[0] not in BASES:
        return None
    for cut in range(len(parts), 0, -1):
        candidate = ROOT.joinpath(*parts[:cut])
        if candidate.is_dir() and any(candidate.glob("*.py")):
            return "/".join(parts[:cut])
        if candidate.with_suffix(".py").is_file():
            return "/".join(parts[:cut - 1])
    return None


def _resolve_relative(package: Path, node: ast.ImportFrom) -> str | None:
    base = package
    for _ in range(node.level - 1):
        base = base.parent
    dotted = rel(base).replace("/", ".")
    return f"{dotted}.{node.module}" if node.module else dotted


def _cxx_deps(folder: Path) -> set[str]:
    """Pastas de engine/ e bridge/ incluídas (#include "...") pelo C++ desta pasta."""
    own = rel(folder)
    deps: set[str] = set()
    for source in sorted(folder.iterdir()):
        if source.suffix not in CXX_SUFFIXES:
            continue
        for include in _INCLUDE.findall(source.read_text(encoding="utf-8", errors="ignore")):
            target = (folder / include).resolve()
            if target.is_file():
                dep = rel(target.parent)
                if dep != own and _pillar(target.parent) in CXX_BASES:
                    deps.add(dep)
    return deps


def has_deps_block(folder: Path) -> bool:
    """Pastas de código dos pilares declaram dependências; docs, dados e testes não."""
    pillar = _pillar(folder)
    if pillar in BASES:
        return any(folder.glob("*.py"))
    if pillar in CXX_BASES:
        return any(f.suffix in CXX_SUFFIXES for f in folder.iterdir())
    return False


def measured_deps(package: Path) -> set[str]:
    """Pastas internas usadas pelo código desta pasta (sem ela mesma)."""
    if _pillar(package) in CXX_BASES:
        return _cxx_deps(package)
    own = rel(package)
    deps: set[str] = set()
    for source in package.glob("*.py"):
        tree = ast.parse(source.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            modules: list[str] = []
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    base = _resolve_relative(package, node)
                    modules = [base] if node.module else [f"{base}.{a.name}" for a in node.names]
                else:
                    modules = [node.module or ""]
                    # "from ui.core import tools" importa o módulo ui/core/tools.py
                    modules += [f"{node.module}.{a.name}" for a in node.names] if node.module else []
            for module in modules:
                target = _module_to_package(module)
                if target and target != own:
                    deps.add(target)
    # "import ui" sozinho não diz nada sobre jurisdição: só pastas concretas contam.
    return {d for d in deps if d not in BASES}


def declared_deps(readme_text: str) -> set[str] | None:
    match = DEPS_BLOCK.search(readme_text)
    if match is None:
        return None
    return set(re.findall(r"`([^`]+)`", match.group(1)))


def problems(package: Path) -> list[str]:
    readme = package / "README.md"
    if not readme.is_file():
        return ["sem README.md"]
    text = readme.read_text(encoding="utf-8")
    found = []
    missing_files = [p.name for p in sorted(package.iterdir())
                     if p.is_file() and p.suffix in CITED_SUFFIXES and p.name != "README.md"
                     and f"`{p.name}`" not in text]
    if missing_files:
        found.append(f"arquivos sem menção no README: {', '.join(missing_files)}")
    declared = declared_deps(text)
    if not has_deps_block(package):
        if declared is not None:
            found.append("bloco arccc:deps numa pasta sem código de pilar (tire o bloco)")
    elif declared is None:
        found.append("sem bloco <!-- arccc:deps --> ... <!-- /arccc:deps -->")
    else:
        actual = measured_deps(package)
        if actual - declared:
            found.append(f"importa sem declarar: {', '.join(sorted(actual - declared))}")
        if declared - actual:
            found.append(f"declara mas não importa: {', '.join(sorted(declared - actual))}")
    if DRAFT_MARK in text:
        found.append(f"rascunho: contém '{DRAFT_MARK}'")
    return found


def deps_block(package: Path) -> str:
    lines = [f"- `{dep}`" for dep in sorted(measured_deps(package))] or ["(nenhuma dependência interna)"]
    return "<!-- arccc:deps -->\n" + "\n".join(lines) + "\n<!-- /arccc:deps -->"


def _first_doc_line(source: Path) -> str:
    try:
        doc = ast.get_docstring(ast.parse(source.read_text(encoding="utf-8"))) or ""
    except SyntaxError:
        return ""
    return doc.strip().splitlines()[0] if doc.strip() else ""


def scaffold(package: Path) -> str:
    cited = [p for p in sorted(package.iterdir())
             if p.is_file() and p.suffix in CITED_SUFFIXES and p.name != "README.md"]
    rows = "\n".join(f"| `{p.name}` | {_first_doc_line(p) if p.suffix == '.py' else DRAFT_MARK} |"
                     for p in cited)
    return (
        f"# `{rel(package)}/`\n\n"
        f"**Responsabilidade:** {DRAFT_MARK}\n\n"
        f"## Porta de entrada\n\n{DRAFT_MARK}\n\n"
        f"## Arquivos\n\n| Arquivo | Responsabilidade |\n|---|---|\n{rows}\n\n"
        f"## Regras\n\n{DRAFT_MARK}\n"
        + (f"\n## Dependências internas\n\n"
           f"Medidas pelo teste `tests/test_arccc_package_docs.py`; import novo entre\n"
           f"pastas entra aqui junto (e é uma decisão de arquitetura, não detalhe).\n\n"
           f"{deps_block(package)}\n" if has_deps_block(package) else "")
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--deps", metavar="PASTA")
    parser.add_argument("--scaffold", metavar="PASTA")
    args = parser.parse_args(argv)
    if args.deps:
        print(deps_block(ROOT / args.deps))
        return 0
    if args.scaffold:
        target = ROOT / args.scaffold / "README.md"
        if target.exists():
            print(f"{rel(target)} já existe; nada foi escrito.")
            return 1
        target.write_text(scaffold(ROOT / args.scaffold), encoding="utf-8")
        print(f"esqueleto escrito em {rel(target)} (troque cada '{DRAFT_MARK}')")
        return 0
    pending = {rel(p): problems(p) for p in packages()}
    pending = {k: v for k, v in pending.items() if v}
    for name, issues in pending.items():
        print(f"{name}: " + "; ".join(issues))
    print(f"\n{len(packages()) - len(pending)}/{len(packages())} pastas documentadas")
    return 1 if pending else 0


if __name__ == "__main__":
    sys.exit(main())
