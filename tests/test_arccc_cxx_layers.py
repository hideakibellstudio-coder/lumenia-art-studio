"""Camadas do pilar C++ (motor e ponte), medidas pelo #include.

Até 2026-09-25 o motor tinha 9 pares de pastas em ciclo (canvas <-> document
pelo histórico, raster <-> brush/canvas/color/math pelo Dab, e subpastas
incluindo a pasta-mãe) e a ponte incluía o interior do motor. A estrutura
passou a ser em camadas, de baixo para cima:

    engine/utils -> engine/infrastructure/* -> engine/core/<módulo> (na ordem
    de CORE_ORDER) -> engine/boundary/orchestrator -> engine/boundary/public-api
    -> bridge (só por public-api/AladynEngine.hpp)

Uma pasta só inclui camadas abaixo dela; subpasta nunca inclui a pasta-mãe.
Módulo novo em engine/core entra em CORE_ORDER no lugar que as dependências
dele pedem (e no README de engine/core).
"""
from __future__ import annotations

import os
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INCLUDE = re.compile(r'#include\s+"([^"]+)"')
SUFFIXES = (".hpp", ".cpp", ".h")
PUBLIC_HEADER = "engine/boundary/public-api/AladynEngine.hpp"

# Módulos de engine/core, de baixo para cima: cada um só inclui os anteriores.
CORE_ORDER = ["math", "texture", "color", "stroke", "canvas", "selection",
              "brush", "document", "history", "raster", "engines"]


def _file_edges() -> list[tuple[str, str]]:
    edges = []
    for base in ("engine", "bridge"):
        for source in sorted((ROOT / base).rglob("*")):
            if source.suffix not in SUFFIXES:
                continue
            for include in INCLUDE.findall(source.read_text(encoding="utf-8", errors="ignore")):
                target = (source.parent / include).resolve()
                if target.is_file():
                    edges.append((source.relative_to(ROOT).as_posix(), target.relative_to(ROOT).as_posix()))
    return edges


EDGES = _file_edges()


def _folder_edges() -> dict[str, set[str]]:
    graph: dict[str, set[str]] = defaultdict(set)
    for source, target in EDGES:
        a, b = os.path.dirname(source), os.path.dirname(target)
        if a != b:
            graph[a].add(b)
    return graph


def _layer(folder: str) -> tuple[int, int]:
    """(camada, posição dentro de engine/core) de uma pasta do pilar C++."""
    parts = folder.split("/")
    if parts[0] == "bridge":
        return (5, 0)
    if parts[1] == "utils":
        return (0, 0)
    if parts[1] == "infrastructure":
        return (1, 0)
    if parts[1] == "core":
        return (2, CORE_ORDER.index(parts[2]))
    return (3, 0) if parts[2] == "orchestrator" else (4, 0)


def _module(folder: str) -> str:
    """Pasta de primeiro nível dentro da camada (engine/core/document/filters -> engine/core/document)."""
    parts = folder.split("/")
    return "/".join(parts[:3]) if parts[0] == "engine" and parts[1] in ("core", "boundary", "infrastructure") else "/".join(parts[:2])


def test_core_modules_are_all_in_the_declared_order():
    modules = sorted(p.name for p in (ROOT / "engine/core").iterdir() if p.is_dir() and p.name != "__pycache__")
    assert modules == sorted(CORE_ORDER), "módulo novo em engine/core: declare a posição em CORE_ORDER"


def test_no_folder_cycles():
    graph = _folder_edges()
    cycles = sorted({tuple(sorted((a, b))) for a in graph for b in graph[a] if a in graph.get(b, set())})
    assert cycles == [], f"pastas que se incluem mutuamente: {cycles}"


def test_subfolder_never_includes_its_parent():
    upward = [(s, t) for s, t in EDGES if os.path.dirname(s).startswith(os.path.dirname(t) + "/")]
    assert upward == [], "subpasta incluindo a pasta-mãe (a mãe é que usa a filha):\n" + "\n".join(f"{s} -> {t}" for s, t in upward)


def test_includes_only_go_down_the_layers():
    wrong = []
    for source, target in EDGES:
        a, b = os.path.dirname(source), os.path.dirname(target)
        if a == b or _module(a) == _module(b):
            continue
        if _layer(b) >= _layer(a):
            wrong.append(f"{source} -> {target}")
    assert wrong == [], "inclusão para o lado ou para cima:\n" + "\n".join(wrong)


def test_bridge_reaches_the_engine_only_through_the_public_header():
    outside = sorted({t for s, t in EDGES if s.startswith("bridge/") and t.startswith("engine/") and t != PUBLIC_HEADER})
    assert outside == [], f"a ponte inclui o interior do motor: {outside}"
    assert any(t == PUBLIC_HEADER for s, t in EDGES if s.startswith("bridge/"))
